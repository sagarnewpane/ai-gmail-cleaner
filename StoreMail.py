import time
import random
import sqlite3

from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest


def fetch_all_message_ids(service, query=""):
    """Fetch all message IDs in the account for batching."""
    all_ids = []
    page_token = None

    while True:
        results = service.users().messages().list(
            userId="me",
            q=query,
            pageToken=page_token,
            maxResults=500  # max allowed per page
        ).execute()

        messages = results.get("messages", [])
        all_ids.extend([m["id"] for m in messages])

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    return all_ids


def fetch_all_messages(service, message_ids, batch_size=50, max_retries=5):
    """
    Fetch all messages in batches with retries until every message is fetched.

    Args:
        service: Gmail API service instance
        message_ids: List of Gmail message IDs
        batch_size: Number of messages per batch
        max_retries: Max retry attempts per batch

    Returns:
        List of successfully fetched messages
    """
    all_messages = []
    remaining_ids = list(message_ids)  # copy of IDs to track unfetched

    while remaining_ids:
        print(f"Remaining messages: {len(remaining_ids)}")
        next_round_ids = []

        # Process in batches
        for i in range(0, len(remaining_ids), batch_size):
            batch_ids = remaining_ids[i:i + batch_size]

            success_ids = []

            for attempt in range(max_retries):
                batch_messages = []

                def callback(request_id, response, exception):
                    if exception:
                        # if 429, keep ID for retry
                        if hasattr(exception, 'resp') and exception.resp.status == 429:
                            next_round_ids.append(request_id)
                        else:
                            print(f"Error fetching {request_id}: {exception}")
                    else:
                        batch_messages.append(response)
                        success_ids.append(request_id)

                batch = BatchHttpRequest(callback=callback, batch_uri='https://gmail.googleapis.com/batch')

                for msg_id in batch_ids:
                    batch.add(service.users().messages().get(
                        userId="me",
                        id=msg_id,
                        format="metadata",
                        metadataHeaders=["From","Subject","Date","List-Unsubscribe"]
                    ), request_id=msg_id)

                try:
                    batch.execute()
                    break  # batch succeeded
                except HttpError as e:
                    if e.resp.status == 429:
                        sleep_time = (2 ** attempt) + random.random()
                        print(f"Rate limit hit. Retrying in {sleep_time:.2f} sec...")
                        time.sleep(sleep_time)
                    else:
                        print(f"HttpError: {e}")
                        # mark batch IDs for retry in next round
                        next_round_ids.extend(batch_ids)
                        break

            # store successful messages
            all_messages.extend(batch_messages)
            time.sleep(0.3)  # small pause between batches

        # prepare next round with remaining IDs
        remaining_ids = list(set(next_round_ids))
        if remaining_ids:
            print(f"Retrying {len(remaining_ids)} failed messages...")

    print(f"All messages fetched: {len(all_messages)}")
    return all_messages


def parse_email_metadata(msg):
    headers = {h['name']: h['value'] for h in msg['payload']['headers']}

    email_data = {
        "id": msg['id'],
        "from": headers.get("From"),
        "subject": headers.get("Subject"),
        "date": headers.get("Date"),
        "unsubscribe_url": None,
        "snippet": msg.get("snippet"),  # add snippet for context
    }

    # Extract List-Unsubscribe URL
    unsub_header = headers.get("List-Unsubscribe")
    if unsub_header:
        import re
        urls = re.findall(r'<(https?://[^>]+)>', unsub_header)
        if urls:
            email_data["unsubscribe_url"] = urls[0]

    return email_data


def insert_emails_transaction(emails, db_name="emails.db"):
    """
    Insert a list of emails into the SQLite database using a single transaction.
    Faster than inserting one by one.

    emails: list of dicts with keys: id, from, subject, date, body, category, unsubscribe_url
    """
    if not emails:
        return

    # Prepare data for bulk insert
    data = [
        (
            e.get("id"),
            e.get("from"),
            e.get("subject"),
            e.get("date"),
            e.get("snippet"),
            e.get("category"),
            e.get("unsubscribe_url")
        )
        for e in emails
    ]

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    try:
        conn.execute("BEGIN TRANSACTION")  # start transaction
        cursor.executemany("""
            INSERT OR REPLACE INTO emails
            (id, sender, subject, date, snippet, category, unsubscribe_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()  # commit once
        print(f"Inserted {len(emails)} emails successfully.")
    except sqlite3.Error as e:
        conn.rollback()  # rollback on error
        print(f"Error inserting emails: {e}")
    finally:
        conn.close()

import sqlite3
from googleapiclient.errors import HttpError

# -------------------------------
# 1. Ensure Review Label Exists
# -------------------------------
def get_or_create_label(service, label_name="Review_Not_Important", user_id="me"):
    """
    Ensure a Gmail label exists. Create it if missing.
    """
    try:
        results = service.users().labels().list(userId=user_id).execute()
        labels = results.get("labels", [])

        for label in labels:
            if label["name"] == label_name:
                print(f"Found label: {label_name}")
                return label["id"]

        # If not found, create it
        label_body = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }
        new_label = service.users().labels().create(userId=user_id, body=label_body).execute()
        print(f"Created new label: {label_name}")
        return new_label["id"]

    except HttpError as e:
        print("[WARNING] Error creating/getting label:", e)
        return None


# -------------------------------
# 2. Fetch NOT IMPORTANT IDs from DB
# -------------------------------
def fetch_not_important_ids(db="emails.db"):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM emails
        WHERE category='NOT IMPORTANT' AND reviewed=0
    """)
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids


# -------------------------------
# 3. Apply Review Label in Gmail
# -------------------------------
def label_not_important(service, review_label_id, db="emails.db", user_id="me"):
    """
    Add review label to all NOT IMPORTANT emails from DB.
    Returns the number of messages labeled.
    """
    msg_ids = fetch_not_important_ids(db)
    if not msg_ids:
        print("No NOT IMPORTANT emails found in DB.")
        return 0

    try:
        # Gmail API can handle only up to 1000 IDs per request
        chunk_size = 1000
        for i in range(0, len(msg_ids), chunk_size):
            chunk = msg_ids[i:i+chunk_size]
            service.users().messages().batchModify(
                userId=user_id,
                body={
                    "ids": chunk,
                    "addLabelIds": [review_label_id]
                }
            ).execute()

        print(f"Labeled {len(msg_ids)} messages with Review_Not_Important.")
        return len(msg_ids)

    except HttpError as e:
        print("[WARNING] Error labeling mails:", e)
        return 0



# -------------------------------
# 4. Move Review Label mails to Trash
# -------------------------------
def move_to_trash(service, msg_ids, user_id="me"):
    """
    Move a list of message IDs to Trash in chunks to avoid timeouts.
    """
    if not msg_ids:
        print("No messages to move to Trash.")
        return 0

    chunk_size = 500  # adjust as needed
    total = 0

    for i in range(0, len(msg_ids), chunk_size):
        chunk = msg_ids[i:i + chunk_size]
        try:
            service.users().messages().batchModify(
                userId=user_id,
                body={
                    "ids": chunk,
                    "addLabelIds": ["TRASH"]
                }
            ).execute()
            total += len(chunk)
            print(f"Moved {len(chunk)} messages to Trash (batch {i // chunk_size + 1})")
        except HttpError as e:
            print(f"[WARNING] Error moving batch {i // chunk_size + 1} to Trash:", e)
        except Exception as e:
            print(f"[WARNING] Unexpected error in batch {i // chunk_size + 1}:", e)

    print(f"Total messages moved to Trash: {total}")
    return total


def mark_as_reviewed(ids, db="emails.db"):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.executemany("UPDATE emails SET reviewed=1 WHERE id=?", [(i,) for i in ids])
    conn.commit()
    conn.close()

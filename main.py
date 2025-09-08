import os
import time
from connectGmail import gmail_service
from CreateDb import create_db
import ClassifyMail
from SortMail import (
    get_or_create_label,
    fetch_not_important_ids,
    move_to_trash,
    label_not_important,
    mark_as_reviewed
)
from StoreMail import fetch_all_message_ids, fetch_all_messages, parse_email_metadata, insert_emails_transaction
from Unsubscribe import handle_unsubscribing

# -----------------------
# CONFIG
# -----------------------
DB_PATH = "emails.db"
CHUNK_SIZE = 100  # For classification and labeling

# -----------------------
# MAIN SCRIPT
# -----------------------
def main():
    # 1. Authenticate Gmail
    service = gmail_service()
    service._baseUrl = "https://gmail.googleapis.com/"

    # 2. Initialize DB
    if os.path.exists(DB_PATH):
        while True:
            choice = input(
                f"Database '{DB_PATH}' already exists. What would you like to do?\n"
                "1. Start Fresh (Deletes all existing data)\n"
                "2. Continue with existing data\n"
                "3. Exit\n"
                "Enter your choice (1/2/3): "
            ).strip()
            if choice == '1':
                print("Starting fresh, deleting old database...")
                os.remove(DB_PATH)
                create_db(DB_PATH)
                break
            elif choice == '2':
                print(f"Continuing with existing database '{DB_PATH}'")
                break
            elif choice == '3':
                print("Exiting.")
                return
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    else:
        print(f"Database not found at '{DB_PATH}', creating...")
        create_db(DB_PATH)

    # 3. Fetch all message IDs from Gmail
    print("Fetching all message IDs from Gmail...")
    message_ids = fetch_all_message_ids(service)
    print(f"Total messages fetched: {len(message_ids)}")

    # 4. Fetch messages in batches
    print("Fetching full message data in batches...")
    start_time = time.time()
    all_messages = fetch_all_messages(service, message_ids, batch_size=CHUNK_SIZE)
    end_time = time.time()
    print(f"Fetched {len(all_messages)} messages in {end_time - start_time:.2f}s")

    # 5. Parse emails
    print("Parsing emails...")
    parsed_emails = [parse_email_metadata(msg) for msg in all_messages]

    # 6. Store emails in DB using a transaction
    print(f"Inserting {len(parsed_emails)} emails into DB...")
    insert_emails_transaction(parsed_emails, db_name=DB_PATH)
    print("[SUCCESS] Emails stored in DB")

    # 7. Classify unclassified emails in chunks
    print("Classifying emails with Gemini...")
    total_classified = 0
    while True:
        rows = ClassifyMail.fetch_unclassified(db=DB_PATH, limit=CHUNK_SIZE)
        if not rows:
            print("[SUCCESS] All emails are classified")
            break

        try:
            classifications = ClassifyMail.classify_emails(rows)
            ClassifyMail.update_classifications(rows, classifications, db=DB_PATH)
            total_classified += len(rows)
            print(f"[SUCCESS] Classified {total_classified} emails so far")
        except Exception as e:
            print("[WARNING] Error classifying emails:", e)
            time.sleep(2)  # small pause before retrying

    # 8. Handle NOT IMPORTANT emails
    print("Handling NOT IMPORTANT emails...")
    label_id = get_or_create_label(service)
    if not label_id:
        print("[ERROR] Failed to get or create review label. Exiting.")
        return

    non_important_ids = fetch_not_important_ids(db=DB_PATH)
    print(f"Total NOT IMPORTANT emails (unreviewed): {len(non_important_ids)}")

    if non_important_ids:
        print(f"Found {len(non_important_ids)} NOT IMPORTANT emails to process.")
        review_label = input("Move these emails to the 'Review' label in Gmail? (y/n): ")
        if review_label.lower() == 'y':
            labeled_count = label_not_important(service, label_id, db=DB_PATH)
            if labeled_count:
                # Mark as reviewed so they are not processed again
                mark_as_reviewed(non_important_ids, db=DB_PATH)

                review_trash = input("Review your marked emails in Gmail! After reviewing, do you want to move these NOT IMPORTANT emails to Trash? (y/n): ")
                if review_trash.lower() == 'y':
                    move_to_trash(service, non_important_ids)
                    print("[SUCCESS] NOT IMPORTANT emails moved to Trash.")
                else:
                    print("[INFO] Aborted moving emails to Trash.")
            else:
                print("[WARNING] Failed to label NOT IMPORTANT emails.")
        else:
            print("[INFO] Aborted labeling emails.")
    else:
        print("[INFO] No NOT IMPORTANT emails to process")

    # 9. Handle Unsubscribe Links
    handle_unsubscribing(db_name=DB_PATH)

if __name__ == "__main__":
    main()

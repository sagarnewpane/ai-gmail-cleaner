import sqlite3
import csv

def get_unsubscribe_links(db_name="emails.db"):
    """Fetches emails with unsubscribe links from the database."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT sender, subject, unsubscribe_url FROM emails WHERE unsubscribe_url IS NOT NULL AND unsubscribe_url != ''")
    rows = cursor.fetchall()
    conn.close()
    return rows

def export_to_csv(unsubscribe_list):
    """Exports the list of unsubscribe links to a CSV file."""
    filename = "unsubscribe_links.csv"
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Sender', 'Subject', 'Unsubscribe Link'])
        writer.writerows(unsubscribe_list)
    print(f"Exported {len(unsubscribe_list)} unsubscribe links to '{filename}'.")

def print_to_terminal(unsubscribe_list):
    """Prints the list of unsubscribe links to the terminal."""
    print("\n--- Unsubscribe Links ---")
    for i, (sender, subject, url) in enumerate(unsubscribe_list):
        print(f"{i+1}. From: {sender}")
        print(f"   Subject: {subject}")
        print(f"   Link: {url}\n")
    print("--- End of Links ---")

def handle_unsubscribing(db_name="emails.db"):
    """Handles the user interaction for unsubscribing from emails."""
    unsubscribe_list = get_unsubscribe_links(db_name)
    if not unsubscribe_list:
        print("\nNo emails with unsubscribe links found.")
        return

    while True:
        print(f"\nFound {len(unsubscribe_list)} emails with unsubscribe links.")
        choice = input(
            "What would you like to do?\n"
            "1. Export links to unsubscribe_links.csv\n"
            "2. Print links in the terminal\n"
            "3. Both export and print\n"
            "4. Skip\n"
            "Enter your choice (1/2/3/4): "
        ).strip()

        if choice == '1':
            export_to_csv(unsubscribe_list)
            break
        elif choice == '2':
            print_to_terminal(unsubscribe_list)
            break
        elif choice == '3':
            export_to_csv(unsubscribe_list)
            print_to_terminal(unsubscribe_list)
            break
        elif choice == '4':
            print("Skipping unsubscribe process.")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, or 4.")
            
    print("\nUnsubscribe process finished.")

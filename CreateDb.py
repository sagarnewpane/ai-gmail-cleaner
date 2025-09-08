import sqlite3

def create_db(db_name="emails.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id TEXT PRIMARY KEY,
        sender TEXT,
        subject TEXT,
        date TEXT,
        snippet TEXT,
        category TEXT,
        unsubscribe_url TEXT,
        reviewed INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()
    print(f"Database '{db_name}' created with table 'emails'")

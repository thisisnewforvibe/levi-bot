"""
Migration script to add initial_reminder_sent field to existing reminders table.
Run this once to update the database schema.
"""

import sqlite3
from config import DATABASE_PATH

def migrate():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(reminders)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'initial_reminder_sent' not in columns:
        print("Adding initial_reminder_sent column...")
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE reminders 
            ADD COLUMN initial_reminder_sent INTEGER DEFAULT 0
        """)
        
        # For existing reminders that have follow_up_sent = 1, 
        # set initial_reminder_sent = 1 (they were already sent)
        cursor.execute("""
            UPDATE reminders 
            SET initial_reminder_sent = 1 
            WHERE follow_up_sent = 1
        """)
        
        # Reset follow_up_sent to 0 for pending reminders
        # so they can receive follow-up questions
        cursor.execute("""
            UPDATE reminders 
            SET follow_up_sent = 0 
            WHERE status = 'pending' AND initial_reminder_sent = 1
        """)
        
        conn.commit()
        print("✅ Migration completed successfully!")
        print("   - Added initial_reminder_sent column")
        print("   - Updated existing reminders")
        print("   - Reset follow_up_sent for pending reminders")
    else:
        print("⚠️  Column initial_reminder_sent already exists. No migration needed.")
    
    # Show current state
    cursor.execute("""
        SELECT COUNT(*) FROM reminders 
        WHERE status = 'pending' AND initial_reminder_sent = 1 AND follow_up_sent = 0
    """)
    pending_followups = cursor.fetchone()[0]
    
    print(f"\n📊 Current state:")
    print(f"   - Reminders waiting for follow-up: {pending_followups}")
    
    conn.close()

if __name__ == "__main__":
    migrate()

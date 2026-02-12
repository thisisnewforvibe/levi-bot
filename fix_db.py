import sqlite3

conn = sqlite3.connect('reminders.db')
cursor = conn.cursor()

# Mark all stuck reminders as done
cursor.execute("UPDATE reminders SET status = 'done' WHERE id = 2")
conn.commit()

print('Updated reminder 2 to done')

# Show remaining pending reminders
cursor.execute("SELECT id, task_text, status, follow_up_sent FROM reminders WHERE status = 'pending'")
print('Remaining pending:', cursor.fetchall())

conn.close()

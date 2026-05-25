import sqlite3

db_path = 'data/NKJV.SQLite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Books mapping in DB ---")
cursor.execute("SELECT book_number, short_name, long_name FROM books")
for row in cursor.fetchall():
    if "John" in row[2] or row[0] in [430, 360]:
        print(row)

print("\n--- John 3:16 test ---")
cursor.execute("SELECT text FROM verses WHERE book_number=430 AND chapter=3 AND verse=16")
row = cursor.fetchone()
if row:
    print(f"John 3:16 (430): {row[0][:100]}")
else:
    print("John 3:16 (430) not found")

conn.close()

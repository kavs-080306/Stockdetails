import sqlite3

conn = sqlite3.connect('stock.db')
c = conn.cursor()

# Create table if missing
c.execute('''CREATE TABLE IF NOT EXISTS products 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
              name TEXT, quantity INTEGER, category TEXT, 
              updatedAt TEXT)''')

print("=== BEFORE CLEANING ===")
c.execute("SELECT id, name, quantity, category FROM products ORDER BY name")
rows = c.fetchall()
print(f"Total rows: {len(rows)}")
for row in rows:
    print(f"ID:{row[0]} {row[1]} ({row[2]}) - {row[3]}")

# Find & DELETE duplicates (keep FIRST by name)
print("\n=== REMOVING DUPLICATES (keep first by name) ===")
c.execute("""
DELETE FROM products 
WHERE rowid NOT IN (
    SELECT MIN(rowid) 
    FROM products 
    GROUP BY name
)
""")
deleted = c.rowcount
conn.commit()

print(f"✅ DELETED {deleted} duplicate rows!")

# FINAL RESULT
print("\n=== AFTER CLEANING ===")
c.execute("SELECT id, name, quantity, category FROM products ORDER BY name")
final = c.fetchall()
print(f"Final rows: {len(final)}")
for row in final:
    print(f"ID:{row[0]} {row[1]} ({row[2]}) - {row[3]}")

conn.close()
print("\n🎉 DUPLICATES CLEANED! Restart app.py")

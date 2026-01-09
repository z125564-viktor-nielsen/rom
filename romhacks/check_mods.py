import sqlite3

conn = sqlite3.connect('requests.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# List all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [r[0] for r in cur.fetchall()])

# Check ports table structure
cur.execute("PRAGMA table_info(ports)")
print("\nPorts columns:")
for col in cur.fetchall():
    print(f"  {col['name']}: {col['type']}")

# Check if mod_links exists in ports
cur.execute("SELECT id, title, mod_links, mod_instructions FROM ports")
rows = cur.fetchall()
print(f"\nPorts ({len(rows)} found):")
for r in rows:
    mod_inst = r['mod_instructions'][:50] if r['mod_instructions'] else None
    print(f"  {r['title']}: mod_links={r['mod_links']}, mod_instructions={mod_inst}")

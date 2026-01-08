import sqlite3
import json

db_path = 'c:\\Users\\vikto\\Documents\\romhacks\\rom\\romhacks\\requests.db'

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT * FROM games WHERE id = 'pokemon_unbound'")
row = cursor.fetchone()

if row:
    print(f"Title: {row['title']}")
    print(f"Image URL: {row['image_url']}")
    print(f"Screenshots: {row['screenshots']}")
else:
    print("Game not found in DB")

conn.close()

#!/usr/bin/env python3
"""Quick database schema verification"""
import sqlite3
from database import init_db

# Initialize database
init_db()

# Check tables exist
conn = sqlite3.connect('requests.db')
cursor = conn.cursor()

# Get table info
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]
print('✓ Tables in database:')
for table in tables:
    print(f'  - {table}')

# Check critical columns
cursor.execute('PRAGMA table_info(games)')
game_cols = {row[1] for row in cursor.fetchall()}
print(f'\n✓ Games table has game_series: {"game_series" in game_cols}')

cursor.execute('PRAGMA table_info(ports)')
port_cols = {row[1] for row in cursor.fetchall()}
print(f'✓ Ports table has game_series: {"game_series" in port_cols}')

cursor.execute('PRAGMA table_info(monthly_downloads)')
md_cols = {row[1] for row in cursor.fetchall()}
print(f'✓ Monthly downloads table exists: {len(md_cols) > 0}')

cursor.execute('PRAGMA table_info(monthly_popular_history)')
mh_cols = {row[1] for row in cursor.fetchall()}
print(f'✓ Monthly popular history table exists: {len(mh_cols) > 0}')

conn.close()

print('\n✓ Database schema verification complete!')

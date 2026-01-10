#!/usr/bin/env python3
"""
Database Migration Script
This script applies pending schema migrations to the database.
Run this before deploying new code changes.

Usage:
    python migrate_database.py --backup     # Create backup before migrating
    python migrate_database.py              # Apply migrations
    python migrate_database.py --verify     # Verify migrations
"""

import sqlite3
import json
import os
import sys
import argparse
import shutil
from datetime import datetime
from database import DB_PATH, FILTER_CONFIGS, get_filter_value

def backup_database():
    """Create a backup of the current database"""
    if not os.path.exists(DB_PATH):
        print("⚠ Database does not exist yet, skipping backup")
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{DB_PATH}.backup_{timestamp}"
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"✓ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"✗ Failed to backup database: {e}")
        return None

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_column_exists(cursor, table, column):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    return column in columns

def migrate_add_game_series_column():
    """Add game_series column to games and ports tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    migrations_applied = []
    
    try:
        # Add game_series to games table
        if not check_column_exists(cursor, 'games', 'game_series'):
            cursor.execute("ALTER TABLE games ADD COLUMN game_series TEXT")
            migrations_applied.append("Added game_series column to games table")
            print("  ✓ Added game_series column to games table")
        else:
            print("  - game_series column already exists in games table")
        
        # Add game_series to ports table
        if not check_column_exists(cursor, 'ports', 'game_series'):
            cursor.execute("ALTER TABLE ports ADD COLUMN game_series TEXT")
            migrations_applied.append("Added game_series column to ports table")
            print("  ✓ Added game_series column to ports table")
        else:
            print("  - game_series column already exists in ports table")
        
        conn.commit()
        return migrations_applied
    
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error: {e}")
        return []
    finally:
        conn.close()

def migrate_add_monthly_downloads_table():
    """Add monthly_downloads table for tracking downloads per month"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    migrations_applied = []
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_downloads'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE monthly_downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    ip_hash TEXT NOT NULL,
                    year_month TEXT NOT NULL,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(game_id, ip_hash, year_month)
                )
            ''')
            migrations_applied.append("Created monthly_downloads table")
            print("  ✓ Created monthly_downloads table")
        else:
            print("  - monthly_downloads table already exists")
        
        # Create index
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_monthly_downloads_year_month'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE INDEX idx_monthly_downloads_year_month
                ON monthly_downloads(year_month)
            ''')
            migrations_applied.append("Created index on monthly_downloads")
            print("  ✓ Created index idx_monthly_downloads_year_month")
        else:
            print("  - Index idx_monthly_downloads_year_month already exists")
        
        conn.commit()
        return migrations_applied
    
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error: {e}")
        return []
    finally:
        conn.close()

def migrate_add_monthly_popular_history_table():
    """Add monthly_popular_history table for storing past months' top games"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    migrations_applied = []
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_popular_history'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE monthly_popular_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year_month TEXT NOT NULL,
                    game_id TEXT NOT NULL,
                    game_type TEXT NOT NULL,
                    download_count INTEGER NOT NULL,
                    rank INTEGER NOT NULL,
                    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(year_month, game_id, game_type)
                )
            ''')
            migrations_applied.append("Created monthly_popular_history table")
            print("  ✓ Created monthly_popular_history table")
        else:
            print("  - monthly_popular_history table already exists")
        
        conn.commit()
        return migrations_applied
    
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error: {e}")
        return []
    finally:
        conn.close()

def migrate_add_reviews_columns():
    """Add missing columns to reviews table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    migrations_applied = []
    
    try:
        # Columns to add: name, type, default value
        columns_to_add = [
            ('ra_game_id', 'INTEGER'),
            ('achievements_earned', 'INTEGER DEFAULT 0'),
            ('achievements_total', 'INTEGER DEFAULT 0'),
            ('completion_percentage', 'REAL DEFAULT 0'),
        ]
        
        for col_name, col_def in columns_to_add:
            if not check_column_exists(cursor, 'reviews', col_name):
                cursor.execute(f"ALTER TABLE reviews ADD COLUMN {col_name} {col_def}")
                migrations_applied.append(f"Added {col_name} column to reviews table")
                print(f"  ✓ Added {col_name} column to reviews table")
            else:
                print(f"  - {col_name} column already exists in reviews table")
        
        conn.commit()
        return migrations_applied
    
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error: {e}")
        return []
    finally:
        conn.close()

def populate_game_series_auto_detect():
    """Auto-populate game_series for existing games and ports where not set"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    migrations_applied = []
    
    try:
        # Populate games table
        cursor.execute("SELECT id, base_game, title FROM games WHERE game_series IS NULL OR game_series = ''")
        games_to_update = cursor.fetchall()
        
        if games_to_update:
            for game_row in games_to_update:
                game_dict = dict(game_row)
                series = get_filter_value(game_dict, 'game_series')
                if series:
                    cursor.execute("UPDATE games SET game_series = ? WHERE id = ?", (series, game_dict['id']))
            
            migrations_applied.append(f"Auto-populated game_series for {len(games_to_update)} games")
            print(f"  ✓ Auto-populated game_series for {len(games_to_update)} games")
        else:
            print("  - All games already have game_series populated")
        
        # Populate ports table
        cursor.execute("SELECT id, base_game, title FROM ports WHERE game_series IS NULL OR game_series = ''")
        ports_to_update = cursor.fetchall()
        
        if ports_to_update:
            for port_row in ports_to_update:
                port_dict = dict(port_row)
                series = get_filter_value(port_dict, 'game_series')
                if series:
                    cursor.execute("UPDATE ports SET game_series = ? WHERE id = ?", (series, port_dict['id']))
            
            migrations_applied.append(f"Auto-populated game_series for {len(ports_to_update)} ports")
            print(f"  ✓ Auto-populated game_series for {len(ports_to_update)} ports")
        else:
            print("  - All ports already have game_series populated")
        
        conn.commit()
        return migrations_applied
    
    except Exception as e:
        conn.rollback()
        print(f"  ✗ Error: {e}")
        return []
    finally:
        conn.close()

def verify_schema():
    """Verify that all expected schema changes are in place"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    issues = []
    
    # Check games table columns
    expected_game_cols = ['game_series']
    cursor.execute("PRAGMA table_info(games)")
    game_cols = {row[1] for row in cursor.fetchall()}
    
    for col in expected_game_cols:
        if col not in game_cols:
            issues.append(f"Missing column '{col}' in games table")
    
    # Check ports table columns
    expected_port_cols = ['game_series']
    cursor.execute("PRAGMA table_info(ports)")
    port_cols = {row[1] for row in cursor.fetchall()}
    
    for col in expected_port_cols:
        if col not in port_cols:
            issues.append(f"Missing column '{col}' in ports table")

    # Check reviews table columns
    expected_review_cols = ['ra_game_id', 'achievements_earned', 'achievements_total', 'completion_percentage']
    cursor.execute("PRAGMA table_info(reviews)")
    review_cols = {row[1] for row in cursor.fetchall()}
    
    for col in expected_review_cols:
        if col not in review_cols:
            issues.append(f"Missing column '{col}' in reviews table")
    
    # Check tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_downloads'")
    if not cursor.fetchone():
        issues.append("Missing table 'monthly_downloads'")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monthly_popular_history'")
    if not cursor.fetchone():
        issues.append("Missing table 'monthly_popular_history'")
    
    conn.close()
    
    return issues

def main():
    parser = argparse.ArgumentParser(description='Database migration script')
    parser.add_argument('--backup', action='store_true', help='Create backup before migrating')
    parser.add_argument('--verify', action='store_true', help='Only verify schema without applying migrations')
    parser.add_argument('--no-populate', action='store_true', help='Skip auto-population of game_series')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("DATABASE MIGRATION SCRIPT")
    print("=" * 60)
    
    if args.verify:
        print("\nVerifying schema...")
        issues = verify_schema()
        if issues:
            print("✗ Schema issues found:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print("✓ All schema changes are in place!")
            sys.exit(0)
    
    # Create backup if requested
    if args.backup:
        print("\nCreating backup...")
        backup_database()
    
    print("\nApplying migrations...")
    all_migrations = []
    
    print("\n1. Adding game_series column...")
    all_migrations.extend(migrate_add_game_series_column())
    
    print("\n2. Adding monthly_downloads table...")
    all_migrations.extend(migrate_add_monthly_downloads_table())
    
    print("\n3. Adding monthly_popular_history table...")
    all_migrations.extend(migrate_add_monthly_popular_history_table())

    print("\n4. Adding reviews columns...")
    all_migrations.extend(migrate_add_reviews_columns())
    
    if not args.no_populate:
        print("\n5. Auto-populating game_series...")
        all_migrations.extend(populate_game_series_auto_detect())
    
    # Verify migrations
    print("\n" + "=" * 60)
    print("Verifying schema...")
    issues = verify_schema()
    
    if issues:
        print("✗ Schema verification failed:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("✓ All schema changes verified successfully!")
    
    print("\n" + "=" * 60)
    print(f"✓ Migration complete! {len(all_migrations)} changes applied:")
    for migration in all_migrations:
        print(f"  - {migration}")
    print("=" * 60)

if __name__ == '__main__':
    main()

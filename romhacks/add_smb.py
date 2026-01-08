#!/usr/bin/env python3
"""Add Super Mario Bros. Remastered port entry directly"""
import json
import sqlite3
import sys
import os

# The database path
DB_PATH = '/var/www/romhacks/rom/romhacks/requests.db'
JSON_PATH = '/var/www/romhacks/rom/romhacks/super-mario-bros-remastered.json'

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

try:
    # Read the JSON file
    with open(JSON_PATH, 'r') as f:
        port_data = json.load(f)

    # Extract platform instructions
    platform_instructions = port_data.pop('platform_instructions', {})

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert the port
    port_id = port_data.get('id', port_data.get('title', 'port').lower().replace(' ', '_').replace("'", ''))

    cursor.execute('''
        INSERT OR REPLACE INTO ports (
            id, title, console, version, release_date, author,
            description, features, image_url, screenshots, download_link,
            base_game, original_platform, popular, instruction, instruction_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        port_id,
        port_data.get('title'),
        port_data.get('console', 'PC'),
        port_data.get('version'),
        port_data.get('release_date'),
        port_data.get('author'),
        port_data.get('description'),
        json.dumps(port_data.get('features', [])),
        port_data.get('image_url'),
        json.dumps(port_data.get('screenshots', [])),
        port_data.get('download_link'),
        port_data.get('base_game'),
        port_data.get('original_platform'),
        1 if port_data.get('popular', False) else 0,
        1 if port_data.get('instruction', False) else 0,
        port_data.get('instruction_text'),
    ))

    print(f"✓ Added {port_data['title']} to ports database")

    # Add platform instructions
    for platform, instructions in platform_instructions.items():
        platform_lower = platform.lower().replace(' ', '_')
        col_name = f'instructions_{platform_lower}'
        
        cursor.execute(f'UPDATE ports SET {col_name} = ? WHERE id = ?', 
                       (instructions, port_id))
        print(f"✓ Added {platform.upper()} platform instructions")

    conn.commit()
    conn.close()

    print(f"\n✅ Successfully created port entry: {port_data['title']}")
    print(f"   ID: {port_id}")
    print(f"   Platforms: {port_data.get('console')}")
    screenshots = port_data.get('screenshots', [])
    print(f"   Screenshots: {len(screenshots)}")
    features = port_data.get('features', [])
    print(f"   Features: {len(features)}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

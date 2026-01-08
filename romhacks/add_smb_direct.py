#!/usr/bin/env python3
"""
Direct port entry insertion script
Run this on the remote server: python3 add_smb_direct.py
"""
import json
import sqlite3
import sys

def main():
    DB_PATH = '/var/www/romhacks/rom/romhacks/requests.db'
    JSON_PATH = '/var/www/romhacks/rom/romhacks/super-mario-bros-remastered.json'
    
    try:
        # Read the JSON file
        with open(JSON_PATH, 'r') as f:
            port_data = json.load(f)

        # Extract platform instructions
        platform_instructions = port_data.pop('platform_instructions', {})

        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get port ID
        port_id = port_data.get('id')
        
        # First, check if ports table has the instruction columns
        cursor.execute("PRAGMA table_info(ports)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        # Add platform instruction columns if they don't exist
        for platform in ['pc', 'android', 'linux', 'web', 'ios', 'mac', 'switch', 'ps4', 'xbox']:
            col_name = f'instructions_{platform}'
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE ports ADD COLUMN {col_name} TEXT")
                    print(f"  Added column {col_name}")
                except:
                    pass

        # Insert or update the port
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
            port_data.get('instruction_text', ''),
        ))

        print(f"✓ Added {port_data['title']} to ports database (ID: {port_id})")

        # Add platform instructions
        for platform, instructions in platform_instructions.items():
            platform_lower = platform.lower().replace(' ', '_')
            col_name = f'instructions_{platform_lower}'
            
            try:
                cursor.execute(f'UPDATE ports SET {col_name} = ? WHERE id = ?', 
                               (instructions, port_id))
                print(f"✓ Added {platform} platform instructions")
            except Exception as e:
                print(f"⚠ Warning adding {platform} instructions: {e}")

        conn.commit()
        
        # Verify the insertion
        cursor.execute('SELECT * FROM ports WHERE id = ?', (port_id,))
        result = cursor.fetchone()
        
        conn.close()

        if result:
            print(f"\n✅ Successfully created port entry!")
            print(f"   Title: {result['title']}")
            print(f"   ID: {result['id']}")
            print(f"   Platforms: {result['console']}")
            print(f"   Author: {result['author']}")
            print(f"   Features: {len(json.loads(result['features']) if result['features'] else [])} items")
            return 0
        else:
            print("❌ Error: Entry was not created properly")
            return 1
            
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return 1
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

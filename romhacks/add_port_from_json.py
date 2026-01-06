#!/usr/bin/env python3
"""
Port Entry Creator from JSON
Load port data from a JSON file and create/update port entries
"""

import json
import sys
from database import insert_port, set_platform_instructions

def add_port_from_json(json_file):
    """Add a port entry from a JSON file"""
    
    try:
        with open(json_file, 'r') as f:
            port_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File '{json_file}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in '{json_file}'")
        sys.exit(1)
    
    # Validate required fields
    required_fields = ['id', 'title', 'console', 'author', 'description', 'download_link', 'base_game', 'image_url']
    missing_fields = [field for field in required_fields if not port_data.get(field)]
    
    if missing_fields:
        print(f"❌ Error: Missing required fields: {', '.join(missing_fields)}")
        sys.exit(1)
    
    # Extract platform instructions if present
    platform_instructions = port_data.pop('platform_instructions', {})
    
    # Insert the port
    insert_port(port_data)
    print(f"✓ Added {port_data['title']} to ports database")
    
    # Add platform instructions
    for platform, instructions in platform_instructions.items():
        platform_lower = platform.lower().replace(' ', '_')
        set_platform_instructions(port_data['id'], platform_lower, instructions, is_port=True)
        print(f"✓ Added {platform.upper()} platform instructions")
    
    print(f"\n✅ Successfully created port entry: {port_data['title']}")
    print(f"   ID: {port_data['id']}")
    print(f"   Platforms: {port_data['console']}")
    screenshots = port_data.get('screenshots', [])
    print(f"   Screenshots: {len(screenshots)}")
    features = port_data.get('features', [])
    print(f"   Features: {len(features)}")
    print()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python add_port_from_json.py <json_file>")
        print("\nExample JSON file structure:")
        print(json.dumps({
            "id": "sm64_coop_dx",
            "title": "SM64 Coop DX",
            "console": "Windows, Android",
            "version": "1.0+",
            "release_date": "2023-01-01",
            "author": "Coop Deluxe",
            "description": "Description here...",
            "features": ["Feature 1", "Feature 2"],
            "download_link": "https://github.com/...",
            "base_game": "Super Mario 64",
            "original_platform": "Nintendo 64",
            "image_url": "https://...",
            "screenshots": ["https://...", "https://..."],
            "popular": True,
            "platform_instructions": {
                "Windows": "Instructions for Windows...",
                "ANDROID": "Instructions for Android..."
            }
        }, indent=2))
        sys.exit(1)
    
    add_port_from_json(sys.argv[1])

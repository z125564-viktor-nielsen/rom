#!/usr/bin/env python3
"""
Universal Port Entry Creator
Input port data and create/update port entries with full information
"""

import json
import sys
from database import insert_port, set_platform_instructions

def add_port_entry():
    """Interactive script to add a port entry with all details"""
    
    print("\n" + "="*60)
    print("PORT ENTRY CREATOR - Add a new decompiled port")
    print("="*60 + "\n")
    
    # Basic Information
    print("--- BASIC INFORMATION ---")
    port_id = input("Port ID (e.g., sm64_coop_dx): ").strip()
    title = input("Title (e.g., SM64 Coop DX): ").strip()
    console = input("Platforms (e.g., PC, Android or PC, Android, Linux): ").strip()
    author = input("Author/Creator: ").strip()
    version = input("Version (e.g., 1.0+): ").strip()
    release_date = input("Release Date (YYYY-MM-DD): ").strip()
    base_game = input("Base Game (e.g., Super Mario 64): ").strip()
    original_platform = input("Original Platform (e.g., Nintendo 64): ").strip()
    
    # Description
    print("\n--- DESCRIPTION & DETAILS ---")
    print("Description (press Enter twice when done):")
    description_lines = []
    while True:
        line = input()
        if not line:
            if description_lines and not description_lines[-1]:
                break
            description_lines.append(line)
        else:
            description_lines.append(line)
    description = '\n'.join(description_lines).strip()
    
    # Features
    print("\nFeatures (comma-separated, e.g., Online Play, Widescreen, Mods):")
    features_input = input().strip()
    features = [f.strip() for f in features_input.split(',') if f.strip()]
    
    # Links
    print("\n--- LINKS ---")
    download_link = input("Download Link (e.g., GitHub URL): ").strip()
    project_link = input("Project/Website Link (optional): ").strip()
    
    # Images
    print("\n--- IMAGES ---")
    image_url = input("Cover Image URL: ").strip()
    
    print("Screenshot URLs (one per line, press Enter twice when done):")
    screenshots = []
    while True:
        url = input().strip()
        if not url:
            if screenshots or not input.count('\n'):
                break
            continue
        screenshots.append(url)
    
    # Online Play
    online_play = input("\nHas Online/Multiplayer? (y/n): ").strip().lower() == 'y'
    
    # Popular
    popular = input("Mark as Popular? (y/n): ").strip().lower() == 'y'
    
    # Create port data
    port_data = {
        'id': port_id,
        'title': title,
        'console': console,
        'version': version,
        'release_date': release_date,
        'author': author,
        'description': description,
        'features': features,
        'image_url': image_url,
        'screenshots': screenshots,
        'download_link': download_link,
        'base_game': base_game,
        'original_platform': original_platform,
        'popular': popular,
        'online_play': online_play
    }
    
    # Insert the port
    insert_port(port_data)
    print(f"\n✓ Added {title} to ports database")
    
    # Platform Instructions
    print("\n--- PLATFORM INSTRUCTIONS ---")
    platforms = [p.strip().upper() for p in console.split(',')]
    
    for platform in platforms:
        platform_lower = platform.lower().replace(' ', '_')
        print(f"\nInstructions for {platform} (press Enter twice when done):")
        instruction_lines = []
        while True:
            line = input()
            if not line:
                if instruction_lines and not instruction_lines[-1]:
                    break
                instruction_lines.append(line)
            else:
                instruction_lines.append(line)
        
        instructions = '\n'.join(instruction_lines).strip()
        if instructions:
            set_platform_instructions(port_id, platform_lower, instructions, is_port=True)
            print(f"✓ Added {platform} platform instructions")
    
    print(f"\n✅ Successfully created port entry: {title}")
    print(f"   ID: {port_id}")
    print(f"   Platforms: {console}")
    print(f"   Screenshots: {len(screenshots)}")
    print(f"   Features: {len(features)}")
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    try:
        add_port_entry()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

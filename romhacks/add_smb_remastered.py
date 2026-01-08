#!/usr/bin/env python3
import json
import sys
sys.path.insert(0, '/var/www/romhacks/rom/romhacks')

from database import insert_port, set_platform_instructions

# Load the JSON file
with open('/var/www/romhacks/rom/romhacks/super-mario-bros-remastered.json', 'r') as f:
    port_data = json.load(f)

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

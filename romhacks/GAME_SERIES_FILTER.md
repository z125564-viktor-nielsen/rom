# Game Series Filter - Quick Start Guide

## What Was Added

A new **Game Series** filter has been added to both ROM Hacks and Ports pages. This allows users to filter games by franchise (Pokemon, Mario, Zelda, Sonic, etc.).

## Features

### Auto-Detection
The system automatically detects game series from the `base_game` or `title` fields. For example:
- "Pokemon FireRed" → Detected as "Pokemon"
- "Super Mario 64" → Detected as "Mario"
- "Sonic the Hedgehog" → Detected as "Sonic"

### Supported Series (Auto-Detected)
- Pokemon
- Mario
- Zelda
- Metroid
- Kirby
- Sonic
- Mega Man
- Final Fantasy
- Dragon Quest
- Fire Emblem
- Castlevania
- Contra
- Street Fighter
- Mortal Kombat

### Dynamic Filtering
The series dropdown updates based on:
- Currently selected console
- Currently selected original platform (for ports)
- Available games in the filtered results

## How Users Will Use It

1. Navigate to ROM Hacks or Ports page
2. Use the new **Series** dropdown in the filter section
3. Select a game series (e.g., "Pokemon")
4. Only games from that series will be displayed
5. Can combine with other filters (console, game, etc.)

## Extensible System

The new system makes it easy to add more filters in the future. See `FILTER_SYSTEM.md` for complete documentation on adding new filters like:
- Genre (RPG, Platformer, etc.)
- Difficulty level
- Quality ratings
- And more!

## Technical Changes

### Files Modified
1. `database.py` - Added filter configuration system and game_series column
2. `romhacks.html` - Added series filter dropdown
3. `ports.html` - Added series filter dropdown
4. `app.js` - Added JavaScript filtering logic for series

### Database Changes
- New column `game_series` added to both `games` and `ports` tables
- Automatic migration - no manual SQL needed
- Auto-detection fills in values for existing games

## Admin Usage

When adding or editing games/ports through the admin interface:
1. You can manually set the `game_series` field
2. If left empty, the system will auto-detect it
3. Manual values override auto-detection

## Example Workflow

**User wants to find all Pokemon ROM hacks for GBA:**
1. Select "GBA" from Console dropdown
2. Select "Pokemon" from Series dropdown
3. Results show only Pokemon GBA hacks

**User wants to find all Mario ports:**
1. Go to Ports page
2. Select "Mario" from Series dropdown
3. Results show all Mario ports across all platforms

## Future Enhancements

The flexible filter system allows for easy addition of:
- More game series patterns
- Genre filters
- Difficulty ratings
- Quality/completion status
- And any other categorization you can think of!

See `FILTER_SYSTEM.md` for detailed instructions on adding new filters.

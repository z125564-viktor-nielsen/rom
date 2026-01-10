# Console Color Fix

## Problem
GBA games were showing different colors on the website - Fire Emblem appeared grey and Pokemon appeared purple, even though they're both on the same GBA platform.

## Root Cause
The console color lookup was case-sensitive and didn't handle variations in console naming. The database might contain:
- `"GBA"` (uppercase)
- `"Game Boy Advance"` (full name)
- `"gba"` (lowercase)

But the `CONSOLE_STYLES` dictionary only had lowercase abbreviated keys like `'gba'`. When the template tried to look up a console name that didn't match exactly (e.g., `"GBA"` or `"Game Boy Advance"`), it would fall back to the default grey color.

## Solution
Added a normalization function `normalize_console_name()` that:
1. Converts console names to lowercase
2. Removes spaces and hyphens
3. Maps full names to standard abbreviations (e.g., "Game Boy Advance" → "gba")
4. Returns the normalized key for style lookup

## Files Changed
1. **app.py**: Added `normalize_console_name()` function and `normalize_console` template filter
2. **templates/base_game_hub.html**: Applied filter to both console badge locations
3. **templates/romhacks.html**: Applied filter to console badge
4. **templates/index.html**: Applied filter to console badge
5. **templates/game.html**: Applied filter to console badge

## Usage
In templates, use the filter like this:
```jinja2
{{ styles.get(game.console | normalize_console, styles['default']) }}
```

## Testing
All variations now correctly map to their respective colors:
- "GBA", "Game Boy Advance", "gba" → purple
- "GB", "Game Boy" → emerald
- "SNES", "Super Nintendo" → indigo
- etc.

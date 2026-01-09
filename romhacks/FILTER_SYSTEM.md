# Filter Configuration System Documentation

## Overview
The ROM Hacks website now features a flexible, extensible filter/tagging system that makes it easy to add new filters without modifying multiple parts of the codebase. This document explains how the system works and how to add new filters.

## Current Filters
- **Game Series**: Automatically categorizes games by franchise (Pokemon, Mario, Zelda, etc.)
  - Supports auto-detection from base_game or title fields
  - Displayed in both ROM hacks and ports pages
  - Dynamically updates dropdown based on current filter selections

## System Architecture

### 1. Database Layer (`database.py`)

#### Filter Configuration Dictionary
All filters are defined in the `FILTER_CONFIGS` dictionary at the top of `database.py`:

```python
FILTER_CONFIGS = {
    'game_series': {
        'description': 'Game series/franchise (e.g., Pokemon, Mario, Zelda)',
        'type': 'TEXT',
        'auto_detect': lambda game: _auto_detect_series(game.get('base_game', ''), game.get('title', ''))
    },
    # Add more filters here...
}
```

#### Key Components:
- **`_auto_detect_series(base_game, title)`**: Auto-detects game series from base game or title
- **`get_filter_value(record, filter_name)`**: Retrieves filter value with auto-detection fallback
- **`init_db()`**: Automatically creates database columns for all configured filters
- **`get_games()` / `get_ports()`**: Applies filter values (with auto-detection) to all returned records
- **`insert_game()` / `insert_port()`**: Saves filter values during game/port creation
- **`update_game()` / `update_port()`**: Allows updating filter values via admin interface

### 2. Template Layer (`romhacks.html`, `ports.html`)

Each filter appears as:
1. A dropdown in the filters grid
2. A `data-*` attribute on each game card for JavaScript filtering

Example for game series:
```html
<!-- Filter dropdown -->
<select id="series-filter" onchange="filterBySeries(this.value)">
    <option value="">All Series</option>
</select>

<!-- Game card with data attribute -->
<div class="hack-card" data-game-series="{{ game.game_series or '' }}">
```

### 3. JavaScript Layer (`app.js`)

#### Filter State Variables
```javascript
let activeConsole = 'all';
let activeOriginalPlatform = 'all';
let activeGameFilter = '';
let activeSeriesFilter = '';  // New filter variable
let netplayFilter = false;
```

#### Key Functions:
- **`updateSeriesDropdown()`**: Populates series dropdown with unique values from visible cards
- **`filterBySeries(series)`**: Applies series filter and updates pagination
- **`updatePagination()`**: Main filter logic that checks all active filters including series
- **`filterHacks()`**: Resets dependent filters when console changes

## How to Add a New Filter

### Step 1: Add to FILTER_CONFIGS (database.py)

```python
FILTER_CONFIGS = {
    'game_series': { ... },
    'genre': {
        'description': 'Game genre (e.g., RPG, Platformer, Action)',
        'type': 'TEXT',
        'auto_detect': None  # Or provide a function for auto-detection
    },
}
```

### Step 2: Add Filter Variable (app.js)

```javascript
let activeGenreFilter = '';
```

### Step 3: Add Filter Dropdown (templates)

In `romhacks.html` and/or `ports.html`:

```html
<!-- Genre Filter -->
<div class="space-y-2">
    <span class="text-[10px] uppercase font-semibold text-gray-500 tracking-wider">Genre</span>
    <div class="relative">
        <select id="genre-filter" onchange="filterByGenre(this.value)" class="w-full bg-gray-800/50 text-gray-100 border border-gray-700/50 hover:border-gray-600 focus:border-blue-500 pl-3 pr-8 py-2 text-xs rounded-lg focus:outline-none font-mono appearance-none transition-all cursor-pointer">
            <option value="">All Genres</option>
        </select>
        <span class="material-symbols-outlined absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 text-sm pointer-events-none">unfold_more</span>
    </div>
</div>
```

### Step 4: Add Data Attribute to Cards (templates)

```html
<div class="hack-card" ... data-genre="{{ game.genre or '' }}">
```

### Step 5: Add JavaScript Functions (app.js)

```javascript
function updateGenreDropdown() {
    const genreFilter = document.getElementById('genre-filter');
    if (!genreFilter) return;

    const genres = new Set();
    allCards.forEach(card => {
        const cardGenre = (card.dataset.genre || '').trim();
        // Add any other filter checks if needed
        if (cardGenre) {
            genres.add(cardGenre);
        }
    });

    const sortedGenres = Array.from(genres).sort();
    const currentValue = genreFilter.value;

    genreFilter.innerHTML = '<option value="">All Genres</option>';
    sortedGenres.forEach(genre => {
        const option = document.createElement('option');
        option.value = genre.toLowerCase();
        option.textContent = genre;
        genreFilter.appendChild(option);
    });

    genreFilter.value = currentValue;
}

function filterByGenre(genre) {
    activeGenreFilter = genre.toLowerCase();
    currentPage = 1;
    updateGenreDropdown();
    updatePagination();
}
```

### Step 6: Update Filter Logic (app.js)

In `updatePagination()` and `nextPage()`, add genre check:

```javascript
const cardGenre = (card.dataset.genre || '').toLowerCase();
// ...
let matchGenre = (activeGenreFilter === '' || cardGenre === activeGenreFilter);
// ...
return matchConsole && matchNetplay && matchGame && matchSeries && matchGenre && ...;
```

### Step 7: Initialize Dropdown (app.js)

In `DOMContentLoaded`:

```javascript
if (allCards.length > 0) {
    updateGameDropdown();
    updateSeriesDropdown();
    updateGenreDropdown();  // Add this
    updatePagination();
}
```

### Step 8: Reset Filter When Needed (app.js)

In `filterHacks()`:

```javascript
activeGenreFilter = ''; // Reset genre filter when console changes
// ...
const genreFilter = document.getElementById('genre-filter');
if (genreFilter) {
    genreFilter.value = '';
}
```

## Auto-Detection Feature

The system supports automatic value detection. For example, game series is auto-detected from base_game or title:

```python
def _auto_detect_series(base_game, title):
    text = (base_game or title).lower()
    
    series_patterns = {
        'Pokemon': ['pokemon', 'pokémon'],
        'Mario': ['mario', 'smb', 'super mario'],
        # ... more patterns
    }
    
    for series, patterns in series_patterns.items():
        for pattern in patterns:
            if pattern in text:
                return series
    
    return None
```

To use auto-detection for your filter:
1. Define an auto-detect function
2. Add it to the filter config: `'auto_detect': lambda game: your_function(game)`
3. The function will run whenever a game_series value is missing

## Database Migration

The system automatically handles database migrations:
- When `init_db()` runs, it checks for each filter in `FILTER_CONFIGS`
- If a column doesn't exist, it's automatically added to both `games` and `ports` tables
- No manual SQL migration needed!

## Benefits of This System

1. **Centralized Configuration**: All filter definitions in one place
2. **Automatic Database Migration**: Columns added automatically
3. **Auto-Detection**: Intelligently fill in missing values
4. **Type Safety**: Each filter defines its database type
5. **Easy to Extend**: Add new filters by following the 8-step process
6. **Consistent Behavior**: All filters work the same way across the site

## Examples of Future Filters

Here are some ideas for filters you could easily add:

```python
FILTER_CONFIGS = {
    'game_series': { ... },
    
    'genre': {
        'description': 'Game genre',
        'type': 'TEXT',
        'auto_detect': None
    },
    
    'difficulty': {
        'description': 'Difficulty level',
        'type': 'TEXT',
        'auto_detect': None
    },
    
    'region': {
        'description': 'Game region (US, EU, JP, etc.)',
        'type': 'TEXT',
        'auto_detect': lambda game: game.get('base_region', '').upper()
    },
    
    'quality_rating': {
        'description': 'Quality/completeness rating',
        'type': 'INTEGER',
        'auto_detect': None
    },
}
```

## Testing Your New Filter

1. Restart your Flask application
2. The database migration runs automatically
3. Add or edit a game/port with your new filter value
4. Verify the dropdown populates correctly
5. Test filtering by selecting different values
6. Ensure it combines correctly with other filters

## Troubleshooting

**Filter not appearing?**
- Check that the column was added to the database (inspect with SQLite tool)
- Verify the dropdown element has the correct ID
- Check JavaScript console for errors

**Auto-detection not working?**
- Ensure your auto_detect function returns the correct type
- Add debug logging to see what values are being generated
- Test the function with sample data

**Filtering not working?**
- Verify the data attribute is present on cards (inspect HTML)
- Check that the filter variable is being set correctly
- Ensure updatePagination() includes your filter in the logic

## Maintenance Notes

When the database structure changes or you need to repopulate filter values:
1. The auto-detection will fill in missing values automatically
2. You can manually update values via the admin interface
3. The system is backwards-compatible - existing games without filter values will still display

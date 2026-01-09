# Database Deployment Guide

## Summary of Changes

Your local database has been updated with the following schema changes:

### 1. **Game Series Filter System** (New)
- Added `FILTER_CONFIGS` system for managing reusable filters/tags
- Implements `game_series` filter with automatic detection
- Auto-detects series from game title (Pokemon, Mario, Zelda, etc.)

### 2. **game_series Column** (New)
- Added to both `games` and `ports` tables
- Enables filtering and organization by game franchise
- Auto-populated for existing entries based on title/base_game

### 3. **Monthly Downloads Tracking** (New)
- New table: `monthly_downloads`
- Tracks downloads per month per game (unique by game_id, ip_hash, year_month)
- Includes index on `year_month` for fast queries
- Purpose: Monthly analytics and popularity trends

### 4. **Monthly Popular History** (New)
- New table: `monthly_popular_history`
- Stores archived rankings of top games per month
- Fields: year_month, game_id, game_type, download_count, rank
- Allows tracking historical popularity trends

---

## Deployment Steps

### Step 1: Backup Your Production Database (RECOMMENDED)
```bash
# On your server
cp requests.db requests.db.backup_$(date +%Y%m%d_%H%M%S)
```

### Step 2: Deploy the Migration Script
Copy `migrate_database.py` to your server and run:

```bash
# Option A: With backup (RECOMMENDED)
python migrate_database.py --backup

# Option B: Manual backup only
python migrate_database.py
```

### Step 3: Verify the Migration
```bash
# Verify schema is correct
python migrate_database.py --verify

# Expected output:
# ✓ All schema changes verified successfully!
```

### Step 4: Deploy New Code
Once migration succeeds, deploy the updated code:
- `database.py` (updated schema and filter system)
- `app.py` (any dependent changes)
- Other modified files from your git changes

### Step 5: Restart Application
```bash
# Restart your Flask app / service
systemctl restart romhacks
# or
supervisorctl restart romhacks
```

---

## Migration Options

### Full Migration (Recommended)
```bash
python migrate_database.py --backup
```
This will:
- Create a backup of your database
- Add all new columns and tables
- Auto-populate `game_series` for existing games/ports

### Schema Only (If Auto-Populate Causes Issues)
```bash
python migrate_database.py --backup --no-populate
```
Then manually populate game_series later:
```bash
sqlite3 requests.db "UPDATE games SET game_series = 'Pokemon' WHERE title LIKE '%pokemon%';"
```

### Verify Without Changes
```bash
python migrate_database.py --verify
```
Shows if all changes are already applied (safe to run anytime)

---

## Rollback Procedure (If Needed)

If something goes wrong:

```bash
# 1. Stop the application
systemctl stop romhacks

# 2. Restore from backup
cp requests.db.backup_YYYYMMDD_HHMMSS requests.db

# 3. Restart application
systemctl start romhacks
```

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `database.py` | Modified | Added FILTER_CONFIGS, filter functions, new table schemas |
| `app.py` | Modified | Filter system integration in game/port retrieval |
| `migrate_database.py` | New | Safe migration script with backup/verify options |

---

## Testing Checklist

After deployment, verify:

- [ ] Application starts without errors
- [ ] Games and ports load correctly
- [ ] Filters work (if UI integrated)
- [ ] Download tracking still works
- [ ] Admin dashboard functions normally
- [ ] No console errors in application logs

---

## Quick Reference

| New Column | Table | Purpose |
|-----------|-------|---------|
| `game_series` | games, ports | Filter by franchise (Pokemon, Mario, etc.) |

| New Table | Purpose |
|-----------|---------|
| `monthly_downloads` | Track downloads per month for analytics |
| `monthly_popular_history` | Archive popular games ranking per month |

---

## Support

If migration fails:
1. Check application logs: `tail -f /var/log/romhacks.log`
2. Verify database is not locked: `lsof requests.db`
3. Restore from backup and try again
4. Check that your Python version supports the syntax

---

## Version Info

- **Migration Script Version**: 1.0
- **Database Schema Version**: Updated with filter system
- **Python**: 3.8+ recommended
- **SQLite**: 3.8.0+ (for UNIQUE constraints)

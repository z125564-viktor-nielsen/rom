# Pre-Deployment Checklist

## Local Verification ✓
- [x] Database schema changes applied locally
- [x] All new tables created and verified
- [x] All new columns added and verified
- [x] Filter system working
- [x] Migration script tested and working
- [x] No syntax errors in code

## Files Ready to Push
- [x] `database.py` - Updated schema with filter system
- [x] `app.py` - Filter system integration
- [x] `migrate_database.py` - Migration script for server
- [x] `DATABASE_DEPLOYMENT.md` - Deployment instructions
- [x] `MIGRATION_SUMMARY.md` - Summary of changes
- [x] `verify_schema.py` - Quick verification tool

## Before Pushing to Server

### Prerequisites Check
- [ ] Have SSH access to server
- [ ] Have database backup procedure in place
- [ ] Have maintenance window scheduled (if needed)
- [ ] Notified team about upcoming deployment

### Backup & Safety
- [ ] Created local backup of requests.db
- [ ] Verified backup can be restored
- [ ] Have rollback procedure documented

## Server Deployment Steps

### Step 1: Pull Code Changes
```bash
cd /path/to/romhacks
git pull origin main  # or your branch
```

### Step 2: Backup Database
```bash
cp requests.db requests.db.backup_$(date +%Y%m%d_%H%M%S)
```

### Step 3: Run Migration
```bash
python migrate_database.py --backup
# Or verify first if you want to be extra careful:
python migrate_database.py --verify
```

### Step 4: Verify Schema
```bash
python migrate_database.py --verify
# Expected: ✓ All schema changes verified successfully!
```

### Step 5: Restart Service
```bash
systemctl stop romhacks
systemctl start romhacks
# Or:
systemctl restart romhacks
```

### Step 6: Health Check
```bash
# Check service is running
systemctl status romhacks

# Check logs for errors
journalctl -u romhacks -n 50

# Test application
curl http://localhost:5000/
# or
curl https://yourdomain.com/
```

## Post-Deployment Validation

### Application Tests
- [ ] Homepage loads without errors
- [ ] Games list loads and displays
- [ ] Ports list loads and displays
- [ ] Individual game page works
- [ ] Download tracking works
- [ ] Filters display (if UI integrated)
- [ ] Admin dashboard functions
- [ ] Submissions still work

### Database Tests
```bash
# Test game_series field
sqlite3 requests.db "SELECT COUNT(*) FROM games WHERE game_series IS NOT NULL;"

# Test monthly_downloads table
sqlite3 requests.db "SELECT COUNT(*) FROM monthly_downloads;"

# Test monthly_popular_history table
sqlite3 requests.db "SELECT COUNT(*) FROM monthly_popular_history;"
```

### Logs Check
```bash
# Watch logs during first operations
tail -f /var/log/romhacks.log

# Check for errors
grep -i "error\|failed\|exception" /var/log/romhacks.log | tail -20
```

## If Something Goes Wrong

### Rollback Steps
1. Stop the application:
   ```bash
   systemctl stop romhacks
   ```

2. Restore backup:
   ```bash
   cp requests.db requests.db.broken_$(date +%Y%m%d_%H%M%S)
   cp requests.db.backup_YYYYMMDD_HHMMSS requests.db
   ```

3. Revert code changes:
   ```bash
   git revert HEAD  # or checkout previous version
   ```

4. Restart:
   ```bash
   systemctl start romhacks
   ```

5. Alert team and check logs

## Migration Troubleshooting

### Database Locked Error
```bash
# Check what process has the database
lsof requests.db

# Kill process if needed (carefully!)
kill -9 <PID>
```

### Permission Denied Error
```bash
# Check file ownership and permissions
ls -l requests.db

# Fix if needed:
chown romhacks:romhacks requests.db
chmod 664 requests.db
```

### Migration Script Not Found
- Ensure `migrate_database.py` is in the same directory as `database.py`
- Check it has execute permissions: `chmod +x migrate_database.py`

### Schema Verification Fails
- Check you're in correct directory
- Verify requests.db exists
- Check database file permissions
- Try: `python migrate_database.py --backup` to re-run migration

## Communication

### Before Deployment
- [ ] Notify users of upcoming maintenance (if needed)
- [ ] Post status update
- [ ] Set estimated downtime window

### After Successful Deployment
- [ ] Confirm stability in logs
- [ ] Post deployment complete message
- [ ] Link to MIGRATION_SUMMARY.md for reference

## Contact & Support

If you encounter issues:
1. Check the logs first
2. Review MIGRATION_SUMMARY.md and DATABASE_DEPLOYMENT.md
3. Verify database backup exists and is good
4. Run: `python migrate_database.py --verify` for diagnosis

---

**Deployment Date**: _______________
**Deployed By**: _______________
**Notes**: _______________


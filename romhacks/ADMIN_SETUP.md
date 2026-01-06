# Admin Dashboard Setup

## Accessing the Admin Portal

The admin dashboard is protected with a password and accessible at `/admin/login`.

### Security Setup

**IMPORTANT: Change these immediately before deploying!**

Set these environment variables on your server:

```bash
export ADMIN_PASSWORD="your-very-secure-password-here"
export SECRET_KEY="your-flask-secret-key-here"
```

Or add to your `.env` file (if using python-dotenv):
```
ADMIN_PASSWORD=your-very-secure-password-here
SECRET_KEY=your-flask-secret-key-here
```

### Features

- **Login Page** (`/admin/login`) - Password-protected entry point
- **Dashboard** (`/admin`) - View pending, approved, and rejected submissions
- **Submission Review** - Full details of each submission with:
  - Basic game info
  - Description
  - Download links
  - Base game requirements (ROMs needed)
  - Screenshots and cover art
  - Metadata (submitted date, submitter email)
  
- **Actions**:
  - **Approve** - Mark submission as approved
  - **Reject** - Mark submission as rejected with custom reason
  - **View Metadata** - IP hash, submission time, user email

### Workflow

1. Navigate to `/admin/login`
2. Enter the `ADMIN_PASSWORD`
3. View submissions by status (Pending, Approved, Rejected)
4. Click "Review" on any submission
5. Approve or Reject with optional notes
6. Click "Logout" when done

### Database Changes

The `requests` table now tracks:
- `status` - 'new', 'approved', 'rejected'
- `admin_notes` - Reason for rejection or approval notes
- `ip_hash` - Anonymized submitter IP
- `user_agent_hash` - User agent hash for fraud detection

### Security Notes

- All admin sessions use Flask sessions (cookie-based)
- IPs are hashed for privacy
- Password is checked against environment variable (not stored in code)
- Rate limiting applies to login attempts (10 per hour)
- All admin actions require valid session

### Logout

Users stay logged in based on their session. Sessions are invalidated when:
- User clicks "Logout"
- Browser closes (default Flask session behavior)

To adjust session timeout, modify the Flask session config in `app.py`.

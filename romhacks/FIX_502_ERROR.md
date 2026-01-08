# Fix 502 Bad Gateway Error

## Root Cause
The Flask development server (`app.run()`) wasn't listening on an accessible interface, or wasn't running at all.

## Solution Steps

### 1. Install Dependencies on Server
```bash
cd /var/www/romhacks
pip install -r requirements.txt
```

### 2. Set Up Systemd Service
```bash
sudo cp romhacks.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable romhacks
sudo systemctl start romhacks
sudo systemctl status romhacks
```

### 3. Configure Nginx
```bash
sudo cp nginx.conf /etc/nginx/sites-available/romhacks
sudo ln -s /etc/nginx/sites-available/romhacks /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4. Verify Status
```bash
# Check if Flask app is running
curl http://127.0.0.1:5000/

# Check Nginx logs for errors
sudo tail -f /var/log/nginx/error.log

# Check Flask service logs
sudo journalctl -u romhacks -f
```

## Changes Made
1. **app.py**: Changed `app.run(debug=False)` to `app.run(host='0.0.0.0', port=5000, debug=False)` to listen on all interfaces
2. **requirements.txt**: Added `gunicorn==21.2.0` for production WSGI server
3. **romhacks.service**: Systemd service file to run app with gunicorn
4. **nginx.conf**: Proper nginx proxy configuration pointing to gunicorn

## Notes
- App now runs on port 5000 via gunicorn
- Nginx proxies requests from port 80 to port 5000
- Uses 4 workers for better performance
- Static files served directly by Nginx

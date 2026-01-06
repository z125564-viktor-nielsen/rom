from flask import Flask, render_template, abort, send_from_directory, request, jsonify, session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from database import (
    get_db_connection,
    init_db,
    get_games,
    get_ports,
    get_game_by_id,
    get_port_by_id,
    track_download,
    get_download_count,
    get_download_counts_for_ids,
    submit_feedback,
    submit_game,
    hash_string,
    get_submissions,
    get_submission_by_id,
    update_submission_status,
    reject_submission,
    approve_submission,
    update_game,
    update_port,
    delete_game,
    delete_port,
)
import json
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')  # Change this!

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Initialize database on startup
init_db()

# Admin authentication
def login_required(f):
    """Decorator to require admin login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
@limiter.limit("10 per hour")
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        admin_username = os.environ.get('ADMIN_USERNAME', 'PeterGriffin77*')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')  # Change this!
        
        if username == admin_username and password == admin_password:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid username or password'), 401
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect('/')

@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    status = request.args.get('status', 'new')
    submissions = get_submissions(status)
    
    return render_template('admin_dashboard.html', submissions=submissions, active_status=status)

@app.route('/admin/submission/<int:submission_id>')
@login_required
def admin_submission_detail(submission_id):
    """View submission details"""
    submission = get_submission_by_id(submission_id)
    if not submission:
        abort(404)
    
    return render_template('admin_submission_detail.html', submission=submission)

@app.route('/api/admin/submission/<int:submission_id>/approve', methods=['POST'])
@login_required
def api_approve_submission(submission_id):
    """API to approve a submission"""
    success = approve_submission(submission_id)
    return jsonify({'success': success})

@app.route('/api/admin/submission/<int:submission_id>/reject', methods=['POST'])
@login_required
def api_reject_submission(submission_id):
    """API to reject a submission with reason"""
    data = request.get_json() or {}
    reason = data.get('reason', '')
    success = reject_submission(submission_id, reason)
    return jsonify({'success': success})

@app.route('/api/admin/submission/<int:submission_id>/status', methods=['GET'])
@login_required
def api_submission_status(submission_id):
    """API to get submission status"""
    submission = get_submission_by_id(submission_id)
    if not submission:
        return jsonify({'error': 'Not found'}), 404
    
    return jsonify({
        'id': submission['id'],
        'status': submission['status'],
        'admin_notes': submission['admin_notes']
    })


# --- Admin Game/Port Management Routes ---

@app.route('/admin/games')
@login_required
def admin_games():
    """Admin page to manage games (romhacks)"""
    games = get_games()
    attach_download_counts(games)
    games.sort(key=lambda g: g.get('title', '').lower())
    return render_template('admin_games.html', items=games, item_type='game')


@app.route('/admin/ports')
@login_required
def admin_ports():
    """Admin page to manage ports"""
    ports_data = get_ports()
    attach_download_counts(ports_data)
    ports_data.sort(key=lambda p: p.get('title', '').lower())
    return render_template('admin_games.html', items=ports_data, item_type='port')


@app.route('/admin/game/<game_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_game(game_id):
    """Edit a game (romhack)"""
    game = get_game_by_id(game_id)
    if not game:
        abort(404)
    
    if request.method == 'POST':
        data = {}
        # Extract form data
        for field in ['title', 'console', 'version', 'release_date', 'author',
                      'description', 'base_game', 'version_region', 'download_link',
                      'image_url', 'base_region', 'base_revision', 'base_header',
                      'base_checksum_crc32', 'base_checksum_md5', 'base_checksum_sha1',
                      'patch_format', 'patch_output_ext', 'dev_stage', 'instruction_text',
                      'discord_url', 'reddit_url', 'support_forum_url', 'troubleshooting_url',
                      'rom_checker_url', 'instructions_pc', 'instructions_android',
                      'instructions_linux', 'instructions_web', 'instructions_ios',
                      'instructions_mac', 'instructions_switch', 'instructions_ps4', 'instructions_xbox']:
            if field in request.form:
                data[field] = request.form.get(field, '').strip()
        
        # Handle features as comma-separated list
        features_str = request.form.get('features', '')
        data['features'] = [f.strip() for f in features_str.split(',') if f.strip()]
        
        # Handle screenshots as newline-separated list
        screenshots_str = request.form.get('screenshots', '')
        data['screenshots'] = [s.strip() for s in screenshots_str.split('\n') if s.strip()]
        
        # Boolean fields
        data['popular'] = 'popular' in request.form
        data['online_play'] = 'online_play' in request.form
        data['instruction'] = 'instruction' in request.form
        
        update_game(game_id, data)
        return redirect(url_for('admin_games'))
    
    return render_template('admin_edit_game.html', item=game, item_type='game')


@app.route('/admin/port/<port_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_port(port_id):
    """Edit a port"""
    port = get_port_by_id(port_id)
    if not port:
        abort(404)
    
    if request.method == 'POST':
        data = {}
        # Extract form data
        for field in ['title', 'console', 'version', 'release_date', 'author',
                      'description', 'base_game', 'original_platform', 'download_link',
                      'image_url', 'base_region', 'base_revision', 'base_header',
                      'base_checksum_crc32', 'base_checksum_md5', 'base_checksum_sha1',
                      'patch_format', 'patch_output_ext', 'instruction_text',
                      'discord_url', 'reddit_url', 'support_forum_url', 'troubleshooting_url',
                      'rom_checker_url', 'instructions_pc', 'instructions_android',
                      'instructions_linux', 'instructions_web', 'instructions_ios',
                      'instructions_mac', 'instructions_switch', 'instructions_ps4', 'instructions_xbox']:
            if field in request.form:
                data[field] = request.form.get(field, '').strip()
        
        # Handle features as comma-separated list
        features_str = request.form.get('features', '')
        data['features'] = [f.strip() for f in features_str.split(',') if f.strip()]
        
        # Handle screenshots as newline-separated list
        screenshots_str = request.form.get('screenshots', '')
        data['screenshots'] = [s.strip() for s in screenshots_str.split('\n') if s.strip()]
        
        # Boolean fields
        data['popular'] = 'popular' in request.form
        data['online_play'] = 'online_play' in request.form
        data['instruction'] = 'instruction' in request.form
        
        update_port(port_id, data)
        return redirect(url_for('admin_ports'))
    
    return render_template('admin_edit_game.html', item=port, item_type='port')


@app.route('/api/admin/game/<game_id>/delete', methods=['POST'])
@login_required
def api_delete_game(game_id):
    """API to delete a game"""
    success = delete_game(game_id)
    return jsonify({'success': success})


@app.route('/api/admin/port/<port_id>/delete', methods=['POST'])
@login_required
def api_delete_port(port_id):
    """API to delete a port"""
    success = delete_port(port_id)
    return jsonify({'success': success})


def attach_download_counts(items):
    """Annotate each item with its download count."""
    if not items:
        return

    ids = [item.get('id') for item in items if item.get('id')]
    counts = get_download_counts_for_ids(ids)
    for item in items:
        item['download_count'] = counts.get(item.get('id'), 0)


def get_platform_instructions(game):
    """Extract platform-specific instructions from database columns."""
    instructions = {}
    
    # Check each platform column
    for platform in ['pc', 'android', 'linux', 'web', 'ios', 'mac', 'switch', 'ps4', 'xbox']:
        col_name = f'instructions_{platform}'
        if col_name in game and game[col_name]:
            instructions[platform] = game[col_name]
    
    return instructions


def get_social_links(game):
    """Extract social media links from database JSON."""
    links = []
    
    if game.get('social_links'):
        try:
            links = json.loads(game['social_links'])
        except (json.JSONDecodeError, TypeError):
            links = []
    
    return links


def format_download_count(count):
    """Turn raw download totals into a readable label."""
    try:
        total = int(count or 0)
    except (TypeError, ValueError):
        total = 0

    if total >= 1000:
        value = round(total / 1000, 1)
        if value.is_integer():
            return f"{int(value)}k"
        return f"{value:.1f}k"

    return str(total)


@app.template_filter('download_count_label')
def download_count_label(count):
    return format_download_count(count)

# --- COLOR CODING LOGIC ---
CONSOLE_STYLES = {
    'gb': 'bg-emerald-900/70 text-emerald-200 border-emerald-500/50',
    'gbc': 'bg-lime-900/80 text-lime-300 border-lime-500/50',
    'gba': 'bg-purple-900/80 text-purple-300 border-purple-500/50',
    'snes': 'bg-indigo-900/80 text-indigo-300 border-indigo-500/50',
    'n64': 'bg-red-900/80 text-red-300 border-red-500/50',
    'nds': 'bg-pink-900/80 text-pink-300 border-pink-500/50',
    '3ds': 'bg-orange-900/80 text-orange-300 border-orange-500/50',
    'wii': 'bg-cyan-900/80 text-cyan-300 border-cyan-500/50',
    'gcn': 'bg-violet-900/80 text-violet-300 border-violet-500/50',
    'default': 'bg-gray-800 text-gray-300 border-gray-600'
}
PLATFORM_STYLE = {
    'android': 'bg-green-900/70 text-green-200 border-green-500/50',
    'windows': 'bg-blue-900/70 text-blue-200 border-blue-500/50',
    'linux': 'bg-yellow-900/70 text-yellow-200 border-yellow-500/50',
    'macos': 'bg-gray-700/70 text-gray-200 border-gray-500/50',
    'mac': 'bg-gray-700/70 text-gray-200 border-gray-500/50'
}

@app.route('/')
def index():
    games = get_games()
    ports_data = get_ports()
    # Attach download counts to all items
    attach_download_counts(games)
    attach_download_counts(ports_data)
    
    # Sort by downloads and take top 12
    games.sort(key=lambda g: g.get('download_count', 0), reverse=True)
    ports_data.sort(key=lambda p: p.get('download_count', 0), reverse=True)
    
    popular_games = games[:12]
    popular_ports = ports_data[:12]

    return render_template('index.html', games=popular_games, ports=popular_ports, styles=CONSOLE_STYLES, platform_styles=PLATFORM_STYLE)

@app.route('/ports')
def ports():
    ports_data = get_ports()
    attach_download_counts(ports_data)
    ports_data.sort(key=lambda p: p.get('download_count', 0), reverse=True)
    ports_data = ports_data[:12]
    return render_template('ports.html', games=ports_data, styles=PLATFORM_STYLE)

@app.route('/romhacks')
def romhacks():
    games = get_games()
    attach_download_counts(games)
    games.sort(key=lambda g: g.get('download_count', 0), reverse=True)
    games = games[:12]
    return render_template('romhacks.html', games=games, styles=CONSOLE_STYLES)

@app.route('/patcher')
def patcher():
    return render_template('patcher.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/disclaimer')
def disclaimer():
    return render_template('disclaimer.html')

@app.route('/submit')
def submit():
    return render_template('submit.html')

@app.route('/logo/<filename>')
def logo_file(filename):
    return send_from_directory('logo', filename)


@app.route('/sitemap.xml')
def sitemap():
    """Generate dynamic sitemap.xml for SEO"""
    from flask import Response
    from datetime import datetime
    
    base_url = request.url_root.rstrip('/')
    
    # Static pages with priorities
    static_pages = [
        ('/', '1.0', 'daily'),
        ('/romhacks', '0.9', 'daily'),
        ('/ports', '0.9', 'daily'),
        ('/patcher', '0.8', 'weekly'),
        ('/submit', '0.6', 'monthly'),
        ('/contact', '0.5', 'monthly'),
        ('/privacy-policy', '0.3', 'yearly'),
        ('/disclaimer', '0.3', 'yearly'),
    ]
    
    # Get all games and ports
    games = get_games()
    ports = get_ports()
    
    xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_parts.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    
    # Add static pages
    for path, priority, changefreq in static_pages:
        xml_parts.append(f'''  <url>
    <loc>{base_url}{path}</loc>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>''')
    
    # Add game pages
    for game in games:
        xml_parts.append(f'''  <url>
    <loc>{base_url}/game/{game['id']}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>''')
    
    # Add port pages
    for port in ports:
        xml_parts.append(f'''  <url>
    <loc>{base_url}/game/{port['id']}</loc>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>''')
    
    xml_parts.append('</urlset>')
    
    return Response('\n'.join(xml_parts), mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    """Serve robots.txt for search engine crawlers"""
    from flask import Response
    
    base_url = request.url_root.rstrip('/')
    
    robots_content = f"""# robots.txt for ROMHACKS.NET
User-agent: *
Allow: /

# Disallow admin pages
Disallow: /admin
Disallow: /admin/
Disallow: /api/

# Sitemap location
Sitemap: {base_url}/sitemap.xml
"""
    return Response(robots_content, mimetype='text/plain')


@app.route('/game/<game_id>')
def game_page(game_id):
    game = get_game_by_id(game_id)
    is_port = False
    if game is None:
        # Try ports as well
        game = get_port_by_id(game_id)
        is_port = True
    if game is None:
        abort(404)
    # Use appropriate color styles based on whether it's a port or game
    styles = PLATFORM_STYLE if is_port else CONSOLE_STYLES
    download_count = get_download_count(game_id)
    # Parse platform-specific instructions
    instructions = get_platform_instructions(game)
    # Parse social links
    social_links = get_social_links(game)
    return render_template('game.html', game=game, styles=styles, is_port=is_port, download_count=download_count, instructions=instructions, social_links=social_links)

@app.route('/api/track-download/<game_id>', methods=['POST'])
@limiter.limit("30 per hour")
def track_download_endpoint(game_id):
    client_ip = request.remote_addr
    # If behind a proxy, try to get the real IP
    if request.headers.get('X-Forwarded-For'):
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    result = track_download(game_id, client_ip)
    return jsonify({'success': result})

@app.route('/api/feedback', methods=['POST'])
@limiter.limit("10 per hour")
def submit_feedback_endpoint():
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('description'):
        return jsonify({'success': False, 'message': 'Description is required'}), 400
    
    feedback_type = data.get('type', '').strip()
    if feedback_type not in ['broken-link', 'correction']:
        return jsonify({'success': False, 'message': 'Invalid feedback type'}), 400
    
    # Get client IP
    client_ip = request.remote_addr
    if request.headers.get('X-Forwarded-For'):
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    # Submit feedback
    feedback_id = submit_feedback(
        feedback_type=feedback_type,
        title=data.get('title', '').strip(),
        url=data.get('url', '').strip(),
        description=data.get('description', '').strip(),
        email=data.get('email', '').strip(),
        ip_address=client_ip
    )
    
    return jsonify({'success': True, 'id': feedback_id})

@app.route('/api/submit-game', methods=['POST'])
@limiter.limit("5 per hour")
def submit_game_endpoint():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['title', 'base_game', 'console', 'author', 'description', 'download_link', 'patch_format']
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        return jsonify({
            'success': False,
            'error': f'Missing required fields: {", ".join(missing_fields)}'
        }), 400
    
    # Get client IP
    client_ip = request.remote_addr
    if request.headers.get('X-Forwarded-For'):
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    # Add user agent to submission data
    data['user_agent'] = request.headers.get('User-Agent', '')
    
    # Submit game
    result = submit_game(data, client_ip)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': 'Game submission received! Our team will review it shortly.',
            'id': result['id']
        })
    else:
        return jsonify({
            'success': False,
            'error': result.get('error', 'Failed to submit game')
        }), 400

if __name__ == '__main__':
    app.run(debug=False)
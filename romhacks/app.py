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
    get_feedback,
    update_feedback_status,
    delete_feedback,
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
    insert_game,
    insert_port,
    get_monthly_download_counts_for_ids,
    check_and_archive_previous_month,
    get_all_archived_months,
    get_monthly_popular_history,
    # Review system functions
    submit_review,
    get_reviews,
    get_review_stats,
    get_review_stats_batch,
    has_user_reviewed,
    vote_helpful,
    delete_review,
    get_user_votes,
)
import json
import os
import requests
import boto3
import uuid
from botocore.config import Config
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')  # Change this!

# RetroAchievements OAuth config
RA_CLIENT_ID = os.environ.get('RA_CLIENT_ID', '')
RA_CLIENT_SECRET = os.environ.get('RA_CLIENT_SECRET', '')
RA_REDIRECT_URI = os.environ.get('RA_REDIRECT_URI', 'http://localhost:5000/auth/ra/callback')

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000000 per day", "100000 per hour"],
    storage_uri="memory://"
)

# Initialize database on startup
init_db()

# Check and archive previous month's data if needed
check_and_archive_previous_month()

@app.context_processor
def inject_globals():
    return {
        'current_year': datetime.now().year,
        'site_name': 'ROMHACKS.NET'
    }

# --- Performance & SEO Middleware ---
@app.after_request
def add_cache_headers(response):
    """Add cache headers for performance optimization"""
    # Cache static assets for 30 days
    if request.path.startswith('/static/'):
        response.cache_control.max_age = 2592000  # 30 days
        response.cache_control.public = True
    # Cache sitemaps and robots.txt for 7 days
    elif request.path in ['/sitemap.xml', '/robots.txt']:
        response.cache_control.max_age = 604800  # 7 days
        response.cache_control.public = True
    # No cache for pages with dynamic download counts
    elif request.path.startswith('/game/') or request.path.startswith('/port/') or request.path.endswith('-rom-hacks'):
        response.cache_control.no_cache = True
        response.cache_control.must_revalidate = True
        response.cache_control.public = True
    # No cache for category and index pages with dynamic download counts
    elif request.path in ['/romhacks', '/ports', '/']:
        response.cache_control.no_cache = True
        response.cache_control.must_revalidate = True
        response.cache_control.public = True
    # No cache for dynamic pages (admin, API, etc)
    elif '/admin/' in request.path or '/api/' in request.path:
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.private = True
    
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    return response

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
    """Admin dashboard with submissions and feedback"""
    view = request.args.get('view', 'submissions')
    status = request.args.get('status', 'new')
    
    # Always get counts for all statuses (needed for badges/tabs)
    pending_count = len(get_submissions('new'))
    approved_count = len(get_submissions('approved'))
    rejected_count = len(get_submissions('rejected'))
    
    feedback_new_count = len(get_feedback(status='new'))
    feedback_resolved_count = len(get_feedback(status='resolved'))
    feedback_ignored_count = len(get_feedback(status='ignored'))
    
    # Get data for the active view only
    submissions = get_submissions(status) if view == 'submissions' else []
    feedback_list = get_feedback(status=status) if view == 'feedback' else []
    
    return render_template('admin_dashboard.html', 
                          active_view=view,
                          submissions=submissions, 
                          active_status=status,
                          pending_count=pending_count,
                          approved_count=approved_count,
                          rejected_count=rejected_count,
                          feedback_list=feedback_list,
                          feedback_new_count=feedback_new_count,
                          feedback_resolved_count=feedback_resolved_count,
                          feedback_ignored_count=feedback_ignored_count)

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

@app.route('/admin/feedback/<int:feedback_id>')
@login_required
def admin_feedback_detail(feedback_id):
    """View feedback details"""
    feedback_list = get_feedback()
    feedback = next((f for f in feedback_list if f['id'] == feedback_id), None)
    if not feedback:
        abort(404)
    
    return render_template('admin_feedback_detail.html', feedback=feedback)

@app.route('/api/admin/feedback/<int:feedback_id>/status', methods=['POST'])
@login_required
def api_update_feedback_status(feedback_id):
    """API to update feedback status"""
    data = request.get_json() or {}
    new_status = data.get('status', '')
    
    if new_status not in ['new', 'resolved', 'ignored']:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    
    success = update_feedback_status(feedback_id, new_status)
    return jsonify({'success': success})

@app.route('/api/admin/feedback/<int:feedback_id>/notes', methods=['POST'])
@login_required
def api_update_feedback_notes(feedback_id):
    """API to update feedback admin notes"""
    data = request.get_json() or {}
    admin_notes = data.get('admin_notes', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE feedback SET admin_notes = ? WHERE id = ?', (admin_notes, feedback_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    
    return jsonify({'success': success})

@app.route('/api/admin/feedback/<int:feedback_id>/delete', methods=['POST'])
@login_required
def api_delete_feedback(feedback_id):
    """API to delete feedback"""
    success = delete_feedback(feedback_id)
    return jsonify({'success': success})



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


# R2 Upload Helper
def get_r2_client():
    account_id = os.environ.get('R2_ACCOUNT_ID')
    access_key = os.environ.get('R2_ACCESS_KEY_ID')
    secret_key = os.environ.get('R2_SECRET_ACCESS_KEY')
    
    if not all([account_id, access_key, secret_key]):
        return None

    return boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )

@app.route('/admin/generate-presigned-url', methods=['POST'])
@login_required 
def generate_presigned_url():
    if session.get('role') != 'admin':
         return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    filename = data.get('filename')
    filetype = data.get('filetype')
    
    if not filename or not filetype:
        return jsonify({'error': 'Missing filename or filetype'}), 400
        
    # Generate unique filename
    ext = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    object_key = f"screenshots/{unique_filename}"
    
    s3 = get_r2_client()
    if not s3:
        return jsonify({'error': 'R2 storage not configured'}), 500
        
    try:
        bucket = os.environ.get('R2_BUCKET')
        
        # Generate presigned URL
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket,
                'Key': object_key,
                'ContentType': filetype
            },
            ExpiresIn=3600
        )
        
        public_base = os.environ.get('R2_PUBLIC_BASE', '')
        if public_base:
             public_url = f"{public_base.rstrip('/')}/{object_key}"
        else:
             public_url = f"https://{bucket}.r2.cloudflarestorage.com/{object_key}"

        return jsonify({
            'signedUrl': presigned_url,
            'publicUrl': public_url
        })
        
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return jsonify({'error': str(e)}), 500


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
                      'patch_format', 'patch_output_ext', 'dev_stage',
                      'official_website', 'discord_url', 'reddit_url', 'support_forum_url', 'troubleshooting_url',
                      'rom_checker_url', 'instructions_pc', 'instructions_android',
                      'instructions_linux', 'instructions_ios',
                      'instructions_mac', 'instructions_switch']:
            if field in request.form:
                data[field] = request.form.get(field, '').strip()
        
        # Handle instruction_text only if special instructions checkbox is checked
        if 'instruction' in request.form:
            data['instruction_text'] = request.form.get('instruction_text', '').strip()
        else:
            data['instruction_text'] = ''
        
        # Handle features as newline-separated list
        features_str = request.form.get('features', '')
        data['features'] = [f.strip() for f in features_str.replace('\r\n', '\n').split('\n') if f.strip()]
        
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
        # Extract form data (exclude ROM/patch-specific fields for ports)
        for field in ['title', 'console', 'version', 'release_date', 'author',
                      'description', 'base_game', 'original_platform', 'download_link',
                      'image_url',
                      'official_website', 'discord_url', 'reddit_url', 'support_forum_url', 'troubleshooting_url',
                      'rom_checker_url', 'instructions_pc', 'instructions_android',
                      'instructions_linux', 'instructions_ios',
                      'instructions_mac', 'instructions_switch',
                      'mod_links', 'mod_instructions']:
            if field in request.form:
                data[field] = request.form.get(field, '').strip()
        
        # Handle instruction_text only if special instructions checkbox is checked
        if 'instruction' in request.form:
            data['instruction_text'] = request.form.get('instruction_text', '').strip()
        else:
            data['instruction_text'] = ''
        
        # Handle features as newline-separated list
        features_str = request.form.get('features', '')
        data['features'] = [f.strip() for f in features_str.replace('\r\n', '\n').split('\n') if f.strip()]
        
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


@app.route('/admin/game/add', methods=['GET', 'POST'])
@login_required
def admin_add_game():
    """Add a new game (romhack)"""
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
                      'instructions_linux', 'instructions_ios',
                      'instructions_mac', 'instructions_switch']:
            if field in request.form:
                data[field] = request.form.get(field, '').strip()
        
        # Generate ID from title
        title = data.get('title', '')
        data['id'] = request.form.get('id', '').strip() or title.lower().replace(' ', '_').replace("'", '')
        
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
        
        insert_game(data)
        return redirect(url_for('admin_games'))
    
    # Empty item for the form
    empty_item = {
        'id': '', 'title': '', 'console': '', 'version': '', 'release_date': '',
        'author': '', 'description': '', 'base_game': '', 'version_region': '',
        'features': [], 'screenshots': [], 'image_url': '', 'download_link': '',
        'base_region': '', 'base_revision': '', 'base_header': '',
        'base_checksum_crc32': '', 'base_checksum_md5': '', 'base_checksum_sha1': '',
        'patch_format': '', 'patch_output_ext': '', 'dev_stage': '',
        'popular': False, 'online_play': False, 'instruction': False, 'instruction_text': '',
        'discord_url': '', 'reddit_url': '', 'support_forum_url': '', 'troubleshooting_url': '',
        'rom_checker_url': '', 'instructions_pc': '', 'instructions_android': '',
        'instructions_linux': '', 'instructions_ios': '',
        'instructions_mac': '', 'instructions_switch': ''
    }
    return render_template('admin_edit_game.html', item=empty_item, item_type='game', is_new=True)


@app.route('/admin/port/add', methods=['GET', 'POST'])
@login_required
def admin_add_port():
    """Add a new port"""
    if request.method == 'POST':
        data = {}
        # Extract form data (exclude ROM/patch-specific fields for ports)
        for field in ['title', 'console', 'version', 'release_date', 'author',
                      'description', 'base_game', 'original_platform', 'download_link',
                      'image_url', 'instruction_text',
                      'discord_url', 'reddit_url', 'support_forum_url', 'troubleshooting_url',
                      'rom_checker_url', 'instructions_pc', 'instructions_android',
                      'instructions_linux', 'instructions_web', 'instructions_ios',
                      'instructions_mac', 'instructions_switch', 'instructions_ps4', 'instructions_xbox']:
            if field in request.form:
                data[field] = request.form.get(field, '').strip()
        
        # Generate ID from title
        title = data.get('title', '')
        data['id'] = request.form.get('id', '').strip() or title.lower().replace(' ', '_').replace("'", '')
        
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
        
        insert_port(data)
        return redirect(url_for('admin_ports'))
    
    # Empty item for the form
    empty_item = {
        'id': '', 'title': '', 'console': '', 'version': '', 'release_date': '',
        'author': '', 'description': '', 'base_game': '', 'original_platform': '',
        'features': [], 'screenshots': [], 'image_url': '', 'download_link': '',
        'popular': False, 'online_play': False, 'instruction': False, 'instruction_text': '',
        'discord_url': '', 'reddit_url': '', 'support_forum_url': '', 'troubleshooting_url': '',
        'rom_checker_url': '', 'instructions_pc': '', 'instructions_android': '',
        'instructions_linux': '', 'instructions_ios': '',
        'instructions_mac': '', 'instructions_switch': ''
    }
    return render_template('admin_edit_game.html', item=empty_item, item_type='port', is_new=True)


@app.route('/admin/import-json', methods=['GET', 'POST'])
@login_required
def admin_import_json():
    """Import games or ports from JSON"""
    if request.method == 'POST':
        json_data = None
        item_type = 'game'
        
        # Handle both JSON POST and form data
        if request.is_json:
            # JSON POST request
            data = request.get_json() or {}
            json_data = json.dumps(data)
            item_type = data.get('item_type', 'game') if isinstance(data, dict) and 'item_type' in data else 'game'
        else:
            # Form POST request
            json_data = request.form.get('json_data', '')
            item_type = request.form.get('item_type', 'game')
        
        if not json_data or not json_data.strip():
            if request.is_json:
                return jsonify({'success': False, 'error': 'No JSON data provided'}), 400
            else:
                return render_template('admin_import_json.html', 
                                       json_error='No JSON data provided')
        
        try:
            items = json.loads(json_data)
            if not isinstance(items, list):
                items = [items]
            
            success_count = 0
            errors = []
            
            for item in items:
                try:
                    if item_type == 'port':
                        insert_port(item)
                    else:
                        insert_game(item)
                    success_count += 1
                except Exception as e:
                    errors.append(f"Error importing {item.get('title', 'unknown')}: {str(e)}")
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': f'Successfully imported {success_count} of {len(items)} items',
                    'success_count': success_count,
                    'total': len(items),
                    'errors': errors
                })
            else:
                return render_template('admin_import_json.html', 
                                       success_count=success_count, 
                                       errors=errors,
                                       total=len(items))
        except json.JSONDecodeError as e:
            if request.is_json:
                return jsonify({'success': False, 'error': f'Invalid JSON: {str(e)}'}), 400
            else:
                return render_template('admin_import_json.html', 
                                       json_error=f"Invalid JSON: {str(e)}")
    
    return render_template('admin_import_json.html')


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
    for platform in ['pc', 'android', 'linux', 'ios', 'mac', 'switch']:
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


def get_emulator_guides():
    """Load emulator guides for all consoles from JSON file."""
    try:
        guides_path = os.path.join(os.path.dirname(__file__), 'emulator_guides.json')
        with open(guides_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_console_emulator_guide(console):
    """Get the emulator guide for a specific console."""
    guides = get_emulator_guides()
    console_key = console.lower().replace(' ', '').replace('-', '')
    return guides.get(console_key, None)


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


def normalize_console_name(console):
    """Normalize console names to match CONSOLE_STYLES keys"""
    if not console:
        return 'default'
    
    # Convert to lowercase and remove spaces/hyphens
    normalized = console.lower().strip().replace(' ', '').replace('-', '')
    
    # Map full names to abbreviations
    console_mapping = {
        'gameboy': 'gb',
        'gameboycolor': 'gbc',
        'gameboyadvance': 'gba',
        'supernintendo': 'snes',
        'nintendo64': 'n64',
        'nintendods': 'nds',
        'nintendo3ds': '3ds',
        'gamecube': 'gcn'
    }
    
    # Check if it's a full name that needs mapping
    if normalized in console_mapping:
        return console_mapping[normalized]
    
    # Return as-is (already abbreviated) or default
    return normalized if normalized in CONSOLE_STYLES else 'default'


@app.template_filter('normalize_console')
def normalize_console_filter(console):
    """Template filter to normalize console names"""
    return normalize_console_name(console)


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

def attach_monthly_download_counts(items):
    """Attach monthly download counts to a list of game/port dicts"""
    if not items:
        return
    ids = [item['id'] for item in items]
    counts = get_monthly_download_counts_for_ids(ids)
    for item in items:
        item['monthly_download_count'] = counts.get(item['id'], 0)

@app.route('/')
def index():
    games = get_games()
    ports_data = get_ports()
    
    # Attach total download counts for display
    attach_download_counts(games)
    attach_download_counts(ports_data)
    
    # Attach monthly download counts for sorting
    attach_monthly_download_counts(games)
    attach_monthly_download_counts(ports_data)
    
    # Sort by monthly downloads (most popular this month) and take top 12
    games.sort(key=lambda g: (g.get('monthly_download_count', 0), g.get('download_count', 0)), reverse=True)
    ports_data.sort(key=lambda p: (p.get('monthly_download_count', 0), p.get('download_count', 0)), reverse=True)
    
    popular_games = games[:12]
    popular_ports = ports_data[:12]
    
    # Get current month name for display
    current_month = datetime.now().strftime('%B %Y')

    return render_template('index.html', games=popular_games, ports=popular_ports, 
                          styles=CONSOLE_STYLES, platform_styles=PLATFORM_STYLE,
                          current_month=current_month)

@app.route('/ports')
def ports():
    ports_data = get_ports()
    attach_download_counts(ports_data)
    attach_monthly_download_counts(ports_data)
    ports_data.sort(key=lambda p: (p.get('monthly_download_count', 0), p.get('download_count', 0)), reverse=True)
    ports_data = ports_data[:12]
    
    # Get current month name for display
    current_month = datetime.now().strftime('%B %Y')
    
    return render_template('ports.html', games=ports_data, styles=PLATFORM_STYLE, current_month=current_month)

@app.route('/romhacks')
def romhacks():
    games = get_games()
    attach_download_counts(games)
    attach_monthly_download_counts(games)
    games.sort(key=lambda g: (g.get('monthly_download_count', 0), g.get('download_count', 0)), reverse=True)
    games = games[:12]
    
    # Get current month name for display
    current_month = datetime.now().strftime('%B %Y')
    
    return render_template('romhacks.html', games=games, styles=CONSOLE_STYLES, current_month=current_month)

@app.route('/patcher')
def patcher():
    return render_template('patcher.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/claim')
def claim():
    return render_template('claim.html')

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


# --- Base Game Hub Pages (Programmatic SEO) ---
@app.route('/<base_game>-rom-hacks')
@app.route('/<base_game>-hacks')
def base_game_hub(base_game):
    """Generate dynamic hub pages for specific base games (e.g., /pokemon-emerald-rom-hacks)"""
    # Normalize base_game parameter for search
    base_game_normalized = base_game.lower().replace('-', ' ')
    
    # Get all games
    all_games = get_games()
    
    # Special handling for major franchises to aggregate all related games
    if base_game_normalized == 'pokemon' or base_game_normalized == 'pokémon':
        matching_games = [
            game for game in all_games 
            if 'pokemon' in game.get('base_game', '').lower() or 'pokémon' in game.get('base_game', '').lower()
        ]
        base_game_display = "Pokémon"
    elif base_game_normalized == 'mario':
        matching_games = [
            game for game in all_games 
            if 'mario' in game.get('base_game', '').lower()
        ]
        base_game_display = "Mario"
    elif base_game_normalized == 'zelda':
        matching_games = [
            game for game in all_games 
            if 'zelda' in game.get('base_game', '').lower()
        ]
        base_game_display = "Zelda"
    elif base_game_normalized == 'super mario world':
        matching_games = [
            game for game in all_games 
            if 'super mario world' in game.get('base_game', '').lower()
        ]
        base_game_display = "Super Mario World"
    elif base_game_normalized == 'fire emblem':
        matching_games = [
            game for game in all_games 
            if 'fire emblem' in game.get('base_game', '').lower()
        ]
        base_game_display = "Fire Emblem"
    else:
        # Filter games that match this base game identically (handling é/e mismatch)
        matching_games = [
            game for game in all_games 
            if game.get('base_game', '').lower().replace('é', 'e') == base_game_normalized.replace('é', 'e')
        ]
        # Get formatted base game name for display
        base_game_display = ' '.join(word.capitalize() for word in base_game_normalized.split())
    
    if not matching_games:
        abort(404)
    
    # Sort by download count
    attach_download_counts(matching_games)
    matching_games.sort(key=lambda g: g.get('download_count', 0), reverse=True)
    
    return render_template(
        'base_game_hub.html',
        base_game=base_game_display,
        base_game_slug=base_game,
        games=matching_games,
        styles=CONSOLE_STYLES,
        game_count=len(matching_games)
    )


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
    
    # Add major franchise hubs (manual override for high SEO value)
    franchise_hubs = [
        ('pokemon', 'daily', '0.95'),
        ('mario', 'daily', '0.92'),
        ('zelda', 'daily', '0.92'),
        ('fire-emblem', 'weekly', '0.88'),
        ('super-mario-world', 'weekly', '0.88')
    ]
    for franchise, changefreq, priority in franchise_hubs:
         xml_parts.append(f'''  <url>
    <loc>{base_url}/{franchise}-rom-hacks</loc>
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
    
    # Add base game hub pages (programmatic SEO)
    unique_base_games = set()
    for game in games:
        base_game = game.get('base_game', '')
        if base_game:
            unique_base_games.add(base_game)
    
    for base_game in sorted(unique_base_games):
        base_game_slug = base_game.lower().replace(' ', '-')
        xml_parts.append(f'''  <url>
    <loc>{base_url}/{base_game_slug}-rom-hacks</loc>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
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
        # If it's actually a port ID, send them to the port page (game.html has no modding section)
        port = get_port_by_id(game_id)
        if port:
            return redirect(url_for('port_page', port_id=game_id))
        abort(404)
    # Use appropriate color styles based on whether it's a port or game
    styles = PLATFORM_STYLE if is_port else CONSOLE_STYLES
    download_count = get_download_count(game_id)
    # Parse platform-specific instructions (legacy, kept for backward compatibility)
    instructions = get_platform_instructions(game)
    # Parse social links
    social_links = get_social_links(game)
    # Get emulator guide for the console
    console = game.get('console', '')
    emulator_guide = get_console_emulator_guide(console) if not is_port else None
    return render_template('game.html', game=game, styles=styles, is_port=is_port, download_count=download_count, instructions=instructions, social_links=social_links, emulator_guide=emulator_guide)

@app.route('/port/<port_id>')
def port_page(port_id):
    game = get_port_by_id(port_id)
    if game is None:
        abort(404)
    # Use platform styles for ports
    styles = PLATFORM_STYLE
    download_count = get_download_count(port_id)
    # Parse platform-specific instructions
    instructions = get_platform_instructions(game)
    # Parse social links
    social_links = get_social_links(game)
    return render_template('port_games.html', game=game, styles=styles, is_port=True, download_count=download_count, instructions=instructions, social_links=social_links)

@app.route('/api/track-download/<game_id>', methods=['POST'])
@limiter.limit("30 per hour")
def track_download_endpoint(game_id):
    client_ip = request.remote_addr
    # If behind a proxy, try to get the real IP
    if request.headers.get('X-Forwarded-For'):
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    result = track_download(game_id, client_ip)
    # Get the updated count and return formatted
    new_count = get_download_count(game_id)
    return jsonify({'success': result, 'new_count': format_download_count(new_count)})

@app.route('/api/feedback', methods=['POST'])
@limiter.limit("10 per hour")
def submit_feedback_endpoint():
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('description'):
        return jsonify({'success': False, 'message': 'Description is required'}), 400
    
    feedback_type = data.get('type', '').strip()
    if feedback_type not in ['broken-link', 'correction', 'claim', 'feedback']:
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


# ============================================
# RETROACHIEVEMENTS AUTHENTICATION
# ============================================

@app.route('/auth/ra/login')
def ra_login():
    """Initiate RetroAchievements OAuth login"""
    # Store return URL if provided
    return_url = request.args.get('return_url', '/')
    session['ra_return_url'] = return_url
    
    # For now, redirect to a simple web API auth flow
    # RA uses API key-based auth, so we'll use a simpler approach
    return redirect(url_for('ra_login_page'))


@app.route('/auth/ra/login-page')
def ra_login_page():
    """Show RetroAchievements login form"""
    # Get return_url from query params first, then session, then default to /
    return_url = request.args.get('return_url') or session.get('ra_return_url', '/')
    session['ra_return_url'] = return_url
    return render_template('ra_login.html', return_url=return_url)


@app.route('/auth/ra/verify', methods=['POST'])
@limiter.limit("10 per minute")
def ra_verify():
    """Verify RetroAchievements credentials using their Web API"""
    data = request.get_json()
    username = data.get('username', '').strip()
    api_key = data.get('api_key', '').strip()
    
    if not username or not api_key:
        return jsonify({'success': False, 'error': 'Username and API key are required'}), 400
    
    try:
        # Verify credentials by fetching user profile
        ra_url = f'https://retroachievements.org/API/API_GetUserSummary.php?z={username}&y={api_key}&u={username}'
        response = requests.get(ra_url, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            
            # Check if valid response (has required fields)
            if user_data and 'ID' in user_data:
                # Store in session
                session['ra_user'] = {
                    'username': username,
                    'user_id': user_data.get('ID'),
                    'profile_pic': f"https://retroachievements.org{user_data.get('UserPic', '/UserPic/_.png')}",
                    'total_points': user_data.get('TotalPoints', 0),
                    'api_key': api_key  # Store for future API calls
                }
                
                return jsonify({
                    'success': True,
                    'user': {
                        'username': username,
                        'profile_pic': session['ra_user']['profile_pic'],
                        'total_points': session['ra_user']['total_points']
                    }
                })
        
        return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to verify credentials'}), 500


@app.route('/auth/ra/logout', methods=['POST'])
def ra_logout():
    """Log out RetroAchievements user"""
    session.pop('ra_user', None)
    return jsonify({'success': True})


@app.route('/api/auth/status')
def auth_status():
    """Get current authentication status"""
    ra_user = session.get('ra_user')
    if ra_user:
        return jsonify({
            'logged_in': True,
            'user': {
                'username': ra_user['username'],
                'profile_pic': ra_user['profile_pic'],
                'total_points': ra_user['total_points']
            }
        })
    return jsonify({'logged_in': False})


# ============================================
# REVIEW SYSTEM API ENDPOINTS
# ============================================

@app.route('/api/reviews/<game_id>', methods=['GET'])
def get_game_reviews(game_id):
    """Get reviews for a game"""
    try:
        game_type = request.args.get('type', 'romhack')
        sort_by = request.args.get('sort', 'helpful')
        filter_type = request.args.get('filter', 'all')
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))
        
        # Get reviews (only with text for display)
        reviews = get_reviews(game_id, game_type, sort_by, filter_type, limit, offset, with_text_only=True)
        # Stats include ALL reviews (even those without text)
        stats = get_review_stats(game_id, game_type)
        
        # Get current user's votes if logged in
        ra_user = session.get('ra_user')
        user_votes = {}
        user_review = None
        
        if ra_user:
            review_ids = [r['id'] for r in reviews]
            if review_ids:
                user_votes = get_user_votes(review_ids, ra_user['username'])
            user_review = has_user_reviewed(game_id, game_type, ra_user['username'])
        
        return jsonify({
            'reviews': reviews,
            'stats': stats,
            'user_votes': user_votes,
            'user_review': user_review
        })
    except Exception as e:
        print(f"Error fetching reviews: {e}")
        return jsonify({
            'reviews': [],
            'stats': {'total': 0, 'positive': 0, 'negative': 0, 'percentage': 0, 'label': 'No Reviews', 'label_class': 'neutral'},
            'user_votes': {},
            'user_review': None,
            'error': str(e)
        })


def fetch_ra_game_progress(username, api_key, ra_game_id):
    """Fetch user's game progress from RetroAchievements"""
    if not ra_game_id:
        return None
    try:
        url = f'https://retroachievements.org/API/API_GetGameInfoAndUserProgress.php?z={username}&y={api_key}&u={username}&g={ra_game_id}'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and 'NumAchievements' in data:
                earned = data.get('NumAwardedToUser', 0) or 0
                total = data.get('NumAchievements', 0) or 0
                percentage = round((earned / total * 100), 1) if total > 0 else 0
                return {
                    'achievements_earned': earned,
                    'achievements_total': total,
                    'completion_percentage': percentage
                }
    except Exception as e:
        print(f"Error fetching RA progress: {e}")
    return None


@app.route('/api/reviews/<game_id>', methods=['POST'])
@limiter.limit("30 per hour")
def post_game_review(game_id):
    """Submit or update a review"""
    try:
        ra_user = session.get('ra_user')
        if not ra_user:
            return jsonify({'success': False, 'error': 'Login required'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
            
        game_type = data.get('type', 'romhack')
        recommended = data.get('recommended')
        review_text = data.get('review_text', '').strip()
        ra_game_id = data.get('ra_game_id')  # Optional RA game ID for progress tracking
        
        if recommended is None:
            return jsonify({'success': False, 'error': 'Please select thumbs up or down'}), 400
        
        # Fetch game progress if RA game ID provided
        game_progress = None
        if ra_game_id and ra_user.get('api_key'):
            game_progress = fetch_ra_game_progress(ra_user['username'], ra_user['api_key'], ra_game_id)
        
        result = submit_review(
            game_id=game_id,
            game_type=game_type,
            ra_username=ra_user['username'],
            ra_user_id=ra_user.get('user_id'),
            ra_profile_pic=ra_user.get('profile_pic'),
            ra_total_points=ra_user.get('total_points', 0),
            recommended=1 if recommended else 0,
            review_text=review_text,
            ra_game_id=ra_game_id,
            game_progress=game_progress
        )
        
        return jsonify(result)
    except Exception as e:
        print(f"Error submitting review: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/api/reviews/batch', methods=['POST'])
def get_batch_review_stats():
    """Get review stats for multiple games at once"""
    data = request.get_json()
    game_ids = data.get('game_ids', [])
    game_type = data.get('type', 'romhack')
    
    if not game_ids:
        return jsonify({})
    
    stats = get_review_stats_batch(game_ids, game_type)
    return jsonify(stats)


@app.route('/api/reviews/vote/<int:review_id>', methods=['POST'])
@limiter.limit("60 per minute")
def vote_review(review_id):
    """Vote on a review (helpful yes/no/funny)"""
    ra_user = session.get('ra_user')
    if not ra_user:
        return jsonify({'success': False, 'error': 'Login required'}), 401
    
    data = request.get_json()
    vote_type = data.get('vote_type', 'yes')
    
    result = vote_helpful(review_id, ra_user['username'], vote_type)
    return jsonify(result)


@app.route('/api/admin/reviews/<int:review_id>', methods=['DELETE'])
@login_required
def admin_delete_review(review_id):
    """Admin: delete a review"""
    result = delete_review(review_id)
    return jsonify({'success': result})


if __name__ == '__main__':
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host='0.0.0.0', port=5000, debug=False)
import sqlite3
import json
import os
from datetime import datetime
import hashlib

DB_PATH = 'requests.db'


def _normalize_consoles(value):
    """Normalize console/platform field into a list of lowercase tokens.

    Supports:
    - "pc"
    - "pc, android"
    - ["pc", "android"]
    - JSON string: "[\"pc\", \"android\"]"
    """
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        parts = list(value)
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            return []

        # JSON list stored as TEXT in sqlite
        if s.startswith('[') and s.endswith(']'):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    parts = parsed
                else:
                    parts = [s]
            except Exception:
                parts = [s]
        elif ',' in s:
            parts = [p.strip() for p in s.split(',')]
        else:
            parts = [s]
    else:
        parts = [str(value)]

    normalized = []
    for p in parts:
        if p is None:
            continue
        token = str(p).strip().lower()
        if token:
            normalized.append(token)

    # de-dupe while preserving order
    seen = set()
    out = []
    for token in normalized:
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Games (Romhacks) table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            console TEXT NOT NULL,
            version TEXT,
            release_date TEXT,
            author TEXT,
            description TEXT,
            features TEXT,
            image_url TEXT,
            screenshots TEXT,
            download_link TEXT,
            base_game TEXT,
            version_region TEXT,
            popular INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Lightweight migration for optional fields
    cursor.execute("PRAGMA table_info(games)")
    game_cols = {row[1] for row in cursor.fetchall()}  # row[1] = column name
    if 'instruction' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN instruction INTEGER DEFAULT 0")
    if 'instruction_text' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN instruction_text TEXT")
    
    # Ports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ports (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            console TEXT NOT NULL,
            version TEXT,
            release_date TEXT,
            author TEXT,
            description TEXT,
            features TEXT,
            image_url TEXT,
            screenshots TEXT,
            download_link TEXT,
            base_game TEXT,
            popular INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("PRAGMA table_info(ports)")
    port_cols = {row[1] for row in cursor.fetchall()}  # row[1] = column name
    if 'instruction' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN instruction INTEGER DEFAULT 0")
    if 'instruction_text' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN instruction_text TEXT")
    
    # Requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            base_game TEXT,
            console TEXT,
            app TEXT,
            patch_page_url TEXT,
            release_date TEXT,
            author TEXT,
            notes TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'new',
            admin_notes TEXT,
            ip_hash TEXT,
            user_agent_hash TEXT
        )
    ''')

    cursor.execute("PRAGMA table_info(requests)")
    request_cols = {row[1] for row in cursor.fetchall()}  # row[1] = column name
    if 'release_date' not in request_cols:
        cursor.execute("ALTER TABLE requests ADD COLUMN release_date TEXT")
    
    # Downloads table for tracking patch downloads
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            ip_hash TEXT NOT NULL,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(game_id, ip_hash)
        )
    ''')
    
    conn.commit()
    conn.close()

def load_games_from_json():
    """Load games from JSON file into database"""
    if not os.path.exists('games.json'):
        return
    
    with open('games.json', 'r') as f:
        games = json.load(f)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for game in games:
        consoles = _normalize_consoles(game.get('console'))
        instruction_text = (
            game.get('instruction_text')
            or game.get('special_instructions')
            or game.get('instructions')
            or game.get('instruction_notes')
        )
        instruction_value = None
        if 'instruction' in game:
            instruction_value = 1 if game.get('instruction') else 0

        cursor.execute('''
            INSERT INTO games (
                id, title, console, version, release_date, author,
                description, features, image_url, screenshots,
                download_link, base_game, version_region, popular,
                instruction, instruction_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                console = excluded.console,
                version = excluded.version,
                release_date = excluded.release_date,
                author = excluded.author,
                description = excluded.description,
                features = excluded.features,
                image_url = excluded.image_url,
                screenshots = excluded.screenshots,
                download_link = excluded.download_link,
                base_game = excluded.base_game,
                version_region = excluded.version_region,
                popular = excluded.popular,
                instruction = COALESCE(excluded.instruction, games.instruction),
                instruction_text = COALESCE(excluded.instruction_text, games.instruction_text)
        ''', (
            game.get('id'),
            game.get('title'),
            json.dumps(consoles) if len(consoles) > 1 else (consoles[0] if consoles else ''),
            game.get('version'),
            game.get('release_date'),
            game.get('author'),
            game.get('description'),
            json.dumps(game.get('features', [])),
            game.get('image_url'),
            json.dumps(game.get('screenshots', [])),
            game.get('download_link'),
            game.get('base_game'),
            game.get('version_region'),
            1 if game.get('popular', False) else 0,
            instruction_value,
            instruction_text,
        ))
    
    conn.commit()
    conn.close()

def load_ports_from_json():
    """Load ports from JSON file into database"""
    if not os.path.exists('ports.json'):
        return
    
    with open('ports.json', 'r') as f:
        ports = json.load(f)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for port in ports:
        consoles = _normalize_consoles(port.get('console'))
        instruction_text = (
            port.get('instruction_text')
            or port.get('special_instructions')
            or port.get('instructions')
            or port.get('instruction_notes')
        )
        instruction_value = None
        if 'instruction' in port:
            instruction_value = 1 if port.get('instruction') else 0

        cursor.execute('''
            INSERT INTO ports (
                id, title, console, version, release_date, author,
                description, features, image_url, screenshots,
                download_link, base_game, popular,
                instruction, instruction_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                console = excluded.console,
                version = excluded.version,
                release_date = excluded.release_date,
                author = excluded.author,
                description = excluded.description,
                features = excluded.features,
                image_url = excluded.image_url,
                screenshots = excluded.screenshots,
                download_link = excluded.download_link,
                base_game = excluded.base_game,
                popular = excluded.popular,
                instruction = COALESCE(excluded.instruction, ports.instruction),
                instruction_text = COALESCE(excluded.instruction_text, ports.instruction_text)
        ''', (
            port.get('id'),
            port.get('title'),
            json.dumps(consoles) if len(consoles) > 1 else (consoles[0] if consoles else ''),
            port.get('version'),
            port.get('release_date'),
            port.get('author'),
            port.get('description'),
            json.dumps(port.get('features', [])),
            port.get('image_url'),
            json.dumps(port.get('screenshots', [])),
            port.get('download_link'),
            port.get('base_game'),
            1 if port.get('popular', False) else 0,
            instruction_value,
            instruction_text,
        ))
    
    conn.commit()
    conn.close()

def get_games():
    """Get all games from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games')
    rows = cursor.fetchall()
    conn.close()
    
    games = []
    for row in rows:
        game = dict(row)
        game['consoles'] = _normalize_consoles(game.get('console'))
        game['features'] = json.loads(game['features'])
        game['screenshots'] = json.loads(game['screenshots'])
        game['popular'] = bool(game['popular'])
        games.append(game)
    
    return games

def get_ports():
    """Get all ports from database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ports')
    rows = cursor.fetchall()
    conn.close()
    
    ports = []
    for row in rows:
        port = dict(row)
        port['consoles'] = _normalize_consoles(port.get('console'))
        port['features'] = json.loads(port['features'])
        port['screenshots'] = json.loads(port['screenshots'])
        port['popular'] = bool(port['popular'])
        ports.append(port)
    
    return ports

def get_game_by_id(game_id):
    """Get a specific game by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games WHERE id = ?', (game_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        game = dict(row)
        game['consoles'] = _normalize_consoles(game.get('console'))
        game['features'] = json.loads(game['features'])
        game['screenshots'] = json.loads(game['screenshots'])
        game['popular'] = bool(game['popular'])
        return game
    return None

def get_port_by_id(port_id):
    """Get a specific port by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ports WHERE id = ?', (port_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        port = dict(row)
        port['consoles'] = _normalize_consoles(port.get('console'))
        port['features'] = json.loads(port['features'])
        port['screenshots'] = json.loads(port['screenshots'])
        port['popular'] = bool(port['popular'])
        return port
    return None

def create_request(title, base_game, console, app, patch_page_url, release_date, author, notes, ip_hash, user_agent_hash):
    """Create a new hack request"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO requests (title, base_game, console, app, patch_page_url, release_date, author, notes, ip_hash, user_agent_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, base_game, console, app, patch_page_url, release_date, author, notes, ip_hash, user_agent_hash))
    
    conn.commit()
    request_id = cursor.lastrowid
    conn.close()
    
    return request_id

def get_requests(status=None):
    """Get all requests, optionally filtered by status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute('SELECT * FROM requests WHERE status = ? ORDER BY submitted_at DESC', (status,))
    else:
        cursor.execute('SELECT * FROM requests ORDER BY submitted_at DESC')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def hash_string(s):
    """Hash a string for anonymization"""
    return hashlib.sha256(s.encode()).hexdigest()[:16]

def track_download(game_id, ip_address):
    """Track a download by game ID and IP address. Returns True if this is a new IP."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hash the IP for privacy
    ip_hash = hash_string(ip_address)
    
    try:
        cursor.execute('''
            INSERT INTO downloads (game_id, ip_hash)
            VALUES (?, ?)
        ''', (game_id, ip_hash))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # This IP has already downloaded this game
        conn.close()
        return False

def get_download_count(game_id):
    """Get the number of unique IPs that have downloaded a game."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(DISTINCT ip_hash) as count
        FROM downloads
        WHERE game_id = ?
    ''', (game_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else 0

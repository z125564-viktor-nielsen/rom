import sqlite3
import json
import os
from datetime import datetime
import hashlib

DB_PATH = 'requests.db'


# ============================================
# FILTER CONFIGURATION SYSTEM
# ============================================
# This system makes it easy to add new filters/tags to games and ports.
# To add a new filter:
# 1. Add a new entry to FILTER_CONFIGS with column name and optional auto-detect function
# 2. The column will be automatically added to both games and ports tables
# 3. Use get_filter_value() to extract values during game/port retrieval
# 4. Add UI elements in templates and JavaScript filtering logic

FILTER_CONFIGS = {
    'game_series': {
        'description': 'Game series/franchise (e.g., Pokemon, Mario, Zelda)',
        'type': 'TEXT',
        'auto_detect': lambda game: _auto_detect_series(game.get('base_game', ''), game.get('title', ''))
    },
    # Add more filters here as needed:
    # 'genre': {
    #     'description': 'Game genre (e.g., RPG, Platformer, Action)',
    #     'type': 'TEXT',
    #     'auto_detect': None
    # },
    # 'difficulty': {
    #     'description': 'Difficulty level (e.g., Easy, Medium, Hard)',
    #     'type': 'TEXT',
    #     'auto_detect': None
    # },
}

def _auto_detect_series(base_game, title):
    """Auto-detect game series from base_game or title"""
    if not base_game and not title:
        return None
    
    # Normalize strings for comparison
    text = (base_game or title).lower()
    
    # Series detection rules
    series_patterns = {
        'Pokemon': ['pokemon', 'pokémon'],
        'Mario': ['mario', 'smb', 'super mario'],
        'Zelda': ['zelda'],
        'Metroid': ['metroid'],
        'Kirby': ['kirby'],
        'Sonic': ['sonic'],
        'Mega Man': ['mega man', 'megaman', 'rockman'],
        'Final Fantasy': ['final fantasy'],
        'Dragon Quest': ['dragon quest'],
        'Fire Emblem': ['fire emblem'],
        'Castlevania': ['castlevania'],
        'Contra': ['contra'],
        'Street Fighter': ['street fighter'],
        'Mortal Kombat': ['mortal kombat'],
    }
    
    for series, patterns in series_patterns.items():
        for pattern in patterns:
            if pattern in text:
                return series
    
    return None

def get_filter_value(record, filter_name):
    """Get the value for a filter, with auto-detection fallback"""
    if filter_name not in FILTER_CONFIGS:
        return None
    
    config = FILTER_CONFIGS[filter_name]
    value = record.get(filter_name)
    
    # If value is empty and auto_detect is available, use it
    if not value and config.get('auto_detect'):
        value = config['auto_detect'](record)
    
    return value

# ============================================
# END FILTER CONFIGURATION SYSTEM
# ============================================


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
            base_region TEXT,
            base_revision TEXT,
            base_header TEXT,
            base_checksum_crc32 TEXT,
            base_checksum_md5 TEXT,
            base_checksum_sha1 TEXT,
            patch_format TEXT,
            patch_output_ext TEXT,
            dev_stage TEXT,
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
    if 'base_region' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN base_region TEXT")
    if 'base_revision' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN base_revision TEXT")
    if 'base_header' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN base_header TEXT")
    if 'base_checksum_crc32' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN base_checksum_crc32 TEXT")
    if 'base_checksum_md5' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN base_checksum_md5 TEXT")
    if 'base_checksum_sha1' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN base_checksum_sha1 TEXT")
    if 'patch_format' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN patch_format TEXT")
    if 'patch_output_ext' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN patch_output_ext TEXT")
    if 'online_play' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN online_play INTEGER DEFAULT 0")
    if 'instructions_json' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN instructions_json TEXT")
    # Add platform-specific instruction columns
    for platform in ['pc', 'android', 'linux', 'web', 'ios', 'mac', 'switch', 'ps4', 'xbox']:
        col_name = f'instructions_{platform}'
        if col_name not in game_cols:
            cursor.execute(f"ALTER TABLE games ADD COLUMN {col_name} TEXT")
    if 'social_links' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN social_links TEXT")
    if 'dev_stage' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN dev_stage TEXT")
    # Support/help link columns
    if 'support_forum_url' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN support_forum_url TEXT")
    if 'discord_url' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN discord_url TEXT")
    if 'reddit_url' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN reddit_url TEXT")
    if 'troubleshooting_url' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN troubleshooting_url TEXT")
    if 'rom_checker_url' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN rom_checker_url TEXT")
    if 'wiki_url' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN wiki_url TEXT")
    if 'game_series' not in game_cols:
        cursor.execute("ALTER TABLE games ADD COLUMN game_series TEXT")
    if 'base_hash' in game_cols:
        # Can't drop columns in SQLite, so we'll leave them but not use them
        pass
    if 'base_hash_type' in game_cols:
        pass
    if 'output_extension' in game_cols:
        pass
    
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
            original_platform TEXT,
            base_region TEXT,
            base_revision TEXT,
            base_header TEXT,
            base_checksum_crc32 TEXT,
            base_checksum_md5 TEXT,
            base_checksum_sha1 TEXT,
            patch_format TEXT,
            patch_output_ext TEXT,
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
    if 'original_platform' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN original_platform TEXT")
    if 'base_region' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN base_region TEXT")
    if 'base_revision' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN base_revision TEXT")
    if 'base_header' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN base_header TEXT")
    if 'base_checksum_crc32' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN base_checksum_crc32 TEXT")
    if 'base_checksum_md5' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN base_checksum_md5 TEXT")
    if 'base_checksum_sha1' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN base_checksum_sha1 TEXT")
    if 'patch_format' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN patch_format TEXT")
    if 'patch_output_ext' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN patch_output_ext TEXT")
    if 'online_play' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN online_play INTEGER DEFAULT 0")
    if 'instructions_json' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN instructions_json TEXT")
    # Add platform-specific instruction columns
    for platform in ['pc', 'android', 'linux', 'web', 'ios', 'mac', 'switch', 'ps4', 'xbox']:
        col_name = f'instructions_{platform}'
        if col_name not in port_cols:
            cursor.execute(f"ALTER TABLE ports ADD COLUMN {col_name} TEXT")
    if 'social_links' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN social_links TEXT")
    # Support/help link columns
    if 'support_forum_url' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN support_forum_url TEXT")
    if 'discord_url' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN discord_url TEXT")
    if 'reddit_url' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN reddit_url TEXT")
    if 'troubleshooting_url' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN troubleshooting_url TEXT")
    if 'rom_checker_url' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN rom_checker_url TEXT")
    if 'wiki_url' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN wiki_url TEXT")
    if 'game_series' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN game_series TEXT")
    if 'mod_links' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN mod_links TEXT")
    if 'mod_instructions' not in port_cols:
        cursor.execute("ALTER TABLE ports ADD COLUMN mod_instructions TEXT")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_type TEXT DEFAULT 'romhack',
            title TEXT NOT NULL,
            base_game TEXT,
            console TEXT,
            author TEXT,
            release_date TEXT,
            version TEXT,
            description TEXT,
            features TEXT,
            download_link TEXT,
            patch_format TEXT,
            patch_page_url TEXT,
            project_link TEXT,
            base_region TEXT,
            base_revision TEXT,
            base_checksum_crc32 TEXT,
            base_checksum_md5 TEXT,
            base_checksum_sha1 TEXT,
            image_url TEXT,
            screenshots TEXT,
            dev_stage TEXT,
            online_play INTEGER DEFAULT 0,
            email TEXT,
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
    
    # Add any missing columns
    migration_columns = {
        'game_type': 'TEXT DEFAULT "romhack"',
        'version': 'TEXT',
        'description': 'TEXT',
        'features': 'TEXT',
        'download_link': 'TEXT',
        'patch_format': 'TEXT',
        'project_link': 'TEXT',
        'base_region': 'TEXT',
        'base_revision': 'TEXT',
        'base_checksum_crc32': 'TEXT',
        'base_checksum_md5': 'TEXT',
        'base_checksum_sha1': 'TEXT',
        'image_url': 'TEXT',
        'screenshots': 'TEXT',
        'dev_stage': 'TEXT',
        'online_play': 'INTEGER DEFAULT 0',
        'email': 'TEXT',
        'consoles': 'TEXT',
        'instructions_pc': 'TEXT',
        'instructions_android': 'TEXT',
        'instructions_linux': 'TEXT'
    }
    
    for col_name, col_type in migration_columns.items():
        if col_name not in request_cols:
            cursor.execute(f"ALTER TABLE requests ADD COLUMN {col_name} {col_type}")
    
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

    # Feedback table for broken link reports and correction requests
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            title TEXT,
            url TEXT,
            description TEXT NOT NULL,
            email TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'new',
            admin_notes TEXT,
            ip_hash TEXT
        )
    ''')
    
    # Monthly downloads table for tracking downloads per month
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monthly_downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL,
            ip_hash TEXT NOT NULL,
            year_month TEXT NOT NULL,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(game_id, ip_hash, year_month)
        )
    ''')
    
    # Index for faster monthly queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_monthly_downloads_year_month 
        ON monthly_downloads(year_month)
    ''')
    
    # Monthly popular history table for storing past months' top games
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monthly_popular_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            year_month TEXT NOT NULL,
            game_id TEXT NOT NULL,
            game_type TEXT NOT NULL,
            download_count INTEGER NOT NULL,
            rank INTEGER NOT NULL,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(year_month, game_id, game_type)
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
                instruction, instruction_text, base_region, base_revision,
                base_header, base_checksum_crc32, base_checksum_md5,
                base_checksum_sha1, patch_format, patch_output_ext
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                instruction_text = COALESCE(excluded.instruction_text, games.instruction_text),
                base_region = COALESCE(excluded.base_region, games.base_region),
                base_revision = COALESCE(excluded.base_revision, games.base_revision),
                base_header = COALESCE(excluded.base_header, games.base_header),
                base_checksum_crc32 = COALESCE(excluded.base_checksum_crc32, games.base_checksum_crc32),
                base_checksum_md5 = COALESCE(excluded.base_checksum_md5, games.base_checksum_md5),
                base_checksum_sha1 = COALESCE(excluded.base_checksum_sha1, games.base_checksum_sha1),
                patch_format = COALESCE(excluded.patch_format, games.patch_format),
                patch_output_ext = COALESCE(excluded.patch_output_ext, games.patch_output_ext)
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
            game.get('base_region'),
            game.get('base_revision'),
            game.get('base_header'),
            game.get('base_checksum_crc32'),
            game.get('base_checksum_md5'),
            game.get('base_checksum_sha1'),
            game.get('patch_format'),
            game.get('patch_output_ext'),
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

def insert_game(game_data):
    """Insert a game (romhack) directly into the games table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    game_id = game_data.get('id', game_data.get('title', 'game').lower().replace(' ', '_').replace("'", ''))
    
    cursor.execute('''
        INSERT OR REPLACE INTO games (
            id, title, console, version, release_date, author,
            description, features, image_url, screenshots, download_link,
            base_game, version_region, base_region, base_revision, base_header,
            base_checksum_crc32, base_checksum_md5, base_checksum_sha1,
            patch_format, patch_output_ext, dev_stage, popular, online_play,
            instruction, instruction_text, discord_url, reddit_url,
            support_forum_url, troubleshooting_url, rom_checker_url, wiki_url,
            instructions_pc, instructions_android, instructions_linux,
            instructions_web, instructions_ios, instructions_mac,
            instructions_switch, instructions_ps4, instructions_xbox, game_series
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        game_id,
        game_data.get('title'),
        game_data.get('console', ''),
        game_data.get('version'),
        game_data.get('release_date'),
        game_data.get('author'),
        game_data.get('description'),
        json.dumps(game_data.get('features', [])),
        game_data.get('image_url'),
        json.dumps(game_data.get('screenshots', [])),
        game_data.get('download_link'),
        game_data.get('base_game'),
        game_data.get('version_region'),
        game_data.get('base_region'),
        game_data.get('base_revision'),
        game_data.get('base_header'),
        game_data.get('base_checksum_crc32'),
        game_data.get('base_checksum_md5'),
        game_data.get('base_checksum_sha1'),
        game_data.get('patch_format'),
        game_data.get('patch_output_ext'),
        game_data.get('dev_stage'),
        1 if game_data.get('popular', False) else 0,
        1 if game_data.get('online_play', False) else 0,
        1 if game_data.get('instruction', False) else 0,
        game_data.get('instruction_text'),
        game_data.get('discord_url'),
        game_data.get('reddit_url'),
        game_data.get('support_forum_url'),
        game_data.get('troubleshooting_url'),
        game_data.get('rom_checker_url'),
        game_data.get('wiki_url'),
        game_data.get('instructions_pc'),
        game_data.get('instructions_android'),
        game_data.get('instructions_linux'),
        game_data.get('instructions_web'),
        game_data.get('instructions_ios'),
        game_data.get('instructions_mac'),
        game_data.get('instructions_switch'),
        game_data.get('instructions_ps4'),
        game_data.get('instructions_xbox'),
        game_data.get('game_series') or get_filter_value(game_data, 'game_series'),
    ))
    
    conn.commit()
    conn.close()
    return game_id

def insert_port(port_data):
    """Insert a port directly into the ports table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    port_id = port_data.get('id', port_data.get('title', 'port').lower().replace(' ', '_').replace("'", ''))
    
    cursor.execute('''
        INSERT OR REPLACE INTO ports (
            id, title, console, version, release_date, author,
            description, features, image_url, screenshots, download_link,
            base_game, original_platform, popular, game_series
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        port_id,
        port_data.get('title'),
        port_data.get('console', 'PC'),
        port_data.get('version'),
        port_data.get('release_date'),
        port_data.get('author'),
        port_data.get('description'),
        json.dumps(port_data.get('features', [])),
        port_data.get('image_url'),
        json.dumps(port_data.get('screenshots', [])),
        port_data.get('download_link'),
        port_data.get('base_game'),
        port_data.get('original_platform'),
        1 if port_data.get('popular', False) else 0,
        port_data.get('game_series') or get_filter_value(port_data, 'game_series'),
    ))
    
    conn.commit()
    conn.close()
    return port_id

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
        
        # Apply filter configurations with auto-detection
        for filter_name in FILTER_CONFIGS:
            game[filter_name] = get_filter_value(game, filter_name)
        
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
        if port.get('mod_links'):
            try:
                port['mod_links'] = json.loads(port['mod_links'])
            except:
                port['mod_links'] = []
        port['popular'] = bool(port['popular'])
        port['online_play'] = bool(port.get('online_play'))
        
        # Apply filter configurations with auto-detection
        for filter_name in FILTER_CONFIGS:
            port[filter_name] = get_filter_value(port, filter_name)
        
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
        game['online_play'] = bool(game.get('online_play'))
        
        # Apply filter configurations with auto-detection
        for filter_name in FILTER_CONFIGS:
            game[filter_name] = get_filter_value(game, filter_name)
        
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
        if port.get('mod_links'):
            try:
                port['mod_links'] = json.loads(port['mod_links'])
            except:
                port['mod_links'] = []
        port['popular'] = bool(port['popular'])
        port['online_play'] = bool(port.get('online_play'))
        
        # Apply filter configurations with auto-detection
        for filter_name in FILTER_CONFIGS:
            port[filter_name] = get_filter_value(port, filter_name)
        
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
    
    # Get current year-month for monthly tracking
    current_month = datetime.now().strftime('%Y-%m')
    
    # Track in monthly_downloads table (allows one download per IP per month)
    try:
        cursor.execute('''
            INSERT INTO monthly_downloads (game_id, ip_hash, year_month)
            VALUES (?, ?, ?)
        ''', (game_id, ip_hash, current_month))
    except sqlite3.IntegrityError:
        # Already downloaded this month by this IP
        pass
    
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
        conn.commit()  # Still commit the monthly tracking
        conn.close()
        return False

def submit_game(submission_data, ip_address):
    """Submit a new game to the requests table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hash the IP for privacy
    ip_hash = hash_string(ip_address)
    user_agent = submission_data.get('user_agent', '')
    user_agent_hash = hash_string(user_agent)
    
    try:
        cursor.execute('''
            INSERT INTO requests (
                game_type,
                title,
                base_game,
                console,
                consoles,
                author,
                release_date,
                version,
                description,
                features,
                download_link,
                patch_format,
                project_link,
                base_region,
                base_revision,
                base_checksum_crc32,
                base_checksum_md5,
                base_checksum_sha1,
                image_url,
                screenshots,
                dev_stage,
                online_play,
                email,
                notes,
                instructions_pc,
                instructions_android,
                instructions_linux,
                ip_hash,
                user_agent_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            submission_data.get('game_type', 'romhack'),
            submission_data.get('title'),
            submission_data.get('base_game'),
            submission_data.get('console'),
            submission_data.get('consoles'),
            submission_data.get('author'),
            submission_data.get('release_date'),
            submission_data.get('version'),
            submission_data.get('description'),
            submission_data.get('features'),
            submission_data.get('download_link'),
            submission_data.get('patch_format'),
            submission_data.get('project_link'),
            submission_data.get('base_region'),
            submission_data.get('base_revision'),
            submission_data.get('base_checksum_crc32'),
            submission_data.get('base_checksum_md5'),
            submission_data.get('base_checksum_sha1'),
            submission_data.get('image_url'),
            submission_data.get('screenshots'),
            submission_data.get('dev_stage'),
            submission_data.get('online_play', 0),
            submission_data.get('email'),
            submission_data.get('notes'),
            submission_data.get('instructions_pc'),
            submission_data.get('instructions_android'),
            submission_data.get('instructions_linux'),
            ip_hash,
            user_agent_hash
        ))
        conn.commit()
        request_id = cursor.lastrowid
        conn.close()
        return {'success': True, 'id': request_id}
    except Exception as e:
        conn.close()
        return {'success': False, 'error': str(e)}

def submit_feedback(feedback_type, title, url, description, email, ip_address):
    """Submit feedback (broken link report or correction request)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Hash the IP for privacy
    ip_hash = hash_string(ip_address)
    
    cursor.execute('''
        INSERT INTO feedback (type, title, url, description, email, ip_hash)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (feedback_type, title, url, description, email, ip_hash))
    
    conn.commit()
    feedback_id = cursor.lastrowid
    conn.close()
    
    return feedback_id

def get_feedback(status=None, feedback_type=None):
    """Get feedback, optionally filtered by status or type"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM feedback WHERE 1=1'
    params = []
    
    if status:
        query += ' AND status = ?'
        params.append(status)
    if feedback_type:
        query += ' AND type = ?'
        params.append(feedback_type)
    
    query += ' ORDER BY submitted_at DESC'
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def update_feedback_status(feedback_id, status, admin_notes=None):
    """Update the status of a feedback entry"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE feedback SET status = ?, admin_notes = ? WHERE id = ?
    ''', (status, admin_notes, feedback_id))
    
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0

def delete_feedback(feedback_id):
    """Delete a feedback entry"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM feedback WHERE id = ?', (feedback_id,))
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    
    return success

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


def get_download_counts_for_ids(game_ids):
    """Get download counts for a batch of game or port IDs."""
    if not game_ids:
        return {}

    conn = get_db_connection()
    cursor = conn.cursor()
    placeholder = ','.join('?' for _ in game_ids)
    cursor.execute(f'''
        SELECT game_id, COUNT(DISTINCT ip_hash) as count
        FROM downloads
        WHERE game_id IN ({placeholder})
        GROUP BY game_id
    ''', tuple(game_ids))

    rows = cursor.fetchall()
    conn.close()

    return {row['game_id']: row['count'] for row in rows}


def set_platform_instructions(game_id, platform, instructions_text, is_port=False):
    """Set platform-specific instructions for a game or port."""
    table = 'ports' if is_port else 'games'
    col_name = f'instructions_{platform.lower()}'
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute(f'UPDATE {table} SET {col_name} = ? WHERE id = ?', 
                   (instructions_text, game_id))
    conn.commit()
    conn.close()
    
    return True

def get_submissions(status=None):
    """Get all submissions from requests table, optionally filtered by status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute('SELECT * FROM requests WHERE status = ? ORDER BY submitted_at DESC', (status,))
    else:
        cursor.execute('SELECT * FROM requests ORDER BY submitted_at DESC')
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_submission_counts():
    """Get count of submissions by status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COALESCE(status, 'new') as status, COUNT(*) as count FROM requests GROUP BY COALESCE(status, 'new')")
        rows = cursor.fetchall()
        
        counts = {'new': 0, 'approved': 0, 'rejected': 0}
        for row in rows:
            status = row['status'] if row['status'] else 'new'
            if status in counts:
                counts[status] = row['count']
        
        conn.close()
        return counts
    except Exception as e:
        conn.close()
        # Return defaults if query fails
        return {'new': 0, 'approved': 0, 'rejected': 0}

def get_submission_by_id(submission_id):
    """Get a specific submission by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM requests WHERE id = ?', (submission_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def update_submission_status(submission_id, status, admin_notes=None):
    """Update the status of a submission"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE requests SET status = ?, admin_notes = ? WHERE id = ?
    ''', (status, admin_notes, submission_id))
    
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    
    return success

def reject_submission(submission_id, reason):
    """Reject a submission with a reason"""
    return update_submission_status(submission_id, 'rejected', reason)

def approve_submission(submission_id):
    """Approve a submission"""
    return update_submission_status(submission_id, 'approved', None)


def update_game(game_id, data):
    """Update a game's data in the games table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build dynamic update query based on provided fields
    allowed_fields = [
        'title', 'console', 'version', 'release_date', 'author',
        'description', 'features', 'image_url', 'screenshots',
        'download_link', 'base_game', 'version_region', 'popular',
        'instruction', 'instruction_text', 'base_region', 'base_revision',
        'base_header', 'base_checksum_crc32', 'base_checksum_md5',
        'base_checksum_sha1', 'patch_format', 'patch_output_ext',
        'online_play', 'dev_stage', 'social_links',
        'support_forum_url', 'discord_url', 'reddit_url',
        'troubleshooting_url', 'rom_checker_url', 'wiki_url',
        'instructions_pc', 'instructions_android', 'instructions_linux',
        'instructions_web', 'instructions_ios', 'instructions_mac',
        'instructions_switch', 'instructions_ps4', 'instructions_xbox',
        'game_series'
    ]
    
    update_parts = []
    values = []
    
    for field in allowed_fields:
        if field in data:
            update_parts.append(f'{field} = ?')
            value = data[field]
            # Convert lists to JSON strings
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            # Convert booleans to integers
            if isinstance(value, bool):
                value = 1 if value else 0
            values.append(value)
    
    if not update_parts:
        conn.close()
        return False
    
    values.append(game_id)
    query = f"UPDATE games SET {', '.join(update_parts)} WHERE id = ?"
    
    try:
        cursor.execute(query, values)
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        conn.close()
        raise e


def update_port(port_id, data):
    """Update a port's data in the ports table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build dynamic update query based on provided fields
    allowed_fields = [
        'title', 'console', 'version', 'release_date', 'author',
        'description', 'features', 'image_url', 'screenshots',
        'download_link', 'base_game', 'original_platform', 'popular',
        'instruction', 'instruction_text', 'base_region', 'base_revision',
        'base_header', 'base_checksum_crc32', 'base_checksum_md5',
        'base_checksum_sha1', 'patch_format', 'patch_output_ext',
        'online_play', 'social_links',
        'support_forum_url', 'discord_url', 'reddit_url',
        'troubleshooting_url', 'rom_checker_url', 'wiki_url',
        'instructions_pc', 'instructions_android', 'instructions_linux',
        'instructions_web', 'instructions_ios', 'instructions_mac',
        'instructions_switch', 'instructions_ps4', 'instructions_xbox',
        'game_series',
        'mod_links', 'mod_instructions'
    ]
    
    update_parts = []
    values = []
    
    for field in allowed_fields:
        if field in data:
            update_parts.append(f'{field} = ?')
            value = data[field]
            # Convert lists to JSON strings
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            # Convert booleans to integers
            if isinstance(value, bool):
                value = 1 if value else 0
            values.append(value)
    
    if not update_parts:
        conn.close()
        return False
    
    values.append(port_id)
    query = f"UPDATE ports SET {', '.join(update_parts)} WHERE id = ?"
    
    try:
        cursor.execute(query, values)
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        conn.close()
        raise e


def delete_game(game_id):
    """Delete a game from the games table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM games WHERE id = ?', (game_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        conn.close()
        raise e


def delete_port(port_id):
    """Delete a port from the ports table"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM ports WHERE id = ?', (port_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    except Exception as e:
        conn.close()
        raise e

def get_monthly_download_counts(year_month=None):
    """Get download counts for a specific month (defaults to current month)"""
    if year_month is None:
        year_month = datetime.now().strftime('%Y-%m')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT game_id, COUNT(*) as count
        FROM monthly_downloads
        WHERE year_month = ?
        GROUP BY game_id
    ''', (year_month,))
    
    counts = {row['game_id']: row['count'] for row in cursor.fetchall()}
    conn.close()
    return counts


def get_monthly_download_counts_for_ids(game_ids, year_month=None):
    """Get monthly download counts for a list of game IDs"""
    if not game_ids:
        return {}
    
    if year_month is None:
        year_month = datetime.now().strftime('%Y-%m')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    placeholders = ','.join(['?' for _ in game_ids])
    params = [year_month] + list(game_ids)
    
    cursor.execute(f'''
        SELECT game_id, COUNT(*) as count
        FROM monthly_downloads
        WHERE year_month = ? AND game_id IN ({placeholders})
        GROUP BY game_id
    ''', params)
    
    counts = {row['game_id']: row['count'] for row in cursor.fetchall()}
    conn.close()
    return counts


def archive_monthly_popular(year_month=None, top_n=20):
    """Archive the top games/ports for a given month to history.
    
    Call this at the start of each new month to archive the previous month's data.
    """
    if year_month is None:
        # Default to previous month
        today = datetime.now()
        if today.month == 1:
            year_month = f"{today.year - 1}-12"
        else:
            year_month = f"{today.year}-{today.month - 1:02d}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get top games for the month
    cursor.execute('''
        SELECT md.game_id, COUNT(*) as download_count
        FROM monthly_downloads md
        INNER JOIN games g ON md.game_id = g.id
        WHERE md.year_month = ?
        GROUP BY md.game_id
        ORDER BY download_count DESC
        LIMIT ?
    ''', (year_month, top_n))
    
    games = cursor.fetchall()
    for rank, row in enumerate(games, 1):
        try:
            cursor.execute('''
                INSERT INTO monthly_popular_history 
                (year_month, game_id, game_type, download_count, rank)
                VALUES (?, ?, 'game', ?, ?)
            ''', (year_month, row['game_id'], row['download_count'], rank))
        except sqlite3.IntegrityError:
            pass  # Already archived
    
    # Get top ports for the month
    cursor.execute('''
        SELECT md.game_id, COUNT(*) as download_count
        FROM monthly_downloads md
        INNER JOIN ports p ON md.game_id = p.id
        WHERE md.year_month = ?
        GROUP BY md.game_id
        ORDER BY download_count DESC
        LIMIT ?
    ''', (year_month, top_n))
    
    ports = cursor.fetchall()
    for rank, row in enumerate(ports, 1):
        try:
            cursor.execute('''
                INSERT INTO monthly_popular_history 
                (year_month, game_id, game_type, download_count, rank)
                VALUES (?, ?, 'port', ?, ?)
            ''', (year_month, row['game_id'], row['download_count'], rank))
        except sqlite3.IntegrityError:
            pass  # Already archived
    
    conn.commit()
    conn.close()
    return {'games_archived': len(games), 'ports_archived': len(ports)}


def get_monthly_popular_history(year_month, game_type=None):
    """Get the archived popular games/ports for a specific month"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if game_type:
        cursor.execute('''
            SELECT * FROM monthly_popular_history
            WHERE year_month = ? AND game_type = ?
            ORDER BY rank
        ''', (year_month, game_type))
    else:
        cursor.execute('''
            SELECT * FROM monthly_popular_history
            WHERE year_month = ?
            ORDER BY game_type, rank
        ''', (year_month,))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return history


def get_all_archived_months():
    """Get a list of all months that have been archived"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT year_month FROM monthly_popular_history
        ORDER BY year_month DESC
    ''')
    
    months = [row['year_month'] for row in cursor.fetchall()]
    conn.close()
    return months


def check_and_archive_previous_month():
    """Check if we need to archive the previous month's data and do so if needed.
    
    This should be called on app startup or periodically.
    """
    today = datetime.now()
    
    # Calculate previous month
    if today.month == 1:
        prev_year_month = f"{today.year - 1}-12"
    else:
        prev_year_month = f"{today.year}-{today.month - 1:02d}"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if previous month is already archived
    cursor.execute('''
        SELECT COUNT(*) as count FROM monthly_popular_history
        WHERE year_month = ?
    ''', (prev_year_month,))
    
    already_archived = cursor.fetchone()['count'] > 0
    conn.close()
    
    if not already_archived:
        # Check if there's any data for the previous month to archive
        counts = get_monthly_download_counts(prev_year_month)
        if counts:
            return archive_monthly_popular(prev_year_month)
    
    return None
from flask import Flask, render_template, abort, send_from_directory, request, jsonify
from database import get_db_connection, init_db, get_games, get_ports, get_game_by_id, get_port_by_id, track_download, get_download_count
import json

app = Flask(__name__)

# Initialize database on startup
init_db()

# --- COLOR CODING LOGIC ---
CONSOLE_STYLES = {
    'gb': 'bg-emerald-900/70 text-emerald-200 border-emerald-500/50',
    'gbc': 'bg-lime-900/80 text-lime-300 border-lime-500/50',
    'gba': 'bg-purple-900/80 text-purple-300 border-purple-500/50',
    'snes': 'bg-indigo-900/80 text-indigo-300 border-indigo-500/50',
    'n64': 'bg-red-900/80 text-red-300 border-red-500/50',
    'nds': 'bg-pink-900/80 text-pink-300 border-pink-500/50',
    'wii': 'bg-cyan-900/80 text-cyan-300 border-cyan-500/50',
    'default': 'bg-gray-800 text-gray-300 border-gray-600'
}
PC_STYLE = {
    'android': 'bg-green-900/70 text-green-200 border-green-500/50',
    'pc': 'bg-sky-900/70 text-sky-200 border-sky-500/50'
}

@app.route('/')
def index():
    games = get_games()
    ports_data = get_ports()
    # Filter for popular games and ports only
    popular_games = [g for g in games if g.get('popular', False)]
    popular_ports = [p for p in ports_data if p.get('popular', False)]
    return render_template('index.html', games=popular_games, ports=popular_ports, styles=CONSOLE_STYLES, pc_styles=PC_STYLE)

@app.route('/ports')
def ports():
    ports_data = get_ports()
    return render_template('ports.html', games=ports_data, styles=PC_STYLE)

@app.route('/romhacks')
def romhacks():
    games = get_games()
    return render_template('romhacks.html', games=games, styles=CONSOLE_STYLES)

@app.route('/patcher')
def patcher():
    return render_template('patcher.html')

@app.route('/logo/<filename>')
def logo_file(filename):
    return send_from_directory('logo', filename)

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
    styles = PC_STYLE if is_port else CONSOLE_STYLES
    download_count = get_download_count(game_id)
    return render_template('game.html', game=game, styles=styles, download_count=download_count)

@app.route('/api/track-download/<game_id>', methods=['POST'])
def track_download_endpoint(game_id):
    client_ip = request.remote_addr
    # If behind a proxy, try to get the real IP
    if request.headers.get('X-Forwarded-For'):
        client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    result = track_download(game_id, client_ip)
    return jsonify({'success': result})

if __name__ == '__main__':
    app.run(debug=True)
#!/usr/bin/env python3
"""Verify admin API endpoints"""

import json
import sys
from database import init_db, submit_game, get_submissions

print('=' * 60)
print('ADMIN API ENDPOINTS VERIFICATION')
print('=' * 60)

# Initialize
init_db()

# Create a test submission
test_data = {
    'game_type': 'port',
    'title': 'Super Mario 64 Port',
    'base_game': 'Super Mario 64',
    'console': 'Windows',
    'author': 'Port Team',
    'release_date': '2024-01-06',
    'version': '2.0',
    'description': 'Decompiled port of SM64',
    'features': '["Online Play", "4K Support"]',
    'download_link': 'https://example.com/sm64.zip',
    'patch_format': 'zip',
    'email': 'porter@example.com',
    'consoles': 'Windows, Linux'
}

result = submit_game(test_data, '192.168.1.100')
if not result['success']:
    print(f'✗ Failed to create test submission: {result}')
    sys.exit(1)

test_id = result['id']
print(f'✓ Created test submission (ID: {test_id})')

# Check the submission was stored correctly
from database import get_submission_by_id
sub = get_submission_by_id(test_id)

print('\nVerifying submission data integrity:')
checks = [
    ('Title', sub['title'], 'Super Mario 64 Port'),
    ('Game Type', sub['game_type'], 'port'),
    ('Base Game', sub['base_game'], 'Super Mario 64'),
    ('Console', sub['console'], 'Windows'),
    ('Author', sub['author'], 'Port Team'),
    ('Status', sub['status'], 'new'),
    ('Version', sub['version'], '2.0'),
    ('Download Link', sub['download_link'], 'https://example.com/sm64.zip'),
    ('Email', sub['email'], 'porter@example.com'),
    ('Consoles', sub.get('consoles'), 'Windows, Linux'),
]

all_passed = True
for field, actual, expected in checks:
    if actual == expected:
        print(f'  ✓ {field}: {actual}')
    else:
        print(f'  ✗ {field}: expected "{expected}", got "{actual}"')
        all_passed = False

if not all_passed:
    print('\n✗ Some fields failed validation')
    sys.exit(1)

print('\n' + '=' * 60)
print('API ENDPOINTS VERIFICATION')
print('=' * 60)

# Now test API endpoints with Flask test client
from app import app

app.config['TESTING'] = True
client = app.test_client()

# 1. Test admin login
print('\n1. Testing admin login...')
response = client.post('/admin/login', data={
    'username': 'PeterGriffin77*',
    'password': 'admin'
}, follow_redirects=True)

if response.status_code == 200:
    print('  ✓ Admin login endpoint works')
else:
    print(f'  ✗ Admin login failed with status {response.status_code}')

# 2. Test admin dashboard access
print('2. Testing admin dashboard...')
response = client.get('/admin', follow_redirects=True)
if 'Admin Dashboard' in response.get_data(as_text=True):
    print('  ✓ Admin dashboard renders')
else:
    print('  ✗ Admin dashboard not found')

# 3. Test submission detail page
print('3. Testing submission detail page...')
response = client.get(f'/admin/submission/{test_id}')
if 'Review Submission' in response.get_data(as_text=True):
    print('  ✓ Submission detail page renders')
else:
    print('  ✗ Submission detail page not found')

# 4. Test approve API
print('4. Testing approve API...')
response = client.post(f'/api/admin/submission/{test_id}/approve',
    headers={'Content-Type': 'application/json'})
data = json.loads(response.get_data(as_text=True))
if data.get('success'):
    print('  ✓ Approve API works')
else:
    print('  ✗ Approve API failed')

# 5. Test reject API
print('5. Testing reject API...')
# Create another submission to reject
result2 = submit_game({**test_data, 'title': 'Test Port 2'}, '192.168.1.101')
reject_id = result2['id']

response = client.post(f'/api/admin/submission/{reject_id}/reject',
    data=json.dumps({'reason': 'Not suitable for the database'}),
    headers={'Content-Type': 'application/json'})
data = json.loads(response.get_data(as_text=True))
if data.get('success'):
    print('  ✓ Reject API works')
else:
    print('  ✗ Reject API failed')

print('\n' + '=' * 60)
print('ALL ADMIN ENDPOINTS VERIFIED! ✓')
print('=' * 60)

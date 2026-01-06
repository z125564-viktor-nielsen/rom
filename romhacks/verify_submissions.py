#!/usr/bin/env python3
"""Verify submission and admin functionality"""

import sys
from database import (
    init_db, get_submissions, get_submission_by_id, 
    submit_game, approve_submission, reject_submission
)

print('=' * 60)
print('SUBMISSION & ADMIN VERIFICATION')
print('=' * 60)

# 1. Database Check
try:
    init_db()
    print('✓ Database initialization')
except Exception as e:
    print(f'✗ Database initialization: {e}')
    sys.exit(1)

# 2. Submission Functions Check
try:
    test_data = {
        'game_type': 'romhack',
        'title': 'Test Hack',
        'base_game': 'Pokemon FireRed',
        'console': 'GBA',
        'author': 'Test Author',
        'release_date': '2024-01-06',
        'version': '1.0',
        'description': 'Test description',
        'features': '["Online Play"]',
        'download_link': 'https://example.com/test.zip',
        'patch_format': 'ips',
        'email': 'test@example.com'
    }
    
    result = submit_game(test_data, '192.168.1.1')
    if result['success']:
        test_id = result['id']
        print(f'✓ Submit game function (ID: {test_id})')
    else:
        print(f'✗ Submit game function: {result.get("error")}')
        sys.exit(1)
except Exception as e:
    print(f'✗ Submit game function: {e}')
    sys.exit(1)

# 3. Retrieval Functions Check
try:
    all_subs = get_submissions()
    print(f'✓ Get all submissions ({len(all_subs)} total)')
    assert len(all_subs) >= 1, 'No submissions found'
except Exception as e:
    print(f'✗ Get all submissions: {e}')
    sys.exit(1)

# 4. Status Filtering Check
try:
    new_subs = get_submissions('new')
    print(f'✓ Filter by status "new" ({len(new_subs)} submissions)')
    assert len(new_subs) >= 1, 'No new submissions found'
except Exception as e:
    print(f'✗ Status filtering: {e}')
    sys.exit(1)

# 5. Get Single Submission Check
try:
    sub = get_submission_by_id(test_id)
    assert sub is not None, 'Submission not found by ID'
    assert sub['title'] == 'Test Hack', 'Title mismatch'
    assert sub['status'] == 'new', 'Default status should be "new"'
    print(f'✓ Get submission by ID (Title: {sub["title"]}, Status: {sub["status"]})')
except Exception as e:
    print(f'✗ Get submission by ID: {e}')
    sys.exit(1)

# 6. Approve Function Check
try:
    success = approve_submission(test_id)
    assert success, 'Approve function returned False'
    sub = get_submission_by_id(test_id)
    assert sub['status'] == 'approved', 'Status not updated to approved'
    print(f'✓ Approve submission function')
except Exception as e:
    print(f'✗ Approve submission: {e}')
    sys.exit(1)

# 7. Reject Function Check
try:
    test_data2 = dict(test_data)
    test_data2['title'] = 'Test Hack 2'
    result2 = submit_game(test_data2, '192.168.1.2')
    reject_id = result2['id']
    
    success = reject_submission(reject_id, 'Test rejection reason')
    assert success, 'Reject function returned False'
    sub = get_submission_by_id(reject_id)
    assert sub['status'] == 'rejected', 'Status not updated to rejected'
    assert sub['admin_notes'] == 'Test rejection reason', 'Rejection reason not saved'
    print(f'✓ Reject submission function')
except Exception as e:
    print(f'✗ Reject submission: {e}')
    sys.exit(1)

# 8. Verify approved submission in filtered results
try:
    approved_subs = get_submissions('approved')
    assert len(approved_subs) >= 1, 'No approved submissions in filtered query'
    print(f'✓ Filter by status "approved" ({len(approved_subs)} submissions)')
except Exception as e:
    print(f'✗ Approved filter: {e}')
    sys.exit(1)

# 9. Verify rejected submission in filtered results
try:
    rejected_subs = get_submissions('rejected')
    assert len(rejected_subs) >= 1, 'No rejected submissions in filtered query'
    print(f'✓ Filter by status "rejected" ({len(rejected_subs)} submissions)')
except Exception as e:
    print(f'✗ Rejected filter: {e}')
    sys.exit(1)

print('=' * 60)
print('ALL CHECKS PASSED! ✓')
print('=' * 60)
print('Summary:')
print(f'  Total submissions: {len(get_submissions())}')
print(f'  New submissions: {len(get_submissions("new"))}')
print(f'  Approved submissions: {len(get_submissions("approved"))}')
print(f'  Rejected submissions: {len(get_submissions("rejected"))}')

import json
import pytest
from django.test import Client


@pytest.mark.django_db
def test_live_api_and_auth_guard():
    c = Client()

    # Test A - student with college email -> 201
    r = c.post('/api/accounts/register/',
        json.dumps({'email': 'testaudit@college.ac.in', 'password': 'Test@1234',
                    'first_name': 'Test', 'last_name': 'User', 'role': 'student',
                    'college': 'Test College', 'batch_year': 2025}),
        content_type='application/json')
    status = 'PASS' if r.status_code == 201 else 'FAIL'
    print(f'\nTest A (student college email -> 201): {r.status_code} {status}')
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.content}"

    # Test B - student with gmail -> 400
    r = c.post('/api/accounts/register/',
        json.dumps({'email': 'testaudit@gmail.com', 'password': 'Test@1234',
                    'first_name': 'Test', 'last_name': 'User', 'role': 'student',
                    'college': 'Test College'}),
        content_type='application/json')
    status = 'PASS' if r.status_code == 400 else 'FAIL'
    print(f'Test B (student gmail -> 400):         {r.status_code} {status} | {r.json()}')
    assert r.status_code == 400

    # Test C - alumni with college email -> 400
    r = c.post('/api/accounts/register/',
        json.dumps({'email': 'alumni@college.ac.in', 'password': 'Test@1234',
                    'first_name': 'Test', 'last_name': 'Alumni', 'role': 'alumni',
                    'college': 'Test College'}),
        content_type='application/json')
    status = 'PASS' if r.status_code == 400 else 'FAIL'
    print(f'Test C (alumni college email -> 400):  {r.status_code} {status} | {r.json()}')
    assert r.status_code == 400

    # Test D - /me/ without token -> 401
    r = c.get('/api/accounts/me/')
    status = 'PASS' if r.status_code == 401 else 'FAIL'
    print(f'Test D (me without token -> 401):      {r.status_code} {status}')
    assert r.status_code == 401

    # Step 12a - dashboard/student/ -> 302 redirect
    r = c.get('/dashboard/student/')
    status = 'PASS' if r.status_code == 302 else 'FAIL'
    print(f'Step 12a (dashboard/student/ -> 302):  {r.status_code} {status} | Location: {r.get("Location", "none")}')
    assert r.status_code == 302
    assert '/auth/login/' in r.get('Location', '')

    # Step 12b - dashboard/alumni/ -> 302 redirect
    r = c.get('/dashboard/alumni/')
    status = 'PASS' if r.status_code == 302 else 'FAIL'
    print(f'Step 12b (dashboard/alumni/ -> 302):   {r.status_code} {status} | Location: {r.get("Location", "none")}')
    assert r.status_code == 302
    assert '/auth/login/' in r.get('Location', '')

    print('\nAll live API + auth guard tests: PASS')

"""
Feed system tests — Day 6-7 Prompt 3
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.feed.models import Post, PostLike, PostComment, PostSave, PostReport

User = get_user_model()
pytestmark = pytest.mark.django_db


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def auth(client, user):
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
    return client


# ─────────────────────────────────────────────────────────────
# GROUP 1 — Feed list
# ─────────────────────────────────────────────────────────────

def test_authenticated_user_can_view_feed(student_with_token):
    res = student_with_token.get('/api/feed/')
    assert res.status_code == 200
    data = res.json()
    assert 'results' in data
    assert 'count' in data


def test_unauthenticated_user_cannot_view_feed(api_client):
    res = api_client.get('/api/feed/')
    assert res.status_code == 401


def test_feed_returns_only_active_posts(student_with_token, verified_alumni):
    Post.objects.create(author=verified_alumni, post_type='general',
                        content='Active post content here.', status='active')
    Post.objects.create(author=verified_alumni, post_type='general',
                        content='Hidden post content here.', status='hidden')
    Post.objects.create(author=verified_alumni, post_type='general',
                        content='Deleted post content here.', status='deleted')

    res = student_with_token.get('/api/feed/')
    assert res.status_code == 200
    results = res.json()['results']
    assert len(results) == 1
    assert results[0]['content'] == 'Active post content here.'


def test_feed_filter_by_type_job(student_with_token, verified_alumni):
    Post.objects.create(author=verified_alumni, post_type='job',
                        content='Job post content here.', company_name='Acme',
                        job_role='Dev', status='active')
    Post.objects.create(author=verified_alumni, post_type='general',
                        content='General post content here.', status='active')

    res = student_with_token.get('/api/feed/?type=job')
    assert res.status_code == 200
    results = res.json()['results']
    assert len(results) == 1
    assert results[0]['post_type'] == 'job'


def test_feed_search_in_content(student_with_token, verified_alumni):
    Post.objects.create(author=verified_alumni, post_type='general',
                        content='Python developer needed for backend role.', status='active')
    Post.objects.create(author=verified_alumni, post_type='general',
                        content='Frontend React position available now.', status='active')

    res = student_with_token.get('/api/feed/?search=python')
    assert res.status_code == 200
    results = res.json()['results']
    assert len(results) == 1
    assert 'Python' in results[0]['content'] or 'python' in results[0]['content'].lower()


# ─────────────────────────────────────────────────────────────
# GROUP 2 — Post creation
# ─────────────────────────────────────────────────────────────

def test_alumni_can_create_general_post(api_client, verified_alumni):
    auth(api_client, verified_alumni)
    res = api_client.post('/api/feed/', {
        'post_type': 'general',
        'content': 'This is a test post from alumni.',
    }, format='json')
    assert res.status_code == 201
    assert Post.objects.filter(author=verified_alumni, post_type='general').exists()


def test_faculty_can_create_post(api_client, verified_faculty):
    auth(api_client, verified_faculty)
    res = api_client.post('/api/feed/', {
        'post_type': 'announcement',
        'content': 'Important announcement from faculty.',
    }, format='json')
    assert res.status_code == 201


def test_student_cannot_create_post(api_client, verified_student):
    auth(api_client, verified_student)
    res = api_client.post('/api/feed/', {
        'post_type': 'general',
        'content': 'Student trying to post.',
    }, format='json')
    assert res.status_code == 403


def test_alumni_create_job_post_requires_company_name(api_client, verified_alumni):
    auth(api_client, verified_alumni)
    res = api_client.post('/api/feed/', {
        'post_type': 'job',
        'content': 'Job posting without company details here.',
    }, format='json')
    assert res.status_code == 400


def test_post_content_min_length(api_client, verified_alumni):
    auth(api_client, verified_alumni)
    res = api_client.post('/api/feed/', {
        'post_type': 'general',
        'content': 'Short',
    }, format='json')
    assert res.status_code == 400


# ─────────────────────────────────────────────────────────────
# GROUP 3 — Post edit and delete
# ─────────────────────────────────────────────────────────────

def test_author_can_edit_own_post(api_client, verified_alumni, alumni_post):
    auth(api_client, verified_alumni)
    res = api_client.patch(f'/api/feed/{alumni_post.id}/', {
        'content': 'Updated content for this post here.',
    }, format='json')
    assert res.status_code == 200
    alumni_post.refresh_from_db()
    assert alumni_post.content == 'Updated content for this post here.'


def test_other_user_cannot_edit_post(api_client, verified_alumni, alumni_post, db):
    other = User.objects.create_user(
        username='other_alumni', email='other@company.com',
        password='pass123', role='alumni', is_verified=True, is_active=True,
    )
    auth(api_client, other)
    res = api_client.patch(f'/api/feed/{alumni_post.id}/', {
        'content': 'Trying to edit someone elses post.',
    }, format='json')
    assert res.status_code == 403


def test_author_can_delete_own_post(api_client, verified_alumni, alumni_post):
    auth(api_client, verified_alumni)
    res = api_client.delete(f'/api/feed/{alumni_post.id}/')
    assert res.status_code == 204
    alumni_post.refresh_from_db()
    assert alumni_post.status == 'deleted'


# ─────────────────────────────────────────────────────────────
# GROUP 4 — Likes
# ─────────────────────────────────────────────────────────────

def test_student_can_like_post(api_client, verified_student, alumni_post):
    auth(api_client, verified_student)
    res = api_client.post(f'/api/feed/{alumni_post.id}/like/', format='json')
    assert res.status_code == 200
    data = res.json()
    assert data['liked'] is True
    assert PostLike.objects.filter(post=alumni_post, user=verified_student).exists()
    assert data['likes_count'] == 1


def test_like_again_toggles_off(api_client, verified_student, alumni_post):
    auth(api_client, verified_student)
    api_client.post(f'/api/feed/{alumni_post.id}/like/', format='json')
    res = api_client.post(f'/api/feed/{alumni_post.id}/like/', format='json')
    assert res.status_code == 200
    data = res.json()
    assert data['liked'] is False
    assert not PostLike.objects.filter(post=alumni_post, user=verified_student).exists()
    assert data['likes_count'] == 0


def test_likes_count_cached_correctly(api_client, alumni_post, db):
    users = []
    for i in range(3):
        u = User.objects.create_user(
            username=f'liker_{i}', email=f'liker{i}@company.com',
            password='pass123', role='alumni', is_verified=True, is_active=True,
        )
        users.append(u)
        c = api_client.__class__()
        auth(c, u)
        c.post(f'/api/feed/{alumni_post.id}/like/', format='json')

    # Use any authenticated client to fetch
    auth(api_client, users[0])
    res = api_client.get(f'/api/feed/{alumni_post.id}/')
    assert res.status_code == 200
    assert res.json()['likes_count'] == 3


# ─────────────────────────────────────────────────────────────
# GROUP 5 — Comments
# ─────────────────────────────────────────────────────────────

def test_student_can_comment(api_client, verified_student, alumni_post):
    auth(api_client, verified_student)
    res = api_client.post(f'/api/feed/{alumni_post.id}/comments/', {
        'content': 'Great post! Very informative.',
    }, format='json')
    assert res.status_code == 201
    assert PostComment.objects.filter(post=alumni_post, author=verified_student).exists()


def test_comment_on_nonexistent_post(api_client, verified_student):
    auth(api_client, verified_student)
    res = api_client.post('/api/feed/99999/comments/', {
        'content': 'Comment on missing post.',
    }, format='json')
    assert res.status_code == 404


def test_comment_author_can_delete_own_comment(api_client, verified_student, alumni_post):
    auth(api_client, verified_student)
    create_res = api_client.post(f'/api/feed/{alumni_post.id}/comments/', {
        'content': 'Comment to be deleted soon.',
    }, format='json')
    assert create_res.status_code == 201
    comment_id = create_res.json()['id']

    del_res = api_client.delete(f'/api/feed/comments/{comment_id}/')
    assert del_res.status_code == 204

    comment = PostComment.objects.get(id=comment_id)
    assert comment.is_deleted is True


def test_deleted_comment_shows_placeholder(api_client, verified_student, alumni_post):
    comment = PostComment.objects.create(
        post=alumni_post, author=verified_student,
        content='Original content.', is_deleted=True,
    )
    auth(api_client, verified_student)
    res = api_client.get(f'/api/feed/{alumni_post.id}/comments/')
    assert res.status_code == 200
    results = res.json()['results']
    match = next((c for c in results if c['id'] == comment.id), None)
    assert match is not None
    assert match['content'] == '[This comment was deleted]'


def test_nested_reply_works(api_client, verified_student, alumni_post):
    auth(api_client, verified_student)
    parent_res = api_client.post(f'/api/feed/{alumni_post.id}/comments/', {
        'content': 'Parent comment here.',
    }, format='json')
    assert parent_res.status_code == 201
    parent_id = parent_res.json()['id']

    reply_res = api_client.post(f'/api/feed/{alumni_post.id}/comments/', {
        'content': 'Reply here.',
        'parent': parent_id,
    }, format='json')
    assert reply_res.status_code == 201
    reply = PostComment.objects.get(id=reply_res.json()['id'])
    assert reply.parent_id == parent_id


# ─────────────────────────────────────────────────────────────
# GROUP 6 — Save + Report
# ─────────────────────────────────────────────────────────────

def test_student_can_save_post(api_client, verified_student, alumni_post):
    auth(api_client, verified_student)
    res = api_client.post(f'/api/feed/{alumni_post.id}/save/', format='json')
    assert res.status_code == 200
    assert res.json()['saved'] is True
    assert PostSave.objects.filter(post=alumni_post, user=verified_student).exists()


def test_saved_posts_visible_in_saved_feed(api_client, verified_student, verified_alumni):
    auth(api_client, verified_student)
    p1 = Post.objects.create(author=verified_alumni, post_type='general',
                             content='First post to save here.', status='active')
    p2 = Post.objects.create(author=verified_alumni, post_type='general',
                             content='Second post to save here.', status='active')
    api_client.post(f'/api/feed/{p1.id}/save/', format='json')
    api_client.post(f'/api/feed/{p2.id}/save/', format='json')

    res = api_client.get('/api/feed/saved/')
    assert res.status_code == 200
    assert res.json()['count'] == 2


def test_user_can_report_post(api_client, verified_student, alumni_post):
    auth(api_client, verified_student)
    res = api_client.post(f'/api/feed/{alumni_post.id}/report/', {
        'reason': 'spam',
    }, format='json')
    assert res.status_code == 201


def test_user_cannot_report_same_post_twice(api_client, verified_student, alumni_post):
    auth(api_client, verified_student)
    api_client.post(f'/api/feed/{alumni_post.id}/report/', {'reason': 'spam'}, format='json')
    res = api_client.post(f'/api/feed/{alumni_post.id}/report/', {'reason': 'spam'}, format='json')
    assert res.status_code == 400

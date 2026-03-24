"""
Day 11-12: Referral System Tests
Groups: skill_matcher, referral_list, referral_creation,
        application, application_management, faculty_recommendation
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from apps.referrals.models import Referral, ReferralApplication, FacultyReferralRecommendation


# ══════════════════════════════════════════════════════════════
# GROUP 1: Skill Matching Engine
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_perfect_skill_match_returns_100():
    from utils.skill_matcher import calculate_skill_match
    result = calculate_skill_match(
        student_skills=['Python', 'Django', 'PostgreSQL'],
        required_skills=['Python', 'Django', 'PostgreSQL'],
    )
    assert result['score'] == 100
    assert result['can_apply'] is True
    assert result['missing_skills'] == []


@pytest.mark.django_db
def test_no_match_returns_0_and_cannot_apply():
    from utils.skill_matcher import calculate_skill_match
    result = calculate_skill_match(
        student_skills=['Java', 'Spring Boot'],
        required_skills=['Python', 'Django', 'React', 'PostgreSQL'],
    )
    assert result['score'] == 0
    assert result['can_apply'] is False
    assert len(result['missing_skills']) == 4


@pytest.mark.django_db
def test_partial_match_above_threshold_can_apply():
    from utils.skill_matcher import calculate_skill_match
    result = calculate_skill_match(
        student_skills=['Python', 'Django'],
        required_skills=['Python', 'Django', 'React', 'AWS'],
    )
    # 2/4 required = 50% of 80 = score of 40 — exactly at threshold
    assert result['can_apply'] is True
    assert result['score'] >= 40


@pytest.mark.django_db
def test_partial_match_below_threshold_cannot_apply():
    from utils.skill_matcher import calculate_skill_match
    result = calculate_skill_match(
        student_skills=['Python'],
        required_skills=['Python', 'React', 'AWS', 'Docker', 'Kubernetes'],
    )
    # 1/5 = 20% of 80 = 16 — below 40 threshold
    assert result['can_apply'] is False
    assert result['score'] < 40


@pytest.mark.django_db
def test_preferred_skills_boost_score():
    from utils.skill_matcher import calculate_skill_match
    result_without_preferred = calculate_skill_match(
        student_skills=['Python', 'Django'],
        required_skills=['Python', 'Django'],
        preferred_skills=['Docker', 'AWS'],
    )
    result_with_preferred = calculate_skill_match(
        student_skills=['Python', 'Django', 'Docker', 'AWS'],
        required_skills=['Python', 'Django'],
        preferred_skills=['Docker', 'AWS'],
    )
    assert result_with_preferred['score'] > result_without_preferred['score']
    assert result_with_preferred['score'] == 100


@pytest.mark.django_db
def test_empty_required_skills_always_matches():
    from utils.skill_matcher import calculate_skill_match
    result = calculate_skill_match(
        student_skills=['Python'],
        required_skills=[],
    )
    assert result['score'] == 100
    assert result['can_apply'] is True


@pytest.mark.django_db
def test_empty_student_skills_never_matches():
    from utils.skill_matcher import calculate_skill_match
    result = calculate_skill_match(
        student_skills=[],
        required_skills=['Python', 'Django'],
    )
    assert result['score'] == 0
    assert result['can_apply'] is False


@pytest.mark.django_db
def test_case_insensitive_skill_matching():
    from utils.skill_matcher import calculate_skill_match
    result = calculate_skill_match(
        student_skills=['python', 'DJANGO', 'PostgreSQL'],
        required_skills=['Python', 'Django', 'postgresql'],
    )
    assert result['score'] == 100


# ══════════════════════════════════════════════════════════════
# GROUP 2: Referral List API
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_authenticated_user_can_view_referrals(student_api_client, active_referral):
    response = student_api_client.get('/api/referrals/')
    assert response.status_code == 200
    assert 'results' in response.data
    assert response.data['count'] >= 1


@pytest.mark.django_db
def test_unauthenticated_cannot_view_referrals(api_client):
    response = api_client.get('/api/referrals/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_expired_referrals_not_shown_in_list(student_api_client, active_referral, expired_referral):
    response = student_api_client.get('/api/referrals/')
    assert response.status_code == 200
    referral_ids = [r['id'] for r in response.data['results']]
    assert active_referral.id in referral_ids
    assert expired_referral.id not in referral_ids


@pytest.mark.django_db
def test_filter_by_work_type(student_api_client, active_referral):
    response = student_api_client.get('/api/referrals/?work_type=full_time')
    assert response.status_code == 200
    for ref in response.data['results']:
        assert ref['work_type'] == 'full_time'


@pytest.mark.django_db
def test_filter_by_company_name(student_api_client, active_referral):
    response = student_api_client.get('/api/referrals/?company=TestCorp')
    assert response.status_code == 200
    assert any(r['company_name'] == 'TestCorp' for r in response.data['results'])


@pytest.mark.django_db
def test_search_by_job_title(student_api_client, active_referral):
    response = student_api_client.get('/api/referrals/?search=Python Developer')
    assert response.status_code == 200
    assert len(response.data['results']) >= 1


# ══════════════════════════════════════════════════════════════
# GROUP 3: Referral Creation
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_alumni_can_create_referral(alumni_api_client, verified_alumni):
    payload = {
        'company_name': 'Startup Inc',
        'job_title': 'Full Stack Developer',
        'job_description': 'We are a fast-growing startup looking for a full stack developer to join our team. You will work on both frontend and backend systems.',
        'work_type': 'full_time',
        'experience_level': 'fresher',
        'required_skills': ['React', 'Node.js', 'MongoDB'],
        'max_applicants': 3,
        'deadline': (timezone.now() + timedelta(days=10)).isoformat(),
    }
    response = alumni_api_client.post('/api/referrals/', payload, format='json')
    assert response.status_code == 201
    assert Referral.objects.filter(job_title='Full Stack Developer', posted_by=verified_alumni).exists()


@pytest.mark.django_db
def test_student_cannot_create_referral(student_api_client):
    payload = {
        'company_name': 'Test Co',
        'job_title': 'Developer',
        'job_description': 'This should not be allowed for students to post.',
        'required_skills': ['Python'],
        'max_applicants': 5,
        'deadline': (timezone.now() + timedelta(days=5)).isoformat(),
    }
    response = student_api_client.post('/api/referrals/', payload, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_max_applicants_cannot_exceed_5(alumni_api_client):
    payload = {
        'company_name': 'Test',
        'job_title': 'Developer',
        'job_description': 'Testing max applicants validation for the referral system.',
        'required_skills': ['Python'],
        'max_applicants': 10,
        'deadline': (timezone.now() + timedelta(days=5)).isoformat(),
    }
    response = alumni_api_client.post('/api/referrals/', payload, format='json')
    assert response.status_code == 400
    assert 'max_applicants' in response.data


@pytest.mark.django_db
def test_past_deadline_rejected(alumni_api_client):
    payload = {
        'company_name': 'Test',
        'job_title': 'Developer',
        'job_description': 'Testing past deadline validation for referral creation.',
        'required_skills': ['Python'],
        'max_applicants': 5,
        'deadline': (timezone.now() - timedelta(hours=1)).isoformat(),
    }
    response = alumni_api_client.post('/api/referrals/', payload, format='json')
    assert response.status_code == 400
    assert 'deadline' in response.data


# ══════════════════════════════════════════════════════════════
# GROUP 4: Referral Application
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_student_with_matching_skills_can_apply(student_api_client, active_referral, student_with_matching_skills):
    response = student_api_client.post(f'/api/referrals/{active_referral.id}/apply/', {}, format='json')
    assert response.status_code == 201
    assert response.data.get('can_apply') is True
    assert ReferralApplication.objects.filter(
        referral=active_referral, student=student_with_matching_skills
    ).exists()


@pytest.mark.django_db
def test_student_with_no_skills_cannot_apply(student_api_client, active_referral, student_with_no_skills):
    response = student_api_client.post(f'/api/referrals/{active_referral.id}/apply/', {}, format='json')
    assert response.status_code == 400
    assert response.data.get('can_apply') is False
    assert 'missing_skills' in response.data


@pytest.mark.django_db
def test_cannot_apply_to_expired_referral(student_api_client, expired_referral, student_with_matching_skills):
    response = student_api_client.post(f'/api/referrals/{expired_referral.id}/apply/', {}, format='json')
    assert response.status_code == 400
    assert 'expired' in str(response.data).lower()


@pytest.mark.django_db
def test_cannot_apply_to_full_referral(student_api_client, full_referral, student_with_matching_skills):
    response = student_api_client.post(f'/api/referrals/{full_referral.id}/apply/', {}, format='json')
    assert response.status_code == 400
    assert 'slot' in str(response.data).lower() or 'full' in str(response.data).lower()


@pytest.mark.django_db
def test_cannot_apply_twice_to_same_referral(student_api_client, active_referral, confirmed_referral_application):
    response = student_api_client.post(f'/api/referrals/{active_referral.id}/apply/', {}, format='json')
    assert response.status_code == 400
    assert 'already' in str(response.data).lower()


@pytest.mark.django_db
def test_alumni_cannot_apply_to_referral(alumni_api_client, active_referral):
    response = alumni_api_client.post(f'/api/referrals/{active_referral.id}/apply/', {}, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_total_applications_increments_after_apply(student_api_client, active_referral, student_with_matching_skills):
    count_before = active_referral.total_applications
    student_api_client.post(f'/api/referrals/{active_referral.id}/apply/', {}, format='json')
    active_referral.refresh_from_db()
    assert active_referral.total_applications == count_before + 1


@pytest.mark.django_db
def test_referral_closes_when_all_slots_filled(alumni_api_client, verified_alumni, verified_student):
    """When last slot is filled, referral status becomes closed"""
    from apps.accounts.models import StudentProfile
    referral = Referral.objects.create(
        posted_by=verified_alumni,
        company_name='SlotTest Inc',
        job_title='Slot Test Role',
        job_description='Testing slot filling behavior when all applicants have applied.',
        work_type='full_time',
        experience_level='fresher',
        required_skills=['Python'],
        max_applicants=1,
        deadline=timezone.now() + timedelta(days=5),
        status='active',
    )
    # Set student skills to match
    try:
        sp = verified_student.student_profile
        sp.skills = ['Python', 'Django', 'REST API']
        sp.save(update_fields=['skills'])
    except Exception:
        pass

    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework.test import APIClient
    client = APIClient()
    refresh = RefreshToken.for_user(verified_student)
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))

    response = client.post(f'/api/referrals/{referral.id}/apply/', {}, format='json')
    assert response.status_code == 201
    referral.refresh_from_db()
    assert referral.status == 'closed'


# ══════════════════════════════════════════════════════════════
# GROUP 5: Application Management
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_student_can_view_own_applications(student_api_client, confirmed_referral_application):
    response = student_api_client.get('/api/referrals/my-applications/')
    assert response.status_code == 200
    app_ids = [a['id'] for a in response.data]
    assert confirmed_referral_application.id in app_ids


@pytest.mark.django_db
def test_student_can_withdraw_application(student_api_client, confirmed_referral_application):
    response = student_api_client.delete(
        f'/api/referrals/my-applications/{confirmed_referral_application.id}/'
    )
    assert response.status_code == 200
    confirmed_referral_application.refresh_from_db()
    assert confirmed_referral_application.status == 'withdrawn'


@pytest.mark.django_db
def test_alumni_can_update_application_status(alumni_api_client, confirmed_referral_application):
    response = alumni_api_client.patch(
        f'/api/referrals/applications/{confirmed_referral_application.id}/update/',
        {'status': 'shortlisted', 'alumni_note': 'Great profile, moving forward.'},
        format='json',
    )
    assert response.status_code == 200
    confirmed_referral_application.refresh_from_db()
    assert confirmed_referral_application.status == 'shortlisted'
    assert confirmed_referral_application.alumni_note == 'Great profile, moving forward.'


@pytest.mark.django_db
def test_success_story_created_when_hired(alumni_api_client, confirmed_referral_application):
    from apps.referrals.models import ReferralSuccessStory
    response = alumni_api_client.patch(
        f'/api/referrals/applications/{confirmed_referral_application.id}/update/',
        {'status': 'hired'},
        format='json',
    )
    assert response.status_code == 200
    assert ReferralSuccessStory.objects.filter(application=confirmed_referral_application).exists()


@pytest.mark.django_db
def test_skill_match_check_endpoint(student_api_client, active_referral, student_with_matching_skills):
    response = student_api_client.get(f'/api/referrals/{active_referral.id}/match-check/')
    assert response.status_code == 200
    assert 'score' in response.data
    assert 'can_apply' in response.data
    assert 'matched_skills' in response.data
    assert 'missing_skills' in response.data


# ══════════════════════════════════════════════════════════════
# GROUP 6: Faculty Recommendation
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_faculty_can_recommend_student(faculty_api_client, active_referral, verified_student):
    response = faculty_api_client.post(
        f'/api/referrals/{active_referral.id}/recommend/',
        {'student_id': verified_student.id, 'note': 'Excellent student with strong Python skills.'},
        format='json',
    )
    assert response.status_code == 201
    assert FacultyReferralRecommendation.objects.filter(
        faculty=faculty_api_client._faculty,
        student=verified_student,
        referral=active_referral,
    ).exists()


@pytest.mark.django_db
def test_student_cannot_recommend(student_api_client, active_referral, verified_student):
    response = student_api_client.post(
        f'/api/referrals/{active_referral.id}/recommend/',
        {'student_id': verified_student.id},
        format='json',
    )
    assert response.status_code == 403

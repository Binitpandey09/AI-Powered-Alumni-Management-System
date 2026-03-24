"""
tests/test_ai_tools.py
Complete test suite for Day 16-19 AI Tools — Phase 8.
Covers: service layer, all 4 API views, usage tracking.
"""
import pytest
from decimal import Decimal
from apps.payments.models import AIToolUsage


# ══════════════════════════════════════════════════════════════
# TEST GROUP 1: AI Service Layer
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_score_resume_returns_valid_structure(mock_openai):
    from utils.ai_tools_service import score_resume
    result = score_resume(
        resume_text="Python developer with Django experience. Built e-commerce app.",
        student_profile_data={
            "skills": ["Python", "Django"],
            "education_summary": "B.Tech CSE",
            "projects_count": 1,
            "internships_count": 0,
        },
        job_role="Backend Developer",
    )
    assert result['success'] is True
    data = result['data']
    assert 'overall_score' in data
    assert 'grade' in data
    assert 'strengths' in data
    assert 'weaknesses' in data
    assert 'improvements' in data
    assert 'ats_score' in data
    assert 'ats_keywords_found' in data
    assert 'ats_keywords_missing' in data
    assert isinstance(data['overall_score'], int)
    assert 0 <= data['overall_score'] <= 100
    assert data['grade'] in ['A', 'B', 'C', 'D', 'F']


@pytest.mark.django_db
def test_score_resume_section_scores_present(mock_openai):
    from utils.ai_tools_service import score_resume
    result = score_resume(
        resume_text="Test resume content with Python and Django skills.",
        student_profile_data={
            "skills": ["Python"],
            "education_summary": "B.Tech",
            "projects_count": 0,
            "internships_count": 0,
        },
    )
    assert result['success'] is True
    section_scores = result['data'].get('section_scores', {})
    required_sections = ['contact_info', 'education', 'skills', 'experience', 'projects', 'formatting']
    for section in required_sections:
        assert section in section_scores, f"Missing section: {section}"


@pytest.mark.django_db
def test_analyze_skill_gap_returns_valid_structure(mock_openai):
    from utils.ai_tools_service import analyze_skill_gap
    result = analyze_skill_gap(
        student_skills=["Python", "Django", "JavaScript"],
        target_role="Full Stack Developer",
        current_education="B.Tech Computer Science",
    )
    assert result['success'] is True
    data = result['data']
    assert 'readiness_score' in data
    assert 'readiness_level' in data
    assert 'skills_to_learn' in data
    assert 'learning_roadmap' in data
    assert 'total_weeks_to_ready' in data
    assert 'job_market_insight' in data
    assert isinstance(data['readiness_score'], int)
    assert 0 <= data['readiness_score'] <= 100
    assert data['readiness_level'] in ['Not Ready', 'Getting There', 'Almost Ready', 'Job Ready']


@pytest.mark.django_db
def test_generate_interview_questions_structure(mock_openai):
    from utils.ai_tools_service import generate_interview_questions
    result = generate_interview_questions(
        student_profile_data={
            "skills": ["Python", "Django"],
            "education_summary": "B.Tech",
            "projects_summary": "E-commerce app",
            "experience_level": "fresher",
        },
        job_role="Software Engineer",
        num_questions=3,
    )
    assert result['success'] is True
    data = result['data']
    assert 'questions' in data
    assert len(data['questions']) >= 1
    q = data['questions'][0]
    assert 'id' in q
    assert 'question' in q
    assert 'type' in q
    assert 'difficulty' in q
    assert 'hint' in q
    assert 'time_limit_seconds' in q


@pytest.mark.django_db
def test_evaluate_interview_answer_structure(mock_openai):
    from utils.ai_tools_service import evaluate_interview_answer
    result = evaluate_interview_answer(
        question="Explain how Django ORM works.",
        answer="Django ORM provides a Pythonic way to interact with the database using models and querysets.",
        job_role="Python Developer",
        student_skills=["Python", "Django"],
    )
    assert result['success'] is True
    data = result['data']
    assert 'score' in data
    assert 'feedback' in data
    assert 'strengths' in data
    assert 'improvements' in data
    assert 'ideal_answer_points' in data
    assert isinstance(data['score'], int)
    assert 0 <= data['score'] <= 10


@pytest.mark.django_db
def test_build_resume_returns_sections(mock_openai):
    from utils.ai_tools_service import build_resume
    result = build_resume(
        student_profile_data={
            "name": "Test Student",
            "email": "test@college.ac.in",
            "skills": ["Python", "Django"],
            "education": [],
            "projects": [],
            "internships": [],
            "certifications": [],
        },
        target_role="Backend Developer",
    )
    assert result['success'] is True
    data = result['data']
    assert 'resume_sections' in data
    sections = data['resume_sections']
    assert 'header' in sections
    assert 'summary' in sections
    assert 'skills' in sections


@pytest.mark.django_db
def test_ai_service_handles_empty_skills_gracefully(mock_openai):
    from utils.ai_tools_service import score_resume
    result = score_resume(
        resume_text="",
        student_profile_data={
            "skills": [],
            "education_summary": "",
            "projects_count": 0,
            "internships_count": 0,
        },
    )
    # Should not crash even with empty inputs
    assert 'success' in result


# ══════════════════════════════════════════════════════════════
# TEST GROUP 2: Resume Score API View
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_resume_score_requires_usage_id(student_api_client):
    response = student_api_client.post('/api/ai/resume-score/', {}, format='json')
    assert response.status_code == 400
    assert 'usage_id' in str(response.data).lower()


@pytest.mark.django_db
def test_resume_score_rejects_invalid_usage_id(student_api_client, verified_student):
    response = student_api_client.post('/api/ai/resume-score/', {'usage_id': 99999}, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_resume_score_rejects_wrong_tool_type(student_api_client, skill_gap_usage):
    """Using a skill_gap usage_id for resume_check should fail"""
    response = student_api_client.post(
        '/api/ai/resume-score/', {'usage_id': skill_gap_usage.id}, format='json'
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_resume_score_succeeds_with_valid_usage(student_api_client, resume_check_free_usage, mock_openai):
    response = student_api_client.post(
        '/api/ai/resume-score/',
        {'usage_id': resume_check_free_usage.id, 'job_role': 'Backend Developer'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['success'] is True
    assert 'result' in response.data
    result = response.data['result']
    assert 'overall_score' in result
    assert 'grade' in result


@pytest.mark.django_db
def test_resume_score_result_saved_to_usage(student_api_client, resume_check_free_usage, mock_openai):
    student_api_client.post(
        '/api/ai/resume-score/',
        {'usage_id': resume_check_free_usage.id},
        format='json',
    )
    resume_check_free_usage.refresh_from_db()
    assert bool(resume_check_free_usage.result_data) is True
    assert 'overall_score' in resume_check_free_usage.result_data


@pytest.mark.django_db
def test_resume_score_returns_cached_result_on_second_call(
    student_api_client, resume_check_free_usage, mock_openai
):
    """Second call with same usage_id should return cached result, not call OpenAI again"""
    resume_check_free_usage.result_data = {'overall_score': 85, 'grade': 'A', 'cached_test': True}
    resume_check_free_usage.save()
    response = student_api_client.post(
        '/api/ai/resume-score/',
        {'usage_id': resume_check_free_usage.id},
        format='json',
    )
    assert response.status_code == 200
    assert response.data.get('cached') is True


@pytest.mark.django_db
def test_resume_score_get_returns_past_results(student_api_client, resume_check_free_usage):
    resume_check_free_usage.result_data = {
        'overall_score': 75,
        'grade': 'B',
        'ats_score': 70,
        'summary': 'Good resume.',
    }
    resume_check_free_usage.save()
    response = student_api_client.get('/api/ai/resume-score/')
    assert response.status_code == 200
    assert 'results' in response.data
    assert len(response.data['results']) >= 1


# ══════════════════════════════════════════════════════════════
# TEST GROUP 3: Skill Gap API View
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_skill_gap_requires_target_role(student_api_client, skill_gap_usage):
    response = student_api_client.post(
        '/api/ai/skill-gap/',
        {'usage_id': skill_gap_usage.id},
        format='json',
    )
    assert response.status_code == 400
    assert 'target_role' in str(response.data).lower()


@pytest.mark.django_db
def test_skill_gap_succeeds_with_valid_data(
    student_api_client, skill_gap_usage, student_with_full_profile, mock_openai
):
    response = student_api_client.post(
        '/api/ai/skill-gap/',
        {'usage_id': skill_gap_usage.id, 'target_role': 'Full Stack Developer at a startup'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['success'] is True
    result = response.data['result']
    assert 'readiness_score' in result
    assert 'skills_to_learn' in result
    assert 'learning_roadmap' in result


@pytest.mark.django_db
def test_skill_gap_result_saved(student_api_client, skill_gap_usage, mock_openai):
    student_api_client.post(
        '/api/ai/skill-gap/',
        {'usage_id': skill_gap_usage.id, 'target_role': 'Backend Developer'},
        format='json',
    )
    skill_gap_usage.refresh_from_db()
    assert bool(skill_gap_usage.result_data) is True


# ══════════════════════════════════════════════════════════════
# TEST GROUP 4: AI Interview API View
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_interview_start_requires_job_role(student_api_client, interview_usage, mock_openai):
    response = student_api_client.post(
        '/api/ai/interview/',
        {'action': 'start', 'usage_id': interview_usage.id},
        format='json',
    )
    # job_role defaults to 'Software Engineer' if not provided — should succeed
    assert response.status_code == 200


@pytest.mark.django_db
def test_interview_start_returns_questions(student_api_client, interview_usage, mock_openai):
    response = student_api_client.post(
        '/api/ai/interview/',
        {'action': 'start', 'usage_id': interview_usage.id, 'job_role': 'Python Developer', 'num_questions': 3},
        format='json',
    )
    assert response.status_code == 200
    assert 'data' in response.data
    questions = response.data['data']['questions']
    assert len(questions) >= 1
    assert 'id' in questions[0]
    assert 'question' in questions[0]


@pytest.mark.django_db
def test_interview_submit_answer(student_api_client, interview_usage, mock_openai):
    # First start the interview
    start_response = student_api_client.post(
        '/api/ai/interview/',
        {'action': 'start', 'usage_id': interview_usage.id, 'job_role': 'Software Engineer', 'num_questions': 3},
        format='json',
    )
    assert start_response.status_code == 200
    first_question_id = start_response.data['data']['questions'][0]['id']

    # Submit answer
    answer_response = student_api_client.post(
        '/api/ai/interview/',
        {
            'action': 'submit_answer',
            'usage_id': interview_usage.id,
            'question_id': first_question_id,
            'answer': 'Django ORM abstracts database operations using Python objects called models. QuerySets are lazy and cached for efficiency.',
        },
        format='json',
    )
    assert answer_response.status_code == 200
    assert 'evaluation' in answer_response.data
    evaluation = answer_response.data['evaluation']
    assert 'score' in evaluation
    assert 'feedback' in evaluation


@pytest.mark.django_db
def test_interview_finish_generates_report(student_api_client, interview_usage, mock_openai):
    # Start interview
    start_r = student_api_client.post(
        '/api/ai/interview/',
        {'action': 'start', 'usage_id': interview_usage.id, 'job_role': 'Python Developer', 'num_questions': 3},
        format='json',
    )
    questions = start_r.data['data']['questions']

    # Answer all questions
    for q in questions:
        student_api_client.post(
            '/api/ai/interview/',
            {
                'action': 'submit_answer',
                'usage_id': interview_usage.id,
                'question_id': q['id'],
                'answer': 'This is my test answer for this question.',
            },
            format='json',
        )

    # Finish
    finish_r = student_api_client.post(
        '/api/ai/interview/',
        {'action': 'finish', 'usage_id': interview_usage.id},
        format='json',
    )
    assert finish_r.status_code == 200
    assert 'report' in finish_r.data
    report = finish_r.data['report']
    assert 'overall_score' in report
    assert 'grade' in report
    assert 'hiring_recommendation' in report


@pytest.mark.django_db
def test_interview_invalid_action(student_api_client, interview_usage):
    response = student_api_client.post(
        '/api/ai/interview/',
        {'action': 'invalid_action', 'usage_id': interview_usage.id},
        format='json',
    )
    assert response.status_code == 400


# ══════════════════════════════════════════════════════════════
# TEST GROUP 5: Resume Builder API View
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_resume_builder_requires_usage_id(student_api_client):
    response = student_api_client.post('/api/ai/resume-build/', {'target_role': 'Developer'}, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_resume_builder_succeeds(
    student_api_client, resume_build_usage, student_with_full_profile, mock_openai
):
    response = student_api_client.post(
        '/api/ai/resume-build/',
        {'usage_id': resume_build_usage.id, 'target_role': 'Backend Developer'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['success'] is True
    result = response.data['result']
    assert 'resume_sections' in result
    sections = result['resume_sections']
    assert 'header' in sections
    assert 'summary' in sections


# ══════════════════════════════════════════════════════════════
# TEST GROUP 6: AI Tool Usage Tracking
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_first_resume_check_is_free(student_api_client, verified_student):
    """Before any usage, student should have 1 free resume check"""
    response = student_api_client.get('/api/payments/ai-tools/check/resume_check/')
    assert response.status_code == 200
    assert response.data['free_uses_remaining'] == 1
    assert response.data['is_free_next'] is True


@pytest.mark.django_db
def test_after_free_use_no_more_free(student_api_client, verified_student):
    """After 1 free use, no more free uses available"""
    AIToolUsage.objects.create(user=verified_student, tool_type='resume_check', is_free_use=True)
    response = student_api_client.get('/api/payments/ai-tools/check/resume_check/')
    assert response.status_code == 200
    assert response.data['free_uses_remaining'] == 0
    assert response.data['is_free_next'] is False


@pytest.mark.django_db
def test_ai_interview_has_no_free_uses(student_api_client):
    response = student_api_client.get('/api/payments/ai-tools/check/ai_interview/')
    assert response.status_code == 200
    assert response.data['free_uses_remaining'] == 0
    assert response.data['price'] == '99.00'


@pytest.mark.django_db
def test_resume_builder_has_no_free_uses(student_api_client):
    response = student_api_client.get('/api/payments/ai-tools/check/resume_builder/')
    assert response.status_code == 200
    assert response.data['free_uses_remaining'] == 0
    assert response.data['price'] == '149.00'


@pytest.mark.django_db
def test_skill_gap_has_no_free_uses(student_api_client):
    response = student_api_client.get('/api/payments/ai-tools/check/skill_gap/')
    assert response.status_code == 200
    assert response.data['free_uses_remaining'] == 0
    assert response.data['price'] == '79.00'


@pytest.mark.django_db
def test_cv_parser_is_always_free(student_api_client):
    response = student_api_client.get('/api/payments/ai-tools/check/cv_parser/')
    assert response.status_code == 200
    assert response.data['is_free_next'] is True


@pytest.mark.django_db
def test_another_students_usage_does_not_affect_my_count(student_api_client, verified_student):
    """Another student's free usage should not reduce my free uses"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    other = User.objects.create_user(
        username='other2@college.ac.in',
        email='other2@college.ac.in',
        password='Test@1234',
        role='student',
        is_verified=True,
    )
    AIToolUsage.objects.create(user=other, tool_type='resume_check', is_free_use=True)
    response = student_api_client.get('/api/payments/ai-tools/check/resume_check/')
    assert response.data['free_uses_remaining'] == 1

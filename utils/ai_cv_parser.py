"""
AI-powered CV data extraction using OpenAI.
Upgraded to extract all Naukri-style profile sections.
"""
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert CV/Resume parser for an Indian student job platform. "
    "Extract all information from the CV and return ONLY valid JSON. "
    "Be thorough — extract every detail you can find. "
    "For dates use the format shown in examples. "
    "Return null/empty for missing fields, never omit keys."
)

_USER_PROMPT_TEMPLATE = """Parse this CV and return JSON with EXACTLY this structure:
{{
  "basic": {{
    "first_name": "", "last_name": "", "phone": "", "email": "",
    "gender": "", "date_of_birth": "YYYY-MM-DD or empty",
    "current_location": "", "linkedin_url": "", "github_url": "", "portfolio_url": ""
  }},
  "profile_summary": "full professional summary text",
  "education": [{{
    "education_type": "graduation or class_12 or class_10",
    "degree": "", "specialization": "", "institute_name": "",
    "board_or_university": "", "start_year": 2020, "end_year": 2024,
    "is_pursuing": false, "grade_type": "percentage or cgpa",
    "grade_value": "", "study_mode": "full_time or part_time or distance"
  }}],
  "skills": ["Python", "Django"],
  "projects": [{{
    "title": "", "description": "", "tech_stack": [],
    "start_month": "Sep'25", "end_month": "Nov'25",
    "is_ongoing": false, "project_url": "", "github_url": ""
  }}],
  "internships": [{{
    "company_name": "", "role": "", "description": "",
    "start_month": "", "end_month": "", "is_ongoing": false,
    "stipend": "", "location": "", "skills_used": []
  }}],
  "certifications": [{{
    "title": "", "issuing_organization": "",
    "issue_date": "YYYY-MM-DD or empty", "expiry_date": "YYYY-MM-DD or empty",
    "does_not_expire": false, "credential_id": "", "credential_url": ""
  }}],
  "awards": [{{
    "title": "", "issuer": "",
    "date_received": "YYYY-MM-DD or empty", "description": ""
  }}],
  "competitive_exams": [{{
    "exam_name": "", "year": 2023, "score_or_rank": "", "description": ""
  }}],
  "languages": [{{
    "language": "", "proficiency": "beginner or proficient or expert",
    "can_read": true, "can_write": true, "can_speak": true
  }}],
  "employments": [{{
    "company_name": "", "job_title": "", "description": "",
    "start_month": "", "end_month": "", "is_current": false,
    "location": "", "skills_used": []
  }}],
  "looking_for": "internship or full-time or part-time or freelance",
  "college": "", "degree": "", "branch": "",
  "graduation_year": null, "preferred_locations": []
}}

CV TEXT:
{cv_text}"""


def parse_cv_with_ai(cv_text: str) -> dict:
    """
    Send CV text to OpenAI and return fully parsed profile data.
    Falls back to empty dict on any error.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    if not api_key or not cv_text.strip():
        return {}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[
                {'role': 'system', 'content': _SYSTEM_PROMPT},
                {'role': 'user', 'content': _USER_PROMPT_TEMPLATE.format(
                    cv_text=cv_text[:8000]
                )},
            ],
            temperature=0.1,
            max_tokens=3000,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        return json.loads(raw)

    except Exception as exc:
        logger.warning("AI CV parsing failed: %s", exc)
        return {}


def apply_cv_data_to_profile(user, cv_data: dict) -> dict:
    """
    Apply AI-parsed CV data to the student's profile and all section models.
    Only works for students. Returns summary of what was updated.
    """
    if user.role != 'student':
        return {'updated_sections': [], 'profile_completeness': 0, 'is_complete': False}

    from apps.accounts.models import (
        StudentProfile, StudentEducation, StudentProject,
        StudentInternship, StudentCertification, StudentAward,
        StudentCompetitiveExam, StudentLanguage, StudentEmployment,
    )

    updated_sections = []

    # ── 1. Basic info ─────────────────────────────────────────────────────────
    basic = cv_data.get('basic', {})

    user_dirty = False
    for field, key in [('first_name', 'first_name'), ('last_name', 'last_name'),
                       ('phone', 'phone'), ('college', 'college')]:
        val = basic.get(key) or cv_data.get(key, '')
        if val and not getattr(user, field, ''):
            setattr(user, field, val)
            user_dirty = True
    if user_dirty:
        user.save()

    try:
        profile = user.student_profile
    except StudentProfile.DoesNotExist:
        return {'updated_sections': [], 'profile_completeness': 0, 'is_complete': False}

    profile_dirty = False
    profile_str_fields = [
        ('profile_summary', cv_data.get('profile_summary', '')),
        ('gender', basic.get('gender', '')),
        ('current_location', basic.get('current_location', '')),
        ('looking_for', cv_data.get('looking_for', '')),
        ('degree', cv_data.get('degree', '')),
        ('branch', cv_data.get('branch', '')),
    ]
    for attr, val in profile_str_fields:
        if val and not getattr(profile, attr, ''):
            setattr(profile, attr, val)
            profile_dirty = True

    dob = basic.get('date_of_birth', '')
    if dob and not profile.date_of_birth:
        try:
            from datetime import date
            profile.date_of_birth = date.fromisoformat(dob)
            profile_dirty = True
        except (ValueError, TypeError):
            pass

    grad_year = cv_data.get('graduation_year')
    if grad_year and not profile.graduation_year:
        try:
            profile.graduation_year = int(grad_year)
            profile_dirty = True
        except (ValueError, TypeError):
            pass

    pref_locs = cv_data.get('preferred_locations', [])
    if pref_locs and not profile.preferred_locations:
        profile.preferred_locations = pref_locs
        profile_dirty = True

    skills = cv_data.get('skills', [])
    if skills and not profile.skills:
        profile.skills = skills
        profile_dirty = True

    if profile_dirty:
        profile.save()
        updated_sections.append('basic_info')

    # ── 2. Education ──────────────────────────────────────────────────────────
    edu_created = False
    for edu in cv_data.get('education', []):
        institute = edu.get('institute_name', '').strip()
        degree = edu.get('degree', '').strip()
        if not institute:
            continue
        exists = StudentEducation.objects.filter(
            user=user, institute_name__iexact=institute, degree__iexact=degree
        ).exists()
        if not exists:
            StudentEducation.objects.create(
                user=user,
                education_type=edu.get('education_type', 'graduation'),
                degree=degree,
                specialization=edu.get('specialization', ''),
                institute_name=institute,
                board_or_university=edu.get('board_or_university', ''),
                start_year=edu.get('start_year'),
                end_year=edu.get('end_year'),
                is_pursuing=bool(edu.get('is_pursuing', False)),
                grade_type=edu.get('grade_type', ''),
                grade_value=edu.get('grade_value', ''),
                study_mode=edu.get('study_mode', ''),
            )
            edu_created = True
    if edu_created:
        updated_sections.append('education')

    # ── 3. Projects ───────────────────────────────────────────────────────────
    proj_created = False
    for proj in cv_data.get('projects', []):
        title = proj.get('title', '').strip()
        if not title:
            continue
        if not StudentProject.objects.filter(user=user, title__iexact=title).exists():
            StudentProject.objects.create(
                user=user,
                title=title,
                description=proj.get('description', ''),
                tech_stack=proj.get('tech_stack', []),
                start_month=proj.get('start_month', ''),
                end_month='Present' if proj.get('is_ongoing') else proj.get('end_month', ''),
                is_ongoing=bool(proj.get('is_ongoing', False)),
                project_url=proj.get('project_url', ''),
                github_url=proj.get('github_url', ''),
            )
            proj_created = True
    if proj_created:
        updated_sections.append('projects')

    # ── 4. Internships ────────────────────────────────────────────────────────
    intern_created = False
    for intern in cv_data.get('internships', []):
        company = intern.get('company_name', '').strip()
        role = intern.get('role', '').strip()
        if not company:
            continue
        if not StudentInternship.objects.filter(
            user=user, company_name__iexact=company, role__iexact=role
        ).exists():
            StudentInternship.objects.create(
                user=user,
                company_name=company,
                role=role,
                description=intern.get('description', ''),
                start_month=intern.get('start_month', ''),
                end_month=intern.get('end_month', ''),
                is_ongoing=bool(intern.get('is_ongoing', False)),
                stipend=intern.get('stipend', ''),
                location=intern.get('location', ''),
                skills_used=intern.get('skills_used', []),
            )
            intern_created = True
    if intern_created:
        updated_sections.append('internships')

    # ── 5. Certifications ─────────────────────────────────────────────────────
    cert_created = False
    for cert in cv_data.get('certifications', []):
        title = cert.get('title', '').strip()
        org = cert.get('issuing_organization', '').strip()
        if not title:
            continue
        if not StudentCertification.objects.filter(
            user=user, title__iexact=title, issuing_organization__iexact=org
        ).exists():
            issue_date = _parse_date(cert.get('issue_date'))
            expiry_date = None if cert.get('does_not_expire') else _parse_date(cert.get('expiry_date'))
            StudentCertification.objects.create(
                user=user,
                title=title,
                issuing_organization=org,
                issue_date=issue_date,
                expiry_date=expiry_date,
                does_not_expire=bool(cert.get('does_not_expire', False)),
                credential_id=cert.get('credential_id', ''),
                credential_url=cert.get('credential_url', ''),
            )
            cert_created = True
    if cert_created:
        updated_sections.append('certifications')

    # ── 6. Awards ─────────────────────────────────────────────────────────────
    award_created = False
    for award in cv_data.get('awards', []):
        title = award.get('title', '').strip()
        if not title:
            continue
        if not StudentAward.objects.filter(user=user, title__iexact=title).exists():
            StudentAward.objects.create(
                user=user,
                title=title,
                issuer=award.get('issuer', ''),
                date_received=_parse_date(award.get('date_received')),
                description=award.get('description', ''),
            )
            award_created = True
    if award_created:
        updated_sections.append('awards')

    # ── 7. Competitive Exams ──────────────────────────────────────────────────
    exam_created = False
    for exam in cv_data.get('competitive_exams', []):
        name = exam.get('exam_name', '').strip()
        year = exam.get('year')
        if not name:
            continue
        if not StudentCompetitiveExam.objects.filter(
            user=user, exam_name__iexact=name, year=year
        ).exists():
            StudentCompetitiveExam.objects.create(
                user=user,
                exam_name=name,
                year=year,
                score_or_rank=exam.get('score_or_rank', ''),
                description=exam.get('description', ''),
            )
            exam_created = True
    if exam_created:
        updated_sections.append('competitive_exams')

    # ── 8. Languages ──────────────────────────────────────────────────────────
    lang_created = False
    for lang in cv_data.get('languages', []):
        language = lang.get('language', '').strip()
        if not language:
            continue
        if not StudentLanguage.objects.filter(
            user=user, language__iexact=language
        ).exists():
            StudentLanguage.objects.create(
                user=user,
                language=language,
                proficiency=lang.get('proficiency', 'proficient'),
                can_read=bool(lang.get('can_read', True)),
                can_write=bool(lang.get('can_write', True)),
                can_speak=bool(lang.get('can_speak', True)),
            )
            lang_created = True
    if lang_created:
        updated_sections.append('languages')

    # ── 9. Employment ─────────────────────────────────────────────────────────
    emp_created = False
    for emp in cv_data.get('employments', []):
        company = emp.get('company_name', '').strip()
        job_title = emp.get('job_title', '').strip()
        if not company:
            continue
        if not StudentEmployment.objects.filter(
            user=user, company_name__iexact=company, job_title__iexact=job_title
        ).exists():
            StudentEmployment.objects.create(
                user=user,
                company_name=company,
                job_title=job_title,
                description=emp.get('description', ''),
                start_month=emp.get('start_month', ''),
                end_month=emp.get('end_month', ''),
                is_current=bool(emp.get('is_current', False)),
                location=emp.get('location', ''),
                skills_used=emp.get('skills_used', []),
            )
            emp_created = True
    if emp_created:
        updated_sections.append('employments')

    # Recalculate completeness
    from utils.profile_helpers import get_full_profile_completeness
    completeness = get_full_profile_completeness(user)

    return {
        'updated_sections': updated_sections,
        'profile_completeness': completeness['percentage'],
        'is_complete': completeness['is_complete'],
    }


def _parse_date(value):
    """Safely parse a YYYY-MM-DD string to a date object, or return None."""
    if not value:
        return None
    try:
        from datetime import date
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None

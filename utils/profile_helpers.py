"""
Profile completeness helpers for AlumniAI.
"""


def get_full_profile_completeness(user) -> dict:
    """
    Weighted completeness score for a student profile.
    Returns dict with percentage, sections breakdown, and is_complete flag.
    """
    from apps.accounts.models import (
        StudentProfile, StudentEducation, StudentProject,
        StudentInternship, StudentCertification, StudentLanguage,
    )

    sections = {
        'basic_info':      {'weight': 15, 'complete': False, 'missing': []},
        'education':       {'weight': 20, 'complete': False, 'missing': []},
        'skills':          {'weight': 15, 'complete': False, 'missing': []},
        'profile_summary': {'weight': 10, 'complete': False, 'missing': []},
        'projects':        {'weight': 15, 'complete': False, 'missing': []},
        'internships':     {'weight': 10, 'complete': False, 'missing': []},
        'certifications':  {'weight': 5,  'complete': False, 'missing': []},
        'languages':       {'weight': 5,  'complete': False, 'missing': []},
        'resume':          {'weight': 5,  'complete': False, 'missing': []},
    }

    try:
        profile = user.student_profile
    except StudentProfile.DoesNotExist:
        return {'percentage': 0, 'sections': sections, 'is_complete': False}

    # basic_info: first_name, last_name, phone, profile_pic, current_location, gender
    basic_required = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone': user.phone,
        'profile_pic': user.profile_pic,
        'current_location': profile.current_location,
        'gender': profile.gender,
    }
    missing_basic = [k for k, v in basic_required.items() if not v]
    sections['basic_info']['complete'] = len(missing_basic) == 0
    sections['basic_info']['missing'] = missing_basic

    # education: at least 1 entry
    has_edu = StudentEducation.objects.filter(user=user).exists()
    sections['education']['complete'] = has_edu
    if not has_edu:
        sections['education']['missing'] = ['Add at least one education entry']

    # skills: >= 3
    skills = profile.skills or []
    sections['skills']['complete'] = len(skills) >= 3
    if len(skills) < 3:
        sections['skills']['missing'] = [f'Add at least {3 - len(skills)} more skill(s)']

    # profile_summary
    sections['profile_summary']['complete'] = bool(profile.profile_summary)
    if not profile.profile_summary:
        sections['profile_summary']['missing'] = ['Write a profile summary']

    # projects: at least 1
    has_proj = StudentProject.objects.filter(user=user).exists()
    sections['projects']['complete'] = has_proj
    if not has_proj:
        sections['projects']['missing'] = ['Add at least one project']

    # internships: at least 1
    has_intern = StudentInternship.objects.filter(user=user).exists()
    sections['internships']['complete'] = has_intern
    if not has_intern:
        sections['internships']['missing'] = ['Add at least one internship']

    # certifications: at least 1
    has_cert = StudentCertification.objects.filter(user=user).exists()
    sections['certifications']['complete'] = has_cert
    if not has_cert:
        sections['certifications']['missing'] = ['Add at least one certification']

    # languages: at least 1
    from apps.accounts.models import StudentLanguage
    has_lang = StudentLanguage.objects.filter(user=user).exists()
    sections['languages']['complete'] = has_lang
    if not has_lang:
        sections['languages']['missing'] = ['Add at least one language']

    # resume
    sections['resume']['complete'] = bool(profile.resume_file)
    if not profile.resume_file:
        sections['resume']['missing'] = ['Upload your resume']

    # Calculate total
    percentage = sum(
        s['weight'] for s in sections.values() if s['complete']
    )

    # Cache on profile
    if profile.profile_completeness_score != percentage:
        profile.profile_completeness_score = percentage
        profile.save(update_fields=['profile_completeness_score'])

    return {
        'percentage': percentage,
        'sections': sections,
        'is_complete': percentage >= 80,
    }

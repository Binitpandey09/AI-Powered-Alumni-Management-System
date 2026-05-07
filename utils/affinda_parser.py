"""
Resume parsing using Affinda REST API (v3).
Uses the /v3/documents endpoint with a collection that has the resume extractor.
Maps Affinda's response to the cv_data format expected by apply_cv_data_to_profile().
"""
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

AFFINDA_API_BASE = "https://api.affinda.com/v3"


def parse_cv_with_affinda(file_obj, filename):
    """
    Parse CV using Affinda REST API and return structured data in the format
    expected by apply_cv_data_to_profile() in utils/ai_cv_parser.py.
    """
    api_key = getattr(settings, 'AFFINDA_API_KEY', '')
    collection_id = getattr(settings, 'AFFINDA_COLLECTION_ID', '')

    if not api_key or not collection_id:
        logger.error("Affinda API Key or Collection ID not configured.")
        return None

    try:
        file_obj.seek(0)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        resp = requests.post(
            f"{AFFINDA_API_BASE}/documents",
            headers=headers,
            files={"file": (filename, file_obj, "application/pdf")},
            data={"collection": collection_id, "wait": "true"},
            timeout=30,
        )

        if resp.status_code != 200:
            logger.error("Affinda upload failed (%s): %s", resp.status_code, resp.text[:500])
            return None

        doc = resp.json()
        raw_data = doc.get("data", {})

        if not raw_data:
            logger.warning("Affinda returned empty data for file: %s", filename)
            return None

        return _map_affinda_to_cv_data(raw_data)

    except Exception as e:
        logger.error("Affinda parsing failed: %s", e, exc_info=True)
        return None


def _map_affinda_to_cv_data(data):
    """
    Maps Affinda's REST API response (plain dict) to the cv_data dict format
    expected by apply_cv_data_to_profile().
    """
    try:
        # ── Basic info ────────────────────────────────────────────
        name_obj = data.get('name') or {}
        emails = data.get('emails') or []
        phones = data.get('phoneNumbers') or []
        websites = data.get('websites') or []
        location_obj = data.get('location') or {}

        # Extract URLs
        linkedin_url = data.get('linkedin', '') or ''
        github_url = ''
        portfolio_url = ''
        for site in websites:
            url = site if isinstance(site, str) else str(site)
            url_lower = url.lower()
            if 'linkedin' in url_lower and not linkedin_url:
                linkedin_url = url
            elif 'github' in url_lower:
                github_url = url
            elif not portfolio_url:
                portfolio_url = url

        basic = {
            'first_name': name_obj.get('first', ''),
            'last_name': name_obj.get('last', ''),
            'email': emails[0] if emails else '',
            'phone': phones[0] if phones else '',
            'current_location': location_obj.get('formatted', '') or location_obj.get('rawInput', ''),
            'linkedin_url': linkedin_url,
            'github_url': github_url,
            'portfolio_url': portfolio_url,
        }

        # ── Education ─────────────────────────────────────────────
        education = []
        college = ''
        degree_top = ''
        branch_top = ''

        for edu in (data.get('education') or []):
            dates = edu.get('dates') or {}
            end_date = dates.get('completionDate', '')
            start_date = dates.get('startDate', '')
            end_year = _extract_year(end_date)
            start_year = _extract_year(start_date)

            institute = edu.get('organization', '') or ''
            accreditation = edu.get('accreditation') or {}
            degree_name = accreditation.get('education', '') or ''
            edu_level = accreditation.get('educationLevel', '') or ''

            grade_obj = edu.get('grade') or {}
            grade_value = grade_obj.get('value', '') or grade_obj.get('raw', '') or ''
            grade_metric = grade_obj.get('metric', '') or ''

            # Determine education type
            edu_type = _classify_education_type(degree_name, edu_level, institute)

            # Determine grade_type
            grade_type = ''
            if grade_metric:
                metric_lower = grade_metric.lower()
                if 'cgpa' in metric_lower or 'gpa' in metric_lower:
                    grade_type = 'cgpa'
                elif 'percent' in metric_lower or '%' in str(grade_value):
                    grade_type = 'percentage'

            education.append({
                'institute_name': institute,
                'degree': degree_name,
                'specialization': '',
                'education_type': edu_type,
                'start_year': start_year,
                'end_year': end_year,
                'grade_value': grade_value,
                'grade_type': grade_type,
                'study_mode': '',
                'board_or_university': '',
                'is_pursuing': dates.get('isCurrent', False) or False,
            })

            # Use the first graduation-level entry as the top-level degree/college
            if not college and edu_type == 'graduation':
                college = institute
                degree_top = degree_name

        # ── Employment (work experience) ──────────────────────────
        employments = []
        internships = []

        for exp in (data.get('workExperience') or []):
            dates = exp.get('dates') or {}
            company = exp.get('organization', '') or ''
            job_title = exp.get('jobTitle', '') or ''
            description = exp.get('jobDescription', '') or ''
            is_current = dates.get('isCurrent', False) or False

            start_month = dates.get('startDate', '') or ''
            end_month = dates.get('endDate', '') or ''
            if is_current:
                end_month = 'Present'

            entry = {
                'company_name': company,
                'job_title': job_title,
                'role': job_title,
                'description': description,
                'start_month': start_month,
                'end_month': end_month,
                'is_current': is_current,
                'is_ongoing': is_current,
                'location': '',
                'skills_used': [],
            }

            # Classify as internship or employment
            title_lower = job_title.lower()
            if 'intern' in title_lower or 'trainee' in title_lower:
                internships.append(entry)
            else:
                employments.append(entry)

        # ── Skills ────────────────────────────────────────────────
        skills = []
        for s in (data.get('skills') or []):
            if isinstance(s, dict):
                skill_name = s.get('name', '')
            else:
                skill_name = str(s)
            if skill_name and skill_name not in skills:
                skills.append(skill_name)

        # ── Summary ───────────────────────────────────────────────
        summary = data.get('summary', '') or data.get('objective', '') or ''

        # ── Certifications ────────────────────────────────────────
        certifications = []
        for cert in (data.get('certifications') or []):
            if isinstance(cert, str):
                title = cert
            else:
                title = cert.get('name', '') or cert.get('title', '') or str(cert)
            if title:
                certifications.append({
                    'title': title,
                    'issuing_organization': '',
                    'issue_date': '',
                    'expiry_date': '',
                    'does_not_expire': True,
                    'credential_id': '',
                    'credential_url': '',
                })

        # ── Languages ─────────────────────────────────────────────
        languages = []
        for lang in (data.get('languages') or []):
            if isinstance(lang, str):
                lang_name = lang
            else:
                lang_name = lang.get('name', '') or str(lang)
            if lang_name:
                languages.append({
                    'language': lang_name,
                    'proficiency': 'proficient',
                    'can_read': True,
                    'can_write': True,
                    'can_speak': True,
                })

        return {
            'basic': basic,
            'education': education,
            'employments': employments,
            'internships': internships,
            'certifications': certifications,
            'skills': skills,
            'profile_summary': summary,
            'college': college,
            'degree': degree_top,
            'branch': branch_top,
            'projects': [],
            'awards': [],
            'competitive_exams': [],
            'languages': languages,
        }

    except Exception as e:
        logger.warning("Error mapping Affinda data: %s", e, exc_info=True)
        return {}


def _extract_year(date_str):
    """Extract a 4-digit year from a date string like '2023-06-15'."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    try:
        for part in date_str.split('-'):
            if len(part) == 4 and part.isdigit():
                return int(part)
    except (ValueError, TypeError):
        pass
    return None


def _classify_education_type(degree, edu_level, institute):
    """
    Classify as 'class_10', 'class_12', or 'graduation'.
    Uses Affinda's educationLevel field + keyword matching.
    """
    combined = (degree + ' ' + institute).lower()

    # Affinda's educationLevel can be: 'school', 'bachelors', 'masters', 'doctoral', etc.
    if edu_level:
        level_lower = edu_level.lower()
        if level_lower in ('bachelors', 'masters', 'doctoral', 'postgraduate'):
            return 'graduation'
        if level_lower == 'school':
            # Distinguish 10th vs 12th via degree text
            if any(k in combined for k in ('12', 'xii', 'hsc', 'intermediate', 'higher secondary')):
                return 'class_12'
            if any(k in combined for k in ('10', 'x ', 'ssc', 'matric', 'secondary')):
                return 'class_10'
            return 'class_12'  # default school to 12th

    # Keyword fallback
    if any(k in combined for k in ('10th', 'x ', 'ssc', 'secondary school', 'matric', 'class 10')):
        return 'class_10'
    if any(k in combined for k in ('12th', 'xii', 'hsc', 'higher secondary', 'intermediate', 'class 12')):
        return 'class_12'
    return 'graduation'

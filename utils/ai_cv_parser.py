"""
CV parsing and AI summary generation using Google Gemini REST API.
No SDK required — uses requests directly (works on Python 3.8+).
"""
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)

_PROMPT_TEMPLATE = """You are an expert CV/Resume parser for an Indian student job platform.
Extract all information from the CV text below and return ONLY valid JSON with EXACTLY this structure.
Return null/empty for missing fields, never omit keys.

IMPORTANT RULES:
- education_type MUST be exactly one of: "graduation" (for B.Tech/B.E./B.Sc/M.Tech/MBA/MCA/any degree), "class_12" (for 12th/HSC/Intermediate), "class_10" (for 10th/SSC/Matriculation)
- grade_type MUST be exactly one of: "percentage", "cgpa", or "" (empty string)
- study_mode MUST be exactly one of: "full_time", "part_time", "distance", or "" (empty string)
- For basic.first_name and basic.last_name: split the full name from the resume header
- For college: use the name of the primary college/university where the person is studying/studied
- For degree: e.g. "B.Tech", "B.E.", "MCA", "MBA"
- For branch: e.g. "Computer Science", "Electronics", "Information Technology"
- graduation_year: the year the person graduated or will graduate from their primary degree

{{
  "basic": {{
    "first_name": "", "last_name": "", "phone": "", "email": "",
    "gender": "", "date_of_birth": "YYYY-MM-DD or empty string",
    "current_location": "", "linkedin_url": "", "github_url": "", "portfolio_url": ""
  }},
  "profile_summary": "full professional summary text or empty string",
  "education": [
    {{
      "education_type": "graduation",
      "degree": "B.Tech",
      "specialization": "Computer Science",
      "institute_name": "ABC University",
      "board_or_university": "",
      "start_year": 2020,
      "end_year": 2024,
      "is_pursuing": false,
      "grade_type": "cgpa",
      "grade_value": "8.5",
      "study_mode": "full_time"
    }}
  ],
  "skills": ["Python", "Django"],
  "projects": [{{"title": "", "description": "", "tech_stack": [], "start_month": "Sep 2024", "end_month": "Nov 2024", "is_ongoing": false, "project_url": "", "github_url": ""}}],
  "internships": [{{"company_name": "", "role": "", "description": "", "start_month": "", "end_month": "", "is_ongoing": false, "stipend": "", "location": "", "skills_used": []}}],
  "certifications": [{{"title": "", "issuing_organization": "", "issue_date": "YYYY-MM-DD or empty string", "expiry_date": "YYYY-MM-DD or empty string", "does_not_expire": false, "credential_id": "", "credential_url": ""}}],
  "awards": [{{"title": "", "issuer": "", "date_received": "YYYY-MM-DD or empty string", "description": ""}}],
  "competitive_exams": [{{"exam_name": "", "year": 2023, "score_or_rank": "", "description": ""}}],
  "languages": [{{"language": "", "proficiency": "beginner or proficient or expert", "can_read": true, "can_write": true, "can_speak": true}}],
  "employments": [{{"company_name": "", "job_title": "", "description": "", "start_month": "", "end_month": "", "is_current": false, "location": "", "skills_used": []}}],
  "looking_for": "internship or full-time or part-time or freelance or empty string",
  "college": "",
  "degree": "",
  "branch": "",
  "graduation_year": null,
  "preferred_locations": []
}}

CV TEXT:
{cv_text}"""


def _call_gemini(prompt, api_key, model="gemini-2.0-flash"):
    import time
    url = GEMINI_API_URL.format(model=model, api_key=api_key)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096},
    }
    # Retry up to 3 times on 429 (rate limit) with backoff
    for attempt in range(3):
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 429:
            if attempt < 2:
                wait = (attempt + 1) * 20  # 20s, 40s
                logger.warning("Gemini 429 rate limit, retrying in %ds (attempt %d/3)...", wait, attempt + 1)
                time.sleep(wait)
                continue
            # Parse the error to distinguish RPM vs RPD
            try:
                err_msg = resp.json().get("error", {}).get("message", "")
            except Exception:
                err_msg = ""
            if "quota" in err_msg.lower() or "day" in err_msg.lower():
                raise RuntimeError(
                    "Gemini daily quota exceeded. Your free API key allows ~50 requests/day. "
                    "Wait until tomorrow or upgrade at https://aistudio.google.com/apikey"
                )
            raise RuntimeError(
                "Gemini rate limit hit (too many requests per minute). Wait 60 seconds and try again."
            )
        if resp.status_code in (400, 403, 401):
            msg = resp.json().get("error", {}).get("message", "API error")
            raise RuntimeError(f"Gemini API error: {msg}")
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def parse_cv_with_ai(cv_text):
    """Parse CV text using Gemini and return structured cv_data dict."""
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Gemini API key not configured. Add GEMINI_API_KEY to your .env file.")
    if not cv_text.strip():
        return {}
    try:
        model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
        raw = _call_gemini(_PROMPT_TEMPLATE.format(cv_text=cv_text[:12000]), api_key, model)
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except RuntimeError:
        raise
    except json.JSONDecodeError as exc:
        logger.warning("Gemini returned invalid JSON: %s", exc)
        return {}
    except Exception as exc:
        logger.warning("AI CV parsing failed: %s", exc)
        return {}


def generate_summary_with_ai(profile_data, api_key):
    """Generate a professional profile summary using Gemini."""
    prompt = (
        "You are an expert career counselor. Write a professional profile summary in 3-4 sentences. "
        "Make it compelling and suitable for job applications on LinkedIn or Naukri. "
        "Write in first person. Return only the summary text, no labels or quotes.\n\n"
        f"Student profile data: {json.dumps(profile_data)}"
    )
    model = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
    return _call_gemini(prompt, api_key, model)


def _parse_date(value):
    if not value:
        return None
    try:
        from datetime import date
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def apply_cv_data_to_profile(user, cv_data):
    """Apply parsed cv_data dict to the user's profile models."""
    if user.role != "student":
        return {"updated_sections": [], "profile_completeness": 0, "is_complete": False}

    from apps.accounts.models import (
        StudentProfile, StudentEducation, StudentProject,
        StudentInternship, StudentCertification, StudentAward,
        StudentCompetitiveExam, StudentLanguage, StudentEmployment,
    )

    logger.info("apply_cv_data_to_profile: sections present: %s", list(cv_data.keys()))
    logger.info("apply_cv_data_to_profile: education raw: %s", cv_data.get("education", []))

    updated_sections = []
    basic = cv_data.get("basic", {})

    # ── User model fields (first_name, last_name, phone, college) ────────────
    user_dirty = False
    for field, key in [("first_name", "first_name"), ("last_name", "last_name"),
                       ("phone", "phone")]:
        val = basic.get(key, "")
        if val and not getattr(user, field, ""):
            setattr(user, field, val)
            user_dirty = True
    # college is top-level in cv_data, not inside basic
    college_val = cv_data.get("college", "") or basic.get("college", "")
    if college_val and not user.college:
        user.college = college_val
        user_dirty = True
    if user_dirty:
        user.save()

    try:
        profile = user.student_profile
    except StudentProfile.DoesNotExist:
        return {"updated_sections": [], "profile_completeness": 0, "is_complete": False}

    # ── StudentProfile fields ─────────────────────────────────────────────────
    profile_dirty = False

    # Simple string fields — only fill if currently empty
    simple_fields = [
        ("profile_summary", cv_data.get("profile_summary", "")),
        ("gender",          basic.get("gender", "")),
        ("current_location", basic.get("current_location", "")),
        ("looking_for",     cv_data.get("looking_for", "")),
        ("degree",          cv_data.get("degree", "") or basic.get("degree", "")),
        ("branch",          cv_data.get("branch", "") or basic.get("branch", "")),
        ("github_url",      basic.get("github_url", "")),
        ("portfolio_url",   basic.get("portfolio_url", "")),
    ]
    for attr, val in simple_fields:
        if val and not getattr(profile, attr, ""):
            setattr(profile, attr, val)
            profile_dirty = True

    # linkedin_url lives on StudentProfile too (via github_url / portfolio_url)
    # but also store linkedin on the user's alumni_profile if needed — skip for student
    # Store linkedin in profile_summary context only; no dedicated field on StudentProfile

    # Date of birth
    dob = basic.get("date_of_birth", "")
    if dob and not profile.date_of_birth:
        try:
            from datetime import date
            profile.date_of_birth = date.fromisoformat(str(dob)[:10])
            profile_dirty = True
        except (ValueError, TypeError):
            pass

    # Graduation year — pull from education list if not in top-level
    grad_year = cv_data.get("graduation_year")
    if not grad_year:
        for edu in cv_data.get("education", []):
            if edu.get("end_year"):
                grad_year = edu["end_year"]
                break
    if grad_year and not profile.graduation_year:
        try:
            profile.graduation_year = int(str(grad_year).strip())
            profile_dirty = True
        except (ValueError, TypeError):
            pass

    if cv_data.get("preferred_locations") and not profile.preferred_locations:
        profile.preferred_locations = cv_data["preferred_locations"]
        profile_dirty = True

    if cv_data.get("skills") and not profile.skills:
        profile.skills = cv_data["skills"]
        profile_dirty = True

    if profile_dirty:
        profile.save()
        updated_sections.append("basic_info")

    # Education
    edu_created = False

    def _to_int(val):
        try:
            return int(val) if val not in (None, "", "null") else None
        except (ValueError, TypeError):
            return None

    for edu in cv_data.get("education", []):
        institute = edu.get("institute_name", "").strip()
        degree = edu.get("degree", "").strip()

        # Normalize education_type — Gemini sometimes returns non-standard values
        raw_type = str(edu.get("education_type", "")).lower().strip()
        if any(k in raw_type for k in ("12", "xii", "hsc", "higher secondary", "intermediate", "class_12")):
            edu_type = "class_12"
        elif any(k in raw_type for k in ("10", "x", "ssc", "secondary", "matric", "class_10")):
            edu_type = "class_10"
        else:
            edu_type = "graduation"  # default: covers B.Tech, M.Tech, MBA, etc.

        # Normalize grade_type
        raw_grade = str(edu.get("grade_type", "")).lower()
        grade_type = "cgpa" if "cgpa" in raw_grade or "gpa" in raw_grade else ("percentage" if "percent" in raw_grade else "")

        # Normalize study_mode
        raw_mode = str(edu.get("study_mode", "")).lower()
        if "part" in raw_mode:
            study_mode = "part_time"
        elif "distance" in raw_mode or "online" in raw_mode:
            study_mode = "distance"
        else:
            study_mode = "full_time"

        # Skip only if institute is missing
        if not institute:
            continue

        # Duplicate check: match on institute + education_type only
        if not StudentEducation.objects.filter(
            user=user,
            institute_name__iexact=institute,
            education_type=edu_type,
        ).exists():
            StudentEducation.objects.create(
                user=user,
                education_type=edu_type,
                degree=degree,
                specialization=edu.get("specialization", ""),
                institute_name=institute,
                board_or_university=edu.get("board_or_university", ""),
                start_year=_to_int(edu.get("start_year")),
                end_year=_to_int(edu.get("end_year")),
                is_pursuing=bool(edu.get("is_pursuing", False)),
                grade_type=grade_type,
                grade_value=str(edu.get("grade_value", "") or ""),
                study_mode=study_mode,
            )
            edu_created = True
    if edu_created:
        updated_sections.append("education")

    # Projects
    proj_created = False
    for proj in cv_data.get("projects", []):
        title = proj.get("title", "").strip()
        if not title:
            continue
        if not StudentProject.objects.filter(user=user, title__iexact=title).exists():
            StudentProject.objects.create(
                user=user, title=title, description=proj.get("description", ""),
                tech_stack=proj.get("tech_stack", []),
                start_month=proj.get("start_month", ""),
                end_month="Present" if proj.get("is_ongoing") else proj.get("end_month", ""),
                is_ongoing=bool(proj.get("is_ongoing", False)),
                project_url=proj.get("project_url", ""), github_url=proj.get("github_url", ""),
            )
            proj_created = True
    if proj_created:
        updated_sections.append("projects")

    # Internships
    intern_created = False
    for intern in cv_data.get("internships", []):
        company = intern.get("company_name", "").strip()
        role = intern.get("role", "").strip()
        if not company:
            continue
        if not StudentInternship.objects.filter(user=user, company_name__iexact=company, role__iexact=role).exists():
            StudentInternship.objects.create(
                user=user, company_name=company, role=role,
                description=intern.get("description", ""),
                start_month=intern.get("start_month", ""), end_month=intern.get("end_month", ""),
                is_ongoing=bool(intern.get("is_ongoing", False)),
                stipend=intern.get("stipend", ""), location=intern.get("location", ""),
                skills_used=intern.get("skills_used", []),
            )
            intern_created = True
    if intern_created:
        updated_sections.append("internships")

    # Certifications
    cert_created = False
    for cert in cv_data.get("certifications", []):
        title = cert.get("title", "").strip()
        org = cert.get("issuing_organization", "").strip()
        if not title:
            continue
        if not StudentCertification.objects.filter(user=user, title__iexact=title, issuing_organization__iexact=org).exists():
            StudentCertification.objects.create(
                user=user, title=title, issuing_organization=org,
                issue_date=_parse_date(cert.get("issue_date")),
                expiry_date=None if cert.get("does_not_expire") else _parse_date(cert.get("expiry_date")),
                does_not_expire=bool(cert.get("does_not_expire", False)),
                credential_id=cert.get("credential_id", ""), credential_url=cert.get("credential_url", ""),
            )
            cert_created = True
    if cert_created:
        updated_sections.append("certifications")

    # Awards
    award_created = False
    for award in cv_data.get("awards", []):
        title = award.get("title", "").strip()
        if not title:
            continue
        if not StudentAward.objects.filter(user=user, title__iexact=title).exists():
            StudentAward.objects.create(
                user=user, title=title, issuer=award.get("issuer", ""),
                date_received=_parse_date(award.get("date_received")),
                description=award.get("description", ""),
            )
            award_created = True
    if award_created:
        updated_sections.append("awards")

    # Competitive Exams
    exam_created = False
    for exam in cv_data.get("competitive_exams", []):
        name = exam.get("exam_name", "").strip()
        year = exam.get("year")
        if not name:
            continue
        if not StudentCompetitiveExam.objects.filter(user=user, exam_name__iexact=name, year=year).exists():
            StudentCompetitiveExam.objects.create(
                user=user, exam_name=name, year=year,
                score_or_rank=exam.get("score_or_rank", ""),
                description=exam.get("description", ""),
            )
            exam_created = True
    if exam_created:
        updated_sections.append("competitive_exams")

    # Languages
    lang_created = False
    for lang in cv_data.get("languages", []):
        language = lang.get("language", "").strip()
        if not language:
            continue
        if not StudentLanguage.objects.filter(user=user, language__iexact=language).exists():
            StudentLanguage.objects.create(
                user=user, language=language,
                proficiency=lang.get("proficiency", "proficient"),
                can_read=bool(lang.get("can_read", True)),
                can_write=bool(lang.get("can_write", True)),
                can_speak=bool(lang.get("can_speak", True)),
            )
            lang_created = True
    if lang_created:
        updated_sections.append("languages")

    # Employment
    emp_created = False
    for emp in cv_data.get("employments", []):
        company = emp.get("company_name", "").strip()
        job_title = emp.get("job_title", "").strip()
        if not company:
            continue
        if not StudentEmployment.objects.filter(user=user, company_name__iexact=company, job_title__iexact=job_title).exists():
            StudentEmployment.objects.create(
                user=user, company_name=company, job_title=job_title,
                description=emp.get("description", ""),
                start_month=emp.get("start_month", ""), end_month=emp.get("end_month", ""),
                is_current=bool(emp.get("is_current", False)),
                location=emp.get("location", ""), skills_used=emp.get("skills_used", []),
            )
            emp_created = True
    if emp_created:
        updated_sections.append("employments")

    from utils.profile_helpers import get_full_profile_completeness
    completeness = get_full_profile_completeness(user)
    return {
        "updated_sections": updated_sections,
        "profile_completeness": completeness["percentage"],
        "is_complete": completeness["is_complete"],
    }

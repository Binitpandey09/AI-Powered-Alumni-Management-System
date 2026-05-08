"""
AI-powered skill matching using Gemini 2.0 Flash.

Replaces the simple string-comparison skill_matcher with a genuine semantic
analysis that considers:
  - Student's full profile (degree, branch, graduation year, skills, summary)
  - Student's resume text (extracted from uploaded PDF/DOCX if available)
  - Full job description + required skills + preferred skills + experience level

Returns the SAME dict format as calculate_skill_match() in skill_matcher.py,
so it is a drop-in replacement. Falls back to the old algorithm if the AI
call fails or times out.
"""

import json
import logging
import re

from django.conf import settings

from utils.skill_matcher import calculate_skill_match

logger = logging.getLogger(__name__)

# Characters to keep when trimming resume (avoid sending 10 000+ token resumes)
_MAX_RESUME_CHARS = 3000
_MAX_JD_CHARS = 2000


# ── Resume extraction ─────────────────────────────────────────────────────────

def _extract_resume_text(student_profile) -> str:
    """Try to read resume text from the student's uploaded file. Returns '' on failure."""
    try:
        resume_field = student_profile.resume_file
        if not resume_field:
            return ''
        # Django FileField — open in binary mode
        with resume_field.open('rb') as f:
            raw = f.read()

        import io
        filename = resume_field.name or ''
        from utils.cv_parser import extract_cv_text
        text = extract_cv_text(io.BytesIO(raw), filename)
        return text[:_MAX_RESUME_CHARS].strip()
    except Exception as exc:
        logger.debug("Resume extraction skipped: %s", exc)
        return ''


# ── Build Gemini prompt ───────────────────────────────────────────────────────

def _build_prompt(student_user, student_profile, referral, resume_text: str) -> str:
    skills_str = ', '.join(student_profile.skills or []) or 'Not listed'
    req_skills_str  = ', '.join(referral.required_skills or []) or 'Not specified'
    pref_skills_str = ', '.join(referral.preferred_skills or []) or 'None'
    jd = (referral.job_description or '')[:_MAX_JD_CHARS].strip()

    resume_section = (
        f"\nSTUDENT RESUME (extracted text):\n{resume_text}\n"
        if resume_text else
        "\n(No resume uploaded — match based on profile only)\n"
    )

    profile_section = f"""STUDENT PROFILE:
- Degree: {student_profile.degree or 'Not specified'}
- Branch / Major: {student_profile.branch or 'Not specified'}
- Graduation Year: {student_profile.graduation_year or 'Not specified'}
- Skills listed on profile: {skills_str}
- Profile summary: {(getattr(student_profile, 'profile_summary', None) or 'Not provided')[:500]}
{resume_section}"""

    job_section = f"""JOB REQUIREMENTS:
- Job Title: {referral.job_title}
- Company: {referral.company_name}
- Experience Level: {referral.experience_level or 'Not specified'}
- Work Type: {referral.work_type or 'Not specified'}
- Required Skills: {req_skills_str}
- Preferred Skills: {pref_skills_str}
- Job Description:
{jd or 'Not provided'}"""

    return f"""You are a professional technical recruiter AI. Analyse how well the student's profile matches the job description and skills.

{profile_section}

{job_section}

INSTRUCTIONS:
1. Compare the student's skills, experience, education, and resume against the job requirements.
2. Use SEMANTIC matching — "Python" matches "Python3", "ML" matches "Machine Learning", "JS" matches "JavaScript".
3. Consider the full job description context, not just the skill keywords.
4. Score strictly: 0-39 = poor fit, 40-69 = moderate fit, 70-89 = good fit, 90-100 = excellent fit.
5. Only include a required skill in "matched_skills" if you are confident the student has it.
6. Only include it in "missing_skills" if the student clearly lacks it.

Return ONLY a valid JSON object with these exact keys (no markdown, no extra text):
{{
  "score": <integer 0-100>,
  "matched_skills": <list of required skills the student demonstrably has>,
  "missing_skills": <list of required skills the student clearly lacks>,
  "preferred_matched": <list of preferred skills the student has>,
  "reason": <one concise sentence summarising the match quality>
}}"""


# ── Call Gemini ───────────────────────────────────────────────────────────────

def _call_groq(prompt: str) -> dict:
    """Call Groq (Llama-3.3-70B) and return parsed JSON."""
    from groq import Groq

    api_key    = getattr(settings, 'GROQ_API_KEY', '') or ''
    model_name = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')

    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a skill matching AI. Always respond with valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=512,
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


# ── Main public function ──────────────────────────────────────────────────────

def ai_calculate_skill_match(student_user, referral) -> dict:
    """
    AI-powered replacement for calculate_skill_match().

    Args:
        student_user : User instance (must have .student_profile)
        referral     : Referral instance

    Returns:
        dict with keys: score, matched_skills, missing_skills,
                        preferred_matched, can_apply, reason
        (same format as calculate_skill_match in skill_matcher.py)
    """
    try:
        student_profile = student_user.student_profile
    except Exception:
        # No profile — hard fallback
        return calculate_skill_match([], referral.required_skills, referral.preferred_skills)

    # If no required skills, nothing to match
    if not referral.required_skills:
        return {
            'score': 100,
            'matched_skills': [],
            'missing_skills': [],
            'preferred_matched': [],
            'can_apply': True,
            'reason': 'No specific skills required for this role.',
        }

    student_skills = student_profile.skills or []
    resume_text = _extract_resume_text(student_profile)

    try:
        prompt = _build_prompt(student_user, student_profile, referral, resume_text)
        data = _call_groq(prompt)

        score = int(data.get('score', 0))
        score = max(0, min(100, score))  # clamp to 0-100

        result = {
            'score': score,
            'matched_skills': data.get('matched_skills') or [],
            'missing_skills': data.get('missing_skills') or [],
            'preferred_matched': data.get('preferred_matched') or [],
            'can_apply': score >= 40,
            'reason': data.get('reason', ''),
        }

        logger.info(
            "AI match: user=%s referral=%s score=%s",
            student_user.id, referral.id, score,
        )
        return result

    except Exception as exc:
        logger.warning(
            "AI skill match failed (user=%s, referral=%s): %s — falling back to keyword match.",
            student_user.id, referral.id, exc,
        )
        # Graceful fallback to the original algorithm
        return calculate_skill_match(
            student_skills,
            referral.required_skills,
            referral.preferred_skills,
        )

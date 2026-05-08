"""
utils/ai_tools_service.py
Central AI service layer for all 4 AI Career Tools.
Uses Groq (Llama-3.3-70B) — free tier, 14,400 req/day, fast responses.
"""
import json
import re
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


# ── Groq helper ───────────────────────────────────────────────

def _call_groq(prompt: str, max_tokens: int = 2048, temperature: float = 0.3) -> dict:
    """
    Send a prompt to Groq (Llama-3.3-70B) and return parsed JSON.
    Groq uses the OpenAI-compatible API — response_format=json_object gives clean JSON.
    Raises ValueError on parse failure, Exception on API failure.
    """
    from groq import Groq

    api_key    = getattr(settings, 'GROQ_API_KEY', '') or ''
    model_name = getattr(settings, 'GROQ_MODEL', 'llama-3.3-70b-versatile')

    if not api_key:
        raise ValueError("GROQ_API_KEY is not configured in settings.")

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "You are a helpful AI assistant. Always respond with valid JSON only. No markdown, no explanation outside JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        response_format={"type": "json_object"},  # Guarantees clean JSON output
    )

    raw = response.choices[0].message.content.strip()

    # Strip any accidental markdown fences
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    return json.loads(raw)


# ══════════════════════════════════════════════════════════════
# SERVICE 1 — Resume Score Checker
# ══════════════════════════════════════════════════════════════

def score_resume(resume_text, student_profile_data, job_role=None):
    """
    Analyzes a student resume and returns a detailed ATS score report.

    resume_text            : str  — raw text from PDF/DOC (or '' if no file)
    student_profile_data   : dict — skills, education, projects, internships
    job_role               : str  — optional target role

    Returns {"success": True, "data": {...}} or {"success": False, "error": "..."}
    """
    job_context = f"Target role: {job_role}" if job_role else "General software engineering role"

    prompt = f"""You are an expert resume reviewer with 15 years of experience at top tech companies.
Analyze this resume and return a detailed score report.
{job_context}

RESUME TEXT:
{resume_text[:4000] if resume_text else "(No resume file — use profile data below)"}

STUDENT PROFILE:
- Skills: {', '.join(student_profile_data.get('skills', []))}
- Education: {student_profile_data.get('education_summary', 'Not provided')}
- Projects count: {student_profile_data.get('projects_count', 0)}
- Internships count: {student_profile_data.get('internships_count', 0)}

Return ONLY this JSON (no other text):
{{
  "overall_score": <integer 0-100>,
  "section_scores": {{
    "contact_info": <integer 0-10>,
    "education":    <integer 0-20>,
    "skills":       <integer 0-20>,
    "experience":   <integer 0-25>,
    "projects":     <integer 0-15>,
    "formatting":   <integer 0-10>
  }},
  "strengths":   ["<strength 1>", "<strength 2>", "<strength 3>"],
  "weaknesses":  ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
  "improvements": [
    {{"section": "<section>", "issue": "<issue>", "suggestion": "<fix>"}},
    {{"section": "<section>", "issue": "<issue>", "suggestion": "<fix>"}},
    {{"section": "<section>", "issue": "<issue>", "suggestion": "<fix>"}}
  ],
  "ats_score": <integer 0-100>,
  "ats_keywords_found":   ["<keyword>"],
  "ats_keywords_missing": ["<keyword>"],
  "summary": "<2-3 sentence overall assessment>",
  "grade": "<A/B/C/D/F>"
}}"""

    try:
        data = _call_groq(prompt, max_tokens=1500, temperature=0.3)
        return {"success": True, "data": data}
    except json.JSONDecodeError as e:
        logger.error("score_resume JSON parse error: %s", e)
        return {"success": False, "error": "AI response parsing failed. Please try again."}
    except Exception as e:
        logger.error("score_resume error: %s", e)
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# SERVICE 2 — Resume Builder
# ══════════════════════════════════════════════════════════════

def build_resume(student_profile_data, target_role=None, template_style='professional'):
    """
    Generates a complete ATS-optimised professional resume from profile data.

    Returns {"success": True, "data": {resume_sections, tailoring_notes, ats_tips}}
    """
    role_context = (
        f"Tailor this resume specifically for: {target_role}"
        if target_role
        else "Create a general software engineering resume"
    )

    prompt = f"""You are an expert resume writer who creates ATS-optimized resumes for tech roles.
{role_context}

STUDENT DATA:
Name:           {student_profile_data.get('name', '')}
Email:          {student_profile_data.get('email', '')}
Phone:          {student_profile_data.get('phone', '')}
Location:       {student_profile_data.get('location', '')}
Skills:         {', '.join(student_profile_data.get('skills', []))}
Education:      {json.dumps(student_profile_data.get('education', []))}
Projects:       {json.dumps(student_profile_data.get('projects', []))}
Internships:    {json.dumps(student_profile_data.get('internships', []))}
Certifications: {json.dumps(student_profile_data.get('certifications', []))}
Summary:        {student_profile_data.get('profile_summary', '')}
GitHub:         {student_profile_data.get('github_url', '')}

Return ONLY this JSON (no other text):
{{
  "resume_sections": {{
    "header": {{
      "name":     "<full name>",
      "email":    "<email>",
      "phone":    "<phone>",
      "location": "<city, state>",
      "github":   "<github url>"
    }},
    "summary": "<3-4 line compelling professional summary tailored to the role>",
    "education": [
      {{"degree": "<degree>", "institution": "<college>", "year": "<year>", "grade": "<CGPA/percentage>"}}
    ],
    "skills": {{
      "technical": ["<skill>"],
      "tools":     ["<tool>"],
      "soft":      ["<soft skill>"]
    }},
    "experience": [
      {{"title": "<role>", "company": "<company>", "duration": "<dates>", "bullets": ["<bullet 1>", "<bullet 2>", "<bullet 3>"]}}
    ],
    "projects": [
      {{"name": "<name>", "description": "<1 line>", "tech_stack": ["<tech>"], "bullets": ["<bullet 1>", "<bullet 2>"]}}
    ],
    "certifications": [
      {{"name": "<cert>", "issuer": "<issuer>", "year": "<year>"}}
    ],
    "achievements": ["<achievement 1>", "<achievement 2>"]
  }},
  "tailoring_notes":       "<how this resume was tailored for the role>",
  "ats_optimization_tips": ["<tip 1>", "<tip 2>", "<tip 3>"]
}}"""

    try:
        data = _call_groq(prompt, max_tokens=2500, temperature=0.4)
        return {"success": True, "data": data}
    except json.JSONDecodeError as e:
        logger.error("build_resume JSON parse error: %s", e)
        return {"success": False, "error": "AI response parsing failed. Please try again."}
    except Exception as e:
        logger.error("build_resume error: %s", e)
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# SERVICE 3a — AI Interviewer: Generate Questions
# ══════════════════════════════════════════════════════════════

def generate_interview_questions(student_profile_data, job_role, num_questions=5):
    """
    Generates personalised interview questions for the candidate.
    Called at START of interview session.

    Returns {"success": True, "data": {questions, job_role, total_questions, estimated_duration_minutes}}
    """
    prompt = f"""You are a senior technical interviewer at a top tech company.
Generate {num_questions} interview questions for a candidate applying for: {job_role}

CANDIDATE PROFILE:
Skills:           {', '.join(student_profile_data.get('skills', []))}
Education:        {student_profile_data.get('education_summary', '')}
Projects:         {student_profile_data.get('projects_summary', '')}
Experience level: {student_profile_data.get('experience_level', 'fresher')}

Mix: technical questions (based on their skills), behavioural questions, one HR question.
Make questions progressively harder. Make them specific and realistic.

Return ONLY this JSON (no other text):
{{
  "questions": [
    {{
      "id": 1,
      "type": "technical",
      "difficulty": "medium",
      "question": "<the question>",
      "hint": "<what a strong answer should cover>",
      "time_limit_seconds": 180
    }}
  ],
  "job_role": "{job_role}",
  "total_questions": {num_questions},
  "estimated_duration_minutes": {num_questions * 4}
}}"""

    try:
        data = _call_groq(prompt, max_tokens=1500, temperature=0.5)
        return {"success": True, "data": data}
    except json.JSONDecodeError as e:
        logger.error("generate_interview_questions JSON parse error: %s", e)
        return {"success": False, "error": "AI response parsing failed. Please try again."}
    except Exception as e:
        logger.error("generate_interview_questions error: %s", e)
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# SERVICE 3b — AI Interviewer: Evaluate Single Answer
# ══════════════════════════════════════════════════════════════

def evaluate_interview_answer(question, answer, job_role, student_skills):
    """
    Evaluates one interview answer and returns instant feedback.
    Called AFTER each answer is submitted.

    Returns {"success": True, "data": {score, feedback, strengths, improvements,
             ideal_answer_points, follow_up_question}}
    """
    prompt = f"""You are a senior technical interviewer evaluating a candidate's answer.
Give honest, specific, constructive feedback.

Job Role: {job_role}
Question: {question}
Candidate's Answer: {answer[:1000] if answer else "(No answer provided)"}
Candidate's Skills: {', '.join(student_skills[:10])}

Return ONLY this JSON (no other text):
{{
  "score": <integer 0-10>,
  "feedback": "<2-3 sentence overall feedback>",
  "strengths":            ["<strength 1>", "<strength 2>"],
  "improvements":         ["<improvement 1>", "<improvement 2>"],
  "ideal_answer_points":  ["<key point 1>", "<key point 2>", "<key point 3>"],
  "follow_up_question":   "<optional follow-up question>"
}}"""

    try:
        data = _call_groq(prompt, max_tokens=600, temperature=0.3)
        return {"success": True, "data": data}
    except json.JSONDecodeError as e:
        logger.error("evaluate_interview_answer JSON parse error: %s", e)
        return {"success": False, "error": "AI response parsing failed. Please try again."}
    except Exception as e:
        logger.error("evaluate_interview_answer error: %s", e)
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# SERVICE 3c — AI Interviewer: Generate Final Report
# ══════════════════════════════════════════════════════════════

def generate_interview_report(questions_and_answers, job_role, student_name):
    """
    Generates a comprehensive post-interview performance report.
    Called at the END after all questions are answered.

    questions_and_answers: list of {question, answer, score, feedback, question_type}

    Returns {"success": True, "data": {overall_score, grade, performance_by_type,
             top_strengths, areas_to_improve, recommended_resources,
             hiring_recommendation, detailed_feedback, next_steps}}
    """
    qa_summary = json.dumps([
        {
            "question":       qa.get("question", ""),
            "answer_summary": qa.get("answer", "")[:200],
            "score":          qa.get("score", 0),
            "type":           qa.get("question_type", "technical"),
        }
        for qa in questions_and_answers
    ])

    prompt = f"""You are a senior interviewer writing a post-interview evaluation report.

Candidate: {student_name}
Role applied for: {job_role}

Questions and Answers Summary:
{qa_summary}

Return ONLY this JSON (no other text):
{{
  "overall_score": <integer 0-100>,
  "grade": "<A/B/C/D/F>",
  "performance_by_type": {{
    "technical":  <integer 0-100>,
    "behavioral": <integer 0-100>,
    "hr":         <integer 0-100>
  }},
  "top_strengths":    ["<strength 1>", "<strength 2>", "<strength 3>"],
  "areas_to_improve": ["<area 1>", "<area 2>", "<area 3>"],
  "recommended_resources": [
    {{"topic": "<topic>", "resource": "<specific book/course/platform>"}},
    {{"topic": "<topic>", "resource": "<specific resource>"}}
  ],
  "hiring_recommendation": "<Strong Hire/Hire/Maybe/No Hire>",
  "detailed_feedback": "<2-3 paragraph honest assessment>",
  "next_steps": ["<step 1>", "<step 2>", "<step 3>"]
}}"""

    try:
        data = _call_groq(prompt, max_tokens=1200, temperature=0.3)
        return {"success": True, "data": data}
    except json.JSONDecodeError as e:
        logger.error("generate_interview_report JSON parse error: %s", e)
        return {"success": False, "error": "AI response parsing failed. Please try again."}
    except Exception as e:
        logger.error("generate_interview_report error: %s", e)
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# SERVICE 4 — Skill Gap Analyzer
# ══════════════════════════════════════════════════════════════

def analyze_skill_gap(student_skills, target_role, current_education=None):
    """
    Compares student skills vs industry requirements for a target role.
    Returns a readiness score, gap list, and week-by-week learning roadmap.

    Returns {"success": True, "data": {readiness_score, readiness_level,
             skills_to_learn, learning_roadmap, total_weeks_to_ready,
             job_market_insight, similar_roles_easier}}
    """
    prompt = f"""You are a career coach and tech industry expert helping students close skill gaps.
Give specific, actionable learning roadmaps with real free resources.

Target role: {target_role}
Student's current skills: {', '.join(student_skills) if student_skills else 'None listed'}
Education: {current_education or 'Not specified'}

Return ONLY this JSON (no other text):
{{
  "target_role": "{target_role}",
  "readiness_score": <integer 0-100>,
  "readiness_level": "<Not Ready/Getting There/Almost Ready/Job Ready>",
  "current_skills_relevant": ["<relevant skill>"],
  "skills_to_learn": [
    {{
      "skill":             "<skill name>",
      "priority":          "<Critical/High/Medium/Nice to Have>",
      "why_needed":        "<1 sentence>",
      "estimated_weeks":   <integer 1-12>,
      "free_resources":    ["<YouTube channel or free course>", "<docs link>"],
      "paid_resources":    ["<Udemy/book>"]
    }}
  ],
  "learning_roadmap": [
    {{
      "week":      1,
      "focus":     "<focus area>",
      "skills":    ["<skill>"],
      "milestone": "<what student achieves after this week>"
    }}
  ],
  "total_weeks_to_ready": <integer>,
  "job_market_insight":   "<2-3 sentences about demand for this role>",
  "similar_roles_easier": ["<easier role 1>", "<easier role 2>"]
}}"""

    try:
        data = _call_groq(prompt, max_tokens=2000, temperature=0.4)
        return {"success": True, "data": data}
    except json.JSONDecodeError as e:
        logger.error("analyze_skill_gap JSON parse error: %s", e)
        return {"success": False, "error": "AI response parsing failed. Please try again."}
    except Exception as e:
        logger.error("analyze_skill_gap error: %s", e)
        return {"success": False, "error": str(e)}

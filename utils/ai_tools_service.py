"""
utils/ai_tools_service.py
Central AI service layer for all 4 AI tools.
Uses OpenAI gpt-4o-mini for all operations.
"""
import json
import os
from openai import OpenAI
from django.conf import settings


def get_openai_client():
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _strip_markdown(raw: str) -> str:
    """Strip markdown code fences from OpenAI response before json.loads()."""
    raw = raw.strip()
    if raw.startswith("```"):
        # Remove opening fence (```json or ```)
        raw = raw[raw.index("\n") + 1:] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[: raw.rfind("```")]
    return raw.strip()


# ══════════════════════════════════════════════════════════════
# SERVICE 1 — Resume Scorer
# ══════════════════════════════════════════════════════════════

def score_resume(resume_text, student_profile_data, job_role=None):
    """
    Analyzes a student resume and gives a detailed score with feedback.

    resume_text: str — raw text extracted from the resume PDF/doc
    student_profile_data: dict — student profile including skills, education, projects
    job_role: str — optional target job role (e.g. "Software Engineer at Google")

    Returns dict:
    {
        "overall_score": int (0-100),
        "section_scores": {
            "contact_info": int (0-10),
            "education": int (0-20),
            "skills": int (0-20),
            "experience": int (0-25),
            "projects": int (0-15),
            "formatting": int (0-10)
        },
        "strengths": [str, str, str],
        "weaknesses": [str, str, str],
        "improvements": [{"section": str, "issue": str, "suggestion": str}],
        "ats_score": int (0-100),
        "ats_keywords_found": [str],
        "ats_keywords_missing": [str],
        "summary": str,
        "grade": str ("A"/"B"/"C"/"D"/"F")
    }
    """
    client = get_openai_client()

    system_prompt = (
        "You are an expert resume reviewer with 15 years of experience at top tech companies. "
        "You analyze resumes for software engineering and tech roles. "
        "You give honest, actionable feedback. "
        "You ALWAYS respond with valid JSON only. No markdown, no explanation outside JSON."
    )

    job_context = f"Target role: {job_role}" if job_role else "General software engineering role"

    user_prompt = f"""Analyze this resume and return a detailed JSON score report.
{job_context}

RESUME TEXT:
{resume_text[:4000]}

STUDENT PROFILE DATA:
- Skills: {', '.join(student_profile_data.get('skills', []))}
- Education: {student_profile_data.get('education_summary', 'Not provided')}
- Projects count: {student_profile_data.get('projects_count', 0)}
- Internships count: {student_profile_data.get('internships_count', 0)}

Return this EXACT JSON structure (no other text):
{{
  "overall_score": <integer 0-100>,
  "section_scores": {{
    "contact_info": <integer 0-10>,
    "education": <integer 0-20>,
    "skills": <integer 0-20>,
    "experience": <integer 0-25>,
    "projects": <integer 0-15>,
    "formatting": <integer 0-10>
  }},
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
  "improvements": [
    {{"section": "<section name>", "issue": "<specific issue>", "suggestion": "<actionable fix>"}},
    {{"section": "<section name>", "issue": "<specific issue>", "suggestion": "<actionable fix>"}},
    {{"section": "<section name>", "issue": "<specific issue>", "suggestion": "<actionable fix>"}}
  ],
  "ats_score": <integer 0-100>,
  "ats_keywords_found": ["<keyword>", "<keyword>"],
  "ats_keywords_missing": ["<keyword>", "<keyword>"],
  "summary": "<2-3 sentence overall assessment>",
  "grade": "<A/B/C/D/F>"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        raw = response.choices[0].message.content
        result = json.loads(_strip_markdown(raw))
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"AI response parsing failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"AI service error: {str(e)}"}


# ══════════════════════════════════════════════════════════════
# SERVICE 2 — Resume Builder
# ══════════════════════════════════════════════════════════════

def build_resume(student_profile_data, target_role=None, template_style='professional'):
    """
    Generates a complete professional resume from student profile data.

    student_profile_data: dict with all profile sections
    target_role: str — optional target job role for tailoring
    template_style: str — 'professional', 'modern', 'minimal'

    Returns dict with resume_sections, tailoring_notes, ats_optimization_tips
    """
    client = get_openai_client()

    system_prompt = (
        "You are an expert resume writer who creates ATS-optimized resumes for tech roles. "
        "You write concise, impactful bullet points using the STAR method. "
        "You ALWAYS respond with valid JSON only. No markdown, no explanation outside JSON."
    )

    role_context = (
        f"Tailor this resume for: {target_role}"
        if target_role
        else "Create a general software engineering resume"
    )

    user_prompt = f"""Create a complete professional resume from this student profile data.
{role_context}

STUDENT DATA:
Name: {student_profile_data.get('name', '')}
Email: {student_profile_data.get('email', '')}
Phone: {student_profile_data.get('phone', '')}
Location: {student_profile_data.get('location', '')}
Skills: {', '.join(student_profile_data.get('skills', []))}
Education: {json.dumps(student_profile_data.get('education', []))}
Projects: {json.dumps(student_profile_data.get('projects', []))}
Internships: {json.dumps(student_profile_data.get('internships', []))}
Certifications: {json.dumps(student_profile_data.get('certifications', []))}
Summary: {student_profile_data.get('profile_summary', '')}
GitHub: {student_profile_data.get('github_url', '')}

Return this EXACT JSON structure (no other text):
{{
  "resume_sections": {{
    "header": {{
      "name": "<full name>",
      "email": "<email>",
      "phone": "<phone>",
      "location": "<city, state>",
      "github": "<github url if available>"
    }},
    "summary": "<3-4 line compelling professional summary tailored to the role>",
    "education": [
      {{"degree": "<degree name>", "institution": "<college name>", "year": "<grad year>", "grade": "<CGPA or percentage>"}}
    ],
    "skills": {{
      "technical": ["<skill>", "<skill>"],
      "tools": ["<tool>", "<tool>"],
      "soft": ["Communication", "Problem Solving"]
    }},
    "experience": [
      {{"title": "<role>", "company": "<company>", "duration": "<dates>", "bullets": ["<bullet 1>", "<bullet 2>", "<bullet 3>"]}}
    ],
    "projects": [
      {{"name": "<project name>", "description": "<1 line description>", "tech_stack": ["<tech>", "<tech>"], "bullets": ["<bullet 1>", "<bullet 2>"]}}
    ],
    "certifications": [
      {{"name": "<cert name>", "issuer": "<issuer>", "year": "<year>"}}
    ],
    "achievements": ["<achievement 1>", "<achievement 2>"]
  }},
  "tailoring_notes": "<how this resume was tailored>",
  "ats_optimization_tips": ["<tip 1>", "<tip 2>", "<tip 3>"]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2500,
            temperature=0.4,
        )
        raw = response.choices[0].message.content
        result = json.loads(_strip_markdown(raw))
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"AI response parsing failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"AI service error: {str(e)}"}


# ══════════════════════════════════════════════════════════════
# SERVICE 3 — AI Interviewer
# ══════════════════════════════════════════════════════════════

def generate_interview_questions(student_profile_data, job_role, num_questions=5):
    """
    Generates personalized interview questions based on student profile and target role.
    Called at the START of an interview session.

    Returns dict with questions list, job_role, total_questions, estimated_duration_minutes
    """
    client = get_openai_client()

    system_prompt = (
        "You are a senior technical interviewer at a top tech company. "
        "You create realistic, role-specific interview questions. "
        "You ALWAYS respond with valid JSON only."
    )

    user_prompt = f"""Generate {num_questions} interview questions for this candidate applying for: {job_role}

CANDIDATE PROFILE:
Skills: {', '.join(student_profile_data.get('skills', []))}
Education: {student_profile_data.get('education_summary', '')}
Projects: {student_profile_data.get('projects_summary', '')}
Experience level: {student_profile_data.get('experience_level', 'fresher')}

Create a mix of: technical questions (based on their skills), behavioral questions, and one HR question.
Questions should be progressively harder.

Return this EXACT JSON (no other text):
{{
  "questions": [
    {{
      "id": 1,
      "type": "technical",
      "difficulty": "medium",
      "question": "<the question>",
      "hint": "<what a good answer should cover>",
      "time_limit_seconds": 180
    }}
  ],
  "job_role": "{job_role}",
  "total_questions": {num_questions},
  "estimated_duration_minutes": {num_questions * 4}
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1500,
            temperature=0.5,
        )
        raw = response.choices[0].message.content
        result = json.loads(_strip_markdown(raw))
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"AI response parsing failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def evaluate_interview_answer(question, answer, job_role, student_skills):
    """
    Evaluates a single interview answer and gives feedback.
    Called after each answer is submitted.

    Returns dict with score, feedback, strengths, improvements,
    ideal_answer_points, follow_up_question
    """
    client = get_openai_client()

    system_prompt = (
        "You are a senior technical interviewer evaluating a candidate's answer. "
        "Give honest, constructive feedback. Be specific. "
        "You ALWAYS respond with valid JSON only."
    )

    user_prompt = f"""Evaluate this interview answer.
Job Role: {job_role}
Question: {question}
Candidate's Answer: {answer[:1000]}
Candidate's Skills: {', '.join(student_skills[:10])}

Return this EXACT JSON (no other text):
{{
  "score": <integer 0-10>,
  "feedback": "<2-3 sentence overall feedback>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvements": ["<improvement 1>", "<improvement 2>"],
  "ideal_answer_points": ["<key point 1>", "<key point 2>", "<key point 3>"],
  "follow_up_question": "<optional follow-up question>"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=600,
            temperature=0.3,
        )
        raw = response.choices[0].message.content
        result = json.loads(_strip_markdown(raw))
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"AI response parsing failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def generate_interview_report(questions_and_answers, job_role, student_name):
    """
    Generates a comprehensive interview performance report.
    Called at the END of the interview after all questions are answered.

    questions_and_answers: list of dicts with question, answer, score, feedback

    Returns dict with overall_score, grade, performance_by_type, top_strengths,
    areas_to_improve, recommended_resources, hiring_recommendation,
    detailed_feedback, next_steps
    """
    client = get_openai_client()

    system_prompt = (
        "You are a senior interviewer writing a post-interview evaluation report. "
        "You ALWAYS respond with valid JSON only."
    )

    qa_summary = json.dumps([
        {
            "question": qa.get("question", ""),
            "answer_summary": qa.get("answer", "")[:200],
            "score": qa.get("score", 0),
            "type": qa.get("question_type", "technical"),
        }
        for qa in questions_and_answers
    ])

    user_prompt = f"""Write a comprehensive interview report for {student_name} interviewing for {job_role}.

Questions and Answers Summary:
{qa_summary}

Return this EXACT JSON (no other text):
{{
  "overall_score": <integer 0-100, average of all answer scores scaled to 100>,
  "grade": "<A/B/C/D/F>",
  "performance_by_type": {{
    "technical": <integer 0-100>,
    "behavioral": <integer 0-100>,
    "hr": <integer 0-100>
  }},
  "top_strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "areas_to_improve": ["<area 1>", "<area 2>", "<area 3>"],
  "recommended_resources": [
    {{"topic": "<topic>", "resource": "<specific book/course/platform>"}},
    {{"topic": "<topic>", "resource": "<specific resource>"}}
  ],
  "hiring_recommendation": "<Strong Hire/Hire/Maybe/No Hire>",
  "detailed_feedback": "<2-3 paragraph detailed honest assessment>",
  "next_steps": ["<step 1>", "<step 2>", "<step 3>"]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1200,
            temperature=0.3,
        )
        raw = response.choices[0].message.content
        result = json.loads(_strip_markdown(raw))
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"AI response parsing failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════
# SERVICE 4 — Skill Gap Analyzer
# ══════════════════════════════════════════════════════════════

def analyze_skill_gap(student_skills, target_role, current_education=None):
    """
    Analyzes skill gap between student's current skills and target role requirements.

    student_skills: list of str
    target_role: str — e.g. "Full Stack Developer at FAANG"
    current_education: str — optional degree info

    Returns dict with readiness_score, readiness_level, skills_to_learn,
    learning_roadmap, total_weeks_to_ready, job_market_insight, similar_roles_easier
    """
    client = get_openai_client()

    system_prompt = (
        "You are a career coach and tech industry expert who helps students close skill gaps. "
        "You give specific, actionable learning roadmaps. "
        "You ALWAYS respond with valid JSON only."
    )

    user_prompt = f"""Analyze the skill gap for this student targeting: {target_role}

Current Skills: {', '.join(student_skills) if student_skills else 'None listed'}
Education: {current_education or 'Not specified'}

Create a detailed skill gap analysis and learning roadmap.

Return this EXACT JSON (no other text):
{{
  "target_role": "{target_role}",
  "readiness_score": <integer 0-100>,
  "readiness_level": "<Not Ready/Getting There/Almost Ready/Job Ready>",
  "current_skills_relevant": ["<relevant skill from student>"],
  "skills_to_learn": [
    {{
      "skill": "<skill name>",
      "priority": "<Critical/High/Medium/Nice to Have>",
      "why_needed": "<1 sentence why this skill matters for the role>",
      "estimated_weeks": <integer 1-12>,
      "free_resources": ["<YouTube channel or free course>", "<documentation link>"],
      "paid_resources": ["<Udemy course>", "<book name>"]
    }}
  ],
  "learning_roadmap": [
    {{
      "week": 1,
      "focus": "<focus area>",
      "skills": ["<skill>"],
      "milestone": "<what student can do after this week>"
    }}
  ],
  "total_weeks_to_ready": <integer>,
  "job_market_insight": "<2-3 sentences about current demand for this role>",
  "similar_roles_easier": ["<easier role 1>", "<easier role 2>"]
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2000,
            temperature=0.4,
        )
        raw = response.choices[0].message.content
        result = json.loads(_strip_markdown(raw))
        return {"success": True, "data": result}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"AI response parsing failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

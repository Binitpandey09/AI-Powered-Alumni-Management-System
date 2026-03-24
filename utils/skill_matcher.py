import re


def normalize_skill(skill):
    """Normalize skill name for comparison — lowercase, strip whitespace, remove special chars."""
    return re.sub(r'[^a-z0-9+#.]', '', skill.lower().strip())


def calculate_skill_match(student_skills, required_skills, preferred_skills=None):
    """
    Calculate how well a student's skills match a referral's requirements.

    Returns dict:
        score           : int (0-100)
        matched_skills  : list of matched required skills
        missing_skills  : list of required skills student does NOT have
        preferred_matched: list of preferred skills also matched
        can_apply       : bool (score >= 40)
        reason          : str (human readable explanation)
    """
    if not required_skills:
        return {
            'score': 100,
            'matched_skills': [],
            'missing_skills': [],
            'preferred_matched': [],
            'can_apply': True,
            'reason': 'No specific skills required for this referral.',
        }

    if not student_skills:
        return {
            'score': 0,
            'matched_skills': [],
            'missing_skills': list(required_skills),
            'preferred_matched': [],
            'can_apply': False,
            'reason': 'Your profile has no skills listed. Add your skills to apply.',
        }

    norm_student = [normalize_skill(s) for s in student_skills]
    norm_required = [normalize_skill(s) for s in required_skills]

    matched = []
    missing = []

    for i, norm_req in enumerate(norm_required):
        original_req = required_skills[i]
        if norm_req in norm_student:
            matched.append(original_req)
        elif any(
            (norm_req in ns or ns in norm_req)
            for ns in norm_student
            if len(ns) > 2
        ):
            matched.append(original_req)
        else:
            missing.append(original_req)

    # Base score from required skills
    # If preferred_skills provided: required = 80%, preferred = 20%
    # If no preferred_skills: required = 100%
    required_weight = 80 if preferred_skills else 100
    required_score = (len(matched) / len(required_skills)) * required_weight

    # Preferred skills bonus (20% weight, only when preferred_skills provided)
    preferred_matched = []
    preferred_bonus = 0.0
    if preferred_skills:
        norm_preferred = [normalize_skill(s) for s in preferred_skills]
        for i, norm_pref in enumerate(norm_preferred):
            if norm_pref in norm_student or any(
                (norm_pref in ns or ns in norm_pref)
                for ns in norm_student
                if len(ns) > 2
            ):
                preferred_matched.append(preferred_skills[i])
        preferred_bonus = (len(preferred_matched) / len(preferred_skills)) * 20

    total_score = min(100, int(required_score + preferred_bonus))
    can_apply = total_score >= 40

    if total_score == 100:
        reason = 'Perfect match! You have all the required skills.'
    elif total_score >= 80:
        reason = f'Strong match. You have {len(matched)}/{len(required_skills)} required skills.'
    elif total_score >= 60:
        reason = (
            f'Good match. You have {len(matched)}/{len(required_skills)} required skills. '
            f'Consider adding: {", ".join(missing[:2])}.'
        )
    elif total_score >= 40:
        reason = (
            f'Partial match. You have {len(matched)}/{len(required_skills)} required skills. '
            f'Missing: {", ".join(missing)}.'
        )
    else:
        reason = (
            f'Insufficient match. You only have {len(matched)}/{len(required_skills)} required skills. '
            f'Missing: {", ".join(missing)}.'
        )

    return {
        'score': total_score,
        'matched_skills': matched,
        'missing_skills': missing,
        'preferred_matched': preferred_matched,
        'can_apply': can_apply,
        'reason': reason,
    }

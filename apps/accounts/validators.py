import secrets
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError


PERSONAL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'yahoo.co.in', 'rediffmail.com', 'live.com', 'msn.com',
    'aol.com', 'icloud.com', 'protonmail.com', 'mail.com',
    'ymail.com', 'zoho.com',
}

EDUCATIONAL_SUFFIXES = ('.ac.in', '.edu', '.edu.in')
EDUCATIONAL_KEYWORDS = ('university', 'college', 'institute', 'iit', 'nit', 'iiit', 'iim')


def _get_domain(email):
    """Extract domain from email string."""
    if not email or '@' not in email:
        raise ValidationError("Enter a valid email address.")
    return email.strip().lower().split('@')[1]


def validate_student_email(email):
    domain = _get_domain(email)
    if domain in PERSONAL_DOMAINS:
        raise ValidationError(
            "Students must register with their official college email address."
        )
    return email


def validate_alumni_company_email(email):
    domain = _get_domain(email)
    if domain in PERSONAL_DOMAINS:
        raise ValidationError(
            "Alumni must register with their current company email address."
        )
    if any(domain.endswith(suffix) for suffix in EDUCATIONAL_SUFFIXES):
        raise ValidationError(
            "Alumni must register with their current company email address."
        )
    if any(keyword in domain for keyword in EDUCATIONAL_KEYWORDS):
        raise ValidationError(
            "Alumni must register with their current company email address."
        )
    return email


def validate_faculty_email(email):
    domain = _get_domain(email)
    is_educational = (
        any(domain.endswith(suffix) for suffix in EDUCATIONAL_SUFFIXES)
        or any(keyword in domain for keyword in EDUCATIONAL_KEYWORDS)
    )
    if not is_educational:
        raise ValidationError(
            "Faculty must register with their official institution email address."
        )
    return email


def generate_otp():
    """Return a cryptographically random 6-digit OTP string."""
    return str(secrets.randbelow(1_000_000)).zfill(6)

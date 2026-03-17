from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re


# Phone number validator
phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
)


def validate_file_size(file, max_size_mb=5):
    """
    Validate file size
    
    Args:
        file: File object
        max_size_mb: Maximum file size in MB (default: 5)
    
    Raises:
        ValidationError: If file size exceeds limit
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        raise ValidationError(f'File size cannot exceed {max_size_mb}MB')


def validate_file_extension(file, allowed_extensions):
    """
    Validate file extension
    
    Args:
        file: File object
        allowed_extensions: List of allowed extensions (e.g., ['pdf', 'doc', 'docx'])
    
    Raises:
        ValidationError: If file extension is not allowed
    """
    ext = file.name.split('.')[-1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f'File extension .{ext} is not allowed. Allowed extensions: {", ".join(allowed_extensions)}'
        )


def validate_resume_file(file):
    """
    Validate resume file (size and extension)
    
    Args:
        file: Resume file object
    
    Raises:
        ValidationError: If validation fails
    """
    validate_file_size(file, max_size_mb=5)
    validate_file_extension(file, ['pdf', 'doc', 'docx'])


def validate_image_file(file):
    """
    Validate image file (size and extension)
    
    Args:
        file: Image file object
    
    Raises:
        ValidationError: If validation fails
    """
    validate_file_size(file, max_size_mb=5)
    validate_file_extension(file, ['jpg', 'jpeg', 'png', 'gif'])


def validate_graduation_year(year):
    """
    Validate graduation year
    
    Args:
        year: Graduation year (integer)
    
    Raises:
        ValidationError: If year is invalid
    """
    from datetime import datetime
    current_year = datetime.now().year
    
    if year < 1950 or year > current_year + 10:
        raise ValidationError(
            f'Graduation year must be between 1950 and {current_year + 10}'
        )


def validate_linkedin_url(url):
    """
    Validate LinkedIn URL format
    
    Args:
        url: LinkedIn URL string
    
    Raises:
        ValidationError: If URL format is invalid
    """
    linkedin_pattern = r'^https?://(www\.)?linkedin\.com/in/[\w-]+/?$'
    if not re.match(linkedin_pattern, url):
        raise ValidationError('Invalid LinkedIn URL format')


def validate_github_url(url):
    """
    Validate GitHub URL format
    
    Args:
        url: GitHub URL string
    
    Raises:
        ValidationError: If URL format is invalid
    """
    github_pattern = r'^https?://(www\.)?github\.com/[\w-]+/?$'
    if not re.match(github_pattern, url):
        raise ValidationError('Invalid GitHub URL format')


def validate_positive_amount(value):
    """
    Validate that amount is positive
    
    Args:
        value: Amount value
    
    Raises:
        ValidationError: If amount is not positive
    """
    if value <= 0:
        raise ValidationError('Amount must be greater than zero')


def validate_rating(value):
    """
    Validate rating value (1-5)
    
    Args:
        value: Rating value
    
    Raises:
        ValidationError: If rating is not between 1 and 5
    """
    if value < 1 or value > 5:
        raise ValidationError('Rating must be between 1 and 5')

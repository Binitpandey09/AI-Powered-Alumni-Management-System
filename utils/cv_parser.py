"""
CV / Resume text extraction utilities.
Supports PDF (via PyPDF2) and DOCX (via python-docx).
"""
import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_obj) -> str:
    """Extract plain text from a PDF file-like object."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(file_obj)
        pages = [page.extract_text() or '' for page in reader.pages]
        return '\n'.join(pages).strip()
    except Exception as exc:
        logger.warning("PDF extraction failed: %s", exc)
        return ''


def extract_text_from_docx(file_obj) -> str:
    """Extract plain text from a DOCX file-like object."""
    try:
        from docx import Document
        doc = Document(file_obj)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return '\n'.join(paragraphs).strip()
    except Exception as exc:
        logger.warning("DOCX extraction failed: %s", exc)
        return ''


def extract_cv_text(file_obj, filename: str) -> str:
    """
    Dispatch to the correct extractor based on file extension.
    Returns extracted text or empty string on failure.
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext == 'pdf':
        return extract_text_from_pdf(file_obj)
    elif ext in ('doc', 'docx'):
        return extract_text_from_docx(file_obj)
    logger.warning("Unsupported CV format: %s", ext)
    return ''

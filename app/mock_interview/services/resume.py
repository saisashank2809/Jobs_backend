"""
mock_interview/services/resume.py
Resume text extraction utility.
Supports PDF (via pypdf, already in requirements.txt) and plain text.
No API keys required.
"""

import io

try:
    # pypdf is listed in jobs backend requirements
    from pypdf import PdfReader  # type: ignore
    _PDF_READER = "pypdf"
except ImportError:
    try:
        from PyPDF2 import PdfReader  # type: ignore
        _PDF_READER = "PyPDF2"
    except ImportError:
        PdfReader = None  # type: ignore
        _PDF_READER = None


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using the available PDF library."""
    if PdfReader is None:
        return ""
    text = ""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as exc:
        print(f"Error extracting text from PDF: {exc}")
        return ""
    return text.strip()


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    General file text extractor based on file extension.
    Supports .pdf and .txt (and falls back to UTF-8 decode for others).
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower.endswith(".txt"):
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1")
    else:
        try:
            return file_bytes.decode("utf-8")
        except Exception:
            return ""

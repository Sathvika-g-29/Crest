
import pytest
import pymupdf

from app.services.resume_parser import extract_text_from_pdf

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def create_pdf(path, text="Sample resume text"):
    """Create a small real PDF for testing."""
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), text)
        document.save(path)


def test_extracts_text_from_valid_pdf(tmp_path):
    pdf_path = tmp_path / "resume.pdf"
    create_pdf(pdf_path, "Python FastAPI developer")

    result = extract_text_from_pdf(str(pdf_path))

    assert "Python FastAPI developer" in result


def test_rejects_invalid_pdf(tmp_path):
    pdf_path = tmp_path / "invalid.pdf"
    pdf_path.write_text("This is not a PDF", encoding="utf-8")

    with pytest.raises(ValueError, match="valid PDF"):
        extract_text_from_pdf(str(pdf_path))


def test_rejects_pdf_with_no_readable_text(tmp_path):
    pdf_path = tmp_path / "empty.pdf"

    with pymupdf.open() as document:
        document.new_page()
        document.save(pdf_path)

    with pytest.raises(ValueError, match="No readable text"):
        extract_text_from_pdf(str(pdf_path))

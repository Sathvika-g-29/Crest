import fitz


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF resume.

    Args:
        file_path: Path to the uploaded PDF.

    Returns:
        Extracted text from all pages.
    """

    document = fitz.open(file_path)

    pages_text = []

    for page in document:
        text = page.get_text()
        pages_text.append(text)

    document.close()

    return "\n".join(pages_text).strip()
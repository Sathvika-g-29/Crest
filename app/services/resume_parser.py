
import pymupdf


def extract_text_from_pdf(file_path: str) -> str:
    """Extract readable text from a PDF file."""

    try:
        with pymupdf.open(file_path) as document:
            if document.is_encrypted:
                raise ValueError(
                    "Password-protected PDFs are not supported."
                )

            if document.page_count == 0:
                raise ValueError("The PDF contains no pages.")

            pages_text = [
                page.get_text()
                for page in document
            ]

            extracted_text = "\n".join(pages_text).strip()

            if not extracted_text:
                raise ValueError(
                    "No readable text was found in the PDF. "
                    "The resume may be scanned or image-based."
                )

            return extracted_text

    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            "The uploaded file could not be read as a valid PDF."
        ) from exc

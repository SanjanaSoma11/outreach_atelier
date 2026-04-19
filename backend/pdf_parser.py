import io
import pdfplumber


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes without writing to disk."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
    return "\n\n".join(text_parts)

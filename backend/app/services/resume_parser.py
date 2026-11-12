from pathlib import Path
import io
import pymupdf
from docx import Document

def extract_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        with pymupdf.open(stream=content, filetype="pdf") as doc:
            text = "\n".join(page.get_text("text") for page in doc)
    elif ext == ".docx":
        doc = Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs)
        for table in doc.tables:
            for row in table.rows:
                text += "\n" + " | ".join(cell.text for cell in row.cells)
    else:
        raise ValueError("Only PDF and DOCX files are supported")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not text:
        raise ValueError("No readable text found. Scanned PDFs need OCR; OCR is not enabled in this version.")
    return text

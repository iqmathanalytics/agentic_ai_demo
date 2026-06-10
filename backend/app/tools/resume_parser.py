from __future__ import annotations

import base64
import io
from typing import Any


def parse_resume(file_name: str, file_data: str) -> dict[str, Any]:
    raw = base64.b64decode(file_data.split(",")[-1])
    lower_name = file_name.lower()
    try:
        if lower_name.endswith(".pdf"):
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(raw))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return {"text": text.strip(), "pages": len(reader.pages)}
        if lower_name.endswith(".docx"):
            from docx import Document

            document = Document(io.BytesIO(raw))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            return {"text": text.strip(), "pages": None}
    except Exception as exc:
        return {"text": "", "error": str(exc)}
    return {"text": "", "error": "Unsupported file type."}


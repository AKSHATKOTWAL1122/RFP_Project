from __future__ import annotations

import pymupdf as fitz


class DocumentExtractionError(Exception):
    def __init__(self, supplier_name: str, message: str):
        self.supplier_name = supplier_name
        self.message = message
        super().__init__(f"[{supplier_name}] {message}")


def extract_text(pdf_path: str, supplier_name: str) -> str:
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise DocumentExtractionError(supplier_name, f"could not open PDF: {exc}") from exc

    try:
        pages = [page.get_text("text") for page in doc]
    except Exception as exc:
        raise DocumentExtractionError(supplier_name, f"could not read PDF: {exc}") from exc
    finally:
        doc.close()

    text = "\n".join(pages).strip()
    if not text:
        raise DocumentExtractionError(supplier_name, "no extractable text (empty or scanned PDF)")
    return text

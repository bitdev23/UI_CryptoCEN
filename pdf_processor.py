"""PDF processing: extract text from PDFs and chunk for RAG."""
from typing import List, Tuple
import fitz  # pymupdf
import os
from pathlib import Path
import logging
try:
    from docx import Document
    _HAS_DOCX = True
except Exception:
    _HAS_DOCX = False

logger = logging.getLogger("valtrilabs.pdf_processor")


def extract_text_from_pdf(path: str) -> str:
    """Extract text from one PDF file; returns empty string on error."""
    try:
        doc = fitz.open(path)
    except Exception as e:
        logger.exception("Failed to open PDF: %s", path)
        return ""
    text_chunks = []
    try:
        for page in doc:
            text = page.get_text()
            if text:
                text_chunks.append(text)
    except Exception:
        logger.exception("Error while reading PDF pages: %s", path)
    finally:
        doc.close()
    return "\n".join(text_chunks)


def extract_text_from_docx(path: str) -> str:
    """Extract text from one DOCX file; returns empty string on error."""
    if not _HAS_DOCX:
        logger.warning("python-docx not installed; cannot parse DOCX: %s", path)
        return ""
    try:
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        logger.exception("Failed to extract DOCX: %s", path)
        return ""


def load_document(path: str) -> Tuple[str, str]:
    """Load one PDF/DOCX file and return (source, text)."""
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        text = extract_text_from_pdf(path)
    elif ext == ".docx":
        text = extract_text_from_docx(path)
    else:
        logger.warning("Unsupported document type: %s", path)
        return (path, "")
    return (path, text)


def load_pdfs(folder: str = "data/pdfs") -> List[Tuple[str, str]]:
    """Load all PDFs in folder and return list of (filename, text)."""
    results = []
    p = Path(folder)
    if not p.exists():
        logger.warning("PDF folder does not exist: %s", folder)
        return results
    # process PDFs
    for f in p.glob("**/*.pdf"):
        logger.info("Processing PDF: %s", f)
        text = extract_text_from_pdf(str(f))
        if not text:
            logger.warning("No text extracted from %s", f)
            continue
        results.append((str(f), text))
    # process DOCX files if python-docx available
    if _HAS_DOCX:
        for f in p.glob("**/*.docx"):
            logger.info("Processing DOCX: %s", f)
            try:
                doc = Document(str(f))
                paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
                text = "\n".join(paragraphs)
                if text:
                    results.append((str(f), text))
            except Exception:
                logger.exception("Failed to extract DOCX: %s", f)
    return results


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Chunk text with overlap for RAG retrieval."""
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be larger than overlap")
    if not text:
        return []

    out = []
    step = chunk_size - overlap
    start = 0
    L = len(text)
    while start < L:
        end = min(start + chunk_size, L)
        out.append(text[start:end])
        if end >= L:
            break
        start += step
    return out


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.DEBUG)
    pdfs = load_pdfs()
    print(f"Loaded {len(pdfs)} PDFs")
    if pdfs:
        chunks = chunk_text(pdfs[0][1])
        print(f"Example chunks: {len(chunks)}")

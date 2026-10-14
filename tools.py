"""The four document tools. This is the ONLY file that imports a PDF library.

Each tool parses lazily on every call. Nothing is held between calls except the
open file handle: no text cache, no index.
"""

import re
try:
    import pymupdf as fitz
except ImportError:
    import fitz


class ToolError(Exception):
    """A tool received bad input or the PDF could not be read."""


def list_documents(doc_path):
    """Return the uploaded file's doc_id, title and page count."""
    doc = fitz.open(doc_path)
    try:
        return {
            "doc_id": doc_path,
            "title": doc.metadata.get("title") or doc_path.split("/")[-1],
            "page_count": doc.page_count,
        }
    finally:
        doc.close()


def list_headings(doc_path):
    """Return [{title, page}] using the PDF outline if present, otherwise a
    simple regex for numbered headings and short ALL-CAPS lines."""
    doc = fitz.open(doc_path)
    try:
        headings = []
        try:
            for item in doc.get_toc():
                level, title, page = item
                headings.append({"title": title.strip(), "page": page})
            if headings:
                return headings
        except Exception:
            pass

        # Fallback: numbered headings and short ALL-CAPS lines.
        for i in range(doc.page_count):
            page = doc[i]
            text = page.get_text("text")
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                if re.match(r"^\d+(\.\d+)*\s+\S", line) and len(line) < 120:
                    headings.append({"title": line, "page": i + 1})
                elif line.isupper() and len(line) < 80:
                    headings.append({"title": line, "page": i + 1})
        return headings
    finally:
        doc.close()


def get_page(doc_path, page_number):
    """Return the text of one page. Physical, 1-indexed page numbers."""
    doc = fitz.open(doc_path)
    try:
        if not isinstance(page_number, int) or page_number < 1:
            raise ToolError("page_number must be a positive integer")
        if page_number > doc.page_count:
            raise ToolError(
                f"page_number {page_number} out of range "
                f"(document has {doc.page_count} pages)"
            )
        return doc[page_number - 1].get_text("text")
    finally:
        doc.close()


def search_keyword(doc_path, keyword):
    """Case-insensitive, whitespace and hyphen normalized search.
    Returns a sorted list of page numbers only."""
    if not isinstance(keyword, str) or not keyword.strip():
        raise ToolError("keyword must be a non-empty string")

    doc = fitz.open(doc_path)
    try:
        # Normalize: collapse whitespace, then remove hyphens, then lowercase.
        def norm(s):
            return re.sub(r"\s+", "", s.replace("-", "")).lower()

        needle = norm(keyword)
        hits = []
        for i in range(doc.page_count):
            if needle in norm(doc[i].get_text("text")):
                hits.append(i + 1)
        return sorted(hits)
    finally:
        doc.close()


class DocHandle:
    """Binds a document path to the four tools.

    The agent only ever holds a BudgetedTools wrapper, never a raw tool.
    """

    def __init__(self, doc_path):
        self.doc_path = doc_path
        self.list_documents = lambda **kw: list_documents(doc_path)
        self.list_headings = lambda **kw: list_headings(doc_path)
        self.get_page = lambda page_number, **kw: get_page(doc_path, page_number)
        self.search_keyword = lambda keyword, **kw: search_keyword(doc_path, keyword)
"""File system tools for the LLM-Powered File System Assistant.

Four self-contained tools that read, list, write, and search resume files
(.pdf, .txt, .docx). Each tool has a plain, structured (dict/list) input and
output so it can be called directly from Python or exposed to an LLM as a
"function" for tool calling (see llm_file_assistant.py).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from docx import Document
from pypdf import PdfReader

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".docx"}

# Characters of surrounding text to include on each side of a search match.
DEFAULT_CONTEXT_CHARS = 60


def _normalize_extension(extension: str) -> str:
    """Normalize an extension to lowercase with a leading dot, e.g. 'PDF' -> '.pdf'."""
    extension = extension.strip().lower()
    if extension and not extension.startswith("."):
        extension = f".{extension}"
    return extension


def _human_readable_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _read_txt(path: Path) -> tuple[str, dict]:
    content = path.read_text(encoding="utf-8", errors="replace")
    metadata = {"line_count": content.count("\n") + 1 if content else 0}
    return content, metadata


def _read_pdf(path: Path) -> tuple[str, dict]:
    reader = PdfReader(str(path))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    content = "\n".join(pages_text)
    metadata = {"page_count": len(reader.pages)}
    return content, metadata


def _read_docx(path: Path) -> tuple[str, dict]:
    document = Document(str(path))
    paragraphs = [p.text for p in document.paragraphs]
    content = "\n".join(paragraphs)
    metadata = {"paragraph_count": len(paragraphs)}
    return content, metadata


_READERS: dict[str, Callable[[Path], tuple[str, dict]]] = {
    ".txt": _read_txt,
    ".pdf": _read_pdf,
    ".docx": _read_docx,
}


def read_file(filepath: str) -> dict:
    """Read a resume file (.pdf, .txt, or .docx) and extract its text content.

    Args:
        filepath: Path to the file to read.

    Returns:
        dict with keys:
            success (bool), filepath (str), filename (str), extension (str),
            content (str | None), metadata (dict), error (str | None)
    """
    path = Path(filepath)
    extension = _normalize_extension(path.suffix)

    response = {
        "success": False,
        "filepath": str(path),
        "filename": path.name,
        "extension": extension,
        "content": None,
        "metadata": {},
        "error": None,
    }

    if not path.exists():
        response["error"] = f"File not found: {filepath}"
        logger.warning(response["error"])
        return response

    if not path.is_file():
        response["error"] = f"Path is not a file: {filepath}"
        logger.warning(response["error"])
        return response

    reader = _READERS.get(extension)
    if reader is None:
        response["error"] = (
            f"Unsupported file extension '{extension}'. "
            f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
        logger.warning(response["error"])
        return response

    try:
        content, type_metadata = reader(path)
    except Exception as exc:
        response["error"] = f"Failed to read '{filepath}': {exc}"
        logger.error(response["error"])
        return response

    stat = path.stat()
    response["metadata"] = {
        "size_bytes": stat.st_size,
        "size_readable": _human_readable_size(stat.st_size),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "char_count": len(content),
        "word_count": len(content.split()),
        **type_metadata,
    }
    response["success"] = True
    response["content"] = content
    return response


def list_files(directory: str, extension: Optional[str] = None) -> list:
    """List files in a directory, optionally filtered by extension.

    Args:
        directory: Path to the directory to list.
        extension: Optional extension filter, e.g. '.pdf' or 'pdf'.

    Returns:
        List of dicts, one per file, each with:
            name, path, extension, size_bytes, size_readable, modified.
        Returns an empty list if the directory does not exist or is empty.
    """
    dir_path = Path(directory)

    if not dir_path.exists() or not dir_path.is_dir():
        logger.warning("Directory not found or not a directory: %s", directory)
        return []

    normalized_extension = _normalize_extension(extension) if extension else None

    entries = []
    try:
        for entry in sorted(dir_path.iterdir()):
            if not entry.is_file():
                continue
            if normalized_extension and entry.suffix.lower() != normalized_extension:
                continue
            stat = entry.stat()
            entries.append(
                {
                    "name": entry.name,
                    "path": str(entry),
                    "extension": entry.suffix.lower(),
                    "size_bytes": stat.st_size,
                    "size_readable": _human_readable_size(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
    except OSError as exc:
        logger.error("Error listing directory '%s': %s", directory, exc)
        return []

    return entries


def write_file(filepath: str, content: str) -> dict:
    """Write text content to a file, creating parent directories if needed.

    Args:
        filepath: Destination path for the file.
        content: Text content to write.

    Returns:
        dict with keys: success (bool), filepath (str), bytes_written (int), error (str | None)
    """
    path = Path(filepath)
    response = {"success": False, "filepath": str(path), "bytes_written": 0, "error": None}

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        response["success"] = True
        response["bytes_written"] = len(content.encode("utf-8"))
    except OSError as exc:
        response["error"] = f"Failed to write '{filepath}': {exc}"
        logger.error(response["error"])

    return response


def search_in_file(filepath: str, keyword: str) -> dict:
    """Search for a keyword in a file's content (case-insensitive).

    Args:
        filepath: Path to the file to search (.pdf, .txt, or .docx).
        keyword: Keyword or phrase to search for.

    Returns:
        dict with keys:
            success (bool), filepath (str), keyword (str), match_count (int),
            matches (list of {line_number, context, matched_text}), error (str | None)
    """
    response = {
        "success": False,
        "filepath": filepath,
        "keyword": keyword,
        "match_count": 0,
        "matches": [],
        "error": None,
    }

    if not keyword or not keyword.strip():
        response["error"] = "Keyword must not be empty."
        return response

    read_result = read_file(filepath)
    if not read_result["success"]:
        response["error"] = read_result["error"]
        return response

    content = read_result["content"]
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)

    matches = []
    for match in pattern.finditer(content):
        start, end = match.start(), match.end()
        context_start = max(0, start - DEFAULT_CONTEXT_CHARS)
        context_end = min(len(content), end + DEFAULT_CONTEXT_CHARS)
        context = " ".join(content[context_start:context_end].split())
        line_number = content.count("\n", 0, start) + 1
        matches.append(
            {
                "line_number": line_number,
                "context": context,
                "matched_text": match.group(),
            }
        )

    response["success"] = True
    response["match_count"] = len(matches)
    response["matches"] = matches
    return response

"""Unit tests for fs_tools.py.

Runs against isolated temp directories (pytest's tmp_path fixture) so tests
don't depend on the generated sample resumes and can run in any order.

Usage:
    pytest -v
"""

from docx import Document
from fpdf import FPDF

from fs_tools import list_files, read_file, search_in_file, write_file

SAMPLE_TEXT = "John Doe\nSkills: Python, Django, PostgreSQL.\nPython is his strongest skill."


# ---------- helpers ----------

def _make_txt(tmp_path, name="resume.txt", text=SAMPLE_TEXT):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _make_docx(tmp_path, name="resume.docx", text=SAMPLE_TEXT):
    path = tmp_path / name
    document = Document()
    for line in text.split("\n"):
        document.add_paragraph(line)
    document.save(str(path))
    return path


def _make_pdf(tmp_path, name="resume.pdf", text=SAMPLE_TEXT):
    path = tmp_path / name
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in text.split("\n"):
        pdf.set_x(pdf.l_margin)
        if line.strip():
            pdf.multi_cell(0, 6, line)
        else:
            pdf.ln(6)
    pdf.output(str(path))
    return path


# ---------- read_file ----------

def test_read_file_txt(tmp_path):
    path = _make_txt(tmp_path)
    result = read_file(str(path))
    assert result["success"] is True
    assert "Python" in result["content"]
    assert result["extension"] == ".txt"
    assert result["metadata"]["line_count"] == 3
    assert result["error"] is None


def test_read_file_docx(tmp_path):
    path = _make_docx(tmp_path)
    result = read_file(str(path))
    assert result["success"] is True
    assert "Django" in result["content"]
    assert result["metadata"]["paragraph_count"] == 3


def test_read_file_pdf(tmp_path):
    path = _make_pdf(tmp_path)
    result = read_file(str(path))
    assert result["success"] is True
    assert "Python" in result["content"]
    assert result["metadata"]["page_count"] == 1


def test_read_file_not_found(tmp_path):
    result = read_file(str(tmp_path / "missing.txt"))
    assert result["success"] is False
    assert "not found" in result["error"].lower()
    assert result["content"] is None


def test_read_file_unsupported_extension(tmp_path):
    path = tmp_path / "resume.xyz"
    path.write_text("hello")
    result = read_file(str(path))
    assert result["success"] is False
    assert "unsupported" in result["error"].lower()


def test_read_file_directory_path(tmp_path):
    result = read_file(str(tmp_path))
    assert result["success"] is False
    assert "not a file" in result["error"].lower()


# ---------- list_files ----------

def test_list_files_all(tmp_path):
    _make_txt(tmp_path, "a.txt")
    _make_docx(tmp_path, "b.docx")
    result = list_files(str(tmp_path))
    names = {f["name"] for f in result}
    assert names == {"a.txt", "b.docx"}
    assert all("size_bytes" in f and "modified" in f for f in result)


def test_list_files_filtered_by_extension(tmp_path):
    _make_txt(tmp_path, "a.txt")
    _make_docx(tmp_path, "b.docx")
    result = list_files(str(tmp_path), extension=".txt")
    assert len(result) == 1
    assert result[0]["name"] == "a.txt"


def test_list_files_extension_without_dot(tmp_path):
    _make_txt(tmp_path, "a.txt")
    result = list_files(str(tmp_path), extension="txt")
    assert len(result) == 1


def test_list_files_nonexistent_directory():
    result = list_files("/path/does/not/exist")
    assert result == []


def test_list_files_empty_directory(tmp_path):
    result = list_files(str(tmp_path))
    assert result == []


# ---------- write_file ----------

def test_write_file_creates_file(tmp_path):
    path = tmp_path / "notes.txt"
    result = write_file(str(path), "hello world")
    assert result["success"] is True
    assert result["bytes_written"] == len(b"hello world")
    assert path.read_text() == "hello world"


def test_write_file_creates_nested_directories(tmp_path):
    path = tmp_path / "a" / "b" / "c" / "summary.txt"
    result = write_file(str(path), "nested content")
    assert result["success"] is True
    assert path.exists()
    assert path.read_text() == "nested content"


def test_write_file_overwrites_existing_file(tmp_path):
    path = tmp_path / "notes.txt"
    write_file(str(path), "first")
    result = write_file(str(path), "second")
    assert result["success"] is True
    assert path.read_text() == "second"


# ---------- search_in_file ----------

def test_search_in_file_finds_case_insensitive_matches(tmp_path):
    path = _make_txt(tmp_path)
    result = search_in_file(str(path), "python")
    assert result["success"] is True
    assert result["match_count"] == 2
    assert all("python" in m["context"].lower() for m in result["matches"])


def test_search_in_file_no_matches(tmp_path):
    path = _make_txt(tmp_path)
    result = search_in_file(str(path), "Kubernetes")
    assert result["success"] is True
    assert result["match_count"] == 0
    assert result["matches"] == []


def test_search_in_file_empty_keyword(tmp_path):
    path = _make_txt(tmp_path)
    result = search_in_file(str(path), "")
    assert result["success"] is False
    assert "keyword" in result["error"].lower()


def test_search_in_file_missing_file(tmp_path):
    result = search_in_file(str(tmp_path / "missing.txt"), "python")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_search_in_file_includes_line_number(tmp_path):
    path = _make_txt(tmp_path)
    result = search_in_file(str(path), "Django")
    assert result["matches"][0]["line_number"] == 2

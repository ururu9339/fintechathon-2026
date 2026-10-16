import io
import zipfile
from xml.etree import ElementTree

from pypdf import PdfReader

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_ARCHIVE_SIZE_BYTES = 50 * 1024 * 1024


def validate_upload_file(file_bytes: bytes, filename: str) -> str | None:
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return "File size exceeds the 10 MB limit."
    ext = filename.lower().rsplit(".", 1)[-1]
    valid = {
        "pdf": file_bytes.startswith(b"%PDF-"),
        "png": file_bytes.startswith(b"\x89PNG"),
        "jpg": file_bytes.startswith(b"\xff\xd8"),
        "jpeg": file_bytes.startswith(b"\xff\xd8"),
        "docx": file_bytes.startswith(b"PK\x03\x04"),
    }
    if ext not in valid:
        return "Unsupported file type."
    if not valid[ext]:
        return f"Invalid {ext.upper()} header signature."
    if ext == "docx":
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
                if sum(info.file_size for info in archive.infolist()) > MAX_ARCHIVE_SIZE_BYTES:
                    return "DOCX archive expands beyond the safety limit."
        except zipfile.BadZipFile:
            return "Invalid DOCX zip archive."
    return None


def extract_text_from_docx(file_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    words = [
        node.text.strip()
        for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        if node.text and node.text.strip()
    ]
    return "\n".join(words)


def parse_pdf(file_bytes: bytes) -> tuple[str, str]:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        return "failed", str(exc)
    return ("scanned_pdf_detected", "") if len(text.strip()) < 50 else ("ok", text)

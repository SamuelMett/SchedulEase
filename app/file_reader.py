# app/file_reader.py

import docx
from pypdf import PdfReader

def extract_text_from_file(file_path: str) -> str:
    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        return "".join(page.extract_text() or "" for page in reader.pages)
    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)
    else:
        raise ValueError("Unsupported file type. Please use PDF or DOCX.")
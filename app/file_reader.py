import io
from fastapi import UploadFile, HTTPException
from pypdf import PdfReader

async def extract_text_from_file(file: UploadFile) -> str:
    """
    Extracts text content from an uploaded file (currently supports PDF).
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=415, # Unsupported Media Type
            detail="Unsupported file type. Please upload a PDF."
        )

    try:
        # Read the file content into memory
        file_bytes = await file.read()
        pdf_stream = io.BytesIO(file_bytes)

        # Use pypdf to read the text
        reader = PdfReader(pdf_stream)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        
        if not text:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the PDF. The file might be empty or image-based."
            )
        return text

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while reading the PDF file: {e}"
        )
import io
from docx import Document

def extract_docx(file_stream):
    # Wrap the raw bytes in a BytesIO "virtual file"
    stream = io.BytesIO(file_stream)
    
    # Pass the virtual file to Document
    doc = Document(stream)
    
    text = ""
    for para in doc.paragraphs:
        if para.text.strip():  # Only add if there is actual text
            text += para.text + "\n"
    
    return text
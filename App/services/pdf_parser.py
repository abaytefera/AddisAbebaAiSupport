
import pdfplumber
import io

def extract_pdf(file_stream):
    text = ""
    # We open the stream of bytes directly
    with pdfplumber.open(io.BytesIO(file_stream)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text
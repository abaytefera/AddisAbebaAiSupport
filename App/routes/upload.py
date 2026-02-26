from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from App.database.connection import SessionLocal
from App.services.docx_parser import extract_docx
from App.services.pdf_parser import extract_pdf
from App.services.document_processor import process_document
from App.services.dependencies import require_company_admin 

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    category: str = "General",
    db: Session = Depends(get_db), # Injected DB
    admin: dict = Depends(require_company_admin)
):
    # 1. Validate Extension
    valid_types = [
        "application/pdf", 
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
        "text/plain"
    ]
    if file.content_type not in valid_types:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    # 2. Read and Parse
    content = await file.read()
    try:
        if file.content_type == "application/pdf":
            text = extract_pdf(content)
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_docx(content)
        else:
            text = content.decode("utf-8")

        # 3. Call the processor with the DB session and Admin info
        process_document(db, text, file.filename, category, admin)

        return {
            "message": "Upload successful",
            "document_name": file.filename,
            "company_id": admin.get("company_id")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

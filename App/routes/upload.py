from fastapi import APIRouter, UploadFile, File, HTTPException, Depends,Form
from sqlalchemy.orm import Session
from App.database.connection import SessionLocal
from App.services.docx_parser import extract_docx
from App.services.pdf_parser import extract_pdf
from App.services.document_processor import process_knowledge_entry
from App.services.dependencies import require_company_admin 
from App.schemas.upload import TextEntryRequest
from sqlalchemy import desc
from App.models.model import Document,DocumentChunk,CompanyStatus
import io

import cloudinary.uploader
import traceback


router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    title: str = Form(...),            
    category: str = Form(...),
    db: Session = Depends(get_db), 
    admin: dict = Depends(require_company_admin)
):
    # 1. Read the bytes IMMEDIATELY and ONCE
    # This is the ONLY place 'await' should happen for the file data
    file_bytes = await file.read() 
    
    try:
        # 2. Extract Text (Use synchronous functions)
        if file.content_type == "application/pdf":
            # Pass the bytes directly
            text = extract_pdf(file_bytes) 
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = extract_docx(file_bytes)
        else:
            # bytes.decode() is a synchronous operation
            text = file_bytes.decode("utf-8")

        # 3. Call the processor
        # IMPORTANT: Pass file_bytes to the processor as well 
        # so it doesn't try to 'await file.read()' again
        await process_knowledge_entry(
            db=db,
            entry_type="File",
            text=text,
            title=title,
            category=category,
            admin=admin,
            # CHANGE THIS: Use 'file=' because that is what the function expects
            file=file_bytes, 
            filename=file.filename,
            version=1
        )
        return {"message": "Upload successful"}

    except Exception as e:
        # This will print the exact line causing the crash in your terminal
        import traceback
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
@router.post("/text")
async def upload_text(
    payload: TextEntryRequest,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_company_admin)
):
    try:
        # 2. Map the incoming JSON to your processor
        # Note: We pass content as 'text' and set version to 1
        new_doc = await process_knowledge_entry(
            db=db,
            entry_type="Text",
            text=payload.content,
            version=1,
            title=payload.title,
            category=payload.category,
            admin=admin,
            file=None,  # No file for manual text
            filename=None
        )

        return {
            "message": "Text knowledge trained successfully",
            "document_id": str(new_doc.id),
            "title": new_doc.title
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text processing failed: {str(e)}")



from sqlalchemy.orm import joinedload
from sqlalchemy import desc

@router.get("/document")
async def get_uploaded_documents(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_company_admin)
):
    try:
        company_id = admin.get("company_id")
        
        # Use joinedload to bring in chunks in one go if needed
        # Or keep it simple if you prefer reconstruction in the loop
        documents = db.query(Document).filter(
            Document.company_id == company_id
        ).options(joinedload(Document.chunks)).order_by(desc(Document.created_at)).all()

        response_data = []
        for doc in documents:
            # Reconstruct content: if it's Text, join the chunk_text from the relationship
            full_content = None
            if hasattr(doc.type, 'value') and doc.type.value == "Text":
                # doc.chunks is available because of the relationship in your model
                full_content = " ".join([chunk.chunk_text for chunk in doc.chunks])

            response_data.append({
                "id": str(doc.id),
                "title": doc.title,
                "document_name": doc.document_name,
                "category": doc.category,
                "status": doc.Status.value if hasattr(doc.Status, 'value') else doc.Status,
                "type": doc.type.value if hasattr(doc.type, 'value') else doc.type, 
                "content": full_content,
                "version": doc.document_version,
                "url": doc.file_metadata.get("url") if doc.file_metadata else None,
                "created_at": doc.created_at.isoformat()
            })

        return response_data

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch documents")
@router.delete("/document/{document_id}")
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_company_admin)
):
    # 1. Fetch document and verify ownership
    doc = db.query(Document).filter(
        Document.id == document_id, 
        Document.company_id == admin["company_id"]
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Store Cloudinary public_id before deleting from DB
    # Assuming your metadata stores the public_id from earlier
    cloudinary_public_id = doc.file_metadata.get("public_id") if doc.file_metadata else None

    try:
        # 2. Delete Chunks first (if not handled by 'cascade delete' in your model)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()

        # 3. Delete the Document
        db.delete(doc)

        # 4. Commit DB changes first
        db.commit()

        # 5. Only if DB commit succeeds, cleanup Cloudinary
        if cloudinary_public_id:
            try:
                cloudinary.uploader.destroy(cloudinary_public_id)
            except Exception as cloud_err:
                # We don't raise here because the DB is already clean, 
                # but we log it for manual cleanup later.
                print(f"⚠️ Cloudinary Cleanup Warning: {str(cloud_err)}")

        return {"message": "Document and associated chunks deleted successfully"}

    except Exception as e:
        db.rollback()
        print(f"❌ Delete Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Failed to delete document. Database rolled back.")
@router.patch("/document/{document_id}/status")
async def toggle_status(
    document_id: str,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_company_admin)
):
    try:
        doc = db.query(Document).filter(
            Document.id == document_id, 
            Document.company_id == admin["company_id"]
        ).first()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Extract the current value safely
        # If it's CompanyStatus.Active, we want just "Active"
        raw_status = doc.Status.value if hasattr(doc.Status, 'value') else str(doc.Status)
        
        # Toggle logic
        new_status = "Inactive" if "Active" in raw_status else "Active"
        
        doc.Status = new_status
        
        db.commit()
        db.refresh(doc)
        
        return {
            "message": f"Document is now {new_status}",
            "status": new_status
        }

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update status")
@router.post("/knowledge/update-text")
async def update_manual_entry(
    payload: dict, # previous_id, title, category, content
    db: Session = Depends(get_db),
    admin: dict = Depends(require_company_admin)
):
    try:
        # 1. Locate the old version
        old_doc = db.query(Document).filter(
            Document.id == payload.get("previous_id"),
            Document.company_id == admin["company_id"]
        ).first()

        if not old_doc:
            raise HTTPException(status_code=404, detail="Original entry not found")

        # 2. Start Versioning Logic
        # Calculate new version (e.g., "1" becomes 2)
        try:
            current_v = int(old_doc.document_version)
        except (ValueError, TypeError):
            current_v = 1
        
        new_v = current_v + 1

        # 3. Inactivate the old document
        # This stays in the session and only commits if the new entry succeeds
        old_doc.Status = CompanyStatus.Inactive

        # 4. Create the New Document Version
        # This re-runs the chunking and embedding process for the new content
        new_doc = await process_knowledge_entry(
            db=db,
            entry_type="Text",
            text=payload.get("content"),
            version=new_v,
            title=payload.get("title"),
            category=payload.get("category"),
            admin=admin,
            file=None,
            filename=None
        )

        # 5. Final Commit
        # This confirms both the inactivation of the old and creation of the new
        db.commit()

        return {
            "message": f"Updated to Version {new_v}",
            "new_id": str(new_doc.id)
        }

    except Exception as e:
        db.rollback()
        print(f"Update Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update manual entry")
@router.post("/knowledge/update-file")
async def update_file_version(
    file: UploadFile = File(...),
    previous_id: str = Form(...),
    title: str = Form(...),
    category: str = Form(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(require_company_admin)
):
    # 1. Fetch the document we are replacing
    old_doc = db.query(Document).filter(Document.id == previous_id, 
                                        Document.company_id == admin["company_id"]).first()
    if not old_doc:
        raise HTTPException(status_code=404, detail="Original document not found")

    # 2. Extract Text & Prepare Metadata
    file_bytes = await file.read()
    if file.content_type == "application/pdf":
        text = extract_pdf(file_bytes)
    else:
        text = file_bytes.decode("utf-8")

    # 3. Transactional Logic
    try:
        # Step A: Inactivate the previous document
        old_doc.Status = CompanyStatus.Inactive 
        
        # Step B: Calculate new version string/int
        new_v = str(int(old_doc.document_version) + 1)

        # Step C: Use your existing processor to create the NEW record and chunks
        await process_knowledge_entry(
            db=db,
            entry_type="File",
            text=text,
            title=title,
            category=category,
            admin=admin,
            file=file_bytes,
            filename=file.filename,
            version=new_v
        )
        
        return {"message": f"Version {new_v} created, old version inactivated"}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
@router.patch("/document/{doc_id}/metadata")
async def update_metadata(
    doc_id: str,
    payload: dict, # Expects {"title": "...", "category": "..."}
    db: Session = Depends(get_db),
    admin: dict = Depends(require_company_admin)
):
    # 1. Verification
    doc = db.query(Document).filter(
        Document.id == doc_id, 
        Document.company_id == admin["company_id"]
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # 2. Direct Update (No version change)
    if "title" in payload:
        doc.title = payload["title"]
    if "category" in payload:
        doc.category = payload["category"]
    
    try:
        db.commit()
        return {"message": "Metadata updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database update failed")
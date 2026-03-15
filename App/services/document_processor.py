from sqlalchemy.orm import Session
from App.models.model import Document, DocumentChunk
from App.services.chunker import chunk_text
from App.services.embeddings import create_embedding
import os
import cloudinary

import cloudinary.uploader

cloudinary.config(
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key = os.getenv("CLOUDINARY_API_KEY"),
        api_secret = os.getenv("CLOUDINARY_API_SECRET"),
        secure = True # Ensures all URLs generated are HTTPS
    )



async def process_knowledge_entry(db: Session, entry_type: str, text: str, version: int, title: str, category: str, admin: dict, file=None, filename: str = None):
    cloudinary_public_id = None
    
    try:
        upload_url = None

        # 1. Only upload to Cloudinary if it's a FILE
        if entry_type.lower() == "file" and file:
            upload_result = cloudinary.uploader.upload(
                file, 
                resource_type="auto",
                folder="ai_knowledge_base",
                access_mode="public",
                 type="upload"

                                                         )
            upload_url = upload_result.get('secure_url')
            cloudinary_public_id = upload_result.get('public_id')
            doc_name = filename or title
        else:
            # For manual text entries
            doc_name = title

        # 2. Database Operations (Ensure column names match your Model)
        print(f"DEBUG: company_id={admin.get('company_id')}, creator_id={admin.get('sub')}")
        new_doc = Document(
    document_name=doc_name,
    title=title,
    file_metadata={"url": upload_url,"public_id": cloudinary_public_id} if upload_url else None,
    type=entry_type,
    category=category,
    company_id=admin.get("company_id"), # This is correct
    creator_id=admin.get("sub"),        # CHANGE THIS from "user_id" to "sub"
    document_version=str(version)
)
        
        db.add(new_doc)
        db.flush() 

       
        
        

        # 3. Chunking & Embeddings
        chunks = chunk_text(text)
        for chunk_content in chunks:
            embedding = create_embedding(chunk_content)
            db_chunk = DocumentChunk(
               
                document_id=new_doc.id,
                 company_id=admin.get("company_id"),
                chunk_text=chunk_content,
                embedding=embedding
            )
            db.add(db_chunk)

        # Final Commit
        db.commit()
        return new_doc

    except Exception as e:
        # --- THE ROLLBACK LOGIC ---
        db.rollback()
        
        # If we successfully uploaded a file but the DB failed afterward, 
        # remove it from Cloudinary now.
        if cloudinary_public_id:
            try:
                cloudinary.uploader.destroy(cloudinary_public_id)
                print(f"♻️ Rolled back Cloudinary file: {cloudinary_public_id}")
            except Exception as cloud_err:
                print(f"🚨 Failed to delete file from Cloudinary: {str(cloud_err)}")
        
        print(f"❌ Processing Error: {str(e)}")
        raise e
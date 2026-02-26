from sqlalchemy.orm import Session
from App.models.model import Document, DocumentChunk
from App.services.chunker import chunk_text
from App.services.embeddings import create_embedding

def process_document(db: Session, text: str, filename: str, category: str, admin: dict):
    try:
        # 1. Create the parent Document
        new_doc = Document(
            document_name=filename,
            category=category,
            company_id=admin.get("company_id"), # From JWT payload
            creator_id=admin.get("user_id"),    # From JWT payload
            document_version="v1"
        )
        db.add(new_doc)
        db.flush()  # Generates the ID for the chunks to use

        # 2. Process text into chunks
        chunks = chunk_text(text)
        if not chunks:
            return

        for chunk_content in chunks:
            embedding = create_embedding(chunk_content)
            
            # 3. Create Chunks linked to the parent Document ID
            db_chunk = DocumentChunk(
                document_id=new_doc.id,
                company_id=admin.get("company_id"),
                chunk_text=chunk_content,
                embedding=embedding
            )
            db.add(db_chunk)

        db.commit()
        print(f"✅ Successfully saved {filename} with {len(chunks)} chunks.")
        
    except Exception as e:
        db.rollback()
        raise e

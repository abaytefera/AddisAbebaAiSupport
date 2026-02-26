from sqlalchemy import select, and_
from App.database.connection import SessionLocal
from App.models.model import DocumentChunk
from App.services.embeddings import create_embedding

def search_chunks(query: str, k: int = 5, company_id: str = ""):
 
    with SessionLocal() as db:
        try:
            query_embedding = create_embedding(query)

        
            stmt = (
                select(DocumentChunk)
                .where(DocumentChunk.company_id == company_id) # Strict isolation
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(k)
            )

            results = db.execute(stmt).scalars().all()
            return results
        except Exception as e:
            print(f"Search error: {e}")
            raise # Let the service layer handle the error message
from sqlalchemy import select, and_
from App.database.connection import SessionLocal
from App.models.model import DocumentChunk, Document, CompanyStatus
from App.services.embeddings import create_embedding

def search_chunks(query: str, k: int = 5, company_id: str = ""):
    with SessionLocal() as db:
        try:
            # 1. Generate the vector for the search query
            query_embedding = create_embedding(query)

            # 2. Build the query with a join to filter by Document status
            stmt = (
                select(DocumentChunk)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(
                    and_(
                        DocumentChunk.company_id == company_id,
                        # Use the enum and the capitalized column name from your model
                        Document.Status == CompanyStatus.Active 
                    )
                )
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(k)
            )

            # 3. Execute and return results
            results = db.execute(stmt).scalars().all()
            return results
            
        except Exception as e:
            print(f"Search error: {e}")
            raise
from pydantic import BaseModel
from uuid import UUID
from typing import List



class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    text: str


class SearchResponse(BaseModel):
    results: List[SearchResult]

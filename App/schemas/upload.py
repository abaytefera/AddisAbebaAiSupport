from pydantic import BaseModel
class TextEntryRequest(BaseModel):
    title: str
    category: str
    content: str  # This is the 'text' to be chunked
   
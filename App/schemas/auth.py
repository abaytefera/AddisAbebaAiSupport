from pydantic import BaseModel, EmailStr,ConfigDict
from typing import Optional
from uuid import UUID
from enum import Enum
class CompanyCreate(BaseModel):
    name: str
    email:str

class CompanyStatus(str, Enum):
    Active = "Active"
    Inactive = "Inactive"

class CompanyResponse(BaseModel):
    id: UUID  
    name: str
    email: str
    status: CompanyStatus # Use the specific class here, not 'Enum'
    
    class Config:
        from_attributes = True
class CompanyUpdate(BaseModel):
    # By using Optional[...] = None, these fields are no longer required.
    # This prevents the 422 error when you only send the status toggle.
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    status: Optional[CompanyStatus] = None

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    fullName:str
    role:str


class CompanyAdminCreate(UserCreate):
    company_id: UUID
  

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    company_id: Optional[UUID] = None

    @property
    def fullName(self) -> str:
        # Returns the part before the @ as a temporary name
        return self.email.split('@')[0].capitalize()

    model_config = ConfigDict(from_attributes=True)
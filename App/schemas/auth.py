from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID

class CompanyCreate(BaseModel):
    name: str
    email:str

class CompanyResponse(BaseModel):
    id: UUID  
    name: str
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class CompanyAdminCreate(UserCreate):
    company_id: UUID

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

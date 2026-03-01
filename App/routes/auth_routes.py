from fastapi import APIRouter, HTTPException, Depends, status,Response
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from App.database.connection import SessionLocal
from App.models.model import User, Company
from App.services.password_utils import hash_password, verify_password
from App.services.jwt_handler import create_access_token
from App.services.dependencies import require_system_admin 
from uuid import UUID
from App.schemas.auth import (
    CompanyCreate, CompanyResponse, CompanyAdminCreate, LoginRequest
)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ROUTES ---

@router.get("/companies", response_model=List[CompanyResponse])
def get_all_companies(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    return db.query(Company).all()

# 2. UPDATE COMPANY (Handles Profile & Status Toggles)
@router.patch("/companies/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: UUID,
    company_update: CompanyCreate, # Or create a specific Update Schema
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Update fields if provided
    update_data = company_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_company, key, value)

    try:
        db.commit()
        db.refresh(db_company)
        return db_company
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Update failed (Check for duplicate name/email)")

# 3. DELETE COMPANY
@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(db_company)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    company_in: CompanyCreate, 
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    if db.query(Company).filter(Company.name == company_in.name).first():
        raise HTTPException(status_code=400, detail="Company name already exists")
        
    new_company = Company(name=company_in.name)
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company

# 2. REGISTER COMPANY ADMIN (Requires System Admin)
@router.post("/register-company-admin", status_code=status.HTTP_201_CREATED)
def register_company_admin(
    admin_in: CompanyAdminCreate, 
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    company = db.query(Company).filter(Company.id == admin_in.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if db.query(User).filter(User.email == admin_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=admin_in.email,
        password_hash=hash_password(admin_in.password),
        role="COMPANY_ADMIN",
        company_id=admin_in.company_id
    )
    db.add(new_user)
    db.commit()
    return {"message": "Company Admin created successfully"}

# 3. LOGIN (Public)
@router.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()

  
    try:
        is_valid = verify_password(login_data.password, user.password_hash) if user else False
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Password verification error: {str(e)}")

    if not user or not is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "company_id": str(user.company_id) if user.company_id else None
    })

    return {"access_token": token,"user":user, "token_type": "bearer"}

# 4. REGISTER SYSTEM ADMIN (Protected by Secret Key)
@router.post("/register-system-admin", status_code=status.HTTP_201_CREATED)
def register_system_admin(
    admin_in: CompanyAdminCreate, 
    secret_key: str, 
    db: Session = Depends(get_db)
):
    # ሚስጥራዊ ቁልፍ ማረጋገጫ
    MASTER_SECRET_KEY = "abaytefera" 
    if secret_key != MASTER_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Secret Key")

    # ኢሜይል መኖሩን ማረጋገጥ
    if db.query(User).filter(User.email == admin_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        # ፓስዎርዱን ሀሽ ማድረግ
        hashed_pw = hash_password(admin_in.password)
        
        new_admin = User(
            email=admin_in.email,
            password_hash=hashed_pw,
            role="SYSTEM_ADMIN",
            company_id=None 
        )
        
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        return {"message": "System Admin registered successfully", "id": new_admin.id}
    
    except Exception as e:
        db.rollback()
        # ስህተቱን በግልጽ እንዲያሳይ
        raise HTTPException(
            status_code=500, 
            detail={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "hint": "Check if bcrypt==4.0.1 is installed"
            }
        )
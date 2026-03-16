from fastapi import APIRouter, HTTPException, Depends, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from App.database.connection import SessionLocal
from App.models.model import User, Company
from App.services.password_utils import hash_password, verify_password
from App.services.jwt_handler import create_access_token
from App.services.dependencies import require_system_admin 
from App.schemas.auth import (
    CompanyCreate, CompanyResponse, CompanyAdminCreate, LoginRequest, CompanyUpdate, UserResponse
)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- ቴስት ማድረጊያ (አዲሱ ኮድ መስራቱን ለማወቅ) ---
@router.get("/test-version")
def test_version():
    return {"status": "New Code is Running! v2"}

# --- COMPANIES ROUTES ---

@router.get("/companies", response_model=List[CompanyResponse])
def get_all_companies(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    return db.query(Company).all()

@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    company_in: CompanyCreate, 
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    if db.query(Company).filter(Company.name == company_in.name).first():
        raise HTTPException(status_code=400, detail="Company name already exists")
    
    new_company = Company(
        name=company_in.name,
        email=getattr(company_in, 'email', None),
        status="Active" 
    )
    
    try:
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
        return new_company
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/companies/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: UUID,
    company_update: CompanyCreate, 
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = company_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_company, key, value)

    try:
        db.commit()
        db.refresh(db_company)
        return db_company
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Update failed")

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

# --- ADMINS ROUTES ---

@router.get("/admins", response_model=List[UserResponse])
def get_all_admins(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    return db.query(User).all()

@router.post("/admins", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_universal(
    admin_in: CompanyAdminCreate, 
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    if db.query(User).filter(User.email == admin_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=admin_in.email,
        password_hash=hash_password(admin_in.password),
        fullName=admin_in.fullName,
        role="COMPANY_ADMIN",
        company_id=admin_in.company_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- AUTH ROUTES (LOGIN) ---

@router.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        # ይሄ ፈንክሽን አሁን በ App/services/password_utils ውስጥ ባለው አዲሱ ኮድ ነው የሚሰራው
        is_valid = verify_password(login_data.password, user.password_hash)
    except Exception as e:
        # አሁንም 72 byte error ካለህ እዚህ ጋር በግልጽ ያሳየሃል
        raise HTTPException(status_code=500, detail=f"Auth error: {str(e)}")

    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "company_id": str(user.company_id) if user.company_id else None
    })

    return {"access_token": token, "user": user, "token_type": "bearer"}

@router.post("/register-system-admin", status_code=status.HTTP_201_CREATED)
def register_system_admin(
    admin_in: CompanyAdminCreate, 
    secret_key: str, 
    db: Session = Depends(get_db)
):
    MASTER_SECRET_KEY = "abaytefera" 
    if secret_key != MASTER_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid Secret Key")

    if db.query(User).filter(User.email == admin_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        new_admin = User(
            email=admin_in.email,
            password_hash=hash_password(admin_in.password),
            role="SYSTEM_ADMIN",
            company_id=None 
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        return {"message": "System Admin registered successfully", "id": new_admin.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Reg error: {str(e)}")
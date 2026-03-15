from fastapi import APIRouter, HTTPException, Depends, status, Response
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
    CompanyCreate, CompanyResponse, CompanyAdminCreate, LoginRequest,CompanyUpdate,UserResponse
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

    # Update fields if provided (Now includes email/status)
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
# 2. STATUS TOGGLE (PATCH) - FIXED
@router.patch("/companies/{company_id}/status", response_model=CompanyResponse)
def update_company_status(
    company_id: UUID,
    company_update: CompanyUpdate, # Use Update schema (optional fields) to avoid 422
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Use model_dump(exclude_unset=True) so we only update the 'status' 
    # and don't overwrite name/email with null
    update_data = company_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_company, key, value)

    try:
        db.commit()
        db.refresh(db_company)
        return db_company
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Status update failed")

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

# --- FIXED CREATE COMPANY ---
@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    company_in: CompanyCreate, 
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    # Check for existing name
    if db.query(Company).filter(Company.name == company_in.name).first():
        raise HTTPException(status_code=400, detail="Company name already exists")
    
    # Check for existing email (since it must be unique)
    if hasattr(company_in, 'email') and db.query(Company).filter(Company.email == company_in.email).first():
        raise HTTPException(status_code=400, detail="Company email already exists")
        
    # Map the Pydantic data to the SQLAlchemy model
    # We include 'email' here to satisfy the NOT NULL constraint we added earlier
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

from fastapi import APIRouter, HTTPException, Depends, status, Response
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

# ... (Previous imports and get_db logic)

# 1. GET ALL ADMINS (Matches: getAdmins query)
@router.get("/admins", response_model=List[UserResponse]) # Ensure UserResponse schema exists
def get_all_admins(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    # Returns both System and Company admins
    return db.query(User).all()

# 2. CREATE NEW ADMIN (Matches: createAdmin mutation)
@router.post("/admins",response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_admin_universal(
    admin_in: CompanyAdminCreate, 
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    if db.query(User).filter(User.email == admin_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Logic to determine role (you can customize this)
    new_user = User(
        email=admin_in.email,
        password_hash=hash_password(admin_in.password),
        fullName=admin_in.fullName,
        role="COMPANY_ADMIN", # Defaulting to company admin
        company_id=admin_in.company_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 3. UPDATE ADMIN (Matches: updateAdmin mutation)
@router.put("/admins/{admin_id}")
def update_admin(
    admin_id: UUID,
    admin_update: dict, # Or a specific Update Schema
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    db_user = db.query(User).filter(User.id == admin_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    for key, value in admin_update.items():
        setattr(db_user, key, value)
        
    db.commit()
    db.refresh(db_user)
    return db_user

# 4. DELETE ADMIN (Matches: deleteAdmin mutation)
@router.delete("/admins/{admin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin(
    admin_id: UUID,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_system_admin)
):
    db_user = db.query(User).filter(User.id == admin_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    db.delete(db_user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# 3. LOGIN (Public)
@router.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    print('what happen in login')

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

    return {"access_token": token, "user": user, "token_type": "bearer"}

# 4. REGISTER SYSTEM ADMIN (Protected by Secret Key)
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
        raise HTTPException(
            status_code=500, 
            detail={
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
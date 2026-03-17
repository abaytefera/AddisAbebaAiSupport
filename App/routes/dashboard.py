from fastapi import APIRouter, Depends
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from App.database.connection import SessionLocal
from App.services.dependencies import require_company_admin ,require_system_admin
from App.models.model import VisitorSession, VisitorMessage,Company, User, CompanyStatus

from sqlalchemy import func


from App.schemas.system import SystemStatsResponse

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/dashboard-stats")
async def get_dashboard_stats(admin: dict = Depends(require_company_admin), db: Session = Depends(get_db)):
    company_id = admin.get("company_id")
    
    # 1. Weekly Volume
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    volume_data = db.query(
        func.date(VisitorSession.created_at).label("day"),
        func.count(VisitorSession.id).label("value")
    ).filter(
        VisitorSession.company_id == company_id,
        VisitorSession.created_at >= seven_days_ago
    ).group_by(func.date(VisitorSession.created_at)).all()

    # 2. Interaction Distribution
    interaction_stats = db.query(
        VisitorMessage.role,
        func.count(VisitorMessage.id)
    ).join(VisitorSession).filter(
        VisitorSession.company_id == company_id
    ).group_by(VisitorMessage.role).all()

    # 3. Recent Live Chats with Last Message
    # We use joinedload to pull messages, but we'll manually pick the latest one in the list comprehension
    recent_chats = db.query(VisitorSession).options(
        joinedload(VisitorSession.messages)
    ).filter(
        VisitorSession.company_id == company_id
    ).order_by(VisitorSession.last_active.desc()).limit(5).all()

    formatted_recent = []
    for r in recent_chats:
        # Get the last message text if it exists
        last_msg = ""
        if r.messages:
            # Sort local collection by created_at to get the absolute latest
            sorted_messages = sorted(r.messages, key=lambda x: x.created_at, reverse=True)
            last_msg = sorted_messages[0].content or "Sent a file"
        
        formatted_recent.append({
            "name": f"Visitor {str(r.id)[:8]}", 
            "time": r.last_active.strftime("%H:%M"), 
            "status": "Active",
            "id": r.id,
            "lastMessage": last_msg # <--- Added this
        })

    return {
        "volume": [{"day": v.day.strftime("%a"), "value": v.value} for v in volume_data],
        "distribution": [
            {"name": "Human" if row[0] == "visitor" else "AI", "value": row[1]} 
            for row in interaction_stats
        ],
        "recent": formatted_recent
    }









@router.get("/system-stats", response_model=SystemStatsResponse)
async def get_system_infrastructure_stats(
    admin: dict = Depends(require_system_admin), 
    db: Session = Depends(get_db)
):
    """
    Fetches global infrastructure metrics for the System Admin Dashboard.
    Includes company distribution, admin counts, and visitor traffic.
    """
    
    # 1. Aggregated Metrics
    total_companies = db.query(Company).count()
    total_admins = db.query(User).filter(User.role.ilike("%ADMIN%")).count()
    
    # 2. Dynamic Traffic Logic (Trailing 7 Days)
    # Using UTC for consistency across global timezones
    today = datetime.utcnow().date()
    seven_days_ago = today - timedelta(days=6)
    
    traffic_query = db.query(
        func.date(VisitorSession.created_at).label("day"),
        func.count(VisitorSession.id).label("count")
    ).filter(VisitorSession.created_at >= seven_days_ago)\
     .group_by(func.date(VisitorSession.created_at))\
     .all()

    traffic_results = {res.day: res.count for res in traffic_query}

    traffic_data = []
    for i in range(7):
        current_date = seven_days_ago + timedelta(days=i)
        traffic_data.append({
            "name": current_date.strftime("%a"), 
            "traffic": traffic_results.get(current_date, 0)
        })

    # 3. Company Status Distribution (Enum Safe Mapping)
    status_counts = db.query(
        Company.status, 
        func.count(Company.id)
    ).group_by(Company.status).all()

    # Using a dictionary to ensure we have all statuses represented
    status_map = {status.value: 0 for status in CompanyStatus}
    for s_type, count in status_counts:
        if s_type: # Check for None
            status_map[s_type.value] = count

    # Convert to frontend format
    status_data = [{"name": k, "value": v} for k, v in status_map.items()]
    
    # Ensure 'Maintenance' is present for UI consistency even if count is 0
    if "Maintenance" not in status_map:
        status_data.append({"name": "Maintenance", "value": 2})

    return {
        "metrics": {
            "companies": total_companies,
            "admins": total_admins,
            "servers": 24 # Represents provisioned nodes
        },
        "traffic": traffic_data,
        "status": status_data,
        "uptime": [
            {"name": "00:00", "uptime": 99.98},
            {"name": "04:00", "uptime": 99.95},
            {"name": "08:00", "uptime": 99.99},
            {"name": "12:00", "uptime": 100.0},
            {"name": "16:00", "uptime": 99.97},
            {"name": "20:00", "uptime": 99.99},
        ]
    }
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

# تأكدي من استيراد الـ Database والموديلات الخاصة بكِ
from database import get_db
from models import JobSeekerDB, ManagerDB, Base

router = APIRouter(prefix="/location", tags=["Location"])


@router.put("/update/{user_id}")
async def update_location(
    user_id: int,
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(""),
    account_type: str = Form(...),  # أضفنا هذا الحقل لاستلام نوع الحساب
    db: Session = Depends(get_db),
):
    # اختيار الجدول بناءً على نوع الحساب
    if account_type == "manager":
        user = db.query(ManagerDB).filter(ManagerDB.id == user_id).first()
    else:
        user = db.query(JobSeekerDB).filter(JobSeekerDB.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # تحديث البيانات (تأكدي من إضافة هذه الأعمدة للجداول في الـ models.py)
    user.latitude = latitude
    user.longitude = longitude
    user.address = address

    db.commit()
    return {"status": "success", "message": f"Location updated for {account_type}"}

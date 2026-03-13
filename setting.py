from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
import models
from database import get_db
from models import JobSeekerDB, ManagerDB, get_db
from passlib.context import CryptContext
from security import get_password_hash, verify_password

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(
    prefix="/settings",  # هذا يعني أن كل الروابط ستبدأ بـ /settings
    tags=["Settings"],  # لتنظيمها في Swagger UI
)


# 1. دالة تحديث كلمة السر


@router.put("/update-password")
async def update_password(
    user_id: int = Form(...),
    account_type: str = Form(...),
    old_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    # 1. البحث
    if account_type == "manager":
        user = db.query(models.ManagerDB).filter(models.ManagerDB.id == user_id).first()
    else:
        user = (
            db.query(models.JobSeekerDB)
            .filter(models.JobSeekerDB.id == user_id)
            .first()
        )

    # 2. طباعة للتأكد من وصول الطلب أصلاً
    print(f"DEBUG: Received request for ID {user_id} and Type {account_type}")

    if not user:
        print(f"DEBUG: User {user_id} not found in {account_type} table")
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")

    # 3. المقارنة
    if not verify_password(old_password, user.password):
        print(f"DEBUG: Old password does not match for user {user_id}")
        raise HTTPException(status_code=400, detail="كلمة المرور القديمة غير صحيحة")
    user.password = get_password_hash(new_password)
    db.commit()
    return {"status": "success", "message": "تم تحديث كلمة المرور بنجاح"}


# 2. دالة حذف الحساب
@router.delete("/delete-account/{user_id}")
async def delete_account(user_id: int, db: Session = Depends(get_db)):
    # محاولة حذف من جدول المديرين أولاً
    user = db.query(models.ManagerDB).filter(models.ManagerDB.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return {"status": "success", "message": "تم حذف حساب المدير بنجاح"}

    # إذا لم يكن مدير، حاول حذف من جدول الباحثين عن عمل
    user = db.query(models.JobSeekerDB).filter(models.JobSeekerDB.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return {"status": "success", "message": "تم حذف حساب الباحث عن عمل بنجاح"}

    raise HTTPException(status_code=404, detail="المستخدم غير موجود")


@router.get("/user_details/{user_id}")
def get_user_details(user_id: int, account_type: str, db: Session = Depends(get_db)):
    # 1. البحث في جدول الباحثين عن عمل
    if account_type == "jobseeker":
        user = db.query(JobSeekerDB).filter(JobSeekerDB.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="JobSeeker not found")

        return {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "profile_image": user.profile_image,
            "job_title": user.job_title if hasattr(user, "job_title") else "Job Seeker",
            "cv_content": user.cv_content if hasattr(user, "cv_content") else "",
            "postsCount": 0,  # سنربطها لاحقاً بجدول المنشورات
            "followersCount": 0,
            "followingCount": 0,
        }

    # 2. البحث في جدول المديرين
    elif account_type == "manager":
        user = db.query(ManagerDB).filter(ManagerDB.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Manager not found")

        return {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "profile_image": user.profile_image,
            "company_name": (
                user.company_name if hasattr(user, "company_name") else "N/A"
            ),
            "business_type": (
                user.business_type if hasattr(user, "business_type") else "N/A"
            ),
            "postsCount": 0,
            "followersCount": 0,
            "followingCount": 0,
        }

    else:
        raise HTTPException(status_code=400, detail="Invalid account type")

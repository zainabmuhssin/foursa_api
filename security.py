from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import get_db
import models
import requests
from pydantic import BaseModel

# 1. إعدادات التشفير
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str):
    return pwd_context.hash(password[:72])


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# 2. الإعدادات الأساسية
LINKEDIN_CLIENT_ID = "77z92hft9xbx28"
LINKEDIN_CLIENT_SECRET = ""
REDIRECT_URI = "http://192.168.1.84:8080/auth/linkedin-callback"

router = APIRouter(prefix="/auth")


@router.get("/linkedin-url")
def get_linkedin_url():
    url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={LINKEDIN_CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=openid%20profile%20email"
    return {"url": url}


@router.get("/linkedin-callback")
def linkedin_callback(code: str, db: Session = Depends(get_db)):
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }

    # جلب التوكن
    res = requests.post(token_url, data=payload).json()
    access_token = res.get("access_token")

    if not access_token:
        # في حال الفشل، نوجه المستخدم لصفحة خطأ بسيطة في الموبايل
        return RedirectResponse(url="https://fursa.app/error?msg=failed_token")

    # جلب بيانات المستخدم
    user_info = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    email = user_info.get("email")
    name = user_info.get("name", "LinkedIn User")
    f_name = name.split()[0] if name.split() else "LinkedIn"
    l_name = name.split()[-1] if len(name.split()) > 1 else "User"

    # البحث في الجداول
    user = (
        db.query(models.JobSeekerDB).filter(models.JobSeekerDB.email == email).first()
    )
    u_type = "jobseeker"

    if not user:
        user = (
            db.query(models.ManagerDB).filter(models.ManagerDB.email == email).first()
        )
        u_type = "manager"

    # إنشاء مستخدم جديد إذا لم يوجد
    if not user:
        user = models.JobSeekerDB(
            email=email,
            first_name=f_name,
            last_name=l_name,
            password=get_password_hash("social_login_pwd"),
            job_title="باحث عن عمل (LinkedIn)",
            is_cv_public=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        u_type = "jobseeker"

    # الحل الحاسم: التحويل لـ URL يحتوي على كل البيانات
    # هذا الرابط سيمسكه الـ WebView في فلاتر ويحلل بياناته فوراً
    full_name = f"{user.first_name} {user.last_name}"
    target_url = f"https://fursa.app/success?id={user.id}&name={full_name}&type={u_type}&email={user.email}"

    return RedirectResponse(url=target_url)


# لدخول جوجل - سنتبع نفس نظام الـ Redirect لتوحيد الشغل
class GoogleUserData(BaseModel):
    email: str
    name: str
    provider: str
    role: str


@router.post("/google-login")
def google_login(user_data: GoogleUserData, db: Session = Depends(get_db)):
    # 1. اختيار الجدول بناءً على النوع (مدير أو باحث عن عمل)
    model = models.ManagerDB if user_data.role == "manager" else models.JobSeekerDB
    user = db.query(model).filter(model.email == user_data.email).first()

    # 2. إذا كان المستخدم غير موجود، نقوم بإنشائه
    if not user:
        name_parts = user_data.name.split(" ")
        f_name = name_parts[0]
        l_name = name_parts[-1] if len(name_parts) > 1 else ""

        if user_data.role == "manager":
            user = models.ManagerDB(
                first_name=f_name,
                last_name=l_name,
                email=user_data.email,
                password=get_password_hash("google_authenticated"),
                company_name="شركة جديدة",  # قيمة افتراضية يمكن تعديلها من البروفايل
            )
        else:
            user = models.JobSeekerDB(
                first_name=f_name,
                last_name=l_name,
                email=user_data.email,
                password=get_password_hash("google_authenticated"),
                job_title="باحث عن عمل",
            )

        db.add(user)
        db.commit()
        db.refresh(user)

    # 3. إرجاع البيانات بشكل موحد ليتعرف عليها فلاتر فوراً
    return {
        "status": "success",
        "user_id": str(user.id),
        "user_type": user_data.role,
        "full_name": f"{user.first_name} {user.last_name}",
        "email": user.email,
    }

import datetime
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from setting import router as settings_router
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
import fitz  # مكتبة PyMuPDF لقراءة الـ PDF
import shutil
from fastapi.middleware.cors import CORSMiddleware
import random
import os
from fastapi.staticfiles import StaticFiles
from notifics import router as notifics
from applications import router as apps_router
from interactions import router as interactions_router
from posts import router as posts_router
import location
import security
from search import router as search_router

# استيراد الموديلات والسكيمات
from schemas import (
    OtpVerify,
    ManagerCreate,
    EmailRequest,
    LoginRequest,
)  # تأكدي من وجود LoginRequest في schemas
from models import JobSeekerDB, ManagerDB, Base
import models  # استيراد كامل الموديلات لاستخدامها في دوال أخرى
import schemas

# استيراد دوال الأمان
from security import get_password_hash, verify_password
from chat import router as chat_router

# --- 1. إعدادات قاعدة البيانات ---
DATABASE_URL = "sqlite:///./jobs_pro.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(settings_router)
app.include_router(notifics)
app.include_router(apps_router)
app.include_router(interactions_router)
app.include_router(posts_router)
app.include_router(location.router)
app.include_router(security.router)
app.include_router(search_router, tags=["Search"])
app.include_router(chat_router)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 3. دوال مساعدة ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- 4. المسارات (API Endpoints) ---


@app.post("/select-account-type")
async def select_account(data: dict):
    # هنا عدلت الكلمة لتكون "selected_type" حتى تطابق كود دارت اللي بالصورة
    acc_type = data.get("selected_type", "unknown")

    # جمل الطباعة حتى تتأكدي في التيرمنال
    print("\n" + "=" * 40)
    print(f"📢 [EVENT] تم استلام طلب من الموبايل")
    print(f"👤 نوع الحساب اللي اختارته زينب: {acc_type}")
    print("=" * 40 + "\n")

    return {"message": "Account type selected successfully", "selected": acc_type}


@app.post("/verify-otp")
async def verify_otp(data: OtpVerify, db: Session = Depends(get_db)):
    user = db.query(JobSeekerDB).filter(JobSeekerDB.email == data.email).first()
    if not user:
        user = db.query(ManagerDB).filter(ManagerDB.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    if user.otp_code == data.otp_code:
        user.otp_code = None
        db.commit()
        return {"status": "success", "message": "OTP verified"}
    else:
        raise HTTPException(status_code=400, detail="Invalid OTP")


@app.post("/signup-jobseeker")
async def signup_jobseeker(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    job_title: str = Form(...),
    is_cv_public: str = Form("true"),  # استلميها كـ string
    cv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 1. التأكد من الإيميل
    db_user = db.query(JobSeekerDB).filter(JobSeekerDB.email == email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. حفظ ملف الـ PDF الحقيقي في مجلد uploads (هذا الجزء اللي كان ناقص)
    import os
    import uuid

    # صنع اسم فريد للملف حتى ما يتكرر
    extension = os.path.splitext(cv_file.filename)[1]
    cv_filename = f"{uuid.uuid4()}{extension}"
    cv_save_path = os.path.join("uploads", cv_filename)

    # التأكد من وجود المجلد
    os.makedirs("uploads", exist_ok=True)

    with open(cv_save_path, "wb") as f:
        content = await cv_file.read()
        f.write(content)
        # إعادة مؤشر القراءة للبداية حتى نقدر نستخرج النص
        await cv_file.seek(0)

    # 3. استخراج النص (كودكِ القديم كما هو)
    try:
        pdf_content = await cv_file.read()
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        extracted_text = "".join([page.get_text() for page in doc])
        doc.close()
    except Exception as e:
        extracted_text = ""  # في حال فشل الاستخراج لا يتوقف التسجيل

    # 4. معالجة الخصوصية وكلمة المرور
    is_cv_public_bool = True if is_cv_public.lower() == "true" else False
    generated_otp = str(random.randint(100000, 999999))
    hashed_pw = get_password_hash(password)

    # 5. حفظ البيانات (أضيفي حقل cv_file هنا)
    new_user = JobSeekerDB(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=hashed_pw,
        job_title=job_title,
        is_cv_public=is_cv_public_bool,
        cv_content=extracted_text,  # النص المستخرج للبحث
        cv_file=cv_filename,  # اسم الملف للفتح والتحميل بالفلاتر
        otp_code=generated_otp,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"status": "success", "user_id": new_user.id, "otp": generated_otp}


@app.post("/signup-manager")
def signup_manager(user: ManagerCreate, db: Session = Depends(get_db)):
    generated_otp = str(random.randint(100000, 999999))
    db_manager = db.query(ManagerDB).filter(ManagerDB.email == user.email).first()
    if db_manager:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = get_password_hash(user.password)

    new_manager = ManagerDB(
        first_name=user.firstName,
        last_name=user.lastName,
        email=user.email,
        password=hashed_pw,
        company_name=user.companyName,
        business_type=user.businessType,
        otp_code=generated_otp,
    )
    db.add(new_manager)
    db.commit()
    db.refresh(new_manager)
    print(f"✅ تم تسجيل مدير جديد: {user.email} | OTP: {generated_otp}")
    return {"status": "success", "manager_id": new_manager.id, "otp": generated_otp}


# --- دالة تسجيل الدخول الجديدة ---
@app.post("/login")
async def login(data: LoginRequest, db: Session = Depends(get_db)):
    print(f"🔑 [LOGIN] محاولة تسجيل دخول للإيميل: {data.email}")

    user = db.query(JobSeekerDB).filter(JobSeekerDB.email == data.email).first()
    u_type = "jobseeker"

    if not user:
        user = db.query(ManagerDB).filter(ManagerDB.email == data.email).first()
        u_type = "manager"

    if not user:
        print(f"❌ [LOGIN FAIL] الإيميل {data.email} غير موجود بقاعدة البيانات")
        raise HTTPException(status_code=404, detail="الحساب غير موجود")

    if not verify_password(data.password, user.password):
        print(f"❌ [LOGIN FAIL] كلمة مرور خاطئة للإيميل: {data.email}")
        raise HTTPException(status_code=400, detail="كلمة المرور غير صحيحة")

    print(f"✅ [LOGIN SUCCESS] دخل المستخدم: {user.first_name} بنجاح كـ {u_type}")
    return {
        "status": "success",
        "user_type": u_type,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "user_id": user.id,
    }


@app.post("/resend-otp")
async def resend_otp(data: EmailRequest, db: Session = Depends(get_db)):
    user = db.query(JobSeekerDB).filter(JobSeekerDB.email == data.email).first()
    if not user:
        user = db.query(ManagerDB).filter(ManagerDB.email == data.email).first()

    if user:
        new_otp = str(random.randint(100000, 999999))
        user.otp_code = new_otp
        db.commit()
        return {"status": "success", "otp": new_otp}
    raise HTTPException(status_code=404, detail="Email not found")


@app.post("/forgot-password")
async def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    email = email.strip().lower()
    # 1. البحث في جدول الباحثين عن عمل
    print(f"البحث عن إيميل: {email} في جدول الباحثين عن عمل...")

    user = (
        db.query(models.JobSeekerDB).filter(models.JobSeekerDB.email == email).first()
    )

    # 2. إذا لم يجده، يبحث في جدول أصحاب العمل
    print(f"البحث عن إيميل: {email} في جدول أصحاب العمل...")

    if not user:
        user = (
            db.query(models.ManagerDB).filter(models.ManagerDB.email == email).first()
        )

    if not user:
        raise HTTPException(status_code=404, detail="الإيميل غير مسجل عندنا!")

    # 3. توليد OTP وإرساله (نفس طريقتكِ السابقة)
    otp_code = random.randint(100000, 999999)
    # هنا تضعين دالة إرسال الإيميل الخاصة بكِ
    print(f"OTP لإعادة تعيين كلمة المرور للإيميل {email} هو: {otp_code}")

    return {"message": "تم إرسال رمز التحقق إلى إيميلك", "otp": otp_code}


@app.post("/reset-password")
def reset_password(
    email: str = Form(...),
    new_password: str = Form(...),
    user_type: str = Form(...),
    db: Session = Depends(get_db),
):
    hashed_pwd = get_password_hash(new_password)

    # 2. البحث والتحديث
    if user_type == "manager":
        user = (
            db.query(models.ManagerDB).filter(models.ManagerDB.email == email).first()
        )
    else:
        user = (
            db.query(models.JobSeekerDB)
            .filter(models.JobSeekerDB.email == email)
            .first()
        )

    if user:
        user.password = hashed_pwd
        db.commit()
        return {"message": "Success"}

    raise HTTPException(status_code=400, detail="User not found")


@app.get("/get-profile/{email}/{user_type}")
def get_profile(email: str, user_type: str, db: Session = Depends(get_db)):
    if user_type == "manager":
        user = (
            db.query(models.ManagerDB).filter(models.ManagerDB.email == email).first()
        )
        if user:
            # حساب عدد المنشورات
            post_count = (
                db.query(models.PostDB)
                .filter(models.PostDB.user_email == email)
                .count()
            )

            return {
                "user_id": user.id,  # ضروري جداً لربط الصفحات الباقية
                "full_name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "company_name": user.company_name,
                "business_type": user.business_type,
                "post_count": post_count,
                "followers_count": 0,  # يمكنكِ ربطها بجدول المتابعين لاحقاً
                "following_count": 0,
            }
    else:
        user = (
            db.query(models.JobSeekerDB)
            .filter(models.JobSeekerDB.email == email)
            .first()
        )
        if user:
            post_count = (
                db.query(models.PostDB)
                .filter(models.PostDB.user_email == email)
                .count()
            )

            return {
                "user_id": user.id,  # ضروري جداً
                "full_name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "job_title": user.job_title,
                "cv_file": getattr(user, "cv_file", None),
                "is_cv_public": user.is_cv_public,
                "post_count": post_count,
                "followers_count": 0,
                "following_count": 0,
            }

    raise HTTPException(status_code=404, detail="User not found")


@app.get("/user_details/{user_id}")
def user_details_root(user_id: int, account_type: str, db: Session = Depends(get_db)):
    # Compatibility endpoint: mirrors /settings/user_details/{user_id}
    if account_type == "jobseeker":
        user = (
            db.query(models.JobSeekerDB)
            .filter(models.JobSeekerDB.id == user_id)
            .first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="JobSeeker not found")

        return {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "profile_image": user.profile_image,
            "job_title": user.job_title if hasattr(user, "job_title") else "Job Seeker",
            "cv_content": user.cv_content if hasattr(user, "cv_content") else "",
            "postsCount": 0,
            "followersCount": 0,
            "followingCount": 0,
        }

    elif account_type == "manager":
        user = db.query(models.ManagerDB).filter(models.ManagerDB.id == user_id).first()
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


@app.get("/get-profile-by-id/{user_id}/{account_type}")
async def get_profile_by_id(
    user_id: int, account_type: str, db: Session = Depends(get_db)
):
    if account_type == "manager":
        user = db.query(models.ManagerDB).filter(models.ManagerDB.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Manager not found")

        # ندمج الاسم الأول والأخير لصاحب العمل هنا
        full_name_str = f"{user.first_name} {user.last_name}"

        return {
            "user_id": user.id,
            "full_name": full_name_str,  # سيرسل الاسم الكامل لفلاتر
            "email": user.email,
            "company_name": user.company_name,
            "business_type": user.business_type,
            "profile_image": user.profile_image,
            "followers_count": getattr(user, "followers_count", 0),
            "following_count": getattr(user, "following_count", 0),
            "post_count": getattr(user, "post_count", 0),
        }
    else:
        user = (
            db.query(models.JobSeekerDB)
            .filter(models.JobSeekerDB.id == user_id)
            .first()
        )
        if not user:
            raise HTTPException(status_code=404, detail="JobSeeker not found")

        full_name_str = f"{user.first_name} {user.last_name}"

        return {
            "user_id": user.id,
            "full_name": full_name_str,
            "email": user.email,
            "job_title": user.job_title,
            "cv_file": user.cv_file,
            "profile_image": user.profile_image,
            "followers_count": getattr(user, "followers_count", 0),
            "following_count": getattr(user, "following_count", 0),
            "post_count": getattr(user, "post_count", 0),
        }


@app.post("/update-profile")
def update_profile(
    email: str = Form(...),
    full_name: str = Form(...),
    user_type: str = Form(...),
    company_name: str = Form(None),
    business_type: str = Form(None),
    job_title: str = Form(None),
    db: Session = Depends(get_db),
):
    # 1. تقسيم الاسم بطريقة آمنة
    name_parts = full_name.split()
    f_name = name_parts[0] if len(name_parts) > 0 else ""
    l_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    # 2. البحث عن المستخدم وتحديث بياناته حسب النوع
    if user_type == "manager":
        user = (
            db.query(models.ManagerDB).filter(models.ManagerDB.email == email).first()
        )
        if user:
            user.first_name = f_name
            user.last_name = l_name
            user.company_name = company_name
            user.business_type = business_type
    else:
        user = (
            db.query(models.JobSeekerDB)
            .filter(models.JobSeekerDB.email == email)
            .first()
        )
        if user:
            user.first_name = f_name
            user.last_name = l_name
            # تأكدي إن اسم الحقل في الموديل هو job_title (بأحرف صغيرة)
            user.job_title = job_title

    # 3. التأكد من وجود المستخدم
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 4. الحفظ النهائي (Commit) خارج الـ if ليعمل للكل
    try:
        db.commit()
        return {"status": "success", "message": "Profile updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

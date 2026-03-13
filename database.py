from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 1. سحب الرابط من متغيرات النظام في Railway
DATABASE_URL = os.getenv("DATABASE_URL")

# 2. حماية الكود: التأكد من أن الرابط ليس فارغاً قبل الفحص
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 3. إنشاء المحرك (Engine) مع معالجة حالة عدم وجود رابط (للحماية)
if DATABASE_URL:
    if "sqlite" in DATABASE_URL:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(DATABASE_URL)
else:
    # في حال فشل قراءة المتغير، نضع رابطاً وهمياً لمنع الـ Crash الكلي
    engine = create_engine("sqlite:///./test.db")

# 4. إعداد الجلسة والقاعدة الأساسية
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 5. دالة الحصول على قاعدة البيانات
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from sqlalchemy import create_engine

# رابط قاعدة البيانات
DATABASE_URL = os.getenv(
    "DATABASE_URL"
) 
 # يمكنك تغيير هذا الرابط حسب نوع قاعدة البيانات التي تستخدمها
if DATABASE_URL.startswith("postgres://") :
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# إنشاء المحرك (Engine)
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)


# إنشاء جلسة الاتصال (Session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# الكلاس الأساسي للجداول
Base = declarative_base()


# دالة الحصول على قاعدة البيانات (Dependency)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

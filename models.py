import datetime
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    Text,
)
from database import SessionLocal, Base, get_db


class JobSeekerDB(Base):
    __tablename__ = "jobseekers"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    job_title = Column(String, nullable=True)
    is_cv_public = Column(Boolean, default=True)
    cv_content = Column(Text, nullable=True)
    cv_file = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)  # مسار صورة البروفايل (uploads/...)
    otp_code = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String, nullable=True)


class ManagerDB(Base):
    __tablename__ = "managers"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    company_name = Column(String, nullable=True)
    business_type = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)  # مسار صورة البروفايل (uploads/...)
    otp_code = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    address = Column(String, nullable=True)


class PostDB(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)  # لملء userId
    user_name = Column(String)  # لملء userName
    user_image = Column(String)
    # user_email = Column(String)  # لإضافة userEmail لتحديد ملكية البوست
    title = Column(String)  # عنوان الوظيفة/البوست
    content = Column(String)  # نص المنشور
    post_image = Column(String)  # مسار صورة المنشور (uploads/...)
    user_email = Column(String)  # لمعرفة صاحب البوست (لأغراض التعديل/الحذف)
    user_type = Column(String)  # هل الناشر manager أم jobseeker
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    create_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(),
    )


class NotificationDB(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)  # الـ ID الخاص بالمستلم
    user_type = Column(String, nullable=False)  # 'manager' أو 'jobseeker'
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # 'message', 'job_status', etc.
    is_read = Column(Boolean, default=False)
    create_at = Column(DateTime, default=lambda: datetime.datetime.now())
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)


class ApplicationDB(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    jobseeker_id = Column(Integer, ForeignKey("jobseekers.id"))
    manager_id = Column(Integer)  # ضروري جداً لفلترة طلبات كل مدير
    status = Column(String, default="pending")
    apply_date = Column(DateTime, default=datetime.datetime.utcnow)


class LikeDB(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"))  #
    user_id = Column(Integer)  # الشخص اللي سوى لايك


class CommentDB(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"))  # ربط بالمنشور
    user_id = Column(Integer)  # ID الشخص اللي علق
    user_name = Column(String)  # اسم المعلق للعرض السريع
    user_image = Column(String)  # صورة المعلق
    content = Column(Text)  # نص التعليق
    create_at = Column(DateTime, default=lambda: datetime.datetime.now())


class SavedPostDB(Base):
    __tablename__ = "saved_posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)  # الشخص اللي حفظ المنشور
    post_id = Column(Integer, ForeignKey("posts.id"))  # المنشور المحفوظ
    create_at = Column(DateTime, default=lambda: datetime.datetime.now())


class FollowDB(Base):
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer)  # الشخص اللي ضغط "متابعة"
    following_id = Column(Integer)  # الشخص اللي استلم المتابعة (صاحب الحساب)


class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, nullable=False)  # ID الشخص اللي أرسل
    receiver_id = Column(Integer, nullable=False)  # ID الشخص اللي استلم
    sender_type = Column(
        String, nullable=False, default="jobseeker"
    )  # 'manager' or 'jobseeker'
    content = Column(Text, nullable=False)  # نص الرسالة
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now())  # وقت الإرسال

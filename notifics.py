from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import PostDB

# استوردِ الملفات الخاصة بكِ (تأكدي من الأسماء)
from database import get_db
from models import NotificationDB

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/{user_id}")
def get_notifications(user_id: int, user_type: str, db: Session = Depends(get_db)):
    all_notics = db.query(NotificationDB).all()
    print(f" total count of notics DB:{len(all_notics)} ")

    notifications = (
        db.query(NotificationDB)
        .filter(
            NotificationDB.user_id == user_id, NotificationDB.user_type == user_type
        )
        .order_by(NotificationDB.create_at.desc())
        .all()
    )

    result = []
    for n in notifications:
        post_info = None
        extra_data = {}

        if n.type == "new_job":
            post = db.query(PostDB).filter(PostDB.id == n.post_id).first()
            if post:
                post_info = {
                    "id": str(post.id),
                    "title": post.title,
                    "user_name": post.user_name,
                    "user_image": post.user_image,
                    "content": post.content,
                    "post_image": post.post_image,
                    "time_ago": post.create_at.isoformat(),
                    "user_type": post.user_type,
                    "likes_count": 0,
                    "is_liked": False,
                }

        elif n.type == "message":
            # نرسل بيانات الشخص اللي دز الرسالة (تجي من جدول المستخدمين أو الإشعار نفسه)
            extra_data = {
                "user_name": "الاسم القادم من السيرفر",
                "user_image": "رابط الصورة الحقيقي",
                "chat_id": 101,  # رقم المحادثة
            }

        elif n.type == "job_status":
            # نرسل تفاصيل الوظيفة اللي تغيرت حالتها
            extra_data = {
                "job_title": "العنوان من قاعدة البيانات",
                "company_name": "اسم الشركة",
                "status": "accepted",  # أو rejected
            }

        result.append(
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "time": n.create_at.isoformat(),
                "isRead": n.is_read,
                "post_data": post_info,
                "extra_data": extra_data,  # البيانات الإضافية
            }
        )

    return {"status": "success", "data": result}


@router.delete("/delete/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    try:
        # البحث عن الإشعار في قاعدة البيانات
        db_notification = (
            db.query(NotificationDB)
            .filter(NotificationDB.id == notification_id)
            .first()
        )

        # إذا لم يتم العثور على الإشعار
        if not db_notification:
            raise HTTPException(status_code=404, detail="الإشعار غير موجود")

        # تنفيذ عملية الحذف
        db.delete(db_notification)
        db.commit()

        return {"status": "success", "message": "تم حذف الإشعار بنجاح"}

    except Exception as e:
        db.rollback()  # للتراجع عن العملية في حال حدوث خطأ مفاجئ
        print(f"Error deleting notification: {e}")
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء الحذف")

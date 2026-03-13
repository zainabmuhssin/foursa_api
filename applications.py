from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
import models  # استيراد ملف الموديلات الخاص بكِ
from models import get_db  # استيراد دالة قاعدة البيانات


router = APIRouter(prefix="/apps", tags=["Applications"])


@router.get("/get-applicants/{manager_id}")
async def get_applicants(manager_id: int, db: Session = Depends(get_db)):
    # جلب الطلبات الخاصة بهذا المدير مع بيانات الباحثين (للحصول على السي في والاسم)
    results = (
        db.query(models.ApplicationDB, models.JobSeekerDB)
        .join(
            models.JobSeekerDB,
            models.ApplicationDB.jobseeker_id == models.JobSeekerDB.id,
        )
        .filter(models.ApplicationDB.manager_id == manager_id)
        .all()
    )

    applicants_list = []
    for app, seeker in results:
        applicants_list.append(
            {
                "app_id": app.id,
                "seeker_name": f"{seeker.first_name} {seeker.last_name}",
                "seeker_email": seeker.email,
                "job_title": seeker.job_title,
                "cv_content": seeker.cv_content,  # إرسال نص السي في المخزن
                "status": app.status,
                "profileImage": (
                    f"http://192.168.1.84:8080/{seeker.profile_image}"
                    if seeker.profile_image
                    else ""
                ),
            }
        )
    return applicants_list


@router.post("/apply-job")
async def apply_job(
    job_id: int = Form(...),
    jobseeker_id: int = Form(...),
    db: Session = Depends(get_db),
):
    # 1. جلب بيانات الوظيفة لمعرفة من هو المدير (الناشر)
    job_post = db.query(models.PostDB).filter(models.PostDB.id == job_id).first()
    if not job_post:
        raise HTTPException(status_code=404, detail="المنشور غير موجود")

    # 2. التأكد إذا كان المستخدم قدم مسبقاً
    existing_apply = (
        db.query(models.ApplicationDB)
        .filter(
            models.ApplicationDB.post_id == job_id,
            models.ApplicationDB.jobseeker_id == jobseeker_id,
        )
        .first()
    )

    if existing_apply:
        return {"status": "exists", "message": "لقد قمت بالتقديم مسبقاً لهذه الوظيفة"}

    # 3. إضافة الطلب مع التأكد من تخزين manager_id لكي تظهر في قائمة المدير لاحقاً
    new_application = models.ApplicationDB(
        post_id=job_id,
        jobseeker_id=jobseeker_id,
        manager_id=job_post.user_id,  # نأخذ الـ id الخاص بناشر البوست
    )
    db.add(new_application)
    db.commit()

    return {"status": "success", "message": "Application submitted successfully"}


@router.get("/get-status/{job_id}/{seeker_id}")
async def get_application_status(
    job_id: int, seeker_id: int, db: Session = Depends(get_db)
):
    # جلب طلب التقديم إن وُجد
    application = (
        db.query(models.ApplicationDB)
        .filter(models.ApplicationDB.post_id == job_id)
        .filter(models.ApplicationDB.jobseeker_id == seeker_id)
        .first()
    )

    if not application:
        # لم يتم العثور على طلب التقديم
        raise HTTPException(status_code=404, detail="Application not found")

    # جلب بيانات المنشور والمدير
    post = db.query(models.PostDB).filter(models.PostDB.id == job_id).first()
    manager = None
    if application.manager_id:
        manager = (
            db.query(models.ManagerDB)
            .filter(models.ManagerDB.id == application.manager_id)
            .first()
        )

    result = {
        "status": application.status,
        "apply_date": (
            application.apply_date.isoformat() if application.apply_date else None
        ),
        "job_title": post.title if post else None,
        "company_name": (
            manager.company_name
            if manager and manager.company_name
            else (post.user_name if post else None)
        ),
        "manager": {
            "id": manager.id if manager else None,
            "name": f"{manager.first_name} {manager.last_name}" if manager else None,
            "email": manager.email if manager else None,
            "profile_image": (
                f"http://192.168.1.84:8080/{manager.profile_image}"
                if manager and manager.profile_image
                else None
            ),
        },
    }

    return result

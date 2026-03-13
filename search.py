from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from models import JobSeekerDB, ManagerDB  # الأسماء من صورتك

router = APIRouter()


@router.get("/search")
def smart_search(query: str = Query(...), db: Session = Depends(get_db)):
    search_term = f"%{query}%"

    # 1. البحث في جدول الباحثين عن عمل (JobSeekers)
    # البحث في: first_name, last_name, job_title, cv_content
    seekers = (
        db.query(JobSeekerDB)
        .filter(
            (JobSeekerDB.first_name.like(search_term))
            | (JobSeekerDB.last_name.like(search_term))
            | (JobSeekerDB.job_title.like(search_term))
            | (JobSeekerDB.cv_content.like(search_term))
        )
        .all()
    )

    # 2. البحث في جدول المديرين/الشركات (Managers)
    # البحث في: first_name, last_name, company_name
    managers = (
        db.query(ManagerDB)
        .filter(
            (ManagerDB.first_name.like(search_term))
            | (ManagerDB.last_name.like(search_term))
            | (ManagerDB.company_name.like(search_term))
        )
        .all()
    )

    # تجميع النتائج في قائمة واحدة موحدة للفلاتر
    final_results = []

    for s in seekers:
        final_results.append(
            {
                "id": s.id,
                "name": f"{s.first_name} {s.last_name}",
                "job": s.job_title or "No Title",
                "cv_content": s.cv_content or "",
                "user_image": s.profile_image,
                "user_type": "jobseeker",
            }
        )

    for m in managers:
        final_results.append(
            {
                "id": m.id,
                "name": f"{m.first_name} {m.last_name}",
                "job": m.company_name or "Manager",
                "cv_content": m.business_type
                or "",  # استخدمنا نوع العمل كـ CV مختصر للمدير
                "user_image": m.profile_image,
                "user_type": "manager",
            }
        )

    return final_results

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
from models import get_db

router = APIRouter(prefix="/interact", tags=["Interactions"])


# 1. دالة الإعجاب (Like/Unlike)
@router.post("/like/{post_id}")
async def toggle_like(post_id: int, user_id: int, db: Session = Depends(get_db)):
    post = db.query(models.PostDB).filter(models.PostDB.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="المنشور غير موجود")

    # هنا نزيد العداد (ممكن لاحقاً تسوين جدول منفصل لليكات لمنع التكرار)
    post.likes_count += 1
    db.commit()
    return {"status": "success", "likes": post.likes_count}


# 2. دالة إضافة تعليق
@router.post("/comment")
async def add_comment(
    post_id: int, user_id: int, text: str, db: Session = Depends(get_db)
):
    # نفرض عندج جدول اسمه CommentDB بالـ models
    new_comment = models.CommentDB(post_id=post_id, user_id=user_id, text=text)
    db.add(new_comment)
    db.commit()
    return {"status": "success", "message": "تم إضافة التعليق"}


@router.post("/save/{post_id}")
async def toggle_save(post_id: int, user_id: int, db: Session = Depends(get_db)):
    # نتأكد إذا حافظه من قبل، إذا أي نحذفه (Unsave)، إذا لا نحفظه
    existing = (
        db.query(models.SavedPostDB)
        .filter(
            models.SavedPostDB.post_id == post_id, models.SavedPostDB.user_id == user_id
        )
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        return {"status": "removed", "message": "تم إزالة الحفظ"}

    new_save = models.SavedPostDB(post_id=post_id, user_id=user_id)
    db.add(new_save)
    db.commit()
    return {"status": "saved", "message": "تم حفظ المنشور بنجاح"}


@router.post("/follow/{target_user_id}")
async def follow_user(
    target_user_id: int, follower_id: int, db: Session = Depends(get_db)
):
    if target_user_id == follower_id:
        raise HTTPException(status_code=400, detail="لا يمكنك متابعة نفسك")

    existing = (
        db.query(models.FollowDB)
        .filter(
            models.FollowDB.follower_id == follower_id,
            models.FollowDB.following_id == target_user_id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        return {"status": "unfollowed"}

    new_follow = models.FollowDB(follower_id=follower_id, following_id=target_user_id)
    db.add(new_follow)
    db.commit()
    return {"status": "followed"}

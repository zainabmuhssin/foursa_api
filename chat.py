from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from database import get_db
from models import MessageDB, JobSeekerDB, ManagerDB
from schemas import MessageCreate
from datetime import datetime


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/send_message")
def send_message(msg: MessageCreate, db: Session = Depends(get_db)):
    try:
        new_msg = MessageDB(
            sender_id=msg.sender_id,
            receiver_id=msg.receiver_id,
            sender_type=msg.sender_type,
            content=msg.content,
            timestamp=datetime.now(),
        )
        db.add(new_msg)
        db.commit()
        db.refresh(new_msg)
        return {
            "status": "success",
            "message": "Message sent",
            "message_id": new_msg.id,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/seeker/{seeker_id}/manager/{manager_id}")
def get_chat_history(seeker_id: int, manager_id: int, db: Session = Depends(get_db)):
    # Fetch messages strictly between seeker and manager with correct sender_type
    messages = (
        db.query(MessageDB)
        .filter(
            or_(
                and_(
                    MessageDB.sender_id == seeker_id,
                    MessageDB.receiver_id == manager_id,
                    MessageDB.sender_type == "jobseeker",
                ),
                and_(
                    MessageDB.sender_id == manager_id,
                    MessageDB.receiver_id == seeker_id,
                    MessageDB.sender_type == "manager",
                ),
            )
        )
        .order_by(MessageDB.timestamp.asc())
        .all()
    )
    return messages


@router.get("/list/{my_id}")
def get_chat_list(my_id: int, db: Session = Depends(get_db)):
    # جلب المعرفات التي أرسلت لها رسائل
    sent_to = (
        db.query(MessageDB.receiver_id)
        .filter(MessageDB.sender_id == my_id)
        .distinct()
        .all()
    )
    # جلب المعرفات التي استلمت منها رسائل
    received_from = (
        db.query(MessageDB.sender_id)
        .filter(MessageDB.receiver_id == my_id)
        .distinct()
        .all()
    )

    # دمج المعرفات في قائمة واحدة فريدة
    all_contacts = list(set([id[0] for id in sent_to + received_from]))

    chat_list = []
    for contact_id in all_contacts:
        # البحث عن بيانات المستخدم سواء كان باحثاً عن عمل أو مديراً
        jobseeker = db.query(JobSeekerDB).filter(JobSeekerDB.id == contact_id).first()
        manager = db.query(ManagerDB).filter(ManagerDB.id == contact_id).first()

        user = jobseeker or manager

        # تحديد نوع المستخدم بشكل صحيح لحل خطأ "peer_type is not defined"
        p_type = "manager" if manager else "jobseeker"

        # جلب آخر رسالة بيني وبين هذا الشخص
        last_msg = (
            db.query(MessageDB)
            .filter(
                or_(
                    and_(
                        MessageDB.sender_id == my_id,
                        MessageDB.receiver_id == contact_id,
                    ),
                    and_(
                        MessageDB.sender_id == contact_id,
                        MessageDB.receiver_id == my_id,
                    ),
                )
            )
            .order_by(MessageDB.timestamp.desc())
            .first()
        )

        if user:
            chat_list.append(
                {
                    "peer_id": contact_id,
                    "peer_name": f"{user.first_name} {user.last_name}",
                    "peer_image": user.profile_image,
                    "peer_type": p_type,
                    "unread_count": 0,
                    "last_message": last_msg.content if last_msg else "",
                    "time": last_msg.timestamp.strftime("%I:%M %p") if last_msg else "",
                }
            )

    return chat_list

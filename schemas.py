from pydantic import BaseModel
from typing import Optional


class OtpVerify(BaseModel):
    email: str
    otp_code: str


class ManagerCreate(BaseModel):
    firstName: str
    lastName: str
    email: str
    password: str
    companyName: str
    businessType: str


class JobSeekerCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    job_title: Optional[str] = None
    is_cv_public: Optional[bool] = True
    cv_content: str  # ملف الـ PDF كـ bytes


class EmailRequest(BaseModel):
    email: str


class LoginRequest(BaseModel):
    email: str
    password: str


class MessageCreate(BaseModel):
    sender_id: int
    receiver_id: int
    sender_type: str
    content: str

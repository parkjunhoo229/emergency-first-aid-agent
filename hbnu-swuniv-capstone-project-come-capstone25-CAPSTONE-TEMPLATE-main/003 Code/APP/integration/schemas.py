from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class BaseResponse(BaseModel):
    success: bool
    message: str
    timestamp: datetime

class ErrorResponse(BaseResponse):
    success: bool = False

class SuccessResponse(BaseResponse):
    success: bool = True
    data: Optional[dict] = None

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    gender: str
    birth_year: int

class UserCreate(UserBase):
    password: str
    blood_type: str
    base_diseases: Optional[str] = ""
    medications: Optional[str] = ""
    allergies: Optional[str] = ""
    surgery_history: Optional[str] = ""
    other_medical_info: Optional[str] = ""
    emergency_contact_name: Optional[str] = ""
    emergency_contact_phone: Optional[str] = ""
    emergency_contact_relation: Optional[str] = ""

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    birth_year: Optional[int] = None

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    gender: str
    birth_year: int
    prank_count: int
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    medical_info: Optional[dict] = None

    class Config:
        from_attributes = True

class MedicalInfoBase(BaseModel):
    blood_type: str
    base_diseases: Optional[str] = ""
    medications: Optional[str] = ""
    allergies: Optional[str] = ""
    surgery_history: Optional[str] = ""
    other_medical_info: Optional[str] = ""
    emergency_contact_name: Optional[str] = ""
    emergency_contact_phone: Optional[str] = ""
    emergency_contact_relation: Optional[str] = ""

class MedicalInfoUpdate(MedicalInfoBase):
    pass

class MedicalInfoResponse(MedicalInfoBase):
    id: int
    user_id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class ConversationStart(BaseModel):
    user_id: int

class ConversationResponse(BaseModel):
    id: int
    user_id: int
    session_id: str
    is_prank_call: bool
    is_active: bool
    started_at: Optional[datetime]
    ended_at: Optional[datetime]

    class Config:
        from_attributes = True

class MessageSend(BaseModel):
    session_id: str
    message: str

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender: str
    content: str
    timestamp: Optional[datetime]

    class Config:
        from_attributes = True

class HospitalSearch(BaseModel):
    lat: float
    lng: float

class HospitalResponse(BaseModel):
    id: int
    name: str
    phone: Optional[str]
    address: Optional[str]
    region: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True

class EmailCheck(BaseModel):
    email: EmailStr

class ConversationEnd(BaseModel):
    session_id: str 
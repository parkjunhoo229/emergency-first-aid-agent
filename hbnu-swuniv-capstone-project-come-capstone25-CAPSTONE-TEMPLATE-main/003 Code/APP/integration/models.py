from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from datetime import datetime
from passlib.context import CryptContext
from typing import Optional, Dict, Any
import os
from config import config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base = declarative_base()

DATABASE_URL = config['development'].DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=300
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    phone = Column(String(11), nullable=False)
    gender = Column(String(10), nullable=False)
    birth_year = Column(Integer, nullable=False)
    prank_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    medical_info = relationship("MedicalInfo", back_populates="user", uselist=False, cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    prank_calls = relationship("PrankCallLog", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str):
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password = password_bytes[:72].decode('utf-8', errors='ignore')
        self.password_hash = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            password = password_bytes[:72].decode('utf-8', errors='ignore')
        return pwd_context.verify(password, self.password_hash)

    def to_dict(self, include_medical: bool = False) -> Dict[str, Any]:
        user_data = {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'gender': self.gender,
            'birth_year': self.birth_year,
            'prank_count': self.prank_count,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_medical and self.medical_info:
            user_data['medical_info'] = self.medical_info.to_dict()
            
        return user_data

    def __repr__(self):
        return f'<User {self.email}>'

class MedicalInfo(Base):
    __tablename__ = 'medical_info'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    blood_type = Column(String(10), nullable=False)
    base_diseases = Column(Text, default='')
    medications = Column(Text, default='')
    allergies = Column(Text, default='')
    surgery_history = Column(Text, default='')
    other_medical_info = Column(Text, default='')
    emergency_contact_name = Column(String(50), default='')
    emergency_contact_phone = Column(String(11), default='')
    emergency_contact_relation = Column(String(20), default='')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="medical_info")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'blood_type': self.blood_type,
            'base_diseases': self.base_diseases,
            'medications': self.medications,
            'allergies': self.allergies,
            'surgery_history': self.surgery_history,
            'other_medical_info': self.other_medical_info,
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_phone': self.emergency_contact_phone,
            'emergency_contact_relation': self.emergency_contact_relation,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<MedicalInfo for User {self.user_id}>'

class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_id = Column(String(50), nullable=False, unique=True)
    is_prank_call = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    agent_state = Column(Text, default='{}')
    
    user = relationship("User", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    prank_log = relationship("PrankCallLog", back_populates="conversation", uselist=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'is_prank_call': self.is_prank_call,
            'is_active': self.is_active,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None
        }

    def __repr__(self):
        return f'<Conversation {self.session_id}>'

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    sender = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'sender': self.sender,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

    def __repr__(self):
        return f'<ChatMessage {self.id} by {self.sender}>'

class PrankCallLog(Base):
    __tablename__ = 'prank_call_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="prank_calls")
    conversation = relationship("Conversation", back_populates="prank_log")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'conversation_id': self.conversation_id,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None
        }

    def __repr__(self):
        return f'<PrankCallLog {self.id}>'

class Hospital(Base):
    __tablename__ = 'hospitals'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    phone = Column(Text)
    address = Column(Text)
    region = Column(Text)
    lat = Column(Float)
    lng = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'address': self.address,
            'region': self.region,
            'lat': self.lat,
            'lng': self.lng,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Hospital {self.name}>' 
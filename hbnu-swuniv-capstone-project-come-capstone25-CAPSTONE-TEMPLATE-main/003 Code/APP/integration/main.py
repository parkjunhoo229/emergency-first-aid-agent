from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from contextlib import asynccontextmanager
import uvicorn
import os
import json
from datetime import datetime
import uuid
import requests
from openai import OpenAI
from dotenv import load_dotenv

from models import Base, engine, get_db, User, MedicalInfo, Hospital, Conversation, ChatMessage, PrankCallLog, AsyncSessionLocal
from schemas import *
from config import config
from utils import (
    is_valid_email, is_valid_phone, is_valid_birth_year, 
    is_valid_password, is_valid_name, is_valid_gender, is_valid_blood_type,
    validate_required_fields, create_error_response, create_success_response,
    sanitize_string, format_phone_number
)

from persona import ROLE_DISEASE_INFERENCE
from followup_utils import load_disease_json, get_disease_prompt_string
from analyze_prompt import build_one_agent_prompt
from parse_gpt_response import parse_gpt_response
from fallback import handle_fallback
from emergency_escalation_api import router as escalation_router
from ask_location_api import router as location_router
from first_aid_followup import router as followup_router
from first_aid_warning import router as warning_router
from agent9_integration import init_agent_state, process_agent_message

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

client_id = os.getenv('NAVER_MAPS_CLIENT_ID')
client_secret = os.getenv('NAVER_MAPS_CLIENT_SECRET')

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app_config = config['development']

app = FastAPI(
    title="MediCall API",
    description="의료 응급 상담 서비스 API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(escalation_router)
app.include_router(location_router)
app.include_router(followup_router)
app.include_router(warning_router)

disease_data = load_disease_json()
disease_text = get_disease_prompt_string(disease_data)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc.detail, exc.status_code)
    )

@app.post("/api/check-email")
async def check_email(email_data: EmailCheck, db: AsyncSession = Depends(get_db)):
    try:
        email = email_data.email.lower()
        
        if not is_valid_email(email):
            raise HTTPException(
                status_code=400,
                detail="올바른 이메일 형식을 입력해주세요."
            )
        
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        is_available = existing_user is None
        
        return create_success_response(
            '사용 가능한 이메일입니다.' if is_available else '이미 사용 중인 이메일입니다.',
            {'available': is_available}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'이메일 확인 중 오류가 발생했습니다: {str(e)}'
        )

@app.post("/api/register", status_code=201)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        name = sanitize_string(user_data.name, 50)
        email = user_data.email.lower()
        password = user_data.password
        phone = format_phone_number(user_data.phone)
        gender = sanitize_string(user_data.gender, 10)
        birth_year = user_data.birth_year
        blood_type = sanitize_string(user_data.blood_type, 10)
        
        name_valid, name_msg = is_valid_name(name)
        if not name_valid:
            raise HTTPException(status_code=400, detail=name_msg)
        
        if not is_valid_email(email):
            raise HTTPException(status_code=400, detail="올바른 이메일 형식을 입력해주세요.")
        
        password_valid, password_msg = is_valid_password(password)
        if not password_valid:
            raise HTTPException(status_code=400, detail=password_msg)
        
        if not is_valid_phone(phone):
            raise HTTPException(status_code=400, detail="올바른 전화번호 형식을 입력해주세요. (010으로 시작하는 11자리 숫자)")
        
        if not is_valid_gender(gender):
            raise HTTPException(status_code=400, detail="올바른 성별을 선택해주세요.")
        
        if not is_valid_birth_year(birth_year):
            raise HTTPException(status_code=400, detail="올바른 출생연도를 입력해주세요.")
        
        if not is_valid_blood_type(blood_type):
            raise HTTPException(status_code=400, detail="올바른 혈액형을 선택해주세요.")
        
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="이미 가입된 이메일입니다.")
        
        new_user = User(
            name=name,
            email=email,
            phone=phone,
            gender=gender,
            birth_year=birth_year
        )
        new_user.set_password(password)
        
        db.add(new_user)
        await db.flush()
        
        medical_info = MedicalInfo(
            user_id=new_user.id,
            blood_type=blood_type,
            base_diseases=sanitize_string(user_data.base_diseases, 1000),
            medications=sanitize_string(user_data.medications, 1000),
            allergies=sanitize_string(user_data.allergies, 1000),
            surgery_history=sanitize_string(user_data.surgery_history, 1000),
            other_medical_info=sanitize_string(user_data.other_medical_info, 1000),
            emergency_contact_name=sanitize_string(user_data.emergency_contact_name, 50),
            emergency_contact_phone=format_phone_number(user_data.emergency_contact_phone),
            emergency_contact_relation=sanitize_string(user_data.emergency_contact_relation, 20)
        )
        
        db.add(medical_info)
        await db.commit()
        await db.refresh(new_user)
        
        return create_success_response(
            '회원가입이 완료되었습니다.',
            {'user_id': new_user.id, 'user': new_user.to_dict()}
        )
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'회원가입 중 오류가 발생했습니다: {str(e)}'
        )

@app.post("/api/login")
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    try:
        email = login_data.email.lower()
        password = login_data.password
        
        if not email or not password:
            raise HTTPException(status_code=400, detail="이메일과 비밀번호를 모두 입력해주세요.")
        
        result = await db.execute(
            select(User).options(selectinload(User.medical_info))
            .where(and_(User.email == email, User.is_active == True))
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.check_password(password):
            raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
        
        return create_success_response(
            '로그인 성공',
            {'user': user.to_dict(include_medical=True)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'로그인 중 오류가 발생했습니다: {str(e)}'
        )

@app.get("/api/user/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(User).options(selectinload(User.medical_info))
            .where(and_(User.id == user_id, User.is_active == True))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        return create_success_response(
            '사용자 정보 조회 성공',
            {'user': user.to_dict(include_medical=True)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'사용자 정보 조회 중 오류가 발생했습니다: {str(e)}'
        )

@app.put("/api/user/{user_id}")
async def update_user(user_id: int, user_data: UserUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(User).where(and_(User.id == user_id, User.is_active == True))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        if user_data.name is not None:
            name = sanitize_string(user_data.name, 50)
            name_valid, name_msg = is_valid_name(name)
            if not name_valid:
                raise HTTPException(status_code=400, detail=name_msg)
            user.name = name
            
        if user_data.phone is not None:
            phone = format_phone_number(user_data.phone)
            if not is_valid_phone(phone):
                raise HTTPException(status_code=400, detail="올바른 전화번호 형식을 입력해주세요.")
            user.phone = phone
            
        if user_data.gender is not None:
            gender = sanitize_string(user_data.gender, 10)
            if not is_valid_gender(gender):
                raise HTTPException(status_code=400, detail="올바른 성별을 선택해주세요.")
            user.gender = gender
            
        if user_data.birth_year is not None:
            if not is_valid_birth_year(user_data.birth_year):
                raise HTTPException(status_code=400, detail="올바른 출생연도를 입력해주세요.")
            user.birth_year = user_data.birth_year
        
        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
        
        return create_success_response(
            '사용자 정보가 수정되었습니다.',
            {'user': user.to_dict()}
        )
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'사용자 정보 수정 중 오류가 발생했습니다: {str(e)}'
        )

@app.delete("/api/user/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(User).where(and_(User.id == user_id, User.is_active == True))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return create_success_response('사용자가 삭제되었습니다.')
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'사용자 삭제 중 오류가 발생했습니다: {str(e)}'
        )

@app.post("/api/hospitals/nearby")
async def get_nearby_hospitals(hospital_search: HospitalSearch, db: AsyncSession = Depends(get_db)):
    try:
        lat = hospital_search.lat
        lng = hospital_search.lng
        
        if not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail="올바른 위도 값을 입력해주세요. (-90 ~ 90)")
        if not (-180 <= lng <= 180):
            raise HTTPException(status_code=400, detail="올바른 경도 값을 입력해주세요. (-180 ~ 180)")
        
        region = await get_region_from_coordinates(lat, lng)
        
        result = await db.execute(select(Hospital).where(Hospital.region == region))
        hospitals = result.scalars().all()
        
        hospitals_data = [hospital.to_dict() for hospital in hospitals]
        
        return create_success_response(
            f'{region} 지역의 병원 목록을 조회했습니다.',
            {
                'region': region,
                'user_location': {'lat': lat, 'lng': lng},
                'hospitals': hospitals_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f'병원 조회 중 오류가 발생했습니다: {str(e)}'
        )

@app.post("/api/chat/start")
async def start_conversation(conversation_data: ConversationStart, db: AsyncSession = Depends(get_db)):
    try:
        user_id = conversation_data.user_id
        
        if not user_id:
            raise HTTPException(status_code=400, detail="사용자 ID가 필요합니다.")
        
        result = await db.execute(
            select(User).where(and_(User.id == user_id, User.is_active == True))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        existing_result = await db.execute(
            select(Conversation).where(and_(
                Conversation.user_id == user_id,
                Conversation.is_active == True
            ))
        )
        existing_conversation = existing_result.scalar_one_or_none()
        
        if existing_conversation:
            existing_conversation.is_active = False
            existing_conversation.ended_at = datetime.utcnow()
        
        session_id = f"conv_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        new_conversation = Conversation(
            user_id=user_id,
            session_id=session_id
        )
        
        db.add(new_conversation)
        await db.commit()
        await db.refresh(new_conversation)
        
        return create_success_response(
            '대화가 시작되었습니다.',
            {
                'session_id': session_id,
                'conversation_id': new_conversation.id,
                'initial_message': '안녕하세요. 응급상황 상담사입니다. 현재 어떤 상황인지 자세히 말씀해주세요.'
            }
        )
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'대화 시작 중 오류가 발생했습니다: {str(e)}'
        )

@app.post("/api/chat/send")
async def send_message(message_data: MessageSend, db: AsyncSession = Depends(get_db)):
    try:
        session_id = message_data.session_id
        user_message = message_data.message
        
        if not session_id:
            raise HTTPException(status_code=400, detail="세션 ID가 필요합니다.")
        
        result = await db.execute(
            select(Conversation).options(selectinload(Conversation.user).selectinload(User.medical_info))
            .where(and_(Conversation.session_id == session_id, Conversation.is_active == True))
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="활성화된 대화 세션을 찾을 수 없습니다.")
        
        try:
            agent_state = json.loads(conversation.agent_state) if conversation.agent_state else init_agent_state()
        except json.JSONDecodeError:
            agent_state = init_agent_state()
        
        default_state = init_agent_state()
        for key in default_state:
            if key not in agent_state:
                agent_state[key] = default_state[key]
        
        if user_message:
            user_chat = ChatMessage(
                conversation_id=conversation.id,
                sender='user',
                content=user_message.strip()
            )
            db.add(user_chat)
        
        updated_state, ai_response, is_prank = process_agent_message(agent_state, user_message or "")
        
        ai_chat = ChatMessage(
            conversation_id=conversation.id,
            sender='ai',
            content=ai_response
        )
        db.add(ai_chat)
        
        prank_detected_this_call = False
        if is_prank and not conversation.is_prank_call:
            conversation.is_prank_call = True
            prank_detected_this_call = True
            
            prank_log = PrankCallLog(
                user_id=conversation.user_id,
                conversation_id=conversation.id
            )
            db.add(prank_log)
            
            user = conversation.user
            user.prank_count += 1
        
        conversation.agent_state = json.dumps(updated_state, ensure_ascii=False)
        
        urgency_level = "high"
        if updated_state.get("emergency_level") == "긴급":
            urgency_level = "high"
        elif updated_state.get("emergency_level") == "응급":
            urgency_level = "medium"
        elif updated_state.get("emergency_level") == "비응급":
            urgency_level = "low"
        
        await db.commit()
        
        return create_success_response(
            'AI 응답이 생성되었습니다.',
            {
                'ai_response': ai_response,
                'is_prank': prank_detected_this_call,
                'urgency_level': urgency_level,
                'session_id': session_id,
                'agent_status': {
                    'confirmed_disease': updated_state.get('confirmed_disease'),
                    'emergency_level': updated_state.get('emergency_level'),
                    'report_sent': updated_state.get('report_sent', False),
                    'is_session_active': updated_state.get('is_session_active', True)
                }
            }
        )
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'메시지 처리 중 오류가 발생했습니다: {str(e)}'
        )

@app.post("/api/chat/end")
async def end_conversation(conversation_data: ConversationEnd, db: AsyncSession = Depends(get_db)):
    try:
        session_id = conversation_data.session_id
        
        if not session_id:
            raise HTTPException(status_code=400, detail="세션 ID가 필요합니다.")
        
        result = await db.execute(
            select(Conversation).where(and_(Conversation.session_id == session_id, Conversation.is_active == True))
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="활성화된 대화 세션을 찾을 수 없습니다.")
        
        conversation.is_active = False
        conversation.ended_at = datetime.utcnow()
        
        await db.commit()
        
        return create_success_response(
            '대화가 종료되었습니다.',
            {
                'session_id': session_id,
                'ended_at': conversation.ended_at.isoformat(),
                'is_prank_call': conversation.is_prank_call
            }
        )
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'대화 종료 중 오류가 발생했습니다: {str(e)}'
        )

async def generate_ai_response(conversation: Conversation, user_message: str) -> tuple[str, bool, str]:
    try:
        user = conversation.user
        medical_info = user.medical_info
        
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ChatMessage).where(ChatMessage.conversation_id == conversation.id)
                .order_by(ChatMessage.timestamp).limit(10)
            )
            messages = result.scalars().all()
        
        current_year = datetime.utcnow().year
        age = current_year - user.birth_year
        
        system_prompt = f"""
당신은 전문적인 응급상황 상담사입니다. 다음 정보를 바탕으로 응답해주세요.

사용자 정보:
- 이름: {user.name}
- 나이: {age}세
- 성별: {user.gender}
- 혈액형: {medical_info.blood_type if medical_info else '미등록'}
- 기저질환: {medical_info.base_diseases if medical_info and medical_info.base_diseases else '없음'}
- 복용약물: {medical_info.medications if medical_info and medical_info.medications else '없음'}
- 알레르기: {medical_info.allergies if medical_info and medical_info.allergies else '없음'}
- 과거 장난전화 횟수: {user.prank_count}회

응답 규칙:
1. 실제 응급상황이라면 적절한 응급처치 방법을 제공하세요
2. 필요하다면 추가 질문을 해도 괜찮습니다.
3. 장난전화 의심 시 경고하되, 실제 응급상황일 가능성도 고려하세요
4. 과거 장난전화 횟수가 3회 이상이면 더 엄격하게 판단하세요
5. 응답은 간단명료하게 30초 이내로 읽을 수 있게 작성하세요

JSON 형식으로만 응답하세요:
{{
    "response": "사용자에게 전달할 메시지 (한국어, 200자 이내)",
    "is_prank": true/false,
    "urgency_level": "high/medium/low"
}}
"""
        
        openai_messages = [{"role": "system", "content": system_prompt}]
        
        for msg in messages[-8:]:
            role = "user" if msg.sender == "user" else "assistant"
            openai_messages.append({
                "role": role,
                "content": msg.content
            })
        
        openai_messages.append({
            "role": "user", 
            "content": user_message
        })
        
        ai_response_json = await call_openai_api(openai_messages)
        
        return (
            ai_response_json.get('response', '죄송합니다. 현재 시스템에 문제가 있습니다. 119에 직접 신고해주세요.'),
            ai_response_json.get('is_prank', False),
            ai_response_json.get('urgency_level', 'medium')
        )
        
    except Exception as e:
        print(f"AI 응답 생성 중 오류: {e}")
        return (
            "죄송합니다. 현재 시스템에 문제가 있습니다. 119에 직접 신고해주세요.", 
            False, 
            'high'
        )

async def call_openai_api(messages: list) -> dict:
    try:            
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            temperature=0.3,
            max_tokens=300
        )
            
        try:
            import json
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {
                "response": response.choices[0].message.content,
                "is_prank": False,
                "urgency_level": "medium"
            }
    except Exception as e:
        print(f"OpenAI API 호출 중 오류: {e}")
        return {
            "response": "죄송합니다. 현재 시스템에 문제가 있습니다. 119에 직접 신고해주세요.",
            "is_prank": False,
            "urgency_level": "high"
        }

async def get_region_from_coordinates(lat: float, lng: float) -> str:
    global client_id, client_secret
    url = f"https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc?coords={lng}%2C{lat}&output=json&orders=legalcode"
    headers = {
        'X-NCP-APIGW-API-KEY-ID': client_id,
        'X-NCP-APIGW-API-KEY': client_secret
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(data)
        if data['results'][0]:
            region = data['results'][0]['region']['area1']['name']
            print(region)
            return region
        else:
            return None
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True
    )
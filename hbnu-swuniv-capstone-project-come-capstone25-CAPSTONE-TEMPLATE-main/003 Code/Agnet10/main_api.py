from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import openai, os, requests
from typing import Any, Dict

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:8000")

# 내부 모듈
from persona import ROLE_DISEASE_INFERENCE
from followup_utils import load_disease_json, get_disease_prompt_string
from analyze_prompt import build_one_agent_prompt
from parse_gpt_response import parse_gpt_response
from fallback import handle_fallback

# 외부 API 라우터
from first_aid_followup import router as followup_router
from ask_location_api import router as location_router
from emergency_escalation_api import router as escalation_router
from first_aid_warning import router as warning_router


# -------------------------------
# FastAPI 초기 설정
# -------------------------------
app = FastAPI(title="응급처치 AI 에이전트 API")
app.include_router(followup_router)
app.include_router(location_router)
app.include_router(escalation_router)
app.include_router(warning_router)

disease_data = load_disease_json()
disease_text = get_disease_prompt_string(disease_data)


# -------------------------------
# 요청/응답 모델 정의
# -------------------------------
# 에이전트가 사용자 요청을 받을 때 사용하는 입력 데이터 구조
class AgentRequest(BaseModel):
    chat_history: list = Field(default_factory=list)       # 병명 추론
    escalation_history: list = Field(default_factory=list) # 응급도 판단
    report_history: list = Field(default_factory=list)     # 신고 여부 판단
    location_history: list = Field(default_factory=list)   # 위치 수집
    first_history: list = Field(default_factory=list)      # 응급처치 안내
    
    confirmed_symptoms: list = Field(default_factory=list)  # 지금까지 GPT가 추출한 증상 키워드 누적 리스트
    last_candidates: list = Field(default_factory=list)  # 병명 후보 리스트 (아직 확정되지 않은 질병들)
    confirmed_disease: str | None = None  # 최종 확정된 병명 (예: "뇌졸중")
    emergency_level: str | None = None  # 현재 병명의 응급도 ("긴급" / "응급" / "비응급")
    turn_count: int = 0  # 병명 추론에서 GPT가 follow-up 질문을 생성한 횟수
    escalation_done: bool = False   # 응급도 판단 완료 여부 (True면 응급도 단계 스킵)
    user_consented_report: bool | None = None  # 신고 여부 (True=신고 동의, False=거부, None=아직 물어보지 않음)
    final_location_text: str | None = None  # 최종 확정된 위치 텍스트 (예: "한밭대학교 N4동 5층 강의실")
    location_confirmed: bool | None = None
    report_sent: bool = False   # 119 신고 전송 완료 여부 플래그
    first_aid_warning_shown: bool = False    # 응급처치 주의사항 출력 여부 (True면 재출력 생략)
    is_session_active: bool = True  # 세션 유지 여부 (False가 되면 더 이상 Agent 호출 불필요)
    report_message: dict | None = None 
    echo: bool = False 
    
    # 백엔드 → 에이전트로만 보내도 되는 항목
    user_input: str  # 사용자의 최신 발화 (자연어 입력)
    

# 에이전트가 백엔드에게 반환하는 응답 구조
class AgentResponse(BaseModel):
    # 반드시 주고받아야 할 핵심 항목들
    chat_history: list = Field(default_factory=list)       # 병명 추론
    escalation_history: list = Field(default_factory=list) # 응급도 판단
    report_history: list = Field(default_factory=list)     # 신고 여부 판단
    location_history: list = Field(default_factory=list)   # 위치 수집
    first_history: list = Field(default_factory=list)      # 응급처치 안내
    
    confirmed_symptoms: list[str] = Field(default_factory=list)  # 수집된 증상 리스트    
    last_candidates: list[str] = Field(default_factory=list)  # 남은 병명 후보 리스트
    confirmed_disease: str | None = None  # 확정된 병명 (병명 추론 완료 시)
    emergency_level: str | None = None  # 현재 병명의 응급도 ("긴급" / "응급" / "비응급")
    turn_count: int = 0  # 병명 추론에서 GPT가 follow-up 질문을 생성한 횟수
    escalation_done: bool = False   # 응급도 판단 완료 여부 (True면 응급도 단계 스킵)
    user_consented_report: bool | None = None  # 신고 여부 (True=신고 동의, False=거부, None=아직 물어보지 않음)
    final_location_text: str | None = None  # 최종 확정된 위치 텍스트 (예: "한밭대학교 N4동 5층 강의실")
    location_confirmed: bool | None = None
    report_sent: bool = False       # 119 신고 전송 완료 여부 플래그
    first_aid_warning_shown: bool = False    # 응급처치 주의사항 출력 여부 (True면 재출력 생략)    
    is_session_active: bool = True  # 세션 유지 여부 (False가 되면 더 이상 Agent 호출 불필요)
    report_message: dict | None = None  # 119 신고 메시지 (예: "환자는 뇌졸중 의심, 위치는 한밭대 N4동 5층")
    echo: bool = False 
        
    # 에이전트 → 백엔드로만 보내도 되는 항목
    status: str  # 현재 처리 상태 ("진행중", "확정", "fallback", "error" 등)
    message: str  # 내부 로그/상태 설명 (프론트에는 노출되지 않음, 디버깅용, 백엔드도 사용X)
    next_question: str | None = None  # 사용자에게 실제로 보여줄 다음 질문 (or 안내 문장)
    
# -------------------------------
# 공통 상태 패커: 항상 전체 상태를 담아 응답
# -------------------------------
def pack_state(req: AgentRequest, **overrides) -> AgentResponse:
    base = dict(
        # 반드시 주고받는 핵심 항목들 (모두 되돌려보냄)
        chat_history=req.chat_history,
        escalation_history=req.escalation_history,
        report_history=req.report_history,
        location_history=req.location_history,
        first_history=req.first_history,

        confirmed_symptoms=req.confirmed_symptoms,
        last_candidates=req.last_candidates,
        confirmed_disease=req.confirmed_disease,
        emergency_level=req.emergency_level,
        turn_count=req.turn_count,
        escalation_done=req.escalation_done,
        user_consented_report=req.user_consented_report,
        final_location_text=req.final_location_text,
        location_confirmed=req.location_confirmed,
        report_sent=req.report_sent,
        first_aid_warning_shown=req.first_aid_warning_shown,
        is_session_active=req.is_session_active,
        report_message=req.report_message,
        echo=False,

        # 에이전트 → 백엔드 전용 기본값
        user_input=None,
        status="진행중",
        message="",
        next_question=None        
    )
    base.update(overrides)
    return AgentResponse(**base)

# ============================================================
# 사용자 응답 정규화 유틸
# ============================================================
def normalize_consent(text: str) -> bool | None:
    if not text:
        return None

    text = text.strip().lower().replace(" ", "")
    yes_words = [
        "예", "네", "응", "그래", "좋아요", "좋아", "부탁해요", "신고해주세요",
        "신고해줘", "신고", "해줘", "해주세요", "도와줘", "도와주세요"
    ]
    no_words = [
        "아니", "아니요", "싫어요", "안돼", "안돼요", "필요없어요",
        "안해", "하지마", "신고안해", "신고하지마", "괜찮아"
    ]

    if any(w in text for w in yes_words):
        return True
    elif any(w in text for w in no_words):
        return False
    return None

# ============================================================
# 119 신고
# ============================================================
def send_emergency_report(req: AgentRequest) -> AgentResponse:

    # 1. 전송할 데이터 구성
    payload1 = {
        "disease": req.confirmed_disease,   # 병명
        "symptoms": req.confirmed_symptoms, # 증상
        "emergency_level": req.emergency_level, # 응급도
        "location": req.final_location_text # 상세위치
    }    
            
    # 백엔드로 전송
    try:        
        req.report_sent = True  # 신고 완료 마크
        req.report_message = payload1
        
        if req.location_confirmed is True:
            ack="위치가 확인되어 119에 신고를 하였습니다.\n"
        elif req.location_confirmed is False:
            ack="위치 파악이 힘듭니다. 구급대원이 추후 전화드릴테니 핸드폰을 주위에 두세요.\n"
        else:
            # 혹시 None이면 보수적으로 '신고는 완료' 안내
            ack = "119 신고를 완료했습니다. "

        q= ack + "지금부터 응급처치를 안내해 드리겠습니다."
        req.location_history.append({"role": "assistant", "content": q})
        
        return pack_state(req,
            status="확정",
            message="신고 완료",
            report_message=payload1,
            report_sent=True,
            next_question=q,
            echo=True
        )
    except Exception as e:
        return pack_state(req,
            status="error",
            message=f"신고 요청 중 예외 발생: {e}",
            next_question="119 신고 중 오류가 발생했습니다."
        )

# ============================================================
# 1. 병명 추론 단계
# ============================================================
def disease_inference_step(req: AgentRequest) -> AgentResponse:
    MAX_TURNS = 8
    
    chat_history = req.chat_history
    chat_history.append({"role": "user", "content": req.user_input})

    prompt = build_one_agent_prompt(chat_history, disease_text)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": ROLE_DISEASE_INFERENCE},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            timeout=10
        )
        reply = resp.choices[0].message.content.strip()
        parsed = parse_gpt_response(reply)
    except Exception as e:
        return pack_state(req,status="error", message=f"GPT 호출 실패: {e}")

    # 증상 누적
    for s in parsed.get("symptoms", []):
        if s not in req.confirmed_symptoms:
            req.confirmed_symptoms.append(s)

    req.last_candidates = parsed.get("candidates", req.last_candidates)

    if parsed.get("status") == "확정":
        req.confirmed_disease = parsed.get("confirmed_disease")
        req.turn_count = 0
        req.emergency_level = disease_data.get(
            req.confirmed_disease, {}
            ).get("emergency_level", "비응급")
        
        req.chat_history.append({
        "role": "assistant",
        "content": f"병명이 '{req.confirmed_disease}'로 확정되었습니다. (기본 응급도: {req.emergency_level})"
        })
        
        return escalation_step(req)

    elif parsed.get("next_question"):
        req.turn_count += 1
        
        # 턴 수 초과 시 fallback 처리
        if req.turn_count >= MAX_TURNS:
            fb_text = handle_fallback(req.last_candidates, disease_data)
            req.chat_history.append({"role": "assistant", "content": fb_text})
            
            req.is_session_active = False            
            return pack_state(req,
                status="fallback",
                message=f"질문 {MAX_TURNS}회 초과 → fallback 실행",
                next_question=fb_text
            )
            
        req.chat_history.append({"role": "assistant", "content": parsed["next_question"]})
        return pack_state(req,
            status="진행중",
            message="질문 진행",
            next_question=parsed["next_question"],
            confirmed_symptoms=req.confirmed_symptoms,  # 수집된 증상
            last_candidates=req.last_candidates
        )

    else:
        fb_text = handle_fallback(req.last_candidates, disease_data)
        req.chat_history.append({"role": "assistant", "content": fb_text})
        
        req.is_session_active = False
        
        return pack_state(req,
            status="fallback",
            message=f"질문 가능한 증상이 없습니다. (fallback 실행)",
            next_question=fb_text,
            confirmed_symptoms=req.confirmed_symptoms,  # 수집된 증상
            last_candidates=req.last_candidates,  # 병명 후보 전달
        )


# ============================================================
# 2. 응급도 확정 단계
# ============================================================
def escalation_step(req: AgentRequest) -> AgentResponse:
    
    asked = [m for m in req.escalation_history if m["role"] == "assistant"]
    if asked:
        req.escalation_history.append({"role": "user", "content": req.user_input})


    base_level = req.emergency_level or "비응급"
    payload = {
        "disease": req.confirmed_disease,
        "base_level": base_level,  # 하드코딩 대신 현재 기본 응급도 사용
        "escalation_history": req.escalation_history,
        "user_input": req.user_input,
    }

    try:
        resp = requests.post(
            f"{SERVER_URL}/emergency_escalation",
            json=payload,
            timeout=10
        )
        data = resp.json()
        
        if data.get("status") == "확정":
            final_level = data.get("final_emergency_level") or base_level
            req.emergency_level = final_level
            req.escalation_done = True  # 확정 플래그 세팅
            
            return report_consent_step(req)


        # 질문이 온 경우 (assistant→user 순서 유지)
        q = data.get("question")
        if q:
            req.escalation_history.append({"role": "assistant", "content": q})
            return pack_state(req,
                status="진행중",
                message="응급도 판단을 위해 추가 질문이 필요합니다.",
                next_question=q
            )

    except Exception as e:
        return pack_state(req,status="error", message=f"응급도 API 호출 실패: {e}")



# ============================================================
# 3. 신고 여부 확인 단계
# ============================================================
def report_consent_step(req: AgentRequest) -> AgentResponse:
    if req.emergency_level == "긴급":
        req.user_consented_report = True
        return location_step(req)
        

    elif req.emergency_level == "응급":
        # 응급일시 반드시 질문
        asked = [m["content"] for m in req.report_history if m["role"] == "assistant"]
        if not any("신고" in q for q in asked):
            q = (
                f"현재 '{req.confirmed_disease}'로 의심되며, 응급 상황입니다.\n"
                "119에 신고를 도와드릴까요? (예/아니오)"
            )
            req.report_history.append({"role": "assistant", "content": q})
            
            return pack_state(req,
                status="진행중",
                next_question=q,
                message="응급 상황 → 신고 여부 질문 먼저"
            )
        # 여전히 판단 불가 시
        reprompt = "다시 한번 말씀해주세요. (예/아니오)"
        req.report_history.append({"role": "assistant", "content": reprompt})
        return pack_state(req,
            status="진행중",
            next_question=reprompt,
            message="응급 상황이지만 신고 여부 미확인"
        )

    else:
        req.user_consented_report = False
        return first_aid_step(req)

# ============================================================
# 4. 위치 파악 단계
# ============================================================
def location_step(req: AgentRequest) -> AgentResponse:
    if req.location_history:
        req.location_history.append({"role": "user", "content": req.user_input})
    
    if not req.location_history:
        
        first_q = "환자의 정확한 위치를 알려주세요. 예: OO건물 3층, OO공원 앞 사거리 등"
        req.location_history.append({"role": "assistant", "content": first_q})
        return pack_state(req,
            status="진행중",
            next_question=first_q,
            message="위치 히스토리가 없어 최초 질문을 던집니다."
        )

    try:
        payload = {
            "location_history": req.location_history,
            "user_input": req.user_input
        }
        resp = requests.post(f"{SERVER_URL}/location", json=payload, timeout=10)
        data = resp.json()

        if data.get("followup_question"):
            req.location_history.append({"role": "assistant", "content": data["followup_question"]})
            return pack_state(req,
                status="진행중",
                next_question=data["followup_question"],
                message="위치 보완 질문"
            )

        elif data.get("final_location_text"):
            final_loc = data["final_location_text"]
            
            asked = [
                m for m in req.location_history
                if m.get("role") == "assistant"
                and m.get("type") == "confirm_location"
                and m.get("candidate") == final_loc
            ]

            # 아직 위치 확인 질문을 안 했으면 → 질문 생성
            if not asked:
                confirm_question = f"지금 말씀하신 위치가 '{final_loc}' 맞나요? (예/아니오)"
                req.location_history.append({
                    "role": "assistant",
                    "content": confirm_question,
                    "type": "confirm_location",
                    "candidate": final_loc
                })
                return pack_state(req,
                    status="진행중",
                    next_question=confirm_question,
                    message="위치 확인 요청"
                )
            
            normalized = normalize_consent(req.user_input)
            if normalized is True:
                # 예 → 위치 확정 완료
                req.final_location_text = final_loc
                req.location_confirmed = normalized
                
                return send_emergency_report(req)
            
            elif normalized is False:
                # 아니요 → 위치 확정 실패
                false_q="위치 파악 실패\n 위치 파악 시도 내용: " + final_loc
                req.final_location_text = false_q
                req.location_confirmed = normalized
                             
                return send_emergency_report(req)
            
            else:
                # 모호한 답변 → 다시 질문
                reask = f"다시 한 번 말씀해 주세요.\n'{final_loc}'이(가) 맞습니까? (예/아니오)"
                req.location_history.append({"role": "assistant", "content": reask})
                return pack_state(req,
                    status="진행중",
                    next_question=reask,
                    message="모호한 응답 → 다시 확인 요청"
                )
            
        else:
            return pack_state(req,status="error", message="위치 응답 형식 오류")

    except Exception as e:
        return pack_state(req,status="error", message=f"위치 API 실패: {e}")


# ============================================================
# 5. 응급처치 안내 단계 (리팩토링 버전)
# ============================================================
def first_aid_step(req: AgentRequest) -> AgentResponse:
    disease = req.confirmed_disease
    if not disease:
        return pack_state(req,
            status="error",
            message="응급처치 단계 진입 실패: 확정된 병명이 없습니다."
        )

    # 이미 주의사항을 보여줬다면 → 바로 follow-up
    if req.first_aid_warning_shown:
        return _run_first_aid_followup(req)

                
    # 1. 주의사항 먼저 불러오기
    try:
        warn_resp = requests.get(
            f"{SERVER_URL}/first_aid_warning?disease_name={disease}", 
            timeout=10
        )
        warn_data = warn_resp.json()
        warning_text = warn_data.get("warning_text")
        
    except Exception:
        warning_text = None  # 실패해도 진행
        
    if warning_text:
        req.first_aid_warning_shown = True
        warn_q= (f"지금부터 응급처치 주의사항을 안내하겠습니다. 반드시 지켜주세요.\n"
                f"[주의사항]\n{warning_text}\n\n"
                f"이제 응급 처치 안내를 시작하겠습니다.")
        req.location_history.append({"role": "assistant", "content": warn_q})
        
        return pack_state(req,
            status="진행중",
            next_question=warn_q,
            message="응급처치 주의사항 안내",
            echo=True
        )
    
    # 주의사항이 없거나 실패 → 즉시 follow-up
    req.first_aid_warning_shown = True
    return _run_first_aid_followup(req)
def _run_first_aid_followup(req: AgentRequest) -> AgentResponse:
    try:
        # 1. 응급처치 첫 진입이라면 (GPT의 첫 질문이 아직 없음)
        if not req.first_history:
            payload = {
                "disease_name": req.confirmed_disease,
                "emergency_level": req.emergency_level,
                "answer_history": [],
                "symptoms": req.confirmed_symptoms
            }
            resp = requests.post(
                f"{SERVER_URL}/first_aid_followup", json=payload, timeout=10
            )
            data = resp.json()

            if data["status"] == "진행중":
                question = data["question"]
                req.first_history.append({"role": "assistant", "content": question})
                return pack_state(req,
                    status="진행중",
                    next_question=question,
                    message="응급처치 첫 질문 생성"
                )

            elif data["status"] == "확정":
                matched_text = data["matched_text"]
                req.first_history.append({"role": "assistant", "content": matched_text})
                return pack_state(req,
                    status="확정",
                    message="분기 없음 → 즉시 응급처치 안내 완료",
                    next_question=matched_text
                )

            else:
                return pack_state(req,status="error", message="응급처치 첫 질문 생성 실패")

        # 2. 이미 follow-up 중이라면 (GPT가 이전 턴에서 질문 → 유저가 대답)
        else:
            req.first_history.append({"role": "user", "content": req.user_input})

            payload = {
                "disease_name": req.confirmed_disease,
                "emergency_level": req.emergency_level,
                "answer_history": req.first_history,
                "symptoms": req.confirmed_symptoms
            }
            resp = requests.post(
                f"{SERVER_URL}/first_aid_followup", 
                json=payload, 
                timeout=10
            )
            data = resp.json()

            if data["status"] == "진행중":
                question = data["question"]
                req.first_history.append({"role": "assistant", "content": question})
                return pack_state(req,
                    status="진행중",
                    next_question=question,
                    message="응급처치 follow-up 질문 중"
                )

            elif data["status"] == "확정":
                matched_text = data["matched_text"]
                req.first_history.append({"role": "assistant", "content": matched_text})
                req.is_session_active = False
                return pack_state(req,
                    status="확정",
                    message="응급처치 안내 완료",
                    next_question=matched_text
                )

            else:
                return pack_state(req,status="error", message="응급처치 API 응답 오류")

    except Exception as e:
        return pack_state(req,status="error", message=f"응급처치 follow-up 실패: {e}")
 





# ============================================================
# 메인 플로우 컨트롤
# ============================================================
@app.post("/agent", response_model=AgentResponse)
def run_agent(req: AgentRequest = Body(...)):
    if not req.is_session_active:
        return pack_state(req,
            status="error",
            message="세션이 이미 종료되었습니다.",
            next_question="이전 대화가 종료되었습니다. 뒤로 가기를 눌러주세요."
        )
        
    # 0. 최초 질문
    if not req.chat_history:
        first_q = "환자의 상태를 말씀해주세요. 어떤 증상이 있나요?"
        req.chat_history.append({"role": "assistant", "content": first_q})
        return pack_state(req,
            status="진행중",
            message="초기 질문",
            next_question=first_q
        )    

    user_text = (req.user_input or "").strip()
    
    # 0-1. 사용자 입력이 비어있을 때 (공백 또는 엔터)
    if not user_text and not req.echo:
        warn_q  = "입력이 감지되지 않았습니다. 다시 한 번 말씀해주세요."
        if not req.chat_history or req.chat_history[-1].get("content") != warn_q:
            req.chat_history.append({"role": "assistant", "content": warn_q})
        return pack_state(req,
            status="진행중",
            message="빈 입력 감지 → 재질문",
            next_question=warn_q
        )

    req.user_input = user_text

    # 1. 병명 확정
    if not req.confirmed_disease:
        req.turn_count = 0
        return disease_inference_step(req)

    # 2. 응급도 확정
    if not req.escalation_done:
        return escalation_step(req)

    # 3. 신고 여부 판단
    if req.user_consented_report is None:
        # (1) 신고 히스토리에 메세지가 저장되있다면
        if req.user_input and req.report_history:
            last_msg = req.report_history[-1]
            if last_msg["role"] == "assistant" and "신고" in last_msg["content"]:
                req.report_history.append({"role": "user", "content": req.user_input})
                normalized = normalize_consent(req.user_input)
                if normalized is not None:
                    req.user_consented_report = normalized

        # (2) 신고 여부 미확정 상태
        if req.user_consented_report is None:
            res = report_consent_step(req)
            return res

    if req.user_consented_report is True:
        # 4-1. 상세 위치 확보
        if not req.final_location_text:
            return location_step(req)

        # 4-2. 위치 확보 완료 → 아직 미전송이면 신고
        if not req.report_sent:
            return send_emergency_report(req)

        # 4-3. 신고 이미 완료 → 응급처치 진행
        return first_aid_step(req)

    # 5. 신고에 동의하지 않은 경우(또는 비응급 등) → 바로 응급처치
    return first_aid_step(req)
import json
import os
from openai import OpenAI
from persona import ROLE_DISEASE_INFERENCE
from followup_utils import load_disease_json, get_disease_prompt_string
from analyze_prompt import build_one_agent_prompt
from parse_gpt_response import parse_gpt_response
from fallback import handle_fallback
from emergency_escalation_api import run_emergency_escalation_core
from ask_location_api import run_location_core
from first_aid_warning import get_warning_text_core
from first_aid_followup import run_first_aid_core

import requests
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
EMERGENCY_SERVER_URL = os.getenv("EMERGENCY_SERVER_URL", "http://127.0.0.1:6000")

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

disease_data = load_disease_json()
disease_text = get_disease_prompt_string(disease_data)


def normalize_consent_with_history(history: list[dict], user_input: str | None = None) -> bool | None:
    """
    대화 히스토리( assistant의 가장 최근 질문 + user의 가장 최근 답변)를 보고
    user의 가장 최근 답변이 '예/아니요/모름'인지 판단한다.

    True  -> 예
    False -> 아니요
    None  -> 모름/판단불가
    """

    if not history and not user_input:
        return None

    # 최근 user / assistant 메시지 하나씩 찾기
    last_user = None
    last_assistant = None

    # history 가장 뒤에서부터 거꾸로 탐색
    for m in reversed(history):
        role = m.get("role")
        if role == "user" and last_user is None:
            last_user = m
        elif role == "assistant" and last_assistant is None:
            last_assistant = m
        if last_user and last_assistant:
            break

    # user_input 파라미터가 들어온 경우, 그걸 최신 user 발화로 우선 사용
    user_text = (user_input if user_input is not None else (last_user.get("content", "") if last_user else "")).strip()
    question_text = last_assistant.get("content", "") if last_assistant else ""

    if not user_text:
        return None

    prompt = f"""
다음은 시스템(assistant)의 질문과 사용자(user)의 가장 최근 대답이다.

assistant(질문): "{question_text}"
user(대답): "{user_text}"

사용자의 대답이 의미하는 바를 다음 중 하나로 분류하라:

- "예"     → 질문에 대한 긍정 / 수락 / 허용 / 동의 / 신고 요청
- "아니요" → 질문에 대한 부정 / 거절 / 반대 / 신고 거부
- "모름"   → 예/아니오로 판단하기 애매하거나, 질문과 직접적인 예/아니오 관계가 아닌 경우

출력은 반드시 아래 세 단어 중 하나만!
예
아니요
모름
""".strip()

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,
            messages=[
                {"role": "system", "content": "너는 질문-답 세트를 보고 예/아니요/모름을 판단하는 AI이다."},
                {"role": "user", "content": prompt},
            ],
            timeout=20,
        )
        answer = resp.choices[0].message.content.strip()

        if answer == "예":
            return True
        elif answer == "아니요":
            return False
        # "모름"이면 아래 fallback
    except Exception:
        # GPT 실패 시, 마지막 user 발화만으로라도 판단 시도
        pass

    # ----------------------------
    # fallback 키워드 방식
    # ----------------------------
    norm = user_text.replace(" ", "").lower()

    YES = ["예","네","응","그래","맞아","좋아","좋아요","신고해줘","신고해주세요","도와줘","웅","응응","녜","냬","내"]
    NO = ["아니", "아니요","아니오","안돼","싫어","필요없어","틀려","제가아니에요","아닌데","노"]

    for k in YES:
        token = k.replace(" ", "").lower()
        if token and token in norm:
            return True

    for k in NO:
        token = k.replace(" ", "").lower()
        if token and token in norm:
            return False

    return None


def init_agent_state():
    return {
        "patient_checked": False,
        "is_patient_self": None,
        "chat_history": [],
        "escalation_history": [],
        "report_history": [],
        "location_history": [],
        "first_history": [],
        "confirmed_symptoms": [],
        "last_candidates": [],
        "confirmed_disease": None,
        "emergency_level": None,
        "turn_count": 0,
        "escalation_done": False,
        "user_consented_report": None,
        "final_location_text": None,
        "location_confirmed": None,
        "report_sent": False,
        "first_aid_warning_shown": False,
        "first_aid_waiting_for_answer": False,  

        "is_session_active": True,
        "report_message": None,
        
        "user_profile": None,      # 마이페이지 정보
        "gps_location": None,      # 앱에서 받은 GPS
        
        "first_aid_started": False,
    }


def disease_inference_step(state: dict, user_input: str) -> tuple[dict, str]:
    MAX_TURNS = 8
    
    state["chat_history"].append({"role": "user", "content": user_input})
    
    prompt = build_one_agent_prompt(state["chat_history"], disease_text)
    
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": ROLE_DISEASE_INFERENCE},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            timeout=20
        )
        reply = resp.choices[0].message.content.strip()
        parsed = parse_gpt_response(reply)
    except Exception as e:
        return state, f"오류가 발생했습니다: {str(e)}"
    
    for s in parsed.get("symptoms", []):
        if "confirmed_symptoms" not in state:
            state["confirmed_symptoms"] = []
        if s not in state["confirmed_symptoms"]:
            state["confirmed_symptoms"].append(s)
    
    state["last_candidates"] = parsed.get("candidates", state["last_candidates"])
    
    if parsed.get("status") == "확정":
        state["confirmed_disease"] = parsed.get("confirmed_disease")
        state["turn_count"] = 0
        state["emergency_level"] = disease_data.get(
            state["confirmed_disease"], {}
        ).get("emergency_level", "비응급")
        
        state["chat_history"].append({
            "role": "assistant",
            "content": f"병명이 '{state['confirmed_disease']}'로 확정되었습니다. (기본 응급도: {state['emergency_level']})"
        })
        
        return escalation_step(state, "")
    
    elif parsed.get("next_question"):
        state["turn_count"] += 1
        
        if state["turn_count"] >= MAX_TURNS:
            fb_text = handle_fallback(state["last_candidates"], disease_data)
            state["chat_history"].append({"role": "assistant", "content": fb_text})
            state["is_session_active"] = False
            return state, fb_text
        
        state["chat_history"].append({"role": "assistant", "content": parsed["next_question"]})
        return state, parsed["next_question"]
    
    else:
        fb_text = handle_fallback(state["last_candidates"], disease_data)
        state["chat_history"].append({"role": "assistant", "content": fb_text})
        state["is_session_active"] = False
        return state, fb_text


def escalation_step(state: dict, user_input: str) -> tuple[dict, str]:

    base_level = state["emergency_level"] or "비응급"

    try:
        data = run_emergency_escalation_core(
            disease=state["confirmed_disease"],
            base_level=base_level,
            escalation_history=state["escalation_history"],
            user_input=user_input if user_input else None,
        )
        
        status = data.get("status")
        question = data.get("question")
        final_level = data.get("final_emergency_level")
        
        if status == "확정":
            state["emergency_level"] = final_level or base_level
            state["escalation_done"] = True
            return report_consent_step(state, "")
            
        if question:
            state["escalation_history"].append({"role": "assistant", "content": question})
            return state, question

    except Exception as e:
        return state, f"응급도 판단 중 오류가 발생했습니다: {str(e)}"

    # 위 조건에 안 걸린 이상은 비정상 상황
    return state, "응급도 판단 중 오류가 발생했습니다."

def report_consent_step(state: dict, user_input: str) -> tuple[dict, str]:
    if state["emergency_level"] == "긴급":
        state["user_consented_report"] = True
        return location_step(state, "")

    elif state["emergency_level"] == "응급":
        asked = [m["content"] for m in state["report_history"] if m["role"] == "assistant"]
        if not any("신고" in q for q in asked):
            q = (
                f"현재 '{state['confirmed_disease']}'로 의심되며, 응급 상황입니다.\n"
                "119에 신고를 도와드릴까요?"
            )
            state["report_history"].append({"role": "assistant", "content": q})
            return state, q
        
        reprompt = "다시 한번 말씀해주세요. (예/아니오)"
        state["report_history"].append({"role": "assistant", "content": reprompt})
        return state, reprompt
    
    else:
        state["user_consented_report"] = False
        return first_aid_step(state, "")


def location_step(state: dict, user_input: str) -> tuple[dict, str]:
    if state["location_history"] and user_input:
        state["location_history"].append({"role": "user", "content": user_input})
    
    if not state["location_history"]:
        first_q = "환자의 정확한 위치를 알려주세요. 예: OO건물 3층, OO공원 앞 사거리 등"
        if state["emergency_level"] == "긴급":
            first_q = (
                f"현재 '{state['confirmed_disease']}'로 의심되며, 긴급 상황입니다.\n"
                "환자의 정확한 위치를 알려주세요. 예: OO건물 3층, OO공원 앞 사거리 등"
            )
        state["location_history"].append({"role": "assistant", "content": first_q})
        return state, first_q
    
    try:
        # HTTP 호출 제거 → 내부 core 함수 직접 호출
        data = run_location_core(
            location_history=state["location_history"],
            user_input=user_input or ""
        )
        
        # 1) 추가 질문이 필요한 경우
        if data.get("status") == "진행중" and data.get("followup_question"):
            follow_q = data["followup_question"]
            state["location_history"].append({"role": "assistant", "content": follow_q})
            return state, follow_q
        
        # 1) 위치 파악 실패 fallback 처리 먼저
        if data.get("status") == "확정" and data.get("final_location_text"):
            final_loc = data["final_location_text"]

            # 실패 메시지인 경우: 확인 질문 생략하고 바로 신고
            if "위치 파악이 어려워 현장 전화 연결이 필요합니다." in final_loc:
                state["final_location_text"] = final_loc
                state["location_confirmed"] = False
                return send_emergency_report(state)

            # 2) 여기부터는 "정상 위치 확정" 케이스만 처리
            asked = [
                m for m in state["location_history"]
                if m.get("role") == "assistant"
                and m.get("type") == "confirm_location"
                and m.get("candidate") == final_loc
            ]
            
            if not asked:
                confirm_question = f"지금 말씀하신 위치가 '{final_loc}' 맞나요? (예/아니오)"
                state["location_history"].append({
                    "role": "assistant",
                    "content": confirm_question,
                    "type": "confirm_location",
                    "candidate": final_loc
                })
                return state, confirm_question
            
            # 이미 확인 질문이 나간 상태에서, 지금 user_input은 그에 대한 답변
            decision = normalize_consent_with_history(state["location_history"], user_input)
            if decision is True:
                state["final_location_text"] = final_loc
                state["location_confirmed"] = True
                return send_emergency_report(state)
            elif decision is False:
                false_q = "위치 파악 실패\n 위치 파악 시도 내용: " + final_loc
                state["final_location_text"] = false_q
                state["location_confirmed"] = False
                return send_emergency_report(state)
            else:
                reask = f"다시 한 번 말씀해 주세요.\n'{final_loc}'이(가) 맞습니까?"
                state["location_history"].append({"role": "assistant", "content": reask})
                return state, reask
        
        # 여기까지 오면 뭔가 이상한 케이스
        return state, "위치 파악 중 오류가 발생했습니다."
            
    except Exception as e:
        return state, f"위치 파악 중 오류가 발생했습니다: {str(e)}"


def send_emergency_report(state: dict) -> tuple[dict, str]:
    payload = {
        "disease": state["confirmed_disease"],
        "symptoms": state.get("confirmed_symptoms", []),
        "emergency_level": state["emergency_level"],
        "location": state["final_location_text"]
    }
    
    # 환자 정보
    if state.get("is_patient_self") and state.get("user_profile"):
        payload["patient_info"] = state["user_profile"]
    else:
        payload["patient_info"] = None
    
    # GPS 정보
    if state.get("gps_location") is not None:
        payload["gps_location"] = state["gps_location"]
    
    # 119 서버로 실제 신고 전송
    try:
        resp = requests.post(
            f"{EMERGENCY_SERVER_URL}/report",
            json=payload,
            timeout=20,
        )
        print("[119 서버 응답]", resp.status_code, resp.text)
    except Exception as e:
        print(f"[119 서버 전송 실패] {e}")
    
    state["report_sent"] = True
    state["report_message"] = payload

    # -----------------------------
    # 1) 신고 완료 멘트
    # -----------------------------
    if state["location_confirmed"] is True:
        ack = "위치가 확인되어 119에 신고를 하였습니다.\n"
    elif state["location_confirmed"] is False:
        ack = "신고를 하였습니다. 위치 파악이 안되어 구급대원이 추후 전화드릴테니 핸드폰을 주위에 두세요.\n"
    else:
        ack = "119 신고를 완료했습니다.\n"

    # -----------------------------
    # 2) 응급처치 주의사항
    # -----------------------------
    disease = state["confirmed_disease"]
    warning_text = None

    if disease:
        try:
            warn_data = get_warning_text_core(disease)
            warning_text = warn_data.get("warning_text")
        except Exception as e:
            print(f"[first_aid_warning 불러오기 실패] {e}")

    state["first_aid_warning_shown"] = True
    state.setdefault("first_history", [])

    if warning_text:
        warn_msg = (
            "지금부터 응급 처치 시 꼭 지켜야 할 주의사항을 안내하겠습니다.\n"
            f"[주의사항]\n{warning_text}\n"
            "이제 응급 처치 안내를 위해 몇 가지 사항을 확인하겠습니다.\n"
        )
    else:
        warn_msg = "응급 처치 안내를 위해 몇 가지 사항을 확인하겠습니다.\n"

    # -----------------------------
    # 3) 첫 follow-up 질문 생성
    # -----------------------------
    data = run_first_aid_core(
        disease_name=state["confirmed_disease"],
        emergency_level=state["emergency_level"],
        answer_history=state["first_history"],
        symptoms=state.get("confirmed_symptoms", []),
    )

    first_q = data.get("question")

    if not first_q:
        # 바로 matched_text가 나오는 케이스
        first_q = data.get("matched_text") or "응급처치 안내를 시작하겠습니다."

    # 첫 follow-up 질문을 기다리는 상태로 설정
    state["first_aid_waiting_for_answer"] = True
    state["first_history"].append({"role": "assistant", "content": warn_msg})
    state["first_history"].append({"role": "assistant", "content": first_q})

    # 클라이언트에게 반환할 메시지
    full_msg = ack + warn_msg + first_q
    return state, full_msg


def first_aid_step(state: dict, user_input: str) -> tuple[dict, str]:

    disease = state["confirmed_disease"]
    if not disease:
        return state, "응급처치 안내를 시작할 수 없습니다."

    state.setdefault("first_history", [])

    # ---------------------------------------------------------
    # (1) 주의사항을 아직 말하지 않은 경우 → 주의사항 + 첫 질문 한 번에 전송
    # ---------------------------------------------------------
    if not state.get("first_aid_warning_shown", False):
        state["first_aid_warning_shown"] = True

        warning_text = None
        try:
            warn_data = get_warning_text_core(disease)
            warning_text = warn_data.get("warning_text")
        except:
            pass

        if warning_text:
            warn_msg = (
                "지금부터 응급 처치 시 꼭 지켜야 할 주의사항을 안내하겠습니다.\n"
                f"[주의사항]\n{warning_text}\n"
                "응급 처치 안내를 위해 몇 가지 사항을 확인하겠습니다.\n"
            )
        else:
            warn_msg = "응급 처치 안내를 위해 몇 가지 사항을 확인하겠습니다.\n"

        # 첫 follow-up 질문 생성
        data = run_first_aid_core(
            disease_name=disease,
            emergency_level=state["emergency_level"],
            answer_history=state["first_history"],
            symptoms=state.get("confirmed_symptoms", []),
        )

        first_q = data.get("question")
        if not first_q:
            first_q = data.get("matched_text") or "응급처치를 시작합니다."

        # 상태 저장
        state["first_aid_waiting_for_answer"] = True
        state["first_history"].append({"role": "assistant", "content": warn_msg})
        state["first_history"].append({"role": "assistant", "content": first_q})

        return state, warn_msg + first_q

    # ---------------------------------------------------------
    # (2) follow-up 질문에 대한 사용자의 답 처리
    # ---------------------------------------------------------
    if user_input:
        state["first_history"].append({"role": "user", "content": user_input})

    data = run_first_aid_core(
        disease_name=disease,
        emergency_level=state["emergency_level"],
        answer_history=state["first_history"],
        symptoms=state.get("confirmed_symptoms", []),
    )

    status = data.get("status")

    if status == "진행중":
        q = data.get("question")
        if q:
            state["first_history"].append({"role": "assistant", "content": q})
            return state, q
        else:
            return state, "응급처치 안내 중 오류가 발생했습니다."

    elif status == "확정":
        msg = data.get("matched_text") or "응급처치 안내를 완료했습니다."
        state["first_history"].append({"role": "assistant", "content": msg})
        state["is_session_active"] = False
        return state, msg

    return state, "응급처치 안내 중 오류가 발생했습니다."


def simple_prank_detection(user_input: str, confirmed_symptoms: list) -> bool:
    if confirmed_symptoms:
        return False
    
    prank_keywords = [
        "테스트", "test", "장난", "재미", "심심", "놀아줘", 
        "노래", "춤", "게임", "ㅋㅋ", "ㅎㅎ", "농담"
    ]
    
    user_lower = user_input.lower().strip()
    return any(keyword in user_lower for keyword in prank_keywords)


def process_agent_message(state: dict, user_input: str) -> tuple[dict, str, bool]:
    if not state.get("is_session_active", True):
        return state, "대화가 종료되었습니다.\n통화를 종료해 주세요", False
    
    chat_history: list[dict] = state.setdefault("chat_history", [])
    
    raw_input = (user_input or "")
    if not raw_input.strip():
        # 앱 쪽에서 이미 "다시 말씀해주세요"를 처리하므로
        # 에이전트는 아무 메시지도 보내지 않고 상태만 유지
        return state, "", False
    
    if not state.get("patient_checked"):
        if not chat_history:
            first_patient_q = "안녕하세요! AI 응급 상담사입니다. 환자가 본인이신가요?"
            chat_history.append({"role": "assistant", "content": first_patient_q})
        
        # user 답변
        answer = (user_input or "").strip()
        chat_history.append({"role": "user", "content": answer})

        # [변경] 예/아니요를 GPT 기반으로 노말라이징
        decision = normalize_consent_with_history(chat_history, answer)

        if decision is True:
            state["is_patient_self"] = True
            state["patient_checked"] = True

            first_q = "환자의 상태를 말씀해주세요. 어떤 증상이 있나요?"
            chat_history.append({"role": "assistant", "content": first_q})
            return state, first_q, False  # ← 원본처럼 3개 리턴 유지

        if decision is False:
            state["is_patient_self"] = False
            state["patient_checked"] = True

            first_q = "환자의 상태를 말씀해주세요. 어떤 증상이 있나요?"
            chat_history.append({"role": "assistant", "content": first_q})
            return state, first_q, False

        # 애매한 답 → 다시 예/아니요 강제
        retry_q = (
            "죄송합니다, 잘 이해하지 못했습니다. "
            "'예' 또는 '아니요'로 답해주세요."
        )
        chat_history.append({"role": "assistant", "content": retry_q})
        return state, retry_q, False

    
    user_text = (user_input or "").strip()
    
    if not user_text:
        warn_q = "입력이 감지되지 않았습니다. 다시 한 번 말씀해주세요."
        return state, warn_q, False
    
    is_prank = simple_prank_detection(user_text, state.get("confirmed_symptoms", []))
    
    if not state.get("confirmed_disease"):
        state, message = disease_inference_step(state, user_text)
        return state, message, is_prank
    
    if not state.get("escalation_done"):
        state, message = escalation_step(state, user_text)
        return state, message, is_prank
    
    if state.get("user_consented_report") is None:
        if user_text and state.get("report_history"):
            last_msg = state["report_history"][-1]
            if last_msg["role"] == "assistant" and "신고" in last_msg["content"]:
                state["report_history"].append({"role": "user", "content": user_text})
                
                # [변경] 신고 동의 여부에 GPT 기반 예/아니요 노말라이징 사용
                decision = normalize_consent_with_history(state["report_history"], user_text)
                if decision is not None:
                    state["user_consented_report"] = decision
        
        if state.get("user_consented_report") is None:
            state, message = report_consent_step(state, user_text)
            return state, message, is_prank

    
    if state.get("user_consented_report") is True:
        # 1) 위치 단계 먼저 처리
        if not state.get("final_location_text"):
            state, message = location_step(state, user_text)
            return state, message, is_prank

        # 2) 아직 실제 신고 전송 전이면 신고 먼저
        if not state.get("report_sent"):
            state, message = send_emergency_report(state)
            return state, message, is_prank

        # 3) 여기부터는 "신고가 완료된 이후" 단계

        # 신고 직후 첫 진입이면, user_input 무시하고
        #    first_aid_step을 한 번 빈 문자열로 호출해서
        #    '첫 번째 분기 질문'을 무조건 에이전트가 먼저 던지도록 함
        if not state.get("first_history"):
            # 아직 어떤 응급처치 Q/A 기록도 없다는 뜻 = 첫 진입
            state, message = first_aid_step(state, "")
            return state, message, is_prank

        # 4) 그 다음부터는 사용자의 답변을 정상적으로 전달
        state, message = first_aid_step(state, user_text)
        return state, message, is_prank
    
    state, message = first_aid_step(state, user_text)
    return state, message, is_prank


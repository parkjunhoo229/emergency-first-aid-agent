
import json
import requests
import os
from openai import OpenAI
from persona import ROLE_DISEASE_INFERENCE
from followup_utils import load_disease_json, get_disease_prompt_string
from analyze_prompt import build_one_agent_prompt
from parse_gpt_response import parse_gpt_response
from fallback import handle_fallback

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
SERVER_URL = os.getenv('SERVER_URL', 'http://localhost:5000')

disease_data = load_disease_json()
disease_text = get_disease_prompt_string(disease_data)


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


def init_agent_state():
    return {
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
        "is_session_active": True,
        "report_message": None
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
    asked = [m for m in state["escalation_history"] if m["role"] == "assistant"]
    if asked and user_input:
        state["escalation_history"].append({"role": "user", "content": user_input})
    
    base_level = state["emergency_level"] or "비응급"
    
    payload = {
        "disease": state["confirmed_disease"],
        "base_level": base_level,
        "escalation_history": state["escalation_history"],
        "user_input": user_input if user_input else None
    }
    
    try:
        resp = requests.post(
            f"{SERVER_URL}/emergency_escalation",
            json=payload,
            timeout=20
        )
        data = resp.json()
        
        if data.get("status") == "확정":
            final_level = data.get("final_emergency_level") or base_level
            state["emergency_level"] = final_level
            state["escalation_done"] = True
            
            return report_consent_step(state, "")

        q = data.get("question")
        if q:
            state["escalation_history"].append({"role": "assistant", "content": q})
            return state, q
            
    except Exception as e:
        return state, f"응급도 판단 중 오류가 발생했습니다: {str(e)}"
    
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
                "119에 신고를 도와드릴까요? (예/아니오)"
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
        state["location_history"].append({"role": "assistant", "content": first_q})
        return state, first_q
    
    try:
        payload = {
            "location_history": state["location_history"],
            "user_input": user_input
        }
        resp = requests.post(f"{SERVER_URL}/location", json=payload, timeout=20)
        data = resp.json()
        
        if data.get("followup_question"):
            state["location_history"].append({"role": "assistant", "content": data["followup_question"]})
            return state, data["followup_question"]
        
        elif data.get("final_location_text"):
            final_loc = data["final_location_text"]
            
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
            
            normalized = normalize_consent(user_input)
            if normalized is True:
                state["final_location_text"] = final_loc
                state["location_confirmed"] = True
                return send_emergency_report(state)
            
            elif normalized is False:
                false_q = "위치 파악 실패\n 위치 파악 시도 내용: " + final_loc
                state["final_location_text"] = false_q
                state["location_confirmed"] = False
                return send_emergency_report(state)
            
            else:
                reask = f"다시 한 번 말씀해 주세요.\n'{final_loc}'이(가) 맞습니까? (예/아니오)"
                state["location_history"].append({"role": "assistant", "content": reask})
                return state, reask
        
        else:
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
    
    state["report_sent"] = True
    state["report_message"] = payload
    
    if state["location_confirmed"] is True:
        ack = "위치가 확인되어 119에 신고를 하였습니다.\n"
    elif state["location_confirmed"] is False:
        ack = "위치 파악이 힘듭니다. 구급대원이 추후 전화드릴테니 핸드폰을 주위에 두세요.\n"
    else:
        ack = "119 신고를 완료했습니다. "
    
    q = ack + "지금부터 응급처치를 안내해 드리겠습니다."
    state["location_history"].append({"role": "assistant", "content": q})
    
    return state, q


def first_aid_step(state: dict, user_input: str) -> tuple[dict, str]:
    disease = state["confirmed_disease"]
    if not disease:
        return state, "응급처치 안내를 시작할 수 없습니다."
    
    if not state["first_aid_warning_shown"]:
        try:
            warn_resp = requests.get(
                f"{SERVER_URL}/first_aid_warning?disease_name={disease}",
                timeout=20
            )
            warn_data = warn_resp.json()
            warning_text = warn_data.get("warning_text")
        except Exception:
            warning_text = None
        
        if warning_text:
            state["first_aid_warning_shown"] = True
            warn_q = (
                f"지금부터 응급처치 주의사항을 안내하겠습니다. 반드시 지켜주세요.\n"
                f"[주의사항]\n{warning_text}\n\n"
                f"이제 응급 처치 안내를 시작하겠습니다."
            )
            state["location_history"].append({"role": "assistant", "content": warn_q})
            return state, warn_q
        
        state["first_aid_warning_shown"] = True
    
    try:
        if not state["first_history"]:
            payload = {
                "disease_name": state["confirmed_disease"],
                "emergency_level": state["emergency_level"],
                "answer_history": [],
                "symptoms": state.get("confirmed_symptoms", [])
            }
        else:
            if user_input:
                state["first_history"].append({"role": "user", "content": user_input})
            payload = {
                "disease_name": state["confirmed_disease"],
                "emergency_level": state["emergency_level"],
                "answer_history": state["first_history"],
                "symptoms": state.get("confirmed_symptoms", [])
            }
        
        resp = requests.post(
            f"{SERVER_URL}/first_aid_followup",
            json=payload,
            timeout=20
        )
        data = resp.json()
        
        if data["status"] == "진행중":
            question = data["question"]
            state["first_history"].append({"role": "assistant", "content": question})
            return state, question
        
        elif data["status"] == "확정":
            matched_text = data["matched_text"]
            state["first_history"].append({"role": "assistant", "content": matched_text})
            state["is_session_active"] = False
            return state, matched_text
        
        else:
            return state, "응급처치 안내 중 오류가 발생했습니다."
            
    except Exception as e:
        return state, f"응급처치 안내 중 오류가 발생했습니다: {str(e)}"


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
        return state, "이전 대화가 종료되었습니다.", False
    
    if not state.get("chat_history"):
        first_q = "환자의 상태를 말씀해주세요. 어떤 증상이 있나요?"
        state["chat_history"] = [{"role": "assistant", "content": first_q}]
        return state, first_q, False
    
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
                normalized = normalize_consent(user_text)
                if normalized is not None:
                    state["user_consented_report"] = normalized
        
        if state.get("user_consented_report") is None:
            state, message = report_consent_step(state, user_text)
            return state, message, is_prank
    
    if state.get("user_consented_report") is True:
        if not state.get("final_location_text"):
            state, message = location_step(state, user_text)
            return state, message, is_prank
        
        if not state.get("report_sent"):
            state, message = send_emergency_report(state)
            return state, message, is_prank
        
        state, message = first_aid_step(state, user_text)
        return state, message, is_prank
    
    state, message = first_aid_step(state, user_text)
    return state, message, is_prank


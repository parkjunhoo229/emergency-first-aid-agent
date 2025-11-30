from fastapi import APIRouter, Body
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
from persona import ROLE_FIRST_AID_GUIDE
import json
import os
import re

load_dotenv()
router = APIRouter()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class FirstAidFollowupRequest(BaseModel):
    disease_name: str
    emergency_level: str
    answer_history: list[dict]
    symptoms: list[str] = []

class FirstAidFollowupResponse(BaseModel):
    status: str
    question: str | None = None
    matched_text: str | None = None

@router.post("/first_aid_followup", response_model=FirstAidFollowupResponse)
def followup_handler(req: FirstAidFollowupRequest = Body(...)):
    txt_path = Path("first_aid_data") / f"{req.disease_name}.txt"
    if not txt_path.exists():
        return FirstAidFollowupResponse(
            status="error",
            question=None,
            matched_text="지침 파일 없음"
        )

    full_text = txt_path.read_text(encoding="utf-8")
    _, main_text = _split_warning_and_main(full_text)

    if req.answer_history:
        history_text = "\n".join(
            f"{m.get('role', 'unknown')}: {m.get('content', '')}"
            for m in req.answer_history
        )
    else:
        history_text = "없음"

    prompt = f"""
=========================================
[응급처치 안내 상황 데이터]
=========================================
[병명] {req.disease_name}
[응급도] {req.emergency_level}
[확인된 증상] {", ".join(req.symptoms) if req.symptoms else "없음"}
[대화이력]
{history_text}

=========================================
[응급처치 지침 원문]
=========================================
{main_text}

=========================================
[너의 역할과 목표]
=========================================
너는 응급처치 안내 AI야.
응급의료 상담사처럼 행동하며, 사용자와의 대화 기록을 바탕으로 현재 분기 조건을 판단하고,
다음 질문을 하거나 응급처치 원문 중 적절한 지침을 그대로 찾아서 제시해.

너의 목표는 다음과 같다:
1. 응급처치 지침 문서의 구조를 분석하고,
2. 분기 조건(예: “의식이 있는 경우”, “호흡이 없는 경우”, “출혈이 심한 경우”)을 모두 식별하며,
3. 사용자의 응급도·증상·응답 이력을 종합해 
   현재 환자가 어떤 분기에 해당하는지 판단하고,
4. 해당 분기에 맞는 응급처치 절차를 **원문 그대로 안내**하는 것이다.

---

=========================================
[1단계: 지침 구조 분석]
=========================================
- 텍스트를 처음부터 끝까지 읽으며 "조건에 따라 조치가 달라지는 문장"을 모두 찾아라.
  예시:
  - "의식이 있는 경우"
  - "의식이 없는 경우"
  - "호흡이 없는 경우"
  - "출혈이 심한 경우"
  - "임산부인 경우" 등

- 각 조건문은 서로 다른 응급처치 분기를 의미한다.
- 각 조건문 이후의 문단(또는 문장)은 해당 상황에서 취해야 할 응급처치 절차이다.

- 내부적으로 다음과 같은 표를 만들어 이해하라:
  | 분기명 | 조건 문장 | 해당 응급처치 절차(문단) |
  |--------|------------|-----------------------|
  | 예: 의식 있음 | "환자가 의식이 있는 경우" | (이하 원문 절차) |
  | 예: 의식 없음 | "환자가 의식을 잃은 경우" | (이하 원문 절차) |

---

=========================================
[2단계: 환자 상태와 분기 비교]
=========================================
- 다음 데이터를 기준으로 각 분기의 조건과 일치 여부를 평가하라:
  1. 응급도 ({req.emergency_level})
  2. 증상 ({", ".join(req.symptoms) if req.symptoms else "증상 정보 없음"})
  3. 사용자 응답 히스토리 ({req.answer_history if req.answer_history else "없음"})

- 각 분기 조건이 이 데이터와 일치하면 "후보 분기"로 간주한다.
- 여러 후보 분기가 동시에 남아있다면,
  그 분기들을 구분할 수 있는 “핵심 차이 조건”을 찾고,
  그 조건을 확인하기 위한 **예/아니오 질문**을 한 문장으로 생성한다.

---

=========================================
[3단계: 분기 확정 및 응급처치 결정]
=========================================
- 만약 **하나의 분기만 남게 되면**, 즉 가능한 분기(시나리오)가 여러 개였으나  
  응급도·증상·응답 이력을 모두 반영했을 때 **하나의 시나리오만 일치한다면**,  
  그 상태를 “하나의 분기로 확정된 상태”로 간주한다.

- 하나의 분기로 확정되면:
  → 추가 질문은 하지 말고,  
  → 그 분기에 해당하는 응급처치 문단을 **원문 그대로** matched_text에 넣어 반환한다.

- 절대로 요약, 의역, 축약, 재구성하지 말 것.
- 문단의 줄바꿈, 순서, 문체, 문장부호, 어미(“~하세요”, “~하십시오”)를 그대로 유지한다.
- matched_text는 원문의 해당 부분 전체를 그대로 포함해야 한다.

---

=========================================
[4단계: 질문 생성 로직]
=========================================
- 여러 분기가 아직 남아 있을 때만 질문을 생성한다.
- 질문은 반드시 원문 속 조건문과 직접 대응해야 한다.
- “자세히 말해주세요” 같은 모호한 문장은 금지.
- 질문은 반드시 예/아니오로 답할 수 있게 만들어라.
  (예: “환자가 의식을 잃었나요?”, “출혈이 계속되나요?”)

---

=========================================
[5단계: 출력 형식 (JSON 한 줄 ONLY)]
=========================================
- 반드시 아래 JSON 형식 그대로 출력하라.
- 설명, 코드블록(```), 접두사, 불필요한 문장 절대 포함 금지.

{
  "status": "진행중" 또는 "확정",
  "question": "예/아니오로 답할 수 있는 질문 (진행중일 경우)",
  "matched_text": "상황에 맞는 응급처치 원문 (확정일 경우)"
}

조건:
- 분기 조건이 남아 있으면 status="진행중" + question
- 분기 조건이 모두 확인되면 status="확정" + matched_text
- matched_text는 반드시 원문 그대로 반환 (요약 금지)

---

=========================================
[추가 규칙 요약]
=========================================
- '분기'는 반드시 원문 속에 실제 존재하는 조건문이어야 한다.
- GPT가 스스로 새 조건을 만들지 않는다.
- 질문은 반드시 원문 조건과 1:1 대응.
- matched_text는 원문 복사, 요약/가공 금지.
- JSON 이외의 출력, 코드블록, 주석, 설명문 절대 포함하지 말 것.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,
            messages=[
                {"role": "system", "content": ROLE_FIRST_AID_GUIDE},
                {"role": "user", "content": prompt.strip()}
            ],
            timeout=20
        )
        
        reply = resp.choices[0].message.content.strip()        
        parsed = _safe_json_load(reply)
        
        return FirstAidFollowupResponse(
            status=parsed.get("status"),
            question=parsed.get("question"),
            matched_text=parsed.get("matched_text")
        )

    except Exception as e:
        return FirstAidFollowupResponse(
            status="error",
            question=None,
            matched_text=None
        )

def _split_warning_and_main(txt: str):
    match = re.search(r"(?mi)^주의\s*사항\s*[:：]?\s*$", txt)
    if not match:
        return None, txt.strip()
    start = match.end()
    warning_text = txt[start:].strip()
    main_text = txt[:match.start()].strip()
    return warning_text if warning_text else None, main_text


def _safe_json_load(text: str) -> dict:
    try:
        t = text.strip()
        if t.startswith("```"):
            t = re.sub(r"^```(?:json)?", "", t)
            t = re.sub(r"```$", "", t)
        s, e = t.find("{"), t.rfind("}")
        if s != -1 and e != -1:
            return json.loads(t[s:e+1])
    except Exception:
        pass
    return {"status": "error", "question": None, "matched_text": "JSON 파싱 실패"}
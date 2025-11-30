from fastapi import APIRouter, Body
from pydantic import BaseModel
from openai import OpenAI
from persona import ROLE_LOCATION_ASSISTANT
import os, json, re
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()


class LocationRequest(BaseModel):
    location_history: list[dict]
    user_input: str


class LocationResponse(BaseModel):
    status: str
    followup_question: str | None = None
    final_location_text: str | None = None


def _extract_json_response(text: str) -> dict | None:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?", "", t)
        t = re.sub(r"```$", "", t)
    s, e = t.find("{"), t.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            return json.loads(t[s:e+1])
        except json.JSONDecodeError:
            return None
    return None


def _build_prompt(location_history: list[dict]) -> str:
    return "\n".join(f"{m['role']}: {m['content']}" for m in location_history)


@router.post("/location", response_model=LocationResponse)
def run_location(req: LocationRequest = Body(...)):
    history = req.location_history + [{"role": "user", "content": req.user_input}]
    prompt_text = _build_prompt(history)

    SYSTEM_MSG = ROLE_LOCATION_ASSISTANT + """
역할: 119 전달용 상세 위치 보조관.
목표: 구조대가 환자를 정확히 찾을 수 있도록, 현재 위치를 한 문장으로 정리하는 것.

출력 형식:
- 사용자 응답이 충분한 경우 → JSON 한 줄: {"final_location_text": "..."}
- 사용자 응답이 부족한 경우 → JSON 한 줄: {"followup_question": "..."}

필수 조건:
반드시 아래 둘 중 하나를 충족해야 '충분한 위치 정보'로 간주합니다.
    1. 실내인 경우 → 건물명 + 층수 또는 호수 정보 포함
    2. 실외인 경우 → 주변 랜드마크(큰 간판, 건물, 교차로 등)와 위치 특성 포함

final_location_text 작성 규칙:
- 반드시 완전한 한 문장으로 작성합니다. (예: "한밭대학교 N4동 5층 강의실입니다.")
- 약어, 불완전 문장, 불필요한 조사 누락 금지.

특수 응답 처리:
- followup_question은 사용자의 이전 응답에서 **부족한 정보를 보완하기 위한 구체적인 질문**이어야 합니다.
- 무조건 **한 가지 정보만** 명확하게 요청해야 하며, **짧고 직접적인 문장**으로 작성해야 합니다.
- 표현 예시: 
    1. 실내인데 층수 정보가 없는 경우 → "몇 층인지 알 수 있을까요?"
    2. 실외인데 랜드마크가 없는 경우 → "근처에 큰 건물이나 간판이 보이나요?"
- "자세히 말씀해주세요", "더 구체적으로요" 같은 모호한 표현은 절대 사용하지 마세요.
- 질문은 반드시 사용자가 **단문으로 바로 대답할 수 있는 형식**으로 하세요.
- 사용자가 '모르겠어요', '기억 안나요' 등으로 답할 경우 → 대체 가능한 정보를 followup_question으로 출력하세요.
- followup_question을 생성할 때는, 이전에 이미 했던 질문은 절대 반복하지 마세요.
- 동일 의미의 질문(예: "몇 층이신가요?" ↔ "층수를 알 수 있을까요?")도 절대 반복하지 마세요.
- 동일한 질문은 사용자가 먼저 다시 언급하지 않는 이상 다시 묻지 마세요.
- 같은 의미의 질문도 표현만 바꾸는 식으로 반복하지 마세요.
- 절대로 JSON 외의 문장(설명, 예시, 접두문, 코드블록 등)을 출력하지 마세요.
- JSON 문자열만 정확히 한 줄로 출력하세요.
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": prompt_text},
            ],
            timeout=20
        )
        content = resp.choices[0].message.content.strip()
        parsed = _extract_json_response(content)

        if parsed is None:
            return LocationResponse(status="error", followup_question=None, final_location_text="GPT 응답 파싱 실패")

        if "final_location_text" in parsed:
            return LocationResponse(
                status="확정", 
                final_location_text = parsed["final_location_text"]
            )

        elif "followup_question" in parsed:
            user_turns = sum(1 for m in history if m["role"] == "user")
            
            if user_turns >= 5:
                dialogue_log = "\n".join([f"{m['role']}: {m['content']}" for m in req.location_history])
                approx_loc = parsed.get("final_location_text") or "위치 파악이 어려워 현장 전화 연결이 필요합니다."
                combined_text = f"{approx_loc}\n\n[대화 기록]\n{dialogue_log}"

                return LocationResponse(
                    status="확정",
                    final_location_text=combined_text
                )
                
            return LocationResponse(status="진행중", followup_question=parsed["followup_question"])

        else:
            return LocationResponse(status="error", final_location_text="형식 오류")

    except Exception as e:
        return LocationResponse(status="error", final_location_text=f"GPT 호출 실패: {e}")

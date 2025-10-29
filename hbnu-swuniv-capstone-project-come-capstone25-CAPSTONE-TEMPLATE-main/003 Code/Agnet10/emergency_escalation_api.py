from fastapi import APIRouter, Body
from pydantic import BaseModel
from openai import OpenAI
from persona import ROLE_EMERGENCY_ESCALATION
from pathlib import Path
import os, json
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter()


# -------------------------------
# 요청 / 응답 모델 정의
# -------------------------------
class EscalationRequest(BaseModel):
    disease: str
    base_level: str = "비응급"
    escalation_history: list[dict]  # escalation_history 전용
    user_input: str | None = None


class EscalationResponse(BaseModel):
    status: str                     # "진행중" | "확정" | "error"
    question: str | None = None     # 다음 질문 (진행중일 때)
    final_emergency_level: str | None = None
    message: str | None = None      # 오류 또는 안내 메시지


# -------------------------------
# 내부 헬퍼
# -------------------------------
def build_question_prompt(symptom: str, disease: str) -> str:
    return f"""
너는 'AI 응급의료 에이전트'로서, [병명] 환자의 응급도를 최종 확정내기 위해, 아래 증상이 있는지 질문을 만들어야 한다.

[병명]
{disease}

[응급도 격상 증상]
{symptom}

[질문 생성 조건]
- 반드시 해당 증상이 [응급도 격상 증상]에 포함되어 있어야 한다.
- 반드시 **한 가지 증상만** 묻는 **짧고 명확한 문장**으로 작성할 것
- 반드시 증상이 **존재하는지 여부**를 묻는 형식으로 질문할 것! **좋은 예시: \"의식을 잃었나요?\", \"가슴 통증이 있나요?\"**,  **나쁜 예시: \"의식이 있나요?\", \"가슴 통증이 없나요?\"**
- 그 외 설명이나 예시 없이, 질문 문장 하나만 출력할 것
- 금지: 코드블록, 괄호, “예시”, 추가 설명, 접두/접미 문구 일절 금지
""".strip()


def build_analysis_prompt(escalation_history: list[dict], disease: str) -> str:
    turns = "\n".join(f"{m['role']}: {m['content']}" for m in escalation_history)
    return f"""
너는 'AI 응급의료 에이전트'로서, [병명] 환자의 응급도를 최종 확정내기 위해 대화내용을 분석하는 역할을 수행해야한다.

[병명]
{disease}

[대화내용]
{turns}

[분석 조건]
- 반드시 [대화내용]을 분석하여 사용자의 응답을 분석해야한다.
- [대화내용]을 분석하여 질문에 대해 사용자의 응답을 \"예\", \"아니요\"로 분류해야한다.
- 사용자가 증상이 있다고 이야기를 하거나 긍정 하는 경우 \"예\"로 간주한다.
- 사용자가 증상이 없다고 하거나 부정을 하는 경우 \"아니요\"로 간주한다.
- 사용자가 증상이 모르겠다고 하는 경우 \"아니요\"로 간주한다.
- 그 외 설명이나 예시 없이 \"예\", \"아니요\" 둘중 하나로 출력할것
""".strip()


# -------------------------------
# 핵심 로직
# -------------------------------
@router.post("/emergency_escalation", response_model=EscalationResponse)
def run_emergency_escalation_api(req: EscalationRequest = Body(...)):
    """
    병명에 따른 응급도 격상 질문 → 사용자 응답 분석 → 응급도 확정 API 버전
    """
    disease = req.disease
    base_level = req.base_level
    escalation_history = req.escalation_history
    user_input = req.user_input

    # 1 JSON 파일 로드 (병명별 응급도 조건)
    path = Path("emergency_degree") / f"{disease}.json"
    if not path.exists():
        return EscalationResponse(
            status="확정",
            final_emergency_level=base_level,
            message="응급도 격상 조건 파일 없음 → 기본 응급도로 확정"
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return EscalationResponse(status="error", message=f"JSON 파싱 실패: {e}")

    # 2 사용자가 답변한 경우 (응답 분석 단계)
    if user_input:
        escalation_history.append({"role": "user", "content": user_input})
        analysis_prompt = build_analysis_prompt(escalation_history, disease)
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": ROLE_EMERGENCY_ESCALATION},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                timeout=10
            )
            decision = resp.choices[0].message.content.strip()
        except Exception as e:
            return EscalationResponse(status="error", message=f"GPT 분석 실패: {e}")

        if decision == "예":
            # 가장 최근 질문이 어떤 레벨의 증상이었는지 판단
            for level in ["긴급", "응급"]:
                symptoms = data.get(level, [])
                for symptom in symptoms:
                    if symptom in escalation_history[-2]["content"]:  # 직전 질문 포함 시
                        return EscalationResponse(
                            status="확정",
                            final_emergency_level=level,
                            message=f"{level} 증상 확인됨 → 응급도 확정"
                        )
            # 예라고 했지만 매칭 안될 경우
            return EscalationResponse(
                status="확정",
                final_emergency_level=base_level,
                message="응답 예이나 매칭된 증상 없음 → 기본 응급도로 확정"
            )
        else:
            # 아니요면 계속 진행 가능 (다음 질문 요청)
            pass

    # 3 다음 질문 생성 단계
    asked = [m["content"] for m in escalation_history if m["role"] == "assistant"]
    
    for level in ["긴급", "응급"]:
        symptoms = data.get(level, [])
        # 이미 물어본 질문은 건너뜀 
        for symptom in symptoms:
            if any(symptom in a for a in asked):
                continue
            try:
                q_prompt = build_question_prompt(symptom, disease)
                resp = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": ROLE_EMERGENCY_ESCALATION},
                        {"role": "user", "content": q_prompt}
                    ],
                    temperature=0.2,
                    timeout=10
                )
                question = resp.choices[0].message.content.strip()
                escalation_history.append({"role": "assistant", "content": question})
                return EscalationResponse(status="진행중", question=question)
            except Exception as e:
                return EscalationResponse(status="error", message=f"GPT 질문 생성 실패: {e}")

    # 4 모든 질문 완료 → 기본 응급도로 확정
    return EscalationResponse(
        status="확정",
        final_emergency_level=base_level,
        message="모든 격상 증상 확인 불가 → 기본 응급도로 확정"
    )

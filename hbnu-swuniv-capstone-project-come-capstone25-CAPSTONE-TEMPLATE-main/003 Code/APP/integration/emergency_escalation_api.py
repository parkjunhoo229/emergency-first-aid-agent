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


class EscalationRequest(BaseModel):
    disease: str
    base_level: str = "비응급"
    escalation_history: list[dict]
    user_input: str | None = None


class EscalationResponse(BaseModel):
    status: str
    question: str | None = None
    final_emergency_level: str | None = None
    message: str | None = None


def build_question_prompt(symptom: str, disease: str) -> str:
    """
    증상에 대한 예/아니오 질문을 생성하는 프롬프트.
    - 질문 문장 안에 반드시 [응급도 격상 증상]의 의미를 포함하도록 유도
    - 증상마다 문장이 달라지도록 지시
    """
    return f"""
너는 'AI 응급의료 에이전트'로서, [병명] 환자의 응급도를 최종 확정내기 위해, 아래 증상이 있는지 질문을 만들어야 한다.

[병명]
{disease}

[응급도 격상 증상]
{symptom}

[질문 생성 조건]
- 반드시 위 [응급도 격상 증상]의 의미가 질문 문장 안에 자연스럽게 포함되어야 한다.
  - 예: 증상이 '쇼크 증상'이면 "식은땀, 피부 창백, 맥박이 빨라지는 등 쇼크 증상이 있나요?"처럼 표현한다.
- 반드시 **한 가지 증상만** 묻는 **짧고 명확한 문장**으로 작성할 것.
- 반드시 증상이 **존재하는지 여부**를 묻는 형식으로 질문할 것.
  - 좋은 예시: "의식을 잃었나요?", "가슴 통증이 있나요?"
  - 나쁜 예시: "의식이 있나요?", "가슴 통증이 없나요?"
- 동일 병명 내 다른 증상에 대해 이미 했던 질문과 문장이 최대한 겹치지 않도록, 증상 특징을 살려서 문장을 만들어라.
- 그 외 설명이나 예시 없이, 질문 문장 하나만 출력할 것.
- 금지: 코드블록, 괄호, “예시”, 추가 설명, 접두/접미 문구 일절 금지.
""".strip()


def build_analysis_prompt(escalation_history: list[dict], disease: str) -> str:
    """
    GPT가 '예' / '아니요'를 JSON으로만 반환하도록 지시하는 프롬프트.
    """
    turns = "\n".join(f"{m['role']}: {m['content']}" for m in escalation_history)
    return f"""
너는 'AI 응급의료 에이전트'로서, [병명] 환자의 응급도를 최종 확정내기 위해 대화내용을 분석하는 역할을 수행해야 한다.

[병명]
{disease}

[대화내용]
{turns}

[분석 조건]
- 반드시 [대화내용]의 마지막 assistant 질문과 그에 대한 사용자(user)의 최근 답변을 분석해야 한다.
- 해당 질문은 특정 증상의 "존재 여부"를 묻는 예/아니오 질문이다.
- 사용자가 증상이 있다고 이야기하거나, 긍정/동의/수락하는 경우는 "예"로 간주한다.
- 사용자가 증상이 없다고 하거나, 부정/거절/무시하는 경우는 "아니요"로 간주한다.
- 사용자가 "모르겠다", "잘 모르겠어요"처럼 애매하게 말하는 경우에는 상황에 따라 의도에 맞게 "예" 또는 "아니요" 중 하나로 결정하라.

[출력 형식]
- 아래 JSON 형식으로만 출력할 것.

{{
  "answer": "예" 또는 "아니요"
}}
""".strip()


def run_emergency_escalation_core(
    disease: str,
    base_level: str,
    escalation_history: list[dict],
    user_input: str | None = None,
) -> dict:
    """
    응급도 격상 로직의 실제 본체.
    - 에이전트 내부에서는 이 함수만 직접 호출
    - HTTP 요청이 들어오면 라우터가 이 함수를 감싸서 사용

    설계:
    1) 병명.json에서 "긴급" / "응급" 증상 리스트를 읽는다.
    2) 질문 생성 시, 각 질문에 대해 symptom, symptom_level 메타데이터를 escalation_history에 함께 저장한다.
       예: {"role": "assistant", "content": 질문문장, "symptom": "뼈가 피부를 뚫고 나온 경우", "symptom_level": "긴급"}
    3) 사용자가 "예"라고 답하면, 가장 최근 assistant 메시지의 symptom_level로 응급도를 확정한다.
    4) 사용자가 "아니요"라고 답하면, 해당 symptom은 used 처리되고 다음 증상으로 넘어간다.
    5) 모든 증상을 다 사용했는데도 "예"가 없으면 base_level로 확정한다.
    """
    path = Path("emergency_degree") / f"{disease}.json"
    if not path.exists():
        return {
            "status": "확정",
            "question": None,
            "final_emergency_level": base_level,
            "message": "응급도 격상 조건 파일 없음 → 기본 응급도로 확정",
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "status": "error",
            "question": None,
            "final_emergency_level": None,
            "message": f"JSON 파싱 실패: {e}",
        }

    # -----------------------------------
    # 1) 사용자가 방금 답한 경우 → 응답 분석
    # -----------------------------------
    decision = None
    if user_input:
        escalation_history.append({"role": "user", "content": user_input})
        analysis_prompt = build_analysis_prompt(escalation_history, disease)

        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": ROLE_EMERGENCY_ESCALATION},
                    {"role": "user", "content": analysis_prompt},
                ],
                temperature=0.0,
                timeout=20,
            )
            raw = resp.choices[0].message.content.strip()

            # 우선 JSON 파싱 시도
            try:
                parsed = json.loads(raw)
                decision = str(parsed.get("answer", "")).strip()
            except Exception:
                # JSON 형식 안 지켰을 때는 그냥 원문 그대로 사용
                decision = raw.strip()

            decision = decision.replace(" ", "")

            # 기대값이 아니면 사용자 입력 기반 fallback
            if decision not in ("예", "아니요"):
                norm = (user_input or "").replace(" ", "").lower()
                YES = ["예", "네", "응", "어", "그래", "좋아", "좋아요", "ㅇㅇ", "웅", "응응"]
                NO = ["아니", "아니요", "아니오", "싫어", "별로야", "아닌데", "노", "없어", "없는것같아"]

                if norm in YES:
                    decision = "예"
                elif norm in NO:
                    decision = "아니요"

        except Exception as e:
            return {
                "status": "error",
                "question": None,
                "final_emergency_level": None,
                "message": f"GPT 분석 실패: {e}",
            }

        # -----------------------------
        # 1-1) 예 / 아니요에 따른 분기
        # -----------------------------
        if decision == "예":
            # 가장 최근 assistant 질문의 symptom_level을 그대로 사용
            last_q = None
            for m in reversed(escalation_history):
                if m.get("role") == "assistant" and "symptom_level" in m:
                    last_q = m
                    break

            if last_q is not None:
                level = last_q.get("symptom_level")
                if level in ("긴급", "응급"):
                    return {
                        "status": "확정",
                        "question": None,
                        "final_emergency_level": level,
                        "message": f"{level} 증상 확인됨 → 응급도 확정",
                    }
            # 예라고 했는데 증상 매칭 안 되면 기본 응급도
            return {
                "status": "확정",
                "question": None,
                "final_emergency_level": base_level,
                "message": "응답 예이나 매칭된 증상 없음 → 기본 응급도로 확정",
            }

        else:
            # "아니요"인 경우: 그냥 다음 증상 질문으로 진행
            # (별도 처리 없이 아래 '다음 질문 생성 단계'로 내려감)
            pass

    # -----------------------------------
    # 2) 다음 질문 생성 단계
    # -----------------------------------

    # escalation_history 에서 이미 질문한 symptom / question 목록 추출
    used_symptoms = {
        m["symptom"]
        for m in escalation_history
        if m.get("role") == "assistant" and "symptom" in m
    }
    used_questions = {
        m["content"]
        for m in escalation_history
        if m.get("role") == "assistant"
    }

    # "긴급" 먼저, 그다음 "응급" 순서대로 질문
    for level in ["긴급", "응급"]:
        symptoms = data.get(level, [])
        for symptom in symptoms:
            # 이미 질문한 증상은 스킵 (증상을 기반으로 제거!)
            if symptom in used_symptoms:
                continue

            question = None
            last_error: Exception | None = None

            # 동일한 질문 문장이 나오면 최대 2번까지 재생성 시도
            for _ in range(2):
                try:
                    q_prompt = build_question_prompt(symptom, disease)
                    resp = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": ROLE_EMERGENCY_ESCALATION},
                            {"role": "user", "content": q_prompt},
                        ],
                        temperature=0.2,
                        timeout=20,
                    )
                    candidate = resp.choices[0].message.content.strip()

                    # 이전에 이미 한 질문 문장과 완전히 같으면 다시 시도
                    if candidate in used_questions:
                        continue

                    question = candidate
                    break
                except Exception as e:
                    last_error = e
                    continue

            # 재시도 후에도 question이 없으면, 가능한 경우 fallback 질문 생성
            if question is None:
                if last_error is not None:
                    return {
                        "status": "error",
                        "question": None,
                        "final_emergency_level": None,
                        "message": f"GPT 질문 생성 실패: {last_error}",
                    }
                # GPT 호출 실패가 아닌 로직 문제인 경우, 증상명을 직접 사용한 질문으로 fallback
                question = f"{symptom} 증상이 있나요?"

            # 최종 선택된 question을 사용
            used_questions.add(question)

            escalation_history.append(
                {
                    "role": "assistant",
                    "content": question,
                    "symptom": symptom,
                    "symptom_level": level,
                }
            )

            return {
                "status": "진행중",
                "question": question,
                "final_emergency_level": None,
                "message": None,
            }

    # 여기까지 왔다는 것은 모든 증상에 대해 "예"가 없었다는 뜻 → 기본 응급도로 확정
    return {
        "status": "확정",
        "question": None,
        "final_emergency_level": base_level,
        "message": "모든 격상 증상 확인 불가 → 기본 응급도로 확정",
    }


# HTTP 요청이 들어오는 경우에만 사용하는 라우터 (core() 래핑)
@router.post("/emergency_escalation", response_model=EscalationResponse)
def run_emergency_escalation_api(req: EscalationRequest = Body(...)):
    data = run_emergency_escalation_core(
        disease=req.disease,
        base_level=req.base_level,
        escalation_history=req.escalation_history,
        user_input=req.user_input,
    )
    # dict → Pydantic 모델
    return EscalationResponse(**data)

# 응급처치 AI 에이전트 API – 최종 연동 가이드 (2025.10)

## 1. 개요
이 프로젝트는 **GPT 기반 응급처치 AI 에이전트**입니다.  
사용자의 자연어 입력(예: “사람이 쓰러졌어요”, “숨을 쉬지 않아요”)을 기반으로  
**병명 추론 → 응급도 판단 → 119 신고 → 응급처치 안내**를 자동으로 수행합니다.  

앱 또는 백엔드에서는 `/agent` 엔드포인트 하나만 호출하면 전체 프로세스가 자동으로 진행됩니다.

---

## 2. 서버 구성

| 구성 요소 | 역할 |
|------------|------|
| **main_api.py** | 메인 엔트리포인트 (`/agent`) – 전체 대화 흐름 제어 |
| **emergency_escalation_api.py** | 응급도 격상 판단 (긴급/응급 조건 질문) |
| **ask_location_api.py** | 위치 수집 및 보완 질문 자동 생성 |
| **first_aid_followup.py** | 응급처치 안내 (GPT 1회 호출로 질문+응답 판단 통합) |
| **first_aid_warning.py** | 병명별 응급처치 전 ‘주의사항’ 텍스트 반환 |
| **fallback.py** | 병명 추론 실패 시 안전 메시지 및 119 권유 안내 |
| **parse_gpt_response.py** | GPT JSON 응답 파싱 |
| **followup_utils.py** | 병명-증상 매핑 데이터 로드 및 문자열 변환 유틸 |
| **disease_symptom.json** | 병명-증상 매핑 데이터 (기본 응급도 포함) |
| **emergency_degree/** | 병명별 응급도 격상 조건 JSON 폴더 |
| **first_aid_data/** | 병명별 응급처치 지침 TXT 문서 |

---

## 3. 실행 방법

```bash
uvicorn main_api:app --host 0.0.0.0 --port 8000
```
로컬 테스트: `http://localhost:8000`

---

## 4. 환경변수 (.env)

에이전트 서버(이 리포지토리):
```env
OPENAI_API_KEY=sk-***************
SERVER_URL=http://yourip:8000   # 자체 내부 라우팅용 (location, escalation 등)
```

**앱/백엔드 서버(연동 측; 선택):**
```env
```
- `SERVER_URL`: 에이전트 내부 라우팅용 자기 서버 주소

---

## 5. 주요 엔드포인트

| 엔드포인트 | 설명 |
|-------------|------|
| `POST /agent` | 메인 플로우 제어 (자동 병명 추론~응급처치) |
| `POST /emergency_escalation` | 응급도 격상 조건 질문·판단 |
| `POST /location` | 위치 정보 정제 및 보완 질문 |
| `POST /first_aid_followup` | 병명별 응급처치 분기 판단 및 안내 |
| `GET /first_aid_warning` | 병명별 응급처치 주의사항 반환 |

---

## 6. 백엔드 → 에이전트 요청 구조 (AgentRequest)

```json
{
  "chat_history": [],
  "escalation_history": [],
  "report_history": [],
  "location_history": [],
  "first_history": [],
  "confirmed_symptoms": [],
  "last_candidates": [],
  "confirmed_disease": null,
  "emergency_level": null,
  "turn_count": 0,
  "escalation_done": false,
  "user_consented_report": null,
  "final_location_text": null,
  "location_confirmed": null,
  "report_sent": false,
  "first_aid_warning_shown": false,
  "is_session_active": true,
  "report_message": null,
  "echo": false,  // ← 질문 반복 플래그

  "user_input": "환자가 숨을 쉬지 않아요" // ← 매 턴 새 입력
}
```

> **echo 플래그 규칙**  
> echo는 **“직전 질문을 그대로 반복해서 보내야 하는지”**를 판단하기 위한 플래그입니다.  
> - **false**: **user input 작성** (사용자가 새로 말함) → 에이전트로 *직전 에이전트 상태 + user_input* 전달  
> - **true**: **user input 작성 X** → 에이전트로 *직전 에이전트 상태 그대로* 전달하여 질문만 반복  
>  
> 정리: **echo=true가 아닌 경우 항상** “에이전트가 보낸 응답 + 유저 인풋”을 보내고, **echo=true면** “에이전트가 보낸 상태 그대로(유저 인풋 없이)” 재호출합니다.

---

## 7. 에이전트 → 백엔드 응답 구조 (AgentResponse)

```json
{
  "chat_history": [],
  "escalation_history": [],
  "report_history": [],
  "location_history": [],
  "first_history": [],
  "confirmed_symptoms": ["호흡곤란"],
  "last_candidates": ["심정지", "질식"],
  "confirmed_disease": "심정지",
  "emergency_level": "긴급",
  "turn_count": 1,
  "escalation_done": true,
  "user_consented_report": true,
  "final_location_text": "한밭대학교 N4동 5층 강의실",
  "location_confirmed": true,
  "report_sent": true,
  "first_aid_warning_shown": true,
  "is_session_active": true,
  "report_message": {
    "disease": "심정지",
    "symptoms": ["호흡곤란", "의식 소실"],
    "emergency_level": "긴급",
    "location": "한밭대학교 N4동 5층 강의실"
  },
  "echo": false,

  "status": "확정",
  "message": "응급처치 안내 완료",
  "next_question": "지금부터 심폐소생술을 시행하세요."
}
```

---

## 8. 백엔드 연동 방법

간단히 정리하자면
에이전트는 다음과 같은 형식의 응답(AgentResponse)을 백엔드에 반환합니다:
```json
{
  "chat_history": [],
  "escalation_history": [],
  "report_history": [],
  "location_history": [],
  "first_history": [],
  "confirmed_symptoms": ["호흡곤란"],
  "last_candidates": ["심정지", "질식"],
  "confirmed_disease": "심정지",
  "emergency_level": "긴급",
  "turn_count": 1,
  "escalation_done": true,
  "user_consented_report": true,
  "final_location_text": "한밭대학교 N4동 5층 강의실",
  "location_confirmed": true,
  "report_sent": true,
  "first_aid_warning_shown": true,
  "is_session_active": true,
  "report_message": {
    "disease": "심정지",
    "symptoms": ["호흡곤란", "의식 소실"],
    "emergency_level": "긴급",
    "location": "한밭대학교 N4동 5층 강의실"
  },
  "echo": false,

  "status": "확정",
  "message": "응급처치 안내",
  "next_question": "지금부터 심폐소생술을 시작하겠습니다.",
  "user_input": null
}
```

백엔드는 위 응답을 그대로 유지하되,
사용자 입력이 들어오면 아래와 같이 변환하여 에이전트를 다시 호출하면 됩니다 

```json
{
  "chat_history": [],
  "escalation_history": [],
  "report_history": [],
  "location_history": [],
  "first_history": [],
  "confirmed_symptoms": ["호흡곤란"],
  "last_candidates": ["심정지", "질식"],
  "confirmed_disease": "심정지",
  "emergency_level": "긴급",
  "turn_count": 1,
  "escalation_done": true,
  "user_consented_report": true,
  "final_location_text": "한밭대학교 N4동 5층 강의실",
  "location_confirmed": true,
  "report_sent": true,
  "first_aid_warning_shown": true,
  "is_session_active": true,
  "report_message": {
    "disease": "심정지",
    "symptoms": ["호흡곤란", "의식 소실"],
    "emergency_level": "긴급",
    "location": "한밭대학교 N4동 5층 강의실"
  },
  "echo": false,

  "user_input": "사용자의 입력"
}
```

즉, **AgentResponse의 모든 상태 필드를 그대로 유지**하고
**echo 값**에 따라
  **false면** → "user_input"에 사용자의 최신 발화를 추가
  **true면** → "user_input" 없이 그대로 재전송
이 규칙에 따라 **/agent 엔드포인트를 다시 호출**하면 됩니다.



---

## 9. 백엔드 연동 예시

> **루프 규칙**: “이전 응답(AgentResponse)을 그대로 다시 보내되, `echo`와 `user_input`만 규칙대로 갱신해 `/agent`로 POST한다.”

```python
# Python 예시
import requests

AGENT_URL = "http://localhost:8000/agent"

# 세션 전체 상태 (최초 1회만 초기화)
agent_state = {
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
    "report_message": None,
    "echo": False,
}

# 매 턴마다 호출 (user_text가 있을 수도, 없을 수도 있음)
def to_agent(user_text: str | None = None):
    """
    user_text가 None이면 echo=True (직전 질문 반복)
    user_text가 문자열이면 echo=False (새 입력 전달)
    """
    if user_text is None:
        agent_state["echo"] = True
        agent_state.pop("user_input", None)   # 입력 제거 (직전 질문 반복)
    else:
        agent_state["echo"] = False
        agent_state["user_input"] = user_text # 새 입력 추가

    res = requests.post(AGENT_URL, json=agent_state, timeout=10)
    res.raise_for_status()
    data = res.json()
    agent_state.update(data)                  # 최신 상태 덮어쓰기
    return data

# 예시 실행
if __name__ == "__main__":
    # 첫 턴: 유저 입력 존재 → echo=False
    print(to_agent("사람이 쓰러졌어요"))
    # 두 번째 턴: 입력 없이 echo=True → 직전 질문 반복
    print(to_agent())

```

---

## 10. 119 신고 – **백엔드(연동 측)가 해야 할 일**

에이전트는 신고 확정 후 사용자 위치 파악 완료 시 `AgentResponse.report_message`에 **기본 페이로드**를 담아 반환합니다:

```json
{
  "report_message": {
    "disease": "심정지",
    "symptoms": ["호흡곤란", "의식 소실"],
    "emergency_level": "긴급",
    "location": "한밭대학교 N4동 5층 강의실"
  }
}
```

### 백엔드는 이 페이로드를 **확장**하여 실제 119 서버로 전송해야 합니다.
- 추가 필드(예시): `lat`, `lon`, `caller_phone`, `caller_name`, `timestamp`, `session_id` 등
- 최종 전송 예시 (연동 측 백엔드 코드 샘플):

```python
import requests, time, uuid, os

REPORT_SERVER_URL = os.getenv("119_SERVER_URL")

def forward_to_119(report_message, lat, lon, phone, name):
    payload = {
        report_message,
        "lat": lat,
        "lon": lon,
        "caller_phone": phone,
        "caller_name": name,
        "timestamp": int(time.time()*1000),
        "session_id": str(uuid.uuid4())
    }
    r = requests.post(REPORT_SERVER_URL, json=payload, timeout=5)
    r.raise_for_status()
    return r.json()
```

> 정리: **에이전트는 ‘신고 본문 기초 정보’만 생성**합니다. 실제 좌표/전화번호/신고자 이름 등 **개인·위치 정보는 백엔드가 붙여서** 임의로 만든 119 서버(`REPORT_SERVER_URL`)에 **최종 전송**해야 합니다.

---

## 11. 기능 요약

- **빈 입력 처리**: `user_input`이 비면 자동 재질문  
- **echo 처리**: `echo=true`면 입력 없이 직전 질문 반복  
- **주의사항 안내**: 병명 확정 후 `first_aid_warning` → 이어서 `first_aid_followup`  
- **119 신고**: `report_message` 수신 → 백엔드가 좌표/연락처 등 확장 → 119 서버 전송

---

## 12. 상태 코드

| 상태값 | 의미 |
|---------|------|
| `"진행중"` | 질문 중 (대화 계속) |
| `"확정"` | 단계 완료 (병명, 응급도, 응급처치 등) |
| `"fallback"` | 질문 한도 초과 → 119 안내 |
| `"error"` | 예외 발생 (API 실패, GPT 오류 등) |

---

## 13. 대화 흐름 예시

```
사용자: 사람이 쓰러졌어요
에이전트: 환자가 숨을 쉬나요?
사용자: 아니요
에이전트: 병명이 '심정지'로 확정되었습니다. (기본 응급도: 긴급)
에이전트: 위치를 알려주세요.
(위치 확정) → (report_message 생성) → 백엔드가 좌표/전화/이름 첨부 → 119 서버 전송
→ (echo=true) 주의사항 출력 → 응급처치 안내
```

---

## 14. 개발 및 유지보수
- **팀명:** 중증외상센터  
- **개발:** 박준후, 이창석  
- **지도교수:** 박천음 교수님 (한밭대학교 컴퓨터공학과)  
- **최종 수정일:** 2025-10-29

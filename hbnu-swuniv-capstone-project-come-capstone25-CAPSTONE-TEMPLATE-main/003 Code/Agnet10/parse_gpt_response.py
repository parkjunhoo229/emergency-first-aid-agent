import json
import re

def parse_gpt_response(text: str) -> dict:
    """
    GPT 응답을 받아 JSON 객체로 변환합니다.
    응답은 반드시 JSON 한 줄 형식이어야 하며,
    코드펜스(```json ... ```)나 설명 문구가 포함되면 제거 후 처리합니다.
    JSON이 아닐 경우 예외를 발생시킵니다.
    """
    def _strip_code_fence(t: str) -> str:
        t = t.strip()
        # 코드펜스 제거: ``` 또는 ```json 등 제거
        if t.startswith("```"):
            t = re.sub(r"^```(?:json)?", "", t)
            t = re.sub(r"```$", "", t)
        return t.strip()

    cleaned = _strip_code_fence(text)

    # JSON 추출: 가장 바깥의 { ... } 범위 찾기
    s = cleaned.find("{")
    e = cleaned.rfind("}")
    if s == -1 or e == -1 or e <= s:
        raise ValueError("GPT 응답에서 유효한 JSON 객체를 찾을 수 없습니다.")

    json_str = cleaned[s:e+1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as ex:
        raise ValueError(f"JSON 파싱 실패: {ex}")

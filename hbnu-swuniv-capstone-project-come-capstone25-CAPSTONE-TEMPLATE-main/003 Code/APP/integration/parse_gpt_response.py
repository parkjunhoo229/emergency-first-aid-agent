import json
import re

def parse_gpt_response(text: str) -> dict:
    def _strip_code_fence(t: str) -> str:
        t = t.strip()
        if t.startswith("```"):
            t = re.sub(r"^```(?:json)?", "", t)
            t = re.sub(r"```$", "", t)
        return t.strip()

    cleaned = _strip_code_fence(text)

    s = cleaned.find("{")
    e = cleaned.rfind("}")
    if s == -1 or e == -1 or e <= s:
        raise ValueError("GPT 응답에서 유효한 JSON 객체를 찾을 수 없습니다.")

    json_str = cleaned[s:e+1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as ex:
        raise ValueError(f"JSON 파싱 실패: {ex}")

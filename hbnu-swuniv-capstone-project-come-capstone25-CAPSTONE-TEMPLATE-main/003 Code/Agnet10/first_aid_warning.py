import re
from pathlib import Path
from typing import Tuple, Optional
from fastapi import APIRouter, Query

router = APIRouter()

@router.get("/first_aid_warning")
def get_warning_text(disease_name: str = Query(..., description="병명 (예: '질식')")):
    txt_path = Path("first_aid_data") / f"{disease_name}.txt"
    if not txt_path.exists():
        return {"warning_text": None, "message": "지침 파일 없음"}

    full_text = txt_path.read_text(encoding="utf-8")
    warning_text, _ = _split_warning_and_main(full_text)

    return {
        "warning_text": warning_text,
        "message": "주의사항 반환 완료" if warning_text else "주의사항 없음"
    }

def _split_warning_and_main(full_text: str) -> Tuple[Optional[str], str]:
    """
    [주의사항] 섹션과 [응급처치 본문]을 자동으로 구분한다.
    - 주의사항이 텍스트 맨 위에 있을 수도, 중간에 있을 수도 있음.
    - '주의사항' 키워드를 기준으로 양쪽 영역을 나눈다.
    """
    text = full_text.strip()

    # "주의사항"이 없는 경우 전체를 본문으로 반환
    if "주의사항" not in text:
        return None, text

    # "주의사항" 위치 기준으로 분리
    parts = text.split("주의사항", 1)
    before = parts[0].strip()
    after = parts[1].strip()

    # 주의사항이 상단에 있을 경우 (본문보다 먼저 등장)
    if len(before) < len(after):
        # 주의사항 블록 추출
        if "\n\n" in after:
            warning_block, main_text = after.split("\n\n", 1)
        else:
            warning_block, main_text = after, ""
        warning_text = warning_block.strip()
    else:
        # 주의사항이 하단에 있을 경우
        if "\n\n" in before:
            main_text, warning_block = before.split("\n\n", 1)
        else:
            main_text, warning_block = before, ""
        warning_text = warning_block.strip()

    return (warning_text if warning_text else None, main_text.strip())


import re
from pathlib import Path
from typing import Tuple, Optional
from fastapi import APIRouter, Query

router = APIRouter()

def get_warning_text_core(disease_name: str) -> dict:
    """
    first_aid_data/병명.txt 를 읽어서
    주의사항(warning_text)과 본문(main_text)을 분리한 뒤 warning_text만 반환.
    """
    txt_path = Path("first_aid_data") / f"{disease_name}.txt"
    if not txt_path.exists():
        return {"warning_text": None, "message": "지침 파일 없음"}

    full_text = txt_path.read_text(encoding="utf-8")
    warning_text, _ = _split_warning_and_main(full_text)

    return {
        "warning_text": warning_text,
        "message": "주의사항 반환 완료" if warning_text else "주의사항 없음"
    }
    

@router.get("/first_aid_warning")
def get_warning_text(disease_name: str = Query(..., description="병명 (예: '질식')")):
    # HTTP 요청이 들어올 때만 쓰는 래퍼
    return get_warning_text_core(disease_name)


def _split_warning_and_main(full_text: str) -> Tuple[Optional[str], str]:
    text = full_text.strip()

    if "주의 사항" not in text:
        return None, text

    parts = text.split("주의 사항", 1)
    before = parts[0].strip()
    after = parts[1].strip()

    if len(before) < len(after):
        if "\n\n" in after:
            warning_block, main_text = after.split("\n\n", 1)
        else:
            warning_block, main_text = after, ""
        warning_text = warning_block.strip()
    else:
        if "\n\n" in before:
            main_text, warning_block = before.split("\n\n", 1)
        else:
            main_text, warning_block = before, ""
        warning_text = warning_block.strip()

    return (warning_text if warning_text else None, main_text.strip())


# fake_119_server.py
import json
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os

app = FastAPI(title="Fake 119 Server")

class EmergencyReport(BaseModel):
    disease: Optional[str] = None
    symptoms: List[str] = []
    emergency_level: Optional[str] = None
    location: Optional[str] = None
    patient_info: Optional[dict] = None
    gps_location: Optional[dict] = None
    created_at: Optional[datetime] = None

# 메모리에 신고 리스트 저장
REPORTS: List[EmergencyReport] = []


@app.post("/report")
async def receive_report(report: EmergencyReport):
    saved = report.copy(update={"created_at": datetime.utcnow()})
    REPORTS.append(saved)

    print("\n========== [새 119 신고 도착] ==========")

    # Pydantic v2 기반 JSON 직렬화
    json_str = json.dumps(
        saved.model_dump(mode="json"),  # datetime 포함해도 문제 없음
        ensure_ascii=False,
        indent=2,
    )

    print(json_str)

    # 파일 저장 (원하면 사용)
    file_path = "last_report.json"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(json_str)

    print("=====================================\n")

    return {
        "success": True,
        "message": "신고 접수 완료",
        "count": len(REPORTS),
    }


@app.get("/reports")
async def list_reports():
    # JSON으로 자동 변환 가능하게 dump
    return {
        "success": True,
        "reports": [r.model_dump(mode="json") for r in REPORTS],
    }

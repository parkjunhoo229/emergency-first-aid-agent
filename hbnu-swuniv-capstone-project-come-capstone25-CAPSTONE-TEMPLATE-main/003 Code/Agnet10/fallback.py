def handle_fallback(candidates, disease_data):
    """
    병명 확정 실패 시 (질문 불가 or 질문 상한 초과)
    의심 질병 후보 + 가장 높은 응급도 + 119 권유 메시지 출력
    """
    level_priority = {"긴급": 3, "응급": 2, "비응급": 1}
    lines = []
    
    if candidates:        
        highest_level = "비응급"
        
        for d in candidates:
            level = disease_data.get(d, {}).get("emergency_level", "비응급")
            if level_priority[level] > level_priority[highest_level]:
                highest_level = level

        lines.append("추가로 질문할 수 없습니다.")
        lines.append("지금까지의 정보를 바탕으로 다음 질병들이 의심됩니다:")
        for d in candidates:
            level = disease_data.get(d, {}).get("emergency_level", "비응급")
            lines.append(f" - {d} ({level})")

        lines.append(f"\n현재 의심 질병 중 가장 응급한 단계는 '{highest_level}'입니다.")
        lines.append("정확한 판단을 위해 가까운 병원이나 119에 도움을 요청하세요.")
    else:
        lines.append("질문 가능한 증상이 없습니다. 그러나 명확한 병명을 확정하기 어렵습니다.")
        lines.append("가까운 병원에 방문하거나 119에 도움을 요청하세요.")

    # 문자열로 반환
    return "\n".join(lines)
# app/services/report_service.py
from typing import Dict, Any

from app.utils.report_formatter import ReportFormatter
from app.services.raw_report_service import generate_raw_report


def generate_report(ticker: str) -> Dict[str, Any]:
    """
    /api/stocks/report 에서 호출할 서비스 함수
    - ticker: '삼성전자' 같은 종목명 or '005930' 같은 코드
    """
    try:
        # 1) 내부 리포트 JSON 생성 (네가 이미 만든 로직을 여기로 모아놓는 래퍼)
        raw_report = generate_raw_report(ticker)

        # 2) 데이터 없을 때
        if not raw_report or not raw_report.get("report"):
            return ReportFormatter.build_no_data_response(ticker)

        # 3) 정상 응답
        return ReportFormatter.build_success_response(raw_report)

    except Exception as e:
        # 디버깅용으로 로그 한 줄 남겨놓는 것도 좋다
        print(f"[generate_report] error: {e}")
        return ReportFormatter.build_error_response()


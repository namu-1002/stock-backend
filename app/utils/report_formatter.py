from __future__ import annotations
from typing import Any, Dict, List, Optional
import re


class ReportFormatter:
    """
    S02 종목 리포트 스펙에 맞게
    내부 리포트 JSON -> Kakao 스킬 응답(JSON) 으로 변환하는 유틸리티
    """

    @staticmethod
    def build_success_response(report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Case 1. 정상 응답
        """
        item_cards: List[Dict[str, Any]] = [
            ReportFormatter._build_summary_card(report_data),
            ReportFormatter._build_price_card(report_data),
            ReportFormatter._build_financial_card(report_data),
            ReportFormatter._build_valuation_card(report_data),
            ReportFormatter._build_opinion_card(report_data),
        ]

        return {
            "version": "2.0",
            "template": {
                "outputs": [{"itemCard": card} for card in item_cards],
                "quickReplies": ReportFormatter._build_common_quick_replies(),
            },
        }

    @staticmethod
    def build_no_data_response(ticker: str) -> Dict[str, Any]:
        text = f"앗, 아직 '{ticker}'에 대한 리포트 데이터가 없어요 🥲 다른 종목 리포트를 보시겠어요?"

        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {"simpleText": {"text": text}}
                ],
                "quickReplies": [
                    {"label": "다른 종목 리포트", "action": "block", "blockId": "S02"},
                    {"label": "도움말", "action": "block", "blockId": "HELP"},
                ],
            },
        }

    @staticmethod
    def build_error_response() -> Dict[str, Any]:
        text = (
            "지금 리포트를 불러오는 중에 문제가 발생했어요 😢\n"
            "잠시 후 다시 시도하시거나, 다른 종목을 조회해볼까요?"
        )

        return {
            "version": "2.0",
            "template": {
                "outputs": [{"simpleText": {"text": text}}],
                "quickReplies": [
                    {"label": "다시 시도", "action": "block", "blockId": "S02"},
                    {"label": "다른 종목 리포트", "action": "block", "blockId": "S02"},
                    {"label": "도움말", "action": "block", "blockId": "HELP"},
                ],
            },
        }

    # -----------------------
    # ItemCard 생성 부분
    # -----------------------

    @staticmethod
    def _build_summary_card(report_data: Dict[str, Any]) -> Dict[str, Any]:
        sections = report_data.get("report", {}).get("sections", {})
        raw = report_data.get("raw_data", {})
        price_trend = raw.get("price_trend", {})
        basic = raw.get("basic", {})

        summary_text = sections.get("summary", "") or "요약 정보가 없습니다."
        one_line = ReportFormatter._one_line_summary(summary_text)

        one_year = price_trend.get("1y")
        mcap_rank = basic.get("market_cap_rank")
        mcap = basic.get("market_cap")

        def fmt_pct(v: Optional[float]) -> str:
            return f"{v:+.2f}%" if isinstance(v, (int, float)) else "N/A"

        def fmt_won(v: Optional[int]) -> str:
            if not isinstance(v, (int, float)):
                return "N/A"
            if v >= 10**12:
                return f"{v / 10**12:.1f}조원"
            if v >= 10**8:
                return f"{v / 10**8:.0f}억원"
            return f"{int(v):,}원"

        item_list = [
            {"title": "요약 1", "description": f"최근 1년 수익률: {fmt_pct(one_year)}"},
            {"title": "요약 2", "description": f"시가총액: {fmt_won(mcap)}"},
            {"title": "요약 3", "description": f"시총 순위: {mcap_rank}위" if mcap_rank else "시총 순위: N/A"},
            {"title": "요약 4", "description": "상세 내용은 아래 카드에서 확인하세요."},
        ]

        return {
            "imageTitle": {"title": "투자 요약", "description": "해당 종목에 대한 핵심 요약입니다."},
            "title": "",
            "description": f"LLM 한 문장 요약: {one_line}",
            "itemList": item_list,
        }

    @staticmethod
    def _build_price_card(report_data: Dict[str, Any]) -> Dict[str, Any]:
        sections = report_data.get("report", {}).get("sections", {})
        raw = report_data.get("raw_data", {})
        price_trend = raw.get("price_trend", {})
        technical = raw.get("technical", {})

        desc_src = sections.get("price_analysis", "") or "주가 동향 분석 정보가 없습니다."
        one_line = ReportFormatter._one_line_summary(desc_src)

        def fmt_pct(v: Optional[float]) -> str:
            return f"{v:+.2f}%" if isinstance(v, (int, float)) else "N/A"

        item_list = [
            {"title": "1개월 수익률", "description": fmt_pct(price_trend.get("1m"))},
            {"title": "3개월 수익률", "description": fmt_pct(price_trend.get("3m"))},
            {"title": "1년 수익률", "description": fmt_pct(price_trend.get("1y"))},
            {"title": "52주 고점 대비", "description": fmt_pct(price_trend.get("from_high"))},
            {"title": "RSI", "description": f"{technical.get('rsi', 'N/A')} ({technical.get('rsi_signal', 'N/A')})"},
        ]

        return {
            "imageTitle": {"title": "주가 동향 분석", "description": "최근 주가 흐름과 기술적 지표를 분석합니다."},
            "title": "",
            "description": f"LLM 한 문장 요약: {one_line}",
            "itemList": item_list,
        }

    @staticmethod
    def _build_financial_card(report_data: Dict[str, Any]) -> Dict[str, Any]:
        sections = report_data.get("report", {}).get("sections", {})
        desc_src = sections.get("financial_analysis", "") or "재무제표 요약 정보가 없습니다."
        one_line = ReportFormatter._one_line_summary(desc_src)

        item_list = [
            {"title": "매출", "description": "텍스트 요약 기반으로 매출 흐름 설명"},
            {"title": "영업이익", "description": "텍스트 요약 기반으로 수익성 설명"},
            {"title": "순이익", "description": "당기순이익 및 추세 요약"},
            {"title": "현금흐름", "description": "영업/투자/재무 현금흐름 요약"},
            {"title": "재무 안정성", "description": "부채비율·유동비율 등 안정성 평가"},
        ]

        return {
            "imageTitle": {"title": "재무제표", "description": "기업 실적 기반 재무 흐름을 요약합니다."},
            "title": "",
            "description": f"LLM 한 문장 요약: {one_line}",
            "itemList": item_list,
        }

    @staticmethod
    def _build_valuation_card(report_data: Dict[str, Any]) -> Dict[str, Any]:
        raw = report_data.get("raw_data", {})
        metrics = raw.get("metrics", {})

        def fmt(v: Any) -> str:
            return "N/A" if v is None else str(v)

        per = fmt(metrics.get("per"))
        pbr = fmt(metrics.get("pbr"))
        roe = fmt(metrics.get("roe"))
        eps = fmt(metrics.get("eps"))
        bps = fmt(metrics.get("bps"))

        desc = "PER·PBR·ROE 기준으로 현재 주가의 적정성을 평가합니다. 상세 수치는 아래 항목을 참고하세요."

        item_list = [
            {"title": "PER", "description": f"{per}배"},
            {"title": "PBR", "description": f"{pbr}배"},
            {"title": "ROE", "description": f"{roe}%"},
            {"title": "EPS/BPS", "description": f"EPS {eps} / BPS {bps}"},
            {"title": "평가 요약", "description": "적정·저평가·고평가 여부는 리포트 본문 참조"},
        ]

        return {
            "imageTitle": {"title": "밸류에이션", "description": "PER·PBR·ROE로 주가 적정성을 판단합니다."},
            "title": "",
            "description": f"LLM 한 문장 요약: {desc}",
            "itemList": item_list,
        }

    @staticmethod
    def _build_opinion_card(report_data: Dict[str, Any]) -> Dict[str, Any]:
        sections = report_data.get("report", {}).get("sections", {})
        opinion_text = sections.get("investment_opinion", "") or ""

        opinion, target_price = ReportFormatter._extract_opinion_and_target(opinion_text)
        raw = report_data.get("raw_data", {})
        basic = raw.get("basic", {})
        current_price = basic.get("current_price")

        upside_str = ReportFormatter._calc_upside(current_price, target_price)
        desc = ReportFormatter._one_line_summary(opinion_text) or "투자의견 정보가 없습니다."

        item_list = [
            {"title": "종합 의견", "description": opinion or "N/A"},
            {"title": "목표 주가", "description": target_price or "N/A"},
            {"title": "Upside", "description": upside_str},
            {"title": "투자 리스크", "description": "리포트 본문에서 제시한 주요 리스크를 참고하세요."},
            {"title": "모니터링 포인트", "description": "업황·실적·신사업 진행 상황을 지속적으로 체크하세요."},
        ]

        return {
            "imageTitle": {"title": "투자의견", "description": "최종 투자 결론과 리스크를 제공합니다."},
            "title": "",
            "description": f"LLM 한 문장 요약: {desc}",
            "itemList": item_list,
        }

    # -----------------------
    # QuickReply 공통
    # -----------------------

    @staticmethod
    def _build_common_quick_replies() -> List[Dict[str, Any]]:
        return [
            {"label": "뉴스/커뮤니티 보기", "action": "block", "blockId": "S06"},
            {"label": "다른 종목 리포트", "action": "block", "blockId": "S02"},
            {"label": "관심종목 추가", "action": "block", "blockId": "S10"},
            {"label": "도움말", "action": "block", "blockId": "HELP"},
        ]

    # -----------------------
    # Helper Functions
    # -----------------------

    @staticmethod
    def _one_line_summary(text: str, max_len: int = 80) -> str:
        if not text:
            return ""
        for sep in [". ", "。", "\n"]:
            if sep in text:
                text = text.split(sep)[0]
                break
        return text[: max_len] + ("..." if len(text) > max_len else "")

    @staticmethod
    def _extract_opinion_and_target(text: str) -> (Optional[str], Optional[str]):
        if not text:
            return None, None

        lower = text.lower()
        opinion = None

        if "매수" in text or "buy" in lower:
            opinion = "매수(BUY)"
        elif "보유" in text or "hold" in lower:
            opinion = "보유(HOLD)"
        elif "매도" in text or "sell" in lower:
            opinion = "매도(SELL)"

        numbers = re.findall(r"[\d,]+", text)
        target = None
        if numbers:
            num = numbers[0].replace(",", "")
            try:
                target_int = int(num)
                target = f"{target_int:,}원"
            except:
                pass

        return opinion, target

    @staticmethod
    def _calc_upside(current_price: Optional[int], target_price_str: Optional[str]) -> str:
        if not current_price or not target_price_str:
            return "N/A"

        try:
            target_num = int(target_price_str.replace(",", "").replace("원", ""))
        except:
            return "N/A"

        if current_price <= 0:
            return "N/A"

        diff = (target_num - current_price) / current_price * 100.0
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.1f}%"


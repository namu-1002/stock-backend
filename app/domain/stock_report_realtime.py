# app/domain/stock_report_realtime.py
"""
실시간 DART API 조회 기반 종목 리포트 생성
Pinecone 없이 즉시 재무제표를 조회하여 리포트 생성
"""

import sys
import io
import os
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import json

# Windows console encoding fix
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

from app.domain.stock_report_api import StockReportAPI
from app.domain.dart_financial_loader import DartFinancialLoader
from app.domain.metrics_calculator import MetricsCalculator
from app.utils.report_formatter import ReportFormatter
from app.clients.dart_client import DartClient
import google.generativeai as genai

class RealtimeStockReportGenerator:
    """
    실시간 DART API 조회 기반 리포트 생성기
    Pinecone 없이 즉시 재무제표를 조회하여 분석
    """

    def __init__(self):
        """Initialize API"""
        print("🔧 실시간 종목 리포트 생성기 초기화 중...")

        # Stock Report API (정량 데이터)
        self.stock_api = StockReportAPI()
        print("✅ Stock API 초기화 완료")

        # DART API (재무제표)
        dart_key = os.environ.get("DART_API_KEY")
        if not dart_key:
            raise ValueError("DART_API_KEY not found in environment")
        dart_client = DartClient(api_key=dart_key)
        print("✅ DART API 초기화 완료")

        # DART Financial Loader (모듈화)
        self.financial_loader = DartFinancialLoader(dart_client)

        # Metrics Calculator (모듈화)
        self.metrics_calculator = MetricsCalculator()

        # Report Formatter (모듈화)
        self.report_formatter = ReportFormatter()

        # Gemini API (LLM)
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=self.gemini_key)
        print("✅ Gemini API 초기화 완료\n")

    def generate_report(self, ticker: str) -> Dict:
        """
        실시간 종목 리포트 생성

        Args:
            ticker: 종목 코드

        Returns:
            리포트 딕셔너리
        """
        print(f"📊 {ticker} 리포트 생성 중...\n")

        # Step 1: 정량 데이터 수집
        print("[ Step 1 ] 정량 데이터 수집")
        raw_data = self._collect_quantitative_data(ticker)

        if 'error' in raw_data['basic']:
            return {
                'error': f"종목 {ticker} 데이터를 찾을 수 없습니다.",
                'ticker': ticker
            }

        print(f"✅ 종목명: {raw_data['basic']['name']}")
        print(f"✅ 현재가: {raw_data['basic']['current_price']:,}원\n")

        # Step 2: 실시간 재무제표 조회 (DART API) - 모듈 사용
        print("[ Step 2 ] 실시간 재무제표 조회")
        financial_data, financial_df = self.financial_loader.load_financials(ticker)

        if financial_data:
            print(f"✅ 재무제표 조회 성공\n")
        else:
            print(f"⚠️  재무제표 없음 (주가 분석만 진행)\n")

        # Step 2.5: 재무제표에서 밸류에이션 지표 계산 - 모듈 사용
        if financial_df is not None:
            print("[ Step 2.5 ] 밸류에이션 지표 계산")
            calculated_metrics = self.metrics_calculator.calculate_from_dataframe(
                financial_df,
                raw_data['basic']['current_price']
            )
            # 계산된 지표로 덮어쓰기
            if calculated_metrics:
                raw_data['metrics'] = calculated_metrics
                print(f"✅ PER: {calculated_metrics.get('per', 'N/A')}배, "
                      f"PBR: {calculated_metrics.get('pbr', 'N/A')}배, "
                      f"ROE: {calculated_metrics.get('roe', 'N/A')}%\n")

        # Step 3: LLM으로 리포트 생성
        print("[ Step 3 ] LLM 리포트 생성")
        report_content = self._generate_report_with_llm(
            ticker=ticker,
            raw_data=raw_data,
            financial_data=financial_data
        )
        print("✅ 리포트 생성 완료\n")

        return {
            'metadata': {
                'ticker': ticker,
                'company_name': raw_data['basic']['name'],
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'has_financials': financial_data is not None
            },
            'report': report_content,
            'raw_data': raw_data
        }

    def _collect_quantitative_data(self, ticker: str) -> Dict:
        """정량 데이터 수집"""
        return {
            'basic': self.stock_api.get_basic_info(ticker),
            'price_trend': self.stock_api.get_price_trend(ticker),
            'metrics': self.stock_api.get_key_metrics(ticker),
            'technical': self.stock_api.get_technical_analysis(ticker),
            'financial_trend': self.stock_api.get_financial_trend(ticker)
        }


    def _generate_report_with_llm(
        self,
        ticker: str,
        raw_data: Dict,
        financial_data: Optional[str]
    ) -> Dict:
        """LLM으로 리포트 생성"""

        basic = raw_data['basic']
        trend = raw_data['price_trend']
        metrics = raw_data['metrics']
        technical = raw_data['technical']

        # Prompt 생성
        prompt = f"""
당신은 전문 금융 애널리스트입니다. 다음 데이터를 바탕으로 {basic['name']}({ticker})의 투자 리포트를 작성해주세요.

## 📊 제공된 데이터

### 1. 기본 정보
- 종목명: {basic['name']}
- 현재가: {basic['current_price']:,}원
- 전일 대비: {basic['price_change']:,}원 ({basic['price_change_pct']:+.2f}%)
- 시가총액 순위: {basic['market_cap_rank']}위

### 2. 가격 추세
- 1개월 수익률: {trend.get('1m', 'N/A')}%
- 3개월 수익률: {trend.get('3m', 'N/A')}%
- 1년 수익률: {trend.get('1y', 'N/A')}%
- 52주 최고가: {trend.get('52w_high', 0):,}원
- 52주 최저가: {trend.get('52w_low', 0):,}원

### 3. 투자 지표
- PER: {metrics.get('per', 'N/A')}
- PBR: {metrics.get('pbr', 'N/A')}
- ROE: {metrics.get('roe', 'N/A')}%
- 배당수익률: {metrics.get('dividend_yield', 'N/A')}%

### 4. 기술적 분석
- RSI: {technical.get('rsi', 'N/A')} ({technical.get('rsi_signal', 'N/A')})
- 추세: {technical.get('trend', 'N/A')}

### 5. 재무제표 데이터
{financial_data if financial_data else "❌ 재무제표 데이터 없음"}

---

## 📝 리포트 작성 요청

위 데이터를 종합하여 다음 섹션으로 구성된 투자 리포트를 작성해주세요:

### [1. 투자 요약] (3-5줄)
핵심 투자 포인트를 간결하게 요약

### [2. 주가 동향 분석]
최근 주가 흐름 및 기술적 지표 분석

### [3. 재무 상태 분석]
{"재무제표 데이터를 바탕으로 재무 안정성 및 수익성 분석" if financial_data else "재무제표 데이터가 없어 제한적 분석만 가능. 주가 및 밸류에이션 지표 중심으로 분석"}

### [4. 밸류에이션]
제공된 PER, PBR, ROE 지표를 바탕으로 현재 주가의 적정성을 평가하세요.

### [5. 투자 의견]
- 종합 투자 의견 (매수/보유/매도)
- 목표주가 제시
- 투자 리스크 요인
- 주요 모니터링 포인트

---

리포트 작성을 시작해주세요:
"""

        # Gemini로 리포트 생성
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            report_text = response.text

            # 구조화된 리포트로 파싱
            sections = self._parse_report_sections(report_text)

            return {
                'title': f"{basic['name']} 투자 리포트",
                'full_text': report_text,
                'sections': sections,
                'has_financials': financial_data is not None
            }

        except Exception as e:
            return {
                'title': f"{basic['name']} 리포트 생성 실패",
                'error': str(e),
                'sections': {}
            }

    def _parse_report_sections(self, report_text: str) -> Dict:
        """리포트 텍스트를 섹션별로 파싱"""
        sections = {
            'summary': '',
            'price_analysis': '',
            'financial_analysis': '',
            'valuation': '',
            'investment_opinion': ''
        }

        # 섹션 구분자로 분리
        lines = report_text.split('\n')
        current_section = None
        current_content = []

        section_map = {
            '투자 요약': 'summary',
            '주가 동향': 'price_analysis',
            '재무 상태': 'financial_analysis',
            '밸류에이션': 'valuation',
            '투자 의견': 'investment_opinion'
        }

        for line in lines:
            # 섹션 헤더 감지
            is_header = False
            for keyword, section_key in section_map.items():
                if keyword in line and ('[' in line or '#' in line):
                    # 이전 섹션 저장
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()

                    current_section = section_key
                    current_content = []
                    is_header = True
                    break

            if not is_header and current_section:
                current_content.append(line)

        # 마지막 섹션 저장
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def print_report(self, report: Dict):
        """리포트 출력 (formatter 사용)"""
        if 'error' in report:
            print(f"❌ 에러: {report['error']}")
            return

        # ReportFormatter를 사용하여 출력
        formatted_text = self.report_formatter.format_full_report(report)
        print(formatted_text)


# ========================================
# 실행 예시
# ========================================

if __name__ == "__main__":
    print("="*70)
    print("🚀 실시간 종목 리포트 생성기")
    print("="*70)
    print()

    generator = RealtimeStockReportGenerator()

    # 테스트:  (재무제표 없음)
    ticker = '005490'
    print(f"테스트 종목: {ticker} (대한항공)")
    print()

    report = generator.generate_report(ticker)
    generator.print_report(report)

    # JSON 저장
    print("\n💾 리포트를 JSON 파일로 저장 중...")
    output_file = f"stock_report_realtime_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ 저장 완료: {output_file}")

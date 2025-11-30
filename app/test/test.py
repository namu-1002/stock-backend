from app.clients.dart_client import DartClient
from app.domain.dart_financial_loader import DartFinancialLoader
import os

dart_key = os.getenv("DART_API_KEY")
client = DartClient(api_key=dart_key)
loader = DartFinancialLoader(client)

_, df = loader.load_financials("005930")

print(df.head(30))   # 앞 30줄 출력
print(df['account_nm'].unique())  # 모든 계정과목 표시

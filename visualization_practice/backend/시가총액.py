import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from pandas.tseries.offsets import QuarterEnd
import os



########################### ㅅ ㅣ  ㄱ ㅏ 총 액 ###########################


# 1️⃣ 분기별 말일 생성
dates = pd.date_range("2016-03-31", "2025-06-30", freq="Q")

# 2️⃣ 삼성전자 티커 설정 (보통주)
ticker = "005930.KS"
t = yf.Ticker(ticker)

# 발행주식수 (yfinance에서 가져오기)
info = t.fast_info
shares = info.get("sharesOutstanding", None)
if shares is None:
    try:
        shares = t.info["sharesOutstanding"]
    except:
        shares = None

if shares is None:
    raise ValueError("발행주식수 정보를 불러올 수 없습니다.")

# 3️⃣ 분기별 종가 조회 및 시가총액 계산
data = []
for d in dates:
    hist = t.history(start=d - pd.Timedelta(days=10), end=d + pd.Timedelta(days=10))
    if hist.empty:
        continue
    close_price = hist["Close"].iloc[-1]
    market_cap = close_price * shares
    data.append({"date": d, "close_price": close_price, "market_cap": market_cap})

df = pd.DataFrame(data)
df["date"] = pd.to_datetime(df["date"])
df["market_cap_trillion"] = df["market_cap"] / 1_0000_0000_0000  # 조 단위 환산

# 4️⃣ 시각화
plt.figure(figsize=(12,6))
plt.plot(df["date"], df["market_cap_trillion"], marker="o")
plt.title("삼성전자 분기별 시가총액 추이 (2016Q1~2025Q2)", fontsize=14)
plt.ylabel("시가총액 (조 원)")
plt.xlabel("날짜")
plt.grid(True)
plt.show()

# 5️⃣ 데이터 미리보기
print(df.head(10))

output_dir = "C:\\ITstudy\\15_final_project\\visualization_practice\\backend\\시가총액"
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "삼성전자_분기별_시가총액_2016Q1_2025Q2.csv")
df.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"✅ 저장 완료: {output_path}")
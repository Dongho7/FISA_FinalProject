import os
import requests
import time
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
BASE_URL = os.getenv("KIS_BASE_URL")
# .env에서 KIS_ACCESS_TOKEN을 불러옵니다.
token = os.getenv("KIS_ACCESS_TOKEN") 

# --- [KOSPI용] API 데이터 수집 함수 (⭐️ 100일 반복 조회 로직 추가) ---
def get_daily_index_price_history(access_token, symbol, start_date_str, end_date_str):
    """
    (업종/지수) 지정된 지수의 전체 기간 시세를 '100일 단위로 반복 조회'합니다.
    """
    
    all_data_normalized = [] # {'date':..., 'price':...}
    
    # ⭐️ 1. 반복 조회를 위한 날짜 설정
    current_end_date = datetime.strptime(end_date_str, "%Y%m%d")
    start_date_dt = datetime.strptime(start_date_str, "%Y%m%d")
    
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice"
    
    headers = {
        # ⭐️ 2. [버그 수정] .env의 토큰에 "Bearer "가 이미 포함되어 있으므로 f-string 제거
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKUP03500100",  # TR_ID는 요청하신 대로 유지
        "custtype":"P"
    }
    
    print(f"   -> {symbol} (KOSPI/업종 API: U) 조회 시작 (100일 단위 반복)...")

    # ⭐️ 3. 100일 단위 반복 조회 While 루프
    while current_end_date >= start_date_dt:
        query_end_date = current_end_date.strftime("%Y%m%d")
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "U", 
            "FID_INPUT_ISCD": symbol,
            "FID_INPUT_DATE_1": start_date_str, # (시작일은 참고용)
            "FID_INPUT_DATE_2": query_end_date, # (실제 조회 기준일)
            "FID_PERIOD_DIV_CODE": "D"
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()

            if data['rt_cd'] != '0':
                print(f"❌ [API 오류] {symbol} ({query_end_date}): {data.get('msg1', '메시지 없음')}")
                break
            
            RAW_OUTPUT_LIST_KEY = 'output2' 
            
            if RAW_OUTPUT_LIST_KEY not in data or not data[RAW_OUTPUT_LIST_KEY]:
                # 더 이상 데이터가 없으면 반복 중단
                print(f"   -> {symbol}: {query_end_date} 기준 데이터 없음. 조회 완료.")
                break 
            
            output_list = data[RAW_OUTPUT_LIST_KEY]
            
            for item in output_list:
                RAW_DATE_KEY = 'stck_bsop_date'
                RAW_PRICE_KEY = 'bstp_nmix_prpr' 
                
                if RAW_DATE_KEY not in item or RAW_PRICE_KEY not in item:
                    continue # 키가 없으면 해당 아이템 건너뛰기
                    
                all_data_normalized.append({
                    'date': item[RAW_DATE_KEY],
                    'price': item[RAW_PRICE_KEY]
                })
            
            # ⭐️ 4. 다음 조회 날짜 설정
            earliest_date_str = output_list[-1][RAW_DATE_KEY]
            earliest_date_dt = datetime.strptime(earliest_date_str, "%Y%m%d")
            
            print(f"   -> {symbol}: {earliest_date_str} 까지 {len(output_list)}건 수신...")

            # 목표 시작일 도달 시 중단
            if earliest_date_dt <= start_date_dt:
                print(f"   -> {symbol}: 목표 시작일({start_date_str}) 도달. 수집 완료.")
                break
                
            # 다음 요청의 종료일은 (수신된 가장 이른 날짜 - 1일)
            current_end_date = earliest_date_dt - timedelta(days=1)
            time.sleep(0.1) # API 제한 방지

        except requests.exceptions.HTTPError as e:
            print(f"❌ [HTTP 오류] {symbol} ({query_end_date}): {e}")
            print(f"   응답 내용: {e.response.text}") 
            break
        except Exception as e:
            print(f"❌ [기타 오류] {symbol}: {e}")
            break

    print(f"   -> {symbol}: 총 {len(all_data_normalized)}건 수신 완료 (중복 포함).")
    return all_data_normalized

if __name__ == "__main__":
    
    # ⭐️ [요청 반영] 2025년 10월 31일까지
    START_DATE = "20191201"
    END_DATE = "20251107" 
    
    # KOSPI 데이터 조회
    data = get_daily_index_price_history(token, "0001", START_DATE, END_DATE)
    
    if data and isinstance(data, list):
        print("\n✅ 데이터 수신 성공")
        
        try:
            df = pd.DataFrame(data)
            
            # DataFrame 정리
            df.rename(columns={'date': 'Date', 'price': 'KOSPI'}, inplace=True)
            
            # ⭐️ [수정] 반복 조회로 인한 중복 데이터 제거
            df.drop_duplicates(subset=['Date'], keep='first', inplace=True)
            
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            df['KOSPI'] = pd.to_numeric(df['KOSPI'])
            
            # ⭐️ [수정] 날짜 순으로 정렬
            df.sort_index(ascending=True, inplace=True)
            
            file_name = f"KOSPI_{START_DATE}_to_{END_DATE}.csv"
            df.to_csv(file_name)
            
            print(f"✅ 데이터를 {file_name} 파일로 저장 완료.")
            print(f"총 수집 건수: {len(df)}일치 (중복 제거)")
            print("\n--- 저장된 데이터 (앞부분 5줄) ---")
            print(df.head())
            print("\n--- 저장된 데이터 (뒷부분 5줄) ---")
            print(df.tail())
            
        except Exception as e:
            print(f"❌ 데이터프레임 변환 또는 CSV 저장 중 오류 발생: {e}")
    else:
        print("\n--- ❌ 데이터 수신 실패, CSV 저장 생략 ---")
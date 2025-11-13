import os
import requests
import time
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- 1. 환경 설정 및 .env 로드 ---
load_dotenv()
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
BASE_URL = os.getenv("KIS_BASE_URL")
KIS_ACCESS_TOKEN = os.getenv("KIS_ACCESS_TOKEN")  # .env에서 KIS_ACCESS_TOKEN을 불러옵니다.

# --- 2. API 인증 함수 ---
# def get_access_token():
#     """한투 API 접근 토큰을 발급받습니다."""
#     url = f"{BASE_URL}/oauth2/tokenP"
#     headers = {"content-type": "application/json"}
#     data = {
#         "grant_type": "client_credentials",
#         "appkey": APP_KEY,
#         "appsecret": APP_SECRET
#     }
#     try:
#         res = requests.post(url, json=data)
#         res.raise_for_status()
#         token = res.json()["access_token"]
#         print("✅ 접근 토큰 발급 성공")
#         return token
#     except requests.RequestException as e:
#         print(f"❌ 토큰 발급 오류: {e}")
#         return None

# --- 3. API 데이터 수집 함수 (⭐️ 반복 조회 로직 추가) ---
def get_daily_price_history(access_token, symbol, start_date_str, end_date_str):
    """
    지정된 종목의 *전체* 기간 시세를 100일 단위로 반복 조회하여 수집합니다.
    """
    
    all_data = [] # 모든 기간의 데이터를 누적할 리스트
    
    current_end_date = datetime.strptime(end_date_str, "%Y%m%d")
    start_date_dt = datetime.strptime(start_date_str, "%Y%m%d")
    
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
    headers = {
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST03010100"
    }

    while True:
        # API 요청에 사용할 날짜 (문자열)
        query_end_date = current_end_date.strftime("%Y%m%d")
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": symbol,
            "FID_INPUT_DATE_1": start_date_str, # 시작일은 고정
            "FID_INPUT_DATE_2": query_end_date, # 종료일은 변경됨
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0"
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            
            if data['rt_cd'] == '0':
                output2 = data['output2']
                if not output2:
                    # 더 이상 데이터가 없으면 중단
                    print(f"   -> {symbol}: 조회 완료 (데이터 없음)")
                    break 
                    
                # 수집된 데이터 누적
                all_data.extend(output2)
                
                # 수신된 데이터의 가장 이른 날짜(리스트의 마지막 항목)
                earliest_date_str = output2[-1]['stck_bsop_date']
                earliest_date_dt = datetime.strptime(earliest_date_str, "%Y%m%d")
                
                print(f"   -> {symbol}: {earliest_date_str} 까지 100건 수신...")

                # ⭐️ 핵심: 수신된 가장 이른 날짜가 목표 시작일보다 늦으면,
                #          그 날짜의 '하루 전'을 다음 요청의 종료일로 설정
                if earliest_date_dt > start_date_dt:
                    current_end_date = earliest_date_dt - timedelta(days=1)
                    time.sleep(0.1) # API 제한 방지
                else:
                    # 목표 시작일에 도달했으므로 반복 중단
                    print(f"   -> {symbol}: 목표 시작일({start_date_str}) 도달. 수집 완료.")
                    break
            else:
                print(f"❌ [API 오류] {symbol} ({query_end_date}): {data['msg1']}")
                break # 오류 발생 시 해당 종목 중단
                
        except requests.RequestException as e:
            print(f"❌ [HTTP 오류] {symbol} ({query_end_date}): {e}")
            break # 오류 발생 시 해당 종목 중단

    return all_data # 누적된 전체 데이터 반환

# --- 4. 데이터 가공 함수 (이전과 동일) ---
def process_api_responses(response_list):
    """API 응답 딕셔너리 리스트를 받아서 최종 DataFrame으로 병합합니다."""
    ticker_map = {'U001': 'KOSPI'}
    all_price_series = []

    print("\n--- 데이터 가공 시작 ---")
    
    for ticker, output2_list in response_list:
        if not output2_list:
            print(f"경고: {ticker} 데이터가 비어있습니다.")
            continue
            
        temp_df = pd.DataFrame(output2_list)
        
        # ⭐️ 중복 데이터 제거 (반복 조회 시 날짜가 겹칠 수 있음)
        temp_df = temp_df.drop_duplicates(subset=['stck_bsop_date'])
        
        try:
            temp_df = temp_df[['stck_bsop_date', 'stck_clpr']]
        except KeyError:
            print(f"오류: {ticker} 응답에 'stck_bsop_date' 또는 'stck_clpr'가 없습니다.")
            continue

        temp_df['stck_bsop_date'] = pd.to_datetime(temp_df['stck_bsop_date'])
        temp_df = temp_df.set_index('stck_bsop_date')
        temp_df.index.name = 'Date'
        temp_df['stck_clpr'] = pd.to_numeric(temp_df['stck_clpr'])
        column_name = ticker_map.get(ticker, ticker)
        temp_df = temp_df.rename(columns={'stck_clpr': column_name})
        
        all_price_series.append(temp_df)

    if not all_price_series:
        print("❌ 가공할 데이터가 없습니다.")
        return pd.DataFrame()

    final_df = pd.concat(all_price_series, axis=1)
    
    final_columns_order = [
        # '091160', '102960', '091170', '227550', '244580',
        '226490',
        '114260', '363570', 'KOSPI'
    ]
    available_columns = [col for col in final_columns_order if col in final_df.columns]
    final_df = final_df[available_columns]

    final_df = final_df.sort_index(ascending=True)
    final_df = final_df.ffill().bfill()

    print("--- 데이터 가공 완료 ---")
    return final_df

# --- 5. 메인 실행 블록 ---
if __name__ == "__main__":
    
    tickers_to_fetch = [
        # '091160', '102960', '091170', '227550', '244580', # 주식
        '226490',
        '114260', '363570', # 채권
        # '371460', # 현금
        'U001'    # KOSPI
    ]
    
    START_DATE = "20191201"
    END_DATE = "20251107" 
    
    all_responses = [] 
    
    token = KIS_ACCESS_TOKEN

    print(token)
    if token:
        print("--- 기간별 시세 데이터 수집 시작 (100일 단위 반복) ---")
        
        for ticker in tickers_to_fetch:
            print(f"-> {ticker} 전체 기간 데이터 수집 중...")
            
            # ⭐️ 수정된 함수 호출
            full_data_list = get_daily_price_history(token, ticker, START_DATE, END_DATE)
            
            if full_data_list:
                all_responses.append((ticker, full_data_list))
                print(f"✅ [최종 성공] {ticker} (총 {len(full_data_list)}일치)")
            else:
                print(f"❌ [최종 실패] {ticker} 수집 실패")
            
            # (time.sleep은 get_daily_price_history 함수 내부로 이동)
            
        print("--- 전체 데이터 수집 완료 ---")
        print(f"총 {len(all_responses)} / {len(tickers_to_fetch)} 개 자산 수집 성공")

        # --- 6. 데이터 가공 및 CSV 저장 ---
        if all_responses:
            price_df = process_api_responses(all_responses)
            
            file_name = f"ETF_{START_DATE}_{END_DATE}.csv" # 새 이름
            try:
                price_df.to_csv(file_name)
                print(f"\n✅ 전체 기간 데이터가 {file_name} 으로 성공적으로 저장되었습니다.")
                print("--- 저장된 데이터 (앞부분 5줄) ---")
                print(price_df.head())
                print("--- 저장된 데이터 (뒷부분 5줄) ---")
                print(price_df.tail())
            
            except Exception as e:
                print(f"❌ 파일 저장 중 오류 발생: {e}")
        else:
            print("❌ 수집된 데이터가 없어 파일로 저장할 수 없습니다.")
            
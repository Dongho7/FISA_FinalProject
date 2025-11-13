import os
import requests
import json
import time
import pandas as pd
from dotenv import load_dotenv
import sys

# 1. .env 파일 로드 (APP_KEY, APP_SECRET, BASE_URL, KIS_ACCESS_TOKEN)
load_dotenv()
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
BASE_URL = os.getenv("KIS_BASE_URL")
token = os.getenv("KIS_ACCESS_TOKEN")  # .env에서 KIS_ACCESS_TOKEN을 불러옵니다.

# --- (필요한 함수 1: 현재가 조회) ---
def get_stock_price(access_token, symbol):
    """한투 API에서 특정 종목의 가공된 시세 정보를 가져옵니다."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010100"
    }
    symbol_6_digit = symbol.zfill(6)
    params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": symbol_6_digit}
    
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        
        data = res.json()

        if data['rt_cd'] != '0':
            print(f"  [API Error - Price] {symbol}: {data['msg1']}")
            return None

        output = data['output']
        
        market_cap = int(output.get('hts_avls', 0)) * 100_000_000
        change_rate = float(output.get('prdy_ctrt', 0.0))
        sector_name = output.get('bstp_kor_isnm', 'N/A')
        # === [추가됨] 현재가('stck_prpr')를 가져옵니다 ===
        price_str = output.get('stck_prpr', '0').replace(',', '')
        price = int(price_str) if price_str.isdigit() else 0
        
        clean_data = {
            "symbol": symbol_6_digit,            
            "sector": sector_name,  
            "market_cap": market_cap,
            "change_rate": change_rate,
            "price": price  # === [추가됨] "price" 키로 현재가 저장 ===
        }
        
        return clean_data
        
    except requests.exceptions.RequestException as e:
        print(f"  [Request Error - Price] {symbol}: {e}")
        return None
    except Exception as e:
        print(f"  [General Error - Price] {symbol}: {e}")
        return None

# --- (필요한 함수 2: 일봉 차트 조회) ---
def get_stock_history(access_token, symbol):
    """한투 API에서 특정 종목의 일봉 데이터를 가져옵니다."""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice" 
    
    headers = {
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKST01010400"  # 주식일봉차트조회 TR_ID
    }
    
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": symbol.zfill(6),
        "FID_PERIOD_DIV_CODE": "D",  # D: 최근 30거래일
        "FID_ORG_ADJ_PRC": "1"       # 1: 수정주가 반영
    }
    
    res = None
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status() 
        
        data = res.json()

        if data['rt_cd'] != '0':
            print(f"  [API Error - History] {symbol}: {data['msg1']}")
            return None

        output = data.get('output', []) # 'output' 키 사용
        
        history_prices = []
        for day_data in output:
            price = day_data.get('stck_clpr')
            if price:
                history_prices.append(int(price.replace(',', '')))
        
        if not history_prices and data['rt_cd'] == '0':
            print(f"  [Debug - History] {symbol}: API 성공(rt_cd=0)했으나 'output'이 비어있습니다.")
            return [] # 실패가 아닌 빈 리스트 반환

        return history_prices
        
    except requests.exceptions.HTTPError as http_err:
        print(f"  [HTTP Error - History] {symbol}: {http_err}")
        if res is not None:
            print(f"  [Error Raw Response]: {res.text}")
        return None
    except Exception as e:
        print(f"  [General Error - History] {symbol}: {e}")
        return None

# --- (메인 실행 로직) ---
if __name__ == "__main__":
    
    # 1. .env에서 토큰 로드
    if not token:
        print("토큰이 없습니다. .env 파일에 KIS_ACCESS_TOKEN을 설정하세요.")
        sys.exit()
        
    print(f"로드된 토큰 (앞 10자리): {token[:10]}...")

    # 2. KOSPI 200 종목 딕셔너리 로드 (CSV 파일)
    try:
        df = pd.read_csv("data_2200_20251103.csv", dtype={'종목코드': str}, encoding='cp949')
        df['종목코드'] = df['종목코드'].str.zfill(6)
        stock_dict = df.set_index('종목코드')['종목명'].to_dict()
        print(f"CSV 파일 로드 성공. KOSPI 200 종목 {len(stock_dict)}개 확인.")
        
    except Exception as e:
        print(f"CSV 로드 중 오류: {e}")
        sys.exit()

    # 3. 200개 종목 반복 조회 (통합)
    all_stock_data = [] # 최종 데이터를 리스트로 저장
    
    print(f"\nKOSPI 200 통합 데이터 수집을 시작합니다... (총 {len(stock_dict)}개)")

    for i, (symbol, name) in enumerate(stock_dict.items()):
        
        print(f"({i+1}/{len(stock_dict)}) {name}({symbol}) 데이터 조회 중...")
        
        # API 1: 현재가 조회
        stock_data = get_stock_price(token, symbol)
        
        # (!!!) API 속도 제한 (필수)
        time.sleep(0.15) 
        
        if stock_data:
            # API 2: 차트 데이터 조회
            history_data = get_stock_history(token, symbol)
            
            # (!!!) API 속도 제한 (필수)
            time.sleep(0.1)
            
            # 데이터 합치기
            stock_data['name'] = name
            stock_data['history'] = history_data if history_data is not None else []
            
            all_stock_data.append(stock_data)
        else:
            print(f"  -> {name}({symbol}) 현재가 조회 실패. 건너뜁니다.")
            time.sleep(0.15) # 실패 시에도 다음 호출을 위해 딜레이
            
    # 4. 최종 리스트를 JSON 파일로 저장
    output_filename = "heatmap_complete_data.json"
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_stock_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 통합 데이터 수집 완료!")
        print(f"총 {len(all_stock_data)}개의 종목을 '{output_filename}' 파일에 저장했습니다.")
        
    except Exception as e:
        print(f"\n파일 저장 중 오류 발생: {e}")
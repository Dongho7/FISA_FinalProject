import os
import json
import requests
import time
from pykrx import stock # 이 라이브러리가 필요합니다.
from dotenv import load_dotenv
import csv
load_dotenv()
# --- 1. 설정 (사용자 환경에 맞게 수정) ---

# ⚠️ 발급받은 40자리 DART API 인증키를 입력하세요.
DART_API_KEY = os.getenv("dart_api")
if DART_API_KEY is None:
    print("❌ 오류: .env 파일에서 'dart_api' 키를 찾을 수 없습니다.")
    print("   .env 파일이 스크립트와 같은 폴더에 있는지, 변수 이름이 맞는지 확인하세요.")
    exit() # 프로그램 종료
else:
    print(f"✅ API 키 로드 성공 (앞 4자리): {DART_API_KEY[:4]}....")
# 이전에 전처리해서 만든 '조회용 JSON' 파일 경로
LOOKUP_FILE = 'C:\\ITstudy\\15_final_project\\enterprise_information\\기업_조회용.json'

# 재무 데이터를 저장할 폴더 이름
OUTPUT_DIR = 'C:\\ITstudy\\15_final_project\\financial_information\\2025_data'

# 조회할 조건 (예: 2023년 사업보고서)
BSNS_YEAR = '2024'
REPRT_CODE = '11011' # 사업보고서

# DART API URL (다중 회사용)
API_URL = "https://opendart.fss.or.kr/api/fnlttMultiAcnt.json"

# API가 한 번에 허용하는 최대 요청 개수
CHUNK_SIZE = 100

# ---------------------------------------------

def load_lookup_dict():
    """기업_조회용.json 파일을 불러옵니다."""
    try:
        with open(LOOKUP_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 오류: '{LOOKUP_FILE}' 파일을 찾을 수 없습니다.")
        print("이전에 실행한 XML 전처리 코드가 생성한 파일이 맞는지 확인하세요.")
        return None
    

def get_listed_names():
    """
    [수정됨] pykrx를 사용해 KOSPI와 KOSDAQ의 모든 상장사 '이름'을 'set'으로 반환합니다.
    """
    print("🔄 한국거래소(KRX)에서 KOSPI, KOSDAQ 상장사 목록을 불러오는 중...")
    listed_names = set()
    
    try:
        # 1. KOSPI 티커 리스트 가져오기
        kospi_tickers = stock.get_market_ticker_list(market="KOSPI")
        print(f"  - KOSPI 티커 {len(kospi_tickers)}개 확인. 이름으로 변환 중...")
        
        # 2. KOSPI 티커를 이름으로 변환하여 set에 추가
        for ticker in kospi_tickers:
            # get_market_ticker_name 함수로 티커에 해당하는 이름을 조회
            name = stock.get_market_ticker_name(ticker)
            listed_names.add(name)
            
        # 3. KOSDAQ 티커 리스트 가져오기
        kosdaq_tickers = stock.get_market_ticker_list(market="KOSDAQ")
        print(f"  - KOSDAQ 티커 {len(kosdaq_tickers)}개 확인. 이름으로 변환 중...")
        
        # 4. KOSDAQ 티커를 이름으로 변환하여 set에 추가
        for ticker in kosdaq_tickers:
            name = stock.get_market_ticker_name(ticker)
            listed_names.add(name)

        print(f"✅ 총 {len(listed_names)}개의 고유한 상장사 이름을 확인했습니다.")
        return listed_names
        
    except Exception as e:
        print(f"❌ pykrx 라이브러리 실행 중 오류: {e}")
        print("   'pip install pykrx'가 올바르게 설치되었는지 확인하세요.")
        return None

def main():
    # 1. 고유번호 조회용 딕셔너리 로드
    corp_lookup = load_lookup_dict()
    if not corp_lookup:
        return

    # 2. 상장사 이름 목록 로드
    listed_names = get_listed_names()
    if not listed_names:
        return

    # 3. 상장사 이름과 딕셔너리를 매칭하여 '고유번호 리스트' 생성
    target_codes = []
    missed_names = []
    
    for name in listed_names:
        code = corp_lookup.get(name)
        if code:
            target_codes.append(code)
        else:
            # DART XML 원본에 이름이 없거나(예: 스팩) 이름이 미묘하게 다른 경우
            missed_names.append(name)
            
    print(f"✅ DART 고유번호 매칭 성공: {len(target_codes)}개 / 실패: {len(missed_names)}개")

    # 4. 결과 저장 폴더 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("\n--- 🚀 DART API 다중 조회를 시작합니다 (100개씩) ---")

    # 5. 고유번호 리스트를 100개씩 묶어서 API 호출
    for i in range(0, len(target_codes), CHUNK_SIZE):
        chunk_num = (i // CHUNK_SIZE) + 1
        
        # 100개씩 리스트를 자릅니다.
        chunk = target_codes[i:i + CHUNK_SIZE]
        
        # 100개의 고유번호를 콤마(,)로 연결합니다.
        codes_str = ",".join(chunk)
        
        params = {
            'crtfc_key': DART_API_KEY,
            'corp_code': codes_str, # 100개가 콤마로 연결된 문자열
            'bsns_year': BSNS_YEAR,
            'reprt_code': REPRT_CODE
        }
        
        try:
            print(f"  [Chunk {chunk_num}] {len(chunk)}개 기업 데이터 요청 중...")
            response = requests.get(API_URL, params=params)
            response.raise_for_status() # 오류가 있으면 예외 발생
            
            data = response.json()
            
            # 6. 결과 파일 저장
            if data.get('status') == '000':
                output_file = os.path.join(OUTPUT_DIR, f'result_chunk_{chunk_num}.json')
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                print(f"  ➡️  Chunk {chunk_num} 저장 완료: {output_file}")
            else:
                print(f"  ❌ DART API 오류 (Chunk {chunk_num}): {data.get('message')}")

            # DART API는 초당 요청 제한이 있을 수 있으므로, 예의상 잠시 대기
            time.sleep(0.5) 
            
        except requests.exceptions.RequestException as e:
            print(f"  ❌ 네트워크 오류 (Chunk {chunk_num}): {e}")
        except json.JSONDecodeError:
            print(f"  ❌ API 응답 JSON 파싱 오류 (Chunk {chunk_num}): {response.text}")

    print("\n🎉 모든 작업이 완료되었습니다.")

# --- 스크립트 실행 ---
if __name__ == "__main__":
    main()
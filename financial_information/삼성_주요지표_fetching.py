# import os
# import json
# import requests
# import time
# from dotenv import load_dotenv

# # 1. .env 파일에서 API 키 로드
# load_dotenv()
# DART_API_KEY = os.getenv("dart_api")

# if DART_API_KEY is None:
#     print("❌ 오류: .env 파일에서 'dart_api' 키를 찾을 수 없습니다.")
#     exit()
# else:
#     print(f"✅ API 키 로드 성공: {DART_API_KEY[:4]}....")

# # --- 2. 설정 (사용자 요청 기반) ---

# # [신규 API]
# API_URL = "https://opendart.fss.or.kr/api/fnlttCmpnyIndx.json"

# SAMSUNG_CODE = "00126380" # 삼성전자 고유번호

# # [신규] 조회할 지표 코드 (이름을 파일명으로 사용)
# INDICATOR_CODES = {
#     "M210000": "수익성지표",
#     "M220000": "안정성지표",
#     "M230000": "성장성지표",
#     "M240000": "활동성지표"
# }

# # 조회할 연도 (2023, 2024, 2025)
# YEARS_TO_FETCH = list(range(2023, 2026)) 

# # 조회할 보고서 코드
# REPORT_CODES = {
#     "11013": "1분기보고서",
#     "11012": "반기보고서",
#     "11014": "3분기보고서",
#     "11011": "사업보고서"
# }

# # [신규] 저장할 폴더
# OUTPUT_DIR_BASE = "각종지표_시각화_데이터"

# # ---------------------------------------------

# def fetch_and_save_indicator_data(bsns_year, reprt_code, reprt_name, idx_code, idx_name):
#     """
#     지정된 '연도', '보고서', '지표'의 API를 '한 번' 호출하여 파일로 저장합니다.
#     """
    
#     # 연도별로 하위 폴더 생성 (예: .../2023년/)
#     year_output_dir = os.path.join(OUTPUT_DIR_BASE, f"{bsns_year}년")
#     os.makedirs(year_output_dir, exist_ok=True)
    
#     # 파일 이름 (예: .../2023년/삼성전자_2023년_1분기보고서_수익성지표.json)
#     output_file = os.path.join(year_output_dir, f"삼성전자_{bsns_year}년_{reprt_name}_{idx_name}.json")
    
#     # [신규 API] 파라미터 설정
#     params = {
#         'crtfc_key': DART_API_KEY,
#         'corp_code': SAMSUNG_CODE,
#         'bsns_year': str(bsns_year),
#         'reprt_code': reprt_code,
#         'idx_cl_code': idx_code # ⭐️ 지표 구분 코드 추가
#     }

#     print(f"🛠️ API 요청: {bsns_year}년 {reprt_name} ({idx_name})...")

#     try:
#         response = requests.get(API_URL, params=params)
#         response.raise_for_status()
#         data = response.json()

#         if data.get('status') == '000':
#             print(f"  ✅ API 응답 성공! (총 {len(data.get('list', []))}개 지표 항목 수신)")
#             with open(output_file, 'w', encoding='utf-8') as f:
#                 json.dump(data, f, ensure_ascii=False, indent=4)
#             print(f"  🎉 데이터 저장 완료: {output_file}")
            
#         elif data.get('status') == '013': # '013'은 "데이터 없음" 오류
#             print(f"  ⚠️  데이터 없음 (status: 013). (예: 2025년 4분기 보고서)")
#         else:
#             print(f"  ❌ API 오류: {data.get('message')}")

#     except Exception as e:
#         print(f"  ❌ 요청 오류: {e}")

# # --- 메인 실행 ---
# if __name__ == "__main__":
    
#     print(f"--- 삼성전자 주요 재무지표 데이터 수집을 시작합니다 ---")
    
#     # 3중 루프: 연도 -> 분기 -> 지표
#     for year in YEARS_TO_FETCH:
#         print(f"\n--- [{year}년] 데이터 수집 시작 ---")
        
#         for r_code, r_name in REPORT_CODES.items():
            
#             for i_code, i_name in INDICATOR_CODES.items():
                
#                 # API 호출
#                 fetch_and_save_indicator_data(year, r_code, r_name, i_code, i_name)
                
#                 # ⚠️ [필수!] DART API 서버 차단 방지를 위해 1.1초 대기
#                 print("--- 1.1초 대기 ---")
#                 time.sleep(1.1) 
            
#     print("\n🎉 모든 지표 데이터 수집 완료!")
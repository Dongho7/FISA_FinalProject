# import os
# import json
# import requests
# import time
# from dotenv import load_dotenv

# # 1. .env 파일에서 API 키 로드
# load_dotenv()
# DART_API_KEY = os.getenv("dart_api")

# # --- 2. 설정 (사용자 요청 기반) ---

# # [신규 API]
# API_URL = "https://opendart.fss.or.kr/api/alotMatter.json" # 배당에 관한 사항

# SAMSUNG_CODE = "00126380" # 삼성전자 고유번호

# # 조회할 연도
# YEARS_TO_FETCH = list(range(2016, 2026)) 

# # 조회할 보고서 코드
# REPORT_CODES = {
#     "11013": "1분기보고서",
#     "11012": "반기보고서",
#     "11014": "3분기보고서",
#     "11011": "사업보고서"
# }

# # [신규] 저장할 폴더
# OUTPUT_DIR_BASE = "C:\\ITstudy\\15_final_project\\visualization_practice\\backend\\배당"

# # --- 3. 배당 정보 수집 스크립트 ---

# def fetch_dividend_data():
#     """
#     DART API에서 '배당에 관한 사항' 데이터를 연도별/분기별로 수집하여 JSON 파일로 저장합니다.
#     """
#     print("--- 배당 정보 수집 스크립트 시작 ---")
    
#     # 1. API 키 확인
#     if not DART_API_KEY:
#         print("❌ [오류] .env 파일에 'dart_api' 키가 설정되지 않았습니다.")
#         print("스크립트를 중단합니다.")
#         return

#     # 2. 저장 폴더 생성 (없으면)
#     os.makedirs(OUTPUT_DIR_BASE, exist_ok=True)
#     print(f"📂 저장 폴더: {OUTPUT_DIR_BASE}")

#     # 3. 연도별, 보고서별 순회
#     for year in YEARS_TO_FETCH:
#         for rpt_code, rpt_name in REPORT_CODES.items():
            
#             # 4. API 요청 파라미터 설정
#             params = {
#                 'crtfc_key': DART_API_KEY,   # API 인증키
#                 'corp_code': SAMSUNG_CODE, # 회사 고유번호
#                 'bsns_year': str(year),      # 사업 연도
#                 'reprt_code': rpt_code     # 보고서 코드 (1분기, 반기, 3분기, 사업)
#             }

#             print(f"\n[요청] {year}년 {rpt_name} (코드: {rpt_code})...")

#             try:
#                 # 5. API 요청
#                 response = requests.get(API_URL, params=params)
                
#                 # 6. DART API 과부하 방지를 위한 0.5초 대기
#                 time.sleep(0.5) 

#                 if response.status_code == 200:
#                     data = response.json()
                    
#                     # 7. DART API 응답 상태 확인
#                     if data.get('status') == '000':
#                         # 8. 파일명 생성 및 저장
#                         file_name = f"삼성전자_{year}년_{rpt_name}_배당.json"
#                         file_path = os.path.join(OUTPUT_DIR_BASE, file_name)
                        
#                         with open(file_path, 'w', encoding='utf-8') as f:
#                             json.dump(data, f, ensure_ascii=False, indent=4)
                        
#                         print(f"✅ [성공] {file_name} 저장 완료")
                    
#                     else:
#                         # (예: '013' - 해당 데이터가 없습니다.)
#                         # (미래 연도의 3, 4분기는 이 메시지가 뜨는 것이 정상입니다)
#                         print(f"ℹ️ [정보] {year}년 {rpt_name}: {data.get('message')}")

#                 else:
#                     print(f"❌ [HTTP 오류] {year}년 {rpt_name} 요청 실패 (상태 코드: {response.status_code})")
            
#             except requests.exceptions.RequestException as e:
#                 print(f"❌ [네트워크 오류] {year}년 {rpt_name}: {e}")
#             except json.JSONDecodeError:
#                 print(f"❌ [JSON 오류] {year}년 {rpt_name}: 응답 본문을 파싱할 수 없습니다.")

#     print("\n--- 모든 배당 정보 수집 완료 ---")

# if __name__ == "__main__":
#     fetch_dividend_data()

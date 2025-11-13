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
# API_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

# SAMSUNG_CODE = "00126380" # 삼성전자 고유번호
# FS_DIV = "CFS"  # 연결재무제표 (변수명 fs_div -> FS_DIV)

# # 조회할 연도 (2016년부터 2025년까지)
# YEARS_TO_FETCH = list(range(2016, 2026)) 

# # 조회할 보고서 코드
# REPORT_CODES = {
#     "11013": "1분기보고서",
#     "11012": "반기보고서",
#     "11014": "3분기보고서",
#     "11011": "사업보고서"
# }

# # [신규] 저장할 폴더
# OUTPUT_DIR_BASE = "C:\\ITstudy\\15_final_project\\visualization_practice\\backend\\단일회사_전체_재무제표"

# # --- 3. [신규] 모든 결과를 저장할 빈 리스트 ---
# all_financial_data = []

# # --- 4. API 요청 및 데이터 취합 ---

# # 저장할 디렉토리 생성 (없으면)
# os.makedirs(OUTPUT_DIR_BASE, exist_ok=True)

# print("\n🚀 데이터 수집을 시작합니다...")

# for year in YEARS_TO_FETCH:
#     for code, name in REPORT_CODES.items():
        
#         # API 요청 파라미터 설정
#         params = {
#             'crtfc_key': DART_API_KEY,
#             'corp_code': SAMSUNG_CODE,
#             'bsns_year': str(year),
#             'reprt_code': code,
#             'fs_div': FS_DIV
#         }
        
#         print(f"  > {year}년 {name} ({code}) 데이터 요청 중...")
        
#         try:
#             response = requests.get(API_URL, params=params)
#             response.raise_for_status() # 200 OK가 아니면 예외 발생
            
#             data = response.json()
            
#             # DART API 성공 여부 확인
#             if data.get('status') == '000':
#                 # 'list' 키가 있고, 비어있지 않은지 확인
#                 if 'list' in data and data['list']:
#                     print(f"    └ ✅ 성공! {len(data['list'])}개 항목 발견.")
                    
#                     # [핵심 변경] 개별 저장 대신, 전체 리스트에 추가합니다.
#                     # (참고: DART 응답의 'list' 항목에는 이미 bsns_year, reprt_code 등이 포함되어 있습니다)
#                     all_financial_data.extend(data['list'])
#                 else:
#                     print("    └ ⚠️ API는 성공했으나, 해당 기간의 데이터가 없습니다.")
                    
#             elif data.get('status') == '013':
#                 # (013: 해당 자료 없음)은 정상적인 응답입니다.
#                 print(f"    └ ℹ️ 해당 기간({year}년 {name})에 데이터가 없습니다.")
#             else:
#                 print(f"    └ ❌ API 오류: {data.get('message', '알 수 없는 오류')} (status: {data.get('status')})")

#         except requests.exceptions.RequestException as e:
#             print(f"    └ ❌ HTTP 요청 오류: {e}")
#         except json.JSONDecodeError:
#             print("    └ ❌ 응답이 유효한 JSON 형식이 아닙니다. (API 키 만료 또는 서버 오류 가능성)")
        
#         # DART API 정책 준수를 위한 딜레이 (필수)
#         # API는 초당/분당 요청 제한이 있습니다.
#         time.sleep(0.5) # (0.5초 ~ 1초 권장)

# print("\n...데이터 수집 완료...")

# # --- 5. [신규] 취합된 데이터를 하나의 파일로 저장 ---
# if all_financial_data:
#     # 저장할 전체 파일 경로
#     output_filename = os.path.join(OUTPUT_DIR_BASE, f"{SAMSUNG_CODE}_financials_2016-2025_combined.json")
    
#     print(f"\n📊 총 {len(all_financial_data)}개의 재무 항목(레코드)을 수집했습니다.")
#     print(f"💾 데이터를 하나의 파일로 저장합니다: {output_filename}")
    
#     try:
#         with open(output_filename, 'w', encoding='utf-8') as f:
#             # [핵심] 모든 루프가 끝난 후, 단 한 번만 저장합니다.
#             json.dump(all_financial_data, f, ensure_ascii=False, indent=4)
#         print("🎉 저장 완료!")
#     except IOError as e:
#         print(f"❌ 파일 저장 중 오류 발생: {e}")
        
# else:
#     print("ℹ️ 수집된 데이터가 없어 파일을 저장하지 않습니다.")
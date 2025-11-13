import os
import json

# --- 1. 설정 ---
# 1단계(fiscal_data.py)에서 청크 파일이 저장된 폴더
INPUT_DIR = 'C:\\ITstudy\\15_final_project\\financial_information\\2025_data'

# 2단계에서 생성할 최종 통합 파일 이름
FINAL_OUTPUT_FILE = '통합_재무데이터.json'

# 조회를 위한 Key 설정 ('corp_code' 또는 'corp_name')
# 고유번호(corp_code)가 중복이 없고 더 정확합니다.
PRIMARY_KEY = 'corp_code' 
# -----------------

def merge_chunks_to_lookup_file():
    """
    여러 개의 chunk JSON 파일을 읽어,
    조회하기 쉬운 하나의 통합 JSON 딕셔너리로 만듭니다.
    """
    print(f"🛠️ '{INPUT_DIR}' 폴더의 청크 파일 병합을 시작합니다...")
    
    # 최종 통합 딕셔너리
    # 구조: { "고유번호": {재무데이터 리스트}, "고유번호": ... }
    # 예: { "00125178": [ ... ], "00111111": [ ... ] }
    final_lookup_dict = {}

    try:
        # 입력 폴더의 모든 파일을 확인
        file_list = os.listdir(INPUT_DIR)
        
        chunk_files = [f for f in file_list if f.startswith('result_chunk_') and f.endswith('.json')]
        
        if not chunk_files:
            print(f"❌ 오류: '{INPUT_DIR}' 폴더에 'result_chunk_*.json' 파일이 없습니다.")
            return

        print(f"✅ 총 {len(chunk_files)}개의 청크 파일을 발견했습니다.")

        # 각 청크 파일을 순회하며 데이터 추출
        for file_name in chunk_files:
            file_path = os.path.join(INPUT_DIR, file_name)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # API 상태가 정상이(000)고, 'list' 항목이 있는지 확인
            if data.get('status') == '000' and 'list' in data:
                # 'list'는 여러 회사 정보가 담긴 리스트
                for company_data in data['list']:
                    
                    # 설정한 PRIMARY_KEY (예: 'corp_code') 값을 가져옴
                    key = company_data.get(PRIMARY_KEY)
                    
                    if not key:
                        continue # 고유번호가 없는 데이터는 건너뜀

                    # ⚠️ 중요: 한 회사도 '연결(CFS)'과 '개별(OFS)' 2개가 있을 수 있음
                    # 따라서 딕셔너리의 값을 리스트([])로 만들어 차곡차곡 쌓아줍니다.
                    if key not in final_lookup_dict:
                        final_lookup_dict[key] = [] # 새 리스트 생성
                    
                    final_lookup_dict[key].append(company_data)

        # --- 3. 최종 통합 파일 저장 ---
        print(f"\n✅ 총 {len(final_lookup_dict)}개 기업의 데이터를 통합했습니다.")
        
        output_path = os.path.join(INPUT_DIR, FINAL_OUTPUT_FILE)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_lookup_dict, f, ensure_ascii=False, indent=4)
            
        print(f"🎉 최종 통합 파일 저장 완료: {output_path}")

    except FileNotFoundError:
        print(f"❌ 오류: 입력 폴더 '{INPUT_DIR}'를 찾을 수 없습니다.")
    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {e}")

# --- 메인 실행 ---
if __name__ == "__main__":
    merge_chunks_to_lookup_file()
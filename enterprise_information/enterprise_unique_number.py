import xml.etree.ElementTree as ET
import csv
import json
import os

# --- 1. 설정 ---
# ⚠️ 실제 XML 파일 경로와 이름으로 변경하세요.
XML_FILE_PATH = 'C:\\ITstudy\\15_final_project\\CORPCODE.xml'

# ⚠️ 저장될 파일 이름 (원하는 대로 변경 가능)
CSV_OUTPUT_FILE = '기업정보_전체.csv'
JSON_OUTPUT_FILE = '기업_조회용.json'
# -----------------

def parse_large_xml(xml_file, csv_file, json_file):
    """
    대용량 XML 파일을 순차적으로 읽어(iterparse)
    CSV 파일과 조회용 JSON 파일로 변환합니다.
    """
    print(f"🛠️ '{xml_file}' 파일 전처리를 시작합니다...")
    
    # 조회용 딕셔너리 (Key: 기업명, Value: 번호)
    lookup_dict = {}
    
    # CSV에 저장할 데이터 (헤더 포함)
    csv_data = []
    headers = ['corp_code', 'corp_name', 'corp_eng_name', 'modify_date']
    csv_data.append(headers)

    try:
        # iterparse를 사용하여 파일을 순차적으로 읽습니다.
        # 'end' 이벤트(예: </list>)가 발생할 때마다 처리합니다.
        context = ET.iterparse(xml_file, events=('end',))
        
        # 파일의 루트 요소를 가져옵니다. (메모리 관리를 위해 필요)
        _, root = next(context)

        processed_count = 0
        
        for event, elem in context:
            # 우리가 관심 있는 태그는 <list> 입니다.
            if elem.tag == 'list':
                
                # <list> 태그 안의 각 필드 텍스트를 추출합니다.
                code = elem.findtext('corp_code')
                name = elem.findtext('corp_name')
                eng_name = elem.findtext('corp_eng_name')
                date = elem.findtext('modify_date')
                
                if code and name:
                    # 1. CSV용 데이터 추가
                    csv_data.append([code, name, eng_name, date])
                    
                    # 2. 조회용 딕셔너리 추가
                    # (혹시 모를 앞뒤 공백 제거)
                    lookup_dict[name.strip()] = code.strip()

                    processed_count += 1
                
                # 중요: 처리 완료된 요소를 메모리에서 해제합니다!
                elem.clear()

        # 루트 요소도 해제
        root.clear()

        print(f"✅ 총 {processed_count} 개의 <list> 항목 처리를 완료했습니다.")
        
        # --- 2. CSV 파일로 저장 ---
        with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
        print(f"✅ CSV 파일 저장 완료: {csv_file}")

        # --- 3. JSON 파일로 저장 ---
        with open(json_file, 'w', encoding='utf-8') as f:
            # 딕셔너리를 JSON 형식으로 예쁘게 저장
            json.dump(lookup_dict, f, ensure_ascii=False, indent=4)
        print(f"✅ 조회용 JSON 파일 저장 완료: {JSON_OUTPUT_FILE}")

    except FileNotFoundError:
        print(f"❌ 오류: '{xml_file}' 파일을 찾을 수 없습니다. 파일 이름을 확인해 주세요.")
    except ET.ParseError as e:
        print(f"❌ 오류: XML 파싱 중 오류가 발생했습니다: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류가 발생했습니다: {e}")

# --- 메인 실행 ---
parse_large_xml(XML_FILE_PATH, CSV_OUTPUT_FILE, JSON_OUTPUT_FILE)
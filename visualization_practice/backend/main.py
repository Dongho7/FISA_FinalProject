import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import math
from functools import lru_cache # ⭐️ 캐싱을 위한 import
import re # ⭐️ 이 라인이 있어야 합니다.
# --- 1. FastAPI 앱 생성 및 CORS 설정 ---
app = FastAPI()
origins = ["http://localhost", "http://localhost:5500", "http://127.0.0.1:5500"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. 설정 ---
YEARS_TO_FETCH = list(range(2016, 2026)) 

# ⭐️ processed_data 기본 경로 (부모 폴더)
BASE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), # backend 폴더의 부모로 이동
    "processed_data"
)

# 계정 '바구니' (기존과 동일)
ACCOUNT_BASKET = {
    'revenue': ['매출액', '수익(매출액)', '영업수익', '매출'],
    'op_income': ['영업이익', '영업이익(손실)'],
    'cogs': ['매출원가'],
    'sga': ['판매비와관리비', '판매비와 관리비', '판매비와관리비', '판매비', '관리비', '연구개발비'],
    'interest_exp': ['이자비용', '금융원가', '금융비용'],
    'net_income': ['당기순이익', '당기순이익(손실)', '분기순이익', '분기순이익(손실)', '반기순이익', '반기의 순이익', '당기의 순이익', '분기의 순이익']
}
REPORT_NAMES = {
    'q1': "1분기보고서", 'q2': "반기보고서", 'q3': "3분기보고서", 'annual': "사업보고서"
}
# ⭐️ [신규] 보고서 코드를 라벨로 변환하기 위한 맵
REPORT_CODE_MAP = {
    "11013": "Q1",
    "11012": "Q2",
    "11014": "Q3",
    "11011": "ANNUAL"
}

# --- 3. 헬퍼 함수 (공통) ---
def clean_amount(amount_str):
    if not amount_str: return 0
    # ⭐️ [수정] '-' 문자도 0으로 처리
    if amount_str == '-': return 0
    return int(amount_str.replace(',', ''))

# ⭐️⭐️⭐️ [핵심 수정 v4.4] ⭐️⭐️⭐️
# ⭐️ [수정 v4.8] "XI." 같은 로마자 접두사 제거
# ⭐️ [수정 v5.0] 한글/영문 단어는 남겨두고, 숫자/로마자/기호 접두사만 제거
# ⭐️ [수정 v5.2] 항목을 1개 찾는 대신, 바스켓의 모든 항목을 '합산'하여 '숫자'를 반환
def get_account_item(account_list, name_basket, amount_type='thstrm_amount'):
    """
    [수정] sj_div가 'IS'/'CIS'이고 name_basket에 포함되는
    모든 항목의 합계(sum)를 반환합니다.
    """
    if account_list is None:
        return 0 # ⭐️ 합산을 위해 None 대신 0 반환
    
    total_amount = 0
    found_items = set() # ⭐️ 중복 합산 방지 (예: '판매비'와 '판매비와관리비'가 둘 다 있을 경우)

    for item in account_list:
        raw_name = item.get('account_nm', "").strip()
        item_name = re.sub(r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫIVX\d\(\)\[\]\.\s]*', '', raw_name).strip()
        sj_div = item.get('sj_div') 
        
        if sj_div in ('IS', 'CIS') and item_name in name_basket:
            # ⭐️ sga 바스켓처럼 여러 항목이 합산되어야 하는 경우
            # (예: '판매비' + '관리비' + '연구개발비')
            if item_name not in found_items:
                total_amount += clean_amount(item.get(amount_type))
                found_items.add(item_name)
                
            # ⭐️ revenue/op_income/cogs처럼 단일 항목인 경우
            # (만약 '매출'과 '매출액'이 모두 존재하면 큰일 -> 바스켓 순서가 중요)
            # -> 이 로직은 EP1에서 처리하도록 단순 합산만 반환
            pass 
            
    # ⭐️ [수정] 단일 item이 아닌, 합계 숫자(int)를 반환
    return total_amount

# ⭐️ [수정] dividends 파일 구조(List[Dict])에 맞춘 헬퍼
# ⭐️ [수정] dividends 헬퍼 (v4.5) - 이름 '바스켓'을 받도록 수정
def get_dividend_json_value(file_path, se_basket, stock_knd=None):
    """ 
    [수정] 지정된 배당 JSON 파일(List[Dict])에서 값을 추출합니다.
    [수정 4.5] se_name(str) 대신 se_basket(list)를 받습니다.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f) # ⭐️ data_list (리스트)로 로드
        
        if not isinstance(data_list, list):
            raise FileNotFoundError # ⭐️ 리스트가 아니면 오류

        # ⭐️ [수정] 바스켓에 있는 이름을 순회
        for name_to_find in se_basket:
            for item in data_list:
                if item.get('se') == name_to_find: # ⭐️ 일치하는 이름 발견
                    if stock_knd:
                        if item.get('stock_knd') == stock_knd:
                            return float(item.get('thstrm', '0').replace(',', '').replace('-', '0'))
                    else:
                        return float(item.get('thstrm', '0').replace(',', '').replace('-', '0'))
        
        # ⭐️ 바스켓에 있는 이름을 모두 찾지 못한 경우
        print(f"     INFO (Helper): {file_path}에서 {se_basket} 항목을 찾지 못함.")
        return 0.0 # ⭐️ None 대신 0.0 반환 (EP7 로직 유지)
    
    except FileNotFoundError:
        return None # 파일이 없는 것은 None (루프 중단)
    except Exception as e:
        print(f"    ❌ 헬퍼 함수 오류 {file_path}: {e}")
        return None

# ⭐️ [수정 v4.8]
def get_cf_account_item(account_list, name_basket):
    if account_list is None:
        return None
    for item in account_list:
        raw_name = item.get('account_nm', "").strip()
        # ⭐️ [수정] A-Z, 가-힣 제거 -> 숫자, 로마자, 기호 접두사만 제거
        item_name = re.sub(r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫIVX\d\(\)\[\]\.\s]*', '', raw_name).strip()
        
        if item.get('sj_div') == 'CF' and item_name in name_basket:
            return item
    return None

# ⭐️ [수정 v4.8] "XI." 같은 로마자 접두사 제거
# ⭐️ [수정 v5.0] 한글/영문 단어는 남겨두고, 숫자/로마자/기호 접두사만 제거
def get_bs_account_item(account_list, name_basket):
    if account_list is None:
        return None
    for item in account_list:
        raw_name = item.get('account_nm', "").strip()
        # ⭐️ [수정] A-Z, 가-힣 제거 -> 숫자, 로마자, 기호 접두사만 제거
        item_name = re.sub(r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫIVX\d\(\)\[\]\.\s]*', '', raw_name).strip()
        
        if item.get('sj_div') == 'BS' and item_name in name_basket:
            return item
    return None
# --- 4. [신규] 동적 데이터 로딩 헬퍼 ---

@lru_cache(maxsize=None) 
def get_company_name(corp_code: str) -> str:
    # [수정 없음] 이 함수는 정상 동작했습니다.
    try:
        corp_dir = os.path.join(BASE_DATA_DIR, corp_code)
        if not os.path.exists(corp_dir):
            return None 

        for f_name in os.listdir(corp_dir):
            if f_name.endswith("_financials_combined.json"):
                company_name = f_name.replace("_financials_combined.json", "")
                print(f"✅ (Helper): {corp_code} -> {company_name} 이름 매핑 성공")
                return company_name
                
        print(f"❌ (Helper): {corp_dir}에서 ..._financials_combined.json 파일 못찾음")
        return None
    except Exception as e:
        print(f"❌ (Helper) get_company_name 오류: {e}")
        return None

# ⭐️ [대폭 수정] _financials_combined.json 파일의 실제 구조(거대 List)에 맞춤
@lru_cache(maxsize=None)
def load_combined_financials(corp_code: str, company_name: str):
    """
    [수정 4.0]
    _financials_combined.json (거대 List[Dict]) 파일을 로드합니다.
    이 리스트를 다른 함수들이 사용하기 편한 딕셔너리로 변환합니다.
    
    반환 형태:
    {
        "2016.Q1": {"status": "000", "list": [...]},
        "2016.Q2": {"status": "000", "list": [...]}
    }
    """
    if not company_name:
        return None
        
    file_path = os.path.join(
        BASE_DATA_DIR, 
        corp_code, 
        f"{company_name}_financials_combined.json"
    )
    
    print(f"🛠️ (Helper): '{file_path}' 로드 중...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            flat_list = json.load(f) # ⭐️ 1. 거대 리스트로 로드

        if not isinstance(flat_list, list):
             print(f"❌ (Helper): Combined financials가 리스트가 아닙니다! (경로: {file_path})")
             return None

        # ⭐️ 2. 리스트를 딕셔너리로 재가공
        #    {"2016.Q1": [...], "2016.Q2": [...]}
        temp_dict = {}
        for item in flat_list:
            bsns_year = item.get('bsns_year')
            reprt_code = item.get('reprt_code')
            
            if not bsns_year or not reprt_code:
                continue

            # 보고서 코드를 라벨(예: "2016.Q1")로 변환
            q_label = REPORT_CODE_MAP.get(reprt_code)
            if not q_label:
                continue
                
            label = f"{bsns_year}.{q_label}"
            
            # 딕셔너리에 해당 라벨이 없으면 빈 리스트 생성
            if label not in temp_dict:
                temp_dict[label] = []
            
            # 해당 라벨의 리스트에 항목 추가
            temp_dict[label].append(item)

        # ⭐️ 3. 다른 함수들이 사용할 수 있도록 "가짜" DART 응답 딕셔너리 생성
        final_combined_data = {}
        for label, item_list in temp_dict.items():
            final_combined_data[label] = {
                "status": "000",
                "message": "정상 (pre-processed)",
                "list": item_list # ⭐️ 재가공된 리스트
            }
            
        if not final_combined_data:
             print(f"❌ (Helper): {file_path} 파일에서 유효한 보고서 데이터를 추출하지 못했습니다.")
             return None

        print(f"✅ (Helper): Combined financials (List -> Dict) 변환 성공! (총 {len(final_combined_data)}개 분기)")
        return final_combined_data

    except FileNotFoundError:
        print(f"❌ (Helper): Combined financials 파일 없음: {file_path}")
        return None
    except Exception as e:
        print(f"❌ (Helper): Combined financials 로딩/변환 오류: {e}")
        return None


#### --------------------------- 엔드포인트별 처리 함수 ------------------------------- ####

# 엔드포인트 1: 콤보 차트 ---
# 엔드포인트 1: 콤보 차트 ---
def process_timeseries_data(combined_data: dict):
    """ 
    [수정 v5.2] 헬퍼 함수가 '합산된 숫자'를 반환하도록 변경됨에 따라
    item.get('thstrm_amount') 로직을 수정합니다.
    """
    
    chart_data = {"labels": []} 
    for key in ACCOUNT_BASKET.keys(): chart_data[key] = [] 

    print(f"🛠️ (EP1): IS 데이터 전처리를 시작합니다 (v5.2)...")
    
    if not combined_data:
        print("❌ (EP1) G: combined_data가 없습니다.")
        return {}
        
    try:
        last_q3_data_list = None 
        
        sorted_labels = sorted(combined_data.keys(), key=lambda x: (
            int(x.split('.')[0]), 
            int(x.split('.')[1].replace('Q','').replace('ANNUAL','4')) 
        ))

        for label in sorted_labels:
            data = combined_data[label]
            
            if data.get('status') != '000':
                if "Q1" in label: last_q3_data_list = None 
                continue
            
            data_list = data.get('list', [])
            chart_data["labels"].append(label)
            
            if "ANNUAL" in label.upper(): 
                if last_q3_data_list is None:
                    for key in ACCOUNT_BASKET.keys():
                        chart_data[key].append(None)
                    continue
                    
                for key, name_basket in ACCOUNT_BASKET.items():
                    # ⭐️ [수정] 헬퍼가 '합산된 숫자'를 반환
                    annual_total = get_account_item(data_list, name_basket, 'thstrm_amount')
                    
                    # ⭐️ [수정] Q3 누적액은 thstrm_add_amount 또는 thstrm_amount
                    # (get_account_item은 amount_type을 지정할 수 없으므로, 로직 수정)
                    
                    # Q3 누적액 합산 (v5.1 로직 부활)
                    q3_cumulative = 0
                    for item_q3 in last_q3_data_list:
                        raw_name = item_q3.get('account_nm', "").strip()
                        item_name = re.sub(r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫIVX\d\(\)\[\]\.\s]*', '', raw_name).strip()
                        sj_div = item_q3.get('sj_div')
                        
                        if sj_div in ('IS', 'CIS') and item_name in name_basket:
                            q3_cum_val_str = item_q3.get('thstrm_add_amount')
                            if not q3_cum_val_str:
                                 q3_cum_val_str = item_q3.get('thstrm_amount')
                            q3_cumulative += clean_amount(q3_cum_val_str)

                    chart_data[key].append(annual_total - q3_cumulative)
            
            else: # Q1, Q2, Q3
                for key, name_basket in ACCOUNT_BASKET.items():
                    # ⭐️ [수정] 헬퍼가 '합산된 숫자'를 반환
                    # ⭐️ thstrm_add_amount가 없는 데이터(고려아연)는 thstrm_amount가 분기값임
                    amount_q = get_account_item(data_list, name_basket, 'thstrm_amount')
                    chart_data[key].append(amount_q if amount_q != 0 else None) # ⭐️ 0이면 None 처리
            
            if "Q3" in label.upper():
                last_q3_data_list = data_list
            elif "Q1" in label.upper():
                 last_q3_data_list = None
    
    except Exception as e:
        print(f"❌ (EP1) 전처리 중 치명적 오류 발생: {e}")
        return {}

    # 최종 타입 변환
    final_data = {}
    try:
        for key, value_list in chart_data.items():
            if key == "labels": 
                final_data[key] = value_list
            else: 
                final_data[key] = [int(v) if v is not None else None for v in value_list]
    except Exception as e:
        print(f"❌ (EP1) 최종 타입 변환 오류: {e}")
        return {}
        
    print(f"✅ (EP1) IS 데이터 전처리 완료!")
    return final_data

# -엔드포인트 2: 매출 구성비중 차트 ---
def process_revenue_ratio_data(preprocessed_data_combo):
    # [수정 없음]
    chart_data = {"labels": [], "cogs_ratio": [], "sga_ratio": [], "op_income_ratio": []}
    if not preprocessed_data_combo or 'labels' not in preprocessed_data_combo: return {}
    try:
        labels = preprocessed_data_combo['labels']
        revenues = preprocessed_data_combo['revenue']
        cogs_list = preprocessed_data_combo['cogs']
        sga_list = preprocessed_data_combo['sga']
        op_income_list = preprocessed_data_combo['op_income']
        
        for i in range(len(labels)):
            revenue = revenues[i]
            if not revenue or revenue <= 0:
                chart_data["labels"].append(labels[i])
                chart_data["cogs_ratio"].append(None)
                chart_data["sga_ratio"].append(None)
                chart_data["op_income_ratio"].append(None)
                continue
            
            cogs_r = (cogs_list[i] / revenue) * 100 if cogs_list[i] is not None else None
            sga_r = (sga_list[i] / revenue) * 100 if sga_list[i] is not None else None
            op_income_r = (op_income_list[i] / revenue) * 100 if op_income_list[i] is not None else None
            
            chart_data["labels"].append(labels[i])
            chart_data["cogs_ratio"].append(cogs_r)
            chart_data["sga_ratio"].append(sga_r)
            chart_data["op_income_ratio"].append(op_income_r)
        
        final_data = {
            "labels": chart_data["labels"],
            "cogs_ratio": [float(v) if v is not None else None for v in chart_data["cogs_ratio"]],
            "sga_ratio": [float(v) if v is not None else None for v in chart_data["sga_ratio"]],
            "op_income_ratio": [float(v) if v is not None else None for v in chart_data["op_income_ratio"]]
        }
        print(f"✅ (EP2): 매출 구성비중 전처리 완료!")
        return final_data
    except Exception as e:
        print(f"❌ (EP2) 전처리 중 치명적 오류 발생: {e}")
        return {}

# -엔드포인트 3: 이자보상배율(ICR) 차트 ---
def process_icr_data(preprocessed_data_combo):
    # [수정 없음]
    chart_data = {"labels": [], "icr_ratio": []}
    if not preprocessed_data_combo or 'labels' not in preprocessed_data_combo: return {}
    try:
        labels = preprocessed_data_combo['labels']
        op_income_list = preprocessed_data_combo['op_income']
        interest_exp_list = preprocessed_data_combo['interest_exp']
        icr_list = []
        for i in range(len(labels)):
            op_income = op_income_list[i]
            interest_exp = interest_exp_list[i]
            
            if op_income is None or interest_exp is None:
                icr_list.append(None)
                continue
                
            icr = None 
            if interest_exp > 0:
                icr = op_income / interest_exp
            elif op_income <= 0:
                icr = 0.0
            icr_list.append(icr) 
        
        final_list = [float(v) if v is not None else None for v in icr_list]
        final_data = {"labels": labels, "icr_ratio": final_list}
        print(f"✅ (EP3): 이자보상배율 전처리 완료!")
        return final_data
    except Exception as e:
        print(f"❌ (EP3) 전처리 중 치명적 오류 발생: {e}")
        return {}

# 엔드포인트 4: 당기순이익 차트 ---
def process_net_income_data(preprocessed_data_combo):
    # [수정 없음]
    chart_data = {"labels": [], "net_income": [], "net_income_ratio": []}
    if not preprocessed_data_combo or 'labels' not in preprocessed_data_combo: return {}
    try:
        labels = preprocessed_data_combo['labels']
        revenues = preprocessed_data_combo['revenue']
        net_income_list = preprocessed_data_combo['net_income']
        ratio_list = []
        for i in range(len(labels)):
            revenue = revenues[i]
            net_income = net_income_list[i]
            
            if net_income is None or revenue is None:
                ratio_list.append(None)
                continue

            ratio = None
            if revenue > 0:
                ratio = (net_income / revenue) * 100
            elif net_income <= 0:
                ratio = 0.0
            ratio_list.append(ratio)

        final_data = {
            "labels": labels,
            "net_income": [int(v) if v is not None else None for v in net_income_list],
            "net_income_ratio": [float(v) if v is not None else None for v in ratio_list]
        }
        print(f"✅ (EP4): 당기순이익+순이익률 전처리 완료!")
        return final_data
    except Exception as e:
        print(f"❌ (EP4) 전처리 중 치명적 오류 발생: {e}")
        return {}

# 엔드포인트 5: 성장성 지표 
# ⭐️ [대폭 수정] major_indicators 파일 구조(List[Dict])에 맞춤
def process_growth_data(corp_code: str, company_name: str):
    """ 
    [수정] '..._성장성지표.json' (List[Dict]) 파일을 동적으로 읽습니다.
    """
    chart_data = {"labels": [], "yoy_revenue_growth": [], "yoy_op_income_growth": []}
    
    YEARS = list(range(2023, 2026)) 
    REPORTS = {
        'q1': "1분기보고서", 'q2': "반기보고서", 'q3': "3분기보고서", 'annual': "사업보고서"
    }

    print(f"🛠️ (EP5): 성장성 지표({company_name}) 데이터 전처리를 시작합니다...")
    try:
        stop_processing = False
        for year in YEARS:
            if stop_processing: break
            year_str = str(year)
            
            data_dir = os.path.join(BASE_DATA_DIR, corp_code, "major_indicators")

            for q_key, q_name in REPORTS.items():
                if year == 2023 and (q_key == 'q1' or q_key == 'q2'):
                    continue 

                file_name = f"{company_name}_{year_str}년_{q_name}_성장성지표.json"
                file_path = os.path.join(data_dir, file_name)

                revenue_growth_val = None
                op_income_growth_val = None

                try:
                    # ⭐️ [수정] data_list (List[Dict])로 로드
                    with open(file_path, 'r', encoding='utf-8') as f: 
                        data_list = json.load(f)
                    
                    if not isinstance(data_list, list):
                        raise FileNotFoundError 

                    # ⭐️ [수정] data.get('status'), data['list'] 접근 제거
                    for item in data_list:
                        idx_nm = item.get('idx_nm')
                        idx_val = item.get('idx_val')
                        
                        if idx_nm == '매출액증가율(YoY)' and idx_val:
                            revenue_growth_val = float(idx_val)
                        elif idx_nm == '영업이익증가율(YoY)' and idx_val:
                            op_income_growth_val = float(idx_val)
                    
                    chart_data["labels"].append(f"{year_str}.{q_key.upper()}")
                    chart_data["yoy_revenue_growth"].append(revenue_growth_val)
                    chart_data["yoy_op_income_growth"].append(op_income_growth_val)
                
                except FileNotFoundError:
                    print(f"     INFO (EP5): '{file_name}' 없음. 처리를 중단합니다.")
                    stop_processing = True
                    break 
                    
    except Exception as e:
        print(f"❌ (EP5) 전처리 중 치명적 오류 발생: {e}")
        return {}

    final_data = {
        "labels": chart_data["labels"],
        "yoy_revenue_growth": [float(v) if v is not None else None for v in chart_data["yoy_revenue_growth"]],
        "yoy_op_income_growth": [float(v) if v is not None else None for v in chart_data["yoy_op_income_growth"]]
    }
    print(f"✅ (EP5): 성장성 지표 전처리 완료!")
    return final_data

# 엔드포인트 6: 안정성 지표
# ⭐️ [대폭 수정] major_indicators 파일 구조(List[Dict])에 맞춤
def process_stability_data(corp_code: str, company_name: str):
    """ 
    [수정] '..._안정성지표.json' (List[Dict]) 파일을 동적으로 읽습니다.
    """
    chart_data = {"labels": [], "debt_ratio": [], "current_ratio": []}
    
    YEARS = list(range(2023, 2026)) 
    REPORTS = {
        'q1': "1분기보고서", 'q2': "반기보고서", 'q3': "3분기보고서", 'annual': "사업보고서"
    }

    print(f"🛠️ (EP6): 안정성 지표({company_name}) 데이터 전처리를 시작합니다...")
    try:
        stop_processing = False
        for year in YEARS:
            if stop_processing: break
            year_str = str(year)
            
            data_dir = os.path.join(BASE_DATA_DIR, corp_code, "major_indicators")

            for q_key, q_name in REPORTS.items():
                if year == 2023 and (q_key == 'q1' or q_key == 'q2'):
                    continue 

                file_name = f"{company_name}_{year_str}년_{q_name}_안정성지표.json"
                file_path = os.path.join(data_dir, file_name)

                debt_ratio_val = None
                current_ratio_val = None

                try:
                    # ⭐️ [수정] data_list (List[Dict])로 로드
                    with open(file_path, 'r', encoding='utf-8') as f: 
                        data_list = json.load(f)
                        
                    if not isinstance(data_list, list):
                        raise FileNotFoundError 

                    # ⭐️ [수정] data.get('status'), data['list'] 접근 제거
                    for item in data_list:
                        idx_nm = item.get('idx_nm')
                        idx_val = item.get('idx_val')
                        
                        if idx_nm == '부채비율' and idx_val:
                            debt_ratio_val = float(idx_val)
                        elif idx_nm == '유동비율' and idx_val:
                            current_ratio_val = float(idx_val)
                    
                    chart_data["labels"].append(f"{year_str}.{q_key.upper()}")
                    chart_data["debt_ratio"].append(debt_ratio_val)
                    chart_data["current_ratio"].append(current_ratio_val)
                
                except FileNotFoundError:
                    print(f"     INFO (EP6): '{file_name}' 없음. 처리를 중단합니다.")
                    stop_processing = True
                    break 
                    
    except Exception as e:
        print(f"❌ (EP6) 전처리 중 치명적 오류 발생: {e}")
        return {}

    final_data = {
        "labels": chart_data["labels"],
        "debt_ratio": [float(v) if v is not None else None for v in chart_data["debt_ratio"]],
        "current_ratio": [float(v) if v is not None else None for v in chart_data["current_ratio"]]
    }
    print(f"✅ (EP6): 안정성 지표 전처리 완료!")
    return final_data

# 엔드포인트 7: 배당성향 + EPS/DPS 차트
# 엔드포인트 7: 배당성향 + EPS/DPS 차트
def process_dividend_summary_data(corp_code: str, company_name: str):
    """ 
    [수정 4.5] 헬퍼 함수에 이름 '바스켓'(리스트)을 전달합니다.
    """
    chart_data = {"labels": [], "eps": [], "dps": [], "payout_ratio": []}
    
    YEARS = list(range(2016, 2026)) 
    REPORTS_ORDER = [('q1', '1분기보고서'), ('q2', '반기보고서'), ('q3', '3분기보고서'), ('annual', '사업보고서')]

    print(f"🛠️ (EP7): EPS/DPS/배당성향({company_name}) 데이터 전처리를 시작합니다...")
    try:
        stop_processing = False
        
        # ⭐️ [수정] EPS, DPS, 배당성향 이름 바스켓 정의
        EPS_BASKET = ["주당순이익(원)", "(연결)주당순이익(원)", "기본주당이익(원)", "분기주당순이익(원)"]
        DPS_BASKET = ["주당 현금배당금(원)", "(연결)주당 현금배당금(원)", "보통주 주당 현금배당금(원)"]
        PAYOUT_BASKET = ["(연결)현금배당성향(%)"]
        
        for year in YEARS:
            if stop_processing: break
            year_str = str(year)
            
            last_eps = 0.0
            last_dps = 0.0

            for q_key, q_name in REPORTS_ORDER:
                
                if year == 2023 and q_key == 'q1':
                    continue

                dividend_dir = os.path.join(BASE_DATA_DIR, corp_code, "dividends")
                dividend_file = f"{company_name}_{year_str}년_{q_name}_배당.json"
                dividend_path = os.path.join(dividend_dir, dividend_file)
                
                # Q2는 Q3 계산을 위한 베이스로만 사용 (차트에 포함 안됨)
                if year == 2023 and q_key == 'q2':
                    # ⭐️ [수정] 바스켓 전달
                    total_eps_q2 = get_dividend_json_value(dividend_path, EPS_BASKET)
                    total_dps_q2 = get_dividend_json_value(dividend_path, DPS_BASKET, "보통주")

                    if total_eps_q2 is None or total_dps_q2 is None:
                        print(f"     INFO (EP7): 2023 Q3 계산을 위한 '{q_name}' 배당 base 파일 없음. 중단합니다.")
                        stop_processing = True
                        break 
                    
                    last_eps = total_eps_q2
                    last_dps = total_dps_q2
                    continue 

                # Q3, ANNUAL 계산
                # ⭐️ [수정] 바스켓 전달
                total_eps = get_dividend_json_value(dividend_path, EPS_BASKET) 
                total_dps = get_dividend_json_value(dividend_path, DPS_BASKET, "보통주")
                payout_ratio_val = get_dividend_json_value(dividend_path, PAYOUT_BASKET)

                if total_eps is None or total_dps is None or payout_ratio_val is None:
                    print(f"     INFO (EP7): '{q_name}' 데이터 없음. 처리를 중단합니다.")
                    stop_processing = True
                    break
                
                quarterly_eps = total_eps - last_eps
                quarterly_dps = total_dps - last_dps

                chart_data["labels"].append(f"{year_str}.{q_key.upper()}")
                chart_data["eps"].append(quarterly_eps)
                chart_data["dps"].append(quarterly_dps)
                chart_data["payout_ratio"].append(payout_ratio_val) 

                last_eps = total_eps
                last_dps = total_dps
                    
    except Exception as e:
        print(f"❌ (EP7) 전처리 중 치명적 오류 발생: {e}")
        return {}

    final_data = {
        "labels": chart_data["labels"],
        "eps": [float(v) if v is not None else None for v in chart_data["eps"]],
        "dps": [float(v) if v is not None else None for v in chart_data["dps"]],
        "payout_ratio": [float(v) if v is not None else None for v in chart_data["payout_ratio"]]
    }
    print(f"✅ (EP7): EPS/DPS/배당성향 전처리 완료!")
    return final_data

## [EP9 TTM 수정] 현금흐름(FCF) 차트
def process_cash_flow_data(combined_data: dict):
    """ 
    [수정 4.3] main.py의 원본 TTM 로직을 main2.py 환경에 맞게 정확히 재구현
    - (버그1) thstrm_add_amount 대신 thstrm_amount를 사용하도록 수정
    - (버그2) 매년 누적값을 0으로 리셋하도록 수정
    """
    
    # 계정 바구니
    CF_ACCOUNT_BASKET = {
        'ocf': ['영업활동으로 인한 현금흐름', '영업활동현금흐름', '영업활동 현금흐름'],
        'icf': ['투자활동으로 인한 현금흐름', '투자활동현금흐름', '투자활동 현금흐름'],
        'ffcf': ['재무활동으로 인한 현금흐름', '재무활동현금흐름', '재무활동 현금흐름'],
        'capex_t': ['유형자산의 취득', '유형자산의취득', '유형자산의 취득액'],
        'capex_i': ['무형자산의 취득', '무형자산의취득', '무형자산의 취득액']
    }
    
    # 1단계: TTM 계산을 위한 '진짜 분기별' 값을 임시 저장
    quarterly_data = {
        "labels": [], "fcf": [], "ocf": [], "icf": [], "ffcf": [], "capex":[]
    }

    print(f"🛠️ (EP9 TTM): 1. 분기별 현금흐름 계산 중 (main.py 로직 v4.3)...")
    
    if not combined_data:
        print("❌ (EP9): combined_data가 없습니다.")
        return {}
        
    try:
        last_cumulative_values = {} # 직전 분기의 '누적' 값을 저장

        # ⭐️ [수정] 날짜순으로 정렬 (2016.Q1, 2016.Q2 ... 2016.ANNUAL)
        sorted_labels = sorted(combined_data.keys(), key=lambda x: (
            int(x.split('.')[0]), 
            # Q1=1, Q2=2, Q3=3, ANNUAL=4로 변환하여 정렬
            int(x.split('.')[1].replace('Q','').replace('ANNUAL','4')) 
        ))

        current_year = ""
        for label in sorted_labels:
            data = combined_data[label]
            year = label.split('.')[0]

            # ⭐️ [수정] 연도가 바뀌면 누적값 리셋 (main.py 로직)
            if year != current_year:
                last_cumulative_values = {k: 0 for k in quarterly_data.keys() if k != 'labels'}
                current_year = year
            
            if data.get('status') != '000':
                continue

            data_list = data.get('list', [])
            
            current_report_values = {} 
            # ⭐️ Q1만 분기, 나머지는 누적 (main.py 로직)
            is_cumulative_report = ("Q2" in label or "Q3" in label or "ANNUAL" in label)

            for key, name_basket in CF_ACCOUNT_BASKET.items():
                item = get_cf_account_item(data_list, name_basket)
                # ⭐️ [수정] main.py 로직과 동일하게 *무조건* thstrm_amount 사용
                val_str = item.get('thstrm_amount') if item else '0'
                current_report_values[key] = clean_amount(val_str)
            
            quarterly_values = {}
            
            # (누적) CAPEX / FCF 계산
            capex_val = current_report_values.get('capex_t', 0) + current_report_values.get('capex_i', 0)
            fcf_val = current_report_values.get('ocf', 0) - capex_val

            if not is_cumulative_report: # Q1 (1분기)
                quarterly_values = current_report_values 
                quarterly_values['capex'] = capex_val
                quarterly_values['fcf'] = fcf_val
            else: # Q2, Q3, ANNUAL (2,3,4 분기)
                # ⭐️ (이번 누적) - (직전 누적) = (이번 분기 값)
                quarterly_values['capex'] = capex_val - last_cumulative_values.get('capex', 0)
                quarterly_values['fcf'] = fcf_val - last_cumulative_values.get('fcf', 0)
                quarterly_values['ocf'] = current_report_values.get('ocf', 0) - last_cumulative_values.get('ocf', 0)
                quarterly_values['icf'] = current_report_values.get('icf', 0) - last_cumulative_values.get('icf', 0)
                quarterly_values['ffcf'] = current_report_values.get('ffcf', 0) - last_cumulative_values.get('ffcf', 0)
            
            # [1단계] 분기별 데이터 임시 저장
            quarterly_data["labels"].append(label)
            for key in quarterly_data.keys():
                if key != 'labels':
                    quarterly_data[key].append(quarterly_values.get(key, 0))

            # '다음 분기' 계산을 위해 '직전 분기 누적' 값 업데이트 (main.py 로직)
            if not is_cumulative_report: # Q1
                last_cumulative_values['capex'] = quarterly_values.get('capex', 0)
                last_cumulative_values['fcf'] = quarterly_values.get('fcf', 0)
                last_cumulative_values['ocf'] = quarterly_values.get('ocf', 0)
                last_cumulative_values['icf'] = quarterly_values.get('icf', 0)
                last_cumulative_values['ffcf'] = quarterly_values.get('ffcf', 0)
            else: # Q2, Q3, ANNUAL
                last_cumulative_values['capex'] = capex_val
                last_cumulative_values['fcf'] = fcf_val
                last_cumulative_values['ocf'] = current_report_values.get('ocf', 0)
                last_cumulative_values['icf'] = current_report_values.get('icf', 0)
                last_cumulative_values['ffcf'] = current_report_values.get('ffcf', 0)

    except Exception as e:
        print(f"❌ (EP9 TTM) 1. 분기별 처리 중 치명적 오류 발생: {e}")
        return {}

    # --- 2단계: TTM (Trailing Twelve Months) 계산 ---
    print(f"🛠️ (EP9 TTM): 2. TTM (직전 12개월 합산) 계산 중...")
    
    ttm_chart_data = {
        "labels": [], "fcf": [], "ocf": [], "icf": [], "ffcf": [], "capex": []
    }
    
    q_labels = quarterly_data["labels"]
    q_fcf = quarterly_data["fcf"]
    q_ocf = quarterly_data["ocf"]
    q_icf = quarterly_data["icf"]
    q_ffcf = quarterly_data["ffcf"]
    q_capex = quarterly_data["capex"]

    if len(q_labels) < 4:
        print(f"     ❌ (EP9 TTM): TTM 계산을 위한 최소 분기(4개)가 부족합니다.")
        return quarterly_data 

    for i in range(3, len(q_labels)):
        ttm_fcf = sum(filter(None, q_fcf[i-3:i+1]))
        ttm_ocf = sum(filter(None, q_ocf[i-3:i+1]))
        ttm_icf = sum(filter(None, q_icf[i-3:i+1]))
        ttm_ffcf = sum(filter(None, q_ffcf[i-3:i+1]))
        ttm_capex = sum(filter(None, q_capex[i-3:i+1]))
        
        ttm_chart_data["labels"].append(q_labels[i])
        ttm_chart_data["fcf"].append(ttm_fcf)
        ttm_chart_data["ocf"].append(ttm_ocf)
        ttm_chart_data["icf"].append(ttm_icf)
        ttm_chart_data["ffcf"].append(ttm_ffcf)
        ttm_chart_data["capex"].append(ttm_capex)

    final_data = {}
    try:
        for key, value_list in ttm_chart_data.items():
            if key == "labels": 
                final_data[key] = value_list
            else: 
                final_data[key] = [int(v) if v is not None else None for v in value_list]
    except Exception as e:
        print(f"❌ (EP9 TTM) 3. 최종 타입 변환 오류: {e}")
        return {}
        
    print(f"✅ (EP9 TTM): TTM 현금흐름 전처리 완료!")
    return final_data

# [신규 10번] 자산의 구성 (재무상태표) 차트 
def process_balance_sheet_data(combined_data: dict):
    # [수정 없음]
    BS_ACCOUNT_BASKET = {
        'total_assets': ['자산총계'],
        'current_assets': ['유동자산'],
        'non_current_assets': ['비유동자산'],
    }
    
    chart_data = {
        "labels": [],
        "total_assets": [],
        "current_assets": [],
        "non_current_assets": [],
    }

    print(f"🛠️ (EP10): 분기별 재무상태표(BS) 자산 데이터 전처리를 시작합니다...")
    
    if not combined_data:
        print("❌ (EP10): combined_data가 없습니다.")
        return {}
        
    try:
        for label, data in combined_data.items():
            try:
                if data.get('status') != '000':
                    raise FileNotFoundError
                
                data_list = data.get('list', [])
                chart_data["labels"].append(label)
                
                for bs_key, name_basket in BS_ACCOUNT_BASKET.items():
                    item = get_bs_account_item(data_list, name_basket)
                    amount = clean_amount(item.get('thstrm_amount')) if item else 0
                    chart_data[bs_key].append(amount)

            except FileNotFoundError:
                print(f"     INFO (EP10): {label} 재무상태표 데이터 없음. 건너뜁니다.")
                continue
            except Exception as e:
                print(f"     ❌ (EP10): {label} 로드 중 오류: {e}")
                continue

    except Exception as e:
        print(f"❌ (EP10) 전처리 중 치명적 오류 발생: {e}")
        return {}

    final_data = {}
    try:
        for key, value_list in chart_data.items():
            if key == "labels": 
                final_data[key] = value_list
            else: 
                final_data[key] = [int(v) if v is not None else None for v in value_list]
    except Exception as e:
        print(f"❌ (EP10) 최종 타입 변환 오류: {e}")
        return {}
        
    print(f"✅ (EP10): 분기별 재무상태표(BS) 자산 전처리 완료!")
    return final_data

# [신규 12번] 자본의 구성 (재무상태표) 차트
def process_equity_data(combined_data: dict):
    # [수정] 자본총계 바스켓 추가 (고려아연 샘플용)
    BS_EQUITY_BASKET = {
        'total_equity': ['지배기업의 소유주에게 귀속되는 자본', '지배기업 소유주지분', '자본총계'], 
        'capital_stock': ['자본금'],
        'capital_surplus': ['자본잉여금', '주식발행초과금'],
        'retained_earnings': ['이익잉여금', '이익잉여금(결손금)'],
        'other_capital': ['기타자본구성요소', '기타자본항목'] 
    }
    
    chart_data = {
        "labels": [],
        "total_equity": [],
        "capital_stock": [],
        "capital_surplus": [],
        "retained_earnings": [],
        "other_capital": [],
    }

    print(f"🛠️ (EP12): 분기별 자본구성(BS) 데이터 전처리를 시작합니다...")
    
    if not combined_data:
        print("❌ (EP12): combined_data가 없습니다.")
        return {}

    try:
        for label, data in combined_data.items():
            try:
                if data.get('status') != '000':
                    raise FileNotFoundError
                
                data_list = data.get('list', [])
                chart_data["labels"].append(label)
                
                for bs_key, name_basket in BS_EQUITY_BASKET.items():
                    item = get_bs_account_item(data_list, name_basket)
                    amount = clean_amount(item.get('thstrm_amount')) if item else 0
                    chart_data[bs_key].append(amount)

            except FileNotFoundError:
                print(f"     INFO (EP12): {label} 재무상태표 데이터 없음. 건너뜁니다.")
                continue
            except Exception as e:
                print(f"     ❌ (EP12): {label} 로드 중 오류: {e}")
                continue
                
    except Exception as e:
        print(f"❌ (EP12) 전처리 중 치명적 오류 발생: {e}")
        return {}

    final_data = {}
    try:
        for key, value_list in chart_data.items():
            if key == "labels": 
                final_data[key] = value_list
            else: 
                final_data[key] = [int(v) if v is not None else None for v in value_list]
    except Exception as e:
        print(f"❌ (EP12) 최종 타입 변환 오류: {e}")
        return {}
        
    print(f"✅ (EP12): 분기별 자본구성(BS) 전처리 완료!")
    return final_data

# [신규 13번] 부채 현황 (재무상태표) 차트
def process_liabilities_data(combined_data: dict):
    # [수정 없음]
    BS_LIABILITIES_BASKET = {
        'total_liabilities': ['부채총계'],
        'current_liabilities': ['유동부채'],
        'non_current_liabilities': ['비유동부채'],
    }
    
    chart_data = {
        "labels": [],
        "total_liabilities": [],
        "current_liabilities": [],
        "non_current_liabilities": [],
    }

    print(f"🛠️ (EP13): 분기별 부채현황(BS) 데이터 전처리를 시작합니다...")
    
    if not combined_data:
        print("❌ (EP13): combined_data가 없습니다.")
        return {}
        
    try:
        for label, data in combined_data.items():
            try:
                if data.get('status') != '000':
                    raise FileNotFoundError
                
                data_list = data.get('list', [])
                chart_data["labels"].append(label)
                
                for bs_key, name_basket in BS_LIABILITIES_BASKET.items():
                    item = get_bs_account_item(data_list, name_basket)
                    amount = clean_amount(item.get('thstrm_amount')) if item else 0
                    chart_data[bs_key].append(amount)

            except FileNotFoundError:
                print(f"     INFO (EP13): {label} 재무상태표 데이터 없음. 건너뜁니다.")
                continue
            except Exception as e:
                print(f"     ❌ (EP13): {label} 로드 중 오류: {e}")
                continue

    except Exception as e:
        print(f"❌ (EP13) 전처리 중 치명적 오류 발생: {e}")
        return {}

    final_data = {}
    try:
        for key, value_list in chart_data.items():
            if key == "labels": 
                final_data[key] = value_list
            else: 
                final_data[key] = [int(v) if v is not None else None for v in value_list]
    except Exception as e:
        print(f"❌ (EP13) 최종 타입 변환 오류: {e}")
        return {}
        
    print(f"✅ (EP13): 분기별 부채현황(BS) 전처리 완료!")
    return final_data



# --- 9. API 라우팅 (동적 엔드포인트) ---
# [수정 없음] API 라우팅 로직은 그대로 사용합니다.

def get_common_data(corp_code: str):
    """ 공통 헬퍼: corp_code로 이름과 재무 데이터를 로드 """
    company_name = get_company_name(corp_code)
    if not company_name:
        return None, None, {"status": "error", "message": f"기업 코드({corp_code})에 해당하는 폴더나 _financials_combined.json 파일을 찾을 수 없습니다."}
        
    combined_data = load_combined_financials(corp_code, company_name)
    if not combined_data:
        return company_name, None, {"status": "error", "message": f"Combined financials 데이터 로드 실패: {corp_code}"}
        
    return company_name, combined_data, None

# 엔드포인트 1
@app.get("/api/{corp_code}/quarterly-data") 
async def get_quarterly_data(corp_code: str):
    _, combined_data, error_response = get_common_data(corp_code)
    if error_response: return error_response
    
    data = process_timeseries_data(combined_data)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 2
@app.get("/api/{corp_code}/revenue-ratio") 
async def get_revenue_ratio(corp_code: str):
    _, combined_data, error_response = get_common_data(corp_code)
    if error_response: return error_response
    
    base_data = process_timeseries_data(combined_data)
    if not base_data: return {"status": "error", "message": "기본 데이터 가공 실패"}
    
    data = process_revenue_ratio_data(base_data)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 3
@app.get("/api/{corp_code}/icr") 
async def get_icr(corp_code: str):
    _, combined_data, error_response = get_common_data(corp_code)
    if error_response: return error_response

    base_data = process_timeseries_data(combined_data)
    if not base_data: return {"status": "error", "message": "기본 데이터 가공 실패"}

    data = process_icr_data(base_data)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 4
@app.get("/api/{corp_code}/net-income") 
async def get_net_income(corp_code: str):
    _, combined_data, error_response = get_common_data(corp_code)
    if error_response: return error_response

    base_data = process_timeseries_data(combined_data)
    if not base_data: return {"status": "error", "message": "기본 데이터 가공 실패"}

    data = process_net_income_data(base_data)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 5
@app.get("/api/{corp_code}/growth") 
async def get_growth(corp_code: str):
    company_name = get_company_name(corp_code)
    if not company_name:
        return {"status": "error", "message": f"기업 코드({corp_code})에 해당하는 기업 이름을 찾을 수 없습니다."}
        
    data = process_growth_data(corp_code, company_name)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 6    
@app.get("/api/{corp_code}/stability") 
async def get_stability(corp_code: str):
    company_name = get_company_name(corp_code)
    if not company_name:
        return {"status": "error", "message": f"기업 코드({corp_code})에 해당하는 기업 이름을 찾을 수 없습니다."}

    data = process_stability_data(corp_code, company_name)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 7    
@app.get("/api/{corp_code}/dividend-summary") 
async def get_dividend_summary(corp_code: str):
    company_name = get_company_name(corp_code)
    if not company_name:
        return {"status": "error", "message": f"기업 코드({corp_code})에 해당하는 기업 이름을 찾을 수 없습니다."}
        
    data = process_dividend_summary_data(corp_code, company_name)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 9 (8번은 EP9과 병합됨)
@app.get("/api/{corp_code}/cash-flow-ttm")
async def get_cash_flow_ttm(corp_code: str):
    _, combined_data, error_response = get_common_data(corp_code)
    if error_response: return error_response

    data = process_cash_flow_data(combined_data)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 10    
@app.get("/api/{corp_code}/balance-sheet")  
async def get_balance_sheet(corp_code: str):
    _, combined_data, error_response = get_common_data(corp_code)
    if error_response: return error_response
    
    data = process_balance_sheet_data(combined_data)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 12    
@app.get("/api/{corp_code}/equity-composition")
async def get_equity_composition(corp_code: str):
    _, combined_data, error_response = get_common_data(corp_code)
    if error_response: return error_response

    data = process_equity_data(combined_data)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}

# 엔드포인트 13    
@app.get("/api/{corp_code}/liabilities")
async def get_liabilities(corp_code: str):
    _, combined_data, error_response = get_common_data(corp_code)
    if error_response: return error_response
    
    data = process_liabilities_data(combined_data)
    if data: return {"status": "success", "data": data}
    else: return {"status": "error", "message": "데이터 가공 실패"}
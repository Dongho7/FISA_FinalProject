import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import csv 
import math

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

# [수정] DART 재무제표 데이터 폴더 경로
DART_DATA_DIR = os.path.join(
    os.path.dirname(__file__), 
    "단일회사_전체_재무제표" # ⭐️ 새 상위 폴더
)

# [수정] 시가총액 CSV 파일 경로
MARKET_CAP_CSV_PATH = os.path.join(
    os.path.dirname(__file__), 
    '시가총액', 
    '삼성전자_분기별_시가총액_2016Q1_2025Q2.csv'
)

# [수정] 새로운 "주요 재무지표" 폴더 경로
INDICATORS_BASE_DIR = os.path.join(
    os.path.dirname(__file__), 
    "단일회사_주요_재무지표"
)

DIVIDEND_DIR_BASE = os.path.join(
    os.path.dirname(__file__),
    "배당"
)

# 계정 '바구니'
ACCOUNT_BASKET = {
    'revenue': ['매출액', '수익(매출액)', '영업수익'],
    'op_income': ['영업이익', '영업이익(손실)'],
    'cogs': ['매출원가'],
    'sga': ['판매비와관리비', '판매비와 관리비'],
    'interest_exp': ['이자비용', '금융원가', '금융비용'],
    'net_income': ['당기순이익', '당기순이익(손실)', '분기순이익', '분기순이익(손실)', '반기순이익']
}
REPORT_NAMES = {
    'q1': "1분기보고서", 'q2': "반기보고서", 'q3': "3분기보고서", 'annual': "사업보고서"
}

# --- 3. 헬퍼 함수 (공통) ---
def clean_amount(amount_str):
    if not amount_str: return 0
    return int(amount_str.replace(',', ''))

def get_account_item(account_list, name_basket):
    for item in account_list:
        item_name = item.get('account_nm', "").strip()
        if item.get('sj_div') == 'IS' and item_name in name_basket:
            return item
    return None

def load_market_cap_from_csv(csv_path):
    lookup = {}
    print(f"🛠️ 백엔드: 시가총액 CSV 파일 로드 중... ({csv_path})")
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row.get('date')
                market_cap = row.get('market_cap')
                if date and market_cap:
                    lookup[date] = float(market_cap) 
        print(f"✅ 백엔드: 시가총액 CSV 로드 성공! (총 {len(lookup)}개 분기)")
        return lookup
    except FileNotFoundError:
        print(f"❌ [치명적 오류] 시가총액 CSV 파일 없음: {csv_path}")
        return {}
    except Exception as e:
        print(f"❌ [치명적 오류] 시가총액 CSV 로딩 오류: {e}")
        return {}

# 배당 JSON에서 특정 값(누적)을 추출하는 헬퍼
def get_dividend_json_value(file_path, se_name, stock_knd=None):
    """ 지정된 배당 JSON 파일에서 특정 항목(se)의 당기(thstrm) 값을 추출합니다. """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not (data.get('status') == '000' and 'list' in data):
            raise FileNotFoundError # 데이터가 없는 경우 (013)

        for item in data['list']:
            if item.get('se') == se_name:
                # '주당 현금배당금'처럼 stock_knd(보통주/우선주) 구분이 필요한 경우
                if stock_knd:
                    if item.get('stock_knd') == stock_knd:
                        return float(item.get('thstrm', '0').replace(',', ''))
                # (연결)주당순이익처럼 stock_knd 구분이 없는 경우
                else:
                    return float(item.get('thstrm', '0').replace(',', ''))
        return 0.0 # 항목은 있으나 값이 없는 경우
    
    except FileNotFoundError:
        # print(f"    INFO: {file_path} 파일 없음 (다음 분기 데이터)")
        return None # 파일 자체가 없는 경우 (None을 반환해야 루프 중단)
    except Exception as e:
        print(f"    ❌ 헬퍼 함수 오류 {file_path}: {e}")
        return None

# CF 항목을 찾는 헬퍼
def get_cf_account_item(account_list, name_basket):
    """ 현금흐름표(CF) 항목을 찾습니다. """
    for item in account_list:
        item_name = item.get('account_nm', "").strip()
        # ⭐️ sj_div == 'CF' (현금흐름표)
        if item.get('sj_div') == 'CF' and item_name in name_basket:
            return item
    return None

# ⭐️ [신규] 재무상태표(BS)용 헬퍼 함수
def get_bs_account_item(account_list, name_basket):
    """ 재무상태표(BS) 항목을 찾습니다. """
    for item in account_list:
        item_name = item.get('account_nm', "").strip()
        # ⭐️ sj_div == 'BS' (재무상태표)
        if item.get('sj_div') == 'BS' and item_name in name_basket:
            return item
    return None


#### --------------------------- 엔드포인트 ------------------------------- ####


# 엔드포인트 1: 콤보 차트 ---
def process_timeseries_data(market_cap_lookup):
    """ DART 데이터와 시가총액 딕셔너리를 병합합니다. """
    chart_data = {"labels": [], "market_cap": []} 
    for key in ACCOUNT_BASKET.keys(): chart_data[key] = [] 

    print(f"🛠️ 백엔드 (EP1): DART + 시가총액 데이터 전처리를 시작합니다...")
    try:
        for year in YEARS_TO_FETCH:
            year_str = str(year)
            # ⭐️ [수정] 새 폴더 경로 반영
            year_dir = os.path.join(DART_DATA_DIR, f"{year_str}년") 

            # --- Q1 처리 ---
            date_key_q1 = f"{year_str}-03-31"
            file_path_q1 = os.path.join(year_dir, f"삼성전자_{year_str}년_{REPORT_NAMES['q1']}_CFS.json")
            try:
                with open(file_path_q1, 'r', encoding='utf-8') as f: data_q1 = json.load(f)
                if data_q1.get('status') != '000': raise FileNotFoundError
                chart_data["labels"].append(f"{year_str}.1Q")
                for key, name_basket in ACCOUNT_BASKET.items():
                    item = get_account_item(data_q1.get('list', []), name_basket)
                    chart_data[key].append(clean_amount(item.get('thstrm_amount')) if item else None) # ⭐️ 0 대신 None
                chart_data["market_cap"].append(market_cap_lookup.get(date_key_q1, None))
            except FileNotFoundError:
                print(f"    INFO (EP1): {year_str} 1분기 파일 없음. 중단합니다.")
                break 

            # --- Q2 처리 ---
            date_key_q2 = f"{year_str}-06-30"
            file_path_q2 = os.path.join(year_dir, f"삼성전자_{year_str}년_{REPORT_NAMES['q2']}_CFS.json")
            try:
                with open(file_path_q2, 'r', encoding='utf-8') as f: data_q2 = json.load(f)
                if data_q2.get('status') != '000': raise FileNotFoundError
                chart_data["labels"].append(f"{year_str}.2Q")
                for key, name_basket in ACCOUNT_BASKET.items():
                    item = get_account_item(data_q2.get('list', []), name_basket)
                    chart_data[key].append(clean_amount(item.get('thstrm_amount')) if item else None)
                chart_data["market_cap"].append(market_cap_lookup.get(date_key_q2, None))
            except FileNotFoundError:
                print(f"    INFO (EP1): {year_str} 2분기 파일 없음. 중단합니다.")
                break 

            # --- Q3 처리 ---
            date_key_q3 = f"{year_str}-09-30"
            file_path_q3 = os.path.join(year_dir, f"삼성전자_{year_str}년_{REPORT_NAMES['q3']}_CFS.json")
            try:
                with open(file_path_q3, 'r', encoding='utf-8') as f: data_q3 = json.load(f)
                if data_q3.get('status') != '000': raise FileNotFoundError
                chart_data["labels"].append(f"{year_str}.3Q")
                for key, name_basket in ACCOUNT_BASKET.items():
                    item = get_account_item(data_q3.get('list', []), name_basket)
                    chart_data[key].append(clean_amount(item.get('thstrm_amount')) if item else None)
                chart_data["market_cap"].append(market_cap_lookup.get(date_key_q3, None))
            except FileNotFoundError:
                print(f"    INFO (EP1): {year_str} 3분기 파일 없음. 중단합니다.")
                break 
            
            # --- Q4 처리 (계산) ---
            date_key_q4 = f"{year_str}-12-31"
            # ⭐️ [오류 수정] Q4 파일 경로에 'year_dir' 추가
            file_path_annual = os.path.join(year_dir, f"삼성전자_{year_str}년_{REPORT_NAMES['annual']}_CFS.json")
            try:
                with open(file_path_annual, 'r', encoding='utf-8') as f: data_annual = json.load(f)
                if data_annual.get('status') != '000': raise FileNotFoundError
                if 'data_q3' not in locals() or data_q3 is None: raise FileNotFoundError 
                chart_data["labels"].append(f"{year_str}.4Q")
                for key, name_basket in ACCOUNT_BASKET.items():
                    item_annual = get_account_item(data_annual.get('list', []), name_basket)
                    item_q3_cumulative = get_account_item(data_q3.get('list', []), name_basket)
                    if item_annual and item_q3_cumulative:
                        annual_total = clean_amount(item_annual.get('thstrm_amount'))
                        q3_cumulative = clean_amount(item_q3_cumulative.get('thstrm_add_amount'))
                        chart_data[key].append(annual_total - q3_cumulative)
                    else: chart_data[key].append(None)
                chart_data["market_cap"].append(market_cap_lookup.get(date_key_q4, None))
            except FileNotFoundError:
                print(f"    INFO (EP1): {year_str} 4분기 파일 없음. 중단합니다.")
                break
    except Exception as e:
        print(f"❌ (EP1) 전처리 중 치명적 오류 발생: {e}")
        return {}

    # 최종 타입 변환 (JSON 호환성)
    final_data = {}
    try:
        for key, value_list in chart_data.items():
            if key == "labels": 
                final_data[key] = value_list
            elif key == "market_cap": 
                final_data[key] = [float(v) if v is not None else None for v in value_list]
            else: 
                final_data[key] = [int(v) if v is not None else None for v in value_list]
    except Exception as e:
        print(f"❌ (EP1) 최종 타입 변환 오류: {e}")
        return {}
    print(f"✅ 백엔드 (EP1): DART+CSV 전처리 완료!")
    return final_data

# -엔드포인트 2: 매출 구성비중 차트 ---
def process_revenue_ratio_data():
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
            # ⭐️ None 체크 추가
            if not revenue or revenue <= 0:
                chart_data["labels"].append(labels[i])
                chart_data["cogs_ratio"].append(None)
                chart_data["sga_ratio"].append(None)
                chart_data["op_income_ratio"].append(None)
                continue
            
            # ⭐️ None 체크 추가
            cogs_r = (cogs_list[i] / revenue) * 100 if cogs_list[i] is not None else None
            sga_r = (sga_list[i] / revenue) * 100 if sga_list[i] is not None else None
            op_income_r = (op_income_list[i] / revenue) * 100 if op_income_list[i] is not None else None
            
            chart_data["labels"].append(labels[i])
            chart_data["cogs_ratio"].append(cogs_r)
            chart_data["sga_ratio"].append(sga_r)
            chart_data["op_income_ratio"].append(op_income_r)
        
        # ⭐️ 최종 타입 변환 (float/None)
        final_data = {
            "labels": chart_data["labels"],
            "cogs_ratio": [float(v) if v is not None else None for v in chart_data["cogs_ratio"]],
            "sga_ratio": [float(v) if v is not None else None for v in chart_data["sga_ratio"]],
            "op_income_ratio": [float(v) if v is not None else None for v in chart_data["op_income_ratio"]]
        }
        print(f"✅ 백엔드 (EP2): 매출 구성비중 전처리 완료!")
        return final_data
    except Exception as e:
        print(f"❌ (EP2) 전처리 중 치명적 오류 발생: {e}")
        return {}

# -엔드포인트 3: 이자보상배율(ICR) 차트 ---
def process_icr_data():
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
            
            # ⭐️ None 체크 추가
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
        print(f"✅ 백엔드 (EP3): 이자보상배율 전처리 완료!")
        return final_data
    except Exception as e:
        print(f"❌ (EP3) 전처리 중 치명적 오류 발생: {e}")
        return {}

# 엔드포인트 4: 당기순이익 차트 ---
def process_net_income_data():
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
            
            # ⭐️ None 체크 추가
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
        print(f"✅ 백엔드 (EP4): 당기순이익+순이익률 전처리 완료!")
        return final_data
    except Exception as e:
        print(f"❌ (EP4) 전처리 중 치명적 오류 발생: {e}")
        return {}

# 엔드포인트 5: 성장성 지표 
def process_growth_data():
    """ '삼성전자_성장성지표' 폴더에서 '매출액증가율(YoY)'과 '영업이익증가율(YoY)'을 추출합니다. """
    chart_data = {"labels": [], "yoy_revenue_growth": [], "yoy_op_income_growth": []}
    
    YEARS = list(range(2023, 2026)) # 2023년부터
    REPORTS = {
        'q1': "1분기보고서", 'q2': "반기보고서", 'q3': "3분기보고서", 'annual': "사업보고서"
    }

    print(f"🛠️ 백엔드 (EP6): 성장성 지표 데이터 전처리를 시작합니다...")
    try:
        stop_processing = False
        for year in YEARS:
            if stop_processing: break
            year_str = str(year)
            
            # ⭐️ [중요] 성장성 지표 폴더 경로
            data_dir = os.path.join(INDICATORS_BASE_DIR, "삼성전자_성장성지표")

            for q_key, q_name in REPORTS.items():
                if year == 2023 and (q_key == 'q1' or q_key == 'q2'):
                    continue # 2023년 3분기부터 시작

                # ⭐️ [중요] 성장성 지표 파일 이름
                file_name = f"삼성전자_{year_str}년_{q_name}_성장성지표.json"
                file_path = os.path.join(data_dir, file_name)

                revenue_growth_val = None
                op_income_growth_val = None

                try:
                    with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
                    if not (data.get('status') == '000' and 'list' in data):
                        raise FileNotFoundError 

                    for item in data['list']:
                        idx_nm = item.get('idx_nm')
                        idx_val = item.get('idx_val')
                        
                        # ⭐️ 추출할 지표 이름
                        if idx_nm == '매출액증가율(YoY)' and idx_val:
                            revenue_growth_val = float(idx_val)
                        elif idx_nm == '영업이익증가율(YoY)' and idx_val:
                            op_income_growth_val = float(idx_val)
                    
                    chart_data["labels"].append(f"{year_str}.{q_key.upper()}")
                    chart_data["yoy_revenue_growth"].append(revenue_growth_val)
                    chart_data["yoy_op_income_growth"].append(op_income_growth_val)
                
                except FileNotFoundError:
                    # 2025년 2분기까지만 데이터가 있으므로, 2025년 3분기 파일이 없을 때 중단되는 것은 정상입니다.
                    print(f"    INFO (EP6): '{file_name}' 없음. 처리를 중단합니다.")
                    stop_processing = True
                    break 
                    
    except Exception as e:
        print(f"❌ (EP6) 전처리 중 치명적 오류 발생: {e}")
        return {}

    final_data = {
        "labels": chart_data["labels"],
        "yoy_revenue_growth": [float(v) if v is not None else None for v in chart_data["yoy_revenue_growth"]],
        "yoy_op_income_growth": [float(v) if v is not None else None for v in chart_data["yoy_op_income_growth"]]
    }
    print(f"✅ 백엔드 (EP6): 성장성 지표 전처리 완료!")
    return final_data

# 엔드포인트 6: 안정성 지표
def process_stability_data():
    """ '삼성전자_안정성지표' 폴더에서 '부채비율'과 '유동비율'을 추출합니다. """
    chart_data = {"labels": [], "debt_ratio": [], "current_ratio": []}
    
    YEARS = list(range(2023, 2026)) # 2023년부터
    REPORTS = {
        'q1': "1분기보고서", 'q2': "반기보고서", 'q3': "3분기보고서", 'annual': "사업보고서"
    }

    print(f"🛠️ 백엔드 (EP7): 안정성 지표 데이터 전처리를 시작합니다...")
    try:
        stop_processing = False
        for year in YEARS:
            if stop_processing: break
            year_str = str(year)
            
            # ⭐️ [중요] 안정성 지표 폴더 경로
            data_dir = os.path.join(INDICATORS_BASE_DIR, "삼성전자_안정성지표")

            for q_key, q_name in REPORTS.items():
                if year == 2023 and (q_key == 'q1' or q_key == 'q2'):
                    continue # 2023년 3분기부터 시작

                # ⭐️ [중요] 안정성 지표 파일 이름
                file_name = f"삼성전자_{year_str}년_{q_name}_안정성지표.json"
                file_path = os.path.join(data_dir, file_name)

                debt_ratio_val = None
                current_ratio_val = None

                try:
                    with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
                    if not (data.get('status') == '000' and 'list' in data):
                        raise FileNotFoundError 

                    for item in data['list']:
                        idx_nm = item.get('idx_nm')
                        idx_val = item.get('idx_val')
                        
                        # ⭐️ 추출할 지표 이름
                        if idx_nm == '부채비율' and idx_val:
                            debt_ratio_val = float(idx_val)
                        elif idx_nm == '유동비율' and idx_val:
                            current_ratio_val = float(idx_val)
                    
                    chart_data["labels"].append(f"{year_str}.{q_key.upper()}")
                    chart_data["debt_ratio"].append(debt_ratio_val)
                    chart_data["current_ratio"].append(current_ratio_val)
                
                except FileNotFoundError:
                    print(f"    INFO (EP7): '{file_name}' 없음. 처리를 중단합니다.")
                    stop_processing = True
                    break 
                    
    except Exception as e:
        print(f"❌ (EP7) 전처리 중 치명적 오류 발생: {e}")
        return {}

    final_data = {
        "labels": chart_data["labels"],
        "debt_ratio": [float(v) if v is not None else None for v in chart_data["debt_ratio"]],
        "current_ratio": [float(v) if v is not None else None for v in chart_data["current_ratio"]]
    }
    print(f"✅ 백엔드 (EP7): 안정성 지표 전처리 완료!")
    return final_data

# 엔드포인트 7: 배당성향 + EPS/DPS 차트(활동성)
def process_dividend_summary_data():
    """ 
    '배당' 폴더를 읽어 분기별 EPS, DPS, 배당성향(%) 데이터를 결합합니다.
    (활동성지표 폴더는 더 이상 사용하지 않음)
    """
    chart_data = {"labels": [], "eps": [], "dps": [], "payout_ratio": []}
    
    YEARS = list(range(2023, 2026)) 
    REPORTS_ORDER = [('q1', '1분기보고서'), ('q2', '반기보고서'), ('q3', '3분기보고서'), ('annual', '사업보고서')]

    print(f"🛠️ 백엔드 (EP8-통합): EPS/DPS/배당성향 데이터 전처리를 시작합니다...")
    try:
        stop_processing = False
        for year in YEARS:
            if stop_processing: break
            year_str = str(year)
            
            last_eps = 0.0
            last_dps = 0.0

            for q_key, q_name in REPORTS_ORDER:
                
                # 2023년 1분기는 무조건 건너뛰기
                if year == 2023 and q_key == 'q1':
                    continue

                # --- 1. EPS / DPS / 배당성향 데이터 로드 (배당 폴더) ---
                dividend_file = f"삼성전자_{year_str}년_{q_name}_배당.json"
                dividend_path = os.path.join(DIVIDEND_DIR_BASE, dividend_file)
                
                # [로직 수정] 2023년 2분기는 Q3 계산을 위한 Base로만 사용
                if year == 2023 and q_key == 'q2':
                    total_eps_q2 = get_dividend_json_value(dividend_path, "(연결)주당순이익(원)")
                    total_dps_q2 = get_dividend_json_value(dividend_path, "주당 현금배당금(원)", "보통주")

                    if total_eps_q2 is None or total_dps_q2 is None:
                        print(f"    INFO (EP8-통합): 2023 Q3 계산을 위한 '{q_name}' 배당 base 파일 없음. 중단합니다.")
                        stop_processing = True
                        break # Q2 base가 없으면 Q3 계산 불가능
                    
                    last_eps = total_eps_q2
                    last_dps = total_dps_q2
                    continue # Q2는 차트에 추가하지 않고 다음 루프(Q3)로

                # --- (2023 Q3 부터 이 로직이 실행됨) ---
                total_eps = get_dividend_json_value(dividend_path, "(연결)주당순이익(원)")
                total_dps = get_dividend_json_value(dividend_path, "주당 현금배당금(원)", "보통주")
                
                # ⭐️ [수정] 배당성향(%)도 '배당' 폴더에서 바로 읽어옵니다.
                payout_ratio_val = get_dividend_json_value(dividend_path, "(연결)현금배당성향(%)")


                # 3. 파일이 하나라도 없으면 (미래 시점) 중단
                if total_eps is None or total_dps is None or payout_ratio_val is None:
                    print(f"    INFO (EP8-통합): '{q_name}' 데이터 없음. 처리를 중단합니다.")
                    stop_processing = True
                    break
                
                # 4. 분기별 값 계산
                quarterly_eps = total_eps - last_eps
                quarterly_dps = total_dps - last_dps
                # (배당성향은 해당 분기 리포트의 %값을 그대로 사용)

                # 5. 차트 데이터 추가
                chart_data["labels"].append(f"{year_str}.{q_key.upper()}")
                chart_data["eps"].append(quarterly_eps)
                chart_data["dps"].append(quarterly_dps)
                chart_data["payout_ratio"].append(payout_ratio_val) 

                # 6. 다음 분기 계산을 위해 last 값 업데이트
                last_eps = total_eps
                last_dps = total_dps
                    
    except Exception as e:
        print(f"❌ (EP8-통합) 전처리 중 치명적 오류 발생: {e}")
        return {}

    final_data = {
        "labels": chart_data["labels"],
        "eps": [float(v) if v is not None else None for v in chart_data["eps"]],
        "dps": [float(v) if v is not None else None for v in chart_data["dps"]],
        "payout_ratio": [float(v) if v is not None else None for v in chart_data["payout_ratio"]]
    }
    print(f"✅ 백엔드 (EP8-통합): EPS/DPS/배당성향 전처리 완료!")
    return final_data

# [EP9 TTM 수정] 현금흐름(FCF) 차트
def process_cash_flow_data(combined_data: dict):
    """ 
    [수정 4.2] main.py의 원본 TTM 로직을 main2.py 환경에 맞게 정확히 재구현
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

    print(f"🛠️ (EP9 TTM): 1. 분기별 현금흐름 계산 중...")
    
    if not combined_data:
        print("❌ (EP9): combined_data가 없습니다.")
        return {}
        
    try:
        last_cumulative_values = {} # 직전 분기의 '누적' 값을 저장

        # ⭐️ [수정] 날짜순으로 정렬 (2016.Q1, 2016.Q2 ... 2016.ANNUAL)
        sorted_labels = sorted(combined_data.keys(), key=lambda x: (
            int(x.split('.')[0]), 
            # Q1=1, Q2=2, Q3=3, ANNUAL=4로 변환하여 정렬
            x.split('.')[1].replace('Q','').replace('ANNUAL','4') 
        ))

        for label in sorted_labels:
            data = combined_data[label]
            
            # ⭐️ Q1(1분기)일 경우, 새해이므로 누적값 리셋
            if "Q1" in label:
                last_cumulative_values = {k: 0 for k in quarterly_data.keys() if k != 'labels'}
            
            if data.get('status') != '000':
                print(f" INFO (EP9): {label} 데이터 상태가 '000'이 아님. 건너뜁니다.")
                continue

            data_list = data.get('list', [])
            
            # ⭐️ current_report_values: Q1/ANNUAL은 (연간)값, Q2/Q3는 (누적)값을 저장
            current_report_values = {} 
            is_cumulative_report = ("Q2" in label or "Q3" in label or "ANNUAL" in label)

            for key, name_basket in CF_ACCOUNT_BASKET.items():
                item = get_cf_account_item(data_list, name_basket)
                val_str = '0'
                if item:
                    # Q1은 thstrm_amount (분기값)
                    if "Q1" in label:
                        val_str = item.get('thstrm_amount')
                    # Q2, Q3는 thstrm_add_amount (누적값)
                    elif "Q2" in label or "Q3" in label:
                        val_str = item.get('thstrm_add_amount')
                        if not val_str: # thstrm_add_amount가 없는 경우 thstrm_amount (누적)
                            val_str = item.get('thstrm_amount')
                    # ANNUAL은 thstrm_amount (연간값)
                    elif "ANNUAL" in label:
                         val_str = item.get('thstrm_amount')
                         
                current_report_values[key] = clean_amount(val_str)
            
            # ⭐️ quarterly_values: 실제 "분기" 값을 계산하여 저장할 딕셔너리
            quarterly_values = {}
            
            # (누적) CAPEX / FCF 계산
            capex_val = current_report_values.get('capex_t', 0) + current_report_values.get('capex_i', 0)
            fcf_val = current_report_values.get('ocf', 0) - capex_val

            if not is_cumulative_report: # Q1 (1분기)
                quarterly_values = current_report_values # 1분기 값은 그대로 사용
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
                    # ⭐️ .get(key)를 사용하여 안전하게 None 또는 0을 추가
                    quarterly_data[key].append(quarterly_values.get(key, 0))

            # '다음 분기' 계산을 위해 '직전 분기 누적' 값 업데이트
            # ⭐️ (Q1, Q2, Q3, ANNUAL 모두 누적값을 저장)
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
        # ⭐️ None 값이 섞여있을 수 있으므로 안전하게 합산
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
def process_balance_sheet_data():
    """ 
    '단일회사_전체_재무제표' 폴더(CFS.json)를 읽어
    각 분기 말의 자산총계, 유동자산, 비유동자산을 추출합니다. (스냅샷)
    """
    
    # ⭐️ 재무상태표(BS) 계정 바구니
    BS_ACCOUNT_BASKET = {
        'total_assets': ['자산총계'],
        'current_assets': ['유동자산'],
        'non_current_assets': ['비유동자산'],
    }
    
    # 최종 분기별 데이터
    chart_data = {
        "labels": [],
        "total_assets": [],
        "current_assets": [],
        "non_current_assets": [],
    }

    print(f"🛠️ 백엔드 (EP11): 분기별 재무상태표(BS) 데이터 전처리를 시작합니다...")
    try:
        # 재무상태표는 2016년부터 모든 데이터를 사용
        for year in YEARS_TO_FETCH:
            year_str = str(year)
            year_dir = os.path.join(DART_DATA_DIR, f"{year_str}년")

            for q_key, q_name in REPORT_NAMES.items():
                file_path = os.path.join(year_dir, f"삼성전자_{year_str}년_{q_name}_CFS.json")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data.get('status') != '000':
                        raise FileNotFoundError
                    
                    data_list = data.get('list', [])
                    
                    chart_data["labels"].append(f"{year_str}.{q_key.upper()}")
                    
                    for bs_key, name_basket in BS_ACCOUNT_BASKET.items():
                        item = get_bs_account_item(data_list, name_basket)
                        
                        # ⭐️ 재무상태표는 항상 'thstrm_amount' (당기말 잔액)을 사용
                        amount = clean_amount(item.get('thstrm_amount')) if item else 0
                        chart_data[bs_key].append(amount)

                except FileNotFoundError:
                    print(f"    INFO (EP11): {year_str}년 {q_name} 재무상태표 파일 없음. 처리를 중단합니다.")
                    # 1년 중 하나라도 파일이 없으면 해당 연도 이후는 중단
                    raise StopIteration
                except Exception as e:
                    print(f"    ❌ (EP11): {year_str}년 {q_name} 로드 중 오류: {e}")
                    raise StopIteration

    except StopIteration:
        # 파일이 없는 지점(미래 시점)까지의 데이터만 사용
        pass
    except Exception as e:
        print(f"❌ (EP11) 전처리 중 치명적 오류 발생: {e}")
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
        print(f"❌ (EP11) 최종 타입 변환 오류: {e}")
        return {}
        
    print(f"✅ 백엔드 (EP11): 분기별 재무상태표(BS) 전처리 완료!")
    return final_data

# ⬇️ ⬇️ ⬇️ [신규 12번] 자본의 구성 (재무상태표) 차트 ⬇️ ⬇️ ⬇️
def process_equity_data():
    """ 
    '단일회사_전체_재무제표' 폴더(CFS.json)를 읽어
    각 분기 말의 자본 구성 항목(자본금, 이익잉여금 등)을 추출합니다. (스냅샷)
    """
    
    # ⭐️ 재무상태표(BS) 자본 항목 바구니
    BS_EQUITY_BASKET = {
        'total_equity': ['지배기업의 소유주에게 귀속되는 자본', '지배기업 소유주지분'], # (차트의 '지배주주 자본총계')
        'capital_stock': ['자본금'],
        'capital_surplus': ['자본잉여금', '주식발행초과금'], # (자본잉여금의 대부분)
        'retained_earnings': ['이익잉여금', '이익잉여금(결손금)'],
        'other_capital': ['기타자본구성요소', '기타자본항목'] # (차트의 '기타자본항목')
    }
    
    # 최종 분기별 데이터
    chart_data = {
        "labels": [],
        "total_equity": [],
        "capital_stock": [],
        "capital_surplus": [],
        "retained_earnings": [],
        "other_capital": [],
    }

    print(f"🛠️ 백엔드 (EP12): 분기별 자본구성(BS) 데이터 전처리를 시작합니다...")
    try:
        # 2016년부터 모든 데이터를 사용
        for year in YEARS_TO_FETCH:
            year_str = str(year)
            year_dir = os.path.join(DART_DATA_DIR, f"{year_str}년")

            for q_key, q_name in REPORT_NAMES.items():
                file_path = os.path.join(year_dir, f"삼성전자_{year_str}년_{q_name}_CFS.json")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data.get('status') != '000':
                        raise FileNotFoundError
                    
                    data_list = data.get('list', [])
                    
                    chart_data["labels"].append(f"{year_str}.{q_key.upper()}")
                    
                    for bs_key, name_basket in BS_EQUITY_BASKET.items():
                        item = get_bs_account_item(data_list, name_basket)
                        
                        # ⭐️ 재무상태표는 항상 'thstrm_amount' (당기말 잔액)을 사용
                        amount = clean_amount(item.get('thstrm_amount')) if item else 0
                        chart_data[bs_key].append(amount)

                except FileNotFoundError:
                    print(f"    INFO (EP12): {year_str}년 {q_name} 재무상태표 파일 없음. 처리를 중단합니다.")
                    raise StopIteration
                except Exception as e:
                    print(f"    ❌ (EP12): {year_str}년 {q_name} 로드 중 오류: {e}")
                    raise StopIteration

    except StopIteration:
        pass
    except Exception as e:
        print(f"❌ (EP12) 전처리 중 치명적 오류 발생: {e}")
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
        print(f"❌ (EP12) 최종 타입 변환 오류: {e}")
        return {}
        
    print(f"✅ 백엔드 (EP12): 분기별 자본구성(BS) 전처리 완료!")
    return final_data

# ⬇️ ⬇️ ⬇️ [신규 13번] 부채 현황 (재무상태표) 차트 ⬇️ ⬇️ ⬇️
def process_liabilities_data():
    """ 
    '단일회사_전체_재무제표' 폴더(CFS.json)를 읽어
    각 분기 말의 부채 구성 항목(유동부채, 비유동부채, 부채총계)을 추출합니다. (스냅샷)
    """
    
    # ⭐️ 재무상태표(BS) 부채 항목 바구니
    BS_LIABILITIES_BASKET = {
        'total_liabilities': ['부채총계'],
        'current_liabilities': ['유동부채'],
        'non_current_liabilities': ['비유동부채'],
    }
    
    # 최종 분기별 데이터
    chart_data = {
        "labels": [],
        "total_liabilities": [],
        "current_liabilities": [],
        "non_current_liabilities": [],
    }

    print(f"🛠️ 백엔드 (EP13): 분기별 부채현황(BS) 데이터 전처리를 시작합니다...")
    try:
        # 2016년부터 모든 데이터를 사용
        for year in YEARS_TO_FETCH:
            year_str = str(year)
            year_dir = os.path.join(DART_DATA_DIR, f"{year_str}년")

            for q_key, q_name in REPORT_NAMES.items():
                file_path = os.path.join(year_dir, f"삼성전자_{year_str}년_{q_name}_CFS.json")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if data.get('status') != '000':
                        raise FileNotFoundError
                    
                    data_list = data.get('list', [])
                    
                    chart_data["labels"].append(f"{year_str}.{q_key.upper()}")
                    
                    for bs_key, name_basket in BS_LIABILITIES_BASKET.items():
                        item = get_bs_account_item(data_list, name_basket)
                        
                        # ⭐️ 재무상태표는 항상 'thstrm_amount' (당기말 잔액)을 사용
                        amount = clean_amount(item.get('thstrm_amount')) if item else 0
                        chart_data[bs_key].append(amount)

                except FileNotFoundError:
                    print(f"    INFO (EP13): {year_str}년 {q_name} 재무상태표 파일 없음. 처리를 중단합니다.")
                    raise StopIteration
                except Exception as e:
                    print(f"    ❌ (EP13): {year_str}년 {q_name} 로드 중 오류: {e}")
                    raise StopIteration

    except StopIteration:
        pass
    except Exception as e:
        print(f"❌ (EP13) 전처리 중 치명적 오류 발생: {e}")
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
        print(f"❌ (EP13) 최종 타입 변환 오류: {e}")
        return {}
        
    print(f"✅ 백엔드 (EP13): 분기별 부채현황(BS) 전처리 완료!")
    return final_data



# --- 8. API 엔드포인트 정의 ---
market_cap_data_lookup = load_market_cap_from_csv(MARKET_CAP_CSV_PATH)
preprocessed_data_combo = process_timeseries_data(market_cap_data_lookup)
preprocessed_data_ratio = process_revenue_ratio_data()
preprocessed_data_icr = process_icr_data() 
preprocessed_data_net_income = process_net_income_data()
preprocessed_data_growth = process_growth_data()
preprocessed_data_stability = process_stability_data()
preprocessed_data_dividend_summary = process_dividend_summary_data()
preprocessed_data_cash_flow = process_cash_flow_data()
preprocessed_data_balance_sheet = process_balance_sheet_data()
preprocessed_data_equity = process_equity_data()
preprocessed_data_liabilities = process_liabilities_data()

# --- 9. API 라우팅 ---
@app.get("/api/samsung-quarterly-data") #엔드포인트 1
async def get_samsung_quarterly_data():
    if preprocessed_data_combo: return {"status": "success", "data": preprocessed_data_combo}
    else: return {"status": "error", "message": "데이터 가공 실패"}

@app.get("/api/samsung-revenue-ratio") #엔드포인트 2
async def get_samsung_revenue_ratio():
    if preprocessed_data_ratio: return {"status": "success", "data": preprocessed_data_ratio}
    else: return {"status": "error", "message": "데이터 가공 실패"}

@app.get("/api/samsung-icr") #엔드포인트 3
async def get_samsung_icr():
    if preprocessed_data_icr: return {"status": "success", "data": preprocessed_data_icr}
    else: return {"status": "error", "message": "데이터 가공 실패"}

@app.get("/api/samsung-net-income") #엔드포인트 4
async def get_samsung_net_income():
    if preprocessed_data_net_income: return {"status": "success", "data": preprocessed_data_net_income}
    else: return {"status": "error", "message": "데이터 가공 실패"}

@app.get("/api/samsung-growth") #엔드포인트 5
async def get_samsung_growth():
    if preprocessed_data_growth:
        return {"status": "success", "data": preprocessed_data_growth}
    else:
        return {"status": "error", "message": "데이터 가공 실패"}
    
@app.get("/api/samsung-stability")  #엔드포인트 6
async def get_samsung_stability():
    if preprocessed_data_stability:
        return {"status": "success", "data": preprocessed_data_stability}
    else:
        return {"status": "error", "message": "데이터 가공 실패"}
    
@app.get("/api/samsung-dividend-summary")   #엔드포인트 7
async def get_samsung_dividend_summary():
    if preprocessed_data_dividend_summary:
        return {"status": "success", "data": preprocessed_data_dividend_summary}
    else:
        return {"status": "error", "message": "데이터 가공 실패"}
    
@app.get("/api/samsung-cash-flow")
async def get_samsung_cash_flow():
    if preprocessed_data_cash_flow:
        return {"status": "success", "data": preprocessed_data_cash_flow}
    else:
        return {"status": "error", "message": "데이터 가공 실패"}

@app.get("/api/samsung-capex-cash-flow-ttm")
async def get_samsung_capex_cash_flow_ttm():
    # EP9에서 계산된 TTM 현금흐름 데이터를 그대로 재활용합니다.
    if preprocessed_data_cash_flow: 
        return {"status": "success", "data": preprocessed_data_cash_flow}
    else:
        return {"status": "error", "message": "데이터 가공 실패"}
    
@app.get("/api/samsung-balance-sheet")  #엔드포인트 10  
async def get_samsung_balance_sheet():
    if preprocessed_data_balance_sheet:
        return {"status": "success", "data": preprocessed_data_balance_sheet}
    else:
        return {"status": "error", "message": "데이터 가공 실패"}
    
@app.get("/api/samsung-equity-composition")
async def get_samsung_equity_composition():
    if preprocessed_data_equity: 
        return {"status": "success", "data": preprocessed_data_equity}
    else:
        return {"status": "error", "message": "데이터 가공 실패"}
    
@app.get("/api/samsung-liabilities")
async def get_samsung_liabilities():
    if preprocessed_data_liabilities: 
        return {"status": "success", "data": preprocessed_data_liabilities}
    else:
        return {"status": "error", "message": "데이터 가공 실패"}
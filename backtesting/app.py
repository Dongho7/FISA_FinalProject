# app.py (하락장 음영 분석 기능 추가)

import pandas as pd
import numpy as np
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from datetime import datetime
import os
import json 
import google.generativeai as genai
import time
from dotenv import load_dotenv

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")  # ⭐️ (환경변수에서 API 키 로드)

# --- 0. AI 설정 (Gemini) ---
try:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('models/gemini-flash-latest') 
except Exception as e:
    print(f"⚠️ AI 모델 로드 실패: {e}. API 키를 확인하세요.")
    model = None

g_ai_prompt_cache = None
g_backtest_result_cache = None # ⭐️ 반복 계산 방지 캐시

# --- 1. 백테스팅 함수 (이전과 동일) ---

def create_daily_base_rate_series(start_date, end_date):
    # (이전과 동일... 기준금리 이력)
    rate_history = {
        '2021-11-25': 1.00, '2022-01-14': 1.25, '2022-04-14': 1.50,
        '2022-05-26': 1.75, '2022-07-13': 2.25, '2022-08-25': 2.50,
        '2022-10-12': 3.00, '2022-11-24': 3.25, '2023-01-13': 3.50,
        '2024-10-11': 3.25, '2024-11-28': 3.00, '2025-02-25': 2.75,
        '2025-05-29': 2.50,
    }
    all_days = pd.date_range(start=start_date, end=end_date, freq='D')
    rate_series = pd.Series(index=all_days, name="base_rate")
    for date_str, rate in rate_history.items():
        rate_series.loc[rate_series.index >= pd.to_datetime(date_str)] = rate
    rate_series.ffill(inplace=True) 
    return rate_series / 100.0

def load_data(etf_file, kospi_file, start_date, end_date):
    # (이전과 동일... CSV 로드)
    try:
        df_etf = pd.read_csv(etf_file, index_col='Date', parse_dates=True)
        df_kospi = pd.read_csv(kospi_file, index_col='Date', parse_dates=True)
        assets_to_use = ['226490', '114260', '363570']
        df_etf = df_etf[assets_to_use]
        if 'KOSPI' not in df_kospi.columns:
            df_kospi.rename(columns={df_kospi.columns[0]: 'KOSPI'}, inplace=True)
        price_df = pd.concat([df_etf, df_kospi['KOSPI']], axis=1)
        daily_rate_series = create_daily_base_rate_series(start_date, end_date)
        price_df = price_df.join(daily_rate_series)
        price_df.ffill(inplace=True); price_df.bfill(inplace=True)
        price_df.rename(columns={'KOSPI': 'benchmark'}, inplace=True)
        return price_df
    except Exception as e:
        print(f"❌ 데이터 로드 오류: {e}"); return None

def run_monthly_rebalancing_backtest(price_df, initial_capital, target_weights, assets_by_group):
    # (이전과 동일... 월간 리밸런싱 실행)
    dates = price_df.index
    asset_keys = assets_by_group['Stocks'] + assets_by_group['Bonds']
    cash_weight = target_weights['Cash']
    current_shares = {asset: 0 for asset in asset_keys}
    current_cash_value = 0.0
    portfolio_history = [] 
    first_date = dates[0]
    first_prices = price_df.loc[first_date]
    current_cash_value = initial_capital * cash_weight
    stock_value = 0.0; bond_value = 0.0
    for asset in assets_by_group['Stocks']:
        target_value = initial_capital * target_weights[asset]
        current_shares[asset] = target_value / first_prices[asset]
        stock_value += target_value
    for asset in assets_by_group['Bonds']:
        target_value = initial_capital * target_weights[asset]
        current_shares[asset] = target_value / first_prices[asset]
        bond_value += target_value
    portfolio_history.append({'date': first_date.strftime('%Y-%m-%d'), 'value': initial_capital, 'stock_value': stock_value, 'bond_value': bond_value, 'cash_value': current_cash_value})
    for i in range(1, len(dates)):
        date = dates[i]
        today_prices = price_df.loc[date]
        daily_rate = price_df.loc[date, 'base_rate'] / 365.0
        current_cash_value *= (1 + daily_rate)
        stock_value = 0.0; bond_value = 0.0
        for asset in assets_by_group['Stocks']:
            stock_value += current_shares[asset] * today_prices[asset]
        for asset in assets_by_group['Bonds']:
            bond_value += current_shares[asset] * today_prices[asset]
        current_total_value = stock_value + bond_value + current_cash_value
        portfolio_history.append({'date': date.strftime('%Y-%m-%d'), 'value': current_total_value, 'stock_value': stock_value, 'bond_value': bond_value, 'cash_value': current_cash_value})
        is_rebalancing_day = (date.month != (date + pd.Timedelta(days=1)).month)
        if is_rebalancing_day:
            current_cash_value = current_total_value * cash_weight
            for asset in asset_keys:
                target_value = current_total_value * target_weights[asset]
                current_shares[asset] = target_value / today_prices[asset]
    return portfolio_history

def calculate_stats(series):
    # (이전과 동일... CAGR, MDD 계산)
    end_val = series.iloc[-1]; start_val = series.iloc[0]
    num_years = (series.index[-1] - series.index[0]).days / 365.25
    cagr = (end_val / start_val) ** (1 / num_years) - 1
    peak = series.cummax(); drawdown = (series - peak) / peak; mdd = drawdown.min()
    return {"CAGR": cagr, "MDD": mdd, "Final Value": end_val}

# --- 2. 포트폴리오 설정 ---
ETF_FILE = "ETF_20191201_20251107.csv"
KOSPI_FILE = "KOSPI_20191201_to_20251107.csv"
START_DATE = "2019-12-01"; END_DATE = "2025-11-07"
STOCKS = ['226490']; BONDS = ['114260', '363570']
ASSETS_BY_GROUP = {'Stocks': STOCKS, 'Bonds': BONDS}
TARGET_WEIGHTS = {'226490': 0.60, '114260': 0.15, '363570': 0.15, 'Cash': 0.10 }
INITIAL_CAPITAL = 100_000_000

# ⭐️ [신규] 사용자가 요청한 하락장 음영 구간
CRASH_PERIODS = [
    {"name": "코로나19 급락장", "start": "2020-02-14", "end": "2020-03-19"},
    {"name": "2024년 8월 하락(시스템 리스크 발생)", "start": "2024-07-30", "end": "2024-08-05"},
    {"name": "2025년 4월 하락(관세 이슈)", "start": "2025-03-26", "end": "2025-04-09"},
]

# --- 3. ⭐️ AI 분석 함수 (수정) ---

def find_analysis_data(portfolio_history, benchmark_history, user_crash_periods):
    """(수정) 벤치마크의 (1)최악의 하락 '기간', (2)최악의 '하루', (3)사용자 지정 기간을 모두 분석합니다."""
    
    # 1. 시계열 데이터로 변환
    bm_series = pd.Series({pd.to_datetime(item['date']): item['value'] for item in benchmark_history})
    pf_df = pd.DataFrame(portfolio_history); pf_df['date'] = pd.to_datetime(pf_df['date']); pf_df = pf_df.set_index('date'); pf_df.index.name = 'Date'
    
    # 2. 벤치마크의 MDD (최악의 '기간') 분석
    bm_peak = bm_series.cummax(); bm_drawdown = (bm_series - bm_peak) / bm_peak
    mdd_trough_date = bm_drawdown.idxmin(); mdd_peak_date = bm_series.loc[:mdd_trough_date].idxmax()
    
    def get_period_return(series, start_date_str, end_date_str):
        try:
            # ⭐️ 'asof'는 해당 날짜 혹은 그 이전에 가장 가까운 날짜의 데이터를 찾음 (휴장일 대응)
            start_date = pd.to_datetime(start_date_str)
            end_date = pd.to_datetime(end_date_str)
            
            # ⭐️ 데이터 범위 밖의 기간을 요청할 경우 np.nan 반환
            if end_date < series.index.min() or start_date > series.index.max():
                return np.nan
                
            start_val = series.asof(start_date)
            end_val = series.asof(end_date)
            
            if pd.isna(start_val) or pd.isna(end_val): return np.nan
            return (end_val / start_val) - 1
        except Exception:
            return np.nan # 날짜 범위를 벗어나는 등 예외 발생 시

    mdd_period_analysis = {
        "start_date": mdd_peak_date.strftime('%Y-%m-%d'), "end_date": mdd_trough_date.strftime('%Y-%m-%d'),
        "benchmark_return": get_period_return(bm_series, mdd_peak_date, mdd_trough_date),
        "portfolio_return": get_period_return(pf_df['value'], mdd_peak_date, mdd_trough_date),
        "stock_return": get_period_return(pf_df['stock_value'], mdd_peak_date, mdd_trough_date),
        "bond_return": get_period_return(pf_df['bond_value'], mdd_peak_date, mdd_trough_date),
        "cash_return": get_period_return(pf_df['cash_value'], mdd_peak_date, mdd_trough_date)
    }
    
    # 3. 벤치마크의 최악의 '하루' 분석
    bm_daily_returns = bm_series.pct_change(); pf_daily_returns = pf_df['value'].pct_change()
    worst_day_date = bm_daily_returns.idxmin()
    worst_day_analysis = {
        "date": worst_day_date.strftime('%Y-%m-%d'),
        "benchmark_return": bm_daily_returns.loc[worst_day_date],
        "portfolio_return": pf_daily_returns.loc[worst_day_date]
    }
    
    # --- 4. ⭐️ [신규] 사용자가 정의한 하락장 분석 ---
    user_period_analyses = []
    for period in user_crash_periods:
        start_date = period['start']
        end_date = period['end']
        
        analysis = {
            "name": period['name'],
            "start_date": start_date,
            "end_date": end_date,
            "benchmark_return": get_period_return(bm_series, start_date, end_date),
            "portfolio_return": get_period_return(pf_df['value'], start_date, end_date),
            "stock_return": get_period_return(pf_df['stock_value'], start_date, end_date),
            "bond_return": get_period_return(pf_df['bond_value'], start_date, end_date),
            "cash_return": get_period_return(pf_df['cash_value'], start_date, end_date),
        }
        # ⭐️ 계산된 경우에만(NaN이 아님) 리스트에 추가
        if not pd.isna(analysis['benchmark_return']):
            user_period_analyses.append(analysis)

    return mdd_period_analysis, worst_day_analysis, user_period_analyses


def generate_ai_analysis_prompt(stats, mdd_period_analysis, worst_day_analysis, user_period_analyses, user_weights):
    """(수정) AI에게 전달할 프롬프트를 동적으로 생성합니다."""
    
    weights_str = f"주식 {user_weights['226490']*100:.0f}%, 채권 {(user_weights['114260'] + user_weights['363570'])*100:.0f}%, 현금 {user_weights['Cash']*100:.0f}%"
    
    # ⭐️ [신규] 사용자 지정 하락장 분석 결과를 문자열로 변환
    user_periods_str = "\n"
    for analysis in user_period_analyses:
        user_periods_str += (
            f"    - **{analysis['name']} ({analysis['start_date']} ~ {analysis['end_date']})**\n"
            f"      - KOSPI: {analysis['benchmark_return']:.2%}\n"
            f"      - 포트폴리오: {analysis['portfolio_return']:.2%}\n"
            f"      (당시 내부 성과: 주식 {analysis['stock_return']:.2%}, 채권 {analysis['bond_return']:.2%}, 현금 {analysis['cash_return']:.2%})\n"
        )

    prompt = f"""
    당신은 전문 자산 관리 어드바이저입니다. 사용자('사용자'라고 불러줘)의 백테스트 결과를 분석하고 친절한 조언을 제공해야 합니다.(단 10줄 이내로 해주시고, 내용별로 단락 띄어쓰기를 해주세요) 첫 인사는 이렇게 해주세요, "안녕하세요! 전문 자산 관리 어드바이저입니다."

    [1. 사용자의 포트폴리오 구성]
    - {weights_str}
    - 벤치마크: KOSPI
    - 테스트 기간: {START_DATE} ~ {END_DATE}

    [2. 최종 성과 요약]
    - 나의 포트폴리오:
        - 최종 자산: {stats['portfolio']['Final Value']:,.0f} 원
        - 연평균 수익률 (CAGR): {stats['portfolio']['CAGR']:.2%}
        - 최대 손실폭 (MDD): {stats['portfolio']['MDD']:.2%}
    - KOSPI (벤치마크):
        - 최종 자산: {stats['benchmark']['Final Value']:,.0f} 원
        - 연평균 수익률 (CAGR): {stats['benchmark']['CAGR']:.2%}
        - 최대 손실폭 (MDD): {stats['benchmark']['MDD']:.2%}

    [3. KOSPI 최악의 하락 '기간' 분석 ({mdd_period_analysis['start_date']} ~ {mdd_period_analysis['end_date']})]
    - 이 기간 KOSPI는 {mdd_period_analysis['benchmark_return']:.2%} 하락했습니다.
    - 같은 기간, '나의 포트폴리오'는 {mdd_period_analysis['portfolio_return']:.2%} 하락으로 방어했습니다.
    - (당시 포트폴리오 내부: 주식 {mdd_period_analysis['stock_return']:.2%}, 채권 {mdd_period_analysis['bond_return']:.2%}, 현금 {mdd_period_analysis['cash_return']:.2%})

    [4. KOSPI 최악의 '하루' 분석 ({worst_day_analysis['date']})]
    - 이 날 KOSPI는 하루 만에 {worst_day_analysis['benchmark_return']:.2%} 급락했습니다.
    - 같은 날, '나의 포트폴리오'는 {worst_day_analysis['portfolio_return']:.2%} 하락했습니다.

    [5. ⭐️ 사용자 지정 하락장 분석]
    {user_periods_str}

    [지시사항]
    위 데이터를 바탕으로, 다음 5가지 항목을 포함하여 리포트를 작성해주세요. (강조를 위해 ** 사용 금지)

    1.  용어 설명: "최대 손실폭(MDD)"과 "연평균 수익률(CAGR)"이 무엇을 의미하는지 최대 두 문장으로 쉽게 설명해주세요. 그리고, MDD가 투자자에게 왜 중요한지 간략히 언급해주세요.
    2.  성과 비교: 사용자의 포트폴리오가 벤치마크(KOSPI) 대비 수익률과 안정성(MDD) 면에서 어땠는지 평가해주세요.
    3.  핵심 인사이트 (기간 방어): [3. 하락장 상세 분석] 데이터를 활용하여, 벤치마크가 폭락하는 '기간' 동안 채권과 현금이 포트폴리오를 방어하는 데 어떤 역할을 했는지 구체적으로 언급해주세요. (이 부분은, 문단을 별도로 나누어 강조해 주세요)
    4.  핵심 인사이트 (하루 방어): [4. 최악의 하루 분석] 데이터를 활용하여, {worst_day_analysis['date']} 당일 KOSPI가 급락했을 때 포트폴리오가 얼마나 잘 방어했는지 수치를 비교하며 언급해주세요.
    """
    return prompt

# --- 4. Flask API 서버 ---

app = Flask(__name__)
CORS(app) 

@app.route('/api/backtest')
def get_backtest_data():
    """ ⭐️ [수정] 백테스트 실행 + AI 프롬프트 캐시 + '하락장 분석 결과' 반환 """
    
    global g_ai_prompt_cache, g_backtest_result_cache
    
    # ⭐️ 반복 요청 방지 캐시
    if g_backtest_result_cache is not None:
        # print("🔄 캐시된 백테스트 결과를 반환합니다.") # (디버깅용)
        return jsonify(g_backtest_result_cache)
    
    print("⏳ 새로운 백테스트 계산을 시작합니다...")
    
    price_df = load_data(ETF_FILE, KOSPI_FILE, START_DATE, END_DATE)
    if price_df is None: return jsonify({"error": "데이터 파일을 찾을 수 없습니다."}), 500
        
    portfolio_history_list = run_monthly_rebalancing_backtest(
        price_df, INITIAL_CAPITAL, TARGET_WEIGHTS, ASSETS_BY_GROUP
    )
    
    benchmark_series = (price_df['benchmark'] / price_df['benchmark'].iloc[0]) * INITIAL_CAPITAL
    benchmark_history_list = [
        {'date': date.strftime('%Y-%m-%d'), 'value': value}
        for date, value in benchmark_series.items()
    ]
    
    portfolio_series_for_stats = pd.Series(
        [item['value'] for item in portfolio_history_list], 
        index=pd.to_datetime([item['date'] for item in portfolio_history_list])
    )
    stats_portfolio = calculate_stats(portfolio_series_for_stats)
    stats_benchmark = calculate_stats(benchmark_series)
    
    # AI 프롬프트 생성 (및 하락장 분석 데이터 생성)
    user_period_analyses = [] # ⭐️ AI 분석 함수가 실패할 경우를 대비해 초기화
    try:
        mdd_period_analysis, worst_day_analysis, user_period_analyses = find_analysis_data(
            portfolio_history_list, benchmark_history_list, CRASH_PERIODS
        )
        g_ai_prompt_cache = generate_ai_analysis_prompt(
            {"portfolio": stats_portfolio, "benchmark": stats_benchmark}, 
            mdd_period_analysis, 
            worst_day_analysis, 
            user_period_analyses,
            TARGET_WEIGHTS
        )
        print("✅ AI 프롬프트가 성공적으로 캐시되었습니다.")
    except Exception as e:
        print(f"❌ AI 프롬프트 생성 중 오류: {e}")
        g_ai_prompt_cache = None

    # ⭐️ [수정] 프런트엔드에 '하락장 분석 결과' 데이터 추가 전달
    result_data = {
        "portfolio_history": portfolio_history_list,
        "benchmark_history": benchmark_history_list,
        "stats": { "portfolio": stats_portfolio, "benchmark": stats_benchmark },
        "crash_period_results": user_period_analyses # ⭐️ AI가 분석한 '결과'를 전달
    }
    
    g_backtest_result_cache = result_data # ⭐️ 결과 캐시
    return jsonify(result_data)

@app.route('/api/analyze_stream')
def analyze_stream():
    """ ⭐️ AI의 답변을 실시간 스트리밍(SSE)하는 엔드포인트 """

    def stream_analysis():
        global g_ai_prompt_cache
        
        if not model:
            yield f"data: {json.dumps({'text': '오류: AI 모델이 로드되지 않았습니다. API 키를 확인하세요.'})}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            return
            
        if not g_ai_prompt_cache:
            yield f"data: {json.dumps({'text': '오류: AI 분석용 프롬프트가 캐시되지 않았습니다. /api/backtest를 먼저 호출하세요.'})}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            return

        try:
            response = model.generate_content(g_ai_prompt_cache, stream=True)
            for chunk in response:
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
                    time.sleep(0.02)
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            
        except Exception as e:
            print(f"❌ AI 스트리밍 중 오류: {e}")
            yield f"data: {json.dumps({'text': f'AI 스트리밍 중 오류가 발생했습니다: {e}'})}\n\n"
            yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return Response(stream_analysis(), mimetype='text/event-stream')


if __name__ == '__main__':
    # ⭐️ debug=False로 변경하여 자동 새로고침 방지
    app.run(debug=False, host='0.0.0.0', port=5000)
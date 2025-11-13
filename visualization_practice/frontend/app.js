document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. API 주소 정의 ---
    const REVENUE_API_URL = 'http://localhost:8000/api/samsung-quarterly-data';
    const RATIO_API_URL = 'http://localhost:8000/api/samsung-revenue-ratio';
    const ICR_API_URL = 'http://localhost:8000/api/samsung-icr'; 
    const NET_INCOME_API_URL = 'http://localhost:8000/api/samsung-net-income';
    const GROWTH_API_URL = 'http://localhost:8000/api/samsung-growth';
    const STABILITY_API_URL = 'http://localhost:8000/api/samsung-stability';
    const DIVIDEND_SUMMARY_API_URL = 'http://localhost:8000/api/samsung-dividend-summary';
    const CASH_FLOW_API_URL = 'http://localhost:8000/api/samsung-cash-flow';
    const CAPEX_CASH_FLOW_TTM_API_URL = 'http://localhost:8000/api/samsung-capex-cash-flow-ttm';
    const BALANCE_SHEET_API_URL = 'http://localhost:8000/api/samsung-balance-sheet';
    const EQUITY_COMPOSITION_API_URL = 'http://localhost:8000/api/samsung-equity-composition';
    const LIABILITIES_API_URL = 'http://localhost:8000/api/samsung-liabilities';

    /**
     * [차트 1] 콤보 차트 생성 함수 (기존 로직)
     */
    function createRevenueChart(chartData) {
        console.log("🛠️ [차트 1] 콤보 차트 생성을 시작합니다...");
        const ctx = document.getElementById('revenueChart').getContext('2d');

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '영업이익', data: chartData.op_income, backgroundColor: '#f48fb1', stack: 'stack0',
                        order: 1, tooltipOrder: 4 
                    },
                    {
                        label: '판매관리비', data: chartData.sga, backgroundColor: '#90caf9', stack: 'stack0',
                        order: 1, tooltipOrder: 3
                    },
                    {
                        label: '매출원가', data: chartData.cogs, backgroundColor: '#a5d6a7', stack: 'stack0',
                        order: 1, tooltipOrder: 2
                    },
                    {
                        label: '매출액', data: chartData.revenue, type: 'line', borderColor: '#ba68c8',
                        backgroundColor: '#ba68c8', borderWidth: 3, pointRadius: 5, yAxisID: 'y-revenue',
                        order: 0, tooltipOrder: 1
                    },
                    {
                        label: '시가총액(우)', data: chartData.market_cap, type: 'line', borderColor: '#888888',
                        backgroundColor: '#888888', borderWidth: 2, pointRadius: 4, borderDash: [5, 5],
                        yAxisID: 'y-market-cap', order: 0, tooltipOrder: 5
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true, 
                plugins: {
                    title: { display: true, text: '삼성전자 분기별 주요 손익 (2016~2025)', font: { size: 16, weight: 'bold' } },
                    legend: { position: 'top', align: 'center', labels: { padding: 20, usePointStyle: true, pointStyle: 'rectRounded' } },
                    tooltip: {
                        mode: 'index', intersect: false, itemSort: (a, b) => a.dataset.tooltipOrder - b.dataset.tooltipOrder,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) { label += (value / 1_0000_0000_0000).toFixed(1) + '조'; }
                                return label;
                            }
                        }
                    },
                },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    'y-revenue': { 
                        type: 'linear', position: 'left', stacked: true, beginAtZero: true,
                        ticks: { callback: (value) => (value / 1_0000_0000_0000).toFixed(1) + '조' }
                    },
                    'y-market-cap': {
                        type: 'linear', position: 'right', beginAtZero: true, grid: { drawOnChartArea: false }, 
                        ticks: { callback: (value) => (value / 1_0000_0000_0000).toFixed(1) + '조' }
                    }
                }
            }
        });
    }

    /**
     * [차트 2] 매출 구성비중 차트 생성 함수 (기존 로직)
     */
    function createRevenueRatioChart(chartData) {
        console.log("🛠️ [차트 2] 매출 구성비중 차트 생성을 시작합니다...");
        const ctx = document.getElementById('revenueRatioChart').getContext('2d');

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: '영업이익률',
                        data: chartData.op_income_ratio,
                        backgroundColor: '#f48fb1',
                        stack: 'ratio_stack', 
                    },
                    {
                        label: '판매관리비율',
                        data: chartData.sga_ratio,
                        backgroundColor: '#90caf9',
                        stack: 'ratio_stack',
                    },
                    {
                        label: '매출원가율',
                        data: chartData.cogs_ratio,
                        backgroundColor: '#a5d6a7',
                        stack: 'ratio_stack',
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 매출 구성비중 (100% Stacked)', font: { size: 16, weight: 'bold' }
                    },
                    legend: { position: 'top', align: 'center', labels: { padding: 20, usePointStyle: true, pointStyle: 'rectRounded' } },
                    tooltip: {
                        mode: 'index', intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y.toFixed(2) + '%';
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        stacked: true,
                        min: 0,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * [차트 3] 이자보상배율(ICR) 차트 생성 함수 (기존 로직)
     */
    function createICRChart(chartData) {
        console.log("🛠️ [차트 3] 이자보상배율(ICR) 차트를 시작합니다...");
        const ctx = document.getElementById('icrChart').getContext('2d');

        new Chart(ctx, {
            type: 'line', // 꺾은선 그래프
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: '이자보상배율 (ICR)',
                    data: chartData.icr_ratio,
                    borderColor: '#29b6f6', // 밝은 파란색
                    backgroundColor: 'rgba(41, 182, 246, 0.5)',
                    fill: true,
                    tension: 0.4, // 선을 부드럽게
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 이자보상배율 (ICR)', font: { size: 16, weight: 'bold' }
                    },
                    legend: { display: false }, // 범례 숨김
                    tooltip: {
                        mode: 'index', intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                if (context.parsed.y !== null) {
                                    if (!isFinite(context.parsed.y)) {
                                        label += 'N/A (이자 0)';
                                    } else {
                                        label += context.parsed.y.toFixed(2) + '배';
                                    }
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + '배';
                            }
                        }
                    }
                }
            }
        });
    }

    /**
     * [차트 4] 당기순이익 차트 생성 함수 (기존 로직)
     */
    function createNetIncomeChart(chartData) {
        console.log("🛠️ [차트 4] 당기순이익 차트를 시작합니다...");
        const ctx = document.getElementById('netIncomeChart').getContext('2d');

        new Chart(ctx, {
            type: 'bar', 
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: '당기순이익',
                    data: chartData.net_income,
                    backgroundColor: 'rgba(76, 175, 80, 0.5)',
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 분기별 당기순이익', font: { size: 16, weight: 'bold' }
                    },
                    legend: { display: false },
                    tooltip: {
                        mode: 'index', intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    label += (value / 1_0000_0000_0000).toFixed(1) + '조';
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: (value) => (value / 1_0000_0000_0000).toFixed(1) + '조'
                        }
                    }
                }
            }
        });
    }

    function createGrowthChart(chartData) {
        console.log("🛠️ [차트 6] 성장성 지표(YoY) 차트를 시작합니다...");
        const ctx = document.getElementById('growthChart').getContext('2d'); 

        new Chart(ctx, {
            type: 'line', 
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '매출액증가율(YoY)',
                        data: chartData.yoy_revenue_growth,
                        borderColor: '#42a5f5', 
                        backgroundColor: 'rgba(66, 165, 245, 0.3)',
                        fill: false, 
                        tension: 0.4, 
                        yAxisID: 'y_revenue_growth', // ⭐️ 1. 왼쪽 Y축(매출) 지정
                    },
                    {
                        label: '영업이익증가율(YoY)',
                        data: chartData.yoy_op_income_growth,
                        borderColor: '#ef5350', 
                        backgroundColor: 'rgba(239, 83, 80, 0.3)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y_op_income_growth', // ⭐️ 2. 오른쪽 Y축(영업이익) 지정
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 성장성 지표 (YoY)', font: { size: 16, weight: 'bold' }
                    },
                    legend: { 
                        display: true, 
                        position: 'top'
                    }, 
                    tooltip: {
                        mode: 'index', intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    label += value.toFixed(2) + '%'; 
                                }
                                return label;
                            }
                        }
                    }
                },
                // ⭐️ 3. Y축 스케일을 2개로 분리
                scales: {
                    x: { grid: { display: false } },

                    // 왼쪽 Y축 (매출액증가율)
                    'y_revenue_growth': { 
                        type: 'linear',
                        position: 'left',
                        beginAtZero: false, 
                        ticks: {
                            callback: (value) => value.toFixed(1) + '%' 
                        },
                        title: { // 축 제목 추가
                            display: true,
                            text: '매출액증가율 (%)'
                        }
                    },
                    
                    // 오른쪽 Y축 (영업이익증가율)
                    'y_op_income_growth': { 
                        type: 'linear',
                        position: 'right', // ⭐️ 오른쪽
                        beginAtZero: false, 
                        ticks: {
                            callback: (value) => value.toFixed(1) + '%' 
                        },
                        title: { // 축 제목 추가
                            display: true,
                            text: '영업이익증가율 (%)'
                        },
                        grid: { // ⭐️ 오른쪽 축 그리드는 끔 (차트 혼잡 방지)
                            drawOnChartArea: false 
                        }
                    }
                }
            }
        });
    }


    function createStabilityChart(chartData) {
        console.log("🛠️ [차트 7] 안정성 지표 차트를 시작합니다...");
        const ctx = document.getElementById('stabilityChart').getContext('2d'); // ⭐️ HTML의 'stabilityChart' ID

        new Chart(ctx, {
            type: 'line', 
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '부채비율',
                        data: chartData.debt_ratio,
                        borderColor: '#ffa726', // 주황색
                        backgroundColor: 'rgba(255, 167, 38, 0.3)',
                        fill: false, // ⭐️ 부채비율은 영역을 채움
                        tension: 0.4, 
                        yAxisID: 'y_debt_ratio', // ⭐️ 1. 왼쪽 Y축 (낮은 값)
                    },
                    {
                        label: '유동비율',
                        data: chartData.current_ratio,
                        borderColor: '#66bb6a', // 녹색
                        backgroundColor: 'rgba(102, 187, 106, 0.3)',
                        fill: false, // ⭐️ 유동비율도 영역을 채움
                        tension: 0.4,
                        yAxisID: 'y_current_ratio', // ⭐️ 2. 오른쪽 Y축 (높은 값)
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 안정성 지표 (2023.3Q~)', font: { size: 16, weight: 'bold' }
                    },
                    legend: { 
                        display: true, 
                        position: 'top'
                    }, 
                    tooltip: {
                        mode: 'index', intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    label += value.toFixed(2) + '%'; // 둘 다 %
                                }
                                return label;
                            }
                        }
                    }
                },
                // ⭐️ 3. Y축 스케일을 2개로 분리
                scales: {
                    x: { grid: { display: false } },

                    // 왼쪽 Y축 (부채비율)
                    'y_debt_ratio': { 
                        type: 'linear',
                        position: 'left',
                        beginAtZero: true, // ⭐️ 0% 부터 시작
                        ticks: {
                            callback: (value) => value.toFixed(1) + '%' 
                        },
                        title: { 
                            display: true,
                            text: '부채비율 (%)'
                        }
                    },
                    
                    // 오른쪽 Y축 (유동비율)
                    'y_current_ratio': { 
                        type: 'linear',
                        position: 'right', 
                        beginAtZero: true, // ⭐️ 0% 부터 시작
                        ticks: {
                            callback: (value) => value.toFixed(1) + '%' 
                        },
                        title: { 
                            display: true,
                            text: '유동비율 (%)'
                        },
                        grid: { // ⭐️ 오른쪽 축 그리드는 끔 (차트 혼잡 방지)
                            drawOnChartArea: false 
                        }
                    }
                }
            }
        });
    }

// ⭐️ ⬇️ ⬇️ ⬇️ [신규 8번째(통합) 차트] EPS (막대) vs DPS (막대) vs 배당성향 (선) ⬇️ ⬇️ ⬇️
    function createDividendSummaryChart(chartData) {
        console.log("🛠️ [차트 8-통합] EPS/DPS/배당성향 차트를 시작합니다...");
        // ⭐️ HTML에서 수정한 'dividendSummaryChart' ID
        const ctx = document.getElementById('epsDpsChart').getContext('2d'); 

        new Chart(ctx, {
            type: 'bar', // 기본 타입은 막대
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '주당순이익(EPS)',
                        data: chartData.eps,
                        backgroundColor: 'rgba(144, 202, 249, 0.7)', // 하늘색
                        borderColor: 'rgba(144, 202, 249, 1)',
                        borderWidth: 1,
                        yAxisID: 'y_amount', // ⭐️ 왼쪽 Y축 (원)
                    },
                    {
                        label: '주당배당금(DPS)',
                        data: chartData.dps,
                        backgroundColor: 'rgba(30, 136, 229, 0.7)', // 진한 파란색
                        borderColor: 'rgba(30, 136, 229, 1)',
                        borderWidth: 1,
                        yAxisID: 'y_amount', // ⭐️ 왼쪽 Y축 (원)
                    },
                    {
                        label: '배당성향(%)',
                        data: chartData.payout_ratio,
                        type: 'line', // ⭐️ 콤보 차트: 이 데이터만 꺾은선
                        borderColor: '#ec407a', // 핑크/자주 계열
                        backgroundColor: 'rgba(236, 64, 122, 0.3)',
                        fill: false, // 선만 표시
                        tension: 0.4, // 부드럽게
                        yAxisID: 'y_percent', // ⭐️ 오른쪽 Y축 (%)
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 분기별 EPS, DPS 및 배당성향 (2023.3Q~)', font: { size: 16, weight: 'bold' }
                    },
                    legend: { 
                        display: true, 
                        position: 'top'
                    }, 
                    tooltip: {
                        mode: 'index', 
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    // ⭐️ 배당성향(%)일 때와 아닐 때 구분
                                    if (context.dataset.type === 'line') {
                                        label += value.toFixed(2) + '%';
                                    } else {
                                        label += value.toFixed(0) + '원'; 
                                    }
                                }
                                return label;
                            }
                        }
                    }
                },
                // ⭐️ 듀얼 Y축 설정
                scales: {
                    x: { grid: { display: false } },
                    // 왼쪽 Y축 (원)
                    'y_amount': { 
                        type: 'linear',
                        position: 'left',
                        beginAtZero: true, 
                        ticks: {
                            callback: (value) => value.toFixed(0) + '원' 
                        },
                        title: {
                            display: true,
                            text: '금액 (원)'
                        }
                    },
                    // 오른쪽 Y축 (%)
                    'y_percent': { 
                        type: 'linear',
                        position: 'right', 
                        beginAtZero: true, 
                        ticks: {
                            callback: (value) => value.toFixed(1) + '%' 
                        },
                        title: { 
                            display: true,
                            text: '배당성향 (%)'
                        },
                        grid: { 
                            drawOnChartArea: false 
                        }
                    }
                }
            }
        });
    }

    function createCashFlowChart(chartData) {
        console.log("🛠️ [차트 9] 현금흐름(FCF) 차트를 시작합니다...");
        const ctx = document.getElementById('cashFlowChart').getContext('2d'); // ⭐️ HTML의 'cashFlowChart' ID

        // 툴팁과 Ticks에서 '조' 단위로 변환하는 헬퍼
        const trilFormatter = (value) => (value / 1_0000_0000_0000).toFixed(1) + '조';

        new Chart(ctx, {
            type: 'bar', // FCF를 막대 그래프로
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: 'FCF (잉여현금흐름)',
                        data: chartData.fcf,
                        backgroundColor: 'rgba(66, 165, 245, 0.7)', // 파란색 막대
                        order: 1 // ⭐️ 막대를 뒤로 보냄
                    },
                    {
                        label: '영업현금흐름(OCF)',
                        data: chartData.ocf,
                        type: 'line',
                        borderColor: '#f48fb1', // 핑크
                        tension: 0.3,
                        fill: false,
                        order: 0 // ⭐️ 선을 앞으로
                    },
                    {
                        label: '투자현금흐름(ICF)',
                        data: chartData.icf,
                        type: 'line',
                        borderColor: '#ffb74d', // 주황
                        tension: 0.3,
                        fill: false,
                        order: 0
                    },
                    {
                        label: '재무현금흐름(FFCF)',
                        data: chartData.ffcf,
                        type: 'line',
                        borderColor: '#a5d6a7', // 녹색
                        tension: 0.3,
                        fill: false,
                        order: 0
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 분기별 현금흐름 (2016~)', font: { size: 16, weight: 'bold' }
                    },
                    legend: { 
                        display: true, 
                        position: 'top'
                    }, 
                    tooltip: {
                        mode: 'index', 
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    label += (value / 1_0000_0000_0000).toFixed(1) + '조';
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { 
                        beginAtZero: false, // ⭐️ FCF가 마이너스일 수 있으므로
                        ticks: {
                            callback: trilFormatter // Y축 (조)
                        },
                        title: {
                            display: true,
                            text: '금액 (조 원)'
                        }
                    }
                }
            }
        });
    }


    // ⭐️ ⬇️ ⬇️ ⬇️ [신규 10번째 차트] CAPEX vs 현금흐름 TTM ⬇️ ⬇️ ⬇️
    function createCapexCashFlowTTMChart(chartData) {
        console.log("🛠️ [차트 10] CAPEX vs 현금흐름 (TTM) 차트를 시작합니다...");
        const ctx = document.getElementById('capexCashFlowTTMChart').getContext('2d'); 

        // 툴팁과 Ticks에서 '조' 단위로 변환하는 헬퍼
        const trilFormatter = (value) => (value / 1_0000_0000_0000).toFixed(1) + '조';

        new Chart(ctx, {
            type: 'bar', // FCF와 CAPEX를 막대 그래프로
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '영업현금흐름(OCF)',
                        data: chartData.ocf,
                        type: 'line', // ⭐️ OCF만 꺾은선으로 표시
                        borderColor: '#f48fb1', // 핑크색 선
                        tension: 0.3,
                        fill: false,
                        order: 0, // ⭐️ 선이 가장 위에 오도록
                        yAxisID: 'y_amount' 
                    },
                    {
                        label: '자본적 지출(CAPEX)',
                        data: chartData.capex,
                        backgroundColor: 'rgba(255, 193, 7, 0.9)', // 노란색 막대
                        stack: 'cashFlowStack', // ⭐️ 스택 그룹 지정
                        order: 1, 
                        yAxisID: 'y_amount'
                    },
                    {
                        label: 'FCF (잉여현금흐름)',
                        data: chartData.fcf,
                        backgroundColor: 'rgba(66, 165, 245, 0.9)', // 파란색 막대
                        stack: 'cashFlowStack', // ⭐️ 스택 그룹 지정
                        order: 1,
                        yAxisID: 'y_amount'
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 CAPEX vs 현금흐름 (TTM)', font: { size: 16, weight: 'bold' }
                    },
                    legend: { 
                        display: true, 
                        position: 'top'
                    }, 
                    tooltip: {
                        mode: 'index', 
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    label += trilFormatter(value);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    'y_amount': { // Y축 하나만 사용
                        beginAtZero: true, 
                        stacked: true, // ⭐️ 막대를 쌓도록 설정
                        ticks: {
                            callback: trilFormatter // Y축 (조)
                        },
                        title: {
                            display: true,
                            text: '금액 (조 원)'
                        }
                    }
                }
            }
        });
    }

    // ⭐️ ⬇️ ⬇️ ⬇️ [신규 10번째 차트] CAPEX vs 현금흐름 TTM ⬇️ ⬇️ ⬇️
    function createCapexCashFlowTTMChart(chartData) {
        console.log("🛠️ [차트 10] CAPEX vs 현금흐름 (TTM) 차트를 시작합니다...");
        const ctx = document.getElementById('capexCashFlowTTMChart').getContext('2d'); 

        // 툴팁과 Ticks에서 '조' 단위로 변환하는 헬퍼
        const trilFormatter = (value) => (value / 1_0000_0000_0000).toFixed(1) + '조';

        new Chart(ctx, {
            type: 'bar', // FCF와 CAPEX를 막대 그래프로
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '영업현금흐름(OCF)',
                        data: chartData.ocf,
                        type: 'line', // ⭐️ OCF만 꺾은선으로 표시
                        borderColor: '#f48fb1', // 핑크색 선
                        tension: 0.3,
                        fill: false,
                        order: 0, // ⭐️ 선이 가장 위에 오도록
                        yAxisID: 'y_amount' 
                    },
                    {
                        label: '자본적 지출(CAPEX)',
                        data: chartData.capex,
                        backgroundColor: 'rgba(255, 193, 7, 0.9)', // 노란색 막대
                        stack: 'cashFlowStack', // ⭐️ 스택 그룹 지정
                        order: 1, 
                        yAxisID: 'y_amount'
                    },
                    {
                        label: 'FCF (잉여현금흐름)',
                        data: chartData.fcf,
                        backgroundColor: 'rgba(66, 165, 245, 0.9)', // 파란색 막대
                        stack: 'cashFlowStack', // ⭐️ 스택 그룹 지정
                        order: 1,
                        yAxisID: 'y_amount'
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 CAPEX vs 현금흐름 (TTM)', font: { size: 16, weight: 'bold' }
                    },
                    legend: { 
                        display: true, 
                        position: 'top'
                    }, 
                    tooltip: {
                        mode: 'index', 
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    label += trilFormatter(value);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    'y_amount': { // Y축 하나만 사용
                        beginAtZero: true, 
                        stacked: true, // ⭐️ 막대를 쌓도록 설정
                        ticks: {
                            callback: trilFormatter // Y축 (조)
                        },
                        title: {
                            display: true,
                            text: '금액 (조 원)'
                        }
                    }
                }
            }
        });
    }


    // ⭐️ ⬇️ ⬇️ ⬇️ [신규 11번째 차트] 자산의 구성 ⬇️ ⬇️ ⬇️
    function createBalanceSheetChart(chartData) {
        console.log("🛠️ [차트 11] 자산의 구성 차트를 시작합니다...");
        const ctx = document.getElementById('balanceSheetChart').getContext('2d'); 

        // 툴팁과 Ticks에서 '조' 단위로 변환하는 헬퍼
        const trilFormatter = (value) => (value / 1_0000_0000_0000).toFixed(1) + '조';

        new Chart(ctx, {
            type: 'bar', // 유동/비유동자산을 막대 그래프로
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '자산총계',
                        data: chartData.total_assets,
                        type: 'line', // ⭐️ 자산총계만 꺾은선으로 표시
                        borderColor: '#f48fb1', // 핑크색 선
                        tension: 0.3,
                        fill: false,
                        order: 0, // ⭐️ 선이 가장 위에 오도록
                        yAxisID: 'y_amount' 
                    },
                    {
                        label: '유동자산',
                        data: chartData.current_assets, 
                        backgroundColor: 'rgba(255, 193, 7, 0.9)', // 노란색 막대 (이미지 참고)
                        stack: 'assetStack', // ⭐️ 스택 그룹 지정
                        order: 1, 
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '비유동자산',
                        data: chartData.non_current_assets, 
                        backgroundColor: 'rgba(66, 165, 245, 0.9)', // 파란색 막대 (이미지 참고)
                        stack: 'assetStack', // ⭐️ 스택 그룹 지정
                        order: 1,
                        yAxisID: 'y_amount'
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 자산의 구성 (2016~)', font: { size: 16, weight: 'bold' }
                    },
                    legend: { 
                        display: true, 
                        position: 'top'
                    }, 
                    tooltip: {
                        mode: 'index', 
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    label += trilFormatter(value);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    'y_amount': { // Y축 하나만 사용
                        beginAtZero: true, 
                        stacked: true, // ⭐️ 막대를 쌓도록 설정
                        ticks: {
                            callback: trilFormatter // Y축 (조)
                        },
                        title: {
                            display: true,
                            text: '금액 (조 원)'
                        }
                    }
                }
            }
        });
    }


    // ⭐️ ⬇️ ⬇️ ⬇️ [신규 12번째 차트] 자본의 구성 ⬇️ ⬇️ ⬇️
    function createEquityChart(chartData) {
        console.log("🛠️ [차트 12] 자본의 구성 차트를 시작합니다...");
        const ctx = document.getElementById('equityChart').getContext('2d'); // ⭐️ HTML에 'equityChart' ID 필요

        const trilFormatter = (value) => (value / 1_0000_0000_0000).toFixed(1) + '조';

        new Chart(ctx, {
            type: 'bar', // 기본 타입
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: '지배주주 자본총계',
                        data: chartData.total_equity,
                        type: 'line',
                        borderColor: '#81c784', // 연두색 (이미지 참고)
                        tension: 0.3,
                        fill: false,
                        order: 0, // ⭐️ 선이 가장 위에 오도록
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '이익잉여금',
                        data: chartData.retained_earnings,
                        backgroundColor: 'rgba(239, 83, 80, 0.8)', // 핑크/빨강 (이미지 참고)
                        stack: 'equityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '기타자본항목',
                        data: chartData.other_capital,
                        backgroundColor: 'rgba(66, 165, 245, 0.8)', // 파란색
                        stack: 'equityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '자본잉여금',
                        data: chartData.capital_surplus,
                        backgroundColor: 'rgba(255, 238, 88, 0.9)', // 노란색
                        stack: 'equityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '자본금',
                        data: chartData.capital_stock,
                        backgroundColor: 'rgba(170, 170, 170, 0.8)', // 회색 (아주 얇음)
                        stack: 'equityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 자본의 구성 (2016~)', font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    label += trilFormatter(value);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    'y_amount': {
                        // ⭐️ '기타자본항목'이 음수일 수 있으므로 0에서 시작 안 함
                        beginAtZero: false, 
                        stacked: true,
                        ticks: {
                            callback: trilFormatter
                        },
                        title: {
                            display: true,
                            text: '금액 (조 원)'
                        }
                    }
                }
            }
        });
    }


    // ⭐️ ⬇️ ⬇️ ⬇️ [신규 13번째 차트] 부채 현황 ⬇️ ⬇️ ⬇️
    function createLiabilitiesChart(chartData) {
        console.log("🛠️ [차트 13] 부채 현황 차트를 시작합니다...");
        const ctx = document.getElementById('liabilitiesChart').getContext('2d'); // ⭐️ HTML에 'liabilitiesChart' ID 필요

        const trilFormatter = (value) => (value / 1_0000_0000_0000).toFixed(1) + '조';

        new Chart(ctx, {
            type: 'bar', // 기본 타입
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: '부채총계',
                        data: chartData.total_liabilities,
                        type: 'line',
                        borderColor: '#ffb74d', // 주황/금색 (이미지 참고)
                        tension: 0.3,
                        fill: false,
                        order: 0, // ⭐️ 선이 가장 위에 오도록
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '유동부채',
                        data: chartData.current_liabilities,
                        backgroundColor: 'rgba(239, 83, 80, 0.8)', // 핑크/빨강 (이미지 참고)
                        stack: 'liabilityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '비유동부채',
                        data: chartData.non_current_liabilities,
                        backgroundColor: 'rgba(156, 204, 101, 0.8)', // 연두색 (이미지 참고)
                        stack: 'liabilityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: '삼성전자 부채 현황 (2016~)', font: { size: 16, weight: 'bold' }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                if (value !== null) {
                                    label += trilFormatter(value);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    'y_amount': {
                        beginAtZero: true, 
                        stacked: true,
                        ticks: {
                            callback: trilFormatter
                        },
                        title: {
                            display: true,
                            text: '금액 (조 원)'
                        }
                    }
                }
            }
        });
    }
    /**
     * [메인] 차트 초기화 범용 함수 (기존 로직)
     */
    async function initChart(apiUrl, createChartFn) {
        try {
            console.log(`API(${apiUrl}) 요청 중...`);
            const response = await fetch(apiUrl);
            const result = await response.json();

            if (result.status === 'success') {
                createChartFn(result.data);
            } else {
                console.error(`API 에러 (${apiUrl}):`, result.message);
            }
        } catch (error) {
            console.error(`Fetch 에러 (${apiUrl}):`, error);
            if (apiUrl === REVENUE_API_URL) {
                alert("백엔드 서버(localhost:8000)가 실행 중인지 확인하세요!");
            }
        }
    }


    // --- 스크립트 실행 시작! (5개 차트 모두 로드) ---
    initChart(REVENUE_API_URL, createRevenueChart);       // 차트 1: 콤보 차트
    initChart(RATIO_API_URL, createRevenueRatioChart);   // 차트 2: 매출 구성비중 차트
    initChart(ICR_API_URL, createICRChart);              // 차트 3: 이자보상배율 차트
    initChart(NET_INCOME_API_URL, createNetIncomeChart); // 차트 4: 당기순이익 차트
    initChart(GROWTH_API_URL, createGrowthChart);
    initChart(STABILITY_API_URL, createStabilityChart);
    initChart(DIVIDEND_SUMMARY_API_URL, createDividendSummaryChart);
    initChart(CASH_FLOW_API_URL, createCashFlowChart);
    initChart(CAPEX_CASH_FLOW_TTM_API_URL, createCapexCashFlowTTMChart);
    initChart(BALANCE_SHEET_API_URL, createBalanceSheetChart);
    initChart(EQUITY_COMPOSITION_API_URL, createEquityChart);
    initChart(LIABILITIES_API_URL, createLiabilitiesChart);

});
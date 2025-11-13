document.addEventListener('DOMContentLoaded', () => {

    // [⭐️ 추가 v4.9] "조"와 "억"을 동적으로 변환하는 헬퍼 함수
    function formatCurrency(value) {
        if (value === null || value === undefined) return 'N/A';
        
        const oneTrillion = 1_0000_0000_0000;
        const oneHundredMillion = 100_000_000;

        // 1조원 이상일 경우 (예: 1.2조, -9.5조)
        if (Math.abs(value) >= oneTrillion) {
            return (value / oneTrillion).toFixed(1) + '조';
        }
        
        // 1조원 미만 1억원 이상일 경우 (예: 2000억, -2500억)
        if (Math.abs(value) >= oneHundredMillion) {
            return (value / oneHundredMillion).toFixed(0) + '억';
        }
        
        // 1억원 미만일 경우 (예: 0.5억)
        return (value / oneHundredMillion).toFixed(1) + '억';
    }

    // --- 1. [수정] 설정: API 기본 주소 및 테스트할 기업 코드 ---
    const API_BASE_URL = 'http://localhost:8000/api';
    const CURRENT_CORP_CODE = '00105873'; // ⭐️ 테스트할 기업 코드 (예: 고려아연)
    
    // API 엔드포인트 이름 정의
    const ENDPOINTS = {
        REVENUE: 'quarterly-data',
        RATIO: 'revenue-ratio',
        ICR: 'icr',
        NET_INCOME: 'net-income',
        GROWTH: 'growth',
        STABILITY: 'stability',
        DIVIDEND: 'dividend-summary',
        CASH_FLOW_TTM: 'cash-flow-ttm', // ⭐️ 9번, 10번 차트가 공통으로 사용
        BALANCE_SHEET: 'balance-sheet',
        EQUITY: 'equity-composition',
        LIABILITIES: 'liabilities'
    };

    /**
     * [차트 1] 콤보 차트 생성 함수
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
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true, 
                plugins: {
                    title: { display: true, text: `[${CURRENT_CORP_CODE}] 분기별 주요 손익 (2016~2025)`, font: { size: 16, weight: 'bold' } },
                    legend: { position: 'top', align: 'center', labels: { padding: 20, usePointStyle: true, pointStyle: 'rectRounded' } },
                    tooltip: {
                        mode: 'index', intersect: false, itemSort: (a, b) => a.dataset.tooltipOrder - b.dataset.tooltipOrder,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                label += formatCurrency(value); // ⭐️ [수정 v4.9]
                                return label;
                            }
                        }
                    },
                },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    'y-revenue': { 
                        type: 'linear', position: 'left', stacked: true, beginAtZero: true,
                        ticks: { callback: formatCurrency } // ⭐️ [수정 v4.9]
                    }
                }
            }
        });
    }

    /**
     * [차트 2] 매출 구성비중 차트 생성 함수
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
                        display: true, text: `[${CURRENT_CORP_CODE}] 매출 구성비중 (100% Stacked)`, font: { size: 16, weight: 'bold' }
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
     * [차트 3] 이자보상배율(ICR) 차트 생성 함수
     */
    function createICRChart(chartData) {
        console.log("🛠️ [차트 3] 이자보상배율(ICR) 차트를 시작합니다...");
        const ctx = document.getElementById('icrChart').getContext('2d');

        new Chart(ctx, {
            type: 'line', 
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: '이자보상배율 (ICR)',
                    data: chartData.icr_ratio,
                    borderColor: '#29b6f6', 
                    backgroundColor: 'rgba(41, 182, 246, 0.5)',
                    fill: true,
                    tension: 0.4, 
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: `[${CURRENT_CORP_CODE}] 이자보상배율 (ICR)`, font: { size: 16, weight: 'bold' }
                    },
                    legend: { display: false }, 
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
     * [차트 4] 당기순이익 차트 생성 함수
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
                        display: true, text: `[${CURRENT_CORP_CODE}] 분기별 당기순이익`, font: { size: 16, weight: 'bold' }
                    },
                    legend: { display: false },
                    tooltip: {
                        mode: 'index', intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                const value = context.parsed.y;
                                label += formatCurrency(value); // ⭐️ [수정 v4.9]
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
                            callback: formatCurrency // ⭐️ [수정 v4.9]
                        }
                    }
                }
            }
        });
    }

    /**
     * [차트 5] 성장성 지표(YoY) 차트
     */
    function createGrowthChart(chartData) {
        console.log("🛠️ [차트 5] 성장성 지표(YoY) 차트를 시작합니다...");
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
                        yAxisID: 'y_revenue_growth', 
                    },
                    {
                        label: '영업이익증가율(YoY)',
                        data: chartData.yoy_op_income_growth,
                        borderColor: '#ef5350', 
                        backgroundColor: 'rgba(239, 83, 80, 0.3)',
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y_op_income_growth', 
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: `[${CURRENT_CORP_CODE}] 성장성 지표 (YoY)`, font: { size: 16, weight: 'bold' }
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
                scales: {
                    x: { grid: { display: false } },
                    'y_revenue_growth': { 
                        type: 'linear',
                        position: 'left',
                        beginAtZero: false, 
                        ticks: {
                            callback: (value) => value.toFixed(1) + '%' 
                        },
                        title: { 
                            display: true,
                            text: '매출액증가율 (%)'
                        }
                    },
                    'y_op_income_growth': { 
                        type: 'linear',
                        position: 'right', 
                        beginAtZero: false, 
                        ticks: {
                            callback: (value) => value.toFixed(1) + '%' 
                        },
                        title: { 
                            display: true,
                            text: '영업이익증가율 (%)'
                        },
                        grid: { 
                            drawOnChartArea: false 
                        }
                    }
                }
            }
        });
    }

    /**
     * [차트 6] 안정성 지표 차트
     */
    function createStabilityChart(chartData) {
        console.log("🛠️ [차트 6] 안정성 지표 차트를 시작합니다...");
        const ctx = document.getElementById('stabilityChart').getContext('2d'); 

        new Chart(ctx, {
            type: 'line', 
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '부채비율',
                        data: chartData.debt_ratio,
                        borderColor: '#ffa726', 
                        backgroundColor: 'rgba(255, 167, 38, 0.3)',
                        fill: false, 
                        tension: 0.4, 
                        yAxisID: 'y_debt_ratio', 
                    },
                    {
                        label: '유동비율',
                        data: chartData.current_ratio,
                        borderColor: '#66bb6a', 
                        backgroundColor: 'rgba(102, 187, 106, 0.3)',
                        fill: false, 
                        tension: 0.4,
                        yAxisID: 'y_current_ratio', 
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: `[${CURRENT_CORP_CODE}] 안정성 지표 (2023.3Q~)`, font: { size: 16, weight: 'bold' }
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
                scales: {
                    x: { grid: { display: false } },
                    'y_debt_ratio': { 
                        type: 'linear',
                        position: 'left',
                        beginAtZero: true, 
                        ticks: {
                            callback: (value) => value.toFixed(1) + '%' 
                        },
                        title: { 
                            display: true,
                            text: '부채비율 (%)'
                        }
                    },
                    'y_current_ratio': { 
                        type: 'linear',
                        position: 'right', 
                        beginAtZero: true, 
                        ticks: {
                            callback: (value) => value.toFixed(1) + '%' 
                        },
                        title: { 
                            display: true,
                            text: '유동비율 (%)'
                        },
                        grid: { 
                            drawOnChartArea: false 
                        }
                    }
                }
            }
        });
    }

    /**
     * [차트 7] EPS/DPS/배당성향 차트
     */
    function createDividendSummaryChart(chartData) {
        console.log("🛠️ [차트 7] EPS/DPS/배당성향 차트를 시작합니다...");
        const ctx = document.getElementById('dividendSummaryChart').getContext('2d'); 

        new Chart(ctx, {
            type: 'bar', 
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '주당순이익(EPS)',
                        data: chartData.eps,
                        backgroundColor: 'rgba(144, 202, 249, 0.7)', 
                        borderColor: 'rgba(144, 202, 249, 1)',
                        borderWidth: 1,
                        yAxisID: 'y_amount', 
                    },
                    {
                        label: '주당배당금(DPS)',
                        data: chartData.dps,
                        backgroundColor: 'rgba(30, 136, 229, 0.7)', 
                        borderColor: 'rgba(30, 136, 229, 1)',
                        borderWidth: 1,
                        yAxisID: 'y_amount', 
                    },
                    {
                        label: '배당성향(%)',
                        data: chartData.payout_ratio,
                        type: 'line', 
                        borderColor: '#ec407a', 
                        backgroundColor: 'rgba(236, 64, 122, 0.3)',
                        fill: false, 
                        tension: 0.4, 
                        yAxisID: 'y_percent', 
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: `[${CURRENT_CORP_CODE}] 분기별 EPS, DPS 및 배당성향 (2023.3Q~)`, font: { size: 16, weight: 'bold' }
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
                scales: {
                    x: { grid: { display: false } },
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

    /**
     * [차트 8] 현금흐름(FCF) 차트
     */
    function createCashFlowChart(chartData) {
        console.log("🛠️ [차트 8] 현금흐름(TTM) 차트를 시작합니다...");
        const ctx = document.getElementById('cashFlowChart').getContext('2d'); 

        new Chart(ctx, {
            type: 'bar', 
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: 'FCF (잉여현금흐름)',
                        data: chartData.fcf,
                        backgroundColor: 'rgba(66, 165, 245, 0.7)', 
                        order: 1 
                    },
                    {
                        label: '영업현금흐름(OCF)',
                        data: chartData.ocf,
                        type: 'line',
                        borderColor: '#f48fb1', 
                        tension: 0.3,
                        fill: false,
                        order: 0 
                    },
                    {
                        label: '투자현금흐름(ICF)',
                        data: chartData.icf,
                        type: 'line',
                        borderColor: '#ffb74d', 
                        tension: 0.3,
                        fill: false,
                        order: 0
                    },
                    {
                        label: '재무현금흐름(FFCF)',
                        data: chartData.ffcf,
                        type: 'line',
                        borderColor: '#a5d6a7', 
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
                        display: true, text: `[${CURRENT_CORP_CODE}] 분기별 현금흐름 (TTM)`, font: { size: 16, weight: 'bold' }
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
                                label += formatCurrency(value); // ⭐️ [수정 v4.9]
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { 
                        beginAtZero: false, 
                        ticks: {
                            callback: formatCurrency // ⭐️ [수정 v4.9]
                        },
                        title: {
                            display: true,
                            text: '금액 (조/억 원)'
                        }
                    }
                }
            }
        });
    }

    /**
     * [차트 9] CAPEX vs 현금흐름 TTM
     */
    function createCapexCashFlowTTMChart(chartData) {
        console.log("🛠️ [차트 9] CAPEX vs 현금흐름 (TTM) 차트를 시작합니다...");
        const ctx = document.getElementById('capexCashFlowTTMChart').getContext('2d'); 

        new Chart(ctx, {
            type: 'bar', 
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '영업현금흐름(OCF)',
                        data: chartData.ocf,
                        type: 'line', 
                        borderColor: '#f48fb1', 
                        tension: 0.3,
                        fill: false,
                        order: 0, 
                        yAxisID: 'y_amount' 
                    },
                    {
                        label: '자본적 지출(CAPEX)',
                        data: chartData.capex,
                        backgroundColor: 'rgba(255, 193, 7, 0.9)', 
                        stack: 'cashFlowStack', 
                        order: 1, 
                        yAxisID: 'y_amount'
                    },
                    {
                        label: 'FCF (잉여현금흐름)',
                        data: chartData.fcf,
                        backgroundColor: 'rgba(66, 165, 245, 0.9)', 
                        stack: 'cashFlowStack', 
                        order: 1,
                        yAxisID: 'y_amount'
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: `[${CURRENT_CORP_CODE}] CAPEX vs 현금흐름 (TTM)`, font: { size: 16, weight: 'bold' }
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
                                label += formatCurrency(value); // ⭐️ [수정 v4.9]
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
                            callback: formatCurrency // ⭐️ [수정 v4.9]
                        },
                        title: {
                            display: true,
                            text: '금액 (조/억 원)'
                        }
                    }
                }
            }
        });
    }

    /**
     * [차트 10] 자산의 구성
     */
    function createBalanceSheetChart(chartData) {
        console.log("🛠️ [차트 10] 자산의 구성 차트를 시작합니다...");
        const ctx = document.getElementById('balanceSheetChart').getContext('2d'); 

        new Chart(ctx, {
            type: 'bar', 
            data: {
                labels: chartData.labels, 
                datasets: [
                    {
                        label: '자산총계',
                        data: chartData.total_assets,
                        type: 'line', 
                        borderColor: '#f48fb1', 
                        tension: 0.3,
                        fill: false,
                        order: 0, 
                        yAxisID: 'y_amount' 
                    },
                    {
                        label: '유동자산',
                        data: chartData.current_assets, 
                        backgroundColor: 'rgba(255, 193, 7, 0.9)', 
                        stack: 'assetStack', 
                        order: 1, 
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '비유동자산',
                        data: chartData.non_current_assets, 
                        backgroundColor: 'rgba(66, 165, 245, 0.9)', 
                        stack: 'assetStack', 
                        order: 1,
                        yAxisID: 'y_amount'
                    }
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true, text: `[${CURRENT_CORP_CODE}] 자산의 구성 (2016~)`, font: { size: 16, weight: 'bold' }
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
                                label += formatCurrency(value); // ⭐️ [수정 v4.9]
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
                            callback: formatCurrency // ⭐️ [수정 v4.9]
                        },
                        title: {
                            display: true,
                            text: '금액 (조/억 원)'
                        }
                    }
                }
            }
        });
    }

    /**
     * [차트 11] 자본의 구성
     */
    function createEquityChart(chartData) {
        console.log("🛠️ [차트 11] 자본의 구성 차트를 시작합니다...");
        const ctx = document.getElementById('equityChart').getContext('2d'); 

        new Chart(ctx, {
            type: 'bar', 
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: '지배주주 자본총계',
                        data: chartData.total_equity,
                        type: 'line',
                        borderColor: '#81c784', 
                        tension: 0.3,
                        fill: false,
                        order: 0, 
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '이익잉여금',
                        data: chartData.retained_earnings,
                        backgroundColor: 'rgba(239, 83, 80, 0.8)', 
                        stack: 'equityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '기타자본항목',
                        data: chartData.other_capital,
                        backgroundColor: 'rgba(66, 165, 245, 0.8)', 
                        stack: 'equityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '자본잉여금',
                        data: chartData.capital_surplus,
                        backgroundColor: 'rgba(255, 238, 88, 0.9)', 
                        stack: 'equityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '자본금',
                        data: chartData.capital_stock,
                        backgroundColor: 'rgba(170, 170, 170, 0.8)', 
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
                        display: true, text: `[${CURRENT_CORP_CODE}] 자본의 구성 (2016~)`, font: { size: 16, weight: 'bold' }
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
                                label += formatCurrency(value); // ⭐️ [수정 v4.9]
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    'y_amount': {
                        beginAtZero: false, 
                        stacked: true,
                        ticks: {
                            callback: formatCurrency // ⭐️ [수정 v4.9]
                        },
                        title: {
                            display: true,
                            text: '금액 (조/억 원)'
                        }
                    }
                }
            }
        });
    }


    /**
     * [차트 12] 부채 현황
     */
    function createLiabilitiesChart(chartData) {
        console.log("🛠️ [차트 12] 부채 현황 차트를 시작합니다...");
        const ctx = document.getElementById('liabilitiesChart').getContext('2d'); 

        new Chart(ctx, {
            type: 'bar', 
            data: {
                labels: chartData.labels,
                datasets: [
                    {
                        label: '부채총계',
                        data: chartData.total_liabilities,
                        type: 'line',
                        borderColor: '#ffb74d', 
                        tension: 0.3,
                        fill: false,
                        order: 0, 
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '유동부채',
                        data: chartData.current_liabilities,
                        backgroundColor: 'rgba(239, 83, 80, 0.8)', 
                        stack: 'liabilityStack',
                        order: 1,
                        yAxisID: 'y_amount'
                    },
                    {
                        label: '비유동부채',
                        data: chartData.non_current_liabilities,
                        backgroundColor: 'rgba(156, 204, 101, 0.8)', 
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
                        display: true, text: `[${CURRENT_CORP_CODE}] 부채 현황 (2016~)`, font: { size: 16, weight: 'bold' }
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
                                label += formatCurrency(value); // ⭐️ [수정 v4.9]
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
                            callback: formatCurrency // ⭐️ [수정 v4.9]
                        },
                        title: {
                            display: true,
                            text: '금액 (조/억 원)'
                        }
                    }
                }
            }
        });
    }
    
    /**
     * [메인] 차트 초기화 범용 함수
     */
    async function initChart(apiUrl, createChartFn) {
        try {
            console.log(`API(${apiUrl}) 요청 중...`);
            const response = await fetch(apiUrl);
            
            if (!response.ok) {
                // 404, 500 등 서버 에러
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();

            if (result.status === 'success') {
                createChartFn(result.data);
            } else {
                console.error(`API 에러 (${apiUrl}):`, result.message);
            }
        } catch (error) {
            // 네트워크 에러, CORS 에러, JSON 파싱 에러 등
            console.error(`Fetch 에러 (${apiUrl}):`, error);
            if (createChartFn === createRevenueChart) {
                alert("백엔드 서버(localhost:8000)가 실행 중인지, \nCORS 설정이 올바른지 확인하세요!");
            }
        }
    }


    /**
     * ⭐️ [수정] 스크립트 실행 시작 함수
     * 지정된 corpCode를 기반으로 모든 차트 로드를 시작합니다.
     */
    function loadAllCharts(corpCode) {
        if (!corpCode) {
            alert("기업 코드가 지정되지 않았습니다!");
            return;
        }
        
        console.log(`--- [${corpCode}] 기업 데이터 로드 시작 ---`);

        // URL 생성 헬퍼
        const getUrl = (endpoint) => `${API_BASE_URL}/${corpCode}/${endpoint}`;

        // 각 차트 초기화
        initChart(getUrl(ENDPOINTS.REVENUE), createRevenueChart);
        initChart(getUrl(ENDPOINTS.RATIO), createRevenueRatioChart);
        initChart(getUrl(ENDPOINTS.ICR), createICRChart);
        initChart(getUrl(ENDPOINTS.NET_INCOME), createNetIncomeChart);
        initChart(getUrl(ENDPOINTS.GROWTH), createGrowthChart);
        initChart(getUrl(ENDPOINTS.STABILITY), createStabilityChart);
        initChart(getUrl(ENDPOINTS.DIVIDEND), createDividendSummaryChart);
        
        // ⭐️ 9번, 10번 차트는 동일한 TTM API 엔드포인트를 사용
        initChart(getUrl(ENDPOINTS.CASH_FLOW_TTM), createCashFlowChart);
        initChart(getUrl(ENDPOINTS.CASH_FLOW_TTM), createCapexCashFlowTTMChart);
        
        initChart(getUrl(ENDPOINTS.BALANCE_SHEET), createBalanceSheetChart);
        initChart(getUrl(ENDPOINTS.EQUITY), createEquityChart);
        initChart(getUrl(ENDPOINTS.LIABILITIES), createLiabilitiesChart);
    }

    // --- 스크립트 실행 시작! ---
    loadAllCharts(CURRENT_CORP_CODE);

});
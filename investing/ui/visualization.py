'text': '적금 데이터 없음',
            'y':0.5,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'middle'
        },
        annotations=[dict(
            text='적금 데이터가 없습니다.<br>적금을 추가하면 차트가 표시됩니다.',
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            font=dict(size=14)
        )]
    )
    
    return empty_fig, empty_fig, empty_fig

def create_performance_dashboard(user_id, period='1y'):
    """
    성과 대시보드 차트 생성
    
    Args:
        user_id (int): 사용자 ID
        period (str): 기간 ('1m', '3m', '6m', '1y', 'all')
        
    Returns:
        tuple: (성과 지표 차트, 위험 분석 차트)
    """
    # 포트폴리오 성과 지표 조회
    performance_metrics = get_portfolio_performance_metrics(user_id, period)
    
    # 위험 분석 지표 조회
    risk_metrics = calculate_portfolio_risk(user_id)
    
    # 1. 성과 지표 차트 (게이지 차트)
    fig_performance = make_subplots(
        rows=2, cols=2,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}],
            [{"type": "indicator"}, {"type": "indicator"}]
        ],
        subplot_titles=(
            "총 수익률", "연환산 수익률", "최대 낙폭", "샤프 비율"
        )
    )
    
    # 총 수익률 게이지
    fig_performance.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=performance_metrics.get("total_return", 0),
            number={"suffix": "%", "font": {"size": 24}},
            gauge={
                "axis": {"range": [-20, 40], "tickwidth": 1},
                "bar": {"color": CHART_COLORS["blue_scale"][2]},
                "steps": [
                    {"range": [-20, 0], "color": "rgba(255, 0, 0, 0.2)"},
                    {"range": [0, 20], "color": "rgba(0, 255, 0, 0.1)"},
                    {"range": [20, 40], "color": "rgba(0, 255, 0, 0.3)"}
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 0
                }
            }
        ),
        row=1, col=1
    )
    
    # 연환산 수익률 게이지
    fig_performance.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=performance_metrics.get("annualized_return", 0),
            number={"suffix": "%", "font": {"size": 24}},
            gauge={
                "axis": {"range": [-20, 40], "tickwidth": 1},
                "bar": {"color": CHART_COLORS["green_scale"][2]},
                "steps": [
                    {"range": [-20, 0], "color": "rgba(255, 0, 0, 0.2)"},
                    {"range": [0, 20], "color": "rgba(0, 255, 0, 0.1)"},
                    {"range": [20, 40], "color": "rgba(0, 255, 0, 0.3)"}
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 0
                }
            }
        ),
        row=1, col=2
    )
    
    # 최대 낙폭 게이지
    fig_performance.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=performance_metrics.get("max_drawdown", 0),
            number={"suffix": "%", "font": {"size": 24}},
            gauge={
                "axis": {"range": [-50, 0], "tickwidth": 1},
                "bar": {"color": CHART_COLORS["vivid"][0]},
                "steps": [
                    {"range": [-50, -30], "color": "rgba(255, 0, 0, 0.3)"},
                    {"range": [-30, -10], "color": "rgba(255, 165, 0, 0.3)"},
                    {"range": [-10, 0], "color": "rgba(0, 255, 0, 0.1)"}
                ],
                "threshold": {
                    "line": {"color": "green", "width": 4},
                    "thickness": 0.75,
                    "value": -10
                }
            }
        ),
        row=2, col=1
    )
    
    # 샤프 비율 게이지
    fig_performance.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=performance_metrics.get("sharpe_ratio", 0),
            number={"font": {"size": 24}},
            gauge={
                "axis": {"range": [-1, 3], "tickwidth": 1},
                "bar": {"color": CHART_COLORS["wealth"][4]},
                "steps": [
                    {"range": [-1, 0], "color": "rgba(255, 0, 0, 0.2)"},
                    {"range": [0, 1], "color": "rgba(255, 165, 0, 0.2)"},
                    {"range": [1, 2], "color": "rgba(0, 255, 0, 0.2)"},
                    {"range": [2, 3], "color": "rgba(0, 255, 0, 0.4)"}
                ],
                "threshold": {
                    "line": {"color": "green", "width": 4},
                    "thickness": 0.75,
                    "value": 1
                }
            }
        ),
        row=2, col=2
    )
    
    fig_performance.update_layout(
        title={
            'text': f'포트폴리오 성과 지표 ({period})',
            'y':0.97,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        height=500,
        margin=dict(l=30, r=30, t=80, b=30)
    )
    
    # 2. 위험 분석 차트
    fig_risk = make_subplots(
        rows=2, cols=2,
        specs=[
            [{"type": "indicator"}, {"type": "pie"}],
            [{"type": "indicator", "colspan": 2}, {}]
        ],
        subplot_titles=(
            "포트폴리오 베타", "섹터 집중도", "위험 레벨"
        )
    )
    
    # 베타 게이지
    fig_risk.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=risk_metrics.get("portfolio_beta", 1.0),
            number={"font": {"size": 24}},
            gauge={
                "axis": {"range": [0, 2], "tickwidth": 1},
                "bar": {"color": CHART_COLORS["blue_scale"][3]},
                "steps": [
                    {"range": [0, 0.8], "color": "rgba(0, 255, 0, 0.2)"},
                    {"range": [0.8, 1.2], "color": "rgba(255, 255, 0, 0.2)"},
                    {"range": [1.2, 2], "color": "rgba(255, 0, 0, 0.2)"}
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 1
                }
            }
        ),
        row=1, col=1
    )
    
    # 섹터 집중도 (HHI 기반 도넛 차트)
    sector_concentration = risk_metrics.get("sector_concentration", {})
    hhi = sector_concentration.get("hhi", 0)
    interpretation = sector_concentration.get("interpretation", "데이터 없음")
    
    # 집중도에 따른 색상 매핑
    if hhi < 1500:
        color = "green"  # 낮은 집중도
    elif hhi < 2500:
        color = "orange"  # 중간 집중도
    else:
        color = "red"  # 높은 집중도
    
    fig_risk.add_trace(
        go.Pie(
            labels=["집중도", ""],
            values=[hhi, 10000 - hhi],
            hole=.7,
            marker_colors=[color, "rgba(0,0,0,0.1)"],
            textinfo='none',
            hoverinfo='none',
            showlegend=False
        ),
        row=1, col=2
    )
    
    # 섹터 집중도 부가 설명
    fig_risk.add_annotation(
        text=f"HHI: {hhi:,.0f}<br>{interpretation}",
        x=0.75, y=0.75,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(color="black", size=12)
    )
    
    # 위험 레벨 게이지
    risk_level = risk_metrics.get("risk_level", "알 수 없음")
    risk_level_map = {
        "매우 낮음": 1,
        "낮음": 2,
        "중간": 3,
        "높음": 4,
        "매우 높음": 5,
        "알 수 없음": 3  # 기본값
    }
    
    risk_value = risk_level_map.get(risk_level, 3)
    
    fig_risk.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=risk_value,
            number={"font": {"size": 24}},
            gauge={
                "axis": {"range": [0, 5], "tickvals": [1, 2, 3, 4, 5], "ticktext": ["매우 낮음", "낮음", "중간", "높음", "매우 높음"]},
                "bar": {"color": CHART_COLORS["vivid"][risk_value - 1]},
                "steps": [
                    {"range": [0, 1], "color": "rgba(0, 255, 0, 0.4)"},
                    {"range": [1, 2], "color": "rgba(144, 238, 144, 0.4)"},
                    {"range": [2, 3], "color": "rgba(255, 255, 0, 0.4)"},
                    {"range": [3, 4], "color": "rgba(255, 165, 0, 0.4)"},
                    {"range": [4, 5], "color": "rgba(255, 0, 0, 0.4)"}
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "thickness": 0.75,
                    "value": risk_value
                }
            },
            delta={"reference": 3, "valueformat": ".0f", "visible": False}  # 중간 값이 기준
        ),
        row=2, col=1
    )
    
    # 위험 레벨 텍스트 추가
    fig_risk.add_annotation(
        text=f"위험 레벨: {risk_level}",
        x=0.5, y=0.25,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(color="black", size=16)
    )
    
    fig_risk.update_layout(
        title={
            'text': '포트폴리오 위험 분석',
            'y':0.97,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        height=500,
        margin=dict(l=30, r=30, t=80, b=30)
    )
    
    return fig_performance, fig_risk

def create_savings_performance_chart(user_id):
    """
    적금 성과 차트 생성
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        tuple: (월별 저축 추이 차트, 적금 달성률 차트)
    """
    # 적금 성과 분석 데이터 조회
    savings_performance = analyze_savings_performance(user_id)
    
    # 저축 계획 데이터 조회
    savings_plans = get_savings_plans(user_id)
    
    # 1. 월별 저축 추이 차트
    monthly_trend = savings_performance.get("monthly_trend", [])
    
    if monthly_trend:
        # 월별 데이터 정렬
        months = [item.get("month") for item in monthly_trend]
        deposits = [item.get("deposits", 0) for item in monthly_trend]
        withdrawals = [item.get("withdrawals", 0) for item in monthly_trend]
        net = [item.get("net", 0) for item in monthly_trend]
        
        fig_trend = go.Figure()
        
        # 입금액 막대 차트
        fig_trend.add_trace(go.Bar(
            x=months,
            y=deposits,
            name='입금액',
            marker_color=CHART_COLORS["green_scale"][2],
            hovertemplate='%{x}<br>입금액: %{y:,.0f}원<extra></extra>'
        ))
        
        # 출금액 막대 차트 (음수로 표시)
        fig_trend.add_trace(go.Bar(
            x=months,
            y=[-w for w in withdrawals],
            name='출금액',
            marker_color=CHART_COLORS["vivid"][0],
            hovertemplate='%{x}<br>출금액: %{y:,.0f}원<extra></extra>'
        ))
        
        # 순 저축액 선 차트
        fig_trend.add_trace(go.Scatter(
            x=months,
            y=net,
            name='순 저축액',
            line=dict(color=CHART_COLORS["blue_scale"][0], width=3),
            hovertemplate='%{x}<br>순 저축액: %{y:,.0f}원<extra></extra>'
        ))
        
        fig_trend.update_layout(
            title={
                'text': '월별 저축 추이',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title='월',
            yaxis_title='금액 (원)',
            template='plotly_white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=30, r=30, t=80, b=50),
            barmode='relative'
        )
    else:
        # 데이터가 없는 경우 빈 차트
        fig_trend = go.Figure()
        fig_trend.update_layout(
            title={
                'text': '월별 저축 추이',
                'y':0.5,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'middle'
            },
            annotations=[dict(
                text='저축 거래내역 데이터가 없습니다.',
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                font=dict(size=14)
            )]
        )
    
    # 2. 적금 목표 달성률 차트
    if savings_plans:
        fig_goals = go.Figure()
        
        # 달성률에 따른 색상 매핑 함수
        def get_color(achievement_rate):
            if achievement_rate < 30:
                return CHART_COLORS["vivid"][0]  # 빨강
            elif achievement_rate < 70:
                return CHART_COLORS["vivid"][2]  # 노랑
            else:
                return CHART_COLORS["green_scale"][2]  # 초록
        
        # 계획별 데이터
        plan_names = []
        achievement_rates = []
        colors = []
        
        for plan in savings_plans:
            plan_names.append(plan["name"])
            rate = plan.get("achievement_rate", 0)
            achievement_rates.append(rate)
            colors.append(get_color(rate))
        
        # 수평 막대 차트
        fig_goals.add_trace(go.Bar(
            x=achievement_rates,
            y=plan_names,
            orientation='h',
            marker_color=colors,
            text=[f"{rate:.1f}%" for rate in achievement_rates],
            textposition='auto',
            hovertemplate='%{y}<br>달성률: %{x:.1f}%<extra></extra>'
        ))
        
        # 100% 라인 추가
        fig_goals.add_vline(
            x=100, 
            line_dash="dash", 
            line_color="green", 
            opacity=0.7,
            annotation_text="목표",
            annotation_position="top right"
        )
        
        fig_goals.update_layout(
            title={
                'text': '저축 목표 달성률',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title='달성률 (%)',
            xaxis=dict(range=[0, max(120, max(achievement_rates) * 1.1)]),
            template='plotly_white',
            showlegend=False,
            margin=dict(l=120, r=30, t=80, b=50)
        )
    else:
        # 데이터가 없는 경우 빈 차트
        fig_goals = go.Figure()
        fig_goals.update_layout(
            title={
                'text': '저축 목표 달성률',
                'y':0.5,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'middle'
            },
            annotations=[dict(
                text='저축 목표 데이터가 없습니다.',
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                font=dict(size=14)
            )]
        )
    
    return fig_trend, fig_goals

def create_visualization_ui():
    """
    시각화 관련 UI 컴포넌트 생성
    
    Returns:
        tuple: (컨테이너 딕셔너리, 컴포넌트 딕셔너리)
    """
    # 포트폴리오 분석 화면
    with gr.Group(visible=False) as portfolio_analysis_container:
        gr.Markdown("## 포트폴리오 분석")
        
        with gr.Row():
            analysis_refresh_btn = gr.Button("분석 데이터 갱신", variant="primary")
            period_selector = gr.Dropdown(
                ["1개월", "3개월", "6개월", "1년", "전체"],
                value="1년",
                label="기간 선택",
                interactive=True
            )
        
        # 포트폴리오 요약 정보
        with gr.Row():
            portfolio_summary_html = gr.HTML(
                """<div class="summary-card">
                   <h3>포트폴리오 요약 정보를 불러오는 중...</h3>
                   </div>"""
            )
        
        # 수익률 및 가치 추이 차트
        with gr.Row():
            returns_chart = gr.Plot(label="수익률 추이")
            value_chart = gr.Plot(label="포트폴리오 가치 추이")
        
        # 분포 차트들
        with gr.Row():
            country_chart = gr.Plot(label="국가별 분포")
            account_chart = gr.Plot(label="계좌별 분포")
        
        with gr.Row():
            broker_chart = gr.Plot(label="증권사별 분포")
            sector_chart = gr.Plot(label="섹터별 분포")
        
        # 상위 종목 차트
        with gr.Row():
            top_stocks_chart = gr.Plot(label="상위 종목")
    
    # 자산 배분 화면
    with gr.Group(visible=False) as asset_allocation_container:
        gr.Markdown("## 자산 배분 현황")
        
        allocation_refresh_btn = gr.Button("자산 데이터 갱신", variant="primary")
        
        with gr.Row():
            asset_allocation_chart = gr.Plot(label="자산 배분")
        
        with gr.Row():
            savings_chart = gr.Plot(label="적금 현황")
            savings_timeline_chart = gr.Plot(label="적금 만기일 타임라인")
        
        with gr.Row():
            savings_bank_chart = gr.Plot(label="은행별 적금 분포")
    
    # 성과 분석 화면
    with gr.Group(visible=False) as performance_container:
        gr.Markdown("## 투자 성과 분석")
        
        with gr.Row():
            performance_refresh_btn = gr.Button("성과 데이터 갱신", variant="primary")
            performance_period_selector = gr.Dropdown(
                ["1m", "3m", "6m", "1y", "all"],
                value="1y",
                label="기간 선택",
                interactive=True
            )
        
        # 성과 지표 차트
        with gr.Row():
            performance_metrics_chart = gr.Plot(label="성과 지표")
            risk_analysis_chart = gr.Plot(label="위험 분석")
        
        # 적금 성과 차트
        with gr.Row():
            savings_trend_chart = gr.Plot(label="월별 저축 추이")
            savings_goals_chart = gr.Plot(label="저축 목표 달성률")
    
    # 컨테이너 및 컴포넌트 정리
    containers = {
        "portfolio_analysis": portfolio_analysis_container,
        "asset_allocation": asset_allocation_container,
        "performance": performance_container
    }
    
    components = {
        # 포트폴리오 분석 화면
        "analysis_refresh_btn": analysis_refresh_btn,
        "period_selector": period_selector,
        "portfolio_summary_html": portfolio_summary_html,
        "returns_chart": returns_chart,
        "value_chart": value_chart,
        "country_chart": country_chart,
        "account_chart": account_chart,
        "broker_chart": broker_chart,
        "sector_chart": sector_chart,
        "top_stocks_chart": top_stocks_chart,
        
        # 자산 배분 화면
        "allocation_refresh_btn": allocation_refresh_btn,
        "asset_allocation_chart": asset_allocation_chart,
        "savings_chart": savings_chart,
        "savings_timeline_chart": savings_timeline_chart,
        "savings_bank_chart": savings_bank_chart,
        
        # 성과 분석 화면
        "performance_refresh_btn": performance_refresh_btn,
        "performance_period_selector": performance_period_selector,
        "performance_metrics_chart": performance_metrics_chart,
        "risk_analysis_chart": risk_analysis_chart,
        "savings_trend_chart": savings_trend_chart,
        "savings_goals_chart": savings_goals_chart
    }
    
    return containers, components

def setup_visualization_events(app, session_state, components, containers):
    """
    시각화 관련 이벤트 설정
    
    Args:
        app: Gradio 앱 인스턴스
        session_state: 세션 상태 컴포넌트
        components: UI 컴포넌트 딕셔너리
        containers: UI 컨테이너 딕셔너리
    """
    # 포트폴리오 분석 갱신 버튼 클릭 이벤트
    def update_portfolio_analysis(state, period_str):
        if not state or not state.get("user_id"):
            return (None, None, None, None, None, None, None, 
                    """<div class="summary-card"><h3>로그인이 필요합니다</h3></div>""")
        
        # 기간 문자열을 API 파라미터로 변환
        period_map = {
            "1개월": "1m",
            "3개월": "3m",
            "6개월": "6m",
            "1년": "1y",
            "전체": "all"
        }
        period = period_map.get(period_str, "1y")
        
        # 차트 생성
        returns_fig, value_fig = create_portfolio_chart(state["user_id"])
        country_fig, account_fig, broker_fig, sector_fig = create_distribution_charts(state["user_id"])
        top_stocks_fig = create_top_stocks_chart(state["user_id"])
        
        # 포트폴리오 요약 정보 HTML 생성
        summary_html = create_portfolio_summary_html(state["user_id"])
        
        return (
            returns_fig, value_fig, country_fig, account_fig, 
            broker_fig, sector_fig, top_stocks_fig, summary_html
        )
    
    components["analysis_refresh_btn"].click(
        fn=update_portfolio_analysis,
        inputs=[session_state, components["period_selector"]],
        outputs=[
            components["returns_chart"],
            components["value_chart"],
            components["country_chart"],
            components["account_chart"],
            components["broker_chart"],
            components["sector_chart"],
            components["top_stocks_chart"],
            components["portfolio_summary_html"]
        ]
    )
    
    # 기간 선택 변경 이벤트
    components["period_selector"].change(
        fn=update_portfolio_analysis,
        inputs=[session_state, components["period_selector"]],
        outputs=[
            components["returns_chart"],
            components["value_chart"],
            components["country_chart"],
            components["account_chart"],
            components["broker_chart"],
            components["sector_chart"],
            components["top_stocks_chart"],
            components["portfolio_summary_html"]
        ]
    )
    
    # 자산 배분 갱신 버튼 클릭 이벤트
    def update_asset_allocation(state):
        if not state or not state.get("user_id"):
            return None, None, None, None
        
        allocation_fig = create_asset_allocation_chart(state["user_id"])
        savings_fig, timeline_fig, banks_fig = create_savings_charts(state["user_id"])
        
        return allocation_fig, savings_fig, timeline_fig, banks_fig
    
    components["allocation_refresh_btn"].click(
        fn=update_asset_allocation,
        inputs=[session_state],
        outputs=[
            components["asset_allocation_chart"],
            components["savings_chart"],
            components["savings_timeline_chart"],
            components["savings_bank_chart"]
        ]
    )
    
    # 성과 분석 갱신 버튼 클릭 이벤트
    def update_performance_analysis(state, period):
        if not state or not state.get("user_id"):
            return None, None, None, None
        
        performance_fig, risk_fig = create_performance_dashboard(state["user_id"], period)
        savings_trend_fig, savings_goals_fig = create_savings_performance_chart(state["user_id"])
        
        return performance_fig, risk_fig, savings_trend_fig, savings_goals_fig
    
    components["performance_refresh_btn"].click(
        fn=update_performance_analysis,
        inputs=[session_state, components["performance_period_selector"]],
        outputs=[
            components["performance_metrics_chart"],
            components["risk_analysis_chart"],
            components["savings_trend_chart"],
            components["savings_goals_chart"]
        ]
    )
    
    # 성과 분석 기간 선택 변경 이벤트
    components["performance_period_selector"].change(
        fn=update_performance_analysis,
        inputs=[session_state, components["performance_period_selector"]],
        outputs=[
            components["performance_metrics_chart"],
            components["risk_analysis_chart"],
            components["savings_trend_chart"],
            components["savings_goals_chart"]
        ]
    )
    
    # 컨테이너가 표시될 때 자동으로 차트 로드
    def on_portfolio_analysis_show(state):
        if state and state.get("user_id"):
            period_str = "1년"  # 기본값
            return update_portfolio_analysis(state, period_str)
        return (None, None, None, None, None, None, None, 
                """<div class="summary-card"><h3>로그인이 필요합니다</h3></div>""")
    
    def on_asset_allocation_show(state):
        if state and state            "summary": {"total_value": 0, "total_invested": 0, "total_gain_loss": 0, "total_return": 0, "savings_total": 0, "total_assets": 0},
            "distributions": {"country": {}, "account": {}, "broker": {}, "sector": {}},
            "top_stocks": [],
            "history": [],
            "savings": []
        }
    def calculate_portfolio_risk(user_id):
        return {
            "portfolio_beta": 1.0,
            "sector_concentration": {"hhi": 0, "interpretation": "데이터 없음"},
            "top5_concentration": 0,
            "risk_level": "알 수 없음"
        }
    def get_portfolio_performance_metrics(user_id, period='1y'):
        return {
            "total_return": 0,
            "annualized_return": 0,
            "volatility": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0
        }

try:
    from services.savings_service import (
        get_savings_summary,
        analyze_savings_performance,
        get_savings_plans
    )
except ImportError:
    # 더미 함수 정의
    def get_savings_summary(user_id):
        return {"total_amount": 0, "savings": []}
    def analyze_savings_performance(user_id):
        return {
            "summary": {"count": 0, "total_amount": 0, "avg_interest_rate": 0},
            "by_bank": {},
            "monthly_trend": []
        }
    def get_savings_plans(user_id):
        return []

# 차트 배색 테마
CHART_COLORS = {
    "blue_scale": ['#0437F2', '#0F5BE3', '#1F74D4', '#2F8DC5', '#3FA6B6', '#4FBFA7', '#5FD898'],
    "green_scale": ['#184E35', '#16613B', '#137441', '#108747', '#0E9A4D', '#0CAD53', '#09C059'],
    "pastel": ['#FFB5A7', '#FCD5CE', '#F8EDEB', '#F9DCC4', '#FEC89A', '#D8E2DC', '#ECE4DB', '#E8E8E4'],
    "vivid": ['#FF6B6B', '#FFD93D', '#6BCB77', '#4D96FF', '#9D65C9', '#FF9A3C', '#3C8DAD', '#FF5F9E'],
    "wealth": ['#00877F', '#6DECB9', '#ACF6C8', '#FFD6E0', '#FF8FAB', '#5E2F50', '#FFC93C', '#57BE83']
}

def create_portfolio_chart(user_id):
    """
    포트폴리오 수익률 및 가치 차트 생성
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        tuple: (수익률 차트, 가치 차트)
    """
    # 포트폴리오 정보 가져오기
    portfolio_data = get_portfolio_summary(user_id)
    
    # 수익률 차트
    if portfolio_data["history"]:
        dates = [item["date"] for item in portfolio_data["history"]]
        returns = [item.get("return_percent", 0) for item in portfolio_data["history"]]
        
        fig_returns = go.Figure()
        fig_returns.add_trace(go.Scatter(
            x=dates, 
            y=returns,
            mode='lines+markers',
            name='수익률 (%)',
            line=dict(color=CHART_COLORS["blue_scale"][0], width=2),
            hovertemplate='%{x}<br>수익률: %{y:.2f}%<extra></extra>'
        ))
        
        # 벤치마크 (KOSPI) 추가 - 더미 데이터, 실제로는 API로 가져와야 함
        if len(dates) > 1:
            # 더미 데이터 생성 (실제로는 API에서 가져와야 함)
            benchmark_returns = np.cumsum(np.random.normal(0, 0.5, len(dates))) + 3
            
            fig_returns.add_trace(go.Scatter(
                x=dates, 
                y=benchmark_returns,
                mode='lines',
                name='KOSPI',
                line=dict(color='gray', width=1.5, dash='dot'),
                hovertemplate='%{x}<br>KOSPI: %{y:.2f}%<extra></extra>'
            ))
        
        fig_returns.update_layout(
            title={
                'text': '포트폴리오 수익률 추이',
                'y':0.9,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title='날짜',
            yaxis_title='수익률 (%)',
            template='plotly_white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=20, r=20, t=60, b=40),
            hovermode="x unified"
        )
        
        # 0% 라인 추가
        fig_returns.add_hline(
            y=0, 
            line_dash="dash", 
            line_color="red", 
            opacity=0.5,
            annotation_text="손익분기점",
            annotation_position="bottom right"
        )
        
        # 자산 가치 차트
        values = [item.get("value", 0) for item in portfolio_data["history"]]
        realized_profits = [item.get("realized_profit", 0) for item in portfolio_data["history"]]
        unrealized_profits = [item.get("unrealized_profit", 0) for item in portfolio_data["history"]]
        
        fig_values = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 포트폴리오 가치 (주 y축)
        fig_values.add_trace(go.Scatter(
            x=dates, 
            y=values,
            mode='lines',
            name='포트폴리오 가치',
            line=dict(color=CHART_COLORS["blue_scale"][0], width=2.5),
            fill='tozeroy',
            fillcolor='rgba(0, 150, 255, 0.1)',
            hovertemplate='%{x}<br>총 가치: %{y:,.0f}원<extra></extra>'
        ), secondary_y=False)
        
        # 실현 이익과 미실현 이익 추가 (보조 y축)
        if any(realized_profits) or any(unrealized_profits):
            # 실현 이익
            fig_values.add_trace(go.Bar(
                x=dates,
                y=realized_profits,
                name='실현 손익',
                marker_color=CHART_COLORS["green_scale"][2],
                opacity=0.7,
                hovertemplate='%{x}<br>실현 손익: %{y:,.0f}원<extra></extra>'
            ), secondary_y=True)
            
            # 미실현 이익
            fig_values.add_trace(go.Bar(
                x=dates,
                y=unrealized_profits,
                name='미실현 손익',
                marker_color=CHART_COLORS["blue_scale"][3],
                opacity=0.7,
                hovertemplate='%{x}<br>미실현 손익: %{y:,.0f}원<extra></extra>'
            ), secondary_y=True)
        
        fig_values.update_layout(
            title={
                'text': '포트폴리오 가치 및 손익 추이',
                'y':0.9,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            template='plotly_white',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=20, r=20, t=60, b=40),
            barmode='group',
            hovermode="x unified"
        )
        
        fig_values.update_xaxes(title_text="날짜")
        fig_values.update_yaxes(title_text="포트폴리오 가치 (원)", secondary_y=False)
        fig_values.update_yaxes(title_text="손익 (원)", secondary_y=True)
        
        return fig_returns, fig_values
    
    # 데이터가 없는 경우 빈 차트 반환
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': '데이터가 충분하지 않습니다',
            'y':0.5,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'middle'
        },
        annotations=[dict(
            text='포트폴리오 히스토리 데이터가 없습니다.<br>더 많은 거래를 기록하면 차트가 표시됩니다.',
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            font=dict(size=14)
        )]
    )
    
    return empty_fig, empty_fig

def create_distribution_charts(user_id):
    """
    포트폴리오 분포 차트 생성
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        tuple: (국가별 차트, 계좌별 차트, 증권사별 차트, 섹터별 차트)
    """
    # 포트폴리오 정보 가져오기
    portfolio_data = get_portfolio_summary(user_id)
    
    # 국가별 분포
    country_data = portfolio_data["distributions"]["country"]
    account_data = portfolio_data["distributions"]["account"] 
    broker_data = portfolio_data["distributions"]["broker"]
    sector_data = portfolio_data["distributions"]["sector"]
    
    if country_data:
        # 국가별 분포 차트
        fig_country = go.Figure(data=[go.Pie(
            labels=list(country_data.keys()),
            values=list(country_data.values()),
            hole=.4,
            marker=dict(colors=CHART_COLORS["blue_scale"]),
            textinfo='label+percent',
            insidetextorientation='radial',
            hovertemplate='%{label}<br>금액: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
        )])
        
        fig_country.update_layout(
            title={
                'text': '국가별 투자 분포',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            template='plotly_white',
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )
        
        # 계좌별 분포 차트
        fig_account = go.Figure(data=[go.Pie(
            labels=list(account_data.keys()),
            values=list(account_data.values()),
            hole=.4,
            marker=dict(colors=CHART_COLORS["green_scale"]),
            textinfo='label+percent',
            insidetextorientation='radial',
            hovertemplate='%{label}<br>금액: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
        )])
        
        fig_account.update_layout(
            title={
                'text': '계좌별 투자 분포',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            template='plotly_white',
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )
        
        # 증권사별 분포 차트
        fig_broker = go.Figure(data=[go.Pie(
            labels=list(broker_data.keys()),
            values=list(broker_data.values()),
            hole=.4,
            marker=dict(colors=CHART_COLORS["vivid"]),
            textinfo='label+percent',
            insidetextorientation='radial',
            hovertemplate='%{label}<br>금액: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
        )])
        
        fig_broker.update_layout(
            title={
                'text': '증권사별 투자 분포',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            template='plotly_white',
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )
        
        # 섹터별 분포 차트
        fig_sector = go.Figure(data=[go.Pie(
            labels=list(sector_data.keys()),
            values=list(sector_data.values()),
            hole=.4,
            marker=dict(colors=CHART_COLORS["wealth"]),
            textinfo='label+percent',
            insidetextorientation='radial',
            hovertemplate='%{label}<br>금액: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
        )])
        
        fig_sector.update_layout(
            title={
                'text': '섹터별 투자 분포',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            template='plotly_white',
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )
        
        return fig_country, fig_account, fig_broker, fig_sector
    
    # 데이터가 없는 경우 빈 차트 반환
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': '데이터가 충분하지 않습니다',
            'y':0.5,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'middle'
        },
        annotations=[dict(
            text='포트폴리오 데이터가 없습니다.<br>종목을 추가하면 차트가 표시됩니다.',
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            font=dict(size=14)
        )]
    )
    
    return empty_fig, empty_fig, empty_fig, empty_fig

def create_top_stocks_chart(user_id):
    """
    상위 종목 차트 생성
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        plotly.graph_objects.Figure: 상위 종목 차트
    """
    # 포트폴리오 정보 가져오기
    portfolio_data = get_portfolio_summary(user_id)
    
    # 상위 종목 데이터
    top_stocks = portfolio_data.get("top_stocks", [])
    
    if top_stocks:
        # 종목별 색상 매핑 (국가별로 색상 다르게)
        colors = {}
        unique_countries = set(stock.get('country', '기타') for stock in top_stocks)
        color_map = dict(zip(unique_countries, CHART_COLORS["vivid"][:len(unique_countries)]))
        
        for stock in top_stocks:
            country = stock.get('country', '기타')
            colors[stock['name']] = color_map.get(country, '#888888')
        
        # 수평 막대 차트 생성
        fig = go.Figure()
        
        # 상위 순서로 정렬 (역순으로 추가하여 위에서부터 내림차순으로 표시)
        sorted_stocks = sorted(top_stocks, key=lambda x: x['value'])
        
        for stock in sorted_stocks:
            stock_name = stock['name']
            fig.add_trace(go.Bar(
                x=[stock['value']],
                y=[stock_name],
                orientation='h',
                name=stock_name,
                marker_color=colors.get(stock_name, '#888888'),
                text=f"{stock['weight']:.1f}%",
                textposition='inside',
                insidetextanchor='middle',
                hovertemplate='%{y}<br>평가액: %{x:,.0f}원<br>비중: %{text}<extra></extra>'
            ))
        
        fig.update_layout(
            title={
                'text': '상위 종목 투자 금액',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title='평가액 (원)',
            template='plotly_white',
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20),
            height=400
        )
        
        return fig
    
    # 데이터가 없는 경우 빈 차트 반환
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': '상위 종목 데이터 없음',
            'y':0.5,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'middle'
        },
        annotations=[dict(
            text='포트폴리오에 종목이 없습니다.',
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            font=dict(size=14)
        )]
    )
    
    return empty_fig

def create_asset_allocation_chart(user_id):
    """
    자산 배분 차트 생성
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        plotly.graph_objects.Figure: 자산 배분 차트
    """
    # 포트폴리오 정보 가져오기
    portfolio_data = get_portfolio_summary(user_id)
    
    # 주식과 적금 비중 계산
    stock_value = portfolio_data["summary"]["total_value"]
    savings_value = portfolio_data["summary"]["savings_total"]
    
    # 자산 배분 파이 차트
    if stock_value > 0 or savings_value > 0:
        # 데이터 구성
        labels = []
        values = []
        colors = []
        
        if stock_value > 0:
            labels.append("주식")
            values.append(stock_value)
            colors.append(CHART_COLORS["blue_scale"][1])
        
        if savings_value > 0:
            labels.append("적금")
            values.append(savings_value)
            colors.append(CHART_COLORS["green_scale"][1])
        
        # 현금 잔고 추가 (예시, 실제로는 데이터베이스에서 가져와야 함)
        cash_value = portfolio_data["summary"].get("cash_balance", 0)
        if cash_value > 0:
            labels.append("현금")
            values.append(cash_value)
            colors.append(CHART_COLORS["wealth"][2])
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=.5,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textposition='outside',
            insidetextorientation='radial',
            pull=[0.05 if i == 0 else 0 for i in range(len(labels))],
            hovertemplate='%{label}<br>금액: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            title={
                'text': '자산 배분 현황',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            template='plotly_white',
            annotations=[dict(
                text=f'총 자산<br>{stock_value + savings_value + cash_value:,.0f}원',
                x=0.5, y=0.5,
                font_size=14,
                showarrow=False
            )],
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5
            ),
            margin=dict(l=20, r=20, t=50, b=50)
        )
        
        return fig
    
    # 데이터가 없는 경우 빈 차트 반환
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': '자산 데이터 없음',
            'y':0.5,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'middle'
        },
        annotations=[dict(
            text='자산 데이터가 없습니다.',
            showarrow=False,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            font=dict(size=14)
        )]
    )
    
    return empty_fig

def create_savings_charts(user_id):
    """
    적금 차트 생성
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        tuple: (적금 현황 차트, 적금 만기일 차트, 적금 은행 분포 차트)
    """
    # 적금 정보 가져오기
    savings_summary = get_savings_summary(user_id)
    savings_data = savings_summary.get("savings", [])
    
    # 적금 데이터 확인
    if savings_data:
        # 1. 적금 현황 차트 (현재 납입액 vs 예상 만기금액)
        savings_names = [item["name"] for item in savings_data]
        current_amounts = [item["current_amount"] for item in savings_data]
        expected_amounts = [item["expected_amount"] for item in savings_data]
        
        savings_df = pd.DataFrame({
            "name": savings_names,
            "current": current_amounts,
            "expected": expected_amounts
        })
        
        # 만기일이 가까운 순으로 정렬
        savings_df = savings_df.sort_values(by="current", ascending=False)
        
        fig_savings = go.Figure()
        
        fig_savings.add_trace(go.Bar(
            x=savings_df["name"],
            y=savings_df["current"],
            name='현재 납입액',
            marker_color=CHART_COLORS["blue_scale"][1],
            hovertemplate='%{x}<br>현재 납입액: %{y:,.0f}원<extra></extra>'
        ))
        
        fig_savings.add_trace(go.Bar(
            x=savings_df["name"],
            y=savings_df["expected"],
            name='예상 만기금액',
            marker_color=CHART_COLORS["green_scale"][2],
            hovertemplate='%{x}<br>예상 만기금액: %{y:,.0f}원<extra></extra>'
        ))
        
        fig_savings.update_layout(
            title={
                'text': '적금 현황',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title='적금명',
            yaxis_title='금액 (원)',
            template='plotly_white',
            barmode='group',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=20, r=20, t=50, b=100),
            xaxis=dict(tickangle=45)
        )
        
        # 2. 적금 만기일 타임라인 차트
        fig_timeline = go.Figure()
        
        today = datetime.now().date()
        remaining_days = []
        
        for item in savings_data:
            if isinstance(item["end_date"], str):
                end_date = datetime.strptime(item["end_date"], '%Y-%m-%d').date()
            else:
                end_date = item["end_date"]
            
            days_left = (end_date - today).days
            remaining_days.append(days_left)
            
            date_str = end_date.strftime('%Y-%m-%d')
            
            fig_timeline.add_trace(go.Scatter(
                x=[days_left],
                y=[item["expected_amount"]],
                mode='markers',
                name=item["name"],
                marker=dict(
                    size=item["current_amount"] / 50000,  # 현재 금액에 비례한 크기
                    sizemin=15,
                    sizemode='area',
                    sizeref=2.*max(current_amounts)/(30.**2),
                    color=CHART_COLORS["wealth"][savings_data.index(item) % len(CHART_COLORS["wealth"])]
                ),
                text=item["name"],
                hovertemplate='%{text}<br>만기일: ' + date_str + '<br>남은 일수: %{x}일<br>예상 금액: %{y:,.0f}원<extra></extra>'
            ))
        
        fig_timeline.update_layout(
            title={
                'text': '적금 만기일 타임라인',
                'y':0.95,
                'x':0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
            xaxis_title='만기까지 남은 일수',
            yaxis_title='예상 만기금액 (원)',
            template='plotly_white',
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=50),
            hovermode='closest'
        )
        
        # X축 반전 (가까운 일수가 왼쪽으로)
        fig_timeline.update_xaxes(autorange="reversed")
        
        # 3. 은행별 적금 분포 차트
        by_bank = savings_summary.get("by_bank", {})
        
        if by_bank:
            bank_names = list(by_bank.keys())
            bank_amounts = list(by_bank.values())
            
            fig_banks = go.Figure(data=[go.Pie(
                labels=bank_names,
                values=bank_amounts,
                hole=.4,
                marker=dict(colors=CHART_COLORS["vivid"]),
                textinfo='label+percent',
                hovertemplate='%{label}<br>금액: %{value:,.0f}원<br>비중: %{percent}<extra></extra>'
            )])
            
            fig_banks.update_layout(
                title={
                    'text': '은행별 적금 분포',
                    'y':0.95,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'top'
                },
                template='plotly_white',
                margin=dict(l=20, r=20, t=50, b=20)
            )
        else:
            # 은행 데이터가 없는 경우 빈 차트
            fig_banks = go.Figure()
            fig_banks.update_layout(
                title={
                    'text': '은행별 적금 분포',
                    'y':0.5,
                    'x':0.5,
                    'xanchor': 'center',
                    'yanchor': 'middle'
                },
                annotations=[dict(
                    text='은행별 적금 데이터가 없습니다.',
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    font=dict(size=14)
                )]
            )
        
        return fig_savings, fig_timeline, fig_banks
    
    # 데이터가 없는 경우 빈 차트 반환
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title={
            'text': '적금 데이터 """
시각화 관련 UI 컴포넌트 - 고급 차트 및 대시보드 기능 추가
"""
import gradio as gr
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

try:
    from services.portfolio_service import (
        get_portfolio_summary, 
        calculate_portfolio_risk,
        get_portfolio_performance_metrics
    )
except ImportError:
    # 더미 함수 정의
    def get_portfolio_summary(user_id):
        return {
            "summary": {"total_value": 0, "total_invested": 0, "total_gain_loss": 0, "total_return": 0, "savings_total": 0, "total_assets": 0},
            "distributions": {"country": {}, "account": {}, "broker": {}, "sector": {}},
            "top_stocks": [],
            "history": [],
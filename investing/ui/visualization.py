"""
시각화 관련 UI 컴포넌트
"""
import gradio as gr
import plotly.express as px
import plotly.graph_objects as go
# from services.portfolio_service import get_portfolio_summary

def get_portfolio_summary(user_id):
    return {
        "summary": {"total_value": 0, "total_invested": 0, "total_gain_loss": 0, "total_return": 0, "savings_total": 0, "total_assets": 0},
        "distributions": {"country": {}, "account": {}, "broker": {}},
        "top_stocks": [],
        "history": [],
        "savings": []
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
        returns = [item["total_return_percent"] for item in portfolio_data["history"]]
        
        fig_returns = go.Figure()
        fig_returns.add_trace(go.Scatter(
            x=dates, 
            y=returns,
            mode='lines+markers',
            name='수익률 (%)',
            line=dict(color='rgb(0, 100, 200)', width=2)
        ))
        
        fig_returns.update_layout(
            title='포트폴리오 수익률 추이',
            xaxis_title='날짜',
            yaxis_title='수익률 (%)',
            template='plotly_white'
        )
        
        # 0% 라인 추가
        fig_returns.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.5)
        
        # 자산 가치 차트
        values = [item["total_value"] for item in portfolio_data["history"]]
        
        fig_values = go.Figure()
        fig_values.add_trace(go.Scatter(
            x=dates, 
            y=values,
            mode='lines+markers',
            name='포트폴리오 가치',
            line=dict(color='rgb(0, 150, 100)', width=2),
            fill='tozeroy',
            fillcolor='rgba(0, 150, 100, 0.2)'
        ))
        
        fig_values.update_layout(
            title='포트폴리오 가치 추이',
            xaxis_title='날짜',
            yaxis_title='가치 (원)',
            template='plotly_white'
        )
        
        return fig_returns, fig_values
    
    # 데이터가 없는 경우 빈 차트 반환
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title='데이터가 충분하지 않습니다',
        annotations=[dict(
            text='포트폴리오 히스토리 데이터 없음',
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )]
    )
    
    return empty_fig, empty_fig

def create_distribution_charts(user_id):
    """
    포트폴리오 분포 차트 생성
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        tuple: (국가별 차트, 계좌별 차트, 증권사별 차트, 상위종목 차트)
    """
    # 포트폴리오 정보 가져오기
    portfolio_data = get_portfolio_summary(user_id)
    
    # 국가별 분포
    country_data = portfolio_data["distributions"]["country"]
    
    if country_data:
        # 국가별 분포 파이 차트
        fig_country = go.Figure(data=[go.Pie(
            labels=list(country_data.keys()),
            values=list(country_data.values()),
            hole=.3,
            marker_colors=px.colors.qualitative.Pastel
        )])
        
        fig_country.update_layout(
            title='국가별 투자 분포',
            template='plotly_white'
        )
        
        # 계좌별 분포
        account_data = portfolio_data["distributions"]["account"]
        
        fig_account = go.Figure(data=[go.Pie(
            labels=list(account_data.keys()),
            values=list(account_data.values()),
            hole=.3,
            marker_colors=px.colors.qualitative.Bold
        )])
        
        fig_account.update_layout(
            title='계좌별 투자 분포',
            template='plotly_white'
        )
        
        # 증권사별 분포
        broker_data = portfolio_data["distributions"]["broker"]
        
        fig_broker = go.Figure(data=[go.Pie(
            labels=list(broker_data.keys()),
            values=list(broker_data.values()),
            hole=.3,
            marker_colors=px.colors.qualitative.Vivid
        )])
        
        fig_broker.update_layout(
            title='증권사별 투자 분포',
            template='plotly_white'
        )
        
        # 상위 종목 바 차트
        if portfolio_data["top_stocks"]:
            top_stocks = portfolio_data["top_stocks"]
            stock_names = [item["name"] for item in top_stocks]
            stock_values = [item["value"] for item in top_stocks]
            
            fig_top_stocks = go.Figure(data=[go.Bar(
                x=stock_names,
                y=stock_values,
                marker_color='rgb(55, 83, 109)'
            )])
            
            fig_top_stocks.update_layout(
                title='상위 종목 투자 금액',
                xaxis_title='종목명',
                yaxis_title='평가액 (원)',
                template='plotly_white'
            )
            
            return fig_country, fig_account, fig_broker, fig_top_stocks
        
        # 상위 종목 데이터가 없는 경우
        empty_fig = go.Figure()
        empty_fig.update_layout(
            title='상위 종목 데이터 없음',
            annotations=[dict(
                text='종목 데이터 없음',
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )]
        )
        
        return fig_country, fig_account, fig_broker, empty_fig
    
    # 데이터가 없는 경우 빈 차트 반환
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title='데이터가 충분하지 않습니다',
        annotations=[dict(
            text='포트폴리오 데이터 없음',
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )]
    )
    
    return empty_fig, empty_fig, empty_fig, empty_fig

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
        labels = []
        values = []
        
        if stock_value > 0:
            labels.append("주식")
            values.append(stock_value)
        
        if savings_value > 0:
            labels.append("적금")
            values.append(savings_value)
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=.4,
            marker_colors=['rgb(0, 100, 200)', 'rgb(0, 200, 100)']
        )])
        
        fig.update_layout(
            title='자산 배분 현황',
            template='plotly_white',
            annotations=[dict(
                text=f'총 자산<br>{stock_value + savings_value:,.0f}원',
                x=0.5, y=0.5,
                font_size=15,
                showarrow=False
            )]
        )
        
        return fig
    
    # 데이터가 없는 경우 빈 차트 반환
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title='자산 데이터 없음',
        annotations=[dict(
            text='자산 데이터가 없습니다',
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )]
    )
    
    return empty_fig

def create_savings_chart(user_id):
    """
    적금 차트 생성
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        tuple: (적금 현황 차트, 적금 만기일 차트)
    """
    # 포트폴리오 정보 가져오기
    portfolio_data = get_portfolio_summary(user_id)
    
    # 적금 데이터 확인
    if "savings" in portfolio_data and portfolio_data["savings"]:
        savings_data = portfolio_data["savings"]
        
        # 적금별 현재 납입액 막대 그래프
        savings_names = [item["name"] for item in savings_data]
        current_amounts = [item["current_amount"] for item in savings_data]
        expected_amounts = [item["expected_amount"] for item in savings_data]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=savings_names,
            y=current_amounts,
            name='현재 납입액',
            marker_color='rgb(55, 83, 109)'
        ))
        
        fig.add_trace(go.Bar(
            x=savings_names,
            y=expected_amounts,
            name='예상 만기금액',
            marker_color='rgb(26, 118, 255)'
        ))
        
        fig.update_layout(
            title='적금 현황',
            xaxis_title='적금명',
            yaxis_title='금액 (원)',
            template='plotly_white',
            barmode='group'
        )
        
        # 적금 만기일 타임라인
        fig_timeline = go.Figure()
        
        for item in savings_data:
            end_date = item["end_date"]
            
            fig_timeline.add_trace(go.Scatter(
                x=[end_date, end_date],
                y=[0, item["expected_amount"]],
                mode='lines+markers',
                name=item["name"],
                line=dict(width=2)
            ))
        
        fig_timeline.update_layout(
            title='적금 만기일 타임라인',
            xaxis_title='만기일',
            yaxis_title='예상 만기금액 (원)',
            template='plotly_white'
        )
        
        return fig, fig_timeline
    
    # 데이터가 없는 경우 빈 차트 반환
    empty_fig = go.Figure()
    empty_fig.update_layout(
        title='적금 데이터 없음',
        annotations=[dict(
            text='적금 데이터가 없습니다',
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )]
    )
    
    return empty_fig, empty_fig

def create_visualization_ui():
    """
    시각화 관련 UI 컴포넌트 생성
    
    Returns:
        tuple: (컨테이너 딕셔너리, 컴포넌트 딕셔너리)
    """
    # 포트폴리오 분석 화면
    with gr.Group(visible=False) as portfolio_analysis_container:
        gr.Markdown("## 포트폴리오 분석")
        
        analysis_refresh_btn = gr.Button("분석 데이터 갱신")
        
        with gr.Row():
            returns_chart = gr.Plot(label="수익률 추이")
            value_chart = gr.Plot(label="포트폴리오 가치 추이")
        
        with gr.Row():
            country_chart = gr.Plot(label="국가별 분포")
            account_chart = gr.Plot(label="계좌별 분포")
        
        with gr.Row():
            broker_chart = gr.Plot(label="증권사별 분포")
            top_stocks_chart = gr.Plot(label="상위 종목")
    
    # 자산 배분 화면
    with gr.Group(visible=False) as asset_allocation_container:
        gr.Markdown("## 자산 배분 현황")
        
        allocation_refresh_btn = gr.Button("자산 데이터 갱신")
        
        with gr.Row():
            asset_allocation_chart = gr.Plot(label="자산 배분")
        
        with gr.Row():
            savings_chart = gr.Plot(label="적금 현황")
            savings_timeline_chart = gr.Plot(label="적금 만기일 타임라인")
    
    # 컨테이너 및 컴포넌트 정리
    containers = {
        "portfolio_analysis": portfolio_analysis_container,
        "asset_allocation": asset_allocation_container
    }
    
    components = {
        # 포트폴리오 분석 화면
        "analysis_refresh_btn": analysis_refresh_btn,
        "returns_chart": returns_chart,
        "value_chart": value_chart,
        "country_chart": country_chart,
        "account_chart": account_chart,
        "broker_chart": broker_chart,
        "top_stocks_chart": top_stocks_chart,
        
        # 자산 배분 화면
        "allocation_refresh_btn": allocation_refresh_btn,
        "asset_allocation_chart": asset_allocation_chart,
        "savings_chart": savings_chart,
        "savings_timeline_chart": savings_timeline_chart
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
    def update_portfolio_analysis(state):
        if not state or not state.get("user_id"):
            return tuple([None] * 6)
        
        returns_fig, value_fig = create_portfolio_chart(state["user_id"])
        country_fig, account_fig, broker_fig, top_stocks_fig = create_distribution_charts(state["user_id"])
        
        return returns_fig, value_fig, country_fig, account_fig, broker_fig, top_stocks_fig
    
    components["analysis_refresh_btn"].click(
        fn=update_portfolio_analysis,
        inputs=[session_state],
        outputs=[
            components["returns_chart"],
            components["value_chart"],
            components["country_chart"],
            components["account_chart"],
            components["broker_chart"],
            components["top_stocks_chart"]
        ]
    )
    
    # 자산 배분 갱신 버튼 클릭 이벤트
    def update_asset_allocation(state):
        if not state or not state.get("user_id"):
            return None, None, None
        
        allocation_fig = create_asset_allocation_chart(state["user_id"])
        savings_fig, timeline_fig = create_savings_chart(state["user_id"])
        
        return allocation_fig, savings_fig, timeline_fig
    
    components["allocation_refresh_btn"].click(
        fn=update_asset_allocation,
        inputs=[session_state],
        outputs=[
            components["asset_allocation_chart"],
            components["savings_chart"],
            components["savings_timeline_chart"]
        ]
    )
    
    # 컨테이너가 표시될 때 자동으로 차트 로드
    def load_portfolio_analysis(state, is_visible):
        if is_visible and state and state.get("user_id"):
            return update_portfolio_analysis(state)
        return tuple([None] * 6)
    
    def load_asset_allocation(state, is_visible):
        if is_visible and state and state.get("user_id"):
            return update_asset_allocation(state)
        return None, None, None
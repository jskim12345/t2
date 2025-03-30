"""
적금 관련 UI 컴포넌트
"""
import gradio as gr
from datetime import datetime, timedelta

def create_savings_ui():
    """
    적금 관련 UI 컴포넌트 생성
    
    Returns:
        tuple: (컨테이너 딕셔너리, 컴포넌트 딕셔너리)
    """
    # 적금 목록 화면
    with gr.Group(visible=False) as savings_container:
        gr.Markdown("## 적금 목록", elem_classes="header-text")
        
        savings_refresh_btn = gr.Button("적금 정보 갱신", variant="primary", elem_classes="action-button")
        
        savings_table = gr.Dataframe(
            headers=[
                "ID", "적금명", "은행명", "계좌번호", "시작일", "만기일", "월납입액", 
                "금리(%)", "세후금리(%)", "현재납입액", "예상만기금액", "적금유형", "최종업데이트"
            ],
            interactive=False,
            wrap=True,
            column_widths=[
                "50px", "150px", "100px", "120px", "100px", "100px", "100px", 
                "80px", "80px", "120px", "120px", "100px", "150px"
            ],
            height=400,
            elem_classes="savings-table"
        )
        
        gr.Markdown("### 적금 성과 요약", elem_classes="subheader-text")
        
        with gr.Row():
            total_savings = gr.Textbox(label="총 납입액", elem_classes="info-box")
            expected_total = gr.Textbox(label="총 예상 만기금액", elem_classes="info-box")
            avg_interest = gr.Textbox(label="평균 금리", elem_classes="info-box")
    
    # 적금 추가 화면
    with gr.Group(visible=False) as add_savings_container:
        gr.Markdown("## 적금 추가", elem_classes="header-text")
        
        with gr.Row(equal_height=True):
            with gr.Column(scale=1):
                savings_name = gr.Textbox(label="적금명", container=True)
                savings_bank = gr.Dropdown(
                    ["국민은행", "신한은행", "우리은행", "하나은행", "IBK기업은행", "농협은행", "SC제일은행", "기타"],
                    label="은행",
                    container=True
                )
                savings_account = gr.Textbox(label="계좌번호", container=True)
                savings_type = gr.Dropdown(
                    ["정기적금", "자유적금", "청약저축", "주택청약", "기타"],
                    label="적금유형",
                    container=True
                )
            
            with gr.Column(scale=1):
                today = datetime.now().strftime("%Y-%m-%d")
                one_year_later = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
                
                savings_start_date = gr.Textbox(label="시작일", value=today, container=True)
                savings_end_date = gr.Textbox(label="만기일", value=one_year_later, container=True)
                savings_monthly = gr.Number(label="월납입액", precision=0, container=True)
                savings_rate = gr.Number(label="금리(%)", precision=2, container=True)
        
        with gr.Row():
            add_savings_btn = gr.Button("적금 추가", variant="primary", size="lg", elem_classes="action-button")
        
        add_savings_result = gr.Textbox(label="결과", elem_classes="result-message")
        
        # 계산기 추가
        gr.Markdown("### 만기금액 예상 계산기", elem_classes="subheader-text")
        
        with gr.Row():
            calc_monthly = gr.Number(label="월 납입액", precision=0, value=100000, container=True)
            calc_rate = gr.Number(label="연 금리(%)", precision=2, value=3.5, container=True)
            calc_period = gr.Number(label="납입 기간(개월)", precision=0, value=12, container=True)
            
        calc_btn = gr.Button("계산하기", variant="secondary", elem_classes="action-button")
        calc_result = gr.Textbox(label="예상 만기금액", elem_classes="info-box")
    
    # 적금 거래내역 화면
    with gr.Group(visible=False) as savings_transactions_container:
        gr.Markdown("## 적금 거래내역", elem_classes="header-text")
        
        with gr.Row():
            savings_select = gr.Dropdown(
                [],
                label="적금 선택",
                info="조회할 적금을 선택하세요",
                interactive=True,
                container=True
            )
            load_savings_trans_btn = gr.Button("거래내역 불러오기", variant="primary", elem_classes="action-button")
        
        savings_trans_table = gr.Dataframe(
            headers=["ID", "적금명", "날짜", "금액", "거래유형", "메모"],
            interactive=False,
            wrap=True,
            column_widths=["50px", "150px", "100px", "100px", "80px", "200px"],
            height=400,
            elem_classes="transaction-table"
        )
        
        gr.Markdown("### 신규 거래내역 추가", elem_classes="subheader-text")
        
        with gr.Row(equal_height=True):
            with gr.Column(scale=1):
                trans_date = gr.Textbox(label="거래일자", value=today, container=True)
                trans_amount = gr.Number(label="금액", precision=0, container=True)
            
            with gr.Column(scale=1):
                trans_type = gr.Dropdown(
                    ["입금", "출금"],
                    label="거래유형",
                    container=True
                )
                trans_memo = gr.Textbox(label="메모", container=True)
        
        with gr.Row():
            add_trans_btn = gr.Button("거래내역 추가", variant="primary", elem_classes="action-button")
        
        add_trans_result = gr.Textbox(label="결과", elem_classes="result-message")
    
    # 컨테이너 및 컴포넌트 정리
    containers = {
        "savings": savings_container,
        "add_savings": add_savings_container,
        "savings_transactions": savings_transactions_container
    }
    
    components = {
        # 적금 목록 화면
        "savings_refresh_btn": savings_refresh_btn,
        "savings_table": savings_table,
        "total_savings": total_savings,
        "expected_total": expected_total,
        "avg_interest": avg_interest,
        
        # 적금 추가 화면
        "savings_name": savings_name,
        "savings_bank": savings_bank,
        "savings_account": savings_account,
        "savings_type": savings_type,
        "savings_start_date": savings_start_date,
        "savings_end_date": savings_end_date,
        "savings_monthly": savings_monthly,
        "savings_rate": savings_rate,
        "add_savings_btn": add_savings_btn,
        "add_savings_result": add_savings_result,
        "calc_monthly": calc_monthly,
        "calc_rate": calc_rate,
        "calc_period": calc_period,
        "calc_btn": calc_btn,
        "calc_result": calc_result,
        
        # 적금 거래내역 화면
        "savings_select": savings_select,
        "load_savings_trans_btn": load_savings_trans_btn,
        "savings_trans_table": savings_trans_table,
        "trans_date": trans_date,
        "trans_amount": trans_amount,
        "trans_type": trans_type,
        "trans_memo": trans_memo,
        "add_trans_btn": add_trans_btn,
        "add_trans_result": add_trans_result
    }
    
    return containers, components

def setup_savings_ui_events(app, session_state, components, containers):
    """
    적금 관련 UI 이벤트 설정
    
    Args:
        app: Gradio 앱 인스턴스
        session_state: 세션 상태 컴포넌트
        components: UI 컴포넌트 딕셔너리
        containers: UI 컨테이너 딕셔너리
    """
    try:
        from services.savings_service import load_savings, create_savings, add_savings_deposit, add_savings_withdrawal, load_savings_transactions, get_savings_summary
        
        # 적금 정보 갱신 버튼 클릭 이벤트
        def refresh_savings(state):
            if not state or not state.get("user_id"):
                return None, "", "", ""
            
            # 적금 목록 업데이트
            df = load_savings(state["user_id"])
            
            # 적금 요약 정보 계산
            summary = get_savings_summary(state["user_id"])
            total = summary.get("total_amount", 0)
            expected = sum(item.get("expected_amount", 0) for item in summary.get("savings", []))
            
            # 평균 금리 계산
            savings_items = summary.get("savings", [])
            if savings_items:
                avg_rate = sum(item.get("interest_rate", 0) for item in savings_items) / len(savings_items)
            else:
                avg_rate = 0
            
            return df, f"{total:,.0f}원", f"{expected:,.0f}원", f"{avg_rate:.2f}%"
        
        components["savings_refresh_btn"].click(
            fn=refresh_savings,
            inputs=[session_state],
            outputs=[
                components["savings_table"],
                components["total_savings"],
                components["expected_total"],
                components["avg_interest"]
            ]
        )
        
        # 적금 추가 버튼 클릭 이벤트
        def add_savings_handler(state, name, bank, account, start_date, end_date, monthly, rate, savings_type):
            if not state or not state.get("user_id"):
                return None, "로그인이 필요합니다."
            
            try:
                df = create_savings(state["user_id"], name, bank, account, start_date, end_date, monthly, rate, savings_type)
                return df, "적금이 성공적으로 추가되었습니다."
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"적금 추가 오류: {e}")
                return None, f"적금 추가 중 오류가 발생했습니다: {e}"
        
        components["add_savings_btn"].click(
            fn=add_savings_handler,
            inputs=[
                session_state,
                components["savings_name"],
                components["savings_bank"],
                components["savings_account"],
                components["savings_start_date"],
                components["savings_end_date"],
                components["savings_monthly"],
                components["savings_rate"],
                components["savings_type"]
            ],
            outputs=[
                components["savings_table"],
                components["add_savings_result"]
            ]
        )
        
        # 만기금액 계산기
        def calculate_maturity(monthly, rate, period):
            # 단리 계산식: 원금 × (1 + 금리 × 기간)
            # 월 납입식 적금의 경우: 월납입액 × 납입횟수 × (1 + 연이율÷12 × (납입횟수+1)÷2)
            # 세후 이자율 계산 (이자소득세 15.4% 가정)
            after_tax_rate = rate * (1 - 0.154) / 100  # %에서 소수로 변환 및 세후 계산
            
            # 납입 원금
            principal = monthly * period
            
            # 이자 계산 (평균 예치 기간 고려)
            avg_periods = (period + 1) / 2  # 평균 예치 기간 (개월)
            interest = principal * (after_tax_rate / 12) * avg_periods
            
            # 세후 만기금액
            maturity = principal + interest
            
            return f"{maturity:,.0f}원 (세후, 단리 기준)\n원금: {principal:,.0f}원, 이자: {interest:,.0f}원"
        
        components["calc_btn"].click(
            fn=calculate_maturity,
            inputs=[
                components["calc_monthly"],
                components["calc_rate"],
                components["calc_period"]
            ],
            outputs=[components["calc_result"]]
        )
        
        # 적금 거래내역 추가
        def add_transaction_handler(state, savings_id, date, amount, transaction_type, memo):
            if not state or not state.get("user_id") or not savings_id:
                return None, "적금을 선택해주세요."
            
            try:
                if transaction_type == "입금":
                    result = add_savings_deposit(state["user_id"], savings_id, date, amount, memo)
                    message = f"{amount:,.0f}원 입금이 기록되었습니다."
                else:  # 출금
                    result = add_savings_withdrawal(state["user_id"], savings_id, date, amount, memo)
                    message = f"{amount:,.0f}원 출금이 기록되었습니다."
                
                return result, message
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"거래내역 추가 오류: {e}")
                return None, f"거래내역 추가 중 오류가 발생했습니다: {e}"
        
        components["add_trans_btn"].click(
            fn=add_transaction_handler,
            inputs=[
                session_state,
                components["savings_select"],
                components["trans_date"],
                components["trans_amount"],
                components["trans_type"],
                components["trans_memo"]
            ],
            outputs=[
                components["savings_trans_table"],
                components["add_trans_result"]
            ]
        )
        
        # 거래내역 불러오기
        def load_transactions_handler(state, savings_id):
            if not state or not state.get("user_id"):
                return None
            
            try:
                return load_savings_transactions(state["user_id"], savings_id)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"거래내역 로드 오류: {e}")
                return None
        
        components["load_savings_trans_btn"].click(
            fn=load_transactions_handler,
            inputs=[session_state, components["savings_select"]],
            outputs=[components["savings_trans_table"]]
        )
    
    except (ImportError, AttributeError) as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"적금 UI 이벤트 설정 실패: {e}")
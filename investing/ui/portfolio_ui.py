"""
포트폴리오 관련 UI 컴포넌트
"""
import gradio as gr

def create_portfolio_ui():
    """
    포트폴리오 관련 UI 컴포넌트 생성
    
    Returns:
        tuple: (컨테이너 딕셔너리, 컴포넌트 딕셔너리)
    """
    # 포트폴리오 조회 화면
    with gr.Group(visible=True) as portfolio_container:
        gr.Markdown("## 포트폴리오 현황")
        
        refresh_btn = gr.Button("실시간 가격 업데이트")
        
        portfolio_table = gr.Dataframe(
            headers=[
                "증권사", "계좌", "국가", "종목코드", "종목명", "수량", 
                "평단가(원화)", "평단가(달러)", "현재가(원화)", "현재가(달러)",
                "평가액[원화]", "투자비중", "손익금액[원화]", "손익수익[원화]", "총수익률[원가+배당]"
            ],
            interactive=False,
            wrap=True
        )
    
    # 매수 화면
    with gr.Group(visible=False) as buy_container:
        gr.Markdown("## 주식 매수")
        
        with gr.Row():
            with gr.Column():
                buy_증권사 = gr.Dropdown(
                    ["한투", "신한", "삼성", "미래에셋", "NH", "KB", "기타"], 
                    label="증권사"
                )
                buy_계좌 = gr.Dropdown(
                    ["일반", "ISA", "연금"], 
                    label="계좌"
                )
                buy_국가 = gr.Dropdown(
                    ["한국", "미국", "중국", "일본", "기타"], 
                    label="국가"
                )
            
            with gr.Column():
                buy_종목코드 = gr.Textbox(label="종목코드")
                buy_종목명 = gr.Textbox(label="종목명")
                buy_수량 = gr.Number(label="수량", precision=0)
                buy_평단가 = gr.Number(label="매수가")
        
        buy_btn = gr.Button("매수하기", variant="primary")
        buy_result = gr.Textbox(label="결과")
    
    # 매도 화면
    with gr.Group(visible=False) as sell_container:
        gr.Markdown("## 주식 매도")
        
        # 보유 종목 선택 드롭다운 추가
        sell_stock_dropdown = gr.Dropdown(
            [], 
            label="보유 종목 선택",
            interactive=True
        )
        
        with gr.Row():
            with gr.Column():
                sell_계좌 = gr.Dropdown(
                    ["일반", "ISA", "연금"], 
                    label="계좌"
                )
                sell_종목코드 = gr.Textbox(label="종목코드")
            
            with gr.Column():
                sell_수량 = gr.Number(label="수량", precision=0)
                sell_매도가 = gr.Number(label="매도가")
        
        sell_btn = gr.Button("매도하기", variant="primary")
        sell_result = gr.Textbox(label="결과")
    
    # 거래내역 화면
    with gr.Group(visible=False) as transactions_container:
        gr.Markdown("## 주식 거래내역")
        
        load_transaction_btn = gr.Button("거래내역 불러오기")
        
        transaction_table = gr.Dataframe(
            headers=["ID", "종목명", "거래유형", "수량", "가격", "거래일시"],
            interactive=False,
            wrap=True
        )
    
    # 컨테이너 및 컴포넌트 정리
    containers = {
        "portfolio": portfolio_container,
        "buy": buy_container,
        "sell": sell_container,
        "transactions": transactions_container
    }
    
    components = {
        # 포트폴리오 조회 화면
        "refresh_btn": refresh_btn,
        "portfolio_table": portfolio_table,
        
        # 매수 화면
        "buy_증권사": buy_증권사,
        "buy_계좌": buy_계좌,
        "buy_국가": buy_국가,
        "buy_종목코드": buy_종목코드,
        "buy_종목명": buy_종목명,
        "buy_수량": buy_수량,
        "buy_평단가": buy_평단가,
        "buy_btn": buy_btn,
        "buy_result": buy_result,
        
        # 매도 화면
        "sell_stock_dropdown": sell_stock_dropdown,
        "sell_계좌": sell_계좌,
        "sell_종목코드": sell_종목코드,
        "sell_수량": sell_수량,
        "sell_매도가": sell_매도가,
        "sell_btn": sell_btn,
        "sell_result": sell_result,
        
        # 거래내역 화면
        "load_transaction_btn": load_transaction_btn,
        "transaction_table": transaction_table
    }
    
    return containers, components

def setup_portfolio_events(app, session_state, components, containers):
    """
    포트폴리오 관련 이벤트 설정
    
    Args:
        app: Gradio 앱 인스턴스
        session_state: 세션 상태 컴포넌트
        components: UI 컴포넌트 딕셔너리
        containers: UI 컨테이너 딕셔너리
    """
    from services.portfolio_service import update_all_prices, load_portfolio, buy_stock, sell_stock, load_transactions
    
    # 가격 업데이트 버튼 클릭 이벤트
    components["refresh_btn"].click(
        fn=lambda state: update_all_prices(state["user_id"]) and load_portfolio(state["user_id"]),
        inputs=[session_state],
        outputs=[components["portfolio_table"]]
    )
    
    # 매수 버튼 클릭 이벤트
    components["buy_btn"].click(
        fn=lambda state, 증권사, 계좌, 국가, 종목코드, 종목명, 수량, 평단가: (
            buy_stock(
                state["user_id"], 증권사, 계좌, 국가, 종목코드, 종목명, 수량, 평단가
            ),
            "매수가 완료되었습니다."
        ),
        inputs=[
            session_state,
            components["buy_증권사"],
            components["buy_계좌"],
            components["buy_국가"],
            components["buy_종목코드"],
            components["buy_종목명"],
            components["buy_수량"],
            components["buy_평단가"]
        ],
        outputs=[
            components["portfolio_table"],
            components["buy_result"]
        ]
    )
    
    # 매도 화면이 표시될 때 보유 종목 목록 업데이트
    def load_owned_stocks(state):
        if not state or not state.get("user_id"):
            return gr.Dropdown.update(choices=[])
        
        from services.portfolio_service import get_owned_stocks
        stock_list = get_owned_stocks(state["user_id"])
        
        if not stock_list:
            return gr.Dropdown.update(choices=[])
        
        # (표시 텍스트, 값) 형태의 튜플 리스트 생성
        choices = [(f"{stock['종목명']} ({stock['종목코드']}) - {stock['계좌']} - {stock['수량']}주", 
                  (stock['종목코드'], stock['계좌'])) for stock in stock_list]
        
        return gr.Dropdown.update(choices=choices)
    
    # 종목 선택 시 종목코드와 계좌 자동 설정
    def update_sell_info(selected, state):
        if not selected or not state or not state.get("user_id"):
            return "", "", "", ""
        
        종목코드, 계좌 = selected
        
        from services.portfolio_service import get_stock_details
        stock_info = get_stock_details(종목코드, 계좌, state["user_id"])
        
        if not stock_info:
            return 종목코드, 계좌, "", ""
        
        return 종목코드, 계좌, stock_info.get("수량", ""), stock_info.get("현재가_원화", "")
    
    # 드롭다운 선택 시 이벤트
    components["sell_stock_dropdown"].change(
        fn=update_sell_info,
        inputs=[components["sell_stock_dropdown"], session_state],
        outputs=[
            components["sell_종목코드"],
            components["sell_계좌"],
            components["sell_수량"],
            components["sell_매도가"]
        ]
    )
    
    # 매도 버튼 클릭 이벤트
    components["sell_btn"].click(
        fn=lambda state, 종목코드, 계좌, 수량, 매도가: sell_stock(
            state["user_id"], 종목코드, 계좌, 수량, 매도가
        ),
        inputs=[
            session_state,
            components["sell_종목코드"],
            components["sell_계좌"],
            components["sell_수량"],
            components["sell_매도가"]
        ],
        outputs=[
            components["sell_result"],
            components["portfolio_table"]
        ]
    )
    
    # 거래내역 불러오기 버튼 클릭 이벤트
    components["load_transaction_btn"].click(
        fn=lambda state: load_transactions(state["user_id"]),
        inputs=[session_state],
        outputs=[components["transaction_table"]]
    )
    
    # 매도 탭으로 이동할 때 보유 종목 목록 업데이트
    def on_menu_click(state, section):
        if section == "sell":
            # 매도 화면을 위한 종목 목록 업데이트
            dropdown_update = load_owned_stocks(state)
            return [gr.update(visible=(k == section)) for k in containers.keys()], dropdown_update
        else:
            # 다른 메뉴는 기본 동작
            return [gr.update(visible=(k == section)) for k in containers.keys()], gr.update()
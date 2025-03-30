#!/usr/bin/env python
"""
자산관리 프로그램 - 메인 애플리케이션 파일
"""
import os
import sys
import time
import gradio as gr

# 필요한 모듈들 임포트
from models.database import init_databases
from utils.logging import setup_logging
from ui.auth_ui import create_auth_ui
from ui.portfolio_ui import create_portfolio_ui
from ui.savings_ui import create_savings_ui
from ui.visualization import create_visualization_ui
from services.market_service import schedule_price_updates
from services.portfolio_service import update_all_prices, buy_stock, sell_stock, load_portfolio, load_transactions, get_owned_stocks, get_stock_details
from services.savings_service import update_savings_calculation, load_savings

# 로거 초기화
logger = setup_logging()

def create_ui():
    """
    전체 UI 생성 및 구성
    """
    with gr.Blocks(title="자산관리 프로그램", css="""
        .container {max-width: 1200px; margin: auto;}
        .main-panel {border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);}
        .menu-container {background-color: #f5f5f5; padding: 10px; border-radius: 5px;}
        .portfolio-table {font-size: 14px;}
        .header-text {font-weight: bold; font-size: 18px; margin-bottom: 10px;}
        .action-button {padding: 8px 16px; border-radius: 4px;}
        .num-value {text-align: right; font-family: monospace;}
        .sidebar {background-color: #f8f9fa; padding: 15px; border-radius: 8px;}
        .tab-content {padding: 15px;}
    """) as app:
        # 세션 상태 관리 (로그인 상태 및 사용자 정보 저장)
        session_state = gr.State({
            "logged_in": False,
            "session_id": None,
            "user_id": None,
            "username": None
        })
        
        # 인증 UI 컴포넌트 (로그인, 회원가입)
        login_container, register_container, login_components = create_auth_ui()
        
        # 메인 어플리케이션 컨테이너 (로그인 후 표시됨)
        with gr.Row(visible=False, elem_classes="main-panel") as main_container:
            # 사이드바 (계정 정보 및 메뉴)
            with gr.Column(scale=1, min_width=250, elem_classes="sidebar"):
                gr.Markdown("## 계정 정보", elem_classes="header-text")
                user_info = gr.Markdown("로그인: ")
                logout_btn = gr.Button("로그아웃", variant="secondary")
                
                gr.Markdown("---")
                gr.Markdown("## 메뉴", elem_classes="header-text")
                
                # 메뉴 버튼들
                menu_buttons = {}
                
                with gr.Accordion("포트폴리오", open=True, elem_classes="menu-container"):
                    menu_buttons["portfolio"] = gr.Button("포트폴리오 보기", elem_classes="action-button")
                    menu_buttons["portfolio_refresh"] = gr.Button("가격 업데이트", elem_classes="action-button")
                
                with gr.Accordion("거래", open=True, elem_classes="menu-container"):
                    menu_buttons["buy"] = gr.Button("매수하기", elem_classes="action-button")
                    menu_buttons["sell"] = gr.Button("매도하기", elem_classes="action-button")
                    menu_buttons["transactions"] = gr.Button("거래내역 보기", elem_classes="action-button")
                
                with gr.Accordion("적금 관리", open=True, elem_classes="menu-container"):
                    menu_buttons["savings"] = gr.Button("적금 목록", elem_classes="action-button")
                    menu_buttons["add_savings"] = gr.Button("적금 추가", elem_classes="action-button")
                    menu_buttons["savings_transactions"] = gr.Button("적금 거래내역", elem_classes="action-button")
                
                with gr.Accordion("분석", open=True, elem_classes="menu-container"):
                    menu_buttons["portfolio_analysis"] = gr.Button("포트폴리오 분석", elem_classes="action-button")
                    menu_buttons["asset_allocation"] = gr.Button("자산 배분", elem_classes="action-button")
            
            # 메인 컨텐츠 영역
            with gr.Column(scale=4, elem_classes="tab-content"):
                # 각 섹션의 UI 컴포넌트 생성
                portfolio_containers, portfolio_components = create_portfolio_ui()
                savings_containers, savings_components = create_savings_ui()
                visualization_containers, visualization_components = create_visualization_ui()
                
                # UI 컴포넌트 합치기
                all_containers = {
                    **portfolio_containers,
                    **savings_containers,
                    **visualization_containers
                }
                
                all_components = {
                    **portfolio_components,
                    **savings_components,
                    **visualization_components
                }
        
        # 로그인 함수
        def login(username, password):
            from services.auth_service import authenticate_user
            
            success, session_id = authenticate_user(username, password)
            
            if success and session_id:
                from services.auth_service import validate_session
                valid, user_data = validate_session(session_id)
                
                if valid:
                    new_state = {
                        "logged_in": True,
                        "session_id": session_id,
                        "user_id": user_data["user_id"],
                        "username": user_data["username"]
                    }
                    
                    # 사용자 정보 메시지 업데이트
                    user_info_msg = f"사용자: **{user_data['username']}**  \n마지막 로그인: {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    # 포트폴리오 데이터 로드
                    portfolio_df = load_portfolio(user_data["user_id"])
                    
                    # 적금 데이터 로드
                    savings_df = load_savings(user_data["user_id"])
                    
                    logger.info(f"로그인 성공: {username}")
                    
                    return (
                        new_state,
                        "로그인 성공!",
                        gr.update(visible=False),  # login_container
                        gr.update(visible=False),  # register_container
                        gr.update(visible=True),   # main_container
                        user_info_msg,
                        portfolio_df,
                        savings_df,
                        *[gr.update(visible=(k == "portfolio")) for k in all_containers.keys()]
                    )
                
            logger.warning(f"로그인 실패: {username}")
            return (
                session_state.value,  # 상태 변경 없음
                "로그인 실패: 사용자명 또는 비밀번호가 잘못되었습니다.",
                gr.update(visible=True),   # login_container
                gr.update(visible=False),  # register_container
                gr.update(visible=False),  # main_container
                "",
                None,
                None,
                *[gr.update(visible=False) for _ in all_containers.keys()]
            )
        
        # 로그아웃 함수
        def logout(state):
            from services.auth_service import logout_session
            
            if state and state.get("session_id"):
                logout_session(state["session_id"])
                logger.info(f"로그아웃: {state.get('username')}")
            
            return (
                {"logged_in": False, "session_id": None, "user_id": None, "username": None},
                gr.update(visible=True),   # login_container
                gr.update(visible=False),  # register_container
                gr.update(visible=False),  # main_container
                "",
                None,
                None,
                *[gr.update(visible=False) for _ in all_containers.keys()]
            )
        
        # 회원가입 화면 전환 함수
        def show_register():
            return gr.update(visible=False), gr.update(visible=True)
        
        # 로그인 화면으로 돌아가기 함수
        def back_to_login():
            return gr.update(visible=True), gr.update(visible=False), "", ""
        
        # 회원가입 처리 함수
        def register(username, password, confirm_password, email):
            from services.auth_service import register_user
            
            if not username or not password:
                return gr.update(visible=True), gr.update(visible=False), "사용자명과 비밀번호를 입력해주세요.", "", "", ""
            
            if password != confirm_password:
                return gr.update(visible=True), gr.update(visible=False), "비밀번호가 일치하지 않습니다.", "", "", ""
            
            success, message = register_user(username, password, email)
            
            if success:
                logger.info(f"회원가입 성공: {username}")
                return gr.update(visible=True), gr.update(visible=False), "회원가입 성공! 로그인해주세요.", "", "", ""
            else:
                logger.warning(f"회원가입 실패: {username} - {message}")
                return gr.update(visible=True), gr.update(visible=False), f"회원가입 실패: {message}", username, "", email
        
        # 메뉴 항목별 UI 전환 함수
        def show_ui_section(section_name, state):
            return [gr.update(visible=(k == section_name)) for k in all_containers.keys()]
        
        # 이벤트 핸들러 연결
        
        # 인증 관련 이벤트
        login_components["login_btn"].click(
            login,
            inputs=[login_components["username"], login_components["password"]],
            outputs=[
                session_state,
                login_components["message"],
                login_container,
                register_container,
                main_container,
                user_info,
                portfolio_components["portfolio_table"],
                savings_components["savings_table"],
                *all_containers.values()
            ]
        )
        
        login_components["register_btn"].click(
            show_register,
            inputs=[],
            outputs=[login_container, register_container]
        )
        
        login_components["reg_back_btn"].click(
            back_to_login,
            inputs=[],
            outputs=[login_container, register_container, login_components["message"], login_components["reg_message"]]
        )
        
        login_components["reg_submit_btn"].click(
            register,
            inputs=[
                login_components["reg_username"],
                login_components["reg_password"],
                login_components["reg_confirm_password"],
                login_components["reg_email"]
            ],
            outputs=[
                login_container,
                register_container,
                login_components["reg_message"],
                login_components["reg_username"],
                login_components["reg_password"],
                login_components["reg_email"]
            ]
        )
        
        logout_btn.click(
            logout,
            inputs=[session_state],
            outputs=[
                session_state,
                login_container,
                register_container,
                main_container,
                login_components["message"],
                portfolio_components["portfolio_table"],
                savings_components["savings_table"],
                *all_containers.values()
            ]
        )
        
        # 메뉴 버튼들에 이벤트 핸들러 연결
        for section, button in menu_buttons.items():
            button.click(
                lambda state, section=section: show_ui_section(section, state),
                inputs=[session_state],
                outputs=list(all_containers.values())
            )
        
        # 포트폴리오 관련 이벤트
        portfolio_components["refresh_btn"].click(
            lambda state: update_all_prices(state["user_id"]) and load_portfolio(state["user_id"]),
            inputs=[session_state],
            outputs=[portfolio_components["portfolio_table"]]
        )
        
        # 매수 이벤트 핸들러
        portfolio_components["buy_btn"].click(
            fn=lambda state, 증권사, 계좌, 국가, 종목코드, 종목명, 수량, 평단가: (
                buy_stock(state["user_id"], 증권사, 계좌, 국가, 종목코드, 종목명, 수량, 평단가),
                "매수가 완료되었습니다."
            ),
            inputs=[
                session_state,
                portfolio_components["buy_증권사"],
                portfolio_components["buy_계좌"],
                portfolio_components["buy_국가"],
                portfolio_components["buy_종목코드"],
                portfolio_components["buy_종목명"],
                portfolio_components["buy_수량"],
                portfolio_components["buy_평단가"]
            ],
            outputs=[
                portfolio_components["portfolio_table"],
                portfolio_components["buy_result"]
            ]
        )
        
        # 매도 이벤트 핸들러
        portfolio_components["sell_btn"].click(
            fn=lambda state, 종목코드, 계좌, 수량, 매도가: sell_stock(
                state["user_id"], 종목코드, 계좌, 수량, 매도가
            ),
            inputs=[
                session_state,
                portfolio_components["sell_종목코드"],
                portfolio_components["sell_계좌"],
                portfolio_components["sell_수량"],
                portfolio_components["sell_매도가"]
            ],
            outputs=[
                portfolio_components["sell_result"],
                portfolio_components["portfolio_table"]
            ]
        )
        
        # 거래내역 로드 이벤트 핸들러
        portfolio_components["load_transaction_btn"].click(
            fn=lambda state: load_transactions(state["user_id"]),
            inputs=[session_state],
            outputs=[portfolio_components["transaction_table"]]
        )
        
        # 보유 종목 목록 업데이트 함수 (sell_stock_dropdown이 있는 경우)
        if "sell_stock_dropdown" in portfolio_components:
            # 매도 화면이 표시될 때 보유 종목 목록 업데이트
            def load_owned_stocks(state):
                if not state or not state.get("user_id"):
                    return gr.update(choices=[])  # gr.Dropdown.update() 대신 사용
                
                try:
                    stock_list = get_owned_stocks(state["user_id"])
                    
                    if not stock_list:
                        return gr.update(choices=[])
                    
                    # (표시 텍스트, 값) 형태의 튜플 리스트 생성
                    choices = [(f"{stock['종목명']} ({stock['종목코드']}) - {stock['계좌']} - {stock['수량']}주", 
                              (stock['종목코드'], stock['계좌'])) for stock in stock_list]
                    
                    return gr.update(choices=choices)
                except Exception as e:
                    logger.warning(f"보유 종목 목록 조회 실패: {e}")
                    return gr.update(choices=[])
            
            # 종목 선택 시 종목코드와 계좌 자동 설정
            def update_sell_info(selected, state):
                if not selected or not state or not state.get("user_id"):
                    return "", "", "", ""
                
                종목코드, 계좌 = selected
                
                try:
                    stock_info = get_stock_details(종목코드, 계좌, state["user_id"])
                    
                    if not stock_info:
                        return 종목코드, 계좌, "", ""
                    
                    return 종목코드, 계좌, stock_info.get("수량", ""), stock_info.get("현재가_원화", "")
                except Exception as e:
                    logger.warning(f"종목 상세 정보 조회 실패: {e}")
                    return 종목코드, 계좌, "", ""
            
            # 드롭다운 선택 시 이벤트
            portfolio_components["sell_stock_dropdown"].change(
                fn=update_sell_info,
                inputs=[portfolio_components["sell_stock_dropdown"], session_state],
                outputs=[
                    portfolio_components["sell_종목코드"],
                    portfolio_components["sell_계좌"],
                    portfolio_components["sell_수량"],
                    portfolio_components["sell_매도가"]
                ]
            )
            
            # 매도 화면으로 전환 시 보유 종목 목록 업데이트
            menu_buttons["sell"].click(
                fn=lambda state: (
                    show_ui_section("sell", state),
                    load_owned_stocks(state)
                ),
                inputs=[session_state],
                outputs=[
                    *all_containers.values(),
                    portfolio_components["sell_stock_dropdown"]
                ]
            )
        
        # 시각화 관련 이벤트
        try:
            from ui.visualization import (
                create_portfolio_chart, 
                create_distribution_charts,
                create_asset_allocation_chart,
                create_savings_chart
            )
            
            # 포트폴리오 분석 차트 업데이트 이벤트
            def update_portfolio_analysis(state):
                if not state or not state.get("user_id"):
                    return None, None, None, None, None, None
                
                returns_fig, value_fig = create_portfolio_chart(state["user_id"])
                country_fig, account_fig, broker_fig, top_stocks_fig = create_distribution_charts(state["user_id"])
                
                return returns_fig, value_fig, country_fig, account_fig, broker_fig, top_stocks_fig
            
            # 자산 배분 차트 업데이트 이벤트
            def update_asset_allocation(state):
                if not state or not state.get("user_id"):
                    return None, None, None
                
                allocation_fig = create_asset_allocation_chart(state["user_id"])
                savings_fig, timeline_fig = create_savings_chart(state["user_id"])
                
                return allocation_fig, savings_fig, timeline_fig
            
            # 분석 버튼 클릭 이벤트
            visualization_components["analysis_refresh_btn"].click(
                fn=update_portfolio_analysis,
                inputs=[session_state],
                outputs=[
                    visualization_components["returns_chart"],
                    visualization_components["value_chart"],
                    visualization_components["country_chart"],
                    visualization_components["account_chart"],
                    visualization_components["broker_chart"],
                    visualization_components["top_stocks_chart"]
                ]
            )
            
            # 자산 배분 버튼 클릭 이벤트
            visualization_components["allocation_refresh_btn"].click(
                fn=update_asset_allocation,
                inputs=[session_state],
                outputs=[
                    visualization_components["asset_allocation_chart"],
                    visualization_components["savings_chart"],
                    visualization_components["savings_timeline_chart"]
                ]
            )
            
            # 포트폴리오 분석 화면 표시 시 차트 자동 업데이트
            menu_buttons["portfolio_analysis"].click(
                fn=lambda state: (
                    *show_ui_section("portfolio_analysis", state),
                    *update_portfolio_analysis(state)
                ),
                inputs=[session_state],
                outputs=[
                    *all_containers.values(),
                    visualization_components["returns_chart"],
                    visualization_components["value_chart"],
                    visualization_components["country_chart"],
                    visualization_components["account_chart"],
                    visualization_components["broker_chart"],
                    visualization_components["top_stocks_chart"]
                ]
            )
            
            # 자산 배분 화면 표시 시 차트 자동 업데이트
            menu_buttons["asset_allocation"].click(
                fn=lambda state: (
                    *show_ui_section("asset_allocation", state),
                    *update_asset_allocation(state)
                ),
                inputs=[session_state],
                outputs=[
                    *all_containers.values(),
                    visualization_components["asset_allocation_chart"],
                    visualization_components["savings_chart"],
                    visualization_components["savings_timeline_chart"]
                ]
            )
            
        except (ImportError, AttributeError) as e:
            logger.warning(f"시각화 모듈 로드 실패: {e}")
            # 시각화 기능이 없어도 앱이 실행될 수 있도록 패스
        
        # 적금 관련 이벤트
        try:
            from services.savings_service import create_savings, add_savings_deposit, get_savings_by_id
            
            # 적금 추가 버튼 클릭 이벤트
            savings_components["add_savings_btn"].click(
                fn=lambda state, 이름, 은행, 계좌번호, 시작일, 만기일, 월납입액, 금리, 적금유형: (
                    create_savings(
                        state["user_id"], 이름, 은행, 계좌번호, 시작일, 만기일, 
                        월납입액, 금리, 적금유형
                    ),
                    "적금이 추가되었습니다."
                ),
                inputs=[
                    session_state,
                    savings_components["savings_name"],
                    savings_components["savings_bank"],
                    savings_components["savings_account"],
                    savings_components["savings_start_date"],
                    savings_components["savings_end_date"],
                    savings_components["savings_monthly"],
                    savings_components["savings_rate"],
                    savings_components["savings_type"]
                ],
                outputs=[
                    savings_components["savings_table"],
                    savings_components["add_savings_result"]
                ]
            )
            
            # 적금 목록 갱신 버튼 클릭 이벤트
            if "savings_refresh_btn" in savings_components:
                savings_components["savings_refresh_btn"].click(
                    fn=lambda state: (
                        update_savings_calculation(state["user_id"]),
                        load_savings(state["user_id"])
                    )[1],
                    inputs=[session_state],
                    outputs=[savings_components["savings_table"]]
                )
            
            # 적금 선택 시 드롭다운 업데이트 (적금 거래내역 화면에서)
            if "savings_select" in savings_components:
                def load_savings_dropdown(state):
                    if not state or not state.get("user_id"):
                        return gr.update(choices=[])
                    
                    try:
                        savings_list = get_savings_by_id(state["user_id"])
                        
                        if not savings_list:
                            return gr.update(choices=[])
                        
                        # (표시 텍스트, 값) 형태의 튜플 리스트 생성
                        choices = [(f"{saving['이름']} ({saving['은행']}) - {saving['현재납입액']:,.0f}원", 
                                    saving['id']) for saving in savings_list]
                        
                        return gr.update(choices=choices)
                    except Exception as e:
                        logger.warning(f"적금 목록 조회 실패: {e}")
                        return gr.update(choices=[])
                
                # 적금 거래내역 화면으로 전환 시 적금 목록 업데이트
                menu_buttons["savings_transactions"].click(
                    fn=lambda state: (
                        show_ui_section("savings_transactions", state),
                        load_savings_dropdown(state)
                    ),
                    inputs=[session_state],
                    outputs=[
                        *all_containers.values(),
                        savings_components["savings_select"]
                    ]
                )
            
        except (ImportError, AttributeError) as e:
            logger.warning(f"적금 모듈 로드 실패: {e}")
        
        # 앱 시작시 데이터 로드 (로그인 전이므로 아무 작업도 하지 않음)
        app.load(lambda: None, inputs=[], outputs=[])
    
    return app

def main():
    """
    메인 실행 함수
    """
    # 필요한 디렉토리 생성
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # 데이터베이스 초기화
    init_databases()
    
    # 가격 업데이트 스케줄링 (별도 스레드에서 실행)
    try:
        schedule_price_updates()
    except Exception as e:
        logger.error(f"가격 업데이트 스케줄링 실패: {e}")
        # 실패해도 프로그램은 계속 실행
    
    # Gradio UI 생성 및 실행
    app = create_ui()
    app.launch(debug=True)

if __name__ == "__main__":
    main()
y=ma20,
                        mode='lines',
                        name='20일 이동평균',
                        line=dict(color='red', width=1)
                    ),
                    row=1, col=1
                )
            
            if "60일선" in moving_avgs:
                ma60 = df['close'].rolling(window=60).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=ma60,
                        mode='lines',
                        name='60일 이동평균',
                        line=dict(color='green', width=1)
                    ),
                    row=1, col=1
                )
            
            if "120일선" in moving_avgs:
                ma120 = df['close'].rolling(window=120).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=ma120,
                        mode='lines',
                        name='120일 이동평균',
                        line=dict(color='purple', width=1)
                    ),
                    row=1, col=1
                )
            
            # 기술적 지표 추가
            if "볼린저밴드" in indicators:
                # 볼린저 밴드 계산 (20일 기준, 2 표준편차)
                ma20 = df['close'].rolling(window=20).mean()
                std20 = df['close'].rolling(window=20).std()
                upper_band = ma20 + 2 * std20
                lower_band = ma20 - 2 * std20
                
                # 상단 밴드
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=upper_band,
                        mode='lines',
                        name='볼린저 상단',
                        line=dict(color='rgba(250, 128, 114, 0.7)', width=1, dash='dash')
                    ),
                    row=1, col=1
                )
                
                # 하단 밴드
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=lower_band,
                        mode='lines',
                        name='볼린저 하단',
                        line=dict(color='rgba(173, 216, 230, 0.7)', width=1, dash='dash'),
                        fill='tonexty',
                        fillcolor='rgba(173, 216, 230, 0.1)'
                    ),
                    row=1, col=1
                )
            
            if "RSI" in indicators:
                # RSI 계산 (14일 기준)
                def calculate_rsi(data, window=14):
                    diff = data.diff(1)
                    up = diff.clip(lower=0)
                    down = -diff.clip(upper=0)
                    
                    ma_up = up.rolling(window=window).mean()
                    ma_down = down.rolling(window=window).mean()
                    
                    rs = ma_up / ma_down
                    rsi = 100 - (100 / (1 + rs))
                    return rsi
                
                rsi = calculate_rsi(df['close'], 14)
                
                # RSI 서브플롯 추가
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=rsi,
                        mode='lines',
                        name='RSI (14)',
                        line=dict(color='orange', width=1)
                    ),
                    row=2, col=1
                )
                
                # RSI 참조선 추가 (30, 70)
                fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.7, row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.7, row=2, col=1)
                
                # 축 범위 설정
                fig.update_yaxes(range=[0, 100], title_text="RSI", row=2, col=1)
            
            if "MACD" in indicators:
                # MACD 계산 (12, 26, 9 기본값)
                ema12 = df['close'].ewm(span=12, adjust=False).mean()
                ema26 = df['close'].ewm(span=26, adjust=False).mean()
                macd = ema12 - ema26
                signal = macd.ewm(span=9, adjust=False).mean()
                hist = macd - signal
                
                # MACD 차트 추가
                # 메인 차트 하단에 새 서브플롯 추가
                fig = make_subplots(
                    rows=3, cols=1, 
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.5, 0.25, 0.25],
                    subplot_titles=(f"{ticker} 가격 차트", "거래량", "MACD")
                )
                
                # 기존 캔들스틱 다시 추가
                fig.add_trace(
                    go.Candlestick(
                        x=chart_data["dates"],
                        open=chart_data["opens"],
                        high=chart_data["highs"],
                        low=chart_data["lows"],
                        close=chart_data["closes"],
                        name="가격"
                    ),
                    row=1, col=1
                )
                
                # 거래량 다시 추가
                if "volumes" in chart_data and chart_data["volumes"]:
                    fig.add_trace(
                        go.Bar(
                            x=chart_data["dates"],
                            y=chart_data["volumes"],
                            name="거래량",
                            marker_color='rgba(0, 100, 255, 0.5)'
                        ),
                        row=2, col=1
                    )
                
                # MACD 선
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=macd,
                        mode='lines',
                        name='MACD',
                        line=dict(color='blue', width=1)
                    ),
                    row=3, col=1
                )
                
                # 시그널 선
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=signal,
                        mode='lines',
                        name='Signal',
                        line=dict(color='red', width=1)
                    ),
                    row=3, col=1
                )
                
                # 히스토그램
                fig.add_trace(
                    go.Bar(
                        x=df['dates'],
                        y=hist,
                        name='Histogram',
                        marker_color=np.where(hist > 0, 'green', 'red')
                    ),
                    row=3, col=1
                )
            
            if "스토캐스틱" in indicators:
                # 스토캐스틱 계산 (14, 3, 3 기본값)
                def calculate_stochastic(data, k_window=14, d_window=3):
                    low_min = df['low'].rolling(window=k_window).min()
                    high_max = df['high'].rolling(window=k_window).max()
                    
                    k = 100 * ((df['close'] - low_min) / (high_max - low_min))
                    d = k.rolling(window=d_window).mean()
                    
                    return k, d
                
                # 데이터가 없으면 임시 데이터 생성
                if 'low' not in df.columns or 'high' not in df.columns:
                    df['low'] = chart_data.get("lows", df['close'])
                    df['high'] = chart_data.get("highs", df['close'])
                
                k, d = calculate_stochastic(df)
                
                # 스토캐스틱 추가 (거래량 차트 대체)
                fig.update_layout(
                    height=700
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=k,
                        mode='lines',
                        name='%K',
                        line=dict(color='blue', width=1)
                    ),
                    row=2, col=1
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=d,
                        mode='lines',
                        name='%D',
                        line=dict(color='red', width=1)
                    ),
                    row=2, col=1
                )
                
                # 참조선 추가 (20, 80)
                fig.add_hline(y=80, line_dash="dash", line_color="red", opacity=0.7, row=2, col=1)
                fig.add_hline(y=20, line_dash="dash", line_color="green", opacity=0.7, row=2, col=1)
                
                # 축 범위 설정
                fig.update_yaxes(range=[0, 100], title_text="스토캐스틱", row=2, col=1)
            
            # 차트 레이아웃 업데이트
            fig.update_layout(
                height=700,
                title_text=f"{ticker} 차트 ({period}, {chart_type})",
                xaxis_rangeslider_visible=False,
                template="plotly_white",
                hovermode="x unified"
            )
            
            return fig
        except Exception as e:
            print(f"Error in apply_technical_indicators: {e}")
            import traceback
            traceback.print_exc()
            return load_stock_chart(ticker, country, period, chart_type)
    
    components["apply_indicators_btn"].click(
        fn=apply_technical_indicators,
        inputs=[
            components["chart_code"],
            components["chart_country"],
            components["chart_period"],
            components["chart_type"],
            components["moving_avg"],
            components["tech_indicators"]
        ],
        outputs=[components["stock_chart"]]
    )
    
    # 차트 화면에서 돌아가기
    components["back_from_chart_btn"].click(
        fn=lambda: show_container("portfolio"),
        inputs=[],
        outputs=[*containers.values()]
    )
    
    # 거래내역 보기 버튼 클릭 이벤트
    def view_transactions():
        return show_container("transactions")
    
    components["view_transactions_btn"].click(
        fn=view_transactions,
        inputs=[],
        outputs=[*containers.values()]
    )
    
    # 배당 정보 버튼 클릭 이벤트
    def view_dividends():
        return show_container("dividends")
    
    components["view_dividends_btn"].click(
        fn=view_dividends,
        inputs=[],
        outputs=[*containers.values()]
    )
    
    # 종목 편집 버튼 클릭 이벤트
    def edit_stock(code, name, account, quantity, avg_price, sector, country, broker, purchase_date, memo=None):
        # 종목 편집 화면으로 전환
        # 현재 종목 정보를 편집 화면으로 복사
        return (
            *show_container("edit_stock"),
            code,
            name,
            sector,
            country,
            broker,
            account,
            quantity,
            avg_price,
            purchase_date,
            memo or ""
        )
    
    components["edit_stock_btn"].click(
        fn=edit_stock,
        inputs=[
            components["stock_details_code"],
            components["stock_details_name"],
            components["stock_details_account"],
            components["stock_details_quantity"],
            components["stock_details_avg_price"],
            components["stock_details_sector"],
            components["stock_details_country"],
            components["stock_details_broker"],
            components["stock_details_purchase_date"]
        ],
        outputs=[
            *containers.values(),
            components["edit_stock_code"],
            components["edit_stock_name"],
            components["edit_stock_sector"],
            components["edit_stock_country"],
            components["edit_stock_broker"],
            components["edit_stock_account"],
            components["edit_stock_quantity"],
            components["edit_stock_avg_price"],
            components["edit_stock_purchase_date"],
            components["edit_stock_memo"]
        ]
    )
    
    # 종목 정보 업데이트 버튼 클릭 이벤트
    def update_stock_info(state, ticker, name, sector, country, broker, account, quantity, avg_price, purchase_date, memo):
        if not state or not state.get("user_id"):
            return gr.update(value="로그인이 필요합니다.", visible=True)
        
        try:
            # 종목 ID 조회
            stock_details = get_stock_details(ticker, account, state["user_id"])
            
            if not stock_details:
                return gr.update(value="종목 정보를 찾을 수 없습니다.", visible=True)
            
            # 종목 정보 업데이트
            stock_id = stock_details["id"]
            
            # 정보 업데이트
            success = update_portfolio_stock(
                stock_id=stock_id,
                user_id=state["user_id"],
                quantity=quantity,
                sector=sector,
                memo=memo
            )
            
            if success:
                return gr.update(value="종목 정보가 업데이트되었습니다.", visible=True)
            else:
                return gr.update(value="종목 정보 업데이트 중 오류가 발생했습니다.", visible=True)
        except Exception as e:
            return gr.update(value=f"오류 발생: {str(e)}", visible=True)
    
    components["update_stock_btn"].click(
        fn=update_stock_info,
        inputs=[
            session_state,
            components["edit_stock_code"],
            components["edit_stock_name"],
            components["edit_stock_sector"],
            components["edit_stock_country"],
            components["edit_stock_broker"],
            components["edit_stock_account"],
            components["edit_stock_quantity"],
            components["edit_stock_avg_price"],
            components["edit_stock_purchase_date"],
            components["edit_stock_memo"]
        ],
        outputs=[components["edit_stock_result"]]
    )
    
    # 종목 편집 취소 버튼 클릭 이벤트
    components["cancel_edit_btn"].click(
        fn=lambda: show_container("portfolio"),
        inputs=[],
        outputs=[*containers.values()]
    )
    
    # 종목 삭제 버튼 클릭 이벤트
    def delete_stock_handler(state, ticker, account):
        if not state or not state.get("user_id"):
            return "로그인이 필요합니다.", None
        
        try:
            # 종목 ID 조회
            stock_details = get_stock_details(ticker, account, state["user_id"])
            
            if not stock_details:
                return "종목 정보를 찾을 수 없습니다.", None
            
            # 종목 삭제
            stock_id = stock_details["id"]
            success = delete_portfolio_stock(stock_id, state["user_id"])
            
            if success:
                # 포트폴리오 다시 로드
                portfolio_df = load_portfolio(state["user_id"])
                return "종목이 삭제되었습니다.", portfolio_df
            else:
                return "종목 삭제 중 오류가 발생했습니다.", None
        except Exception as e:
            return f"오류 발생: {str(e)}", None
    
    components["delete_stock_btn"].click(
        fn=delete_stock_handler,
        inputs=[
            session_state,
            components["stock_details_code"],
            components["stock_details_account"]
        ],
        outputs=[
            components["login_message"],  # 임시로 로그인 메시지에 결과 표시
            components["portfolio_table"]
        ]
    )
    
    # 매수 화면으로 전환
    def show_buy_screen():
        return show_container("buy")
    
    # 매도 화면으로 전환
    def show_sell_screen():
        return show_container("sell")
    
    # 거래내역 화면으로 전환
    def show_transactions_screen():
        return show_container("transactions")
    
    # 배당금 화면으로 전환
    def show_dividends_screen():
        return show_container("dividends")
    
    # 최적화 화면으로 전환
    def show_optimization_screen():
        return show_container("optimization")
    
    # 매수 버튼 클릭 이벤트
    def buy_stock_handler(state, country, code, name, sector, broker, account, date, quantity, price, currency, exchange_rate, fee, tax, memo):
        if not state or not state.get("user_id"):
            return gr.update(value="로그인이 필요합니다.", visible=True)
        
        if not code or not name or not quantity or not price:
            return gr.update(value="필수 항목을 모두 입력해주세요.", visible=True)
        
        try:
            # 원화 환산 (외화인 경우)
            krw_price = price
            if currency != "KRW":
                krw_price = price * exchange_rate
            
            # 매수 처리
            result = buy_stock(
                user_id=state["user_id"],
                broker=broker,
                account=account,
                country=country,
                ticker=code,
                stock_name=name,
                quantity=quantity,
                price=krw_price,
                memo=memo,
                date=date
            )
            
            if result is not None:
                return gr.update(value=f"매수 완료: {name} ({code}), {quantity}주", visible=True)
            else:
                return gr.update(value="매수 처리 중 오류가 발생했습니다.", visible=True)
        except Exception as e:
            return gr.update(value=f"오류 발생: {str(e)}", visible=True)
    
    components["buy_btn"].click(
        fn=buy_stock_handler,
        inputs=[
            session_state,
            components["buy_country"],
            components["buy_code"],
            components["buy_name"],
            components["buy_sector"],
            components["buy_broker"],
            components["buy_account"],
            components["buy_date"],
            components["buy_quantity"],
            components["buy_price"],
            components["buy_currency"],
            components["buy_exchange_rate"],
            components["buy_fee"],
            components["buy_tax"],
            components["buy_memo"]
        ],
        outputs=[components["buy_result"]]
    )
    
    # 매수 취소 버튼 클릭 이벤트
    components["cancel_buy_btn"].click(
        fn=lambda: show_container("portfolio"),
        inputs=[],
        outputs=[*containers.values()]
    )
    
    # 종목 정보 조회 버튼 클릭 이벤트
    def lookup_stock_info(country, code):
        if not code:
            return gr.update(), gr.update(), gr.update(), gr.update()
        
        try:
            # 국가에 따른 정보 조회
            if country == "한국":
                info = get_krx_stock_info(code)
            else:
                info = get_international_stock_info(code, country)
            
            if not info:
                return gr.update(), gr.update(), gr.update(), gr.update()
            
            return (
                gr.update(value=info.get("name", "")),
                gr.update(value=info.get("sector", "")),
                gr.update(value=info.get("current_price", 0)),
                gr.update(value="종목 정보를 성공적으로 가져왔습니다.")
            )
        except Exception as e:
            return (
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(value=f"종목 정보 조회 실패: {str(e)}")
            )
    
    components["lookup_stock_btn"].click(
        fn=lookup_stock_info,
        inputs=[
            components["buy_country"],
            components["buy_code"]
        ],
        outputs=[
            components["buy_name"],
            components["buy_sector"],
            components["buy_price"],
            components["buy_result"]
        ]
    )
    
    # 현재가 가져오기 버튼 클릭 이벤트
    def get_current_price(country, code, currency):
        if not code:
            return gr.update(), gr.update(value="종목코드를 입력해주세요.", visible=True)
        
        try:
            # 국가에 따른 현재가 조회
            if country == "한국":
                price = get_krx_stock_price(code)
                exchange_rate = 1.0
            else:
                price = get_international_stock_price(code, country)
                
                # 환율 조회 (USD 기준)
                if currency != "KRW" and currency != "USD":
                    exchange_rate = get_exchange_rate(currency, "KRW")
                else:
                    exchange_rate = get_exchange_rate("USD", "KRW")
            
            if not price:
                return gr.update(), gr.update(value="현재가를 가져올 수 없습니다.", visible=True)
            
            return (
                gr.update(value=price),
                gr.update(value=f"현재가: {price} {currency}", visible=True)
            )
        except Exception as e:
            return (
                gr.update(),
                gr.update(value=f"현재가 조회 실패: {str(e)}", visible=True)
            )
    
    components["get_price_btn"].click(
        fn=get_current_price,
        inputs=[
            components["buy_country"],
            components["buy_code"],
            components["buy_currency"]
        ],
        outputs=[
            components["buy_price"],
            components["buy_result"]
        ]
    )
    
    # 환율 정보 업데이트 (통화 변경 시)
    def update_exchange_rate(currency):
        if currency == "KRW":
            return gr.update(value=1.0, interactive=False)
        
        try:
            # 환율 조회
            rate = get_exchange_rate(currency, "KRW")
            
            if not rate:
                return gr.update(value=1.0, interactive=True)
            
            return gr.update(value=rate, interactive=True)
        except Exception as e:
            print(f"Error in update_exchange_rate: {e}")
            return gr.update(value=1.0, interactive=True)
    
    components["buy_currency"].change(
        fn=update_exchange_rate,
        inputs=[components["buy_currency"]],
        outputs=[components["buy_exchange_rate"]]
    )
    
    # 매수 금액 계산 버튼 클릭 이벤트
    def calculate_buy_amount(quantity, price, exchange_rate, fee, tax):
        try:
            # 기본값 처리
            quantity = quantity or 0
            price = price or 0
            exchange_rate = exchange_rate or 1.0
            fee = fee or 0
            tax = tax or 0
            
            # 총 금액 계산 (원화 기준)
            amount = quantity * price * exchange_rate
            
            # 수수료 및 세금 추가
            amount += (amount * fee / 100) if fee > 0 else 0
            amount += (amount * tax / 100) if tax > 0 else 0
            
            return gr.update(value=amount)
        except Exception as e:
            print(f"Error in calculate_buy_amount: {e}")
            return gr.update()
    
    components["calculate_btn"].click(
        fn=calculate_buy_amount,
        inputs=[
            components["buy_quantity"],
            components["buy_price"],
            components["buy_exchange_rate"],
            components["buy_fee"],
            components["buy_tax"]
        ],
        outputs=[components["buy_total"]]
    )
    
    # 보유 종목 목록 새로고침 버튼 클릭 이벤트
    def refresh_owned_stocks(state):
        if not state or not state.get("user_id"):
            return gr.update(choices=[])
        
        try:
            # 보유 종목 목록 조회
            stocks = get_owned_stocks(state["user_id"])
            
            if not stocks:
                return gr.update(choices=[])
            
            # 드롭다운 항목 생성
            choices = [(f"{stock['종목명']} ({stock['종목코드']}) - {stock['계좌']} - {stock['수량']}주", 
                      [stock['종목코드'], stock['계좌']]) for stock in stocks]
            
            return gr.update(choices=choices)
        except Exception as e:
            print(f"Error in refresh_owned_stocks: {e}")
            return gr.update(choices=[])
    
    components["refresh_stock_list_btn"].click(
        fn=refresh_owned_stocks,
        inputs=[session_state],
        outputs=[components["sell_stock_dropdown"]]
    )
    
    # 종목 선택 시 매도 폼 업데이트
    def update_sell_form(selected, state):
        if not selected or not state or not state.get("user_id"):
            return [gr.update() for _ in range(9)]
        
        try:
            # 선택한 종목 정보 파싱
            ticker, account = selected
            
            # 종목 상세 정보 조회
            stock = get_stock_details(ticker, account, state["user_id"])
            
            if not stock:
                return [gr.update() for _ in range(9)]
            
            # 폼 필드 업데이트
            return [
                gr.update(value=ticker),  # sell_code
                gr.update(value=stock.get("종목명", "")),  # sell_name
                gr.update(value=stock.get("증권사", "")),  # sell_broker
                gr.update(value=account),  # sell_account
                gr.update(value=stock.get("국가", "")),  # sell_country
                gr.update(value=stock.get("수량", 0)),  # sell_own_quantity
                gr.update(value=stock.get("평단가_원화", 0)),  # sell_avg_price
                gr.update(value=stock.get("현재가_원화", 0)),  # sell_current_price
                gr.update(value="KRW")  # sell_currency
            ]
        except Exception as e:
            print(f"Error in update_sell_form: {e}")
            return [gr.update() for _ in range(9)]
    
    components["sell_stock_dropdown"].change(
        fn=update_sell_form,
        inputs=[components["sell_stock_dropdown"], session_state],
        outputs=[
            components["sell_code"],
            components["sell_name"],
            components["sell_broker"],
            components["sell_account"],
            components["sell_country"],
            components["sell_own_quantity"],
            components["sell_avg_price"],
            components["sell_current_price"],
            components["sell_currency"]
        ]
    )
    
    # 매도 현재가 가져오기 버튼 클릭 이벤트
    components["get_sell_price_btn"].click(
        fn=get_current_price,
        inputs=[
            components["sell_country"],
            components["sell_code"],
            components["sell_currency"]
        ],
        outputs=[
            components["sell_price"],
            components["sell_result"]
        ]
    )
    
    # 전량 매도 버튼 클릭 이벤트
    def set_all_quantity(own_quantity):
        return gr.update(value=own_quantity)
    
    components["set_all_quantity_btn"].click(
        fn=set_all_quantity,
        inputs=[components["sell_own_quantity"]],
        outputs=[components["sell_quantity"]]
    )
    
    # 매도 손익 계산 버튼 클릭 이벤트
    def calculate_sell_profit(quantity, price, avg_price, fee, tax):
        try:
            # 기본값 처리
            quantity = quantity or 0
            price = price or 0
            avg_price = avg_price or 0
            fee = fee or 0
            tax = tax or 0
            
            # 총 매도금액 계산
            sell_amount = quantity * price
            
            # 수수료 및 세금 차감
            sell_amount -= (sell_amount * fee / 100) if fee > 0 else 0
            sell_amount -= (sell_amount * tax / 100) if tax > 0 else 0
            
            # 매수금액
            buy_amount = quantity * avg_price
            
            # 손익 계산
            profit = sell_amount - buy_amount
            
            # 수익률 계산
            profit_percent = (profit / buy_amount * 100) if buy_amount > 0 else 0
            
            return [
                gr.update(value=sell_amount),
                gr.update(value=profit),
                gr.update(value=profit_percent)
            ]
        except Exception as e:
            print(f"Error in calculate_sell_profit: {e}")
            return [gr.update(), gr.update(), gr.update()]
    
    components["calculate_sell_btn"].click(
        fn=calculate_sell_profit,
        inputs=[
            components["sell_quantity"],
            components["sell                with gr.Row():
                    add_dividend_btn = gr.Button("배당금 추가", variant="primary", elem_classes="action-button")
                    calculate_dividend_tax_btn = gr.Button("세금 계산", elem_classes="secondary-button")
                    cancel_dividend_btn = gr.Button("취소", elem_classes="secondary-button")
                
                dividend_result = gr.Textbox(label="결과", visible=False, interactive=False, elem_classes="result-message")
    
    containers["dividends"] = dividends_container
    
    # 종목 차트 화면
    with gr.Group(visible=False) as chart_container:
        gr.Markdown("## 종목 차트", elem_classes="header-text")
        
        with gr.Row():
            chart_stock_info = gr.Markdown("**종목 정보를 불러오는 중...**", elem_classes="stock-info")
        
        with gr.Row():
            with gr.Column(scale=4):
                chart_period = gr.Radio(
                    ["1개월", "3개월", "6개월", "1년", "3년", "전체"],
                    label="기간",
                    value="1년",
                    interactive=True
                )
            
            with gr.Column(scale=1):
                chart_type = gr.Radio(
                    ["일봉", "주봉", "월봉"],
                    label="주기",
                    value="일봉",
                    interactive=True
                )
        
        with gr.Row():
            stock_chart = gr.Plot(label="종목 차트")
        
        with gr.Row():
            chart_code = gr.Textbox(visible=False)  # 종목코드 저장용
            chart_country = gr.Textbox(visible=False)  # 국가 저장용
            reload_chart_btn = gr.Button("차트 새로고침", elem_classes="secondary-button")
            back_from_chart_btn = gr.Button("돌아가기", elem_classes="secondary-button")
        
        with gr.Accordion("기술적 지표", open=False):
            with gr.Row():
                with gr.Column():
                    moving_avg = gr.CheckboxGroup(
                        ["5일선", "20일선", "60일선", "120일선"],
                        label="이동평균선"
                    )
                
                with gr.Column():
                    tech_indicators = gr.CheckboxGroup(
                        ["MACD", "RSI", "볼린저밴드", "스토캐스틱"],
                        label="기술적 지표"
                    )
            
            apply_indicators_btn = gr.Button("지표 적용", elem_classes="secondary-button")
    
    containers["chart"] = chart_container
    
    # 포트폴리오 최적화 화면
    with gr.Group(visible=False) as optimization_container:
        gr.Markdown("## 포트폴리오 최적화", elem_classes="header-text")
        
        with gr.Row():
            optimization_summary = gr.Markdown(
                "현재 포트폴리오 상태를 분석하고 최적화 방안을 제안합니다.",
                elem_classes="info-text"
            )
        
        with gr.Row():
            start_optimization_btn = gr.Button("포트폴리오 분석 시작", variant="primary", elem_classes="action-button")
        
        with gr.Accordion("리스크 분석", open=True):
            risk_analysis_results = gr.HTML(
                """<div class="result-card">분석 결과를 불러오는 중...</div>""",
                elem_classes="analysis-results"
            )
        
        with gr.Accordion("섹터 다각화", open=True):
            sector_analysis_results = gr.HTML(
                """<div class="result-card">분석 결과를 불러오는 중...</div>""",
                elem_classes="analysis-results"
            )
        
        with gr.Accordion("종목 집중도", open=True):
            concentration_analysis_results = gr.HTML(
                """<div class="result-card">분석 결과를 불러오는 중...</div>""",
                elem_classes="analysis-results"
            )
        
        with gr.Accordion("수익률 개선 방안", open=True):
            performance_improvement_results = gr.HTML(
                """<div class="result-card">분석 결과를 불러오는 중...</div>""",
                elem_classes="analysis-results"
            )
    
    containers["optimization"] = optimization_container
    
    # 종목 편집 화면
    with gr.Group(visible=False) as edit_stock_container:
        gr.Markdown("## 종목 정보 편집", elem_classes="header-text")
        
        # 아이디와 계좌 정보 저장용 숨김 필드
        edit_stock_id = gr.Textbox(visible=False)
        
        with gr.Row():
            with gr.Column():
                edit_stock_code = gr.Textbox(label="종목코드")
                edit_stock_name = gr.Textbox(label="종목명")
                edit_stock_sector = gr.Textbox(label="섹터/산업군")
            
            with gr.Column():
                edit_stock_country = gr.Dropdown(
                    ["한국", "미국", "중국", "일본", "홍콩", "기타"],
                    label="국가"
                )
                edit_stock_broker = gr.Dropdown(
                    ["한투", "신한", "삼성", "미래에셋", "NH", "KB", "기타"],
                    label="증권사"
                )
                edit_stock_account = gr.Dropdown(
                    ["일반", "ISA", "연금", "CMA"],
                    label="계좌"
                )
        
        with gr.Row():
            with gr.Column():
                edit_stock_quantity = gr.Number(label="수량", precision=4)
                edit_stock_avg_price = gr.Number(label="평균 매수가", precision=2)
            
            with gr.Column():
                edit_stock_purchase_date = gr.Textbox(label="최초 매수일", placeholder="YYYY-MM-DD")
                edit_stock_memo = gr.Textbox(label="메모", lines=2)
        
        with gr.Row():
            update_stock_btn = gr.Button("종목 정보 업데이트", variant="primary", elem_classes="action-button")
            cancel_edit_btn = gr.Button("취소", elem_classes="secondary-button")
        
        edit_stock_result = gr.Textbox(label="결과", visible=False, interactive=False, elem_classes="result-message")
    
    containers["edit_stock"] = edit_stock_container
    
    # 모든 컴포넌트 정리
    components.update({
        # 포트폴리오 조회 화면
        "refresh_btn": refresh_btn,
        "export_btn": export_btn,
        "import_btn": import_btn,
        "portfolio_summary": portfolio_summary,
        "portfolio_table": portfolio_table,
        
        # 종목 상세 정보
        "stock_details_code": stock_details_code,
        "stock_details_name": stock_details_name,
        "stock_details_account": stock_details_account,
        "stock_details_quantity": stock_details_quantity,
        "stock_details_avg_price": stock_details_avg_price,
        "stock_details_current": stock_details_current,
        "stock_details_value": stock_details_value,
        "stock_details_gain_loss": stock_details_gain_loss,
        "stock_details_return": stock_details_return,
        "stock_details_dividend": stock_details_dividend,
        "stock_details_sector": stock_details_sector,
        "stock_details_country": stock_details_country,
        "stock_details_broker": stock_details_broker,
        "stock_details_purchase_date": stock_details_purchase_date,
        "view_chart_btn": view_chart_btn,
        "view_transactions_btn": view_transactions_btn,
        "view_dividends_btn": view_dividends_btn,
        "edit_stock_btn": edit_stock_btn,
        "delete_stock_btn": delete_stock_btn,
        
        # 매수 화면
        "buy_tabs": buy_tabs,
        "buy_country": buy_country,
        "buy_code": buy_code,
        "buy_name": buy_name,
        "buy_sector": buy_sector,
        "buy_broker": buy_broker,
        "buy_account": buy_account,
        "buy_date": buy_date,
        "buy_quantity": buy_quantity,
        "buy_price": buy_price,
        "buy_currency": buy_currency,
        "buy_exchange_rate": buy_exchange_rate,
        "buy_fee": buy_fee,
        "buy_tax": buy_tax,
        "buy_memo": buy_memo,
        "buy_total": buy_total,
        "lookup_stock_btn": lookup_stock_btn,
        "get_price_btn": get_price_btn,
        "calculate_btn": calculate_btn,
        "buy_btn": buy_btn,
        "cancel_buy_btn": cancel_buy_btn,
        "buy_result": buy_result,
        
        # 매도 화면
        "sell_stock_dropdown": sell_stock_dropdown,
        "refresh_stock_list_btn": refresh_stock_list_btn,
        "sell_code": sell_code,
        "sell_name": sell_name,
        "sell_broker": sell_broker,
        "sell_account": sell_account,
        "sell_country": sell_country,
        "sell_own_quantity": sell_own_quantity,
        "sell_avg_price": sell_avg_price,
        "sell_current_price": sell_current_price,
        "sell_date": sell_date,
        "sell_quantity": sell_quantity,
        "sell_price": sell_price,
        "sell_fee": sell_fee,
        "sell_tax": sell_tax,
        "sell_currency": sell_currency,
        "sell_memo": sell_memo,
        "sell_total": sell_total,
        "sell_profit": sell_profit,
        "sell_profit_percent": sell_profit_percent,
        "get_sell_price_btn": get_sell_price_btn,
        "calculate_sell_btn": calculate_sell_btn,
        "set_all_quantity_btn": set_all_quantity_btn,
        "sell_btn": sell_btn,
        "cancel_sell_btn": cancel_sell_btn,
        "sell_result": sell_result,
        
        # 거래내역 화면
        "load_transaction_btn": load_transaction_btn,
        "transactions_filter": transactions_filter,
        "transactions_search": transactions_search,
        "transactions_period": transactions_period,
        "transaction_table": transaction_table,
        "export_transactions_btn": export_transactions_btn,
        
        # 배당금 화면
        "dividend_tabs": dividend_tabs,
        "load_dividends_btn": load_dividends_btn,
        "dividends_period": dividends_period,
        "dividends_table": dividends_table,
        "dividends_summary": dividends_summary,
        "dividend_stock_dropdown": dividend_stock_dropdown,
        "refresh_dividend_stocks_btn": refresh_dividend_stocks_btn,
        "dividend_date": dividend_date,
        "dividend_amount": dividend_amount,
        "dividend_currency": dividend_currency,
        "dividend_type": dividend_type,
        "dividend_pretax": dividend_pretax,
        "dividend_posttax": dividend_posttax,
        "dividend_tax_rate": dividend_tax_rate,
        "dividend_memo": dividend_memo,
        "add_dividend_btn": add_dividend_btn,
        "calculate_dividend_tax_btn": calculate_dividend_tax_btn,
        "cancel_dividend_btn": cancel_dividend_btn,
        "dividend_result": dividend_result,
        
        # 차트 화면
        "chart_stock_info": chart_stock_info,
        "chart_period": chart_period,
        "chart_type": chart_type,
        "stock_chart": stock_chart,
        "chart_code": chart_code,
        "chart_country": chart_country,
        "reload_chart_btn": reload_chart_btn,
        "back_from_chart_btn": back_from_chart_btn,
        "moving_avg": moving_avg,
        "tech_indicators": tech_indicators,
        "apply_indicators_btn": apply_indicators_btn,
        
        # 포트폴리오 최적화 화면
        "optimization_summary": optimization_summary,
        "start_optimization_btn": start_optimization_btn,
        "risk_analysis_results": risk_analysis_results,
        "sector_analysis_results": sector_analysis_results,
        "concentration_analysis_results": concentration_analysis_results,
        "performance_improvement_results": performance_improvement_results,
        
        # 종목 편집 화면
        "edit_stock_id": edit_stock_id,
        "edit_stock_code": edit_stock_code,
        "edit_stock_name": edit_stock_name,
        "edit_stock_sector": edit_stock_sector,
        "edit_stock_country": edit_stock_country,
        "edit_stock_broker": edit_stock_broker,
        "edit_stock_account": edit_stock_account,
        "edit_stock_quantity": edit_stock_quantity,
        "edit_stock_avg_price": edit_stock_avg_price,
        "edit_stock_purchase_date": edit_stock_purchase_date,
        "edit_stock_memo": edit_stock_memo,
        "update_stock_btn": update_stock_btn,
        "cancel_edit_btn": cancel_edit_btn,
        "edit_stock_result": edit_stock_result
    })
    
    return containers, components

def setup_portfolio_events(app, session_state, containers, components):
    """
    포트폴리오 관련 이벤트 설정
    
    Args:
        app: Gradio 앱 인스턴스
        session_state: 세션 상태 컴포넌트
        containers: UI 컨테이너 딕셔너리
        components: UI 컴포넌트 딕셔너리
    """
    try:
        from services.portfolio_service import (
            update_all_prices, load_portfolio, buy_stock, sell_stock, 
            load_transactions, get_owned_stocks, get_stock_details,
            add_dividend, get_dividends_by_user, calculate_optimal_portfolio,
            export_portfolio_to_csv, import_portfolio_from_csv,
            update_portfolio_stock, delete_portfolio_stock
        )
        from services.market_service import (
            get_krx_stock_info, get_international_stock_info,
            get_krx_stock_price, get_international_stock_price,
            get_exchange_rate, get_stock_chart_data
        )
    except ImportError as e:
        print(f"Error importing services: {e}")
        return
    
    # 화면 전환 함수
    def show_container(container_name):
        """특정 컨테이너만 표시하고 나머지는 숨김"""
        return [gr.update(visible=(name == container_name)) for name in containers.keys()]
    
    # 포트폴리오 요약 정보 HTML 생성
    def create_portfolio_summary_html(state):
        try:
            if not state or not state.get("user_id"):
                return """<div class="summary-card error">로그인이 필요합니다</div>"""
            
            from services.portfolio_service import get_portfolio_summary
            portfolio_data = get_portfolio_summary(state["user_id"])
            
            summary = portfolio_data["summary"]
            
            # 포트폴리오 요약 HTML 생성
            html = f"""
            <div class="summary-card">
                <div class="summary-row">
                    <div class="summary-item">
                        <div class="summary-label">총 평가액</div>
                        <div class="summary-value">{summary['total_value']:,.0f}원</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">총 투자금액</div>
                        <div class="summary-value">{summary['total_cost']:,.0f}원</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">총 손익</div>
                        <div class="summary-value {get_color_class(summary['total_gain_loss'])}">{summary['total_gain_loss']:,.0f}원</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">투자 수익률</div>
                        <div class="summary-value {get_color_class(summary['total_return_percent'])}">{summary['total_return_percent']:.2f}%</div>
                    </div>
                </div>
                <div class="summary-row">
                    <div class="summary-item">
                        <div class="summary-label">종목 수</div>
                        <div class="summary-value">{summary['stock_count']}개</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">배당금 총액</div>
                        <div class="summary-value">{summary['total_dividend']:,.0f}원</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">배당 수익률</div>
                        <div class="summary-value">{summary['dividend_yield']:.2f}%</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-label">총 수익률(배당포함)</div>
                        <div class="summary-value {get_color_class(summary['total_return_with_dividend'])}">{summary['total_return_with_dividend']:.2f}%</div>
                    </div>
                </div>
            </div>
            """
            return html
        except Exception as e:
            return f"""<div class="summary-card error">포트폴리오 요약 정보를 불러오는 중 오류가 발생했습니다: {str(e)}</div>"""
    
    def get_color_class(value):
        """값에 따른 색상 클래스 반환"""
        if value > 0:
            return "positive"
        elif value < 0:
            return "negative"
        else:
            return ""
            
    # 가격 업데이트 버튼 클릭 이벤트
    def refresh_portfolio(state):
        try:
            if not state or not state.get("user_id"):
                return (
                    None, 
                    """<div class="summary-card error">로그인이 필요합니다</div>"""
                )
            
            # 가격 업데이트 후 포트폴리오 데이터 로드
            update_all_prices(state["user_id"])
            portfolio_df = load_portfolio(state["user_id"])
            
            # 포트폴리오 요약 정보 업데이트
            summary_html = create_portfolio_summary_html(state)
            
            return portfolio_df, summary_html
        except Exception as e:
            return (
                None,
                f"""<div class="summary-card error">포트폴리오 업데이트 중 오류가 발생했습니다: {str(e)}</div>"""
            )
    
    components["refresh_btn"].click(
        fn=refresh_portfolio,
        inputs=[session_state],
        outputs=[
            components["portfolio_table"],
            components["portfolio_summary"]
        ]
    )
    
    # 포트폴리오 테이블 행 선택 이벤트 (종목 상세 정보 표시)
    def show_stock_details(state, evt: gr.SelectData):
        if not state or not state.get("user_id"):
            return [gr.update() for _ in range(14)]
        
        try:
            # 선택한 행 인덱스와 데이터 가져오기
            row_index = evt.index[0]
            
            # 포트폴리오 데이터 로드
            portfolio_df = load_portfolio(state["user_id"])
            
            if portfolio_df is None or portfolio_df.empty or row_index >= len(portfolio_df):
                return [gr.update() for _ in range(14)]
            
            # 선택한 행 데이터
            selected_row = portfolio_df.iloc[row_index]
            
            # 종목코드
            ticker = selected_row.get("종목코드")
            account = selected_row.get("계좌")
            
            # 종목 상세 정보 조회
            stock_details = get_stock_details(ticker, account, state["user_id"])
            
            if not stock_details:
                return [gr.update() for _ in range(14)]
            
            # 반환할 값 준비 (UI 컴포넌트에 맞게 변환)
            values = [
                ticker,  # 종목코드
                selected_row.get("종목명", ""),  # 종목명
                account,  # 계좌
                float(stock_details.get("수량", 0)),  # 수량
                float(stock_details.get("평단가_원화", 0)),  # 평단가
                float(stock_details.get("현재가_원화", 0)),  # 현재가
                float(stock_details.get("평가액", 0)),  # 평가액
                float(stock_details.get("손익금액", 0)),  # 손익
                float(stock_details.get("손익수익", 0)),  # 수익률
                float(stock_details.get("배당금", 0)),  # 누적배당금
                stock_details.get("섹터", ""),  # 섹터
                stock_details.get("국가", ""),  # 국가
                stock_details.get("증권사", ""),  # 증권사
                stock_details.get("매수날짜", datetime.now().strftime("%Y-%m-%d"))  # 최초매수일
            ]
            
            return values
        except Exception as e:
            print(f"Error in show_stock_details: {e}")
            return [gr.update() for _ in range(14)]
    
    if hasattr(components["portfolio_table"], "select"):
        components["portfolio_table"].select(
            fn=show_stock_details,
            inputs=[session_state],
            outputs=[
                components["stock_details_code"],
                components["stock_details_name"],
                components["stock_details_account"],
                components["stock_details_quantity"],
                components["stock_details_avg_price"],
                components["stock_details_current"],
                components["stock_details_value"],
                components["stock_details_gain_loss"],
                components["stock_details_return"],
                components["stock_details_dividend"],
                components["stock_details_sector"],
                components["stock_details_country"],
                components["stock_details_broker"],
                components["stock_details_purchase_date"]
            ]
        )
    
    # 차트 보기 버튼 클릭 이벤트
    def view_stock_chart(ticker, name, country):
        # 차트 화면으로 전환 및 초기 데이터 설정
        return (
            *show_container("chart"),
            f"**{name} ({ticker})** - {country}",
            gr.update(value=ticker),
            gr.update(value=country)
        )
    
    components["view_chart_btn"].click(
        fn=view_stock_chart,
        inputs=[
            components["stock_details_code"],
            components["stock_details_name"],
            components["stock_details_country"]
        ],
        outputs=[
            *containers.values(),
            components["chart_stock_info"],
            components["chart_code"],
            components["chart_country"]
        ]
    )
    
    # 종목 차트 로드
    def load_stock_chart(ticker, country, period, chart_type):
        try:
            if not ticker:
                return None
            
            # 기간 변환
            period_map = {
                "1개월": "1m",
                "3개월": "3m",
                "6개월": "6m",
                "1년": "1y",
                "3년": "5y",  # API에서 3년이 없으면 5년으로 대체
                "전체": "max"
            }
            
            # 주기 변환
            interval_map = {
                "일봉": "1d",
                "주봉": "1wk",
                "월봉": "1mo"
            }
            
            # 차트 데이터 조회
            api_period = period_map.get(period, "1y")
            api_interval = interval_map.get(chart_type, "1d")
            
            chart_data = get_stock_chart_data(ticker, country, api_period, api_interval)
            
            if not chart_data or "dates" not in chart_data:
                return None
            
            # Plotly 차트 생성
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            # 캔들스틱 차트 생성
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.7, 0.3],
                subplot_titles=(f"{ticker} 가격 차트", "거래량")
            )
            
            # 캔들스틱 추가
            fig.add_trace(
                go.Candlestick(
                    x=chart_data["dates"],
                    open=chart_data["opens"],
                    high=chart_data["highs"],
                    low=chart_data["lows"],
                    close=chart_data["closes"],
                    name="가격"
                ),
                row=1, col=1
            )
            
            # 거래량 추가
            if "volumes" in chart_data and chart_data["volumes"]:
                fig.add_trace(
                    go.Bar(
                        x=chart_data["dates"],
                        y=chart_data["volumes"],
                        name="거래량",
                        marker_color='rgba(0, 100, 255, 0.5)'
                    ),
                    row=2, col=1
                )
            
            # 차트 레이아웃 설정
            fig.update_layout(
                height=600,
                title_text=f"{ticker} 차트 ({period}, {chart_type})",
                xaxis_rangeslider_visible=False,
                template="plotly_white",
                hovermode="x unified"
            )
            
            return fig
        except Exception as e:
            print(f"Error in load_stock_chart: {e}")
            return None
    
    # 차트 기간 및 주기 변경 이벤트
    def update_chart(ticker, country, period, chart_type):
        return load_stock_chart(ticker, country, period, chart_type)
    
    components["chart_period"].change(
        fn=update_chart,
        inputs=[
            components["chart_code"],
            components["chart_country"],
            components["chart_period"],
            components["chart_type"]
        ],
        outputs=[components["stock_chart"]]
    )
    
    components["chart_type"].change(
        fn=update_chart,
        inputs=[
            components["chart_code"],
            components["chart_country"],
            components["chart_period"],
            components["chart_type"]
        ],
        outputs=[components["stock_chart"]]
    )
    
    # 차트 새로고침 버튼 클릭 이벤트
    components["reload_chart_btn"].click(
        fn=update_chart,
        inputs=[
            components["chart_code"],
            components["chart_country"],
            components["chart_period"],
            components["chart_type"]
        ],
        outputs=[components["stock_chart"]]
    )
    
    # 기술적 지표 적용 버튼 클릭 이벤트
    def apply_technical_indicators(ticker, country, period, chart_type, moving_avgs, indicators):
        try:
            # 기본 차트 로드
            fig = load_stock_chart(ticker, country, period, chart_type)
            
            if fig is None:
                return None
            
            # 이동평균선 추가
            chart_data = get_stock_chart_data(ticker, country, period, chart_type)
            
            if not chart_data or "dates" not in chart_data or not chart_data["dates"]:
                return fig
            
            import numpy as np
            import pandas as pd
            
            # 데이터프레임 생성
            df = pd.DataFrame({
                'dates': chart_data["dates"],
                'close': chart_data["closes"]
            })
            
            # 이동평균선 추가
            if "5일선" in moving_avgs:
                ma5 = df['close'].rolling(window=5).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=ma5,
                        mode='lines',
                        name='5일 이동평균',
                        line=dict(color='blue', width=1)
                    ),
                    row=1, col=1
                )
            
            if "20일선" in moving_avgs:
                ma20 = df['close'].rolling(window=20).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df['dates'],
                        y=ma20,
                        mode='lines',
                        name='20일"""
포트폴리오 관련 UI 컴포넌트 - 고급 포트폴리오 관리 및 분석 기능 추가
"""
import gradio as gr
import pandas as pd
import json
from datetime import datetime, timedelta

def create_portfolio_ui():
    """
    포트폴리오 관련 UI 컴포넌트 생성
    
    Returns:
        tuple: (컨테이너 딕셔너리, 컴포넌트 딕셔너리)
    """
    # 컨테이너 딕셔너리 (각 화면)
    containers = {}
    
    # 컴포넌트 딕셔너리 (모든 UI 요소)
    components = {}
    
    # 포트폴리오 조회 화면
    with gr.Group() as portfolio_container:
        gr.Markdown("## 포트폴리오 현황", elem_classes="header-text")
        
        with gr.Row():
            refresh_btn = gr.Button("시장 데이터 업데이트", variant="primary", elem_classes="action-button")
            export_btn = gr.Button("내보내기", elem_classes="secondary-button")
            import_btn = gr.Button("가져오기", elem_classes="secondary-button")
        
        with gr.Row():
            portfolio_summary = gr.HTML(
                """<div class="summary-card">포트폴리오 요약 정보를 불러오는 중...</div>""",
                elem_classes="summary-info"
            )
        
        with gr.Row():
            portfolio_table = gr.Dataframe(
                headers=[
                    "증권사", "계좌", "국가", "종목코드", "종목명", "수량", 
                    "평단가(원화)", "평단가(달러)", "현재가(원화)", "현재가(달러)",
                    "평가액[원화]", "투자비중", "손익금액[원화]", "손익수익[원화]", "총수익률[원가+배당]"
                ],
                interactive=False,
                wrap=True,
                height=400,
                elem_classes="portfolio-table"
            )
        
        # 종목 상세 정보 패널
        with gr.Accordion("종목 상세 정보", open=False):
            with gr.Row(equal_height=True):
                stock_details_code = gr.Textbox(label="종목코드", interactive=False)
                stock_details_name = gr.Textbox(label="종목명", interactive=False)
                stock_details_account = gr.Textbox(label="계좌", interactive=False)
                stock_details_quantity = gr.Number(label="수량", precision=2, interactive=False)
                stock_details_avg_price = gr.Number(label="평단가", precision=2, interactive=False)
            
            with gr.Row(equal_height=True):
                stock_details_current = gr.Number(label="현재가", precision=2, interactive=False)
                stock_details_value = gr.Number(label="평가액", precision=0, interactive=False)
                stock_details_gain_loss = gr.Number(label="손익", precision=0, interactive=False)
                stock_details_return = gr.Number(label="수익률", precision=2, interactive=False)
                stock_details_dividend = gr.Number(label="누적배당금", precision=0, interactive=False)
            
            with gr.Row():
                stock_details_sector = gr.Textbox(label="섹터", interactive=False)
                stock_details_country = gr.Textbox(label="국가", interactive=False)
                stock_details_broker = gr.Textbox(label="증권사", interactive=False)
                stock_details_purchase_date = gr.Textbox(label="최초매수일", interactive=False)
            
            with gr.Row():
                view_chart_btn = gr.Button("차트 보기", elem_classes="secondary-button")
                view_transactions_btn = gr.Button("거래내역 보기", elem_classes="secondary-button")
                view_dividends_btn = gr.Button("배당 정보", elem_classes="secondary-button")
                edit_stock_btn = gr.Button("종목 편집", elem_classes="secondary-button")
                delete_stock_btn = gr.Button("종목 삭제", variant="stop", elem_classes="danger-button")
    
    containers["portfolio"] = portfolio_container
    
    # 종목 매수 화면
    with gr.Group(visible=False) as buy_container:
        gr.Markdown("## 주식 매수", elem_classes="header-text")
        
        with gr.Tabs() as buy_tabs:
            with gr.Tab("기본 정보"):
                with gr.Row():
                    with gr.Column():
                        buy_country = gr.Dropdown(
                            ["한국", "미국", "중국", "일본", "홍콩", "기타"], 
                            label="국가",
                            value="한국"
                        )
                        buy_code = gr.Textbox(label="종목코드", placeholder="예: 005930, AAPL")
                        buy_name = gr.Textbox(label="종목명", placeholder="예: 삼성전자, Apple Inc.")
                        buy_sector = gr.Textbox(label="섹터/산업군", placeholder="예: 전자, IT")
                    
                    with gr.Column():
                        buy_broker = gr.Dropdown(
                            ["한투", "신한", "삼성", "미래에셋", "NH", "KB", "기타"],
                            label="증권사"
                        )
                        buy_account = gr.Dropdown(
                            ["일반", "ISA", "연금", "CMA"],
                            label="계좌"
                        )
                        buy_date = gr.Textbox(
                            label="매수일",
                            value=datetime.now().strftime("%Y-%m-%d"),
                            placeholder="YYYY-MM-DD"
                        )
            
            with gr.Tab("거래 정보"):
                with gr.Row():
                    with gr.Column():
                        buy_quantity = gr.Number(label="수량", precision=4, placeholder="0")
                        buy_price = gr.Number(label="매수가", precision=2, placeholder="0")
                        buy_currency = gr.Dropdown(
                            ["KRW", "USD", "JPY", "HKD", "CNY"],
                            label="통화",
                            value="KRW"
                        )
                    
                    with gr.Column():
                        buy_exchange_rate = gr.Number(
                            label="환율 (KRW 기준)",
                            precision=2,
                            value=1.0,
                            interactive=True
                        )
                        buy_fee = gr.Number(label="수수료", precision=2, value=0)
                        buy_tax = gr.Number(label="세금", precision=2, value=0)
                
                with gr.Row():
                    buy_memo = gr.Textbox(
                        label="메모",
                        placeholder="매수 관련 메모를 입력하세요",
                        lines=2
                    )
                    
                with gr.Row():
                    buy_total = gr.Number(
                        label="총 매수금액 (KRW)",
                        precision=0,
                        interactive=False
                    )
        
        with gr.Row():
            lookup_stock_btn = gr.Button("종목 정보 조회", elem_classes="secondary-button")
            get_price_btn = gr.Button("현재가 가져오기", elem_classes="secondary-button")
            calculate_btn = gr.Button("금액 계산", elem_classes="secondary-button")
        
        with gr.Row():
            buy_btn = gr.Button("매수하기", variant="primary", size="lg", elem_classes="action-button")
            cancel_buy_btn = gr.Button("취소", elem_classes="secondary-button")
        
        buy_result = gr.Textbox(label="결과", visible=False, interactive=False, elem_classes="result-message")
    
    containers["buy"] = buy_container
    
    # 주식 매도 화면
    with gr.Group(visible=False) as sell_container:
        gr.Markdown("## 주식 매도", elem_classes="header-text")
        
        with gr.Row():
            # 보유 종목 선택 드롭다운
            sell_stock_dropdown = gr.Dropdown(
                [],
                label="보유 종목 선택",
                info="매도할 종목을 선택하세요",
                interactive=True,
                elem_classes="stock-dropdown"
            )
            
            refresh_stock_list_btn = gr.Button("종목 목록 새로고침", elem_classes="secondary-button")
        
        with gr.Row():
            with gr.Column():
                sell_code = gr.Textbox(label="종목코드", interactive=False)
                sell_name = gr.Textbox(label="종목명", interactive=False)
                sell_broker = gr.Textbox(label="증권사", interactive=False)
                sell_account = gr.Textbox(label="계좌", interactive=False)
            
            with gr.Column():
                sell_country = gr.Textbox(label="국가", interactive=False)
                sell_own_quantity = gr.Number(label="보유 수량", precision=4, interactive=False)
                sell_avg_price = gr.Number(label="평균 매수가", precision=2, interactive=False)
                sell_current_price = gr.Number(label="현재가", precision=2, interactive=False)
        
        gr.Markdown("### 매도 정보", elem_classes="subheader-text")
        
        with gr.Row():
            with gr.Column():
                sell_date = gr.Textbox(
                    label="매도일",
                    value=datetime.now().strftime("%Y-%m-%d"),
                    placeholder="YYYY-MM-DD"
                )
                sell_quantity = gr.Number(
                    label="매도 수량",
                    precision=4,
                    placeholder="0",
                    info="전량 매도 시 보유 수량과 동일하게 입력"
                )
                sell_price = gr.Number(
                    label="매도가",
                    precision=2,
                    placeholder="0"
                )
            
            with gr.Column():
                sell_fee = gr.Number(label="수수료", precision=2, value=0)
                sell_tax = gr.Number(label="세금", precision=2, value=0)
                sell_currency = gr.Dropdown(
                    ["KRW", "USD", "JPY", "HKD", "CNY"],
                    label="통화",
                    value="KRW"
                )
        
        with gr.Row():
            sell_memo = gr.Textbox(
                label="메모",
                placeholder="매도 관련 메모를 입력하세요",
                lines=2
            )
        
        # 매도 결과 미리보기
        with gr.Row():
            sell_total = gr.Number(
                label="총 매도금액 (KRW)",
                precision=0,
                interactive=False
            )
            sell_profit = gr.Number(
                label="예상 손익 (KRW)",
                precision=0,
                interactive=False
            )
            sell_profit_percent = gr.Number(
                label="예상 수익률 (%)",
                precision=2,
                interactive=False
            )
        
        with gr.Row():
            get_sell_price_btn = gr.Button("현재가 가져오기", elem_classes="secondary-button")
            calculate_sell_btn = gr.Button("손익 계산", elem_classes="secondary-button")
            set_all_quantity_btn = gr.Button("전량 매도", elem_classes="secondary-button")
        
        with gr.Row():
            sell_btn = gr.Button("매도하기", variant="primary", size="lg", elem_classes="action-button")
            cancel_sell_btn = gr.Button("취소", elem_classes="secondary-button")
        
        sell_result = gr.Textbox(label="결과", visible=False, interactive=False, elem_classes="result-message")
    
    containers["sell"] = sell_container
    
    # 거래내역 화면
    with gr.Group(visible=False) as transactions_container:
        gr.Markdown("## 주식 거래내역", elem_classes="header-text")
        
        with gr.Row():
            load_transaction_btn = gr.Button("거래내역 불러오기", variant="primary", elem_classes="action-button")
            transactions_filter = gr.Dropdown(
                ["전체", "매수", "매도", "배당"],
                label="필터",
                value="전체"
            )
            transactions_search = gr.Textbox(
                label="검색",
                placeholder="종목명 또는 종목코드 입력"
            )
            transactions_period = gr.Dropdown(
                ["전체 기간", "최근 1개월", "최근 3개월", "최근 6개월", "최근 1년"],
                label="기간",
                value="전체 기간"
            )
        
        transaction_table = gr.Dataframe(
            headers=["ID", "종목명", "거래유형", "수량", "가격", "거래일시", "수수료", "세금", "실현손익", "메모"],
            interactive=False,
            wrap=True,
            height=400,
            elem_classes="transaction-table"
        )
        
        with gr.Row():
            export_transactions_btn = gr.Button("거래내역 내보내기", elem_classes="secondary-button")
    
    containers["transactions"] = transactions_container
    
    # 배당금 화면
    with gr.Group(visible=False) as dividends_container:
        gr.Markdown("## 배당금 관리", elem_classes="header-text")
        
        with gr.Tabs() as dividend_tabs:
            with gr.Tab("배당금 내역"):
                with gr.Row():
                    load_dividends_btn = gr.Button("배당금 내역 불러오기", variant="primary", elem_classes="action-button")
                    dividends_period = gr.Dropdown(
                        ["전체 기간", "최근 1년", "올해", "작년"],
                        label="기간",
                        value="전체 기간"
                    )
                
                dividends_table = gr.Dataframe(
                    headers=["ID", "종목명", "배당일", "배당액", "통화", "세전금액", "세후금액"],
                    interactive=False,
                    wrap=True,
                    height=300,
                    elem_classes="dividends-table"
                )
                
                with gr.Row():
                    dividends_summary = gr.HTML(
                        """<div class="summary-card">배당금 요약 정보를 불러오는 중...</div>""",
                        elem_classes="summary-info"
                    )
            
            with gr.Tab("배당금 추가"):
                with gr.Row():
                    dividend_stock_dropdown = gr.Dropdown(
                        [],
                        label="종목 선택",
                        info="배당금을 받은 종목을 선택하세요",
                        interactive=True,
                        elem_classes="stock-dropdown"
                    )
                    
                    refresh_dividend_stocks_btn = gr.Button("종목 목록 새로고침", elem_classes="secondary-button")
                
                with gr.Row():
                    with gr.Column():
                        dividend_date = gr.Textbox(
                            label="배당일",
                            value=datetime.now().strftime("%Y-%m-%d"),
                            placeholder="YYYY-MM-DD"
                        )
                        dividend_amount = gr.Number(
                            label="배당액",
                            precision=2,
                            placeholder="0"
                        )
                    
                    with gr.Column():
                        dividend_currency = gr.Dropdown(
                            ["KRW", "USD", "JPY", "HKD", "CNY"],
                            label="통화",
                            value="KRW"
                        )
                        dividend_type = gr.Dropdown(
                            ["현금배당", "주식배당"],
                            label="배당 유형",
                            value="현금배당"
                        )
                
                with gr.Row():
                    with gr.Column():
                        dividend_pretax = gr.Number(
                            label="세전 금액",
                            precision=2,
                            placeholder="0"
                        )
                        dividend_posttax = gr.Number(
                            label="세후 금액",
                            precision=2,
                            placeholder="0"
                        )
                    
                    with gr.Column():
                        dividend_tax_rate = gr.Slider(
                            label="적용 세율 (%)",
                            minimum=0,
                            maximum=30,
                            value=15.4,
                            step=0.1
                        )
                        dividend_memo = gr.Textbox(
                            label="메모",
                            placeholder="배당 관련 메모를 입력하세요",
                            lines=2
                        )
                
                with gr.Row():
                    add_dividend_btn = gr.Button("배당금 추가", variant="primary", elem_classes="action-button")
                    calculate_dividend_tax_btn = gr.Button("세금 계산", elem_classes="secondary
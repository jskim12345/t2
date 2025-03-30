def update_all_portfolio_history():
    """
    모든 사용자의 포트폴리오 이력 업데이트
    """
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 오늘 날짜
        today = datetime.now().date()
        
        # 모든 사용자 조회
        cursor.execute("SELECT DISTINCT user_id FROM portfolio")
        user_ids = [row[0] for row in cursor.fetchall() if row[0] is not None]
        
        update_count = 0
        
        for user_id in user_ids:
            # 사용자 포트폴리오 요약 데이터 계산
            cursor.execute("""
                SELECT 
                    SUM(평가액) as total_value,
                    SUM(수량 * 평단가_원화) as total_invested,
                    SUM(손익금액) as total_gain_loss,
                    SUM(배당금) as total_dividend
                FROM portfolio 
                WHERE user_id = ?
            """, (user_id,))
            
            portfolio_summary = cursor.fetchone()
            
            if portfolio_summary and portfolio_summary[0]:
                total_value = portfolio_summary[0]
                total_invested = portfolio_summary[1]
                total_gain_loss = portfolio_summary[2]
                total_dividend = portfolio_summary[3] or 0
                
                # 총 수익률 계산
                total_return = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0
                
                # 현금 잔고 조회 (향후 구현 예정)
                cash_balance = 0
                
                # 실현 이익 조회 (거래내역에서 계산)
                cursor.execute("""
                    SELECT SUM(실현손익) as realized_profit
                    FROM transactions
                    WHERE user_id = ? AND type = '매도'
                """, (user_id,))
                
                realized_result = cursor.fetchone()
                realized_profit = realized_result[0] if realized_result and realized_result[0] else 0
                
                # 포트폴리오 이력 추가/업데이트
                # 같은 날짜의 이력이 있는지 확인
                cursor.execute(
                    "SELECT id FROM portfolio_history WHERE user_id = ? AND date = ?",
                    (user_id, today)
                )
                
                existing = cursor.fetchone()
                
                if existing:
                    # 기존 이력 업데이트
                    cursor.execute(
                        """
                        UPDATE portfolio_history
                        SET total_value = ?, total_invested = ?, total_gain_loss = ?, 
                            total_return_percent = ?, cash_balance = ?, realized_profit = ?,
                            unrealized_profit = ?
                        WHERE id = ?
                        """,
                        (total_value, total_invested, total_gain_loss, total_return, 
                         cash_balance, realized_profit, total_gain_loss, existing[0])
                    )
                else:
                    # 새 이력 추가
                    cursor.execute(
                        """
                        INSERT INTO portfolio_history (
                            user_id, date, total_value, total_invested, total_gain_loss, 
                            total_return_percent, cash_balance, realized_profit, unrealized_profit
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (user_id, today, total_value, total_invested, total_gain_loss, 
                         total_return, cash_balance, realized_profit, total_gain_loss)
                    )
                
                update_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"포트폴리오 이력 업데이트 완료: {update_count}명의 사용자")
        return update_count
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 이력 업데이트"})
        return 0

def get_portfolio_summary(user_id):
    """
    포트폴리오 요약 정보 (시각화용)
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict: 포트폴리오 요약 정보
    """
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 포트폴리오 총 가치 및 손익 계산
        cursor.execute("""
            SELECT 
                SUM(평가액) as total_value,
                SUM(수량 * 평단가_원화) as total_invested,
                SUM(손익금액) as total_gain_loss,
                SUM(배당금) as total_dividend
            FROM portfolio 
            WHERE user_id = ?
        """, (user_id,))
        
        summary = cursor.fetchone()
        total_value = summary[0] or 0
        total_invested = summary[1] or 0
        total_gain_loss = summary[2] or 0
        total_dividend = summary[3] or 0
        
        # 수익률 계산
        if total_invested > 0:
            total_return_percent = (total_gain_loss / total_invested * 100)
            dividend_yield = (total_dividend / total_invested * 100)
            total_return_with_dividend = ((total_gain_loss + total_dividend) / total_invested * 100)
        else:
            total_return_percent = 0
            dividend_yield = 0
            total_return_with_dividend = 0
        
        # 적금 총액 계산
        try:
            from services.savings_service import get_savings_summary
            savings_data = get_savings_summary(user_id)
            savings_total = savings_data.get('total_amount', 0)
            savings_list = savings_data.get('savings', [])
        except (ImportError, AttributeError):
            # 적금 모듈이 없거나 함수가 없는 경우
            savings_total = 0
            savings_list = []
        
        # 전체 자산 (주식 + 적금)
        total_assets = total_value + savings_total
        
        # 주식 비중
        stock_weight = (total_value / total_assets * 100) if total_assets > 0 else 0
        
        # 적금 비중
        savings_weight = (savings_total / total_assets * 100) if total_assets > 0 else 0
        
        # 국가별 분포
        cursor.execute("""
            SELECT 국가, SUM(평가액) as value
            FROM portfolio
            WHERE user_id = ?
            GROUP BY 국가
            ORDER BY value DESC
        """, (user_id,))
        
        country_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 계좌별 분포
        cursor.execute("""
            SELECT 계좌, SUM(평가액) as value
            FROM portfolio
            WHERE user_id = ?
            GROUP BY 계좌
            ORDER BY value DESC
        """, (user_id,))
        
        account_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 증권사별 분포
        cursor.execute("""
            SELECT 증권사, SUM(평가액) as value
            FROM portfolio
            WHERE user_id = ?
            GROUP BY 증권사
            ORDER BY value DESC
        """, (user_id,))
        
        broker_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 섹터별 분포
        cursor.execute("""
            SELECT COALESCE(섹터, '미분류') as sector, SUM(평가액) as value
            FROM portfolio
            WHERE user_id = ?
            GROUP BY COALESCE(섹터, '미분류')
            ORDER BY value DESC
        """, (user_id,))
        
        sector_distribution = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 상위 5개 종목
        cursor.execute("""
            SELECT 종목명, 평가액, 투자비중, 국가, 섹터
            FROM portfolio
            WHERE user_id = ?
            ORDER BY 평가액 DESC
            LIMIT 5
        """, (user_id,))
        
        top_stocks = [
            {
                "name": row[0], 
                "value": row[1], 
                "weight": row[2],
                "country": row[3],
                "sector": row[4] or "미분류"
            } 
            for row in cursor.fetchall()
        ]
        
        # 포트폴리오 종목 수
        cursor.execute("""
            SELECT COUNT(*) FROM portfolio WHERE user_id = ?
        """, (user_id,))
        
        stock_count = cursor.fetchone()[0] or 0
        
        # 포트폴리오 이력 (최근 30일)
        cursor.execute("""
            SELECT date, total_value, total_return_percent, realized_profit, unrealized_profit
            FROM portfolio_history
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 30
        """, (user_id,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                "date": row[0],
                "value": row[1],
                "return_percent": row[2],
                "realized_profit": row[3] or 0,
                "unrealized_profit": row[4] or 0
            })
        
        # 역순 정렬 (오래된 날짜부터)
        history.reverse()
        
        # 배당금 이력
        cursor.execute("""
            SELECT p.종목명, d.지급일, d.배당액
            FROM dividends d
            JOIN portfolio p ON d.portfolio_id = p.id
            WHERE d.user_id = ?
            ORDER BY d.지급일 DESC
            LIMIT 10
        """, (user_id,))
        
        dividends = [
            {
                "stock_name": row[0],
                "payment_date": row[1],
                "amount": row[2]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "summary": {
                "total_value": total_value,
                "total_invested": total_invested,
                "total_gain_loss": total_gain_loss,
                "total_return_percent": total_return_percent,
                "total_dividend": total_dividend,
                "dividend_yield": dividend_yield,
                "total_return_with_dividend": total_return_with_dividend,
                "savings_total": savings_total,
                "total_assets": total_assets,
                "stock_weight": stock_weight,
                "savings_weight": savings_weight,
                "stock_count": stock_count
            },
            "distributions": {
                "country": country_distribution,
                "account": account_distribution,
                "broker": broker_distribution,
                "sector": sector_distribution
            },
            "top_stocks": top_stocks,
            "history": history,
            "dividends": dividends,
            "savings": savings_list
        }
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 요약 정보 조회"})
        
        # 최소한의 기본 구조 반환
        return {
            "summary": {
                "total_value": 0,
                "total_invested": 0,
                "total_gain_loss": 0,
                "total_return_percent": 0,
                "total_dividend": 0,
                "dividend_yield": 0,
                "total_return_with_dividend": 0,
                "savings_total": 0,
                "total_assets": 0,
                "stock_weight": 0,
                "savings_weight": 0,
                "stock_count": 0
            },
            "distributions": {
                "country": {},
                "account": {},
                "broker": {},
                "sector": {}
            },
            "top_stocks": [],
            "history": [],
            "dividends": [],
            "savings": []
        }

def load_transactions(user_id, limit=100):
    """
    사용자의 거래내역 로드
    
    Args:
        user_id (int): 사용자 ID
        limit (int, optional): 최대 조회 개수
        
    Returns:
        pandas.DataFrame: 거래내역 (Data Frame)
    """
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        
        query = """
        SELECT t.id, p.종목명, t.type, t.quantity, t.price, t.transaction_date, 
               t.실현손익, t.거래메모, p.국가, p.계좌
        FROM transactions t
        LEFT JOIN portfolio p ON t.portfolio_id = p.id
        WHERE t.user_id = ?
        ORDER BY t.transaction_date DESC
        LIMIT ?
        """
        
        df = pd.read_sql_query(query, conn, params=(user_id, limit))
        
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
        
        # 종목명이 NULL인 경우 '매도완료 종목'으로 처리
        df['종목명'] = df['종목명'].fillna('매도완료 종목')
        
        # 컬럼명 변경
        df.columns = ["ID", "종목명", "거래유형", "수량", "가격", "거래일시", 
                      "실현손익", "메모", "국가", "계좌"]
        
        # 숫자 포맷팅
        df["수량"] = df["수량"].apply(lambda x: f"{float(x):,.2f}" if pd.notnull(x) else "")
        df["가격"] = df["가격"].apply(lambda x: f"{x:,.0f}원" if pd.notnull(x) else "")
        
        # 실현손익 포맷팅
        df["실현손익"] = df["실현손익"].apply(
            lambda x: f"{x:,.0f}원" if pd.notnull(x) and x != 0 else "-"
        )
        
        # 날짜 포맷팅
        df["거래일시"] = pd.to_datetime(df["거래일시"]).dt.strftime('%Y-%m-%d %H:%M')
        
        # 메모가 없는 경우 처리
        df["메모"] = df["메모"].fillna("-")
        
        return df
    except Exception as e:
        log_exception(logger, e, {"context": "거래내역 로드"})
        return pd.DataFrame()

def get_owned_stocks(user_id):
    """
    사용자가 보유한 종목 목록 조회
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        list: 보유 종목 목록
    """
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        query = """
        SELECT 종목코드, 종목명, 계좌, 수량, 현재가_원화, 국가, 증권사
        FROM portfolio
        WHERE user_id = ? AND 수량 > 0
        ORDER BY 평가액 DESC
        """
        
        cursor.execute(query, (user_id,))
        
        stocks = []
        for row in cursor.fetchall():
            stocks.append({
                "종목코드": row[0],
                "종목명": row[1],
                "계좌": row[2],
                "수량": row[3],
                "현재가_원화": row[4],
                "국가": row[5],
                "증권사": row[6]
            })
        
        conn.close()
        return stocks
    except Exception as e:
        log_exception(logger, e, {"context": "보유 종목 조회"})
        return []

def get_stock_details(ticker, account, user_id=None):
    """
    특정 종목의 상세 정보 조회
    
    Args:
        ticker (str): 종목코드
        account (str): 계좌
        user_id (int, optional): 사용자 ID (지정 시 해당 사용자의 종목만 조회)
        
    Returns:
        dict or None: 종목 상세 정보
    """
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        query = """
        SELECT *
        FROM portfolio
        WHERE 종목코드 = ? AND 계좌 = ?
        """
        
        params = [ticker, account]
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        cursor.execute(query, params)

        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # 결과를 딕셔너리로 변환
        column_names = [desc[0] for desc in cursor.description]
        result = dict(zip(column_names, row))
        
        # 거래내역 추가
        cursor.execute("""
            SELECT type, quantity, price, transaction_date, 거래메모
            FROM transactions
            WHERE portfolio_id = ?
            ORDER BY transaction_date DESC
            LIMIT 5
        """, (result['id'],))
        
        result['recent_transactions'] = [dict(zip(
            ['type', 'quantity', 'price', 'date', 'memo'],
            t
        )) for t in cursor.fetchall()]
        
        # 배당금 내역 추가
        cursor.execute("""
            SELECT 지급일, 배당액, 배당유형
            FROM dividends
            WHERE portfolio_id = ?
            ORDER BY 지급일 DESC
            LIMIT 5
        """, (result['id'],))
        
        result['dividends'] = [dict(zip(
            ['date', 'amount', 'type'],
            d
        )) for d in cursor.fetchall()]
        
        # 종목 시장 정보 추가
        if result['국가'] == '한국':
            stock_info = get_krx_stock_info(ticker)
        else:
            stock_info = get_international_stock_info(ticker, result['국가'])
        
        if stock_info:
            result['market_info'] = stock_info
        
        conn.close()
        return result
    except Exception as e:
        log_exception(logger, e, {"context": "종목 상세 정보 조회", "ticker": ticker})
        return None

def calculate_portfolio_risk(user_id):
    """
    포트폴리오 위험 지표 계산
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict: 위험 지표
    """
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 종목별 정보 조회
        cursor.execute("""
            SELECT 종목코드, 국가, 평가액, 베타, 투자비중
            FROM portfolio
            WHERE user_id = ? AND 수량 > 0
        """, (user_id,))
        
        stocks = [dict(zip(['ticker', 'country', 'value', 'beta', 'weight'], row)) for row in cursor.fetchall()]
        
        # 포트폴리오 총액
        total_value = sum(stock['value'] for stock in stocks) or 1  # 0으로 나눔 방지
        
        # 베타값 계산 (가중평균)
        portfolio_beta = 0
        beta_coverage = 0  # 베타 정보가 있는 종목의 비중
        
        for stock in stocks:
            beta = stock.get('beta')
            if beta:
                weight = stock['value'] / total_value
                portfolio_beta += beta * weight
                beta_coverage += weight
        
        # 가중치 조정 (베타 정보가 없는 종목 보정)
        if beta_coverage > 0:
            portfolio_beta = portfolio_beta / beta_coverage
        else:
            portfolio_beta = 1.0  # 기본값
        
        # 섹터별 비중 계산
        cursor.execute("""
            SELECT COALESCE(섹터, '미분류') as sector, SUM(평가액) as value
            FROM portfolio
            WHERE user_id = ? AND 수량 > 0
            GROUP BY COALESCE(섹터, '미분류')
        """, (user_id,))
        
        sectors = [dict(zip(['sector', 'value'], row)) for row in cursor.fetchall()]
        
        # 섹터 집중도 (허핀달-허쉬만 지수) 계산
        hhi = 0
        for sector in sectors:
            weight = sector['value'] / total_value
            hhi += (weight * 100) ** 2  # 비중을 %로 변환하여 제곱
        
        # 최대 손실 종목과 비중
        max_loss_stock = None
        max_loss_weight = 0
        
        cursor.execute("""
            SELECT 종목명, 투자비중, 손익수익
            FROM portfolio
            WHERE user_id = ? AND 수량 > 0
            ORDER BY 손익수익 ASC
            LIMIT 1
        """, (user_id,))
        
        max_loss_row = cursor.fetchone()
        if max_loss_row:
            max_loss_stock = max_loss_row[0]
            max_loss_weight = max_loss_row[1]
        
        # 국가별 비중 계산 (지역 다각화)
        cursor.execute("""
            SELECT 국가, SUM(평가액) as value
            FROM portfolio
            WHERE user_id = ? AND 수량 > 0
            GROUP BY 국가
        """, (user_id,))
        
        country_weights = {}
        for row in cursor.fetchall():
            country_weights[row[0]] = row[1] / total_value * 100
        
        # 상위 5개 종목 집중도
        cursor.execute("""
            SELECT SUM(평가액) as value
            FROM portfolio
            WHERE user_id = ? AND 수량 > 0
            ORDER BY 평가액 DESC
            LIMIT 5
        """, (user_id,))
        
        top5_value = cursor.fetchone()[0] or 0
        top5_concentration = (top5_value / total_value) * 100
        
        conn.close()
        
        # 위험 지표 요약
        risk_metrics = {
            "portfolio_beta": portfolio_beta,
            "sector_concentration": {
                "hhi": hhi,
                "interpretation": get_hhi_interpretation(hhi)
            },
            "top5_concentration": top5_concentration,
            "max_loss_stock": {
                "name": max_loss_stock,
                "weight": max_loss_weight
            },
            "country_weights": country_weights,
            "risk_level": calculate_risk_level(portfolio_beta, hhi, top5_concentration)
        }
        
        return risk_metrics
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 위험 계산"})
        return {
            "portfolio_beta": 1.0,
            "sector_concentration": {"hhi": 0, "interpretation": "데이터 없음"},
            "top5_concentration": 0,
            "max_loss_stock": {"name": None, "weight": 0},
            "country_weights": {},
            "risk_level": "알 수 없음"
        }

def get_hhi_interpretation(hhi):
    """HHI 지수 해석"""
    if hhi < 1500:
        return "낮은 집중도"
    elif hhi < 2500:
        return "중간 집중도"
    else:
        return "높은 집중도"

def calculate_risk_level(beta, hhi, top5_concentration):
    """종합 위험 수준 계산"""
    risk_score = 0
    
    # 베타 기반 점수
    if beta < 0.8:
        risk_score += 1
    elif beta < 1.0:
        risk_score += 2
    elif beta < 1.2:
        risk_score += 3
    else:
        risk_score += 4
    
    # 섹터 집중도 기반 점수
    if hhi < 1500:
        risk_score += 1
    elif hhi < 2500:
        risk_score += 2
    else:
        risk_score += 3
    
    # 상위 5개 종목 집중도 기반 점수
    if top5_concentration < 30:
        risk_score += 1
    elif top5_concentration < 50:
        risk_score += 2
    elif top5_concentration < 70:
        risk_score += 3
    else:
        risk_score += 4
    
    # 종합 점수 해석
    avg_score = risk_score / 3
    
    if avg_score < 1.5:
        return "매우 낮음"
    elif avg_score < 2.2:
        return "낮음"
    elif avg_score < 3:
        return "중간"
    elif avg_score < 3.5:
        return "높음"
    else:
        return "매우 높음"

def calculate_optimal_portfolio(user_id):
    """
    포트폴리오 최적화 추천
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict: 최적화 추천 정보
    """
    try:
        # 현재 포트폴리오 정보 조회
        current_portfolio = load_portfolio_details(user_id)
        
        if not current_portfolio or not current_portfolio.get('items'):
            return {
                "status": "error",
                "message": "포트폴리오 정보가 없습니다."
            }
        
        # 섹터 불균형 감지
        sector_weights = current_portfolio.get('sectors', {})
        
        sector_imbalances = []
        if sector_weights:
            # 상위 섹터 집중도 확인
            top_sector = max(sector_weights.items(), key=lambda x: x[1])
            if top_sector[1] > 0.4:  # 한 섹터에 40% 이상 집중된 경우
                sector_imbalances.append({
                    "sector": top_sector[0],
                    "weight": top_sector[1],
                    "recommendation": "비중 축소 고려"
                })
            
            # 섹터별 권장 비중 (예시)
            recommended_weights = {
                'IT': 0.20,
                '금융': 0.15,
                '헬스케어': 0.15,
                '소비재': 0.12,
                '산업재': 0.10,
                '통신': 0.08,
                '에너지': 0.08,
                '유틸리티': 0.05,
                '원자재': 0.05,
                '부동산': 0.02
            }
            
            # 권장 비중과 실제 비중 비교
            for sector, rec_weight in recommended_weights.items():
                actual_weight = 0
                for s, w in sector_weights.items():
                    if sector in s:  # 부분 매칭 (예: 'IT서비스'는 'IT'로 매칭)
                        actual_weight += w
                
                # 큰 차이가 있는 경우 추천
                if actual_weight < rec_weight * 0.5:  # 권장 비중의 절반 미만
                    sector_imbalances.append({
                        "sector": sector,
                        "current_weight": actual_weight,
                        "recommended_weight": rec_weight,
                        "recommendation": "비중 확대 고려"
                    })
        
        # 국가별 불균형 감지
        country_weights = current_portfolio.get('countries', {})
        country_imbalances = []
        
        if country_weights:
            # 국내/해외 비중 확인
            domestic_weight = country_weights.get('한국', 0)
            foreign_weight = sum(w for c, w in country_weights.items() if c != '한국')
            
            # 국내 또는 해외에 과도하게 집중된 경우
            if domestic_weight > 0.8:
                country_imbalances.append({
                    "issue": "국내 종목 편중",
                    "recommendation": "해외 종목 추가 고려"
                })
            elif foreign_weight > 0.8:
                country_imbalances.append({
                    "issue": "해외 종목 편중",
                    "recommendation": "국내 종목 추가 고려"
                })
        
        # 종목별 집중도 확인
        items = current_portfolio.get('items', [])
        stock_concentrations = []
        
        if items:
            # 총 평가액
            total_value = sum(item['평가액'] for item in items)
            
            # 한 종목에 20% 이상 집중된 경우
            for item in items:
                weight = item['평가액'] / total_value if total_value > 0 else 0
                if weight > 0.2:
                    stock_concentrations.append({
                        "ticker": item['종목코드'],
                        "name": item['종목명'],
                        "weight": weight,
                        "recommendation": "위험 분산을 위해 비중 축소 고려"
                    })
        
        # 수익률 낮은 종목 확인
        low_performers = []
        
        if items:
            for item in items:
                profit_percent = item.get('손익수익', 0)
                if isinstance(profit_percent, str):
                    # 문자열에서 숫자 추출 (예: "- 5.2%" -> -5.2)
                    profit_percent = float(re.sub(r'[^\d.-]', '', profit_percent))
                
                if profit_percent < -15:  # 15% 이상 손실인 종목
                    low_performers.append({
                        "ticker": item['종목코드'],
                        "name": item['종목명'],
                        "loss_percent": profit_percent,
                        "recommendation": "손절 또는 추가매수 검토"
                    })
        
        # 현금 비중 확인
        cash_balance = 0
        try:
            # 포트폴리오 이력에서 현금 잔고 조회
            conn = get_db_connection('portfolio')
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cash_balance FROM portfolio_history 
                WHERE user_id = ? ORDER BY date DESC LIMIT 1
            """, (user_id,))
            
            cash_result = cursor.fetchone()
            if cash_result:
                cash_balance = cash_result[0] or 0
            
            conn.close()
        except Exception as e:
            log_exception(logger, e, {"context": "현금 잔고 조회"})
        
        cash_recommendation = None
        cash_total = cash_balance + sum(item['평가액'] for item in items)
        cash_weight = cash_balance / cash_total if cash_total > 0 else 0
        
        if cash_weight < 0.05:
            cash_recommendation = {
                "issue": "현금 비중 부족",
                "current_weight": cash_weight,
                "recommendation": "긴급 자금 및 추가 투자를 위한 현금 확보 고려"
            }
        elif cash_weight > 0.3:
            cash_recommendation = {
                "issue": "현금 비중 과다",
                "current_weight": cash_weight,
                "recommendation": "수익률 향상을 위한 투자 확대 고려"
            }
        
        # 최종 추천 결과
        return {
            "status": "success",
            "sector_imbalances": sector_imbalances,
            "country_imbalances": country_imbalances,
            "stock_concentrations": stock_concentrations,
            "low_performers": low_performers,
            "cash_recommendation": cash_recommendation
        }
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 최적화 추천"})
        return {
            "status": "error",
            "message": f"포트폴리오 최적화 추천 중 오류가 발생했습니다: {str(e)}"
        }

def export_portfolio_to_csv(user_id, include_transactions=False):
    """
    포트폴리오 데이터를 CSV 파일로 내보내기
    
    Args:
        user_id (int): 사용자 ID
        include_transactions (bool, optional): 거래내역 포함 여부
        
    Returns:
        str: CSV 파일 경로 또는 오류 메시지
    """
    try:
        import os
        import csv
        from datetime import datetime
        
        # 데이터베이스에서 포트폴리오 정보 조회
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM portfolio WHERE user_id = ? ORDER BY 투자비중 DESC
        """, (user_id,))
        
        portfolio_data = [dict(row) for row in cursor.fetchall()]
        
        if not portfolio_data:
            return "내보낼 포트폴리오 데이터가 없습니다."
        
        # 거래내역 조회
        transactions_data = []
        if include_transactions:
            cursor.execute("""
                SELECT t.*, p.종목명 
                FROM transactions t
                LEFT JOIN portfolio p ON t.portfolio_id = p.id
                WHERE t.user_id = ?
                ORDER BY t.transaction_date DESC
            """, (user_id,))
            
            transactions_data = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # 내보내기 디렉토리 생성
        export_dir = os.path.join('data', 'exports')
        os.makedirs(export_dir, exist_ok=True)
        
        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        portfolio_file = os.path.join(export_dir, f"portfolio_{user_id}_{timestamp}.csv")
        
        # 포트폴리오 데이터 CSV 저장
        with open(portfolio_file, 'w', newline='', encoding='utf-8') as f:
            if portfolio_data:
                fieldnames = list(portfolio_data[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(portfolio_data)
        
        # 거래내역 저장
        if include_transactions and transactions_data:
            trans_file = os.path.join(export_dir, f"transactions_{user_id}_{timestamp}.csv")
            
            with open(trans_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = list(transactions_data[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(transactions_data)
            
            return f"포트폴리오와 거래내역을 내보냈습니다.\n포트폴리오: {portfolio_file}\n거래내역: {trans_file}"
        
        return f"포트폴리오를 내보냈습니다: {portfolio_file}"
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 CSV 내보내기"})
        return f"데이터 내보내기 중 오류가 발생했습니다: {str(e)}"

def import_portfolio_from_csv(user_id, file_path):
    """
    CSV 파일에서 포트폴리오 데이터 가져오기
    
    Args:
        user_id (int): 사용자 ID
        file_path (str): CSV 파일 경로
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    try:
        import csv
        import os
        
        if not os.path.exists(file_path):
            return False, f"파일을 찾을 수 없습니다: {file_path}"
        
        # CSV 파일 읽기
        stocks = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 필수 필드 확인
                required_fields = ['종목코드', '종목명', '수량', '평단가_원화', '국가', '증권사', '계좌']
                if not all(field in row for field in required_fields):
                    continue
                
                # 문자열 데이터 정리 (쉼표, 통화기호 등 제거)
                for key in ['수량', '평단가_원화']:
                    if key in row:
                        row[key] = float(re.sub(r'[^\d.-]', '', str(row[key])))
                
                stocks.append(row)
        
        if not stocks:
            return False, "가져올 포트폴리오 데이터가 없거나 형식이 올바르지 않습니다."
        
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 기존 포트폴리오 유지 또는 삭제 여부 확인 (기본: 유지)
        
        # 데이터 추가
        add_count = 0
        update_count = 0
        
        for stock in stocks:
            # 기존 종목 확인
            cursor.execute(
                "SELECT id FROM portfolio WHERE 종목코드 = ? AND 계좌 = ? AND user_id = ?", 
                (stock['종목코드'], stock['계좌'], user_id)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 기존 종목 업데이트
                update_query = """
                    UPDATE portfolio SET
                    수량 = ?, 평단가_원화 = ?, 국가 = ?, 증권사 = ?, 종목명 = ?, last_update = ?
                    WHERE id = ?
                """
                cursor.execute(
                    update_query,
                    (stock['수량'], stock['평단가_원화'], stock['국가'], stock['증권사'], stock['종목명'], datetime.now(), existing[0])
                )
                update_count += 1
            else:
                # 새 종목 추가
                insert_query = """
                    INSERT INTO portfolio (
                        user_id, 종목코드, 종목명, 수량, 평단가_원화, 국가, 증권사, 계좌, last_update
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(
                    insert_query,
                    (user_id, stock['종목코드'], stock['종목명'], stock['수량'], stock['평단가_원화'], 
                     stock['국가'], stock['증권사'], stock['계좌'], datetime.now())
                )
                add_count += 1
        
        conn.commit()
        conn.close()
        
        # 실시간 가격 업데이트
        update_all_prices(user_id)
        
        return True, f"포트폴리오 가져오기 완료: {add_count}개 추가, {update_count}개 업데이트"
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 CSV 가져오기"})
        return False, f"데이터 가져오기 중 오류가 발생했습니다: {str(e)}"

def get_portfolio_performance_metrics(user_id, period='1y'):
    """
    포트폴리오 성과 지표 계산
    
    Args:
        user_id (int): 사용자 ID
        period (str): 기간 ('1m', '3m', '6m', '1y', 'all')
        
    Returns:
        dict: 성과 지표
    """
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 기간에 따른 날짜 조건 설정
        today = datetime.now().date()
        
        if period == '1m':
            start_date = (datetime.now() - timedelta(days=30)).date()
        elif period == '3m':
            start_date = (datetime.now() - timedelta(days=90)).date()
        elif period == '6m':
            start_date = (datetime.now() - timedelta(days=180)).date()
        elif period == '1y':
            start_date = (datetime.now() - timedelta(days=365)).date()
        else:  # 'all'
            start_date = datetime(2000, 1, 1).date()  # 충분히 오래된 날짜
        
        # 포트폴리오 이력 조회
        cursor.execute("""
            SELECT date, total_value, total_invested, total_return_percent
            FROM portfolio_history
            WHERE user_id = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """, (user_id, start_date, today))
        
        history = [dict(zip(['date', 'value', 'invested', 'return_percent'], row)) for row in cursor.fetchall()]
        
        # 성과 지표 계산
        metrics = {
            "period": period,
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": today.strftime('%Y-%m-%d'),
            "total_return": 0,
            "annualized_return": 0,
            "volatility": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "best_day": {"date": None, "return": 0},
            "worst_day": {"date": None, "return": 0}
        }
        
        if len(history) < 2:
            return metrics  # 충분한 데이터가 없음
        
        # 총 수익률 (시작과 끝 비교)
        start_value = history[0]['value']
        end_value = history[-1]['value']
        
        if start_value > 0:
            total_return = (end_value - start_value) / start_value * 100
            metrics["total_return"] = total_return
        
        # 연환산 수익률
        days = (datetime.strptime(metrics["end_date"], '%Y-%m-%d') - 
                datetime.strptime(metrics["start_date"], '%Y-%m-%d')).days
        
        if days > 0 and start_value > 0:
            annualized_return = ((1 + total_return / 100) ** (365 / days) - 1) * 100
            metrics["annualized_return"] = annualized_return
        
        # 일일 수익률 계산 (변동성, 최대 손실 등 계산용)
        daily_returns = []
        prev_value = None
        
        for idx, day in enumerate(history):
            if idx > 0 and prev_value:
                daily_return = (day['value'] - prev_value) / prev_value * 100
                daily_returns.append(daily_return)
                
                # 최고/최저 일일 수익률 갱신
                if daily_return > metrics["best_day"]["return"]:
                    metrics["best_day"] = {"date": day['date'], "return": daily_return}
                    
                if daily_return < metrics["worst_day"]["return"]:
                    metrics["worst_day"] = {"date": day['date'], "return": daily_return}
            
            prev_value = day['value']
        
        # 변동성 (일일 수익률의 표준편차)
        if daily_returns:
            volatility = np.std(daily_returns)
            metrics["volatility"] = volatility
            
            # 샤프 비율 (무위험 수익률 가정: 3%)
            risk_free_rate = 3.0  # 연간 무위험 수익률 (%)
            daily_risk_free = risk_free_rate / 365  # 일일 무위험 수익률
            
            if volatility > 0:
                avg_daily_return = np.mean(daily_returns)
                sharpe_ratio = (avg_daily_return - daily_risk_free) / volatility
                metrics["sharpe_ratio"] = sharpe_ratio * np.sqrt(252)  # 연환산
        
        # 최대 손실(Drawdown) 계산
        cumulative_returns = []
        peak = -float('inf')
        drawdowns = []
        
        for value in [h['value'] for h in history]:
            if value > peak:
                peak = value
            
            drawdown = (value - peak) / peak * 100 if peak > 0 else 0
            drawdowns.append(drawdown)
        
        if drawdowns:
            metrics["max_drawdown"] = min(drawdowns)
        
        conn.close()
        return metrics
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 성과 지표 계산"})
        return {
            "period": period,
            "start_date": start_date.strftime('%Y-%m-%d') if 'start_date' in locals() else "",
            "end_date": today.strftime('%Y-%m-%d') if 'today' in locals() else "",
            "total_return": 0,
            "annualized_return": 0,
            "volatility": 0,
            "sharpe_ratio": 0,
            "max_drawdown": 0,
            "best_day": {"date": None, "return": 0},
            "worst_day": {"date": None, "return": 0}
        }"""
포트폴리오 관련 서비스 - 고급 분석 및 성과 측정 기능 추가
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import re

# 로깅 설정
from utils.logging import get_logger, log_exception
logger = get_logger(__name__)

# 필요한 함수 import
try:
    from models.database import get_db_connection
except ImportError:
    logger.error("models.database 모듈을 불러올 수 없습니다.")

try:
    from services.market_service import (
        get_krx_stock_price,
        get_international_stock_price,
        get_exchange_rate,
        get_krx_stock_info,
        get_international_stock_info,
        get_dividend_info,
        get_stock_financial_data
    )
except ImportError:
    logger.error("market_service 모듈을 불러올 수 없습니다.")
    # 더미 함수 정의
    def get_krx_stock_price(ticker): return None
    def get_international_stock_price(ticker, country=None): return None
    def get_exchange_rate(from_currency, to_currency): return None
    def get_krx_stock_info(ticker): return None
    def get_international_stock_info(ticker, country=None): return None
    def get_dividend_info(ticker, market=None): return None
    def get_stock_financial_data(ticker, market=None): return None

def load_portfolio(user_id):
    """
    사용자의 포트폴리오 데이터 로드
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        pandas.DataFrame: 포트폴리오 데이터 (Data Frame)
    """
    if user_id is None:
        return pd.DataFrame()  # 로그인하지 않은 경우 빈 데이터프레임 반환
    
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        
        # 포트폴리오 데이터 조회
        query = """
        SELECT 
            p.*,
            SUM(CASE WHEN d.배당액 IS NOT NULL THEN d.배당액 ELSE 0 END) AS 총배당금
        FROM 
            portfolio p
        LEFT JOIN 
            dividends d ON p.id = d.portfolio_id
        WHERE 
            p.user_id = ? 
        GROUP BY 
            p.id
        ORDER BY 
            p.투자비중 DESC
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
        
        conn.close()
        
        # 빈 데이터프레임 처리
        if df.empty:
            return pd.DataFrame()
        
        # UI 표시용 컬럼명 변경 및 선택
        try:
            # 컬럼 선택
            columns_to_display = [
                '증권사', '계좌', '국가', '종목코드', '종목명', '수량', 
                '평단가_원화', '평단가_달러', '현재가_원화', '현재가_달러',
                '평가액', '투자비중', '손익금액', '손익수익', '총수익률', '배당금', '섹터'
            ]
            
            # 존재하는 컬럼만 선택
            available_columns = [col for col in columns_to_display if col in df.columns]
            df = df[available_columns]
            
            # 컬럼명 매핑
            column_mapping = {
                '증권사': "증권사", 
                '계좌': "계좌", 
                '국가': "국가", 
                '종목코드': "종목코드", 
                '종목명': "종목명", 
                '수량': "수량", 
                '평단가_원화': "평단가(원화)", 
                '평단가_달러': "평단가(달러)", 
                '현재가_원화': "현재가(원화)", 
                '현재가_달러': "현재가(달러)",
                '평가액': "평가액[원화]", 
                '투자비중': "투자비중", 
                '손익금액': "손익금액[원화]", 
                '손익수익': "손익수익[원화]", 
                '총수익률': "총수익률[원가+배당]",
                '배당금': "누적배당금",
                '섹터': "섹터",
                '총배당금': "총배당금"
            }
            
            # 사용 가능한 키와 값만으로 매핑 적용
            available_mapping = {k: v for k, v in column_mapping.items() if k in available_columns}
            df.rename(columns=available_mapping, inplace=True)
            
            # 숫자 포맷팅
            numeric_columns = [
                "평단가(원화)", "평단가(달러)", "현재가(원화)", "현재가(달러)",
                "평가액[원화]", "손익금액[원화]", "누적배당금"
            ]
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
            
            percentage_columns = ["투자비중", "손익수익[원화]", "총수익률[원가+배당]"]
            
            for col in percentage_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        except Exception as e:
            log_exception(logger, e, {"context": "포트폴리오 데이터 변환"})
            return pd.DataFrame()
        
        return df
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 로드"})
        return pd.DataFrame()

def load_portfolio_details(user_id):
    """
    사용자의 포트폴리오 상세 데이터 로드 (분석용)
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict: 포트폴리오 상세 데이터
    """
    if user_id is None:
        return {}  # 로그인하지 않은 경우 빈 딕셔너리 반환
    
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 포트폴리오 데이터 조회
        cursor.execute("""
            SELECT * FROM portfolio 
            WHERE user_id = ? 
            ORDER BY 투자비중 DESC
        """, (user_id,))
        
        portfolio_items = [dict(row) for row in cursor.fetchall()]
        
        # 각 종목의 배당금 정보 조회
        for item in portfolio_items:
            cursor.execute("""
                SELECT SUM(배당액) as total_dividend 
                FROM dividends 
                WHERE portfolio_id = ?
            """, (item['id'],))
            
            dividend_result = cursor.fetchone()
            if dividend_result and dividend_result['total_dividend']:
                item['total_dividend'] = dividend_result['total_dividend']
            else:
                item['total_dividend'] = 0
            
            # 거래 내역 조회
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE portfolio_id = ? 
                ORDER BY transaction_date DESC
            """, (item['id'],))
            
            item['transactions'] = [dict(row) for row in cursor.fetchall()]
        
        # 포트폴리오 요약 정보 계산
        summary = calculate_portfolio_summary(portfolio_items)
        
        # 섹터별, 국가별, 계좌별 분류
        sectors = {}
        countries = {}
        accounts = {}
        brokers = {}
        
        for item in portfolio_items:
            # 섹터 분류
            sector = item.get('섹터', '미분류')
            if sector in sectors:
                sectors[sector] += item['평가액']
            else:
                sectors[sector] = item['평가액']
            
            # 국가 분류
            country = item.get('국가', '미분류')
            if country in countries:
                countries[country] += item['평가액']
            else:
                countries[country] = item['평가액']
            
            # 계좌 분류
            account = item.get('계좌', '미분류')
            if account in accounts:
                accounts[account] += item['평가액']
            else:
                accounts[account] = item['평가액']
            
            # 증권사 분류
            broker = item.get('증권사', '미분류')
            if broker in brokers:
                brokers[broker] += item['평가액']
            else:
                brokers[broker] = item['평가액']
        
        # 포트폴리오 이력 데이터 조회
        cursor.execute("""
            SELECT * FROM portfolio_history 
            WHERE user_id = ? 
            ORDER BY date ASC
        """, (user_id,))
        
        history = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        # 최종 결과 반환
        return {
            'items': portfolio_items,
            'summary': summary,
            'sectors': sectors,
            'countries': countries,
            'accounts': accounts,
            'brokers': brokers,
            'history': history
        }
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 상세 데이터 로드"})
        return {}

def calculate_portfolio_summary(portfolio_items):
    """
    포트폴리오 요약 정보 계산
    
    Args:
        portfolio_items (list): 포트폴리오 항목 목록
        
    Returns:
        dict: 포트폴리오 요약 정보
    """
    try:
        total_value = sum(item['평가액'] for item in portfolio_items)
        total_cost = sum(item['수량'] * item['평단가_원화'] for item in portfolio_items)
        total_gain_loss = sum(item['손익금액'] for item in portfolio_items)
        total_dividend = sum(item.get('total_dividend', 0) for item in portfolio_items)
        
        # 투자 수익률 계산
        investment_return = (total_gain_loss / total_cost * 100) if total_cost > 0 else 0
        
        # 배당 수익률 계산
        dividend_yield = (total_dividend / total_cost * 100) if total_cost > 0 else 0
        
        # 총 수익률 (투자 + 배당)
        total_return = ((total_gain_loss + total_dividend) / total_cost * 100) if total_cost > 0 else 0
        
        # 섹터별 비중 계산
        sector_weights = {}
        if total_value > 0:
            for item in portfolio_items:
                sector = item.get('섹터', '미분류')
                weight = (item['평가액'] / total_value) * 100
                
                if sector in sector_weights:
                    sector_weights[sector] += weight
                else:
                    sector_weights[sector] = weight
        
        # 국가별 비중 계산
        country_weights = {}
        if total_value > 0:
            for item in portfolio_items:
                country = item.get('국가', '미분류')
                weight = (item['평가액'] / total_value) * 100
                
                if country in country_weights:
                    country_weights[country] += weight
                else:
                    country_weights[country] = weight
        
        # 상위 종목 비중 (집중도)
        concentration = 0
        if total_value > 0 and portfolio_items:
            # 상위 5개 종목 또는 전체 종목의 비중
            top_n = min(5, len(portfolio_items))
            concentration = sum(item['평가액'] for item in portfolio_items[:top_n]) / total_value * 100
        
        return {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_gain_loss': total_gain_loss,
            'total_dividend': total_dividend,
            'investment_return': investment_return,
            'dividend_yield': dividend_yield,
            'total_return': total_return,
            'sector_weights': sector_weights,
            'country_weights': country_weights,
            'concentration': concentration,
            'count': len(portfolio_items)
        }
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 요약 계산"})
        return {
            'total_value': 0,
            'total_cost': 0,
            'total_gain_loss': 0,
            'total_dividend': 0,
            'investment_return': 0,
            'dividend_yield': 0,
            'total_return': 0,
            'sector_weights': {},
            'country_weights': {},
            'concentration': 0,
            'count': 0
        }

def buy_stock(user_id, broker, account, country, ticker, stock_name, quantity, price, memo=None, date=None):
    """
    주식 매수
    
    Args:
        user_id (int): 사용자 ID
        broker (str): 증권사
        account (str): 계좌
        country (str): 국가
        ticker (str): 종목코드
        stock_name (str): 종목명
        quantity (float): 수량
        price (float): 매수가
        memo (str, optional): 매수 메모
        date (str, optional): 매수 날짜 (없으면 현재 날짜)
        
    Returns:
        pandas.DataFrame: 업데이트된 포트폴리오 (Data Frame)
    """
    try:
        # 수량과 가격 변환
        quantity = float(quantity)
        price = float(price)
        
        # 날짜 처리
        current_time = date if date else datetime.now()
        if isinstance(current_time, str):
            try:
                current_time = datetime.strptime(current_time, '%Y-%m-%d')
            except ValueError:
                current_time = datetime.now()
        
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 해당 종목이 이미 있는지 확인
        cursor.execute(
            "SELECT id, 수량, 평단가_원화 FROM portfolio WHERE 종목코드 = ? AND 계좌 = ? AND user_id = ?", 
            (ticker, account, user_id)
        )
        existing = cursor.fetchone()
        
        if existing:
            # 기존 종목 업데이트 (수량 증가, 평단가 재계산)
            stock_id, existing_quantity, existing_avg_price = existing[0], existing[1], existing[2]
            
            # 새로운 평단가 계산
            new_quantity = existing_quantity + quantity
            new_avg_price = ((existing_avg_price * existing_quantity) + (price * quantity)) / new_quantity
            
            cursor.execute(
                """
                UPDATE portfolio 
                SET 수량 = ?, 평단가_원화 = ?, last_update = ?
                WHERE id = ?
                """, 
                (new_quantity, new_avg_price, current_time, stock_id)
            )
            
            # 거래내역 추가
            cursor.execute(
                """
                INSERT INTO transactions (portfolio_id, user_id, type, quantity, price, 거래메모, transaction_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (stock_id, user_id, '매수', quantity, price, memo, current_time)
            )
            
            logger.info(f"종목 매수 (추가): {stock_name} ({ticker}), 수량: {quantity}, 사용자: {user_id}")
        else:
            # 평단가 달러 변환 (해외 주식)
            avg_price_usd = None
            if country != '한국':
                exchange_rate = get_exchange_rate('USD', 'KRW')
                avg_price_usd = price / exchange_rate if exchange_rate else None
            
            # 종목 정보 조회
            sector = None
            industry = None
            
            if country == '한국':
                stock_info = get_krx_stock_info(ticker)
                if stock_info:
                    sector = stock_info.get('sector')
            else:
                stock_info = get_international_stock_info(ticker, country)
                if stock_info:
                    sector = stock_info.get('sector')
                    industry = stock_info.get('industry')
            
            # 매수 날짜 처리
            purchase_date = None
            if date:
                if isinstance(date, str):
                    try:
                        purchase_date = datetime.strptime(date, '%Y-%m-%d').date()
                    except ValueError:
                        purchase_date = datetime.now().date()
                elif isinstance(date, datetime):
                    purchase_date = date.date()
            else:
                purchase_date = datetime.now().date()
            
            # 베타값 처리
            beta = None
            if stock_info:
                beta = stock_info.get('beta', None)
            
            # 새 종목 추가
            cursor.execute(
                """
                INSERT INTO portfolio (
                    user_id, 증권사, 계좌, 국가, 종목코드, 종목명, 수량, 평단가_원화, 평단가_달러,
                    현재가_원화, 현재가_달러, 평가액, 투자비중, 손익금액, 손익수익, 총수익률, 
                    배당금, 섹터, 산업군, 베타, 매수날짜, 메모, last_update
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, broker, account, country, ticker, stock_name, quantity, price, avg_price_usd, 
                 sector, industry, beta, purchase_date, memo, current_time)
            )
            
            stock_id = cursor.lastrowid
            
            # 거래내역 추가
            cursor.execute(
                """
                INSERT INTO transactions (portfolio_id, user_id, type, quantity, price, 거래메모, transaction_date) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (stock_id, user_id, '매수', quantity, price, memo, current_time)
            )
            
            logger.info(f"종목 매수 (신규): {stock_name} ({ticker}), 수량: {quantity}, 사용자: {user_id}")
        
        conn.commit()
        conn.close()
        
        # 실시간 가격 업데이트
        update_all_prices(user_id)
        
        # 업데이트된 포트폴리오 반환
        return load_portfolio(user_id)
    except Exception as e:
        log_exception(logger, e, {"context": "매수 처리", "ticker": ticker, "quantity": quantity})
        return load_portfolio(user_id)

def sell_stock(user_id, ticker, account, quantity, price, memo=None, date=None):
    """
    주식 매도
    
    Args:
        user_id (int): 사용자 ID
        ticker (str): 종목코드
        account (str): 계좌
        quantity (float): 수량
        price (float): 매도가
        memo (str, optional): 매도 메모
        date (str, optional): 매도 날짜 (없으면 현재 날짜)
        
    Returns:
        tuple: (결과 메시지, 업데이트된 포트폴리오)
    """
    try:
        # 수량과 가격 변환
        quantity = float(quantity)
        price = float(price)
        
        # 날짜 처리
        current_time = date if date else datetime.now()
        if isinstance(current_time, str):
            try:
                current_time = datetime.strptime(current_time, '%Y-%m-%d')
            except ValueError:
                current_time = datetime.now()
        
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 해당 종목 확인
        cursor.execute(
            "SELECT id, 수량, 평단가_원화, 종목명 FROM portfolio WHERE 종목코드 = ? AND 계좌 = ? AND user_id = ?", 
            (ticker, account, user_id)
        )
        existing = cursor.fetchone()
        
        if not existing:
            conn.close()
            return "종목을 찾을 수 없습니다.", load_portfolio(user_id)
        
        stock_id, existing_quantity, avg_price, stock_name = existing
        
        if quantity > existing_quantity:
            conn.close()
            return "보유 수량보다 많은 수량을 매도할 수 없습니다.", load_portfolio(user_id)
        
        # 실현 손익 계산
        realized_profit = (price - avg_price) * quantity
        
        # 거래내역 추가
        cursor.execute(
            """
            INSERT INTO transactions (portfolio_id, user_id, type, quantity, price, 거래메모, 실현손익, transaction_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (stock_id, user_id, '매도', quantity, price, memo, realized_profit, current_time)
        )
        
        # 수량 업데이트
        new_quantity = existing_quantity - quantity
        
        if new_quantity == 0:
            # 모든 주식 매도시 종목 삭제
            cursor.execute("DELETE FROM portfolio WHERE id = ?", (stock_id,))
        else:
            # 수량만 업데이트
            cursor.execute(
                """
                UPDATE portfolio 
                SET 수량 = ?, last_update = ?
                WHERE id = ?
                """, 
                (new_quantity, current_time, stock_id)
            )
        
        conn.commit()
        conn.close()
        
        # 실시간 가격 업데이트
        update_all_prices(user_id)
        
        logger.info(f"종목 매도: {stock_name} ({ticker}), 수량: {quantity}, 사용자: {user_id}")
        return "매도 완료", load_portfolio(user_id)
    except Exception as e:
        log_exception(logger, e, {"context": "매도 처리", "ticker": ticker, "quantity": quantity})
        return f"매도 처리 중 오류가 발생했습니다: {e}", load_portfolio(user_id)

def add_dividend(user_id, ticker, account, amount, payment_date, memo=None):
    """
    배당금 기록 추가
    
    Args:
        user_id (int): 사용자 ID
        ticker (str): 종목코드
        account (str): 계좌
        amount (float): 배당금액
        payment_date (str): 지급일
        memo (str, optional): 메모
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    try:
        # 금액 변환
        amount = float(amount)
        
        # 날짜 변환
        try:
            if isinstance(payment_date, str):
                payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
        except ValueError:
            payment_date = datetime.now().date()
        
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 해당 종목 확인
        cursor.execute(
            "SELECT id, 종목명, 배당금 FROM portfolio WHERE 종목코드 = ? AND 계좌 = ? AND user_id = ?", 
            (ticker, account, user_id)
        )
        existing = cursor.fetchone()
        
        if not existing:
            conn.close()
            return False, "종목을 찾을 수 없습니다."
        
        stock_id, stock_name, current_dividend = existing
        
        # 누적 배당금 업데이트
        new_dividend = (current_dividend or 0) + amount
        
        cursor.execute(
            """
            UPDATE portfolio 
            SET 배당금 = ?, 최근배당일 = ?, last_update = ?
            WHERE id = ?
            """, 
            (new_dividend, payment_date, datetime.now(), stock_id)
        )
        
        # 배당금 이력 추가
        cursor.execute(
            """
            INSERT INTO dividends (portfolio_id, user_id, 지급일, 배당액, 배당유형, 통화) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (stock_id, user_id, payment_date, amount, '현금배당', 'KRW')
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"배당금 추가: {stock_name} ({ticker}), 금액: {amount}, 사용자: {user_id}")
        return True, "배당금이 성공적으로 추가되었습니다."
    except Exception as e:
        log_exception(logger, e, {"context": "배당금 추가", "ticker": ticker, "amount": amount})
        return False, f"배당금 추가 중 오류가 발생했습니다: {e}"

def update_all_prices(user_id=None):
    """
    모든 포트폴리오 종목의 실시간 가격 업데이트
    
    Args:
        user_id (int, optional): 특정 사용자 ID (None인 경우 모든 사용자 포트폴리오 업데이트)
        
    Returns:
        int: 업데이트된 종목 수
    """
    try:
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 사용자 ID로 필터링 조건 설정
        filter_condition = "WHERE user_id = ?" if user_id else ""
        params = (user_id,) if user_id else ()
        
        # 모든 종목 가져오기
        cursor.execute(f"SELECT id, 종목코드, 국가, user_id FROM portfolio {filter_condition}", params)
        stocks = cursor.fetchall()
        
        update_count = 0
        
        for stock in stocks:
            try:
                stock_id, ticker, country, stock_user_id = stock
                
                current_price = None
                usd_price = None
                
                if country == '한국':
                    current_price = get_krx_stock_price(ticker)
                    if current_price:
                        cursor.execute(
                            "UPDATE portfolio SET 현재가_원화 = ?, last_update = ? WHERE id = ?", 
                            (current_price, datetime.now(), stock_id)
                        )
                        update_count += 1
                else:
                    usd_price = get_international_stock_price(ticker, country)
                    if usd_price:
                        # 환율 적용 (USD → KRW)
                        exchange_rate = get_exchange_rate('USD', 'KRW')
                        krw_price = usd_price * exchange_rate if exchange_rate else usd_price
                        
                        cursor.execute(
                            "UPDATE portfolio SET 현재가_달러 = ?, 현재가_원화 = ?, last_update = ? WHERE id = ?", 
                            (usd_price, krw_price, datetime.now(), stock_id)
                        )
                        current_price = krw_price
                        update_count += 1
                
                # 평가액, 손익 계산 업데이트
                if current_price:
                    cursor.execute("""
                        SELECT 수량, 평단가_원화, 배당금 FROM portfolio WHERE id = ?
                    """, (stock_id,))
                    
                    stock_data = cursor.fetchone()
                    
                    if stock_data:
                        qty, avg_price, dividend = stock_data
                        dividend = dividend or 0
                        
                        eval_amount = qty * current_price
                        profit_amount = qty * (current_price - avg_price)
                        profit_percent = (current_price - avg_price) / avg_price * 100 if avg_price > 0 else 0
                        
                        # 배당금을 포함한 총수익률
                        total_profit_amount = profit_amount + dividend
                        total_profit_percent = ((current_price - avg_price) / avg_price * 100) + (dividend / (qty * avg_price) * 100) if avg_price > 0 and qty > 0 else 0
                        
                        cursor.execute("""
                            UPDATE portfolio 
                            SET 평가액 = ?, 손익금액 = ?, 손익수익 = ?, 총수익률 = ?, last_update = ?
                            WHERE id = ?
                        """, (eval_amount, profit_amount, profit_percent, total_profit_percent, datetime.now(), stock_id))
            except Exception as e:
                log_exception(logger, e, {"context": "종목 가격 업데이트", "ticker": ticker})
        
        # 각 사용자별 포트폴리오 투자비중 업데이트
        if user_id:
            # 특정 사용자의 포트폴리오만 업데이트
            cursor.execute("SELECT SUM(평가액) FROM portfolio WHERE user_id = ?", (user_id,))
            total_value = cursor.fetchone()[0] or 0
            
            if total_value > 0:
                cursor.execute("""
                    UPDATE portfolio 
                    SET 투자비중 = (평가액 / ?) * 100
                    WHERE user_id = ?
                """, (total_value, user_id))
        else:
            # 모든 사용자의 포트폴리오 업데이트
            cursor.execute("SELECT DISTINCT user_id FROM portfolio")
            user_ids = [row[0] for row in cursor.fetchall()]
            
            for uid in user_ids:
                cursor.execute("SELECT SUM(평가액) FROM portfolio WHERE user_id = ?", (uid,))
                total_value = cursor.fetchone()[0] or 0
                
                if total_value > 0:
                    cursor.execute("""
                        UPDATE portfolio 
                        SET 투자비중 = (평가액 / ?) * 100
                        WHERE user_id = ?
                    """, (total_value, uid))
        
        conn.commit()
        conn.close()
        
        logger.info(f"가격 업데이트 완료: {update_count}개 종목")
        return update_count
    except Exception as e:
        log_exception(logger, e, {"context": "가격 업데이트"})
        return 0
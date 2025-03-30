"""
포트폴리오 관련 서비스
"""
import pandas as pd
from datetime import datetime

# 로깅 설정
try:
    from utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # 콘솔 출력 설정
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

# 필요한 함수 import
try:
    from models.database import get_db_connection
except ImportError:
    logger.error("models.database 모듈을 불러올 수 없습니다.")

try:
    from services.market_service import (
        get_krx_stock_price,
        get_international_stock_price,
        get_exchange_rate
    )
except ImportError:
    logger.error("market_service 모듈을 불러올 수 없습니다.")
    # 더미 함수 정의
    def get_krx_stock_price(ticker): return None
    def get_international_stock_price(ticker, country=None): return None
    def get_exchange_rate(from_currency, to_currency): return None

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
        query = "SELECT * FROM portfolio WHERE user_id = ? ORDER BY 투자비중 DESC"
        df = pd.read_sql_query(query, conn, params=(user_id,))
        
        conn.close()
        
        # 빈 데이터프레임 처리
        if df.empty:
            return pd.DataFrame()
        
        # UI 표시용 컬럼명 변경 및 선택
        try:
            df = df[[
                '증권사', '계좌', '국가', '종목코드', '종목명', '수량', 
                '평단가_원화', '평단가_달러', '현재가_원화', '현재가_달러',
                '평가액', '투자비중', '손익금액', '손익수익', '총수익률'
            ]]
            
            # 컬럼명 포맷팅 - UI에 표시되는 헤더명 변경
            df.columns = [
                "증권사", "계좌", "국가", "종목코드", "종목명", "수량", 
                "평단가(원화)", "평단가(달러)", "현재가(원화)", "현재가(달러)",
                "평가액[원화]", "투자비중", "손익금액[원화]", "손익수익[원화]", "총수익률[원가+배당]"
            ]
            
            # 숫자 포맷팅
            for col in ["평단가(원화)", "평단가(달러)", "현재가(원화)", "현재가(달러)"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
            
            for col in ["평가액[원화]", "손익금액[원화]"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
            
            for col in ["투자비중", "손익수익[원화]", "총수익률[원가+배당]"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        except Exception as e:
            logger.error(f"포트폴리오 데이터 변환 오류: {e}")
            return pd.DataFrame()
        
        return df
    except Exception as e:
        logger.error(f"포트폴리오 로드 오류: {e}")
        return pd.DataFrame()

def buy_stock(user_id, broker, account, country, ticker, stock_name, quantity, price):
    """
    주식 매수
    
    Args:
        user_id (int): 사용자 ID
        broker (str): 증권사
        account (str): 계좌
        country (str): 국가
        ticker (str): 종목코드
        stock_name (str): 종목명
        quantity (int): 수량
        price (float): 매수가
        
    Returns:
        pandas.DataFrame: 업데이트된 포트폴리오 (Data Frame)
    """
    try:
        # 수량과 가격 변환
        quantity = int(quantity)
        price = float(price)
        
        # 데이터베이스 연결
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 해당 종목이 이미 있는지 확인
        cursor.execute(
            "SELECT id, 수량, 평단가_원화 FROM portfolio WHERE 종목코드 = ? AND 계좌 = ? AND user_id = ?", 
            (ticker, account, user_id)
        )
        existing = cursor.fetchone()
        
        current_time = datetime.now()
        
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
                INSERT INTO transactions (portfolio_id, user_id, type, quantity, price, transaction_date) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (stock_id, user_id, '매수', quantity, price, current_time)
            )
            
            logger.info(f"종목 매수 (추가): {stock_name} ({ticker}), 수량: {quantity}, 사용자: {user_id}")
        else:
            # 평단가 달러 변환 (해외 주식)
            avg_price_usd = None
            if country != '한국':
                exchange_rate = get_exchange_rate('USD', 'KRW')
                avg_price_usd = price / exchange_rate if exchange_rate else None
            
            # 새 종목 추가
            cursor.execute(
                """
                INSERT INTO portfolio (
                    user_id, 증권사, 계좌, 국가, 종목코드, 종목명, 수량, 평단가_원화, 평단가_달러,
                    현재가_원화, 현재가_달러, 평가액, 투자비중, 손익금액, 손익수익, 총수익률, last_update
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, ?)
                """,
                (user_id, broker, account, country, ticker, stock_name, quantity, price, avg_price_usd, current_time)
            )
            
            stock_id = cursor.lastrowid
            
            # 거래내역 추가
            cursor.execute(
                """
                INSERT INTO transactions (portfolio_id, user_id, type, quantity, price, transaction_date) 
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (stock_id, user_id, '매수', quantity, price, current_time)
            )
            
            logger.info(f"종목 매수 (신규): {stock_name} ({ticker}), 수량: {quantity}, 사용자: {user_id}")
        
        conn.commit()
        conn.close()
        
        # 실시간 가격 업데이트
        update_all_prices(user_id)
        
        # 업데이트된 포트폴리오 반환
        return load_portfolio(user_id)
    except Exception as e:
        logger.error(f"매수 오류: {e}")
        return load_portfolio(user_id)

def sell_stock(user_id, ticker, account, quantity, price):
    """
    주식 매도
    
    Args:
        user_id (int): 사용자 ID
        ticker (str): 종목코드
        account (str): 계좌
        quantity (int): 수량
        price (float): 매도가
        
    Returns:
        tuple: (결과 메시지, 업데이트된 포트폴리오)
    """
    try:
        # 수량과 가격 변환
        quantity = int(quantity)
        price = float(price)
        
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
        current_time = datetime.now()
        
        if quantity > existing_quantity:
            conn.close()
            return "보유 수량보다 많은 수량을 매도할 수 없습니다.", load_portfolio(user_id)
        
        # 거래내역 추가
        cursor.execute(
            """
            INSERT INTO transactions (portfolio_id, user_id, type, quantity, price, transaction_date) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (stock_id, user_id, '매도', quantity, price, current_time)
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
        logger.error(f"매도 오류: {e}")
        return f"매도 처리 중 오류가 발생했습니다: {e}", load_portfolio(user_id)

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
                    usd_price = get_international_stock_price(ticker)
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
                        SELECT 수량, 평단가_원화 FROM portfolio WHERE id = ?
                    """, (stock_id,))
                    
                    stock_data = cursor.fetchone()
                    
                    if stock_data:
                        qty, avg_price = stock_data
                        
                        eval_amount = qty * current_price
                        profit_amount = qty * (current_price - avg_price)
                        profit_percent = (current_price - avg_price) / avg_price * 100 if avg_price > 0 else 0
                        
                        cursor.execute("""
                            UPDATE portfolio 
                            SET 평가액 = ?, 손익금액 = ?, 손익수익 = ?, last_update = ?
                            WHERE id = ?
                        """, (eval_amount, profit_amount, profit_percent, datetime.now(), stock_id))
            except Exception as e:
                logger.error(f"종목 {ticker} 가격 업데이트 오류: {e}")
        
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
        logger.error(f"가격 업데이트 오류: {e}")
        return 0

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
                    SUM(손익금액) as total_gain_loss
                FROM portfolio 
                WHERE user_id = ?
            """, (user_id,))
            
            portfolio_summary = cursor.fetchone()
            
            if portfolio_summary and portfolio_summary[0]:
                total_value = portfolio_summary[0]
                total_invested = portfolio_summary[1]
                total_gain_loss = portfolio_summary[2]
                
                # 총 수익률 계산
                total_return = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0
                
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
                        SET total_value = ?, total_invested = ?, total_gain_loss = ?, total_return_percent = ?
                        WHERE id = ?
                        """,
                        (total_value, total_invested, total_gain_loss, total_return, existing[0])
                    )
                else:
                    # 새 이력 추가
                    cursor.execute(
                        """
                        INSERT INTO portfolio_history (user_id, date, total_value, total_invested, total_gain_loss, total_return_percent)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (user_id, today, total_value, total_invested, total_gain_loss, total_return)
                    )
                
                update_count += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"포트폴리오 이력 업데이트 완료: {update_count}명의 사용자")
        return update_count
    except Exception as e:
        logger.error(f"포트폴리오 이력 업데이트 오류: {e}")
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
                SUM(손익금액) as total_gain_loss
            FROM portfolio 
            WHERE user_id = ?
        """, (user_id,))
        
        summary = cursor.fetchone()
        total_value = summary[0] or 0
        total_invested = summary[1] or 0
        total_gain_loss = summary[2] or 0
        total_return = (total_gain_loss / total_invested * 100) if total_invested > 0 else 0
        
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
        
        # 상위 5개 종목
        cursor.execute("""
            SELECT 종목명, 평가액, 투자비중
            FROM portfolio
            WHERE user_id = ?
            ORDER BY 평가액 DESC
            LIMIT 5
        """, (user_id,))
        
        top_stocks = [{"name": row[0], "value": row[1], "weight": row[2]} for row in cursor.fetchall()]
        
        # 포트폴리오 이력 (최근 30일)
        cursor.execute("""
            SELECT date, total_value, total_return_percent
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
                "return": row[2]
            })
        
        # 역순 정렬 (오래된 날짜부터)
        history.reverse()
        
        conn.close()
        
        return {
            "summary": {
                "total_value": total_value,
                "total_invested": total_invested,
                "total_gain_loss": total_gain_loss,
                "total_return": total_return,
                "savings_total": savings_total,
                "total_assets": total_assets
            },
            "distributions": {
                "country": country_distribution,
                "account": account_distribution,
                "broker": broker_distribution
            },
            "top_stocks": top_stocks,
            "history": history,
            "savings": savings_list
        }
    except Exception as e:
        logger.error(f"포트폴리오 요약 정보 조회 오류: {e}")
        
        # 최소한의 기본 구조 반환
        return {
            "summary": {
                "total_value": 0,
                "total_invested": 0,
                "total_gain_loss": 0,
                "total_return": 0,
                "savings_total": 0,
                "total_assets": 0
            },
            "distributions": {
                "country": {},
                "account": {},
                "broker": {}
            },
            "top_stocks": [],
            "history": [],
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
        SELECT t.id, p.종목명, t.type, t.quantity, t.price, t.transaction_date
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
        df.columns = ["ID", "종목명", "거래유형", "수량", "가격", "거래일시"]
        
        # 숫자 포맷팅
        df["수량"] = df["수량"].apply(lambda x: f"{int(x):,d}" if pd.notnull(x) else "")
        df["가격"] = df["가격"].apply(lambda x: f"{x:,.0f}원" if pd.notnull(x) else "")
        
        # 날짜 포맷팅
        df["거래일시"] = pd.to_datetime(df["거래일시"]).dt.strftime('%Y-%m-%d %H:%M')
        
        return df
    except Exception as e:
        logger.error(f"거래내역 로드 오류: {e}")
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
        SELECT 종목코드, 종목명, 계좌, 수량, 현재가_원화
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
                "현재가_원화": row[4]
            })
        
        conn.close()
        return stocks
    except Exception as e:
        logger.error(f"보유 종목 조회 오류: {e}")
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
        conn.close()
        
        if row:
            # 결과를 딕셔너리로 변환
            column_names = [desc[0] for desc in cursor.description]
            result = dict(zip(column_names, row))
            return result
        return None
    except Exception as e:
        logger.error(f"종목 상세 정보 조회 오류: {e}")
        return None
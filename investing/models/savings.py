"""
포트폴리오 관련 데이터 모델 - 새로운 필드 및 기능 지원
"""
import sqlite3
from datetime import datetime
import pandas as pd
from models.database import get_db_connection
from utils.logging import get_logger, log_exception

logger = get_logger(__name__)

def get_portfolio_by_user(user_id):
    """
    사용자 ID로 포트폴리오 조회
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        list: 포트폴리오 항목 목록
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM portfolio WHERE user_id = ? ORDER BY 투자비중 DESC", 
            (user_id,)
        )
        
        portfolio = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return portfolio
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 목록 조회", "user_id": user_id})
        return []

def get_stock_by_ticker(user_id, ticker, account=None):
    """
    종목코드와 계좌로 포트폴리오 항목 조회
    
    Args:
        user_id (int): 사용자 ID
        ticker (str): 종목코드
        account (str, optional): 계좌명
        
    Returns:
        dict or None: 포트폴리오 항목 또는 None (항목이 없는 경우)
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        if account:
            cursor.execute(
                "SELECT * FROM portfolio WHERE user_id = ? AND 종목코드 = ? AND 계좌 = ?", 
                (user_id, ticker, account)
            )
        else:
            cursor.execute(
                "SELECT * FROM portfolio WHERE user_id = ? AND 종목코드 = ?", 
                (user_id, ticker)
            )
        
        stock = cursor.fetchone()
        conn.close()
        
        if stock:
            return dict(stock)
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "종목 상세 조회", "ticker": ticker})
        return None

def add_portfolio_stock(user_id, broker, account, country, ticker, stock_name, quantity, avg_price, 
                       avg_price_usd=None, sector=None, industry=None, memo=None, purchase_date=None):
    """
    포트폴리오에 종목 추가
    
    Args:
        user_id (int): 사용자 ID
        broker (str): 증권사
        account (str): 계좌
        country (str): 국가
        ticker (str): 종목코드
        stock_name (str): 종목명
        quantity (float): 수량
        avg_price (float): 평균 매수가(원화)
        avg_price_usd (float, optional): 평균 매수가(달러, 해외주식)
        sector (str, optional): 섹터
        industry (str, optional): 산업군
        memo (str, optional): 메모
        purchase_date (date, optional): 매수 날짜
        
    Returns:
        int or None: 추가된 항목 ID 또는 None (추가 실패시)
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        current_time = datetime.now()
        
        # 매수 날짜 처리
        if purchase_date is None:
            purchase_date = current_time.date()
        
        # 확장된 필드들을 포함한 삽입 쿼리
        cursor.execute(
            """
            INSERT INTO portfolio (
                user_id, 증권사, 계좌, 국가, 종목코드, 종목명, 수량, 평단가_원화, 평단가_달러,
                현재가_원화, 현재가_달러, 평가액, 투자비중, 손익금액, 손익수익, 총수익률,
                배당금, 섹터, 산업군, 매수날짜, 메모, last_update
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, ?, ?, ?, ?, ?)
            """,
            (user_id, broker, account, country, ticker, stock_name, quantity, avg_price, avg_price_usd, 
             sector, industry, purchase_date, memo, current_time)
        )
        
        stock_id = cursor.lastrowid
        
        # 거래내역 추가
        cursor.execute(
            """
            INSERT INTO transactions (portfolio_id, user_id, type, quantity, price, 거래메모, transaction_date) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (stock_id, user_id, '매수', quantity, avg_price, memo, current_time)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"종목 추가: {stock_name} ({ticker}), 사용자: {user_id}")
        return stock_id
    except Exception as e:
        conn.rollback() if 'conn' in locals() else None
        conn.close() if 'conn' in locals() else None
        log_exception(logger, e, {"context": "종목 추가", "ticker": ticker})
        return None

def update_portfolio_stock(stock_id, user_id, quantity=None, current_price=None, usd_price=None, 
                          sector=None, industry=None, memo=None, beta=None, dividend=None):
    """
    포트폴리오 종목 업데이트
    
    Args:
        stock_id (int): 종목 ID
        user_id (int): 사용자 ID
        quantity (float, optional): 새 수량
        current_price (float, optional): 현재가
        usd_price (float, optional): 달러 가격 (해외주식)
        sector (str, optional): 섹터
        industry (str, optional): 산업군
        memo (str, optional): 메모
        beta (float, optional): 베타값
        dividend (float, optional): 배당금
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        update_fields = []
        update_values = []
        
        # 업데이트할 필드 추가
        if quantity is not None:
            update_fields.append("수량 = ?")
            update_values.append(quantity)
        
        if current_price is not None:
            update_fields.append("현재가_원화 = ?")
            update_values.append(current_price)
        
        if usd_price is not None:
            update_fields.append("현재가_달러 = ?")
            update_values.append(usd_price)
        
        if sector is not None:
            update_fields.append("섹터 = ?")
            update_values.append(sector)
        
        if industry is not None:
            update_fields.append("산업군 = ?")
            update_values.append(industry)
        
        if memo is not None:
            update_fields.append("메모 = ?")
            update_values.append(memo)
        
        if beta is not None:
            update_fields.append("베타 = ?")
            update_values.append(beta)
        
        if dividend is not None:
            update_fields.append("배당금 = ?")
            update_values.append(dividend)
        
        # 마지막 업데이트 시간 추가
        update_fields.append("last_update = ?")
        update_values.append(datetime.now())
        
        # 업데이트할 필드가 있는 경우에만 실행
        if update_fields:
            # 쿼리 구성
            query = f"UPDATE portfolio SET {', '.join(update_fields)} WHERE id = ? AND user_id = ?"
            update_values.extend([stock_id, user_id])
            
            cursor.execute(query, update_values)
            
            # 만약 현재가가 업데이트 되었다면 평가액 등도 업데이트
            if current_price is not None:
                cursor.execute("""
                    SELECT 수량, 평단가_원화, 배당금 FROM portfolio WHERE id = ?
                """, (stock_id,))
                
                stock_data = cursor.fetchone()
                
                if stock_data:
                    qty, avg_price, dividend_amount = stock_data
                    if dividend_amount is None:
                        dividend_amount = 0
                    
                    eval_amount = qty * current_price
                    profit_amount = qty * (current_price - avg_price)
                    profit_percent = (current_price - avg_price) / avg_price * 100 if avg_price > 0 else 0
                    
                    # 배당금을 포함한 총수익률
                    total_profit_amount = profit_amount + dividend_amount
                    total_profit_percent = (profit_percent + (dividend_amount / (qty * avg_price) * 100 if qty * avg_price > 0 else 0))
                    
                    cursor.execute("""
                        UPDATE portfolio 
                        SET 평가액 = ?, 손익금액 = ?, 손익수익 = ?, 총수익률 = ?
                        WHERE id = ?
                    """, (eval_amount, profit_amount, profit_percent, total_profit_percent, stock_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"종목 업데이트 (ID: {stock_id}), 사용자: {user_id}")
        return True
    except Exception as e:
        conn.rollback() if 'conn' in locals() else None
        conn.close() if 'conn' in locals() else None
        log_exception(logger, e, {"context": "종목 업데이트", "stock_id": stock_id})
        return False

def delete_portfolio_stock(stock_id, user_id):
    """
    포트폴리오 종목 삭제
    
    Args:
        stock_id (int): 종목 ID
        user_id (int): 사용자 ID
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 거래내역 보존을 위해 portfolio_id 필드는 null로 설정
        cursor.execute(
            "UPDATE transactions SET portfolio_id = NULL WHERE portfolio_id = ? AND user_id = ?",
            (stock_id, user_id)
        )
        
        # 배당금 내역 삭제
        cursor.execute(
            "DELETE FROM dividends WHERE portfolio_id = ? AND user_id = ?",
            (stock_id, user_id)
        )
        
        # 종목 삭제
        cursor.execute(
            "DELETE FROM portfolio WHERE id = ? AND user_id = ?",
            (stock_id, user_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"종목 삭제 (ID: {stock_id}), 사용자: {user_id}")
        return True
    except Exception as e:
        conn.rollback() if 'conn' in locals() else None
        conn.close() if 'conn' in locals() else None
        log_exception(logger, e, {"context": "종목 삭제", "stock_id": stock_id})
        return False

def add_transaction(portfolio_id, user_id, transaction_type, quantity, price, 
                   fee=0, tax=0, realized_profit=None, date=None, memo=None):
    """
    거래내역 추가
    
    Args:
        portfolio_id (int): 포트폴리오 종목 ID
        user_id (int): 사용자 ID
        transaction_type (str): 거래 유형 ('매수' 또는 '매도')
        quantity (float): 수량
        price (float): 가격
        fee (float, optional): 수수료
        tax (float, optional): 세금
        realized_profit (float, optional): 실현 손익 (매도 시)
        date (datetime, optional): 거래일시 (기본값: 현재 시간)
        memo (str, optional): 메모
        
    Returns:
        int or None: 추가된 거래내역 ID 또는 None (추가 실패시)
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        if date is None:
            date = datetime.now()
        
        cursor.execute(
            """
            INSERT INTO transactions (
                portfolio_id, user_id, type, quantity, price, 수수료, 세금, 
                실현손익, transaction_date, 거래메모
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (portfolio_id, user_id, transaction_type, quantity, price, fee, tax, 
             realized_profit, date, memo)
        )
        
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"거래내역 추가: {transaction_type}, 종목 ID: {portfolio_id}, 사용자: {user_id}")
        return transaction_id
    except Exception as e:
        conn.rollback() if 'conn' in locals() else None
        conn.close() if 'conn' in locals() else None
        log_exception(logger, e, {"context": "거래내역 추가", "portfolio_id": portfolio_id})
        return None

def get_transactions_by_user(user_id, limit=100):
    """
    사용자의 거래내역 조회
    
    Args:
        user_id (int): 사용자 ID
        limit (int, optional): 최대 조회 개수
        
    Returns:
        list: 거래내역 목록
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT t.id, p.종목명, t.type, t.quantity, t.price, t.transaction_date,
                  t.수수료, t.세금, t.실현손익, t.거래메모
            FROM transactions t
            LEFT JOIN portfolio p ON t.portfolio_id = p.id
            WHERE t.user_id = ?
            ORDER BY t.transaction_date DESC
            LIMIT ?
            """,
            (user_id, limit)
        )
        
        transactions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return transactions
    except Exception as e:
        log_exception(logger, e, {"context": "거래내역 조회", "user_id": user_id})
        return []

def add_dividend(portfolio_id, user_id, payment_date, amount, dividend_type='현금배당', currency='KRW', 
                pretax_amount=None, posttax_amount=None):
    """
    배당금 내역 추가
    
    Args:
        portfolio_id (int): 포트폴리오 종목 ID
        user_id (int): 사용자 ID
        payment_date (date): 지급일
        amount (float): 배당액
        dividend_type (str, optional): 배당 유형 (현금배당, 주식배당 등)
        currency (str, optional): 통화
        pretax_amount (float, optional): 세전 금액
        posttax_amount (float, optional): 세후 금액
        
    Returns:
        int or None: 추가된 배당금 내역 ID 또는 None (추가 실패시)
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 세전/세후 금액이 지정되지 않은 경우 배당액으로 설정
        if pretax_amount is None:
            pretax_amount = amount
        if posttax_amount is None:
            posttax_amount = amount
        
        cursor.execute(
            """
            INSERT INTO dividends (
                portfolio_id, user_id, 지급일, 배당액, 배당유형, 통화, 세전금액, 세후금액
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (portfolio_id, user_id, payment_date, amount, dividend_type, 
             currency, pretax_amount, posttax_amount)
        )
        
        dividend_id = cursor.lastrowid
        
        # 포트폴리오의 총 배당금 업데이트
        cursor.execute(
            """
            UPDATE portfolio 
            SET 배당금 = COALESCE(배당금, 0) + ?, 최근배당일 = ?
            WHERE id = ?
            """, 
            (amount, payment_date, portfolio_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"배당금 추가: 종목 ID: {portfolio_id}, 금액: {amount}, 사용자: {user_id}")
        return dividend_id
    except Exception as e:
        conn.rollback() if 'conn' in locals() else None
        conn.close() if 'conn' in locals() else None
        log_exception(logger, e, {"context": "배당금 추가", "portfolio_id": portfolio_id})
        return None

def get_dividends_by_user(user_id, limit=100):
    """
    사용자의 배당금 내역 조회
    
    Args:
        user_id (int): 사용자 ID
        limit (int, optional): 최대 조회 개수
        
    Returns:
        list: 배당금 내역 목록
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT d.id, p.종목명, d.지급일, d.배당액, d.배당유형, d.통화, d.세전금액, d.세후금액
            FROM dividends d
            LEFT JOIN portfolio p ON d.portfolio_id = p.id
            WHERE d.user_id = ?
            ORDER BY d.지급일 DESC
            LIMIT ?
            """,
            (user_id, limit)
        )
        
        dividends = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return dividends
    except Exception as e:
        log_exception(logger, e, {"context": "배당금 내역 조회", "user_id": user_id})
        return []

def add_portfolio_history(user_id, date, total_value, total_invested, total_gain_loss, 
                         total_return_percent, cash_balance=0, realized_profit=0, unrealized_profit=0):
    """
    포트폴리오 이력 추가
    
    Args:
        user_id (int): 사용자 ID
        date (date): 날짜
        total_value (float): 총 평가액
        total_invested (float): 총 투자금액
        total_gain_loss (float): 총 손익금액
        total_return_percent (float): 총 수익률
        cash_balance (float, optional): 현금 잔고
        realized_profit (float, optional): 실현 이익
        unrealized_profit (float, optional): 미실현 이익
        
    Returns:
        int or None: 추가된 이력 ID 또는 None (추가 실패시)
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 같은 날짜의 이력이 있는지 확인
        cursor.execute(
            "SELECT id FROM portfolio_history WHERE user_id = ? AND date = ?",
            (user_id, date)
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
                (total_value, total_invested, total_gain_loss, total_return_percent, 
                 cash_balance, realized_profit, unrealized_profit, existing[0])
            )
            history_id = existing[0]
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
                (user_id, date, total_value, total_invested, total_gain_loss, 
                 total_return_percent, cash_balance, realized_profit, unrealized_profit)
            )
            history_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        logger.info(f"포트폴리오 이력 추가/업데이트: {date}, 사용자: {user_id}")
        return history_id
    except Exception as e:
        conn.rollback() if 'conn' in locals() else None
        conn.close() if 'conn' in locals() else None
        log_exception(logger, e, {"context": "포트폴리오 이력 추가", "user_id": user_id})
        return None

def get_portfolio_history(user_id, days=30):
    """
    포트폴리오 이력 조회
    
    Args:
        user_id (int): 사용자 ID
        days (int, optional): 조회할 일수
        
    Returns:
        list: 포트폴리오 이력 목록
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT date, total_value, total_invested, total_gain_loss, total_return_percent,
                  cash_balance, realized_profit, unrealized_profit
            FROM portfolio_history
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (user_id, days)
        )
        
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # 날짜순으로 정렬 (오래된 날짜부터)
        history.reverse()
        
        return history
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 이력 조회", "user_id": user_id})
        return []

def export_portfolio_data(user_id, include_transactions=False, include_dividends=False):
    """
    포트폴리오 데이터 내보내기
    
    Args:
        user_id (int): 사용자 ID
        include_transactions (bool, optional): 거래내역 포함 여부
        include_dividends (bool, optional): 배당금 내역 포함 여부
        
    Returns:
        dict: 내보내기 데이터
    """
    try:
        # 포트폴리오 항목 조회
        portfolio = get_portfolio_by_user(user_id)
        
        export_data = {
            "portfolio": portfolio,
            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id
        }
        
        # 거래내역 포함 여부
        if include_transactions:
            export_data["transactions"] = get_transactions_by_user(user_id, limit=1000)
        
        # 배당금 내역 포함 여부
        if include_dividends:
            export_data["dividends"] = get_dividends_by_user(user_id, limit=1000)
        
        # 포트폴리오 이력 포함
        export_data["history"] = get_portfolio_history(user_id, days=365)
        
        return export_data
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 데이터 내보내기", "user_id": user_id})
        return {
            "portfolio": [],
            "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": user_id,
            "error": str(e)
        }

def import_portfolio_data(user_id, import_data, overwrite=False):
    """
    포트폴리오 데이터 가져오기
    
    Args:
        user_id (int): 사용자 ID
        import_data (dict): 가져올 데이터
        overwrite (bool, optional): 기존 데이터 덮어쓰기 여부
        
    Returns:
        dict: 결과 (성공한 항목 수 등)
    """
    try:
        conn = get_db_connection('portfolio')
        cursor = conn.cursor()
        
        # 기존 데이터 삭제 (덮어쓰기 모드인 경우)
        if overwrite:
            cursor.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM dividends WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM portfolio WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM portfolio_history WHERE user_id = ?", (user_id,))
        
        results = {
            "portfolio_added": 0,
            "portfolio_updated": 0,
            "transactions_added": 0,
            "dividends_added": 0,
            "history_added": 0
        }
        
        # 포트폴리오 데이터 가져오기
        portfolio_items = import_data.get("portfolio", [])
        
        for item in portfolio_items:
            # 필수 필드 확인
            if not all(k in item for k in ['종목코드', '종목명', '계좌', '수량', '평단가_원화']):
                continue
            
            # 기존 종목 확인
            cursor.execute(
                "SELECT id FROM portfolio WHERE 종목코드 = ? AND 계좌 = ? AND user_id = ?", 
                (item['종목코드'], item['계좌'], user_id)
            )
            existing = cursor.fetchone()
            
            if existing and not overwrite:
                # 기존 종목 업데이트
                item['id'] = existing[0]
                
                update_fields = []
                update_values = []
                
                for key, value in item.items():
                    if key != 'id' and key != 'user_id':
                        update_fields.append(f"{key} = ?")
                        update_values.append(value)
                
                update_fields.append("last_update = ?")
                update_values.append(datetime.now())
                
                cursor.execute(
                    f"UPDATE portfolio SET {', '.join(update_fields)} WHERE id = ?",
                    (*update_values, existing[0])
                )
                
                results["portfolio_updated"] += 1
            else:
                # 새 종목 추가
                item['user_id'] = user_id
                
                fields = list(item.keys())
                placeholders = ', '.join(['?'] * len(fields))
                
                cursor.execute(
                    f"INSERT INTO portfolio ({', '.join(fields)}) VALUES ({placeholders})",
                    tuple(item.values())
                )
                
                results["portfolio_added"] += 1
        
        # 거래내역 데이터 가져오기
        transactions = import_data.get("transactions", [])
        
        for transaction in transactions:
            # 필수 필드 확인
            if not all(k in transaction for k in ['type', 'quantity', 'price', 'transaction_date']):
                continue
            
            transaction['user_id'] = user_id
            
            fields = list(transaction.keys())
            placeholders = ', '.join(['?'] * len(fields))
            
            cursor.execute(
                f"INSERT INTO transactions ({', '.join(fields)}) VALUES ({placeholders})",
                tuple(transaction.values())
            )
            
            results["transactions_added"] += 1
        
        # 배당금 내역 데이터 가져오기
        dividends = import_data.get("dividends", [])
        
        for dividend in dividends:
            # 필수 필드 확인
            if not all(k in dividend for k in ['지급일', '배당액']):
                continue
            
            dividend['user_id'] = user_id
            
            fields = list(dividend.keys())
            placeholders = ', '.join(['?'] * len(fields))
            
            cursor.execute(
                f"INSERT INTO dividends ({', '.join(fields)}) VALUES ({placeholders})",
                tuple(dividend.values())
            )
            
            results["dividends_added"] += 1
        
        # 포트폴리오 이력 데이터 가져오기
        history_items = import_data.get("history", [])
        
        for history in history_items:
            # 필수 필드 확인
            if not all(k in history for k in ['date', 'total_value', 'total_invested']):
                continue
            
            history['user_id'] = user_id
            
            # 같은 날짜의 이력이 있는지 확인
            cursor.execute(
                "SELECT id FROM portfolio_history WHERE user_id = ? AND date = ?",
                (user_id, history['date'])
            )
            
            existing = cursor.fetchone()
            
            if existing and not overwrite:
                # 기존 이력 업데이트
                history_id = existing[0]
                
                update_fields = []
                update_values = []
                
                for key, value in history.items():
                    if key != 'id' and key != 'user_id' and key != 'date':
                        update_fields.append(f"{key} = ?")
                        update_values.append(value)
                
                cursor.execute(
                    f"UPDATE portfolio_history SET {', '.join(update_fields)} WHERE id = ?",
                    (*update_values, history_id)
                )
            else:
                # 새 이력 추가
                fields = list(history.keys())
                placeholders = ', '.join(['?'] * len(fields))
                
                cursor.execute(
                    f"INSERT INTO portfolio_history ({', '.join(fields)}) VALUES ({placeholders})",
                    tuple(history.values())
                )
                
                results["history_added"] += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"포트폴리오 데이터 가져오기 완료, 사용자: {user_id}: {results}")
        return results
    except Exception as e:
        conn.rollback() if 'conn' in locals() else None
        conn.close() if 'conn' in locals() else None
        log_exception(logger, e, {"context": "포트폴리오 데이터 가져오기", "user_id": user_id})
        return {"error": str(e)}
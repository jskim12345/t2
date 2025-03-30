"""
포트폴리오 관련 데이터 모델
"""
import sqlite3
from datetime import datetime
import pandas as pd
from models.database import get_db_connection
from utils.logging import get_logger

logger = get_logger(__name__)

def get_portfolio_by_user(user_id):
    """
    사용자 ID로 포트폴리오 조회
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        list: 포트폴리오 항목 목록
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM portfolio WHERE user_id = ? ORDER BY 투자비중 DESC", 
        (user_id,)
    )
    
    portfolio = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return portfolio

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

def add_portfolio_stock(user_id, broker, account, country, ticker, stock_name, quantity, avg_price, avg_price_usd=None):
    """
    포트폴리오에 종목 추가
    
    Args:
        user_id (int): 사용자 ID
        broker (str): 증권사
        account (str): 계좌
        country (str): 국가
        ticker (str): 종목코드
        stock_name (str): 종목명
        quantity (int): 수량
        avg_price (float): 평균 매수가(원화)
        avg_price_usd (float, optional): 평균 매수가(달러, 해외주식)
        
    Returns:
        int or None: 추가된 항목 ID 또는 None (추가 실패시)
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    current_time = datetime.now()
    
    try:
        cursor.execute(
            """
            INSERT INTO portfolio (
                user_id, 증권사, 계좌, 국가, 종목코드, 종목명, 수량, 평단가_원화, 평단가_달러,
                현재가_원화, 현재가_달러, 평가액, 투자비중, 손익금액, 손익수익, 총수익률, last_update
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, ?)
            """,
            (user_id, broker, account, country, ticker, stock_name, quantity, avg_price, avg_price_usd, current_time)
        )
        
        stock_id = cursor.lastrowid
        
        # 거래내역 추가
        cursor.execute(
            """
            INSERT INTO transactions (portfolio_id, user_id, type, quantity, price, transaction_date) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (stock_id, user_id, '매수', quantity, avg_price, current_time)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"종목 추가: {stock_name} ({ticker}), 사용자: {user_id}")
        return stock_id
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"종목 추가 실패: {e}")
        return None

def update_portfolio_stock(stock_id, user_id, quantity, current_price=None, usd_price=None):
    """
    포트폴리오 종목 업데이트
    
    Args:
        stock_id (int): 종목 ID
        user_id (int): 사용자 ID
        quantity (int): 새 수량
        current_price (float, optional): 현재가
        usd_price (float, optional): 달러 가격 (해외주식)
        
    Returns:
        bool: 성공 여부
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    try:
        # 기본 수량 업데이트
        cursor.execute(
            "UPDATE portfolio SET 수량 = ?, last_update = ? WHERE id = ? AND user_id = ?",
            (quantity, datetime.now(), stock_id, user_id)
        )
        
        # 가격 정보가 있는 경우 추가 업데이트
        if current_price is not None:
            cursor.execute(
                "SELECT 수량, 평단가_원화 FROM portfolio WHERE id = ?", 
                (stock_id,)
            )
            result = cursor.fetchone()
            
            if result:
                qty, avg_price = result[0], result[1]
                
                # 평가액, 손익 계산
                eval_amount = qty * current_price
                profit_amount = qty * (current_price - avg_price)
                profit_percent = (current_price - avg_price) / avg_price * 100 if avg_price > 0 else 0
                
                cursor.execute(
                    """
                    UPDATE portfolio 
                    SET 현재가_원화 = ?, 평가액 = ?, 손익금액 = ?, 손익수익 = ?, last_update = ?
                    WHERE id = ?
                    """,
                    (current_price, eval_amount, profit_amount, profit_percent, datetime.now(), stock_id)
                )
                
                # 달러 가격이 있는 경우 추가 업데이트
                if usd_price is not None:
                    cursor.execute(
                        "UPDATE portfolio SET 현재가_달러 = ? WHERE id = ?",
                        (usd_price, stock_id)
                    )
        
        conn.commit()
        conn.close()
        
        logger.info(f"종목 업데이트 (ID: {stock_id}), 사용자: {user_id}")
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"종목 업데이트 실패 (ID: {stock_id}): {e}")
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
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "DELETE FROM portfolio WHERE id = ? AND user_id = ?",
            (stock_id, user_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"종목 삭제 (ID: {stock_id}), 사용자: {user_id}")
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"종목 삭제 실패 (ID: {stock_id}): {e}")
        return False

def add_transaction(portfolio_id, user_id, transaction_type, quantity, price, date=None):
    """
    거래내역 추가
    
    Args:
        portfolio_id (int): 포트폴리오 종목 ID
        user_id (int): 사용자 ID
        transaction_type (str): 거래 유형 ('매수' 또는 '매도')
        quantity (int): 수량
        price (float): 가격
        date (datetime, optional): 거래일시 (기본값: 현재 시간)
        
    Returns:
        int or None: 추가된 거래내역 ID 또는 None (추가 실패시)
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    if date is None:
        date = datetime.now()
    
    try:
        cursor.execute(
            """
            INSERT INTO transactions (portfolio_id, user_id, type, quantity, price, transaction_date) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (portfolio_id, user_id, transaction_type, quantity, price, date)
        )
        
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"거래내역 추가: {transaction_type}, 종목 ID: {portfolio_id}, 사용자: {user_id}")
        return transaction_id
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"거래내역 추가 실패: {e}")
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
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT t.id, p.종목명, t.type, t.quantity, t.price, t.transaction_date
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

def add_portfolio_history(user_id, date, total_value, total_invested, total_gain_loss, total_return_percent):
    """
    포트폴리오 이력 추가
    
    Args:
        user_id (int): 사용자 ID
        date (date): 날짜
        total_value (float): 총 평가액
        total_invested (float): 총 투자금액
        total_gain_loss (float): 총 손익금액
        total_return_percent (float): 총 수익률
        
    Returns:
        int or None: 추가된 이력 ID 또는 None (추가 실패시)
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    # 같은 날짜의 이력이 있는지 확인
    cursor.execute(
        "SELECT id FROM portfolio_history WHERE user_id = ? AND date = ?",
        (user_id, date)
    )
    
    existing = cursor.fetchone()
    
    try:
        if existing:
            # 기존 이력 업데이트
            cursor.execute(
                """
                UPDATE portfolio_history
                SET total_value = ?, total_invested = ?, total_gain_loss = ?, total_return_percent = ?
                WHERE id = ?
                """,
                (total_value, total_invested, total_gain_loss, total_return_percent, existing[0])
            )
            history_id = existing[0]
        else:
            # 새 이력 추가
            cursor.execute(
                """
                INSERT INTO portfolio_history (user_id, date, total_value, total_invested, total_gain_loss, total_return_percent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, date, total_value, total_invested, total_gain_loss, total_return_percent)
            )
            history_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        logger.info(f"포트폴리오 이력 추가/업데이트: {date}, 사용자: {user_id}")
        return history_id
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"포트폴리오 이력 추가 실패: {e}")
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
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT date, total_value, total_invested, total_gain_loss, total_return_percent
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
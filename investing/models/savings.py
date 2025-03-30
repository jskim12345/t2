"""
적금 관련 데이터 모델
"""
import sqlite3
from datetime import datetime
from models.database import get_db_connection
from utils.logging import get_logger

logger = get_logger(__name__)

def get_savings_by_user(user_id):
    """
    사용자 ID로 적금 목록 조회
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        list: 적금 목록
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM savings WHERE user_id = ? ORDER BY 시작일 DESC", 
        (user_id,)
    )
    
    savings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return savings

def get_savings_by_id(savings_id, user_id):
    """
    적금 ID로 적금 정보 조회
    
    Args:
        savings_id (int): 적금 ID
        user_id (int): 사용자 ID (권한 확인용)
        
    Returns:
        dict or None: 적금 정보 또는 None (정보가 없는 경우)
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM savings WHERE id = ? AND user_id = ?", 
        (savings_id, user_id)
    )
    
    saving = cursor.fetchone()
    conn.close()
    
    if saving:
        return dict(saving)
    return None

def add_savings(user_id, name, bank, account_number, start_date, end_date, 
               monthly_amount, interest_rate, savings_type):
    """
    적금 추가
    
    Args:
        user_id (int): 사용자 ID
        name (str): 적금명
        bank (str): 은행명
        account_number (str): 계좌번호
        start_date (str): 시작일 (YYYY-MM-DD)
        end_date (str): 만기일 (YYYY-MM-DD)
        monthly_amount (float): 월 납입액
        interest_rate (float): 금리 (%)
        savings_type (str): 적금 유형
        
    Returns:
        int or None: 추가된 적금 ID 또는 None (추가 실패시)
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    # 세후 금리 계산 (이자소득세 15.4% 가정)
    after_tax_rate = interest_rate * (1 - 0.154)
    
    try:
        # 현재 납입액 계산
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) else start_date
        today = datetime.now().date()
        
        months_passed = (today.year - start_date_obj.year) * 12 + (today.month - start_date_obj.month)
        if today.day < start_date_obj.day and months_passed > 0:
            months_passed -= 1
        
        current_amount = monthly_amount * max(0, months_passed)
        
        # 만기일 처리
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if isinstance(end_date, str) else end_date
        
        # 총 계약 기간 (개월)
        total_months = (end_date_obj.year - start_date_obj.year) * 12 + (end_date_obj.month - start_date_obj.month)
        
        # 예상 만기 금액 계산 (단리 가정)
        expected_amount = monthly_amount * total_months * (1 + (after_tax_rate/100 * total_months/24))
        
        cursor.execute(
            """
            INSERT INTO savings (
                user_id, 이름, 은행, 계좌번호, 시작일, 만기일, 월납입액, 금리, 세후금리,
                현재납입액, 예상만기금액, 적금유형, last_update
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, name, bank, account_number, start_date, end_date, monthly_amount, interest_rate, after_tax_rate,
             current_amount, expected_amount, savings_type, datetime.now())
        )
        
        savings_id = cursor.lastrowid
        
        # 최초 거래내역 추가 (가입)
        cursor.execute(
            """
            INSERT INTO savings_transactions (
                savings_id, user_id, 날짜, 금액, 거래유형, 메모
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (savings_id, user_id, start_date, monthly_amount, '가입', '적금 가입')
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"적금 추가: {name}, 사용자: {user_id}")
        return savings_id
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"적금 추가 실패: {e}")
        return None

def update_savings(savings_id, user_id, **kwargs):
    """
    적금 정보 업데이트
    
    Args:
        savings_id (int): 적금 ID
        user_id (int): 사용자 ID
        **kwargs: 업데이트할 필드와 값 (이름, 은행, 계좌번호, 월납입액, 금리 등)
        
    Returns:
        bool: 성공 여부
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    # 업데이트할 필드와 값 구성
    fields = []
    values = []
    
    # 한글 필드명과 영문 필드명 매핑
    field_mapping = {
        'name': '이름',
        'bank': '은행',
        'account_number': '계좌번호',
        'start_date': '시작일',
        'end_date': '만기일',
        'monthly_amount': '월납입액',
        'interest_rate': '금리',
        'savings_type': '적금유형'
    }
    
    # 매핑된 필드명으로 업데이트 쿼리 구성
    for key, value in kwargs.items():
        if key in field_mapping:
            fields.append(f"{field_mapping[key]} = ?")
            values.append(value)
    
    # 마지막 업데이트 시간 추가
    fields.append("last_update = ?")
    values.append(datetime.now())
    
    # 금리가 변경된 경우 세후 금리도 업데이트
    if 'interest_rate' in kwargs:
        fields.append("세후금리 = ?")
        after_tax_rate = kwargs['interest_rate'] * (1 - 0.154)
        values.append(after_tax_rate)
    
    # 조건 값 추가
    values.append(savings_id)
    values.append(user_id)
    
    if not fields:
        # 업데이트할 필드가 없으면 성공으로 간주
        return True
    
    try:
        query = f"UPDATE savings SET {', '.join(fields)} WHERE id = ? AND user_id = ?"
        
        cursor.execute(query, values)
        
        conn.commit()
        conn.close()
        
        logger.info(f"적금 업데이트 (ID: {savings_id}), 사용자: {user_id}")
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"적금 업데이트 실패 (ID: {savings_id}): {e}")
        return False

def delete_savings(savings_id, user_id):
    """
    적금 삭제
    
    Args:
        savings_id (int): 적금 ID
        user_id (int): 사용자 ID
        
    Returns:
        bool: 성공 여부
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    try:
        # 적금 삭제 전 관련 거래내역 삭제
        cursor.execute(
            "DELETE FROM savings_transactions WHERE savings_id = ? AND user_id = ?",
            (savings_id, user_id)
        )
        
        # 적금 삭제
        cursor.execute(
            "DELETE FROM savings WHERE id = ? AND user_id = ?",
            (savings_id, user_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"적금 삭제 (ID: {savings_id}), 사용자: {user_id}")
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"적금 삭제 실패 (ID: {savings_id}): {e}")
        return False

def add_savings_transaction(savings_id, user_id, date, amount, transaction_type, memo=None):
    """
    적금 거래내역 추가
    
    Args:
        savings_id (int): 적금 ID
        user_id (int): 사용자 ID
        date (str): 거래일자 (YYYY-MM-DD)
        amount (float): 금액
        transaction_type (str): 거래유형 ('입금', '출금' 등)
        memo (str, optional): 메모
        
    Returns:
        int or None: 추가된 거래내역 ID 또는 None (추가 실패시)
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    try:
        # 거래내역 추가
        cursor.execute(
            """
            INSERT INTO savings_transactions (
                savings_id, user_id, 날짜, 금액, 거래유형, 메모
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (savings_id, user_id, date, amount, transaction_type, memo)
        )
        
        transaction_id = cursor.lastrowid
        
        # 적금 현재 납입액 업데이트
        if transaction_type == '입금':
            cursor.execute(
                """
                UPDATE savings 
                SET 현재납입액 = 현재납입액 + ?, last_update = ?
                WHERE id = ? AND user_id = ?
                """,
                (amount, datetime.now(), savings_id, user_id)
            )
        elif transaction_type == '출금':
            cursor.execute(
                """
                UPDATE savings 
                SET 현재납입액 = 현재납입액 - ?, last_update = ?
                WHERE id = ? AND user_id = ?
                """,
                (amount, datetime.now(), savings_id, user_id)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"적금 거래내역 추가: {transaction_type}, 적금 ID: {savings_id}, 사용자: {user_id}")
        return transaction_id
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"적금 거래내역 추가 실패: {e}")
        return None

def get_savings_transactions(user_id, savings_id=None, limit=100):
    """
    적금 거래내역 조회
    
    Args:
        user_id (int): 사용자 ID
        savings_id (int, optional): 특정 적금 ID
        limit (int, optional): 최대 조회 개수
        
    Returns:
        list: 적금 거래내역 목록
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    if savings_id:
        cursor.execute(
            """
            SELECT t.id, s.이름, t.날짜, t.금액, t.거래유형, t.메모
            FROM savings_transactions t
            JOIN savings s ON t.savings_id = s.id
            WHERE t.user_id = ? AND t.savings_id = ?
            ORDER BY t.날짜 DESC
            LIMIT ?
            """,
            (user_id, savings_id, limit)
        )
    else:
        cursor.execute(
            """
            SELECT t.id, s.이름, t.날짜, t.금액, t.거래유형, t.메모
            FROM savings_transactions t
            JOIN savings s ON t.savings_id = s.id
            WHERE t.user_id = ?
            ORDER BY t.날짜 DESC
            LIMIT ?
            """,
            (user_id, limit)
        )
    
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return transactions

def update_savings_calculation(savings_id=None, user_id=None):
    """
    적금 계산 업데이트 (현재 납입액, 예상 만기금액 등)
    
    Args:
        savings_id (int, optional): 특정 적금 ID (None인 경우 모든 적금 업데이트)
        user_id (int, optional): 특정 사용자 ID (None인 경우 모든 사용자 적금 업데이트)
        
    Returns:
        int: 업데이트된 적금 수
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    # 적금 필터링 조건 설정
    query = "SELECT id, user_id, 시작일, 만기일, 월납입액, 금리, 세후금리 FROM savings"
    params = []
    
    if savings_id is not None and user_id is not None:
        query += " WHERE id = ? AND user_id = ?"
        params = [savings_id, user_id]
    elif savings_id is not None:
        query += " WHERE id = ?"
        params = [savings_id]
    elif user_id is not None:
        query += " WHERE user_id = ?"
        params = [user_id]
    
    cursor.execute(query, params)
    savings_list = cursor.fetchall()
    
    updated_count = 0
    
    for saving in savings_list:
        try:
            s_id, s_user_id = saving['id'], saving['user_id']
            start_date, end_date = saving['시작일'], saving['만기일']
            monthly_amount, interest_rate = saving['월납입액'], saving['세후금리']
            
            # 현재 납입액 계산 (거래내역 기반)
            cursor.execute(
                """
                SELECT SUM(CASE WHEN 거래유형 = '입금' THEN 금액 
                              WHEN 거래유형 = '출금' THEN -금액 
                              ELSE 0 END) 
                FROM savings_transactions
                WHERE savings_id = ?
                """,
                (s_id,)
            )
            
            current_amount_result = cursor.fetchone()
            current_amount = current_amount_result[0] if current_amount_result and current_amount_result[0] is not None else 0
            
            # 날짜 변환
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date() if isinstance(start_date, str) else start_date
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date() if isinstance(end_date, str) else end_date
            
            # 총 계약 기간 (개월)
            total_months = (end_date_obj.year - start_date_obj.year) * 12 + (end_date_obj.month - start_date_obj.month)
            
            # 예상 만기 금액 계산 (단리 가정)
            expected_amount = monthly_amount * total_months * (1 + (interest_rate/100 * total_months/24))
            
            # 업데이트
            cursor.execute(
                """
                UPDATE savings
                SET 현재납입액 = ?, 예상만기금액 = ?, last_update = ?
                WHERE id = ?
                """,
                (current_amount, expected_amount, datetime.now(), s_id)
            )
            
            updated_count += 1
        except Exception as e:
            logger.error(f"적금 계산 오류 (ID: {s_id}): {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"적금 계산 업데이트 완료: {updated_count}개 업데이트됨")
    return updated_count
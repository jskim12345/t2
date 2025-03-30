"""
적금 관련 서비스
"""
import pandas as pd
from datetime import datetime
from datetime import datetime, timedelta

try:
    from utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
try:
    from models.savings import (
        get_savings_by_user,
        get_savings_by_id,
        add_savings,
        update_savings,
        delete_savings,
        add_savings_transaction,
        get_savings_transactions,
        update_savings_calculation
    )
except ImportError:
    # 모듈이 없는 경우 더미 함수 제공
    def get_savings_by_user(user_id): return []
    def get_savings_by_id(savings_id, user_id): return None
    def add_savings(*args, **kwargs): return None
    def update_savings(*args, **kwargs): return False
    def delete_savings(*args, **kwargs): return False
    def add_savings_transaction(*args, **kwargs): return None
    def get_savings_transactions(*args, **kwargs): return []
    def update_savings_calculation(*args, **kwargs): return 0

from utils.logging import get_logger

def get_savings_summary(user_id):
    """
    적금 요약 정보 (시각화용)
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict: 적금 요약 정보
    """
    # 사용자 적금 목록
    savings_list = get_savings_by_user(user_id)
    
    if not savings_list:
        return {"total_amount": 0, "savings": []}
    
    # 총 금액 계산
    total_amount = sum(item['현재납입액'] for item in savings_list if item.get('현재납입액'))
    
    # 적금 데이터 변환
    savings_data = []
    for item in savings_list:
        # 날짜 형식 변환
        start_date = item.get('시작일')
        if isinstance(start_date, str):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                start_date = datetime.now().date()
        
        end_date = item.get('만기일')
        if isinstance(end_date, str):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                # 기본값: 1년 후
                end_date = datetime.now().date() + timedelta(days=365)
        
        savings_data.append({
            "id": item.get('id', 0),
            "name": item.get('이름', '미정'),
            "bank": item.get('은행', ''),
            "start_date": start_date,
            "end_date": end_date,
            "monthly_amount": item.get('월납입액', 0),
            "interest_rate": item.get('금리', 0),
            "current_amount": item.get('현재납입액', 0),
            "expected_amount": item.get('예상만기금액', 0)
        })
    
    return {
        "total_amount": total_amount,
        "savings": savings_data
    }

def load_savings(user_id):
    """
    적금 목록 로드
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        pandas.DataFrame: 적금 목록
    """
    if user_id is None:
        return pd.DataFrame()  # 로그인하지 않은 경우 빈 데이터프레임 반환
    
    # 사용자 적금 목록 조회
    savings = get_savings_by_user(user_id)
    
    if not savings:
        return pd.DataFrame()  # 데이터가 없는 경우 빈 데이터프레임 반환
    
    # 데이터프레임 변환
    df = pd.DataFrame(savings)
    
    # UI 표시용 컬럼명 변경 및 선택
    try:
        # 필요한 컬럼만 선택
        df = df[[
            'id', '이름', '은행', '계좌번호', '시작일', '만기일', '월납입액', 
            '금리', '세후금리', '현재납입액', '예상만기금액', '적금유형', 'last_update'
        ]]
        
        # 컬럼명 포맷팅
        df.columns = [
            "ID", "적금명", "은행명", "계좌번호", "시작일", "만기일", "월납입액", 
            "금리(%)", "세후금리(%)", "현재납입액", "예상만기금액", "적금유형", "최종업데이트"
        ]
        
        # 숫자 포맷팅
        for col in ["월납입액", "현재납입액", "예상만기금액"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{x:,.0f}원" if pd.notnull(x) else "")
        
        for col in ["금리(%)", "세후금리(%)"]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
        
        # 날짜 포맷팅
        for col in ["시작일", "만기일"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
        
        df["최종업데이트"] = pd.to_datetime(df["최종업데이트"]).dt.strftime('%Y-%m-%d %H:%M')
    except Exception as e:
        logger.error(f"적금 데이터 변환 오류: {e}")
        return pd.DataFrame()
    
    return df

def create_savings(user_id, name, bank, account_number, start_date, end_date, monthly_amount, interest_rate, savings_type):
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
        pandas.DataFrame: 업데이트된 적금 목록
    """
    try:
        # 적금 추가
        add_savings(
            user_id, name, bank, account_number, start_date, end_date, 
            monthly_amount, interest_rate, savings_type
        )
        
        logger.info(f"적금 추가: {name}, 사용자: {user_id}")
        
        # 업데이트된 적금 목록 반환
        return load_savings(user_id)
    except Exception as e:
        logger.error(f"적금 추가 오류: {e}")
        return load_savings(user_id)

def edit_savings(user_id, savings_id, **kwargs):
    """
    적금 정보 수정
    
    Args:
        user_id (int): 사용자 ID
        savings_id (int): 적금 ID
        **kwargs: 수정할 필드들 (name, bank, account_number 등)
        
    Returns:
        pandas.DataFrame: 업데이트된 적금 목록
    """
    try:
        # 적금 정보 업데이트
        update_savings(savings_id, user_id, **kwargs)
        
        # 적금 계산 업데이트 (월납입액, 금리 등이 변경된 경우)
        update_savings_calculation(savings_id, user_id)
        
        logger.info(f"적금 수정: ID {savings_id}, 사용자: {user_id}")
        
        # 업데이트된 적금 목록 반환
        return load_savings(user_id)
    except Exception as e:
        logger.error(f"적금 수정 오류: {e}")
        return load_savings(user_id)

def remove_savings(user_id, savings_id):
    """
    적금 삭제
    
    Args:
        user_id (int): 사용자 ID
        savings_id (int): 적금 ID
        
    Returns:
        tuple: (결과 메시지, 업데이트된 적금 목록)
    """
    try:
        # 적금 존재 확인
        savings = get_savings_by_id(savings_id, user_id)
        
        if not savings:
            return "적금을 찾을 수 없습니다.", load_savings(user_id)
        
        # 적금 삭제
        delete_savings(savings_id, user_id)
        
        logger.info(f"적금 삭제: ID {savings_id}, 사용자: {user_id}")
        return "적금이 삭제되었습니다.", load_savings(user_id)
    except Exception as e:
        logger.error(f"적금 삭제 오류: {e}")
        return f"적금 삭제 중 오류가 발생했습니다: {e}", load_savings(user_id)

def add_savings_deposit(user_id, savings_id, date, amount, memo=None):
    """
    적금 입금 기록 추가
    
    Args:
        user_id (int): 사용자 ID
        savings_id (int): 적금 ID
        date (str): 입금일자 (YYYY-MM-DD)
        amount (float): 입금액
        memo (str, optional): 메모
        
    Returns:
        pandas.DataFrame: 업데이트된 적금 거래내역
    """
    try:
        # 적금 존재 확인
        savings = get_savings_by_id(savings_id, user_id)
        
        if not savings:
            logger.warning(f"적금 입금 실패 (적금 없음): ID {savings_id}, 사용자: {user_id}")
            return pd.DataFrame()
        
        # 적금 거래내역 추가
        add_savings_transaction(savings_id, user_id, date, amount, '입금', memo)
        
        # 적금 계산 업데이트
        update_savings_calculation(savings_id, user_id)
        
        logger.info(f"적금 입금 기록 추가: ID {savings_id}, 금액: {amount}, 사용자: {user_id}")
        
        # 업데이트된 거래내역 반환
        return load_savings_transactions(user_id, savings_id)
    except Exception as e:
        logger.error(f"적금 입금 기록 추가 오류: {e}")
        return pd.DataFrame()

def add_savings_withdrawal(user_id, savings_id, date, amount, memo=None):
    """
    적금 출금 기록 추가
    
    Args:
        user_id (int): 사용자 ID
        savings_id (int): 적금 ID
        date (str): 출금일자 (YYYY-MM-DD)
        amount (float): 출금액
        memo (str, optional): 메모
        
    Returns:
        pandas.DataFrame: 업데이트된 적금 거래내역
    """
    try:
        # 적금 존재 확인
        savings = get_savings_by_id(savings_id, user_id)
        
        if not savings:
            logger.warning(f"적금 출금 실패 (적금 없음): ID {savings_id}, 사용자: {user_id}")
            return pd.DataFrame()
        
        # 출금 가능 금액 확인
        if amount > savings['현재납입액']:
            logger.warning(f"적금 출금 실패 (잔액 부족): ID {savings_id}, 사용자: {user_id}")
            return pd.DataFrame()
        
        # 적금 거래내역 추가
        add_savings_transaction(savings_id, user_id, date, amount, '출금', memo)
        
        # 적금 계산 업데이트
        update_savings_calculation(savings_id, user_id)
        
        logger.info(f"적금 출금 기록 추가: ID {savings_id}, 금액: {amount}, 사용자: {user_id}")
        
        # 업데이트된 거래내역 반환
        return load_savings_transactions(user_id, savings_id)
    except Exception as e:
        logger.error(f"적금 출금 기록 추가 오류: {e}")
        return pd.DataFrame()

def load_savings_transactions(user_id, savings_id=None, limit=100):
    """
    적금 거래내역 로드
    
    Args:
        user_id (int): 사용자 ID
        savings_id (int, optional): 특정 적금 ID
        limit (int, optional): 최대 조회 개수
        
    Returns:
        pandas.DataFrame: 적금 거래내역
    """
    # 거래내역 조회
    transactions = get_savings_transactions(user_id, savings_id, limit)
    
    if not transactions:
        return pd.DataFrame()
    
    # 데이터프레임 변환
    df = pd.DataFrame(transactions)
    
    # 컬럼명 변경
    df.columns = ["ID", "적금명", "날짜", "금액", "거래유형", "메모"]
    
    # 숫자 포맷팅
    df["금액"] = df["금액"].apply(lambda x: f"{x:,.0f}원" if pd.notnull(x) else "")
    
    # 날짜 포맷팅
    df["날짜"] = pd.to_datetime(df["날짜"]).dt.strftime('%Y-%m-%d')
    
    # 메모가 없는 경우 처리
    df["메모"] = df["메모"].fillna("-")
    
    return df

def update_all_savings():
    """
    모든 적금 계산 업데이트
    
    Returns:
        int: 업데이트된 적금 수
    """
    return update_savings_calculation()

def get_savings_summary(user_id):
    """
    적금 요약 정보 (시각화용)
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict: 적금 요약 정보
    """
    # 사용자 적금 목록
    savings_list = get_savings_by_user(user_id)
    
    if not savings_list:
        return {"total_amount": 0, "savings": []}
    
    # 총 금액 계산
    total_amount = sum(item['현재납입액'] for item in savings_list if item['현재납입액'])
    
    # 적금 데이터 변환
    savings_data = []
    for item in savings_list:
        # 날짜 형식 변환
        start_date = item['시작일']
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        
        end_date = item['만기일']
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        savings_data.append({
            "id": item['id'],
            "name": item['이름'],
            "bank": item['은행'],
            "start_date": start_date,
            "end_date": end_date,
            "monthly_amount": item['월납입액'],
            "interest_rate": item['금리'],
            "current_amount": item['현재납입액'],
            "expected_amount": item['예상만기금액']
        })
    
    return {
        "total_amount": total_amount,
        "savings": savings_data
    }
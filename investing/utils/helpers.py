"""
유틸리티 헬퍼 함수 모음
"""
import os
import re
from datetime import datetime, timedelta

def ensure_dir(directory):
    """
    디렉토리가 없으면 생성
    
    Args:
        directory (str): 생성할 디렉토리 경로
    """
    if not os.path.exists(directory):
        os.makedirs(directory)

def parse_date(date_str, default=None):
    """
    다양한 형식의 날짜 문자열을 파싱하여 datetime 객체로 변환
    
    Args:
        date_str (str): 날짜 문자열
        default (datetime, optional): 파싱 실패시 반환할 기본값
        
    Returns:
        datetime or default: 변환된 날짜 또는 기본값
    """
    if not date_str:
        return default
    
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y%m%d",
        "%d-%m-%Y",
        "%m/%d/%Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return default

def format_number(number, decimal_places=0, currency_symbol=""):
    """
    숫자를 천 단위 구분자를 포함한 문자열로 변환
    
    Args:
        number (int or float): 변환할 숫자
        decimal_places (int, optional): 소수점 자리수
        currency_symbol (str, optional): 통화 기호
        
    Returns:
        str: 포맷된 숫자 문자열
    """
    if number is None:
        return ""
    
    format_str = f"{currency_symbol}{{:,.{decimal_places}f}}"
    return format_str.format(number)

def calculate_interest(principal, rate, years, compound_freq=1):
    """
    이자 계산 (복리)
    
    Args:
        principal (float): 원금
        rate (float): 연이율 (%, 예: 3.5)
        years (float): 기간 (년)
        compound_freq (int, optional): 복리 계산 주기 (연간 횟수)
        
    Returns:
        float: 원리금 합계
    """
    rate_decimal = rate / 100
    periods = years * compound_freq
    
    # 복리 계산 공식: P * (1 + r/n)^(n*t)
    result = principal * (1 + rate_decimal / compound_freq) ** periods
    
    return result

def calculate_loan_payment(principal, rate, years):
    """
    대출 월 상환금 계산
    
    Args:
        principal (float): 대출 원금
        rate (float): 연이율 (%, 예: 3.5)
        years (float): 대출 기간 (년)
        
    Returns:
        float: 월 상환금
    """
    rate_decimal = rate / 100 / 12  # 월 이율
    num_payments = years * 12  # 총 상환 횟수
    
    # 원리금균등상환 공식: P * r * (1+r)^n / ((1+r)^n - 1)
    if rate_decimal == 0:
        return principal / num_payments
    
    monthly_payment = principal * rate_decimal * (1 + rate_decimal) ** num_payments / ((1 + rate_decimal) ** num_payments - 1)
    
    return monthly_payment

def validate_account_number(account_number, bank_code=None):
    """
    계좌번호 유효성 검사
    
    Args:
        account_number (str): 계좌번호
        bank_code (str, optional): 은행 코드
        
    Returns:
        bool: 유효성 여부
    """
    # 숫자와 하이픈만 남기고 제거
    clean_number = re.sub(r'[^0-9-]', '', account_number)
    
    # 최소 길이 확인
    if len(clean_number.replace('-', '')) < 10:
        return False
    
    # 기본적인 형식 확인
    if not re.match(r'^[\d-]+$', clean_number):
        return False
    
    # 은행별 계좌번호 패턴 확인 (예시)
    if bank_code:
        # 국민은행, 신한은행 등 은행별 패턴 확인 로직 추가 가능
        pass
    
    return True

def get_age_group(birth_date):
    """
    생년월일로 연령대 계산
    
    Args:
        birth_date (datetime): 생년월일
        
    Returns:
        str: 연령대 (예: '20대', '30대')
    """
    if not birth_date:
        return None
    
    today = datetime.now()
    age = today.year - birth_date.year
    
    # 생일이 지나지 않았으면 1살 빼기
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    # 연령대 계산 (10으로 나눈 몫 * 10)
    age_group = (age // 10) * 10
    
    return f"{age_group}대"
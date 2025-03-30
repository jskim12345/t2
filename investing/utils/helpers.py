"""
유틸리티 헬퍼 함수 모음 - 고급 유틸리티 기능 추가
"""
import os
import re
import json
import csv
import random
import string
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP

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
        "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    return default

def format_number(number, decimal_places=0, currency_symbol="", use_thousands_separator=True):
    """
    숫자를 천 단위 구분자를 포함한 문자열로 변환
    
    Args:
        number (int or float): 변환할 숫자
        decimal_places (int, optional): 소수점 자리수
        currency_symbol (str, optional): 통화 기호
        use_thousands_separator (bool, optional): 천 단위 구분자 사용 여부
        
    Returns:
        str: 포맷된 숫자 문자열
    """
    if number is None:
        return ""
    
    # Decimal로 변환하여 정확한 반올림
    decimal_num = Decimal(str(number)).quantize(
        Decimal('0.1') ** decimal_places, 
        rounding=ROUND_HALF_UP
    )
    
    if use_thousands_separator:
        # 천 단위 구분자 사용
        parts = str(decimal_num).split('.')
        integer_part = parts[0]
        
        # 음수 처리
        if integer_part.startswith('-'):
            sign = '-'
            integer_part = integer_part[1:]
        else:
            sign = ''
        
        # 천 단위 구분자 추가
        formatted_integer = ''
        for i, char in enumerate(reversed(integer_part)):
            if i > 0 and i % 3 == 0:
                formatted_integer = ',' + formatted_integer
            formatted_integer = char + formatted_integer
        
        # 부호 복원
        formatted_integer = sign + formatted_integer
        
        # 소수점 처리
        if len(parts) > 1:
            result = f"{currency_symbol}{formatted_integer}.{parts[1]}"
        else:
            result = f"{currency_symbol}{formatted_integer}"
    else:
        # 천 단위 구분자 없이 포맷
        result = f"{currency_symbol}{decimal_num}"
    
    return result

def calculate_interest(principal, rate, years, compound_freq=1, tax_rate=0.154):
    """
    이자 계산 (복리)
    
    Args:
        principal (float): 원금
        rate (float): 연이율 (%, 예: 3.5)
        years (float): 기간 (년)
        compound_freq (int, optional): 복리 계산 주기 (연간 횟수)
        tax_rate (float, optional): 이자소득세율 (기본값: 15.4%)
        
    Returns:
        dict: 계산 결과 (세전 금액, 세후 금액, 이자 등)
    """
    rate_decimal = rate / 100
    periods = years * compound_freq
    
    # 세전 복리 계산 공식: P * (1 + r/n)^(n*t)
    pre_tax_result = principal * (1 + rate_decimal / compound_freq) ** periods
    pre_tax_interest = pre_tax_result - principal
    
    # 세금 계산
    tax = pre_tax_interest * tax_rate
    
    # 세후 금액
    post_tax_result = pre_tax_result - tax
    post_tax_interest = pre_tax_interest - tax
    
    return {
        "principal": principal,
        "pre_tax_result": pre_tax_result,
        "pre_tax_interest": pre_tax_interest,
        "tax": tax,
        "post_tax_result": post_tax_result,
        "post_tax_interest": post_tax_interest,
        "effective_rate": (post_tax_result / principal) ** (1 / years) - 1
    }

def calculate_savings_periodic(monthly_amount, rate, months, compound_freq=12, tax_rate=0.154):
    """
    적금 계산 (정기납입식)
    
    Args:
        monthly_amount (float): 월 납입액
        rate (float): 연이율 (%, 예: 3.5)
        months (int): 납입 기간 (월)
        compound_freq (int, optional): 복리 계산 주기 (연간 횟수)
        tax_rate (float, optional): 이자소득세율 (기본값: 15.4%)
        
    Returns:
        dict: 계산 결과 (세전 금액, 세후 금액, 이자 등)
    """
    rate_decimal = rate / 100 / 12  # 월 이율
    
    # 원금 합계
    principal = monthly_amount * months
    
    # 복리 적용 적금 계산
    # 복리 적금 공식: PMT * (((1 + r)^n - 1) / r)
    if rate_decimal > 0:
        future_value = monthly_amount * ((1 + rate_decimal) ** months - 1) / rate_decimal
    else:
        future_value = principal
    
    pre_tax_interest = future_value - principal
    
    # 세금 계산
    tax = pre_tax_interest * tax_rate
    
    # 세후 금액
    post_tax_result = future_value - tax
    post_tax_interest = pre_tax_interest - tax
    
    return {
        "principal": principal,
        "pre_tax_result": future_value,
        "pre_tax_interest": pre_tax_interest,
        "tax": tax,
        "post_tax_result": post_tax_result,
        "post_tax_interest": post_tax_interest
    }

def calculate_loan_payment(principal, rate, years, payment_freq=12):
    """
    대출 상환금 계산
    
    Args:
        principal (float): 대출 원금
        rate (float): 연이율 (%, 예: 3.5)
        years (float): 대출 기간 (년)
        payment_freq (int, optional): 상환 주기 (연간 횟수, 기본값: 12=월납)
        
    Returns:
        dict: 계산 결과 (월 상환금, 총 상환금, 총 이자 등)
    """
    rate_decimal = rate / 100 / payment_freq  # 상환 주기별 이율
    num_payments = years * payment_freq  # 총 상환 횟수
    
    # 원리금균등상환 공식: P * r * (1+r)^n / ((1+r)^n - 1)
    if rate_decimal == 0:
        payment = principal / num_payments
    else:
        payment = principal * rate_decimal * (1 + rate_decimal) ** num_payments / ((1 + rate_decimal) ** num_payments - 1)
    
    # 총 상환금액
    total_payment = payment * num_payments
    
    # 총 이자
    total_interest = total_payment - principal
    
    # 상환 계획 데이터
    amortization = []
    remaining = principal
    
    for i in range(1, int(num_payments) + 1):
        interest_payment = remaining * rate_decimal
        principal_payment = payment - interest_payment
        remaining -= principal_payment
        
        # 마지막 상환의 경우 남은 잔액 정리
        if i == int(num_payments):
            principal_payment += remaining
            remaining = 0
        
        amortization.append({
            "payment_number": i,
            "payment": payment,
            "principal": principal_payment,
            "interest": interest_payment,
            "remaining": max(0, remaining)
        })
    
    return {
        "payment": payment,
        "num_payments": num_payments,
        "total_payment": total_payment,
        "total_interest": total_interest,
        "amortization": amortization
    }

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
    
    # 은행별 계좌번호 패턴 확인
    if bank_code:
        bank_patterns = {
            '국민': r'^\d{6}-\d{2}-\d{6}$',
            '신한': r'^\d{3}-\d{3}-\d{6}$',
            '우리': r'^\d{4}-\d{3}-\d{6}$',
            '하나': r'^\d{3}-\d{6}-\d{5}$',
            'IBK기업': r'^\d{3}-\d{6}-\d{2}-\d{3}$',
            '농협': r'^\d{3}-\d{4}-\d{4}-\d{2}$',
            'SC제일': r'^\d{3}-\d{2}-\d{6}$'
        }
        
        if bank_code in bank_patterns:
            pattern = bank_patterns[bank_code]
            
            # 하이픈이 있는 형식으로 변환
            digits = clean_number.replace('-', '')
            if bank_code == '국민':
                formatted = f"{digits[:6]}-{digits[6:8]}-{digits[8:]}"
            elif bank_code == '신한':
                formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
            elif bank_code == '우리':
                formatted = f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
            elif bank_code == '하나':
                formatted = f"{digits[:3]}-{digits[3:9]}-{digits[9:]}"
            elif bank_code == 'IBK기업':
                formatted = f"{digits[:3]}-{digits[3:9]}-{digits[9:11]}-{digits[11:]}"
            elif bank_code == '농협':
                formatted = f"{digits[:3]}-{digits[3:7]}-{digits[7:11]}-{digits[11:]}"
            elif bank_code == 'SC제일':
                formatted = f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
            
            return bool(re.match(pattern, formatted))
    
    return True

def get_age_group(birth_date):
    """
    생년월일로 연령대 계산
    
    Args:
        birth_date (datetime or date or str): 생년월일
        
    Returns:
        str: 연령대 (예: '20대', '30대')
    """
    if not birth_date:
        return None
    
    # 문자열 날짜 처리
    if isinstance(birth_date, str):
        birth_date = parse_date(birth_date)
        if not birth_date:
            return None
    
    # datetime을 date로 변환
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()
    
    today = date.today()
    age = today.year - birth_date.year
    
    # 생일이 지나지 않았으면 1살 빼기
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1
    
    # 연령대 계산 (10으로 나눈 몫 * 10)
    age_group = (age // 10) * 10
    
    return f"{age_group}대"

def generate_random_string(length=8, include_digits=True, include_special=False):
    """
    랜덤 문자열 생성
    
    Args:
        length (int): 문자열 길이
        include_digits (bool): 숫자 포함 여부
        include_special (bool): 특수 문자 포함 여부
        
    Returns:
        str: 생성된 랜덤 문자열
    """
    chars = string.ascii_letters
    
    if include_digits:
        chars += string.digits
    
    if include_special:
        chars += string.punctuation
    
    return ''.join(random.choice(chars) for _ in range(length))

def export_to_csv(data, file_path, headers=None, encoding='utf-8'):
    """
    데이터를 CSV 파일로 내보내기
    
    Args:
        data (list): 내보낼 데이터 (딕셔너리 리스트 또는 중첩 리스트)
        file_path (str): 저장할 파일 경로
        headers (list, optional): 열 헤더 목록
        encoding (str, optional): 파일 인코딩
        
    Returns:
        bool: 성공 여부
    """
    try:
        with open(file_path, 'w', newline='', encoding=encoding) as csvfile:
            if data and isinstance(data[0], dict):
                # 딕셔너리 리스트인 경우
                if not headers:
                    headers = list(data[0].keys())
                
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(data)
            else:
                # 중첩 리스트인 경우
                writer = csv.writer(csvfile)
                
                if headers:
                    writer.writerow(headers)
                
                writer.writerows(data)
        
        return True
    except Exception as e:
        print(f"CSV 내보내기 오류: {e}")
        return False

def import_from_csv(file_path, as_dict=True, encoding='utf-8'):
    """
    CSV 파일에서 데이터 가져오기
    
    Args:
        file_path (str): 가져올 파일 경로
        as_dict (bool): 딕셔너리 리스트로 반환 여부
        encoding (str): 파일 인코딩
        
    Returns:
        list: 가져온 데이터
    """
    try:
        with open(file_path, 'r', newline='', encoding=encoding) as csvfile:
            if as_dict:
                reader = csv.DictReader(csvfile)
                return list(reader)
            else:
                reader = csv.reader(csvfile)
                return list(reader)
    except Exception as e:
        print(f"CSV 가져오기 오류: {e}")
        return []

def calculate_portfolio_metrics(portfolio_data):
    """
    포트폴리오 성과 지표 계산
    
    Args:
        portfolio_data (dict): 포트폴리오 데이터
        
    Returns:
        dict: 계산된 지표
    """
    # 여기서는 기본적인 지표만 계산, 실제로는 더 복잡한 계산 가능
    metrics = {
        "total_value": 0,
        "total_cost": 0,
        "total_gain_loss": 0,
        "total_gain_loss_percent": 0,
        "dividend_yield": 0
    }
    
    if not portfolio_data or "items" not in portfolio_data:
        return metrics
    
    total_value = 0
    total_cost = 0
    total_dividend = 0
    
    for item in portfolio_data["items"]:
        quantity = item.get("quantity", 0)
        current_price = item.get("current_price", 0)
        avg_price = item.get("avg_price", 0)
        dividend = item.get("dividend", 0)
        
        value = quantity * current_price
        cost = quantity * avg_price
        
        total_value += value
        total_cost += cost
        total_dividend += dividend
    
    if total_cost > 0:
        total_gain_loss = total_value - total_cost
        total_gain_loss_percent = (total_gain_loss / total_cost) * 100
        dividend_yield = (total_dividend / total_cost) * 100
    else:
        total_gain_loss = 0
        total_gain_loss_percent = 0
        dividend_yield = 0
    
    metrics["total_value"] = total_value
    metrics["total_cost"] = total_cost
    metrics["total_gain_loss"] = total_gain_loss
    metrics["total_gain_loss_percent"] = total_gain_loss_percent
    metrics["dividend_yield"] = dividend_yield
    
    return metrics

def get_korean_age(birth_date):
    """
    한국 나이 계산
    
    Args:
        birth_date (datetime or date or str): 생년월일
        
    Returns:
        int: 한국 나이
    """
    if not birth_date:
        return None
    
    # 문자열 날짜 처리
    if isinstance(birth_date, str):
        birth_date = parse_date(birth_date)
        if not birth_date:
            return None
    
    # datetime을 date로 변환
    if isinstance(birth_date, datetime):
        birth_date = birth_date.date()
    
    today = date.today()
    
    # 한국 나이 계산 (태어난 해부터 1살, 연도가 바뀔 때마다 1살씩 증가)
    korean_age = today.year - birth_date.year + 1
    
    return korean_age

def encrypt_data(data, key):
    """
    간단한 데이터 암호화 (실제 서비스에서는 더 강력한 암호화 사용 필요)
    
    Args:
        data (str): 암호화할 데이터
        key (str): 암호화 키
        
    Returns:
        str: 암호화된 데이터 (base64 인코딩)
    """
    import base64
    
    # 실제 서비스에서는 더 안전한 암호화 방식 사용 필요
    # 여기서는 간단한 XOR 암호화 + base64 인코딩으로 대체
    
    # 키 확장
    key_extended = key * (len(data) // len(key) + 1)
    key_extended = key_extended[:len(data)]
    
    # XOR 암호화
    encrypted = ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(data, key_extended))
    
    # Base64 인코딩
    encoded = base64.b64encode(encrypted.encode()).decode()
    
    return encoded

def decrypt_data(encrypted_data, key):
    """
    간단한 데이터 복호화
    
    Args:
        encrypted_data (str): 암호화된 데이터 (base64 인코딩)
        key (str): 암호화 키
        
    Returns:
        str: 복호화된 데이터
    """
    import base64
    
    try:
        # Base64 디코딩
        decoded = base64.b64decode(encrypted_data).decode()
        
        # 키 확장
        key_extended = key * (len(decoded) // len(key) + 1)
        key_extended = key_extended[:len(decoded)]
        
        # XOR 복호화 (XOR은 동일한 키로 두 번 적용하면 원본이 나옴)
        decrypted = ''.join(chr(ord(a) ^ ord(b)) for a, b in zip(decoded, key_extended))
        
        return decrypted
    except Exception as e:
        print(f"복호화 오류: {e}")
        return None

def json_serialize(obj):
    """
    JSON 직렬화가 불가능한 객체 처리를 위한 사용자 정의 JSON 직렬화
    
    Args:
        obj: 직렬화할 객체
        
    Returns:
        직렬화 가능한 형태로 변환된 객체
    """
    # datetime 객체 처리
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    
    # Decimal 객체 처리
    if isinstance(obj, Decimal):
        return float(obj)
    
    # 기타 객체 처리
    try:
        return str(obj)
    except:
        return None

def save_to_json(data, file_path, encoding='utf-8', indent=2):
    """
    데이터를 JSON 파일로 저장
    
    Args:
        data: 저장할 데이터
        file_path (str): 저장할 파일 경로
        encoding (str): 파일 인코딩
        indent (int): JSON 들여쓰기 크기
        
    Returns:
        bool: 성공 여부
    """
    try:
        with open(file_path, 'w', encoding=encoding) as f:
            json.dump(data, f, default=json_serialize, ensure_ascii=False, indent=indent)
        return True
    except Exception as e:
        print(f"JSON 저장 오류: {e}")
        return False

def load_from_json(file_path, encoding='utf-8'):
    """
    JSON 파일에서 데이터 로드
    
    Args:
        file_path (str): 로드할 파일 경로
        encoding (str): 파일 인코딩
        
    Returns:
        로드된 데이터 또는 None (실패 시)
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return json.load(f)
    except Exception as e:
        print(f"JSON 로드 오류: {e}")
        return None

def get_remaining_days(target_date):
    """
    목표 날짜까지 남은 일수 계산
    
    Args:
        target_date (datetime or date or str): 목표 날짜
        
    Returns:
        int: 남은 일수
    """
    if not target_date:
        return None
    
    # 문자열 날짜 처리
    if isinstance(target_date, str):
        target_date = parse_date(target_date)
        if not target_date:
            return None
    
    # datetime을 date로 변환
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    
    today = date.today()
    
    # 남은 일수 계산
    delta = target_date - today
    
    return delta.days
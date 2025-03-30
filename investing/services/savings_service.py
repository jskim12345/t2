"""
적금 관련 서비스 - 고급 적금 계산 및 목표 관리 기능 추가
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import re
import json

from utils.logging import get_logger, log_exception
try:
    from utils.helpers import (
        parse_date, 
        format_number, 
        calculate_interest, 
        calculate_savings_periodic,
        get_remaining_days
    )
except ImportError:
    from datetime import datetime
    def parse_date(date_str, default=None): return default
    def format_number(number, decimal_places=0): return str(number)
    def calculate_interest(principal, rate, years): return principal * (1 + rate/100*years)
    def calculate_savings_periodic(monthly_amount, rate, months): 
        return {"post_tax_result": monthly_amount * months * (1 + rate/100/12*months/2)}
    def get_remaining_days(target_date): 
        return (target_date - datetime.now().date()).days if isinstance(target_date, date) else 0

logger = get_logger(__name__)

try:
    from models.database import get_db_connection
except ImportError:
    logger.error("models.database 모듈을 불러올 수 없습니다.")
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
    
    try:
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
            
            # 남은 날짜 계산
            days_left = get_remaining_days(end_date)
            
            # 목표 달성률 계산
            target_amount = item.get('목표금액', 0)
            current_amount = item.get('현재납입액', 0)
            
            if target_amount and target_amount > 0:
                achievement_rate = min(100, (current_amount / target_amount) * 100)
            else:
                achievement_rate = 0
            
            savings_data.append({
                "id": item.get('id', 0),
                "name": item.get('이름', '미정'),
                "bank": item.get('은행', ''),
                "start_date": start_date,
                "end_date": end_date,
                "days_left": days_left,
                "monthly_amount": item.get('월납입액', 0),
                "interest_rate": item.get('금리', 0),
                "current_amount": item.get('현재납입액', 0),
                "expected_amount": item.get('예상만기금액', 0),
                "target_amount": target_amount,
                "achievement_rate": achievement_rate,
                "savings_type": item.get('적금유형', '정기적금')
            })
        
        # 적금 타입별 합계
        savings_by_type = {}
        for item in savings_list:
            savings_type = item.get('적금유형', '정기적금')
            amount = item.get('현재납입액', 0)
            
            if savings_type in savings_by_type:
                savings_by_type[savings_type] += amount
            else:
                savings_by_type[savings_type] = amount
        
        # 만기일 기준 정렬 (가까운 순)
        savings_data.sort(key=lambda x: x['days_left'])
        
        # 은행별 합계
        savings_by_bank = {}
        for item in savings_list:
            bank = item.get('은행', '기타')
            amount = item.get('현재납입액', 0)
            
            if bank in savings_by_bank:
                savings_by_bank[bank] += amount
            else:
                savings_by_bank[bank] = amount
        
        # 데이터 요약
        return {
            "total_amount": total_amount,
            "savings": savings_data,
            "by_type": savings_by_type,
            "by_bank": savings_by_bank
        }
    except Exception as e:
        log_exception(logger, e, {"context": "적금 요약 정보 계산"})
        return {"total_amount": 0, "savings": []}

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
    
    try:
        # 사용자 적금 목록 조회
        savings = get_savings_by_user(user_id)
        
        if not savings:
            return pd.DataFrame()  # 데이터가 없는 경우 빈 데이터프레임 반환
        
        # 데이터프레임 변환
        df = pd.DataFrame(savings)
        
        # UI 표시용 컬럼명 변경 및 선택
        try:
            # 필요한 컬럼만 선택
            columns_to_display = [
                'id', '이름', '은행', '계좌번호', '시작일', '만기일', '월납입액', 
                '금리', '세후금리', '현재납입액', '예상만기금액', '적금유형', 
                '금리유형', '목표금액', '목표달성률', '자동이체여부', 'last_update'
            ]
            
            # 존재하는 컬럼만 선택
            available_columns = [col for col in columns_to_display if col in df.columns]
            df = df[available_columns]
            
            # 컬럼명 매핑
            column_mapping = {
                'id': "ID", 
                '이름': "적금명", 
                '은행': "은행명", 
                '계좌번호': "계좌번호", 
                '시작일': "시작일", 
                '만기일': "만기일", 
                '월납입액': "월납입액", 
                '금리': "금리(%)", 
                '세후금리': "세후금리(%)", 
                '현재납입액': "현재납입액", 
                '예상만기금액': "예상만기금액", 
                '적금유형': "적금유형",
                '금리유형': "금리유형",
                '목표금액': "목표금액",
                '목표달성률': "목표달성률(%)",
                '자동이체여부': "자동이체",
                'last_update': "최종업데이트"
            }
            
            # 사용 가능한 키와 값만으로 매핑 적용
            available_mapping = {k: v for k, v in column_mapping.items() if k in available_columns}
            df.rename(columns=available_mapping, inplace=True)
            
            # 남은 일수 계산 추가
            try:
                today = datetime.now().date()
                df["남은일수"] = pd.to_datetime(df["만기일"]).apply(
                    lambda x: max(0, (x.date() - today).days)
                )
            except:
                # 예외 발생 시 남은 일수 열 추가하지 않음
                pass
            
            # 숫자 포맷팅
            for col in ["월납입액", "현재납입액", "예상만기금액", "목표금액"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"{x:,.0f}원" if pd.notnull(x) else "")
            
            for col in ["금리(%)", "세후금리(%)", "목표달성률(%)"]:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "")
            
            # 날짜 포맷팅
            for col in ["시작일", "만기일"]:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
            
            if "최종업데이트" in df.columns:
                df["최종업데이트"] = pd.to_datetime(df["최종업데이트"]).dt.strftime('%Y-%m-%d %H:%M')
            
            # 자동이체 포맷팅
            if "자동이체" in df.columns:
                df["자동이체"] = df["자동이체"].apply(lambda x: "예" if x else "아니오")
        except Exception as e:
            log_exception(logger, e, {"context": "적금 데이터 변환"})
            return pd.DataFrame()
        
        return df
    except Exception as e:
        log_exception(logger, e, {"context": "적금 데이터 로드"})
        return pd.DataFrame()

def create_savings(user_id, name, bank, account_number, start_date, end_date, 
                  monthly_amount, interest_rate, savings_type, 
                  interest_type='단리', target_amount=None, auto_transfer=False, memo=None):
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
        interest_type (str, optional): 금리 유형 ('단리', '복리')
        target_amount (float, optional): 목표 금액
        auto_transfer (bool, optional): 자동이체 여부
        memo
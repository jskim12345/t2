"""
시장 데이터 서비스 (주가, 환율 등)
"""
import threading
import time
import schedule
from datetime import datetime, timedelta
import requests
import json
try:
    import yfinance as yf
    import pykrx.stock as stock
except ImportError:
    # 모듈이 설치되지 않은 경우 대체 기능
    yf = None
    stock = None

from utils.logging import get_logger

logger = get_logger(__name__)

def get_krx_stock_price(ticker):
    """
    KRX에서 한국 주식 현재가 조회
    
    Args:
        ticker (str): 종목코드
        
    Returns:
        float or None: 현재가 또는 None (조회 실패시)
    """
    if not stock:
        logger.warning("pykrx 모듈이 설치되어 있지 않습니다.")
        return None
        
    try:
        # 오늘 날짜
        today = datetime.now().strftime("%Y%m%d")
        
        # 최근 30일 범위 설정 (충분한 거래일을 포함하기 위해)
        fromdate = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        
        # 최근 30일간의 OHLCV 데이터 가져오기
        df = stock.get_market_ohlcv_by_date(fromdate=fromdate, todate=today, ticker=ticker)
        
        if not df.empty:
            # 가장 최근 데이터 반환
            return df.iloc[-1]['종가']
        else:
            logger.warning(f"종목 {ticker}에 대한 데이터를 찾을 수 없습니다.")
            return None
    except Exception as e:
        logger.error(f"KRX 데이터 가져오기 오류: {e}")
        return None

def get_international_stock_price(ticker, country=None):
    """
    Yahoo Finance에서 해외 주식 현재가 조회
    
    Args:
        ticker (str): 종목코드
        country (str, optional): 국가
        
    Returns:
        float or None: 현재가 또는 None (조회 실패시)
    """
    if not yf:
        logger.warning("yfinance 모듈이 설치되어 있지 않습니다.")
        return None
        
    try:
        stock_data = yf.Ticker(ticker)
        # 최근 5일간의 데이터를 가져옴 (주말이나 공휴일 고려)
        history = stock_data.history(period="5d")
        if not history.empty:
            return history['Close'].iloc[-1]
        else:
            logger.warning(f"종목 {ticker}에 대한 데이터를 찾을 수 없습니다.")
            return None
    except Exception as e:
        logger.error(f"Yahoo Finance 데이터 가져오기 오류: {e}")
        return None

def get_exchange_rate(from_currency, to_currency):
    """
    환율 정보 조회
    
    Args:
        from_currency (str): 기준 통화 (예: 'USD')
        to_currency (str): 목표 통화 (예: 'KRW')
        
    Returns:
        float or None: 환율 또는 None (조회 실패시)
    """
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        response = requests.get(url)
        data = json.loads(response.text)
        return data["rates"][to_currency]
    except Exception as e:
        logger.error(f"환율 정보 가져오기 오류 ({from_currency}->{to_currency}): {e}")
        # 실패시 대체 환율 값 반환 (예: 1 USD = 약 1,350 KRW)
        if from_currency == 'USD' and to_currency == 'KRW':
            return 1350
        return None

def update_prices_job():
    """
    모든 종목 가격 업데이트 작업 (스케줄러에서 호출)
    """
    logger.info("자동 가격 업데이트 작업 시작")
    
    from services.portfolio_service import update_all_prices
    from services.savings_service import update_savings_calculation
    
    try:
        # 모든 종목 가격 업데이트
        update_all_prices()
    except Exception as e:
        logger.error(f"가격 업데이트 오류: {e}")
    
    try:
        # 적금 계산 업데이트
        update_savings_calculation()
    except Exception as e:
        logger.error(f"적금 계산 업데이트 오류: {e}")
    
    logger.info("자동 가격 업데이트 작업 완료")

def update_portfolio_history_job():
    """
    포트폴리오 이력 업데이트 작업 (스케줄러에서 호출)
    """
    logger.info("포트폴리오 이력 업데이트 작업 시작")
    
    try:
        from services.portfolio_service import update_all_portfolio_history
        # 모든 사용자의 포트폴리오 이력 업데이트
        update_all_portfolio_history()
    except Exception as e:
        logger.error(f"포트폴리오 이력 업데이트 오류: {e}")
    
    logger.info("포트폴리오 이력 업데이트 작업 완료")

def run_scheduler():
    """
    스케줄러 실행 (별도 스레드)
    """
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"스케줄러 실행 오류: {e}")
            time.sleep(10)  # 오류 발생 시 10초 대기 후 재시도

def schedule_price_updates():
    """
    가격 업데이트 스케줄링
    """
    # 간단한 매일 업데이트 버전
    schedule.every().day.at("09:30").do(update_prices_job)
    schedule.every().day.at("15:30").do(update_prices_job)
    schedule.every().day.at("16:00").do(update_portfolio_history_job)
    
    # 스케줄러 실행 (별도 스레드)
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("가격 업데이트 스케줄러 시작됨")
    
    # 앱 시작시 한번 업데이트
    try:
        update_prices_job()
    except Exception as e:
        logger.error(f"초기 가격 업데이트 오류: {e}")
"""
시장 데이터 서비스 (주가, 환율 등) - 향상된 데이터 수집 및 캐싱 기능
"""
import threading
import time
import schedule
import json
from datetime import datetime, timedelta
import requests
import sqlite3
import traceback

try:
    import yfinance as yf
    import pykrx.stock as stock
    from pykrx import bond
    PYKRX_AVAILABLE = True
except ImportError:
    # 모듈이 설치되지 않은 경우 대체 기능
    yf = None
    stock = None
    bond = None
    PYKRX_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False

from utils.logging import get_logger, log_exception
from models.database import get_db_connection

logger = get_logger(__name__)

# API 키 설정 (실제 서비스에서는 환경 변수 또는 설정 파일에서 로드)
API_KEYS = {
    'alpha_vantage': '',
    'financial_modeling_prep': '',
    'yahoo_finance': '',
    'exchange_rate': ''
}

# 캐시 설정
CACHE_EXPIRY = {
    'stock_price': 60 * 15,  # 15분
    'exchange_rate': 60 * 60,  # 1시간
    'company_info': 60 * 60 * 24,  # 1일
    'financial_data': 60 * 60 * 24 * 7  # 1주일
}

def load_api_keys_from_settings():
    """설정 데이터베이스에서 API 키 로드"""
    try:
        conn = get_db_connection('settings')
        cursor = conn.cursor()
        
        cursor.execute("SELECT setting_key, setting_value FROM system_settings WHERE setting_key LIKE 'api_key_%'")
        keys = cursor.fetchall()
        
        conn.close()
        
        for key in keys:
            if key['setting_key'] == 'api_key_alpha_vantage':
                API_KEYS['alpha_vantage'] = key['setting_value']
            elif key['setting_key'] == 'api_key_financial_modeling_prep':
                API_KEYS['financial_modeling_prep'] = key['setting_value']
            elif key['setting_key'] == 'api_key_exchange_rate':
                API_KEYS['exchange_rate'] = key['setting_value']
        
        logger.info("API 키 로드 완료")
    except Exception as e:
        log_exception(logger, e, {"context": "API 키 로드"})
        logger.warning("API 키 로드 실패, 기본값 사용")

def get_cached_data(data_type, symbol=None, market=None, from_currency=None, to_currency=None):
    """
    캐시된 데이터 조회
    
    Args:
        data_type (str): 데이터 유형 ('stock_price', 'exchange_rate' 등)
        symbol (str, optional): 종목 코드
        market (str, optional): 시장 코드
        from_currency (str, optional): 변환 전 통화
        to_currency (str, optional): 변환 후 통화
        
    Returns:
        dict or None: 캐시된 데이터 또는 None (캐시 없음/만료)
    """
    try:
        conn = get_db_connection('market')
        cursor = conn.cursor()
        
        current_time = datetime.now()
        
        if data_type == 'exchange_rate':
            cursor.execute(
                """
                SELECT rate, timestamp, source
                FROM exchange_rate_cache
                WHERE from_currency = ? AND to_currency = ? AND expiry > ?
                """,
                (from_currency, to_currency, current_time)
            )
        else:
            cursor.execute(
                """
                SELECT data, timestamp
                FROM market_data_cache
                WHERE symbol = ? AND market = ? AND data_type = ? AND expiry > ?
                """,
                (symbol, market or 'default', data_type, current_time)
            )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            if data_type == 'exchange_rate':
                return {
                    'rate': result['rate'],
                    'timestamp': result['timestamp'],
                    'source': result['source']
                }
            else:
                # JSON으로 저장된 데이터를 파싱하여 반환
                return json.loads(result['data'])
                
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "캐시 데이터 조회", "data_type": data_type, "symbol": symbol})
        return None

def cache_data(data_type, data, symbol=None, market=None, from_currency=None, to_currency=None, source=None, expiry_seconds=None):
    """
    데이터 캐싱
    
    Args:
        data_type (str): 데이터 유형
        data: 캐싱할 데이터
        symbol (str, optional): 종목 코드
        market (str, optional): 시장 코드
        from_currency (str, optional): 변환 전 통화
        to_currency (str, optional): 변환 후 통화
        source (str, optional): 데이터 소스
        expiry_seconds (int, optional): 캐시 만료 시간 (초)
    """
    try:
        conn = get_db_connection('market')
        cursor = conn.cursor()
        
        current_time = datetime.now()
        
        if expiry_seconds is None:
            expiry_seconds = CACHE_EXPIRY.get(data_type, 3600)  # 기본 1시간
        
        expiry_time = current_time + timedelta(seconds=expiry_seconds)
        
        if data_type == 'exchange_rate':
            # 기존 환율 데이터 삭제
            cursor.execute(
                "DELETE FROM exchange_rate_cache WHERE from_currency = ? AND to_currency = ?",
                (from_currency, to_currency)
            )
            
            # 새 환율 데이터 추가
            cursor.execute(
                """
                INSERT INTO exchange_rate_cache 
                (from_currency, to_currency, rate, timestamp, expiry, source)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (from_currency, to_currency, data, current_time, expiry_time, source)
            )
        else:
            # 기존 데이터 삭제
            cursor.execute(
                "DELETE FROM market_data_cache WHERE symbol = ? AND market = ? AND data_type = ?",
                (symbol, market or 'default', data_type)
            )
            
            # 새 데이터 추가 (JSON으로 변환하여 저장)
            data_json = json.dumps(data)
            cursor.execute(
                """
                INSERT INTO market_data_cache 
                (symbol, market, data_type, data, timestamp, expiry)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (symbol, market or 'default', data_type, data_json, current_time, expiry_time)
            )
        
        conn.commit()
        conn.close()
        
        logger.debug(f"데이터 캐싱 완료: {data_type}, {symbol or from_currency}")
    except Exception as e:
        log_exception(logger, e, {"context": "데이터 캐싱", "data_type": data_type, "symbol": symbol})

def get_krx_stock_price(ticker, use_cache=True):
    """
    KRX에서 한국 주식 현재가 조회
    
    Args:
        ticker (str): 종목코드
        use_cache (bool): 캐시 사용 여부
        
    Returns:
        float or None: 현재가 또는 None (조회 실패시)
    """
    if not PYKRX_AVAILABLE:
        logger.warning("pykrx 모듈이 설치되어 있지 않습니다.")
        return None
    
    try:
        # 캐시 확인
        if use_cache:
            cached_data = get_cached_data('stock_price', symbol=ticker, market='KRX')
            if cached_data and 'price' in cached_data:
                logger.debug(f"캐시에서 주가 조회: {ticker}")
                return cached_data['price']
        
        # 오늘 날짜
        today = datetime.now().strftime("%Y%m%d")
        
        # 최근 30일 범위 설정 (충분한 거래일을 포함하기 위해)
        fromdate = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        
        # 최근 30일간의 OHLCV 데이터 가져오기
        df = stock.get_market_ohlcv_by_date(fromdate=fromdate, todate=today, ticker=ticker)
        
        if not df.empty:
            # 가장 최근 데이터 반환
            current_price = df.iloc[-1]['종가']
            
            # 캐싱
            cache_data('stock_price', {'price': current_price, 'date': today}, symbol=ticker, market='KRX')
            
            return current_price
        else:
            logger.warning(f"종목 {ticker}에 대한 데이터를 찾을 수 없습니다.")
            return None
    except Exception as e:
        log_exception(logger, e, {"context": "KRX 주가 조회", "ticker": ticker})
        return None

def get_krx_stock_info(ticker):
    """
    KRX 종목 기본 정보 조회
    
    Args:
        ticker (str): 종목코드
        
    Returns:
        dict or None: 종목 정보 또는 None (조회 실패시)
    """
    if not PYKRX_AVAILABLE:
        logger.warning("pykrx 모듈이 설치되어 있지 않습니다.")
        return None
    
    try:
        # 캐시 확인
        cached_data = get_cached_data('stock_info', symbol=ticker, market='KRX')
        if cached_data:
            logger.debug(f"캐시에서 종목 정보 조회: {ticker}")
            return cached_data
        
        # 오늘 날짜
        today = datetime.now().strftime("%Y%m%d")
        
        # 종목 정보 조회
        df_info = stock.get_market_cap_by_ticker(today)
        if ticker in df_info.index:
            info_row = df_info.loc[ticker]
            
            # 업종 정보 조회
            sector = "정보없음"
            try:
                df_sector = stock.get_market_fundamental_by_ticker(today, ticker)
                if not df_sector.empty:
                    sector_info = df_sector.loc[ticker].get('업종')
                    if sector_info:
                        sector = sector_info
            except:
                pass
            
            # 종목 정보 딕셔너리 생성
            stock_info = {
                'ticker': ticker,
                'name': stock.get_market_ticker_name(ticker),
                'market_cap': int(info_row.get('시가총액', 0)),
                'shares': int(info_row.get('상장주식수', 0)),
                'sector': sector
            }
            
            # PER, PBR, 배당수익률 정보 추가
            try:
                df_per = stock.get_market_fundamental_by_ticker(today)
                if ticker in df_per.index:
                    per_row = df_per.loc[ticker]
                    stock_info['per'] = float(per_row.get('PER', 0))
                    stock_info['pbr'] = float(per_row.get('PBR', 0))
                    stock_info['dividend_yield'] = float(per_row.get('DIV', 0))
            except:
                stock_info['per'] = 0
                stock_info['pbr'] = 0
                stock_info['dividend_yield'] = 0
            
            # 52주 최고/최저 정보 추가
            try:
                year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                df_year = stock.get_market_ohlcv_by_date(year_ago, today, ticker)
                stock_info['high_52w'] = df_year['고가'].max()
                stock_info['low_52w'] = df_year['저가'].min()
            except:
                stock_info['high_52w'] = 0
                stock_info['low_52w'] = 0
            
            # 캐싱
            cache_data('stock_info', stock_info, symbol=ticker, market='KRX')
            
            return stock_info
        else:
            logger.warning(f"종목 {ticker}에 대한 정보를 찾을 수 없습니다.")
            return None
    except Exception as e:
        log_exception(logger, e, {"context": "KRX 종목 정보 조회", "ticker": ticker})
        return None

def get_international_stock_price(ticker, country=None, use_cache=True):
    """
    Yahoo Finance에서 해외 주식 현재가 조회
    
    Args:
        ticker (str): 종목코드
        country (str, optional): 국가
        use_cache (bool): 캐시 사용 여부
        
    Returns:
        float or None: 현재가 또는 None (조회 실패시)
    """
    if not yf:
        logger.warning("yfinance 모듈이 설치되어 있지 않습니다.")
        return None
    
    # 티커 포맷 조정 (Apple -> AAPL 등)
    if country == '미국' and '.' not in ticker:
        # 심볼에 .이 포함되어 있지 않으면 그대로 사용
        yf_ticker = ticker
    elif country == '중국':
        # 중국 주식은 보통 Shanghai (ss) 또는 Shenzhen (sz) 거래소
        if ticker.endswith('.SS') or ticker.endswith('.SZ'):
            yf_ticker = ticker
        else:
            # 기본적으로 Shanghai 거래소 가정
            yf_ticker = f"{ticker}.SS"
    else:
        # 기타 국가 및 기본값
        yf_ticker = ticker
    
    try:
        # 캐시 확인
        if use_cache:
            market = f"YF_{country}" if country else "YF"
            cached_data = get_cached_data('stock_price', symbol=yf_ticker, market=market)
            if cached_data and 'price' in cached_data:
                logger.debug(f"캐시에서 해외 주가 조회: {yf_ticker}")
                return cached_data['price']
        
        stock_data = yf.Ticker(yf_ticker)
        
        # 최근 2일간의 데이터를 가져옴 (오늘 거래가 없을 수 있음)
        history = stock_data.history(period="2d")
        
        if not history.empty:
            # 가장 최근 종가 반환
            current_price = history['Close'].iloc[-1]
            
            # 캐싱
            market = f"YF_{country}" if country else "YF"
            cache_data('stock_price', {'price': current_price, 'date': datetime.now().strftime("%Y-%m-%d")}, 
                      symbol=yf_ticker, market=market)
            
            return current_price
        else:
            # 조회 실패 시 Yahoo Finance API 직접 호출 시도
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_ticker}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    price = data['chart']['result'][0]['meta']['regularMarketPrice']
                    
                    # 캐싱
                    market = f"YF_{country}" if country else "YF"
                    cache_data('stock_price', {'price': price, 'date': datetime.now().strftime("%Y-%m-%d")}, 
                              symbol=yf_ticker, market=market)
                    
                    return price
            except:
                pass
            
            logger.warning(f"종목 {yf_ticker}에 대한 데이터를 찾을 수 없습니다.")
            return None
    except Exception as e:
        log_exception(logger, e, {"context": "해외 주가 조회", "ticker": yf_ticker})
        return None

def get_international_stock_info(ticker, country=None):
    """
    Yahoo Finance에서 해외 주식 기본 정보 조회
    
    Args:
        ticker (str): 종목코드
        country (str, optional): 국가
        
    Returns:
        dict or None: 종목 정보 또는 None (조회 실패시)
    """
    if not yf:
        logger.warning("yfinance 모듈이 설치되어 있지 않습니다.")
        return None
    
    # 티커 포맷 조정
    if country == '미국' and '.' not in ticker:
        yf_ticker = ticker
    elif country == '중국':
        if ticker.endswith('.SS') or ticker.endswith('.SZ'):
            yf_ticker = ticker
        else:
            yf_ticker = f"{ticker}.SS"
    else:
        yf_ticker = ticker
    
    try:
        # 캐시 확인
        market = f"YF_{country}" if country else "YF"
        cached_data = get_cached_data('stock_info', symbol=yf_ticker, market=market)
        if cached_data:
            logger.debug(f"캐시에서 해외 종목 정보 조회: {yf_ticker}")
            return cached_data
        
        stock_data = yf.Ticker(yf_ticker)
        
        # 기본 정보 가져오기
        info = stock_data.info
        
        # 종목 정보 딕셔너리 생성
        stock_info = {
            'ticker': yf_ticker,
            'name': info.get('shortName', info.get('longName', yf_ticker)),
            'sector': info.get('sector', '정보없음'),
            'industry': info.get('industry', '정보없음'),
            'market_cap': info.get('marketCap', 0),
            'country': info.get('country', country or '정보없음'),
            'website': info.get('website', ''),
            'per': info.get('trailingPE', 0),
            'pbr': info.get('priceToBook', 0),
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'high_52w': info.get('fiftyTwoWeekHigh', 0),
            'low_52w': info.get('fiftyTwoWeekLow', 0)
        }
        
        # 캐싱
        cache_data('stock_info', stock_info, symbol=yf_ticker, market=market)
        
        return stock_info
    except Exception as e:
        log_exception(logger, e, {"context": "해외 종목 정보 조회", "ticker": yf_ticker})
        return None

def get_exchange_rate(from_currency, to_currency, use_cache=True):
    """
    환율 정보 조회 (다중 소스 지원)
    
    Args:
        from_currency (str): 기준 통화 (예: 'USD')
        to_currency (str): 목표 통화 (예: 'KRW')
        use_cache (bool): 캐시 사용 여부
        
    Returns:
        float or None: 환율 또는 None (조회 실패시)
    """
    try:
        # 캐시 확인
        if use_cache:
            cached_data = get_cached_data('exchange_rate', from_currency=from_currency, to_currency=to_currency)
            if cached_data:
                logger.debug(f"캐시에서 환율 조회: {from_currency}->{to_currency}")
                return cached_data['rate']
        
        # 소스 1: ExchangeRate-API
        try:
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'rates' in data and to_currency in data['rates']:
                rate = data['rates'][to_currency]
                
                # 환율 캐싱
                cache_data('exchange_rate', rate, from_currency=from_currency, to_currency=to_currency, source='exchangerate-api')
                
                return rate
        except Exception as e:
            logger.warning(f"ExchangeRate-API 환율 정보 조회 실패: {e}")
        
        # 소스 2: Open Exchange Rates (백업)
        try:
            if API_KEYS.get('exchange_rate'):
                url = f"https://openexchangerates.org/api/latest.json?app_id={API_KEYS['exchange_rate']}&base={from_currency}"
                response = requests.get(url, timeout=10)
                data = response.json()
                
                if 'rates' in data and to_currency in data['rates']:
                    rate = data['rates'][to_currency]
                    
                    # 환율 캐싱
                    cache_data('exchange_rate', rate, from_currency=from_currency, to_currency=to_currency, source='openexchangerates')
                    
                    return rate
        except Exception as e:
            logger.warning(f"Open Exchange Rates 환율 정보 조회 실패: {e}")
        
        # 소스 3: Yahoo Finance (마지막 대안)
        try:
            symbol = f"{from_currency}{to_currency}=X"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                rate = data['chart']['result'][0]['meta']['regularMarketPrice']
                
                # 환율 캐싱
                cache_data('exchange_rate', rate, from_currency=from_currency, to_currency=to_currency, source='yahoo')
                
                return rate
        except Exception as e:
            logger.warning(f"Yahoo Finance 환율 정보 조회 실패: {e}")
        
        # 모든 소스 실패 시 기본값 반환
        logger.error(f"모든 환율 정보 소스 조회 실패 ({from_currency}->{to_currency})")
        
        # 기본값으로 주요 통화 환율 하드코딩 (최후의 수단)
        default_rates = {
            'USD': {'KRW': 1350, 'JPY': 150, 'EUR': 0.92, 'GBP': 0.79, 'CNY': 7.20},
            'EUR': {'KRW': 1450, 'USD': 1.09, 'JPY': 162, 'GBP': 0.86, 'CNY': 7.80},
            'JPY': {'KRW': 9.0, 'USD': 0.0067, 'EUR': 0.0062},
            'KRW': {'USD': 0.00074, 'JPY': 0.11, 'EUR': 0.00069},
        }
        
        if from_currency in default_rates and to_currency in default_rates[from_currency]:
            return default_rates[from_currency][to_currency]
        
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "환율 정보 조회", "from": from_currency, "to": to_currency})
        return None

def get_stock_financial_data(ticker, market='KRX'):
    """
    종목 재무 데이터 조회
    
    Args:
        ticker (str): 종목코드
        market (str): 시장 코드 ('KRX', 'NASDAQ' 등)
        
    Returns:
        dict or None: 재무 데이터 또는 None (조회 실패시)
    """
    try:
        # 캐시 확인
        cached_data = get_cached_data('financial_data', symbol=ticker, market=market)
        if cached_data:
            logger.debug(f"캐시에서 재무 데이터 조회: {ticker}")
            return cached_data
        
        financial_data = {}
        
        if market == 'KRX' and PYKRX_AVAILABLE:
            # 한국 종목 재무 데이터 (pykrx)
            try:
                today = datetime.now().strftime("%Y%m%d")
                df = stock.get_market_fundamental_by_ticker(today, ticker)
                
                if not df.empty:
                    financial_data = {
                        'ticker': ticker,
                        'per': float(df.loc[ticker]['PER']) if 'PER' in df.columns else 0,
                        'pbr': float(df.loc[ticker]['PBR']) if 'PBR' in df.columns else 0,
                        'div_yield': float(df.loc[ticker]['DIV']) if 'DIV' in df.columns else 0,
                    }
            except Exception as e:
                logger.warning(f"KRX 재무 데이터 조회 실패: {e}")
        else:
            # 해외 종목 재무 데이터 (Yahoo Finance)
            if yf:
                try:
                    stock_data = yf.Ticker(ticker)
                    info = stock_data.info
                    
                    financial_data = {
                        'ticker': ticker,
                        'per': info.get('trailingPE', 0),
                        'pbr': info.get('priceToBook', 0),
                        'div_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
                        'market_cap': info.get('marketCap', 0),
                        'eps': info.get('trailingEps', 0),
                        'revenue': info.get('totalRevenue', 0),
                        'profit_margin': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
                        'roa': info.get('returnOnAssets', 0) * 100 if info.get('returnOnAssets') else 0,
                        'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,
                        'debt_to_equity': info.get('debtToEquity', 0),
                        'current_ratio': info.get('currentRatio', 0),
                    }
                    
                    # 재무제표 데이터 (수익, 비용, 자산 등)
                    try:
                        income_stmt = stock_data.income_stmt
                        if not income_stmt.empty:
                            financial_data['revenue_growth'] = (
                                (income_stmt.loc['Total Revenue'][0] / income_stmt.loc['Total Revenue'][1] - 1) * 100
                                if 'Total Revenue' in income_stmt.index and len(income_stmt.columns) > 1 else 0
                            )
                    except:
                        pass
                except Exception as e:
                    logger.warning(f"Yahoo Finance 재무 데이터 조회 실패: {e}")
        
        # 데이터가 충분히 채워졌으면 캐싱
        if financial_data and len(financial_data) > 2:
            cache_data('financial_data', financial_data, symbol=ticker, market=market)
            
            return financial_data
        else:
            logger.warning(f"종목 {ticker}의 재무 데이터가 충분하지 않습니다.")
            return None
    except Exception as e:
        log_exception(logger, e, {"context": "재무 데이터 조회", "ticker": ticker})
        return None

def get_dividend_info(ticker, market='KRX'):
    """
    배당 정보 조회
    
    Args:
        ticker (str): 종목코드
        market (str): 시장 코드
        
    Returns:
        dict or None: 배당 정보 또는 None (조회 실패시)
    """
    try:
        # 캐시 확인
        cached_data = get_cached_data('dividend_info', symbol=ticker, market=market)
        if cached_data:
            logger.debug(f"캐시에서 배당 정보 조회: {ticker}")
            return cached_data
        
        dividend_info = {}
        
        # 해외 종목 배당 정보 (Yahoo Finance)
        if market != 'KRX' and yf:
            try:
                stock_data = yf.Ticker(ticker)
                dividends = stock_data.dividends
                
                if not dividends.empty:
                    # 최근 배당금
                    recent_dividend = dividends.iloc[-1]
                    
                    # 최근 배당일
                    recent_date = dividends.index[-1].strftime('%Y-%m-%d')
                    
                    # 연간 배당금 계산
                    annual_dividend = 0
                    dividend_frequency = 0
                    
                    # 최근 1년간 배당금 합산
                    one_year_ago = datetime.now() - timedelta(days=365)
                    recent_dividends = dividends[dividends.index > one_year_ago]
                    
                    if not recent_dividends.empty:
                        annual_dividend = recent_dividends.sum()
                        dividend_frequency = len(recent_dividends)
                    
                    # 배당 주기 추정
                    if dividend_frequency == 1:
                        frequency = "연간"
                    elif dividend_frequency == 2:
                        frequency = "반기"
                    elif dividend_frequency == 4:
                        frequency = "분기"
                    else:
                        frequency = "불규칙"
                    
                    # 배당 정보 구성
                    dividend_info = {
                        'ticker': ticker,
                        'recent_dividend': recent_dividend,
                        'recent_date': recent_date,
                        'annual_dividend': annual_dividend,
                        'frequency': frequency,
                        'history': [
                            {'date': date.strftime('%Y-%m-%d'), 'amount': amount}
                            for date, amount in zip(dividends.index[-5:], dividends.values[-5:])
                        ]
                    }
                    
                    # 주가에 대한 배당 수익률 계산 (수년간 평균)
                    try:
                        current_price = get_international_stock_price(ticker)
                        if current_price and current_price > 0:
                            dividend_info['yield'] = (annual_dividend / current_price) * 100
                        else:
                            dividend_info['yield'] = 0
                    except:
                        dividend_info['yield'] = 0
            except Exception as e:
                logger.warning(f"Yahoo Finance 배당 정보 조회 실패: {e}")
        
        # 한국 종목 배당 정보 조회
        elif market == 'KRX' and PYKRX_AVAILABLE:
            try:
                today = datetime.now().strftime("%Y%m%d")
                df = stock.get_market_fundamental_by_ticker(today)
                
                if ticker in df.index and 'DIV' in df.columns:
                    div_yield = df.loc[ticker]['DIV']
                    
                    # 현재가 조회
                    current_price = get_krx_stock_price(ticker)
                    
                    # 배당금 계산 (수익률로부터 역산)
                    if current_price and div_yield > 0:
                        annual_dividend = current_price * (div_yield / 100)
                    else:
                        annual_dividend = 0
                    
                    dividend_info = {
                        'ticker': ticker,
                        'yield': div_yield,
                        'annual_dividend': annual_dividend,
                        'frequency': "연간",  # 한국 주식은 대부분 연간 배당
                        'history': []
                    }
            except Exception as e:
                logger.warning(f"KRX 배당 정보 조회 실패: {e}")
        
        # 데이터가 충분히 채워졌으면 캐싱
        if dividend_info and len(dividend_info) > 2:
            cache_data('dividend_info', dividend_info, symbol=ticker, market=market)
            
            return dividend_info
        else:
            logger.warning(f"종목 {ticker}의 배당 정보가 충분하지 않습니다.")
            return None
    except Exception as e:
        log_exception(logger, e, {"context": "배당 정보 조회", "ticker": ticker})
        return None

def get_market_index(index_code, use_cache=True):
    """
    시장 지수 조회
    
    Args:
        index_code (str): 지수 코드 ('KS11', 'KQ11', 'DJI', 'IXIC', 'SPX' 등)
        use_cache (bool): 캐시 사용 여부
        
    Returns:
        dict or None: 지수 정보 또는 None (조회 실패시)
    """
    try:
        # 캐시 확인
        if use_cache:
            cached_data = get_cached_data('market_index', symbol=index_code)
            if cached_data:
                logger.debug(f"캐시에서 시장 지수 조회: {index_code}")
                return cached_data
        
        index_info = {}
        
        # 국내 지수 조회
        if index_code in ['KS11', 'KOSPI', '코스피']:
            # 코스피 지수
            if PYKRX_AVAILABLE:
                try:
                    today = datetime.now().strftime("%Y%m%d")
                    fromdate = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
                    
                    df = stock.get_index_ohlcv_by_date(fromdate, today, "1001")  # 코스피 지수
                    
                    if not df.empty:
                        last_row = df.iloc[-1]
                        index_info = {
                            'code': 'KS11',
                            'name': '코스피',
                            'current': last_row['종가'],
                            'change': last_row['등락률'],
                            'date': last_row.name.strftime('%Y-%m-%d'),
                            'open': last_row['시가'],
                            'high': last_row['고가'],
                            'low': last_row['저가'],
                            'volume': last_row['거래량']
                        }
                except Exception as e:
                    logger.warning(f"코스피 지수 조회 실패: {e}")
        
        elif index_code in ['KQ11', 'KOSDAQ', '코스닥']:
            # 코스닥 지수
            if PYKRX_AVAILABLE:
                try:
                    today = datetime.now().strftime("%Y%m%d")
                    fromdate = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
                    
                    df = stock.get_index_ohlcv_by_date(fromdate, today, "2001")  # 코스닥 지수
                    
                    if not df.empty:
                        last_row = df.iloc[-1]
                        index_info = {
                            'code': 'KQ11',
                            'name': '코스닥',
                            'current': last_row['종가'],
                            'change': last_row['등락률'],
                            'date': last_row.name.strftime('%Y-%m-%d'),
                            'open': last_row['시가'],
                            'high': last_row['고가'],
                            'low': last_row['저가'],
                            'volume': last_row['거래량']
                        }
                except Exception as e:
                    logger.warning(f"코스닥 지수 조회 실패: {e}")
        
        else:
            # 해외 지수는 Yahoo Finance 사용
            index_map = {
                'DJI': '^DJI',  # 다우존스
                'IXIC': '^IXIC',  # 나스닥
                'SPX': '^GSPC',  # S&P 500
                'FTSE': '^FTSE',  # 영국 FTSE
                'DAX': '^GDAXI',  # 독일 DAX
                'N225': '^N225',  # 일본 니케이
                'HSI': '^HSI'  # 홍콩 항생
            }
            
            # 매핑 테이블에 없는 경우 그대로 사용
            yf_code = index_map.get(index_code, index_code)
            
            if yf:
                try:
                    index_data = yf.Ticker(yf_code)
                    history = index_data.history(period="5d")
                    
                    if not history.empty:
                        last_row = history.iloc[-1]
                        prev_close = history.iloc[-2]['Close'] if len(history) > 1 else last_row['Open']
                        
                        # 변화율 계산
                        change_pct = ((last_row['Close'] - prev_close) / prev_close) * 100
                        
                        # 지수명 매핑
                        index_names = {
                            '^DJI': '다우존스',
                            '^IXIC': '나스닥',
                            '^GSPC': 'S&P 500',
                            '^FTSE': 'FTSE 100',
                            '^GDAXI': 'DAX',
                            '^N225': '니케이 225',
                            '^HSI': '항생'
                        }
                        
                        index_info = {
                            'code': index_code,
                            'name': index_names.get(yf_code, yf_code),
                            'current': last_row['Close'],
                            'change': change_pct,
                            'date': history.index[-1].strftime('%Y-%m-%d'),
                            'open': last_row['Open'],
                            'high': last_row['High'],
                            'low': last_row['Low'],
                            'volume': last_row['Volume']
                        }
                except Exception as e:
                    logger.warning(f"Yahoo Finance 지수 조회 실패: {e}")
        
        # 데이터가 충분히 채워졌으면 캐싱
        if index_info and len(index_info) > 3:
            cache_data('market_index', index_info, symbol=index_code)
            
            return index_info
        else:
            # 보조 방법: API 직접 호출
            try:
                # Yahoo Finance API 직접 호출
                yf_code = index_map.get(index_code, index_code)
                if not yf_code.startswith('^'):
                    yf_code = f"^{yf_code}"
                
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_code}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    meta = data['chart']['result'][0]['meta']
                    
                    index_info = {
                        'code': index_code,
                        'name': index_code,
                        'current': meta.get('regularMarketPrice', 0),
                        'change': meta.get('regularMarketChangePercent', 0),
                        'date': datetime.fromtimestamp(meta.get('regularMarketTime', 0)).strftime('%Y-%m-%d'),
                        'open': meta.get('regularMarketOpen', 0),
                        'high': meta.get('regularMarketDayHigh', 0),
                        'low': meta.get('regularMarketDayLow', 0),
                        'volume': meta.get('regularMarketVolume', 0)
                    }
                    
                    cache_data('market_index', index_info, symbol=index_code)
                    return index_info
            except Exception as e:
                logger.warning(f"API 직접 호출 지수 조회 실패: {e}")
            
            logger.warning(f"지수 {index_code}에 대한 정보가 충분하지 않습니다.")
            return None
    except Exception as e:
        log_exception(logger, e, {"context": "시장 지수 조회", "index": index_code})
        return None

def update_prices_job():
    """
    모든 종목 가격 업데이트 작업 (스케줄러에서 호출)
    """
    logger.info("자동 가격 업데이트 작업 시작")
    
    try:
        from services.portfolio_service import update_all_prices
        from services.savings_service import update_savings_calculation
        
        # 모든 종목 가격 업데이트
        update_all_prices()
        
        # 적금 계산 업데이트
        update_savings_calculation()
        
        # 시장 지수 업데이트
        update_market_indices()
        
        # 환율 업데이트
        update_exchange_rates()
        
        logger.info("자동 가격 업데이트 작업 완료")
    except Exception as e:
        log_exception(logger, e, {"context": "가격 업데이트 작업"})

def update_portfolio_history_job():
    """
    포트폴리오 이력 업데이트 작업 (스케줄러에서 호출)
    """
    logger.info("포트폴리오 이력 업데이트 작업 시작")
    
    try:
        from services.portfolio_service import update_all_portfolio_history
        
        # 모든 사용자의 포트폴리오 이력 업데이트
        update_all_portfolio_history()
        
        logger.info("포트폴리오 이력 업데이트 작업 완료")
    except Exception as e:
        log_exception(logger, e, {"context": "포트폴리오 이력 업데이트 작업"})

def update_market_indices():
    """
    주요 시장 지수 업데이트
    """
    logger.info("시장 지수 업데이트 작업 시작")
    
    # 업데이트할 지수 목록
    indices = ['KS11', 'KQ11', 'DJI', 'IXIC', 'SPX']
    
    try:
        for index_code in indices:
            # 캐시 무시하고 최신 데이터 조회
            get_market_index(index_code, use_cache=False)
        
        logger.info("시장 지수 업데이트 완료")
    except Exception as e:
        log_exception(logger, e, {"context": "시장 지수 업데이트"})

def update_exchange_rates():
    """
    주요 환율 업데이트
    """
    logger.info("환율 업데이트 작업 시작")
    
    # 업데이트할 환율 목록
    currency_pairs = [
        ('USD', 'KRW'),
        ('EUR', 'KRW'),
        ('JPY', 'KRW'),
        ('CNY', 'KRW'),
        ('USD', 'EUR'),
        ('USD', 'JPY')
    ]
    
    try:
        for from_currency, to_currency in currency_pairs:
            # 캐시 무시하고 최신 데이터 조회
            get_exchange_rate(from_currency, to_currency, use_cache=False)
        
        logger.info("환율 업데이트 완료")
    except Exception as e:
        log_exception(logger, e, {"context": "환율 업데이트"})

def run_scheduler():
    """
    스케줄러 실행 (별도 스레드)
    """
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            log_exception(logger, e, {"context": "스케줄러 실행"})
            time.sleep(10)  # 오류 발생 시 10초 대기 후 재시도

def schedule_price_updates():
    """
    가격 업데이트 스케줄링
    """
    # 시장 시간대별 업데이트 (한국, 미국, 유럽 시장 시간 고려)
    schedule.every().day.at("08:45").do(update_prices_job)  # 한국 시장 시작 전
    schedule.every().day.at("15:30").do(update_prices_job)  # 한국 시장 종료 후
    
    schedule.every().day.at("23:45").do(update_prices_job)  # 미국 시장 오전 시작 전 (한국시간)
    schedule.every().day.at("05:30").do(update_prices_job)  # 미국 시장 종료 후 (한국시간)
    
    # 포트폴리오 이력 및 성과 지표 업데이트 (밤 12시)
    schedule.every().day.at("00:00").do(update_portfolio_history_job)
    
    # 환율 업데이트 (하루 4번)
    schedule.every().day.at("09:00").do(update_exchange_rates)
    schedule.every().day.at("13:00").do(update_exchange_rates)
    schedule.every().day.at("17:00").do(update_exchange_rates)
    schedule.every().day.at("21:00").do(update_exchange_rates)
    
    # 시장 지수 업데이트 (매 시간)
    schedule.every().hour.do(update_market_indices)
    
    # 데이터베이스 캐시 정리 (매주 일요일 새벽)
    schedule.every().sunday.at("04:00").do(clean_cache_database)
    
    # 스케줄러 실행 (별도 스레드에서 실행)
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("가격 업데이트 스케줄러 시작됨")
    
    # 앱 시작시 한번 업데이트
    try:
        # API 키 로드
        load_api_keys_from_settings()
        
        # 초기 업데이트 실행
        update_prices_job()
    except Exception as e:
        log_exception(logger, e, {"context": "초기 가격 업데이트"})

def clean_cache_database():
    """
    오래된 캐시 데이터 정리
    """
    logger.info("캐시 데이터베이스 정리 시작")
    
    try:
        conn = get_db_connection('market')
        cursor = conn.cursor()
        
        # 현재 시간
        current_time = datetime.now()
        
        # 만료된 시장 데이터 삭제
        cursor.execute(
            "DELETE FROM market_data_cache WHERE expiry < ?",
            (current_time,)
        )
        market_deleted = cursor.rowcount
        
        # 만료된 환율 데이터 삭제
        cursor.execute(
            "DELETE FROM exchange_rate_cache WHERE expiry < ?",
            (current_time,)
        )
        exchange_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"캐시 데이터베이스 정리 완료: {market_deleted}개 시장 데이터, {exchange_deleted}개 환율 데이터 삭제")
    except Exception as e:
        log_exception(logger, e, {"context": "캐시 데이터베이스 정리"})

def get_stock_chart_data(ticker, market='KRX', period='1y', interval='1d'):
    """
    차트용 주가 데이터 조회
    
    Args:
        ticker (str): 종목코드
        market (str): 시장 코드
        period (str): 기간 ('1d', '1w', '1m', '3m', '6m', '1y', '5y', 'max')
        interval (str): 간격 ('1m', '5m', '15m', '30m', '1h', '1d', '1wk', '1mo')
        
    Returns:
        dict or None: 차트 데이터 또는 None (조회 실패시)
    """
    try:
        # 기간 매핑
        period_map = {
            '1d': '1d',
            '1w': '5d',
            '1m': '1mo',
            '3m': '3mo',
            '6m': '6mo',
            '1y': '1y',
            '5y': '5y',
            'max': 'max'
        }
        
        # 간격 매핑
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '60m',
            '1d': '1d',
            '1wk': '1wk',
            '1mo': '1mo'
        }
        
        yf_period = period_map.get(period, '1y')
        yf_interval = interval_map.get(interval, '1d')
        
        # 캐시 키 생성
        cache_key = f"chart_{period}_{interval}"
        
        # 캐시 확인
        cached_data = get_cached_data(cache_key, symbol=ticker, market=market)
        if cached_data:
            logger.debug(f"캐시에서 차트 데이터 조회: {ticker} ({period}, {interval})")
            return cached_data
        
        if market == 'KRX' and PYKRX_AVAILABLE and interval in ['1d', '1wk', '1mo']:
            # 한국 주식 데이터 (pykrx)
            try:
                # 날짜 범위 계산
                end_date = datetime.now().strftime("%Y%m%d")
                
                if period == '1d':
                    start_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                elif period == '1w':
                    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
                elif period == '1m':
                    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
                elif period == '3m':
                    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")
                elif period == '6m':
                    start_date = (datetime.now() - timedelta(days=180)).strftime("%Y%m%d")
                elif period == '1y':
                    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                else:  # 5y 또는 max
                    start_date = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y%m%d")
                
                df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
                
                if not df.empty:
                    # 데이터 포맷 변환
                    chart_data = {
                        'ticker': ticker,
                        'dates': df.index.strftime('%Y-%m-%d').tolist(),
                        'opens': df['시가'].tolist(),
                        'highs': df['고가'].tolist(),
                        'lows': df['저가'].tolist(),
                        'closes': df['종가'].tolist(),
                        'volumes': df['거래량'].tolist()
                    }
                    
                    # 캐싱
                    cache_data(cache_key, chart_data, symbol=ticker, market=market, expiry_seconds=3600)  # 1시간 캐시
                    
                    return chart_data
            except Exception as e:
                logger.warning(f"KRX 차트 데이터 조회 실패: {e}")
        
        # Yahoo Finance 사용 (해외 주식 및 KRX 백업)
        if yf:
            try:
                stock_data = yf.Ticker(ticker)
                history = stock_data.history(period=yf_period, interval=yf_interval)
                
                if not history.empty:
                    # 데이터 포맷 변환
                    chart_data = {
                        'ticker': ticker,
                        'dates': history.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
                        'opens': history['Open'].tolist(),
                        'highs': history['High'].tolist(),
                        'lows': history['Low'].tolist(),
                        'closes': history['Close'].tolist(),
                        'volumes': history['Volume'].tolist() if 'Volume' in history.columns else []
                    }
                    
                    # 캐싱
                    cache_data(cache_key, chart_data, symbol=ticker, market=market, expiry_seconds=3600)  # 1시간 캐시
                    
                    return chart_data
            except Exception as e:
                logger.warning(f"Yahoo Finance 차트 데이터 조회 실패: {e}")
        
        logger.warning(f"종목 {ticker}의 차트 데이터를 조회할 수 없습니다.")
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "차트 데이터 조회", "ticker": ticker, "period": period})
        return None
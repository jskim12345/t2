"""
데이터베이스 초기화 및 연결 관리 모듈
"""
import os
import sqlite3
from datetime import datetime
import bcrypt
import json
from utils.logging import get_logger

logger = get_logger(__name__)

def init_databases():
    """
    모든 필요한 데이터베이스 초기화
    """
    # 데이터 디렉토리 생성
    os.makedirs('data', exist_ok=True)
    os.makedirs('data/backup', exist_ok=True)
    
    # 각 데이터베이스 초기화
    init_user_database()
    init_portfolio_database()
    init_market_database()
    init_settings_database()
    
    logger.info("데이터베이스 초기화 완료")

def get_db_connection(db_name):
    """
    데이터베이스 연결 반환
    
    Args:
        db_name (str): 데이터베이스 파일명 (확장자 제외)
        
    Returns:
        sqlite3.Connection: 데이터베이스 연결 객체
    """
    conn = sqlite3.connect(f'data/{db_name}.db')
    # Row를 딕셔너리로 반환하도록 설정
    conn.row_factory = sqlite3.Row
    return conn

def init_user_database():
    """
    사용자 인증 관련 데이터베이스 초기화
    """
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    # 사용자 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        email TEXT,
        created_at TIMESTAMP,
        last_login TIMESTAMP,
        profile_settings TEXT,     /* 프로필 설정 (JSON) */
        preferences TEXT,          /* 앱 설정 (JSON) */
        last_backup TIMESTAMP      /* 마지막 백업 시간 */
    )
    ''')
    
    # 세션 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        user_id INTEGER,
        created_at TIMESTAMP,
        expires_at TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT,
        last_activity TIMESTAMP,   /* 마지막 활동 시간 */
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 로그인 로그 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS login_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT,
        success BOOLEAN,
        failure_reason TEXT,       /* 실패 원인 */
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 보안 질문 테이블 (비밀번호 복구용)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS security_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        question TEXT,
        answer_hash TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 알림 설정 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,                /* 알림 유형 (이메일, 앱 내 등) */
        event TEXT,               /* 알림 트리거 이벤트 */
        is_enabled BOOLEAN,
        config TEXT,              /* 알림 설정 (JSON) */
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 기본 관리자 계정 생성 (최초 실행시에만)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # 기본 비밀번호 해싱
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw('admin123'.encode('utf-8'), salt)
        
        # 기본 프로필 설정
        default_profile = json.dumps({
            "display_name": "관리자",
            "language": "ko",
            "theme": "light",
            "currency": "KRW",
            "timezone": "Asia/Seoul"
        })
        
        # 기본 앱 설정
        default_preferences = json.dumps({
            "notifications_enabled": True,
            "auto_update_prices": True,
            "update_interval": 3600,
            "default_view": "portfolio",
            "chart_color_theme": "default"
        })
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, created_at, profile_settings, preferences) VALUES (?, ?, ?, ?, ?, ?)",
            ('admin', hashed.decode('utf-8'), 'admin@example.com', datetime.now(), default_profile, default_preferences)
        )
        logger.info("기본 관리자 계정 생성 완료")
    
    conn.commit()
    conn.close()

def init_portfolio_database():
    """
    포트폴리오, 적금 관련 데이터베이스 초기화
    """
    conn = get_db_connection('portfolio')
    cursor = conn.cursor()
    
    # 포트폴리오 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        증권사 TEXT,
        계좌 TEXT,
        국가 TEXT,
        종목코드 TEXT,
        종목명 TEXT,
        수량 REAL,
        평단가_원화 REAL,
        평단가_달러 REAL,
        현재가_원화 REAL,
        현재가_달러 REAL,
        평가액 REAL,
        투자비중 REAL,
        손익금액 REAL,
        손익수익 REAL,
        총수익률 REAL,
        배당금 REAL,              /* 누적 배당금 */
        최근배당일 DATE,          /* 최근 배당금 지급일 */
        섹터 TEXT,                /* 종목 섹터 정보 */
        산업군 TEXT,              /* 종목 산업군 정보 */
        현금흐름등급 TEXT,        /* 현금흐름 평가 등급 */
        베타 REAL,                /* 시장 대비 베타값 */
        매수날짜 DATE,            /* 최초 매수 날짜 */
        메모 TEXT,                /* 종목 관련 메모 */
        자동매수설정 TEXT,        /* 자동 매수 설정 (JSON) */
        last_update TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 거래 내역 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_id INTEGER,
        user_id INTEGER,
        type TEXT,
        quantity REAL,
        price REAL,
        수수료 REAL,              /* 거래 수수료 */
        세금 REAL,                /* 거래세, 양도소득세 등 */
        transaction_date TIMESTAMP,
        실현손익 REAL,            /* 매도 시 실현 손익 */
        거래메모 TEXT,            /* 거래 관련 메모 */
        FOREIGN KEY (portfolio_id) REFERENCES portfolio (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

    # 포트폴리오 이력 테이블 생성 (수익률 시각화용)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS portfolio_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date DATE,
        total_value REAL,
        total_invested REAL,
        total_gain_loss REAL,
        total_return_percent REAL,
        cash_balance REAL,        /* 현금 잔고 */
        realized_profit REAL,     /* 실현 이익 */
        unrealized_profit REAL,   /* 미실현 이익 */
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 배당금 기록 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dividends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_id INTEGER,
        user_id INTEGER,
        지급일 DATE,
        배당액 REAL,
        배당유형 TEXT,            /* 현금배당, 주식배당 등 */
        통화 TEXT,
        세전금액 REAL,
        세후금액 REAL,
        FOREIGN KEY (portfolio_id) REFERENCES portfolio (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 적금 관련 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS savings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        이름 TEXT,
        은행 TEXT,
        계좌번호 TEXT,
        시작일 DATE,
        만기일 DATE,
        월납입액 REAL,
        금리 REAL,
        세후금리 REAL,
        금리유형 TEXT,            /* 단리, 복리 */
        적금유형 TEXT,            /* 정기적금, 자유적금 등 */
        현재납입액 REAL,
        예상만기금액 REAL,
        자동이체여부 BOOLEAN,     /* 자동이체 설정 여부 */
        자동이체일 INTEGER,       /* 자동이체 날짜 (매월 N일) */
        목표금액 REAL,            /* 목표 금액 */
        목표달성률 REAL,          /* 목표 달성률 */
        특별세율적용 BOOLEAN,     /* 비과세, 세금우대 여부 */
        memo TEXT,                /* 메모 */
        last_update TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 적금 거래내역 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS savings_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        savings_id INTEGER,
        user_id INTEGER,
        날짜 DATE,
        금액 REAL,
        거래유형 TEXT,            /* 입금, 출금, 이자지급 등 */
        메모 TEXT,
        FOREIGN KEY (savings_id) REFERENCES savings (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 예산 관리 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS budget (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        기간 TEXT,                /* 월간, 연간 등 */
        시작일 DATE,
        종료일 DATE,
        카테고리 TEXT,            /* 투자, 저축, 생활비 등 */
        예산금액 REAL,
        실제사용금액 REAL,
        목표비중 REAL,            /* 예산 카테고리별 목표 비중 */
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 목표 관리 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        제목 TEXT,
        목표금액 REAL,
        현재금액 REAL,
        시작일 DATE,
        목표일 DATE,
        우선순위 INTEGER,         /* 목표 우선순위 */
        카테고리 TEXT,            /* 단기, 중기, 장기 등 */
        진행상태 TEXT,            /* 진행중, 완료, 연기 등 */
        메모 TEXT,
        알림설정 TEXT,            /* 알림 설정 (JSON) */
        last_update TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

def init_market_database():
    """
    시장 데이터 관련 데이터베이스 초기화
    """
    conn = get_db_connection('market')
    cursor = conn.cursor()
    
    # 시장 데이터 캐시 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS market_data_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        market TEXT,              /* KRX, NASDAQ, NYSE 등 */
        data_type TEXT,           /* price, ohlcv, company_info 등 */
        data JSON,                /* 캐시된 데이터 (JSON) */
        timestamp TIMESTAMP,      /* 데이터 갱신 시간 */
        expiry TIMESTAMP,         /* 캐시 만료 시간 */
        UNIQUE(symbol, market, data_type)
    )
    ''')
    
    # 환율 데이터 캐시
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exchange_rate_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_currency TEXT,
        to_currency TEXT,
        rate REAL,
        timestamp TIMESTAMP,
        expiry TIMESTAMP,
        source TEXT,              /* 데이터 소스 */
        UNIQUE(from_currency, to_currency)
    )
    ''')
    
    # 종목 기본 정보 (섹터, 산업군 등)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        market TEXT,
        company_name TEXT,
        sector TEXT,
        industry TEXT,
        description TEXT,
        website TEXT,
        market_cap REAL,
        employees INTEGER,
        country TEXT,
        last_update TIMESTAMP,
        UNIQUE(symbol, market)
    )
    ''')
    
    # 금융 지표 (PER, PBR 등)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS financial_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        market TEXT,
        per REAL,                 /* 주가수익비율 */
        pbr REAL,                 /* 주가순자산비율 */
        roe REAL,                 /* 자기자본이익률 */
        dividend_yield REAL,      /* 배당수익률 */
        beta REAL,                /* 베타 */
        last_update TIMESTAMP,
        UNIQUE(symbol, market)
    )
    ''')
    
    # 배당 일정
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dividend_calendar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        market TEXT,
        ex_date DATE,             /* 배당락일 */
        pay_date DATE,            /* 배당지급일 */
        amount REAL,              /* 배당금액 */
        currency TEXT,            /* 통화 */
        frequency TEXT,           /* 배당 주기 (분기, 반기, 연간) */
        last_update TIMESTAMP,
        UNIQUE(symbol, market, ex_date)
    )
    ''')
    
    conn.commit()
    conn.close()

def init_settings_database():
    """
    앱 설정 관련 데이터베이스 초기화
    """
    conn = get_db_connection('settings')
    cursor = conn.cursor()
    
    # 시스템 설정 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE,
        setting_value TEXT,
        description TEXT,
        last_update TIMESTAMP
    )
    ''')
    
    # 알림 템플릿 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notification_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_name TEXT UNIQUE,
        template_type TEXT,       /* email, push, in-app 등 */
        subject_template TEXT,
        body_template TEXT,
        is_active BOOLEAN,
        last_update TIMESTAMP
    )
    ''')
    
    # 기본 시스템 설정 추가
    default_settings = [
        ('version', '2.0.0', '앱 버전'),
        ('data_update_interval', '3600', '데이터 자동 업데이트 간격 (초)'),
        ('backup_schedule', 'daily', '백업 스케줄 (daily, weekly, monthly)'),
        ('max_backup_count', '10', '유지할 최대 백업 개수'),
        ('log_level', 'INFO', '로깅 레벨'),
        ('default_theme', 'light', '기본 테마'),
        ('default_language', 'ko', '기본 언어'),
        ('api_timeout', '30', 'API 요청 타임아웃 (초)'),
        ('api_retry_count', '3', 'API 요청 재시도 횟수')
    ]
    
    # 기존 설정이 없는 경우에만 기본값 추가
    for key, value, description in default_settings:
        cursor.execute("SELECT COUNT(*) FROM system_settings WHERE setting_key = ?", (key,))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO system_settings (setting_key, setting_value, description, last_update) VALUES (?, ?, ?, ?)",
                (key, value, description, datetime.now())
            )
    
    # 기본 알림 템플릿 추가
    default_templates = [
        ('price_alert', 'in-app', '가격 알림', '{{종목명}}의 가격이 {{조건}}되었습니다. 현재가: {{현재가}}'),
        ('dividend_reminder', 'email', '배당금 안내', '{{종목명}}의 배당금 {{금액}}이 {{지급일}}에 지급될 예정입니다.'),
        ('savings_maturity', 'email', '적금 만기 안내', '{{적금명}} 적금이 {{만기일}}에 만기됩니다. 예상 만기금액: {{만기금액}}'),
        ('goal_achievement', 'in-app', '목표 달성 알림', '축하합니다! {{목표명}} 목표를 달성했습니다.')
    ]
    
    # 기존 템플릿이 없는 경우에만 기본값 추가
    for name, type, subject, body in default_templates:
        cursor.execute("SELECT COUNT(*) FROM notification_templates WHERE template_name = ?", (name,))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO notification_templates (template_name, template_type, subject_template, body_template, is_active, last_update) VALUES (?, ?, ?, ?, ?, ?)",
                (name, type, subject, body, True, datetime.now())
            )
    
    conn.commit()
    conn.close()

def backup_database(user_id=None):
    """
    데이터베이스 백업 수행
    
    Args:
        user_id (int, optional): 특정 사용자의 데이터만 백업 (None이면 전체 백업)
        
    Returns:
        str: 백업 파일 경로
    """
    import shutil
    from datetime import datetime
    
    # 백업 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    user_suffix = f"_user{user_id}" if user_id else ""
    backup_dir = "data/backup"
    
    # 디렉토리가 없으면 생성
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # 백업 파일 경로
    backup_file = f"{backup_dir}/backup_{timestamp}{user_suffix}.zip"
    
    try:
        # 데이터베이스 파일 목록
        db_files = ["users.db", "portfolio.db", "market.db", "settings.db"]
        
        # 압축 파일 생성
        shutil.make_archive(
            backup_file.replace(".zip", ""), 
            'zip', 
            "data", 
            include_dir=False,
            base_dir=None
        )
        
        # 백업 완료 후 사용자의 마지막 백업 시간 업데이트
        if user_id:
            conn = get_db_connection('users')
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_backup = ? WHERE id = ?",
                (datetime.now(), user_id)
            )
            conn.commit()
            conn.close()
        
        logger.info(f"데이터베이스 백업 완료: {backup_file}")
        return backup_file
    
    except Exception as e:
        logger.error(f"데이터베이스 백업 실패: {e}")
        return None

def restore_database(backup_file):
    """
    데이터베이스 복원
    
    Args:
        backup_file (str): 백업 파일 경로
        
    Returns:
        bool: 성공 여부
    """
    import shutil
    import tempfile
    import zipfile
    
    try:
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            # 백업 파일 압축 해제
            with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 데이터베이스 파일 목록
            db_files = ["users.db", "portfolio.db", "market.db", "settings.db"]
            
            # 현재 데이터베이스 파일 백업
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            for db_file in db_files:
                original_path = f"data/{db_file}"
                if os.path.exists(original_path):
                    shutil.copy2(original_path, f"{original_path}.{current_time}.bak")
            
            # 복원된 파일 복사
            for db_file in db_files:
                source_path = f"{temp_dir}/{db_file}"
                if os.path.exists(source_path):
                    shutil.copy2(source_path, f"data/{db_file}")
        
        logger.info(f"데이터베이스 복원 완료: {backup_file}")
        return True
    
    except Exception as e:
        logger.error(f"데이터베이스 복원 실패: {e}")
        return False
"""
데이터베이스 초기화 및 연결 관리 모듈
"""
import os
import sqlite3
from datetime import datetime
import bcrypt
from utils.logging import get_logger

logger = get_logger(__name__)

def init_databases():
    """
    모든 필요한 데이터베이스 초기화
    """
    # 데이터 디렉토리 생성
    os.makedirs('data', exist_ok=True)
    
    # 각 데이터베이스 초기화
    init_user_database()
    init_portfolio_database()
    
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
        last_login TIMESTAMP
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
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 기본 관리자 계정 생성 (최초 실행시에만)
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # 기본 비밀번호 해싱
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw('admin123'.encode('utf-8'), salt)
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, created_at) VALUES (?, ?, ?, ?)",
            ('admin', hashed.decode('utf-8'), 'admin@example.com', datetime.now())
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
        수량 INTEGER,
        평단가_원화 REAL,
        평단가_달러 REAL,
        현재가_원화 REAL,
        현재가_달러 REAL,
        평가액 REAL,
        투자비중 REAL,
        손익금액 REAL,
        손익수익 REAL,
        총수익률 REAL,
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
        quantity INTEGER,
        price REAL,
        transaction_date TIMESTAMP,
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
        현재납입액 REAL,
        예상만기금액 REAL,
        적금유형 TEXT,
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
        거래유형 TEXT,
        메모 TEXT,
        FOREIGN KEY (savings_id) REFERENCES savings (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()
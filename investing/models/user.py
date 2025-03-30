"""
사용자 인증 관련 데이터 모델
"""
import sqlite3
from datetime import datetime, timedelta
import uuid
import bcrypt
from models.database import get_db_connection
from utils.logging import get_logger

logger = get_logger(__name__)

def get_user_by_username(username):
    """
    사용자명으로 사용자 정보 조회
    
    Args:
        username (str): 사용자명
        
    Returns:
        dict or None: 사용자 정보 또는 None (사용자가 없는 경우)
    """
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)
    return None

def get_user_by_id(user_id):
    """
    ID로 사용자 정보 조회
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict or None: 사용자 정보 또는 None (사용자가 없는 경우)
    """
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)
    return None

def create_user(username, password_hash, email=None):
    """
    새 사용자 생성
    
    Args:
        username (str): 사용자명
        password_hash (str): 해싱된 비밀번호
        email (str, optional): 이메일 주소
        
    Returns:
        int or None: 생성된 사용자 ID 또는 None (생성 실패시)
    """
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, created_at) VALUES (?, ?, ?, ?)",
            (username, password_hash, email, datetime.now())
        )
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"새 사용자 생성: {username} (ID: {user_id})")
        return user_id
    except sqlite3.IntegrityError:
        conn.rollback()
        conn.close()
        logger.warning(f"사용자 생성 실패 (중복): {username}")
        return None
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"사용자 생성 실패: {e}")
        return None

def update_last_login(user_id):
    """
    사용자 마지막 로그인 시간 업데이트
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        bool: 성공 여부
    """
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"마지막 로그인 업데이트 실패 (ID: {user_id}): {e}")
        return False

def create_session(user_id, ip_address="unknown", user_agent="unknown", hours=24):
    """
    사용자 세션 생성
    
    Args:
        user_id (int): 사용자 ID
        ip_address (str, optional): IP 주소
        user_agent (str, optional): 유저 에이전트
        hours (int, optional): 세션 만료 시간 (시간)
        
    Returns:
        str or None: 세션 ID 또는 None (생성 실패시)
    """
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    try:
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=hours)
        
        cursor.execute(
            """
            INSERT INTO sessions (session_id, user_id, created_at, expires_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, datetime.now(), expires_at, ip_address, user_agent)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"세션 생성: {session_id} (사용자 ID: {user_id})")
        return session_id
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"세션 생성 실패 (사용자 ID: {user_id}): {e}")
        return None

def get_session(session_id):
    """
    세션 ID로 세션 정보 조회
    
    Args:
        session_id (str): 세션 ID
        
    Returns:
        dict or None: 세션 정보 또는 None (세션이 없는 경우)
    """
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    cursor.execute(
        """
        SELECT s.*, u.username 
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_id = ? AND s.expires_at > ?
        """,
        (session_id, datetime.now())
    )
    
    session = cursor.fetchone()
    conn.close()
    
    if session:
        return dict(session)
    return None

def delete_session(session_id):
    """
    세션 삭제 (로그아웃)
    
    Args:
        session_id (str): 세션 ID
        
    Returns:
        bool: 성공 여부
    """
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"세션 삭제: {session_id}")
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"세션 삭제 실패 (세션 ID: {session_id}): {e}")
        return False

def log_login_attempt(user_id, success, ip_address="unknown", user_agent="unknown"):
    """
    로그인 시도 로깅
    
    Args:
        user_id (int): 사용자 ID
        success (bool): 성공 여부
        ip_address (str, optional): IP 주소
        user_agent (str, optional): 유저 에이전트
        
    Returns:
        bool: 로깅 성공 여부
    """
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            INSERT INTO login_logs (user_id, timestamp, ip_address, user_agent, success)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, datetime.now(), ip_address, user_agent, success)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"로그인 로깅 실패 (사용자 ID: {user_id}): {e}")
        return False

def hash_password(password):
    """
    비밀번호 해싱
    
    Args:
        password (str): 비밀번호
        
    Returns:
        str: 해싱된 비밀번호
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def check_password(password, hashed_password):
    """
    비밀번호 확인
    
    Args:
        password (str): 확인할 비밀번호
        hashed_password (str): 저장된 해시된 비밀번호
        
    Returns:
        bool: 비밀번호 일치 여부
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
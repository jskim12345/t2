"""
사용자 인증 관련 서비스
"""
from datetime import datetime
import uuid
from models.user import (
    get_user_by_username, 
    create_user, 
    update_last_login, 
    create_session, 
    get_session, 
    delete_session, 
    log_login_attempt, 
    hash_password, 
    check_password
)
from utils.logging import get_logger

logger = get_logger(__name__)

def register_user(username, password, email=None):
    """
    사용자 등록
    
    Args:
        username (str): 사용자명
        password (str): 비밀번호
        email (str, optional): 이메일
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    # 입력값 검증
    if not username or not password:
        return False, "사용자명과 비밀번호는 필수 입력값입니다."
    
    # 사용자명 중복 확인
    if get_user_by_username(username):
        return False, "이미 사용 중인 사용자명입니다."
    
    # 비밀번호 해싱
    hashed_password = hash_password(password)
    
    # 사용자 생성
    user_id = create_user(username, hashed_password, email)
    
    if user_id:
        logger.info(f"사용자 등록 성공: {username}")
        return True, "사용자 등록 완료"
    else:
        logger.error(f"사용자 등록 실패: {username}")
        return False, "사용자 등록 중 오류가 발생했습니다."

def authenticate_user(username, password, ip_address="unknown", user_agent="unknown"):
    """
    사용자 인증
    
    Args:
        username (str): 사용자명
        password (str): 비밀번호
        ip_address (str, optional): IP 주소
        user_agent (str, optional): 유저 에이전트
        
    Returns:
        tuple: (성공 여부, 세션 ID 또는 None)
    """
    # 사용자 정보 조회
    user = get_user_by_username(username)
    
    if not user:
        logger.warning(f"로그인 실패 (사용자 없음): {username}")
        return False, None
    
    # 비밀번호 검증
    if not check_password(password, user['password_hash']):
        # 로그인 실패 로그 기록
        log_login_attempt(user['id'], False, ip_address, user_agent)
        logger.warning(f"로그인 실패 (비밀번호 불일치): {username}")
        return False, None
    
    # 로그인 성공 처리
    update_last_login(user['id'])
    
    # 세션 생성
    session_id = create_session(user['id'], ip_address, user_agent)
    
    # 로그인 성공 로그 기록
    log_login_attempt(user['id'], True, ip_address, user_agent)
    
    logger.info(f"로그인 성공: {username} (IP: {ip_address})")
    return True, session_id

def validate_session(session_id):
    """
    세션 유효성 검증
    
    Args:
        session_id (str): 세션 ID
        
    Returns:
        tuple: (유효성 여부, 세션 데이터 또는 None)
    """
    if not session_id:
        return False, None
    
    session = get_session(session_id)
    
    if not session:
        return False, None
    
    # 세션 데이터 반환
    return True, {
        "user_id": session['user_id'],
        "username": session['username']
    }

def logout_session(session_id):
    """
    세션 종료 (로그아웃)
    
    Args:
        session_id (str): 세션 ID
        
    Returns:
        bool: 성공 여부
    """
    if not session_id:
        return False
    
    result = delete_session(session_id)
    
    if result:
        logger.info(f"로그아웃 성공: 세션 {session_id}")
    else:
        logger.warning(f"로그아웃 실패: 세션 {session_id}")
    
    return result

def change_password(user_id, current_password, new_password):
    """
    비밀번호 변경
    
    Args:
        user_id (int): 사용자 ID
        current_password (str): 현재 비밀번호
        new_password (str): 새 비밀번호
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    from models.user import get_user_by_id
    
    # 사용자 정보 조회
    user = get_user_by_id(user_id)
    
    if not user:
        return False, "사용자를 찾을 수 없습니다."
    
    # 현재 비밀번호 확인
    if not check_password(current_password, user['password_hash']):
        return False, "현재 비밀번호가 일치하지 않습니다."
    
    # 새 비밀번호 해싱
    hashed_password = hash_password(new_password)
    
    # 비밀번호 업데이트
    from models.database import get_db_connection
    
    conn = get_db_connection('users')
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hashed_password, user_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"비밀번호 변경 성공: 사용자 ID {user_id}")
        return True, "비밀번호가 변경되었습니다."
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"비밀번호 변경 실패: {e}")
        return False, "비밀번호 변경 중 오류가 발생했습니다."
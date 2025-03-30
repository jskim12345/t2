"""
사용자 인증 관련 데이터 모델 - 보안 강화 및 고급 세션 관리 기능 추가
"""
import sqlite3
from datetime import datetime, timedelta
import uuid
import bcrypt
import json
import re
import secrets
import base64
from models.database import get_db_connection
from utils.logging import get_logger, log_exception

logger = get_logger(__name__)

# 비밀번호 정책 설정
PASSWORD_POLICY = {
    'min_length': 8,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_number': True,
    'require_special': True,
    'max_age_days': 90,
    'prevent_reuse': 3,  # 최근 몇 개의 비밀번호 재사용 금지
}

# 세션 설정
SESSION_CONFIG = {
    'default_expiry_hours': 24,
    'max_expiry_hours': 168,  # 최대 7일
    'refresh_threshold_hours': 1,  # 세션 자동 갱신 임계값
    'max_concurrent_sessions': 5,  # 동시 접속 세션 수 제한
}

def get_user_by_username(username):
    """
    사용자명으로 사용자 정보 조회
    
    Args:
        username (str): 사용자명
        
    Returns:
        dict or None: 사용자 정보 또는 None (사용자가 없는 경우)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        conn.close()
        
        if user:
            return dict(user)
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "사용자 조회", "username": username})
        return None

def get_user_by_id(user_id):
    """
    ID로 사용자 정보 조회
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict or None: 사용자 정보 또는 None (사용자가 없는 경우)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        conn.close()
        
        if user:
            return dict(user)
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "사용자 조회", "user_id": user_id})
        return None

def get_user_by_email(email):
    """
    이메일로 사용자 정보 조회
    
    Args:
        email (str): 이메일 주소
        
    Returns:
        dict or None: 사용자 정보 또는 None (사용자가 없는 경우)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        conn.close()
        
        if user:
            return dict(user)
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "사용자 조회", "email": email})
        return None

def validate_password(password):
    """
    비밀번호 강도 검증
    
    Args:
        password (str): 검증할 비밀번호
        
    Returns:
        tuple: (유효성 여부, 메시지)
    """
    errors = []
    
    # 길이 검증
    if len(password) < PASSWORD_POLICY['min_length']:
        errors.append(f"비밀번호는 최소 {PASSWORD_POLICY['min_length']}자 이상이어야 합니다.")
    
    # 대문자 포함 검증
    if PASSWORD_POLICY['require_uppercase'] and not any(c.isupper() for c in password):
        errors.append("비밀번호에는 최소 하나의 대문자가 포함되어야 합니다.")
    
    # 소문자 포함 검증
    if PASSWORD_POLICY['require_lowercase'] and not any(c.islower() for c in password):
        errors.append("비밀번호에는 최소 하나의 소문자가 포함되어야 합니다.")
    
    # 숫자 포함 검증
    if PASSWORD_POLICY['require_number'] and not any(c.isdigit() for c in password):
        errors.append("비밀번호에는 최소 하나의 숫자가 포함되어야 합니다.")
    
    # 특수문자 포함 검증
    if PASSWORD_POLICY['require_special'] and not any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/" for c in password):
        errors.append("비밀번호에는 최소 하나의 특수문자가 포함되어야 합니다.")
    
    # 유효성 결과 반환
    if errors:
        return False, "\n".join(errors)
    return True, "유효한 비밀번호입니다."

def check_password_history(user_id, new_password):
    """
    이전 비밀번호 재사용 여부 확인
    
    Args:
        user_id (int): 사용자 ID
        new_password (str): 새 비밀번호
        
    Returns:
        bool: 재사용 여부 (True: 재사용 가능, False: 재사용 불가)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 비밀번호 이력 조회
        cursor.execute(
            """
            SELECT password_hash FROM password_history
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, PASSWORD_POLICY['prevent_reuse'])
        )
        
        password_history = cursor.fetchall()
        conn.close()
        
        # 이력이 없으면 재사용 가능
        if not password_history:
            return True
        
        # 이전 비밀번호와 비교
        for record in password_history:
            if bcrypt.checkpw(new_password.encode('utf-8'), record['password_hash'].encode('utf-8')):
                return False  # 이전에 사용한 비밀번호
        
        return True  # 재사용 가능한 비밀번호
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 이력 확인", "user_id": user_id})
        return True  # 오류 시 재사용 가능으로 처리

def create_user(username, password_hash, email=None, profile_data=None, require_email_verification=False):
    """
    새 사용자 생성
    
    Args:
        username (str): 사용자명
        password_hash (str): 해싱된 비밀번호
        email (str, optional): 이메일 주소
        profile_data (dict, optional): 프로필 데이터
        require_email_verification (bool): 이메일 인증 필요 여부
        
    Returns:
        int or None: 생성된 사용자 ID 또는 None (생성 실패시)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 기본 프로필 설정
        default_profile = {
            "display_name": username,
            "language": "ko",
            "theme": "light",
            "currency": "KRW",
            "timezone": "Asia/Seoul"
        }
        
        # 사용자 제공 프로필 데이터 병합
        if profile_data:
            default_profile.update(profile_data)
        
        # 프로필 JSON 직렬화
        profile_json = json.dumps(default_profile, ensure_ascii=False)
        
        # 기본 앱 설정
        default_preferences = json.dumps({
            "notifications_enabled": True,
            "auto_update_prices": True,
            "update_interval": 3600,
            "default_view": "portfolio",
            "chart_color_theme": "default"
        })
        
        # 이메일 인증 코드 (필요시)
        verification_code = None
        verification_expiry = None
        email_verified = not require_email_verification
        
        if require_email_verification and email:
            verification_code = secrets.token_urlsafe(32)
            verification_expiry = datetime.now() + timedelta(days=3)
        
        # 사용자 생성
        cursor.execute(
            """
            INSERT INTO users (
                username, password_hash, email, created_at, 
                profile_settings, preferences, 
                email_verified, verification_code, verification_expiry,
                password_last_changed, account_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username, password_hash, email, datetime.now(),
                profile_json, default_preferences,
                email_verified, verification_code, verification_expiry,
                datetime.now(), "active"
            )
        )
        
        user_id = cursor.lastrowid
        
        # 비밀번호 이력 저장
        cursor.execute(
            "INSERT INTO password_history (user_id, password_hash, created_at) VALUES (?, ?, ?)",
            (user_id, password_hash, datetime.now())
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"새 사용자 생성: {username} (ID: {user_id})")
        return user_id
    except sqlite3.IntegrityError as e:
        log_exception(logger, e, {"context": "사용자 생성 (중복)", "username": username})
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "사용자 생성", "username": username})
        return None

def update_last_login(user_id):
    """
    사용자 마지막 로그인 시간 업데이트
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "마지막 로그인 업데이트", "user_id": user_id})
        return False

def get_profile_settings(user_id):
    """
    사용자 프로필 설정 조회
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict or None: 프로필 설정 또는 None (조회 실패시)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute("SELECT profile_settings FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result and result['profile_settings']:
            return json.loads(result['profile_settings'])
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "프로필 설정 조회", "user_id": user_id})
        return None

def update_profile_settings(user_id, profile_settings):
    """
    사용자 프로필 설정 업데이트
    
    Args:
        user_id (int): 사용자 ID
        profile_settings (dict): 프로필 설정
        
    Returns:
        bool: 성공 여부
    """
    try:
        # 기존 설정 조회
        current_settings = get_profile_settings(user_id) or {}
        
        # 새 설정과 병합
        current_settings.update(profile_settings)
        
        # JSON 직렬화
        settings_json = json.dumps(current_settings, ensure_ascii=False)
        
        # 저장
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET profile_settings = ? WHERE id = ?",
            (settings_json, user_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "프로필 설정 업데이트", "user_id": user_id})
        return False

def get_user_preferences(user_id):
    """
    사용자 앱 환경설정 조회
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        dict or None: 환경설정 또는 None (조회 실패시)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute("SELECT preferences FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result and result['preferences']:
            return json.loads(result['preferences'])
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "환경설정 조회", "user_id": user_id})
        return None

def update_user_preferences(user_id, preferences):
    """
    사용자 앱 환경설정 업데이트
    
    Args:
        user_id (int): 사용자 ID
        preferences (dict): 환경설정
        
    Returns:
        bool: 성공 여부
    """
    try:
        # 기존 설정 조회
        current_prefs = get_user_preferences(user_id) or {}
        
        # 새 설정과 병합
        current_prefs.update(preferences)
        
        # JSON 직렬화
        prefs_json = json.dumps(current_prefs, ensure_ascii=False)
        
        # 저장
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET preferences = ? WHERE id = ?",
            (prefs_json, user_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "환경설정 업데이트", "user_id": user_id})
        return False

def create_session(user_id, ip_address="unknown", user_agent="unknown", hours=None):
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
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 현재 활성 세션 수 확인 (제한 초과 시 가장 오래된 세션 제거)
        cursor.execute(
            """
            SELECT COUNT(*) as count, MIN(created_at) as oldest
            FROM sessions
            WHERE user_id = ? AND expires_at > ?
            """,
            (user_id, datetime.now())
        )
        
        session_info = cursor.fetchone()
        active_sessions = session_info['count'] if session_info else 0
        
        # 세션 수 제한 초과 시 가장 오래된 세션 제거
        if active_sessions >= SESSION_CONFIG['max_concurrent_sessions']:
            cursor.execute(
                """
                DELETE FROM sessions
                WHERE user_id = ? AND created_at = ?
                """,
                (user_id, session_info['oldest'])
            )
            logger.warning(f"세션 제한 초과로 오래된 세션 제거: 사용자 ID {user_id}")
        
        # 새 세션 생성
        session_id = str(uuid.uuid4())
        
        # 세션 만료 시간 설정
        if hours is None:
            hours = SESSION_CONFIG['default_expiry_hours']
        
        # 최대 만료 시간 제한
        hours = min(hours, SESSION_CONFIG['max_expiry_hours'])
        
        expires_at = datetime.now() + timedelta(hours=hours)
        
        # 사용자명 조회
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        username = user['username'] if user else None
        
        # 세션 저장
        cursor.execute(
            """
            INSERT INTO sessions (
                session_id, user_id, created_at, expires_at, 
                ip_address, user_agent, last_activity
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, datetime.now(), expires_at, 
             ip_address, user_agent, datetime.now())
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"세션 생성: {session_id} (사용자: {username})")
        return session_id
    except Exception as e:
        log_exception(logger, e, {"context": "세션 생성", "user_id": user_id})
        return None

def get_session(session_id):
    """
    세션 ID로 세션 정보 조회
    
    Args:
        session_id (str): 세션 ID
        
    Returns:
        dict or None: 세션 정보 또는 None (세션이 없는 경우)
    """
    try:
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
            # 세션 활동 시간 업데이트 (별도 함수로 분리)
            update_session_activity(session_id)
            
            # 임계값에 가까워지면 세션 자동 갱신
            time_left = (session['expires_at'] - datetime.now()).total_seconds() / 3600
            if time_left < SESSION_CONFIG['refresh_threshold_hours']:
                refresh_session(session_id)
            
            return dict(session)
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "세션 조회", "session_id": session_id})
        return None

def update_session_activity(session_id):
    """
    세션 마지막 활동 시간 업데이트
    
    Args:
        session_id (str): 세션 ID
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE sessions SET last_activity = ? WHERE session_id = ?",
            (datetime.now(), session_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "세션 활동 업데이트", "session_id": session_id})
        return False

def refresh_session(session_id, hours=None):
    """
    세션 만료 시간 연장
    
    Args:
        session_id (str): 세션 ID
        hours (int, optional): 연장할 시간 (기본값: 기본 만료 시간)
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 기본 연장 시간 설정
        if hours is None:
            hours = SESSION_CONFIG['default_expiry_hours']
        
        # 최대 만료 시간 제한
        hours = min(hours, SESSION_CONFIG['max_expiry_hours'])
        
        new_expiry = datetime.now() + timedelta(hours=hours)
        
        cursor.execute(
            "UPDATE sessions SET expires_at = ? WHERE session_id = ?",
            (new_expiry, session_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.debug(f"세션 갱신: {session_id}, 새 만료일: {new_expiry}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "세션 갱신", "session_id": session_id})
        return False

def delete_session(session_id):
    """
    세션 삭제 (로그아웃)
    
    Args:
        session_id (str): 세션 ID
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"세션 삭제: {session_id}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "세션 삭제", "session_id": session_id})
        return False

def delete_all_user_sessions(user_id):
    """
    사용자의 모든 세션 삭제
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        int: 삭제된 세션 수
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"모든 세션 삭제: 사용자 ID {user_id}, {deleted_count}개 세션")
        return deleted_count
    except Exception as e:
        log_exception(logger, e, {"context": "모든 세션 삭제", "user_id": user_id})
        return 0

def log_login_attempt(user_id, success, ip_address="unknown", user_agent="unknown", failure_reason=None):
    """
    로그인 시도 로깅
    
    Args:
        user_id (int): 사용자 ID
        success (bool): 성공 여부
        ip_address (str, optional): IP 주소
        user_agent (str, optional): 유저 에이전트
        failure_reason (str, optional): 실패 이유
        
    Returns:
        bool: 로깅 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT INTO login_logs (
                user_id, timestamp, ip_address, user_agent, success, failure_reason
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, datetime.now(), ip_address, user_agent, success, failure_reason)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "로그인 로깅", "user_id": user_id})
        return False

def check_login_attempts(user_id, hours=24):
    """
    일정 시간 내 로그인 시도 횟수 확인
    
    Args:
        user_id (int): 사용자 ID
        hours (int): 확인할 시간 범위 (시간)
        
    Returns:
        dict: 로그인 시도 정보
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 확인 기준 시간
        check_time = datetime.now() - timedelta(hours=hours)
        
        # 전체 시도 횟수
        cursor.execute(
            """
            SELECT COUNT(*) as total_attempts
            FROM login_logs
            WHERE user_id = ? AND timestamp > ?
            """,
            (user_id, check_time)
        )
        total_attempts = cursor.fetchone()['total_attempts']
        
        # 실패 시도 횟수
        cursor.execute(
            """
            SELECT COUNT(*) as failed_attempts
            FROM login_logs
            WHERE user_id = ? AND timestamp > ? AND success = 0
            """,
            (user_id, check_time)
        )
        failed_attempts = cursor.fetchone()['failed_attempts']
        
        # 마지막 로그인 시도
        cursor.execute(
            """
            SELECT timestamp, success, ip_address
            FROM login_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        last_attempt = cursor.fetchone()
        
        conn.close()
        
        return {
            'total_attempts': total_attempts,
            'failed_attempts': failed_attempts,
            'last_attempt': dict(last_attempt) if last_attempt else None
        }
    except Exception as e:
        log_exception(logger, e, {"context": "로그인 시도 확인", "user_id": user_id})
        return {
            'total_attempts': 0,
            'failed_attempts': 0,
            'last_attempt': None
        }

def hash_password(password):
    """
    비밀번호 해싱
    
    Args:
        password (str): 비밀번호
        
    Returns:
        str: 해싱된 비밀번호
    """
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 해싱"})
        # 기본 해시값 반환 (실제로는 사용되지 않아야 함)
        return "invalid_hash"

def check_password(password, hashed_password):
    """
    비밀번호 확인
    
    Args:
        password (str): 확인할 비밀번호
        hashed_password (str): 저장된 해시된 비밀번호
        
    Returns:
        bool: 비밀번호 일치 여부
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 확인"})
        return False

def change_password(user_id, new_password_hash):
    """
    비밀번호 변경
    
    Args:
        user_id (int): 사용자 ID
        new_password_hash (str): 새 비밀번호 해시
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 비밀번호 변경
        cursor.execute(
            """
            UPDATE users 
            SET password_hash = ?, password_last_changed = ?
            WHERE id = ?
            """,
            (new_password_hash, datetime.now(), user_id)
        )
        
        # 비밀번호 이력에 추가
        cursor.execute(
            "INSERT INTO password_history (user_id, password_hash, created_at) VALUES (?, ?, ?)",
            (user_id, new_password_hash, datetime.now())
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"비밀번호 변경 완료: 사용자 ID {user_id}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 변경", "user_id": user_id})
        return False

def check_password_expiry(user_id):
    """
    비밀번호 만료 확인
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        tuple: (만료 여부, 남은 일수 또는 경과 일수)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT password_last_changed FROM users WHERE id = ?",
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result['password_last_changed']:
            return True, -PASSWORD_POLICY['max_age_days']  # 정보 없음, 만료된 것으로 처리
        
        # 마지막 변경일부터 경과 일수
        last_changed = datetime.fromisoformat(result['password_last_changed'])
        days_elapsed = (datetime.now() - last_changed).days
        
        # 만료 여부 확인
        is_expired = days_elapsed >= PASSWORD_POLICY['max_age_days']
        
        if is_expired:
            return True, days_elapsed - PASSWORD_POLICY['max_age_days']  # 만료됨, 경과 일수
        else:
            return False, PASSWORD_POLICY['max_age_days'] - days_elapsed  # 유효함, 남은 일수
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 만료 확인", "user_id": user_id})
        return True, 0  # 오류 발생, 만료된 것으로 처리

def generate_password_reset_token(user_id, expires_in_hours=24):
    """
    비밀번호 재설정 토큰 생성
    
    Args:
        user_id (int): 사용자 ID
        expires_in_hours (int): 토큰 만료 시간 (시간)
        
    Returns:
        str or None: 생성된 토큰 또는 None (생성 실패시)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 기존 토큰 무효화
        cursor.execute(
            "DELETE FROM password_reset_tokens WHERE user_id = ?",
            (user_id,)
        )
        
        # 새 토큰 생성
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        cursor.execute(
            """
            INSERT INTO password_reset_tokens (user_id, token, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, token, expires_at, datetime.now())
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"비밀번호 재설정 토큰 생성: 사용자 ID {user_id}")
        return token
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 재설정 토큰 생성", "user_id": user_id})
        return None

def verify_password_reset_token(token):
    """
    비밀번호 재설정 토큰 검증
    
    Args:
        token (str): 검증할 토큰
        
    Returns:
        int or None: 사용자 ID 또는 None (토큰이 유효하지 않은 경우)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT user_id, expires_at FROM password_reset_tokens
            WHERE token = ? AND expires_at > ?
            """,
            (token, datetime.now())
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result['user_id']
        return None
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 재설정 토큰 검증", "token": token[:10] + "..."})
        return None

def invalidate_password_reset_token(token):
    """
    비밀번호 재설정 토큰 무효화
    
    Args:
        token (str): 무효화할 토큰
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM password_reset_tokens WHERE token = ?",
            (token,)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"비밀번호 재설정 토큰 무효화: {token[:10]}...")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 재설정 토큰 무효화", "token": token[:10] + "..."})
        return False

def setup_2fa(user_id, method='totp'):
    """
    2단계 인증 설정
    
    Args:
        user_id (int): 사용자 ID
        method (str): 인증 방식 ('totp', 'email', 'sms')
        
    Returns:
        dict or None: 2단계 인증 설정 정보 또는 None (설정 실패시)
    """
    try:
        import pyotp
        
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 기존 설정 확인
        cursor.execute("SELECT username, email FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return None
        
        # 기존 2FA 설정 삭제
        cursor.execute("DELETE FROM two_factor_auth WHERE user_id = ?", (user_id,))
        
        setup_data = {}
        
        if method == 'totp':
            # TOTP 비밀키 생성
            secret = pyotp.random_base32()
            
            # QR 코드 URI 생성
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user['username'], 
                issuer_name="자산관리 프로그램"
            )
            
            setup_data = {
                'secret': secret,
                'qr_uri': provisioning_uri,
                'method': 'totp'
            }
        elif method == 'email':
            if not user['email']:
                conn.close()
                return None
            
            # 이메일 인증 설정
            setup_data = {
                'email': user['email'],
                'method': 'email'
            }
        elif method == 'sms':
            # SMS 인증 설정 (실제 번호는 별도 테이블에 저장)
            setup_data = {
                'method': 'sms'
            }
        else:
            conn.close()
            return None
        
        # 설정 저장
        cursor.execute(
            """
            INSERT INTO two_factor_auth (
                user_id, method, secret, enabled, created_at, last_used
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, 
                method, 
                json.dumps(setup_data, ensure_ascii=False), 
                False,  # 초기에는 비활성화
                datetime.now(),
                None
            )
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"2FA 설정 생성: 사용자 ID {user_id}, 방식: {method}")
        return setup_data
    except Exception as e:
        log_exception(logger, e, {"context": "2FA 설정", "user_id": user_id, "method": method})
        return None

def enable_2fa(user_id, verification_code=None):
    """
    2단계 인증 활성화
    
    Args:
        user_id (int): 사용자 ID
        verification_code (str, optional): 인증 코드 (TOTP 방식에서 필요)
        
    Returns:
        bool: 성공 여부
    """
    try:
        import pyotp
        
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 2FA 설정 조회
        cursor.execute("SELECT * FROM two_factor_auth WHERE user_id = ?", (user_id,))
        tfa_record = cursor.fetchone()
        
        if not tfa_record:
            conn.close()
            return False
        
        method = tfa_record['method']
        secret_data = json.loads(tfa_record['secret'])
        
        # TOTP 방식인 경우 인증 코드 검증
        if method == 'totp' and verification_code:
            totp = pyotp.TOTP(secret_data['secret'])
            if not totp.verify(verification_code):
                conn.close()
                return False
        
        # 2FA 활성화
        cursor.execute(
            "UPDATE two_factor_auth SET enabled = 1 WHERE user_id = ?",
            (user_id,)
        )
        
        # 사용자 프로필에 2FA 설정 표시
        cursor.execute(
            "UPDATE users SET two_factor_enabled = 1 WHERE id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"2FA 활성화 완료: 사용자 ID {user_id}, 방식: {method}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "2FA 활성화", "user_id": user_id})
        return False

def disable_2fa(user_id):
    """
    2단계 인증 비활성화
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 2FA 설정 비활성화
        cursor.execute(
            "UPDATE two_factor_auth SET enabled = 0 WHERE user_id = ?",
            (user_id,)
        )
        
        # 사용자 프로필 업데이트
        cursor.execute(
            "UPDATE users SET two_factor_enabled = 0 WHERE id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"2FA 비활성화: 사용자 ID {user_id}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "2FA 비활성화", "user_id": user_id})
        return False

def verify_2fa_code(user_id, code):
    """
    2단계 인증 코드 검증
    
    Args:
        user_id (int): 사용자 ID
        code (str): 검증할 코드
        
    Returns:
        bool: 유효성 여부
    """
    try:
        import pyotp
        
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 2FA 설정 조회
        cursor.execute(
            """
            SELECT * FROM two_factor_auth
            WHERE user_id = ? AND enabled = 1
            """,
            (user_id,)
        )
        
        tfa_record = cursor.fetchone()
        
        if not tfa_record:
            conn.close()
            return False
        
        method = tfa_record['method']
        secret_data = json.loads(tfa_record['secret'])
        
        is_valid = False
        
        if method == 'totp':
            # TOTP 방식 검증
            totp = pyotp.TOTP(secret_data['secret'])
            is_valid = totp.verify(code)
        elif method in ['email', 'sms']:
            # 다른 인증 방식 (임시 코드 저장 테이블 조회)
            cursor.execute(
                """
                SELECT * FROM verification_codes
                WHERE user_id = ? AND code = ? AND expires_at > ? AND used = 0
                """,
                (user_id, code, datetime.now())
            )
            
            code_record = cursor.fetchone()
            
            if code_record:
                # 코드 사용 완료 처리
                cursor.execute(
                    "UPDATE verification_codes SET used = 1 WHERE id = ?",
                    (code_record['id'],)
                )
                is_valid = True
        
        if is_valid:
            # 마지막 사용 시간 업데이트
            cursor.execute(
                "UPDATE two_factor_auth SET last_used = ? WHERE user_id = ?",
                (datetime.now(), user_id)
            )
        
        conn.commit()
        conn.close()
        
        return is_valid
    except Exception as e:
        log_exception(logger, e, {"context": "2FA 검증", "user_id": user_id})
        return False

def generate_verification_code(user_id, method, expires_in_minutes=10):
    """
    이메일/SMS 인증 코드 생성
    
    Args:
        user_id (int): 사용자 ID
        method (str): 인증 방식 ('email', 'sms')
        expires_in_minutes (int): 만료 시간 (분)
        
    Returns:
        str or None: 생성된 인증 코드 또는 None (생성 실패시)
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 기존 코드 무효화
        cursor.execute(
            """
            UPDATE verification_codes
            SET expires_at = ?
            WHERE user_id = ? AND method = ? AND used = 0
            """,
            (datetime.now(), user_id, method)
        )
        
        # 새 인증 코드 생성 (6자리 숫자)
        code = ''.join(random.choices(string.digits, k=6))
        expires_at = datetime.now() + timedelta(minutes=expires_in_minutes)
        
        cursor.execute(
            """
            INSERT INTO verification_codes (
                user_id, code, method, created_at, expires_at, used
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, code, method, datetime.now(), expires_at, False)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"인증 코드 생성: 사용자 ID {user_id}, 방식: {method}")
        return code
    except Exception as e:
        log_exception(logger, e, {"context": "인증 코드 생성", "user_id": user_id, "method": method})
        return None

def verify_verification_code(user_id, code, method):
    """
    이메일/SMS 인증 코드 검증
    
    Args:
        user_id (int): 사용자 ID
        code (str): 검증할 코드
        method (str): 인증 방식 ('email', 'sms')
        
    Returns:
        bool: 유효성 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT * FROM verification_codes
            WHERE user_id = ? AND code = ? AND method = ? AND expires_at > ? AND used = 0
            """,
            (user_id, code, method, datetime.now())
        )
        
        code_record = cursor.fetchone()
        
        if code_record:
            # 코드 사용 완료 처리
            cursor.execute(
                "UPDATE verification_codes SET used = 1 WHERE id = ?",
                (code_record['id'],)
            )
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    except Exception as e:
        log_exception(logger, e, {"context": "인증 코드 검증", "user_id": user_id, "method": method})
        return False
        
        cursor.execute(
            "SELECT password_last_changed FROM users WHERE id = ?",
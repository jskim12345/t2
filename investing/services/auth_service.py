"""
사용자 인증 관련 서비스 - 보안 강화 및 고급 인증 기능 추가
"""
from datetime import datetime, timedelta
import uuid
import os
import time
import re
import secrets
import json
import base64
import hashlib

from models.user import (
    get_user_by_username, 
    get_user_by_email,
    create_user, 
    update_last_login, 
    create_session, 
    get_session, 
    delete_session,
    delete_all_user_sessions,
    log_login_attempt, 
    hash_password, 
    check_password,
    validate_password,
    check_password_history,
    change_password,
    check_password_expiry,
    generate_password_reset_token,
    verify_password_reset_token,
    invalidate_password_reset_token,
    setup_2fa,
    enable_2fa,
    disable_2fa,
    verify_2fa_code,
    generate_verification_code,
    verify_verification_code,
    update_profile_settings,
    update_user_preferences
)
from utils.logging import get_logger, log_exception

logger = get_logger(__name__)

# 보안 설정
SECURITY_CONFIG = {
    'max_login_attempts': 5,               # 로그인 시도 제한 횟수
    'lockout_period_minutes': 30,          # 계정 잠금 기간 (분)
    'require_email_verification': True,    # 이메일 인증 필요 여부
    'password_reset_expiry_hours': 24,     # 비밀번호 재설정 링크 만료 시간
    'session_expiry_hours': 24,            # 세션 기본 만료 시간
    'remember_me_days': 30,                # 자동 로그인 유지 기간
    'enforce_2fa_for_admins': True,        # 관리자는 2FA 필수 사용
    'check_ip_change': True                # IP 변경 시 재인증 필요 여부
}

def register_user(username, password, email=None, profile_data=None):
    """
    사용자 등록
    
    Args:
        username (str): 사용자명
        password (str): 비밀번호
        email (str, optional): 이메일
        profile_data (dict, optional): 프로필 데이터
        
    Returns:
        tuple: (성공 여부, 메시지, 사용자 ID)
    """
    # 입력값 검증
    if not username or not password:
        return False, "사용자명과 비밀번호는 필수 입력값입니다.", None
    
    # 사용자명 유효성 검사
    if not re.match(r'^[a-zA-Z0-9_]{4,20}$', username):
        return False, "사용자명은 4-20자의 영문, 숫자, 밑줄(_)만 사용 가능합니다.", None
    
    # 이메일 유효성 검사
    if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False, "유효하지 않은 이메일 형식입니다.", None
    
    # 중복 사용자 확인
    if get_user_by_username(username):
        return False, "이미 사용 중인 사용자명입니다.", None
    
    # 이메일 중복 확인
    if email and get_user_by_email(email):
        return False, "이미 사용 중인 이메일입니다.", None
    
    # 비밀번호 강도 검증
    is_valid_password, password_msg = validate_password(password)
    if not is_valid_password:
        return False, password_msg, None
    
    # 비밀번호 해싱
    hashed_password = hash_password(password)
    
    # 사용자 생성
    user_id = create_user(
        username, 
        hashed_password, 
        email, 
        profile_data,
        SECURITY_CONFIG['require_email_verification']
    )
    
    if not user_id:
        return False, "사용자 등록 중 오류가 발생했습니다.", None
    
    # 이메일 인증이 필요한 경우 인증 메일 발송
    if SECURITY_CONFIG['require_email_verification'] and email:
        try:
            send_verification_email(user_id, email, username)
            logger.info(f"인증 이메일 발송: {email}, 사용자: {username}")
        except Exception as e:
            log_exception(logger, e, {"context": "인증 이메일 발송", "username": username, "email": email})
            # 이메일 발송 실패해도 가입은 완료로 처리
    
    logger.info(f"사용자 등록 성공: {username} (ID: {user_id})")
    return True, "사용자 등록 완료", user_id

def authenticate_user(username, password, ip_address="unknown", user_agent="unknown", remember_me=False, require_2fa=False):
    """
    사용자 인증
    
    Args:
        username (str): 사용자명
        password (str): 비밀번호
        ip_address (str, optional): IP 주소
        user_agent (str, optional): 유저 에이전트
        remember_me (bool, optional): 자동 로그인 여부
        require_2fa (bool, optional): 2단계 인증 요구 여부
        
    Returns:
        tuple: (성공 여부, 세션 ID 또는 None, 메시지, 2FA 필요 여부)
    """
    # 사용자 정보 조회
    user = get_user_by_username(username)
    
    if not user:
        # 가입되지 않은 사용자 또는 이메일로 로그인 시도
        if '@' in username:
            user = get_user_by_email(username)
            if not user:
                logger.warning(f"로그인 실패 (사용자 없음): {username}")
                return False, None, "등록되지 않은 사용자입니다.", False
        else:
            logger.warning(f"로그인 실패 (사용자 없음): {username}")
            return False, None, "등록되지 않은 사용자입니다.", False
    
    # 계정 상태 확인
    account_status = user.get('account_status', 'active')
    if account_status != 'active':
        status_messages = {
            'locked': "계정이 잠겼습니다. 관리자에게 문의하세요.",
            'suspended': "계정이 일시 정지되었습니다.",
            'deleted': "계정이 삭제되었습니다.",
            'pending': "계정 승인 대기 중입니다."
        }
        return False, None, status_messages.get(account_status, "계정 상태가 유효하지 않습니다."), False
    
    # 이메일 인증 확인
    if SECURITY_CONFIG['require_email_verification'] and not user.get('email_verified', False):
        return False, None, "이메일 인증이 필요합니다. 가입 시 발송된 이메일을 확인해주세요.", False
    
    # 로그인 시도 제한 확인
    if is_account_locked(user['id']):
        log_login_attempt(user['id'], False, ip_address, user_agent, "계정 잠금")
        return False, None, f"로그인 시도 횟수를 초과했습니다. {SECURITY_CONFIG['lockout_period_minutes']}분 후에 다시 시도해주세요.", False
    
    # 비밀번호 검증
    if not check_password(password, user['password_hash']):
        # 로그인 실패 로그 기록
        log_login_attempt(user['id'], False, ip_address, user_agent, "비밀번호 불일치")
        logger.warning(f"로그인 실패 (비밀번호 불일치): {username}")
        
        # 로그인 실패 횟수 증가 처리
        if increment_failed_login_attempts(user['id']) >= SECURITY_CONFIG['max_login_attempts']:
            lock_account(user['id'])
            return False, None, "로그인 시도 횟수를 초과했습니다. 계정이 일시적으로 잠겼습니다.", False
        
        remaining_attempts = SECURITY_CONFIG['max_login_attempts'] - get_failed_login_attempts(user['id'])
        return False, None, f"로그인 실패: 잘못된 비밀번호입니다. (남은 시도 횟수: {remaining_attempts})", False
    
    # 비밀번호 만료 확인
    is_expired, days = check_password_expiry(user['id'])
    if is_expired:
        # 비밀번호가 만료되었지만 로그인은 허용
        # 하지만 비밀번호 변경 페이지로 리다이렉트되어야 함
        logger.warning(f"비밀번호 만료 로그인: {username}, {days}일 경과")
        # 여기서는 일단 로그인을 진행하고, 앱에서 상태에 따라 비밀번호 변경 요구
    
    # 2단계 인증 확인
    has_2fa = user.get('two_factor_enabled', False)
    
    if has_2fa and require_2fa:
        # 2단계 인증이 필요한 경우, 1단계 인증 성공 상태로 반환
        log_login_attempt(user['id'], True, ip_address, user_agent, "1단계 인증 성공")
        return True, None, "2단계 인증이 필요합니다.", True
    
    # 로그인 성공 처리
    update_last_login(user['id'])
    
    # 실패 로그인 시도 초기화
    reset_failed_login_attempts(user['id'])
    
    # 세션 만료 시간 설정
    session_hours = SECURITY_CONFIG['session_expiry_hours']
    if remember_me:
        session_hours = SECURITY_CONFIG['remember_me_days'] * 24
    
    # 세션 생성
    session_id = create_session(user['id'], ip_address, user_agent, session_hours)
    
    # 로그인 성공 로그 기록
    log_login_attempt(user['id'], True, ip_address, user_agent)
    
    logger.info(f"로그인 성공: {username} (IP: {ip_address})")
    return True, session_id, "로그인 성공", False

def validate_session(session_id, ip_address=None):
    """
    세션 유효성 검증
    
    Args:
        session_id (str): 세션 ID
        ip_address (str, optional): 현재 IP 주소 (IP 변경 감지용)
        
    Returns:
        tuple: (유효성 여부, 세션 데이터 또는 None, 메시지)
    """
    if not session_id:
        return False, None, "세션이 없습니다."
    
    session = get_session(session_id)
    
    if not session:
        return False, None, "세션이 만료되었거나 유효하지 않습니다."
    
    # IP 변경 감지 (선택적)
    if SECURITY_CONFIG['check_ip_change'] and ip_address and session['ip_address'] != ip_address:
        logger.warning(f"세션 IP 변경 감지: {session['ip_address']} -> {ip_address}, 사용자: {session['username']}")
        # 여기서는 경고만 기록하고 세션은 유효함으로 처리
        # 보안 수준에 따라 세션을 무효화할 수도 있음
    
    # 세션 데이터 반환
    return True, {
        "user_id": session['user_id'],
        "username": session['username'],
        "created_at": session['created_at'],
        "expires_at": session['expires_at'],
        "ip_address": session['ip_address'],
        "user_agent": session['user_agent'],
        "last_activity": session['last_activity']
    }, "유효한 세션"

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

def logout_all_sessions(user_id):
    """
    사용자의 모든 세션 종료 (모든 기기에서 로그아웃)
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        int: 종료된 세션 수
    """
    count = delete_all_user_sessions(user_id)
    logger.info(f"모든 세션 로그아웃: 사용자 ID {user_id}, {count}개 세션 삭제")
    return count

def change_user_password(user_id, current_password, new_password):
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
    
    # 새 비밀번호 유효성 검사
    is_valid, message = validate_password(new_password)
    if not is_valid:
        return False, message
    
    # 이전 비밀번호 재사용 검사
    if not check_password_history(user_id, new_password):
        return False, "최근에 사용한 비밀번호는 재사용할 수 없습니다."
    
    # 새 비밀번호 해싱
    new_password_hash = hash_password(new_password)
    
    # 비밀번호 업데이트
    if change_password(user_id, new_password_hash):
        # 보안을 위해 모든 기존 세션 종료 (선택적)
        if SECURITY_CONFIG.get('logout_on_password_change', True):
            logout_all_sessions(user_id)
        
        logger.info(f"비밀번호 변경 성공: 사용자 ID {user_id}")
        return True, "비밀번호가 변경되었습니다."
    else:
        logger.error(f"비밀번호 변경 실패: 사용자 ID {user_id}")
        return False, "비밀번호 변경 중 오류가 발생했습니다."

def request_password_reset(email_or_username):
    """
    비밀번호 재설정 요청
    
    Args:
        email_or_username (str): 이메일 또는 사용자명
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    # 사용자 조회
    user = None
    if '@' in email_or_username:
        user = get_user_by_email(email_or_username)
    else:
        user = get_user_by_username(email_or_username)
    
    if not user:
        # 보안을 위해 사용자가 없어도 성공 메시지 반환
        logger.info(f"존재하지 않는 계정의 비밀번호 재설정 요청: {email_or_username}")
        return True, "비밀번호 재설정 링크가 이메일로 발송되었습니다."
    
    # 이메일이 없는 경우
    if not user.get('email'):
        logger.warning(f"이메일 없는 계정의 비밀번호 재설정 요청: {user['username']}")
        return False, "이메일이 등록되지 않은 계정입니다. 관리자에게 문의하세요."
    
    # 계정 상태 확인
    if user.get('account_status', 'active') != 'active':
        logger.warning(f"비활성 계정의 비밀번호 재설정 요청: {user['username']}, 상태: {user['account_status']}")
        return False, "계정이 활성 상태가 아닙니다. 관리자에게 문의하세요."
    
    # 비밀번호 재설정 토큰 생성
    token = generate_password_reset_token(
        user['id'], 
        SECURITY_CONFIG['password_reset_expiry_hours']
    )
    
    if not token:
        logger.error(f"비밀번호 재설정 토큰 생성 실패: {user['username']}")
        return False, "비밀번호 재설정 처리 중 오류가 발생했습니다."
    
    # 재설정 이메일 발송
    try:
        send_password_reset_email(user['email'], user['username'], token)
        logger.info(f"비밀번호 재설정 이메일 발송: {user['email']}, 사용자: {user['username']}")
        return True, "비밀번호 재설정 링크가 이메일로 발송되었습니다."
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 재설정 이메일 발송", "username": user['username']})
        return False, "이메일 발송 중 오류가 발생했습니다."

def reset_password_with_token(token, new_password):
    """
    토큰을 사용하여 비밀번호 재설정
    
    Args:
        token (str): 비밀번호 재설정 토큰
        new_password (str): 새 비밀번호
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    # 토큰 검증
    user_id = verify_password_reset_token(token)
    
    if not user_id:
        logger.warning(f"유효하지 않은 비밀번호 재설정 토큰: {token[:10]}...")
        return False, "유효하지 않거나 만료된 재설정 링크입니다."
    
    # 비밀번호 유효성 검사
    is_valid, message = validate_password(new_password)
    if not is_valid:
        return False, message
    
    # 이전 비밀번호 재사용 검사
    if not check_password_history(user_id, new_password):
        return False, "최근에 사용한 비밀번호는 재사용할 수 없습니다."
    
    # 새 비밀번호 해싱
    new_password_hash = hash_password(new_password)
    
    # 비밀번호 업데이트
    if change_password(user_id, new_password_hash):
        # 토큰 무효화
        invalidate_password_reset_token(token)
        
        # 모든 기존 세션 종료
        logout_all_sessions(user_id)
        
        logger.info(f"토큰을 통한 비밀번호 재설정 성공: 사용자 ID {user_id}")
        return True, "비밀번호가 성공적으로 재설정되었습니다. 새 비밀번호로 로그인해주세요."
    else:
        logger.error(f"토큰을 통한 비밀번호 재설정 실패: 사용자 ID {user_id}")
        return False, "비밀번호 재설정 중 오류가 발생했습니다."

def verify_email(token):
    """
    이메일 인증 처리
    
    Args:
        token (str): 이메일 인증 토큰
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    try:
        # 토큰 디코딩 및 검증
        token_parts = token.split('.')
        if len(token_parts) != 3:
            return False, "유효하지 않은 인증 토큰입니다."
        
        # 토큰 해싱 파트 검증
        user_id_b64, timestamp_b64, signature = token_parts
        
        # 원본 데이터 복원
        user_id = base64.b64decode(user_id_b64).decode('utf-8')
        timestamp = int(base64.b64decode(timestamp_b64).decode('utf-8'))
        
        # 토큰 만료 확인
        current_time = int(time.time())
        if current_time - timestamp > 3 * 24 * 60 * 60:  # 3일
            return False, "인증 링크가 만료되었습니다. 새 인증 이메일을 요청해주세요."
        
        # 시그니처 검증
        expected_signature = compute_email_token_signature(user_id, timestamp)
        if signature != expected_signature:
            return False, "유효하지 않은 인증 토큰입니다."
        
        # 사용자 조회
        from models.user import get_user_by_id
        user = get_user_by_id(int(user_id))
        
        if not user:
            return False, "사용자를 찾을 수 없습니다."
        
        # 이미 인증된 경우
        if user.get('email_verified', False):
            return True, "이미 인증된 이메일입니다."
        
        # 이메일 인증 처리
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET email_verified = 1, verification_code = NULL, verification_expiry = NULL WHERE id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"이메일 인증 성공: 사용자 ID {user_id}")
        return True, "이메일이 성공적으로 인증되었습니다. 이제 로그인할 수 있습니다."
    except Exception as e:
        log_exception(logger, e, {"context": "이메일 인증", "token": token[:10] + "..."})
        return False, "인증 처리 중 오류가 발생했습니다."

def resend_verification_email(email):
    """
    인증 이메일 재발송
    
    Args:
        email (str): 이메일 주소
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    # 사용자 조회
    user = get_user_by_email(email)
    
    if not user:
        # 보안을 위해 사용자가 없어도 성공 메시지 반환
        logger.info(f"존재하지 않는 계정의 인증 이메일 재발송 요청: {email}")
        return True, "인증 이메일이 발송되었습니다. 이메일을 확인해주세요."
    
    # 이미 인증된 경우
    if user.get('email_verified', False):
        return True, "이미 인증된 이메일입니다. 로그인해주세요."
    
    # 인증 이메일 발송
    try:
        send_verification_email(user['id'], email, user['username'])
        logger.info(f"인증 이메일 재발송: {email}, 사용자: {user['username']}")
        return True, "인증 이메일이 발송되었습니다. 이메일을 확인해주세요."
    except Exception as e:
        log_exception(logger, e, {"context": "인증 이메일 재발송", "email": email})
        return False, "이메일 발송 중 오류가 발생했습니다."

def setup_user_2fa(user_id, method='totp'):
    """
    2단계 인증 설정
    
    Args:
        user_id (int): 사용자 ID
        method (str): 인증 방식 ('totp', 'email', 'sms')
        
    Returns:
        tuple: (성공 여부, 설정 데이터 또는 오류 메시지)
    """
    setup_data = setup_2fa(user_id, method)
    
    if not setup_data:
        return False, "2단계 인증 설정 중 오류가 발생했습니다."
    
    logger.info(f"2FA 설정 시작: 사용자 ID {user_id}, 방식: {method}")
    return True, setup_data

def confirm_2fa_setup(user_id, verification_code):
    """
    2단계 인증 설정 확인 및 활성화
    
    Args:
        user_id (int): 사용자 ID
        verification_code (str): 확인 코드
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    if enable_2fa(user_id, verification_code):
        logger.info(f"2FA 설정 완료: 사용자 ID {user_id}")
        return True, "2단계 인증이 성공적으로 설정되었습니다."
    else:
        logger.warning(f"2FA 설정 실패: 사용자 ID {user_id}, 잘못된 코드")
        return False, "인증 코드가 유효하지 않습니다. 다시 시도해주세요."

def verify_2fa(user_id, verification_code):
    """
    2단계 인증 코드 검증
    
    Args:
        user_id (int): 사용자 ID
        verification_code (str): 인증 코드
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    if verify_2fa_code(user_id, verification_code):
        logger.info(f"2FA 인증 성공: 사용자 ID {user_id}")
        return True, "인증 성공"
    else:
        logger.warning(f"2FA 인증 실패: 사용자 ID {user_id}, 잘못된 코드")
        return False, "인증 코드가 유효하지 않습니다. 다시 시도해주세요."

def disable_user_2fa(user_id, password):
    """
    2단계 인증 비활성화
    
    Args:
        user_id (int): 사용자 ID
        password (str): 비밀번호 (확인용)
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    # 비밀번호 확인
    from models.user import get_user_by_id
    user = get_user_by_id(user_id)
    
    if not user:
        return False, "사용자를 찾을 수 없습니다."
    
    if not check_password(password, user['password_hash']):
        return False, "비밀번호가 일치하지 않습니다."
    
    # 2FA 비활성화
    if disable_2fa(user_id):
        logger.info(f"2FA 비활성화: 사용자 ID {user_id}")
        return True, "2단계 인증이 비활성화되었습니다."
    else:
        logger.error(f"2FA 비활성화 실패: 사용자 ID {user_id}")
        return False, "2단계 인증 비활성화 중 오류가 발생했습니다."

def send_2fa_code(user_id, method='email'):
    """
    2단계 인증 코드 발송
    
    Args:
        user_id (int): 사용자 ID
        method (str): 전송 방식 ('email', 'sms')
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    # 사용자 정보 조회
    from models.user import get_user_by_id
    user = get_user_by_id(user_id)
    
    if not user:
        return False, "사용자를 찾을 수 없습니다."
    
    # 인증 방식에 따라 처리
    if method == 'email':
        if not user.get('email'):
            return False, "등록된 이메일이 없습니다."
        
        # 인증 코드 생성
        code = generate_verification_code(user_id, 'email')
        if not code:
            return False, "인증 코드 생성 중 오류가 발생했습니다."
        
        # 이메일 발송
        try:
            send_verification_code_email(user['email'], code)
            return True, "인증 코드가 이메일로 발송되었습니다."
        except Exception as e:
            log_exception(logger, e, {"context": "2FA 이메일 코드 발송", "user_id": user_id})
            return False, "이메일 발송 중 오류가 발생했습니다."
    
    elif method == 'sms':
        # SMS 기능은 별도 구현 필요
        return False, "SMS 인증은 현재 지원되지 않습니다."
    
    else:
        return False, "지원되지 않는 인증 방식입니다."

def is_account_locked(user_id):
    """
    계정 잠금 여부 확인
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        bool: 잠금 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        # 계정 상태 확인
        cursor.execute("SELECT account_status FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if result and result['account_status'] == 'locked':
            # 잠금 시간 확인 (일정 시간 경과 후 자동 해제)
            cursor.execute(
                """
                SELECT lockout_time FROM users WHERE id = ? AND lockout_time IS NOT NULL
                """,
                (user_id,)
            )
            
            lockout = cursor.fetchone()
            
            if lockout and lockout['lockout_time']:
                lockout_time = datetime.fromisoformat(lockout['lockout_time'])
                elapsed_minutes = (datetime.now() - lockout_time).total_seconds() / 60
                
                # 잠금 기간 경과 시 자동 해제
                if elapsed_minutes > SECURITY_CONFIG['lockout_period_minutes']:
                    cursor.execute(
                        """
                        UPDATE users 
                        SET account_status = 'active', lockout_time = NULL, failed_login_attempts = 0
                        WHERE id = ?
                        """,
                        (user_id,)
                    )
                    conn.commit()
                    conn.close()
                    return False
                
                conn.close()
                return True
        
        conn.close()
        return False
    except Exception as e:
        log_exception(logger, e, {"context": "계정 잠금 확인", "user_id": user_id})
        return False

def lock_account(user_id):
    """
    계정 잠금
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE users 
            SET account_status = 'locked', lockout_time = ?
            WHERE id = ?
            """,
            (datetime.now(), user_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.warning(f"계정 잠금: 사용자 ID {user_id}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "계정 잠금", "user_id": user_id})
        return False

def unlock_account(user_id):
    """
    계정 잠금 해제
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE users 
            SET account_status = 'active', lockout_time = NULL, failed_login_attempts = 0
            WHERE id = ?
            """,
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"계정 잠금 해제: 사용자 ID {user_id}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "계정 잠금 해제", "user_id": user_id})
        return False

def get_failed_login_attempts(user_id):
    """
    실패한 로그인 시도 횟수 조회
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        int: 실패 시도 횟수
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute("SELECT failed_login_attempts FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result and result['failed_login_attempts']:
            return result['failed_login_attempts']
        return 0
    except Exception as e:
        log_exception(logger, e, {"context": "로그인 실패 횟수 조회", "user_id": user_id})
        return 0

def increment_failed_login_attempts(user_id):
    """
    실패한 로그인 시도 횟수 증가
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        int: 업데이트된 실패 시도 횟수
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE users 
            SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1
            WHERE id = ?
            """,
            (user_id,)
        )
        
        cursor.execute("SELECT failed_login_attempts FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        if result:
            return result['failed_login_attempts']
        return 0
    except Exception as e:
        log_exception(logger, e, {"context": "로그인 실패 횟수 증가", "user_id": user_id})
        return 0

def reset_failed_login_attempts(user_id):
    """
    실패한 로그인 시도 횟수 초기화
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        bool: 성공 여부
    """
    try:
        conn = get_db_connection('users')
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET failed_login_attempts = 0 WHERE id = ?",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "로그인 실패 횟수 초기화", "user_id": user_id})
        return False

def update_user_profile(user_id, profile_data):
    """
    사용자 프로필 업데이트
    
    Args:
        user_id (int): 사용자 ID
        profile_data (dict): 프로필 데이터
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    if not profile_data:
        return False, "업데이트할 프로필 데이터가 없습니다."
    
    if update_profile_settings(user_id, profile_data):
        logger.info(f"프로필 업데이트: 사용자 ID {user_id}")
        return True, "프로필이 업데이트되었습니다."
    else:
        logger.error(f"프로필 업데이트 실패: 사용자 ID {user_id}")
        return False, "프로필 업데이트 중 오류가 발생했습니다."

def update_app_preferences(user_id, preferences):
    """
    앱 환경설정 업데이트
    
    Args:
        user_id (int): 사용자 ID
        preferences (dict): 환경설정 데이터
        
    Returns:
        tuple: (성공 여부, 메시지)
    """
    if not preferences:
        return False, "업데이트할 환경설정이 없습니다."
    
    if update_user_preferences(user_id, preferences):
        logger.info(f"환경설정 업데이트: 사용자 ID {user_id}")
        return True, "환경설정이 업데이트되었습니다."
    else:
        logger.error(f"환경설정 업데이트 실패: 사용자 ID {user_id}")
        return False, "환경설정 업데이트 중 오류가 발생했습니다."

def compute_email_token_signature(user_id, timestamp):
    """
    이메일 인증 토큰 시그니처 계산
    
    Args:
        user_id (str): 사용자 ID
        timestamp (int): 타임스탬프
        
    Returns:
        str: 시그니처
    """
    # 실제 구현에서는 안전한 서버 비밀키 사용
    secret_key = os.environ.get('EMAIL_VERIFICATION_SECRET', 'default_secret_key')
    
    # 시그니처 계산
    message = f"{user_id}.{timestamp}"
    signature = hmac_sha256(secret_key, message)
    
    return signature

def hmac_sha256(key, message):
    """
    HMAC-SHA256 해시 계산
    
    Args:
        key (str): 키
        message (str): 메시지
        
    Returns:
        str: 해시값 (base64)
    """
    import hmac
    
    key_bytes = key.encode('utf-8')
    message_bytes = message.encode('utf-8')
    
    h = hmac.new(key_bytes, message_bytes, hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')

def create_email_verification_token(user_id):
    """
    이메일 인증 토큰 생성
    
    Args:
        user_id (int): 사용자 ID
        
    Returns:
        str: 인증 토큰
    """
    # 타임스탬프
    timestamp = int(time.time())
    
    # 사용자 ID와 타임스탬프를 base64로 인코딩
    user_id_b64 = base64.b64encode(str(user_id).encode('utf-8')).decode('utf-8')
    timestamp_b64 = base64.b64encode(str(timestamp).encode('utf-8')).decode('utf-8')
    
    # 시그니처 계산
    signature = compute_email_token_signature(str(user_id), timestamp)
    
    # 토큰 생성
    token = f"{user_id_b64}.{timestamp_b64}.{signature}"
    
    return token

def send_verification_email(user_id, email, username):
    """
    이메일 인증 메일 발송
    
    Args:
        user_id (int): 사용자 ID
        email (str): 이메일 주소
        username (str): 사용자명
        
    Returns:
        bool: 성공 여부
    """
    # 이메일 템플릿 및 전송 로직은 실제 구현 시 추가
    # 여기서는 이메일 전송을 시뮬레이션
    
    # 인증 토큰 생성
    token = create_email_verification_token(user_id)
    
    # 인증 링크 생성
    verification_link = f"http://localhost:7860/verify_email?token={token}"
    
    # 이메일 내용 생성
    subject = "이메일 인증 안내"
    body = f"""안녕하세요, {username}님!

자산관리 프로그램에 가입해 주셔서 감사합니다.
아래 링크를 클릭하여 이메일 인증을 완료해 주세요:

{verification_link}

이 링크는 3일 동안 유효합니다.
본인이 가입하지 않았다면 이 이메일을 무시해 주세요.

감사합니다,
자산관리 프로그램 팀
"""
    
    # 이메일 전송 로직 (실제 구현 필요)
    try:
        # send_email(email, subject, body)
        logger.info(f"인증 이메일 발송 성공: {email}, 사용자: {username}")
        logger.debug(f"인증 링크: {verification_link}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "인증 이메일 발송", "email": email})
        return False

def send_password_reset_email(email, username, token):
    """
    비밀번호 재설정 이메일 발송
    
    Args:
        email (str): 이메일 주소
        username (str): 사용자명
        token (str): 재설정 토큰
        
    Returns:
        bool: 성공 여부
    """
    # 재설정 링크 생성
    reset_link = f"http://localhost:7860/reset_password?token={token}"
    
    # 이메일 내용 생성
    subject = "비밀번호 재설정 안내"
    body = f"""안녕하세요, {username}님!

비밀번호 재설정 요청이 접수되었습니다.
아래 링크를 클릭하여 새 비밀번호를 설정해 주세요:

{reset_link}

이 링크는 24시간 동안 유효합니다.
본인이 요청하지 않았다면 이 이메일을 무시하고, 계정 보안을 확인해 주세요.

감사합니다,
자산관리 프로그램 팀
"""
    
    # 이메일 전송 로직 (실제 구현 필요)
    try:
        # send_email(email, subject, body)
        logger.info(f"비밀번호 재설정 이메일 발송 성공: {email}, 사용자: {username}")
        logger.debug(f"재설정 링크: {reset_link}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "비밀번호 재설정 이메일 발송", "email": email})
        return False

def send_verification_code_email(email, code):
    """
    인증 코드 이메일 발송
    
    Args:
        email (str): 이메일 주소
        code (str): 인증 코드
        
    Returns:
        bool: 성공 여부
    """
    # 이메일 내용 생성
    subject = "2단계 인증 코드"
    body = f"""안녕하세요!

요청하신 2단계 인증 코드입니다:

{code}

이 코드는 10분 동안 유효합니다.
본인이 요청하지 않았다면 이 이메일을 무시하고, 계정 보안을 확인해 주세요.

감사합니다,
자산관리 프로그램 팀
"""
    
    # 이메일 전송 로직 (실제 구현 필요)
    try:
        # send_email(email, subject, body)
        logger.info(f"인증 코드 이메일 발송 성공: {email}, 코드: {code}")
        return True
    except Exception as e:
        log_exception(logger, e, {"context": "인증 코드 이메일 발송", "email": email})
        return False
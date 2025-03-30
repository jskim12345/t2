"""
로깅 설정 모듈
"""
import os
import logging
from datetime import datetime

# 로거 캐시 (중복 생성 방지)
_loggers = {}

def setup_logging():
    """
    애플리케이션 로깅 설정
    
    Returns:
        logging.Logger: 루트 로거
    """
    # 로그 디렉토리 생성
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    
    # 이미 핸들러가 설정되어 있으면 추가 설정 생략
    if root_logger.hasHandlers():
        return root_logger
    
    # 로그 레벨 설정
    root_logger.setLevel(logging.INFO)
    
    # 현재 날짜로 로그 파일명 생성
    log_file = os.path.join('logs', f'app_{datetime.now().strftime("%Y%m%d")}.log')
    
    # 파일 핸들러 (모든 로그 저장)
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # 콘솔 핸들러 (INFO 이상 로그 출력)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # 핸들러 추가
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

def get_logger(name):
    """
    지정된 이름으로 로거 생성 또는 캐시된 로거 반환
    
    Args:
        name (str): 로거 이름
        
    Returns:
        logging.Logger: 로거 인스턴스
    """
    # 이미 생성된 로거가 있으면 반환
    if name in _loggers:
        return _loggers[name]
    
    # 루트 로거 설정 확인
    root_logger = logging.getLogger()
    if not root_logger.hasHandlers():
        setup_logging()
    
    # 하위 로거 생성
    logger = logging.getLogger(name)
    _loggers[name] = logger
    
    return logger
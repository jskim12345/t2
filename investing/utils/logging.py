"""
로깅 설정 모듈 - 고급 로깅 기능 지원
"""
import os
import logging
import logging.handlers
from datetime import datetime
import json
import traceback

_loggers = {}

def log_exception(logger, e, context=None):
    """
    예외를 상세하게 로깅
    
    Args:
        logger (logging.Logger): 로거 인스턴스
        e (Exception): 발생한 예외
        context (dict, optional): 추가 컨텍스트 정보
    """
    exc_info = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    
    log_data = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": exc_info
    }
    
    if context:
        log_data["context"] = context
    
    logger.error(f"예외 발생: {json.dumps(log_data, ensure_ascii=False, indent=2)}")

def rotate_logs(max_days=30):
    """
    오래된 로그 파일 정리
    
    Args:
        max_days (int): 유지할 최대 로그 일수
    """
    import glob
    import time
    import os
    
    log_dir = 'logs'
    current_time = time.time()
    max_seconds = max_days * 24 * 60 * 60
    
    # 로그 디렉토리 내 모든 로그 파일 검색
    log_files = glob.glob(os.path.join(log_dir, '*.log*'))
    
    for file_path in log_files:
        # 백업 파일 형식 (app_YYYYMMDD.log.YYYY-MM-DD) 처리
        if os.path.isfile(file_path):
            file_time = os.path.getmtime(file_path)
            if current_time - file_time > max_seconds:
                try:
                    os.remove(file_path)
                    print(f"오래된 로그 파일 삭제: {file_path}")
                except Exception as e:
                    print(f"로그 파일 삭제 실패: {file_path} - {e}")

class JsonFormatter(logging.Formatter):
    """JSON 형식으로 로그 포맷팅"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)

def setup_json_logging(log_file='logs/app_json.log'):
    """JSON 형식의 로깅 설정"""
    
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    json_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5)
    json_handler.setFormatter(JsonFormatter())
    
    root_logger = logging.getLogger()
    root_logger.addHandler(json_handler)
    
    return root_logger 로거 캐시 (중복 생성 방지)
_loggers = {}

def setup_logging(log_level="INFO", log_to_file=True, log_to_console=True, log_format=None, rotation='daily'):
    """
    애플리케이션 로깅 설정
    
    Args:
        log_level (str): 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file (bool): 파일에 로그 기록 여부
        log_to_console (bool): 콘솔에 로그 출력 여부
        log_format (str): 로그 포맷 (None인 경우 기본값 사용)
        rotation (str): 로그 파일 회전 방식 ('daily', 'size', 'none')
        
    Returns:
        logging.Logger: 루트 로거
    """
    # 로그 디렉토리 생성
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    
    # 이미 핸들러가 설정되어 있으면 모두 제거
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    # 로그 레벨 설정
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    root_logger.setLevel(level_map.get(log_level.upper(), logging.INFO))
    
    # 로그 포맷 설정
    if log_format:
        file_formatter = logging.Formatter(log_format)
        console_formatter = logging.Formatter(log_format)
    else:
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    
    # 파일 핸들러 (모든 로그 저장)
    if log_to_file:
        if rotation == 'daily':
            # 일별 로그 파일 설정
            log_file = os.path.join('logs', f'app_%Y%m%d.log')
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file, when='midnight', interval=1, backupCount=30)
            file_handler.suffix = '%Y%m%d'
        elif rotation == 'size':
            # 크기 기반 로그 파일 설정
            log_file = os.path.join('logs', 'app.log')
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=10)
        else:
            # 회전 없는 로그 파일 설정
            log_file = os.path.join('logs', f'app_{datetime.now().strftime("%Y%m%d")}.log')
            file_handler = logging.FileHandler(log_file)
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # 콘솔 핸들러 설정
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # 에러 로그 전용 핸들러 (ERROR 이상 로그만 별도 파일에 기록)
    error_log_file = os.path.join('logs', 'error.log')
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file, maxBytes=5*1024*1024, backupCount=5)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # 초기 로그 메시지
    root_logger.info(f"로그 설정 완료 (레벨: {log_level})")
    
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
    
    #
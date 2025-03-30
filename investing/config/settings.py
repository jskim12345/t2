"""
애플리케이션 설정 값
"""
import os

# 애플리케이션 기본 설정
APP_NAME = "자산관리 프로그램"
APP_VERSION = "1.0.0"
DEBUG = True

# 데이터베이스 설정
DB_PATH = "data"
PORTFOLIO_DB = os.path.join(DB_PATH, "portfolio.db")
USERS_DB = os.path.join(DB_PATH, "users.db")

# 로깅 설정
LOG_PATH = "logs"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 보안 설정
SESSION_EXPIRY_HOURS = 24
MIN_PASSWORD_LENGTH = 6

# UI 설정
DEFAULT_PAGE_SIZE = 100
CHART_COLORS = {
    "primary": "rgb(0, 100, 200)",
    "secondary": "rgb(0, 150, 100)",
    "tertiary": "rgb(200, 100, 0)",
    "neutral": "rgb(100, 100, 100)"
}

# API 설정
EXCHANGE_RATE_API = "https://api.exchangerate-api.com/v4/latest/"
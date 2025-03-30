# 프로젝트 구조 및 파일 설명

```
project/
├── app.py                  # 메인 어플리케이션 파일
├── config/                 # 구성 파일
│   └── settings.py         # 설정값 정의
├── models/                 # 데이터베이스 모델
│   ├── database.py         # 데이터베이스 초기화 및 연결 모듈
│   ├── portfolio.py        # 포트폴리오 관련 모델
│   ├── savings.py          # 적금 관련 모델
│   └── user.py             # 사용자 및 인증 관련 모델
├── services/               # 비즈니스 로직 서비스
│   ├── auth_service.py     # 인증 관련 서비스
│   ├── market_service.py   # 시장 데이터 서비스 (주가, 환율 등)
│   ├── portfolio_service.py # 포트폴리오 관련 서비스
│   └── savings_service.py  # 적금 관련 서비스
├── ui/                     # UI 관련 코드
│   ├── auth_ui.py          # 인증 UI 컴포넌트
│   ├── portfolio_ui.py     # 포트폴리오 UI 컴포넌트
│   ├── savings_ui.py       # 적금 UI 컴포넌트
│   └── visualization.py    # 시각화 함수
├── utils/                  # 유틸리티 기능
│   ├── logging.py          # 로깅 설정
│   └── helpers.py          # 기타 헬퍼 함수
├── logs/                   # 로그 파일 디렉토리
├── data/                   # 데이터 파일 디렉토리
│   ├── portfolio.db        # 포트폴리오 데이터베이스
│   └── users.db            # 사용자 데이터베이스
├── README.md               # 프로젝트 설명서
└── requirements.txt        # 필요한 패키지 목록
```

## 파일별 역할

### 메인 파일
- **app.py**: 애플리케이션의 진입점. Gradio UI 생성 및 이벤트 핸들러 설정.

### 구성 파일
- **config/settings.py**: 애플리케이션 설정값 정의 (데이터베이스 경로, 로깅 설정 등).

### 데이터베이스 모델
- **models/database.py**: 데이터베이스 연결 및 초기화 담당.
- **models/user.py**: 사용자 계정 및 인증 관련 데이터 처리.
- **models/portfolio.py**: 포트폴리오 데이터 CRUD 기능 제공.
- **models/savings.py**: 적금 데이터 CRUD 기능 제공.

### 서비스 레이어
- **services/auth_service.py**: 사용자 인증 및 세션 관리 관련 비즈니스 로직.
- **services/market_service.py**: 주가 정보 및 환율 정보 조회, 업데이트 스케줄링.
- **services/portfolio_service.py**: 포트폴리오 관리 비즈니스 로직.
- **services/savings_service.py**: 적금 관리 비즈니스 로직.

### UI 컴포넌트
- **ui/auth_ui.py**: 로그인 및 회원가입 화면 UI 컴포넌트.
- **ui/portfolio_ui.py**: 포트폴리오 조회, 매수/매도, 거래내역 UI 컴포넌트.
- **ui/savings_ui.py**: 적금 조회, 추가, 거래내역 UI 컴포넌트.
- **ui/visualization.py**: 데이터 시각화 관련 UI 컴포넌트 및 차트 생성 함수.

### 유틸리티
- **utils/logging.py**: 로깅 설정 및 로거 생성 함수.
- **utils/helpers.py**: 날짜 처리, 숫자 포맷팅, 이자 계산 등의 유틸리티 함수.

## 주요 기능

### 인증 및 계정 관리
- 로그인/로그아웃 기능
- 회원가입 기능
- 세션 관리 (만료시간 설정)
- 로그인 시도 로깅

### 포트폴리오 관리
- 주식 종목 추가 (매수)
- 주식 종목 매도
- 실시간 가격 업데이트
- 수익률 및 평가액 계산
- 거래내역 조회

### 적금 관리
- 적금 계좌 추가
- 입금/출금 기록
- 예상 만기금액 계산
- 적금 거래내역 조회

### 데이터 시각화
- 포트폴리오 수익률 추이 차트
- 자산 배분 현황 차트 (주식 vs 적금)
- 국가별/계좌별/증권사별 분포 차트
- 상위 종목 차트
- 적금 현황 및 만기일 타임라인 차트

### 보안 기능
- 비밀번호 해싱 (bcrypt)
- 세션 관리 (만료 처리)
- 로그인 기록 관리

### 시스템 관리
- 로깅 시스템 (파일 및 콘솔 출력)
- 주기적인 데이터 업데이트 스케줄링
- 오류 처리 및 로깅
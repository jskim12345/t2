"""
인증 관련 UI 컴포넌트 - 고급 인증 기능 및 2단계 인증 지원
"""
import gradio as gr
import time
from datetime import datetime

def create_auth_ui():
    """
    인증 UI 컴포넌트 생성 (로그인, 회원가입, 비밀번호 재설정 등)
    
    Returns:
        tuple: (컨테이너 딕셔너리, 컴포넌트 딕셔너리)
    """
    # 컨테이너 딕셔너리 (각 화면)
    containers = {}
    
    # 컴포넌트 딕셔너리 (모든 UI 요소)
    components = {}
    
    # 로그인 화면 컴포넌트
    with gr.Row() as login_container:
        with gr.Column(scale=1):
            gr.Markdown("## 자산관리 프로그램 로그인", elem_classes="header-text")
            
            login_username = gr.Textbox(
                label="사용자명 또는 이메일",
                placeholder="사용자명 또는 이메일 주소 입력",
                elem_classes="input-field"
            )
            login_password = gr.Textbox(
                label="비밀번호",
                type="password",
                placeholder="비밀번호 입력",
                elem_classes="input-field"
            )
            
            with gr.Row():
                login_remember = gr.Checkbox(label="로그인 상태 유지", value=False)
            
            with gr.Row():
                login_btn = gr.Button("로그인", variant="primary", elem_classes="action-button")
                register_btn = gr.Button("회원가입", elem_classes="secondary-button")
            
            with gr.Row():
                reset_pwd_btn = gr.Button("비밀번호 찾기", elem_classes="text-button")
            
            login_message = gr.Textbox(label="", visible=False, interactive=False, elem_classes="message-box")
    
    containers["login"] = login_container
    
    # 회원가입 화면 컴포넌트
    with gr.Row(visible=False) as register_container:
        with gr.Column(scale=1):
            gr.Markdown("## 회원가입", elem_classes="header-text")
            
            reg_username = gr.Textbox(
                label="사용자명",
                placeholder="영문, 숫자, 밑줄(_) 4-20자",
                elem_classes="input-field"
            )
            reg_email = gr.Textbox(
                label="이메일",
                placeholder="example@example.com",
                elem_classes="input-field"
            )
            reg_password = gr.Textbox(
                label="비밀번호",
                type="password",
                placeholder="비밀번호 입력",
                elem_classes="input-field"
            )
            reg_confirm_password = gr.Textbox(
                label="비밀번호 확인",
                type="password",
                placeholder="비밀번호 재입력",
                elem_classes="input-field"
            )
            
            # 비밀번호 규칙 안내
            gr.Markdown("""
            **비밀번호 규칙:**
            - 최소 8자 이상
            - 대문자, 소문자, 숫자, 특수문자 포함
            """, elem_classes="info-text")
            
            with gr.Row():
                reg_submit_btn = gr.Button("가입하기", variant="primary", elem_classes="action-button")
                reg_back_btn = gr.Button("뒤로가기", elem_classes="secondary-button")
            
            reg_message = gr.Textbox(label="", visible=False, interactive=False, elem_classes="message-box")
    
    containers["register"] = register_container
    
    # 비밀번호 재설정 요청 화면
    with gr.Row(visible=False) as reset_request_container:
        with gr.Column(scale=1):
            gr.Markdown("## 비밀번호 재설정", elem_classes="header-text")
            gr.Markdown("가입 시 사용한 이메일을 입력하시면 비밀번호 재설정 링크를 보내드립니다.", elem_classes="info-text")
            
            reset_email = gr.Textbox(
                label="이메일",
                placeholder="example@example.com",
                elem_classes="input-field"
            )
            
            with gr.Row():
                reset_submit_btn = gr.Button("재설정 링크 받기", variant="primary", elem_classes="action-button")
                reset_back_btn = gr.Button("뒤로가기", elem_classes="secondary-button")
            
            reset_message = gr.Textbox(label="", visible=False, interactive=False, elem_classes="message-box")
    
    containers["reset_request"] = reset_request_container
    
    # 비밀번호 재설정 화면 (토큰 확인 후)
    with gr.Row(visible=False) as reset_password_container:
        with gr.Column(scale=1):
            gr.Markdown("## 새 비밀번호 설정", elem_classes="header-text")
            
            new_password = gr.Textbox(
                label="새 비밀번호",
                type="password",
                placeholder="새 비밀번호 입력",
                elem_classes="input-field"
            )
            confirm_new_password = gr.Textbox(
                label="새 비밀번호 확인",
                type="password",
                placeholder="새 비밀번호 재입력",
                elem_classes="input-field"
            )
            
            # 비밀번호 규칙 안내
            gr.Markdown("""
            **비밀번호 규칙:**
            - 최소 8자 이상
            - 대문자, 소문자, 숫자, 특수문자 포함
            - 최근 사용한 비밀번호는 재사용 불가
            """, elem_classes="info-text")
            
            # 토큰을 저장하기 위한 숨겨진 필드
            reset_token = gr.Textbox(visible=False)
            
            with gr.Row():
                reset_confirm_btn = gr.Button("비밀번호 변경", variant="primary", elem_classes="action-button")
                reset_cancel_btn = gr.Button("취소", elem_classes="secondary-button")
            
            reset_result_message = gr.Textbox(label="", visible=False, interactive=False, elem_classes="message-box")
    
    containers["reset_password"] = reset_password_container
    
    # 이메일 인증 화면
    with gr.Row(visible=False) as email_verification_container:
        with gr.Column(scale=1):
            gr.Markdown("## 이메일 인증", elem_classes="header-text")
            
            verification_info = gr.Markdown(
                "이메일 인증 진행 중입니다. 잠시만 기다려주세요...",
                elem_classes="info-text"
            )
            
            verification_result = gr.Textbox(label="", visible=False, interactive=False, elem_classes="message-box")
            
            with gr.Row():
                verify_login_btn = gr.Button("로그인 화면으로", visible=False, elem_classes="action-button")
                verify_resend_btn = gr.Button("인증 이메일 재발송", visible=False, elem_classes="secondary-button")
    
    containers["email_verification"] = email_verification_container
    
    # 2단계 인증 화면
    with gr.Row(visible=False) as two_factor_container:
        with gr.Column(scale=1):
            gr.Markdown("## 2단계 인증", elem_classes="header-text")
            gr.Markdown("계정 보안을 위한 2단계 인증이 필요합니다.", elem_classes="info-text")
            
            tfa_code = gr.Textbox(
                label="인증 코드",
                placeholder="6자리 인증 코드 입력",
                elem_classes="input-field"
            )
            
            # 사용자 ID와 인증 방식을 저장하기 위한 숨겨진 필드
            tfa_user_id = gr.Textbox(visible=False)
            tfa_method = gr.Textbox(visible=False, value="totp")
            
            with gr.Row():
                tfa_verify_btn = gr.Button("인증", variant="primary", elem_classes="action-button")
                tfa_cancel_btn = gr.Button("취소", elem_classes="secondary-button")
            
            with gr.Row():
                tfa_resend_btn = gr.Button("인증 코드 재발송", visible=False, elem_classes="text-button")
            
            tfa_message = gr.Textbox(label="", visible=False, interactive=False, elem_classes="message-box")
    
    containers["two_factor"] = two_factor_container
    
    # 2단계 인증 설정 화면
    with gr.Row(visible=False) as two_factor_setup_container:
        with gr.Column(scale=1):
            gr.Markdown("## 2단계 인증 설정", elem_classes="header-text")
            
            # 인증 방식 선택
            tfa_setup_method = gr.Radio(
                ["TOTP (인증 앱)", "이메일"],
                label="인증 방식 선택",
                value="TOTP (인증 앱)"
            )
            
            # TOTP 설정 영역
            with gr.Group(visible=True) as totp_setup_group:
                totp_qr_image = gr.Image(label="QR 코드", elem_classes="qr-code")
                totp_secret = gr.Textbox(label="비밀 키 (직접 입력용)", elem_classes="secret-key")
                
                gr.Markdown("""
                **설정 방법:**
                1. Google Authenticator, Authy 등의 인증 앱 설치
                2. QR 코드 스캔 또는 비밀 키 직접 입력
                3. 앱에 표시된 6자리 코드 입력하여 확인
                """, elem_classes="info-text")
            
            # 이메일 설정 영역
            with gr.Group(visible=False) as email_setup_group:
                email_info = gr.Markdown("이메일 인증을 선택하셨습니다. 로그인 시 등록된 이메일로 인증 코드가 발송됩니다.", elem_classes="info-text")
            
            # 인증 확인
            tfa_setup_code = gr.Textbox(
                label="인증 코드",
                placeholder="인증 앱의 6자리 코드 입력",
                elem_classes="input-field"
            )
            
            # 설정 데이터를 저장하기 위한 숨겨진 필드
            tfa_setup_data = gr.Textbox(visible=False)
            
            with gr.Row():
                tfa_setup_verify_btn = gr.Button("인증 및 설정 완료", variant="primary", elem_classes="action-button")
                tfa_setup_cancel_btn = gr.Button("취소", elem_classes="secondary-button")
            
            tfa_setup_message = gr.Textbox(label="", visible=False, interactive=False, elem_classes="message-box")
    
    containers["two_factor_setup"] = two_factor_setup_container
    
    # 모든 컴포넌트 정리
    components.update({
        # 로그인 화면
        "login_username": login_username,
        "login_password": login_password,
        "login_remember": login_remember,
        "login_btn": login_btn,
        "register_btn": register_btn,
        "reset_pwd_btn": reset_pwd_btn,
        "login_message": login_message,
        
        # 회원가입 화면
        "reg_username": reg_username,
        "reg_email": reg_email,
        "reg_password": reg_password,
        "reg_confirm_password": reg_confirm_password,
        "reg_submit_btn": reg_submit_btn,
        "reg_back_btn": reg_back_btn,
        "reg_message": reg_message,
        
        # 비밀번호 재설정 요청 화면
        "reset_email": reset_email,
        "reset_submit_btn": reset_submit_btn,
        "reset_back_btn": reset_back_btn,
        "reset_message": reset_message,
        
        # 비밀번호 재설정 화면
        "new_password": new_password,
        "confirm_new_password": confirm_new_password,
        "reset_token": reset_token,
        "reset_confirm_btn": reset_confirm_btn,
        "reset_cancel_btn": reset_cancel_btn,
        "reset_result_message": reset_result_message,
        
        # 이메일 인증 화면
        "verification_info": verification_info,
        "verification_result": verification_result,
        "verify_login_btn": verify_login_btn,
        "verify_resend_btn": verify_resend_btn,
        
        # 2단계 인증 화면
        "tfa_code": tfa_code,
        "tfa_user_id": tfa_user_id,
        "tfa_method": tfa_method,
        "tfa_verify_btn": tfa_verify_btn,
        "tfa_cancel_btn": tfa_cancel_btn,
        "tfa_resend_btn": tfa_resend_btn,
        "tfa_message": tfa_message,
        
        # 2단계 인증 설정 화면
        "tfa_setup_method": tfa_setup_method,
        "totp_setup_group": totp_setup_group,
        "email_setup_group": email_setup_group,
        "totp_qr_image": totp_qr_image,
        "totp_secret": totp_secret,
        "tfa_setup_code": tfa_setup_code,
        "tfa_setup_data": tfa_setup_data,
        "tfa_setup_verify_btn": tfa_setup_verify_btn,
        "tfa_setup_cancel_btn": tfa_setup_cancel_btn,
        "tfa_setup_message": tfa_setup_message,
    })
    
    return containers, components

def setup_auth_ui_events(app, session_state, containers, components):
    """
    인증 UI 이벤트 설정
    
    Args:
        app: Gradio 앱 인스턴스
        session_state: 세션 상태 컴포넌트
        containers: UI 컨테이너 딕셔너리
        components: UI 컴포넌트 딕셔너리
    """
    try:
        from services.auth_service import (
            register_user, authenticate_user, logout_session, change_user_password,
            request_password_reset, reset_password_with_token, verify_email,
            resend_verification_email, setup_user_2fa, confirm_2fa_setup,
            verify_2fa, send_2fa_code
        )
    except ImportError as e:
        print(f"Error importing auth_service: {e}")
        return
    
    # 화면 전환 함수
    def show_container(container_name):
        """특정 컨테이너만 표시하고 나머지는 숨김"""
        return [gr.update(visible=(name == container_name)) for name in containers.keys()]
    
    # 로그인 처리
    def login(username, password, remember_me):
        if not username or not password:
            return session_state.value, gr.update(value="사용자명과 비밀번호를 모두 입력해주세요.", visible=True)
        
        # 로그인 시도
        success, session_id, message, need_2fa = authenticate_user(
            username, password, "unknown", "unknown", remember_me, False
        )
        
        if success and session_id:
            # 로그인 성공, 세션 생성
            from services.auth_service import validate_session
            valid, user_data, _ = validate_session(session_id)
            
            if valid:
                new_state = {
                    "logged_in": True,
                    "session_id": session_id,
                    "user_id": user_data["user_id"],
                    "username": user_data["username"]
                }
                
                # 세션 상태 및 성공 메시지 반환
                return new_state, gr.update(value="로그인 성공! 메인 화면으로 이동합니다...", visible=True)
        
        elif success and need_2fa:
            # 2단계 인증 필요
            user = get_user_by_username(username)
            
            # 2단계 인증 화면으로 전환하는 내용 반환
            return (
                session_state.value,
                gr.update(value="2단계 인증이 필요합니다.", visible=True),
                *show_container("two_factor"),
                gr.update(value=str(user["id"])),
                gr.update(value="totp"),
                ""
            )
        
        # 로그인 실패
        return session_state.value, gr.update(value=message, visible=True)
    
    components["login_btn"].click(
        fn=login,
        inputs=[
            components["login_username"],
            components["login_password"],
            components["login_remember"]
        ],
        outputs=[
            session_state,
            components["login_message"]
        ]
    )
    
    # 회원가입 화면 전환
    def show_register():
        return show_container("register")
    
    components["register_btn"].click(
        fn=show_register,
        inputs=[],
        outputs=[*containers.values()]
    )
    
    # 회원가입 처리
    def register(username, email, password, confirm_password):
        # 입력값 검증
        if not username or not password:
            return (
                *show_container("register"),
                gr.update(value="사용자명과 비밀번호는 필수 입력값입니다.", visible=True)
            )
        
        if password != confirm_password:
            return (
                *show_container("register"),
                gr.update(value="비밀번호가 일치하지 않습니다.", visible=True)
            )
        
        # 회원가입 시도
        success, message, user_id = register_user(username, password, email)
        
        if success:
            # 회원가입 성공, 로그인 화면으로 전환
            return (
                *show_container("login"),
                gr.update(value="회원가입 성공! 이메일 인증 후 로그인해주세요.", visible=True)
            )
        
        # 회원가입 실패
        return (
            *show_container("register"),
            gr.update(value=message, visible=True)
        )
    
    components["reg_submit_btn"].click(
        fn=register,
        inputs=[
            components["reg_username"],
            components["reg_email"],
            components["reg_password"],
            components["reg_confirm_password"]
        ],
        outputs=[
            *containers.values(),
            components["reg_message"]
        ]
    )
    
    # 회원가입 화면에서 뒤로가기
    def back_to_login():
        return (
            *show_container("login"),
            gr.update(value="", visible=False)
        )
    
    components["reg_back_btn"].click(
        fn=back_to_login,
        inputs=[],
        outputs=[
            *containers.values(),
            components["login_message"]
        ]
    )
    
    # 비밀번호 재설정 요청 화면 전환
    def show_reset_request():
        return show_container("reset_request")
    
    components["reset_pwd_btn"].click(
        fn=show_reset_request,
        inputs=[],
        outputs=[*containers.values()]
    )
    
    # 비밀번호 재설정 요청 처리
    def request_reset(email):
        if not email:
            return (
                *show_container("reset_request"),
                gr.update(value="이메일을 입력해주세요.", visible=True)
            )
        
        # 재설정 요청 처리
        success, message = request_password_reset(email)
        
        return (
            *show_container("reset_request"),
            gr.update(value=message, visible=True)
        )
    
    components["reset_submit_btn"].click(
        fn=request_reset,
        inputs=[components["reset_email"]],
        outputs=[
            *containers.values(),
            components["reset_message"]
        ]
    )
    
    # 비밀번호 재설정 요청 화면에서 뒤로가기
    components["reset_back_btn"].click(
        fn=back_to_login,
        inputs=[],
        outputs=[
            *containers.values(),
            components["login_message"]
        ]
    )
    
    # 비밀번호 재설정 처리 (토큰 확인 후)
    def reset_password(token, new_password, confirm_password):
        if not new_password or not confirm_password:
            return (
                gr.update(value=token),
                gr.update(value="새 비밀번호를 입력해주세요.", visible=True)
            )
        
        if new_password != confirm_password:
            return (
                gr.update(value=token),
                gr.update(value="비밀번호가 일치하지 않습니다.", visible=True)
            )
        
        # 비밀번호 재설정 처리
        success, message = reset_password_with_token(token, new_password)
        
        if success:
            # 재설정 성공, 로그인 화면으로 전환
            return (
                gr.update(value=""),
                gr.update(value=message, visible=True),
                *show_container("login"),
                gr.update(value=message, visible=True)
            )
        
        # 재설정 실패
        return (
            gr.update(value=token),
            gr.update(value=message, visible=True),
            *show_container("reset_password"),
            gr.update(value="", visible=False)
        )
    
    components["reset_confirm_btn"].click(
        fn=reset_password,
        inputs=[
            components["reset_token"],
            components["new_password"],
            components["confirm_new_password"]
        ],
        outputs=[
            components["reset_token"],
            components["reset_result_message"],
            *containers.values(),
            components["login_message"]
        ]
    )
    
    # 비밀번호 재설정 취소
    components["reset_cancel_btn"].click(
        fn=back_to_login,
        inputs=[],
        outputs=[
            *containers.values(),
            components["login_message"]
        ]
    )
    
    # 이메일 인증 처리
    def process_email_verification(token):
        # 토큰 검증 및 인증 처리
        success, message = verify_email(token)
        
        return (
            gr.update(visible=False),
            gr.update(value=message, visible=True),
            gr.update(visible=True),
            gr.update(visible=not success)
        )
    
    # 이메일 인증 토큰이 있는 경우의 처리 함수 (앱 시작 시 호출)
    def check_verification_token(url_params):
        token = url_params.get("token", None)
        
        if token and "verify_email" in url_params.get("path", ""):
            # 이메일 인증 화면으로 전환 및 토큰 처리
            return (
                *show_container("email_verification"),
                gr.update(visible=False),
                gr.update(value="", visible=False),
                gr.update(visible=False),
                gr.update(visible=False)
            )
        elif token and "reset_password" in url_params.get("path", ""):
            # 비밀번호 재설정 화면으로 전환
            return (
                *show_container("reset_password"),
                gr.update(value=token)
            )
        
        # 토큰이 없는 경우 기본 로그인 화면
        return (
            *show_container("login"),
            gr.update(value="")
        )
    
    # 인증 이메일 재발송
    def resend_verification():
        # 이메일 주소 입력 받기 (팝업 대화상자 대신 간단한 입력 폼으로 대체)
        email = input("이메일 주소를 입력하세요: ")
        
        if not email:
            return gr.update(value="이메일 주소를 입력해주세요.", visible=True)
        
        # 인증 이메일 재발송 요청
        success, message = resend_verification_email(email)
        
        return gr.update(value=message, visible=True)
    
    components["verify_resend_btn"].click(
        fn=resend_verification,
        inputs=[],
        outputs=[components["verification_result"]]
    )
    
    # 인증 완료 후 로그인 화면으로 이동
    components["verify_login_btn"].click(
        fn=back_to_login,
        inputs=[],
        outputs=[
            *containers.values(),
            components["login_message"]
        ]
    )
    
    # 2단계 인증 처리
    def verify_two_factor(user_id, method, code):
        if not code:
            return gr.update(value="인증 코드를 입력해주세요.", visible=True)
        
        try:
            user_id = int(user_id)
        except ValueError:
            return gr.update(value="유효하지 않은 사용자 정보입니다.", visible=True)
        
        # 2단계 인증 검증
        success, message = verify_2fa(user_id, code)
        
        if success:
            # 인증 성공, 로그인 처리
            from models.user import get_user_by_id
            user = get_user_by_id(user_id)
            
            if not user:
                return gr.update(value="사용자 정보를 찾을 수 없습니다.", visible=True)
            
            # 세션 생성
            from services.auth_service import create_session, validate_session
            session_id = create_session(user_id)
            
            if not session_id:
                return gr.update(value="세션 생성에 실패했습니다.", visible=True)
            
            valid, user_data, _ = validate_session(session_id)
            
            if valid:
                new_state = {
                    "logged_in": True,
                    "session_id": session_id,
                    "user_id": user_data["user_id"],
                    "username": user_data["username"]
                }
                
                # 세션 상태 업데이트 및 성공 메시지 반환
                return gr.update(value="인증 성공! 메인 화면으로 이동합니다...", visible=True)
        
        # 인증 실패
        return gr.update(value=message, visible=True)
    
    components["tfa_verify_btn"].click(
        fn=verify_two_factor,
        inputs=[
            components["tfa_user_id"],
            components["tfa_method"],
            components["tfa_code"]
        ],
        outputs=[components["tfa_message"]]
    )
    
    # 2단계 인증 취소
    components["tfa_cancel_btn"].click(
        fn=back_to_login,
        inputs=[],
        outputs=[
            *containers.values(),
            components["login_message"]
        ]
    )
    
    # 인증 코드 재발송
    def resend_2fa_code(user_id, method):
        try:
            user_id = int(user_id)
        except ValueError:
            return gr.update(value="유효하지 않은 사용자 정보입니다.", visible=True)
        
        # 인증 코드 발송 요청
        success, message = send_2fa_code(user_id, method)
        
        return gr.update(value=message, visible=True)
    
    components["tfa_resend_btn"].click(
        fn=resend_2fa_code,
        inputs=[
            components["tfa_user_id"],
            components["tfa_method"]
        ],
        outputs=[components["tfa_message"]]
    )
    
    # 2단계 인증 설정 화면의 인증 방식 변경 이벤트
    def update_2fa_setup_ui(method):
        if method == "TOTP (인증 앱)":
            return gr.update(visible=True), gr.update(visible=False)
        else:  # 이메일
            return gr.update(visible=False), gr.update(visible=True)
    
    components["tfa_setup_method"].change(
        fn=update_2fa_setup_ui,
        inputs=[components["tfa_setup_method"]],
        outputs=[
            components["totp_setup_group"],
            components["email_setup_group"]
        ]
    )
    
    # 2단계 인증 설정 시작
    def start_2fa_setup(user_id, method):
        try:
            user_id = int(user_id)
        except ValueError:
            return (
                gr.update(),  # QR 이미지
                gr.update(),  # 비밀 키
                gr.update(value="", visible=False),  # 설정 데이터
                gr.update(value="유효하지 않은 사용자 정보입니다.", visible=True)  # 메시지
            )
        
        # 인증 방식 변환
        if method == "TOTP (인증 앱)":
            setup_method = "totp"
        else:
            setup_method = "email"
        
        # 2단계 인증 설정 요청
        success, data = setup_user_2fa(user_id, setup_method)
        
        if not success:
            return (
                gr.update(),
                gr.update(),
                gr.update(value="", visible=False),
                gr.update(value=data, visible=True)
            )
        
        if setup_method == "totp":
            # TOTP 설정 데이터 처리
            import qrcode
            from io import BytesIO
            
            # QR 코드 이미지 생성
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data['qr_uri'])
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 이미지를 바이트로 변환
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()
            
            return (
                gr.update(value=img_bytes),
                gr.update(value=data['secret']),
                gr.update(value=json.dumps(data), visible=False),
                gr.update(value="QR 코드를 스캔하거나 비밀 키를 입력한 후, 인증 앱에 표시된 코드를 입력하세요.", visible=True)
            )
        else:
            # 이메일 인증 설정 데이터 처리
            return (
                gr.update(),
                gr.update(),
                gr.update(value=json.dumps(data), visible=False),
                gr.update(value="이메일 인증을 선택하셨습니다. 인증 코드를 받으려면 '인증 및 설정 완료' 버튼을 클릭하세요.", visible=True)
            )
    
    # 2단계 인증 설정 확인
    def confirm_2fa_setup_ui(user_id, setup_data, code):
        if not code:
            return gr.update(value="인증 코드를 입력해주세요.", visible=True)
        
        try:
            user_id = int(user_id)
        except ValueError:
            return gr.update(value="유효하지 않은 사용자 정보입니다.", visible=True)
        
        # 설정 데이터 파싱
        try:
            setup_data = json.loads(setup_data)
        except (json.JSONDecodeError, TypeError):
            return gr.update(value="설정 데이터가 유효하지 않습니다.", visible=True)
        
        # 2단계 인증 설정 확인
        success, message = confirm_2fa_setup(user_id, code)
        
        if success:
            # 설정 성공, 프로필 화면으로 전환 (앱에서 구현)
            return gr.update(value="2단계 인증 설정이 완료되었습니다.", visible=True)
        
        # 설정 실패
        return gr.update(value=message, visible=True)
    
    # 2단계 인증 설정 취소
    components["tfa_setup_cancel_btn"].click(
        fn=lambda: gr.update(value="2단계 인증 설정이 취소되었습니다.", visible=True),
        inputs=[],
        outputs=[components["tfa_setup_message"]]
    )
    
    # 앱 시작 시 URL 파라미터 확인 (이메일 인증, 비밀번호 재설정 등)
    app.load(
        fn=check_verification_token,
        inputs=[],
        outputs=[
            *containers.values(),
            components["reset_token"]
        ]
    )
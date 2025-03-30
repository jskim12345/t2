"""
인증 관련 UI 컴포넌트
"""
import gradio as gr

def create_auth_ui():
    """
    인증 UI 컴포넌트 생성 (로그인 및 회원가입)
    
    Returns:
        tuple: (로그인 컨테이너, 회원가입 컨테이너, 컴포넌트 딕셔너리)
    """
    # 로그인 화면 컴포넌트
    with gr.Row() as login_container:
        with gr.Column(scale=1):
            gr.Markdown("## 자산관리 프로그램 로그인")
            
            login_username = gr.Textbox(label="사용자명")
            login_password = gr.Textbox(label="비밀번호", type="password")
            
            with gr.Row():
                login_btn = gr.Button("로그인", variant="primary")
                register_btn = gr.Button("회원가입")
            
            login_message = gr.Textbox(label="상태 메시지", interactive=False)
    
    # 회원가입 화면 컴포넌트
    with gr.Row(visible=False) as register_container:
        with gr.Column(scale=1):
            gr.Markdown("## 회원가입")
            
            reg_username = gr.Textbox(label="사용자명")
            reg_password = gr.Textbox(label="비밀번호", type="password")
            reg_confirm_password = gr.Textbox(label="비밀번호 확인", type="password")
            reg_email = gr.Textbox(label="이메일")
            
            with gr.Row():
                reg_submit_btn = gr.Button("가입하기", variant="primary")
                reg_back_btn = gr.Button("뒤로가기")
            
            reg_message = gr.Textbox(label="상태 메시지", interactive=False)
    
    # 컴포넌트들을 딕셔너리로 정리
    components = {
        "username": login_username,
        "password": login_password,
        "login_btn": login_btn,
        "register_btn": register_btn,
        "message": login_message,
        "reg_username": reg_username,
        "reg_password": reg_password,
        "reg_confirm_password": reg_confirm_password,
        "reg_email": reg_email,
        "reg_submit_btn": reg_submit_btn,
        "reg_back_btn": reg_back_btn,
        "reg_message": reg_message
    }
    
    return login_container, register_container, components
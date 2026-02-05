"""
이메일 자동화 UI 모듈
Streamlit에서 사용되는 이메일 탭과 관련 기능
"""

import streamlit as st
from email_mcp_server import EmailMCPServer


def email_automation_page():
    """이메일 자동화 시스템"""
    
    st.markdown(
        """
        <div class="main-header">
            <h1 class="header-title">📧 이메일 자동화 시스템</h1>
            <p class="header-subtitle">AI 기반 메일 작성 & 발송 자동화</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 이메일 서버 초기화
    if "email_server" not in st.session_state:
        st.session_state.email_server = EmailMCPServer()
    
    if "selected_email" not in st.session_state:
        st.session_state.selected_email = None
    
    if "draft_response" not in st.session_state:
        st.session_state.draft_response = ""
    
    # 이메일 탭 선택 상태
    if "email_tab" not in st.session_state:
        st.session_state.email_tab = 0
    
    # AI 생성 상태 추적
    if "ai_generated" not in st.session_state:
        st.session_state.ai_generated = False
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📬 메일 수신", "📝 답변 작성 & 검토", "✅ 발송 기록"])
    
    # ========================
    # 탭 1: 메일 수신
    # ========================
    with tab1:
        st.subheader("오늘 온 메일 목록")
        
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button("🔄 새로고침", use_container_width=True, key="refresh_emails"):
                with st.spinner("메일을 로드 중입니다..."):
                    result = st.session_state.email_server.fetch_todays_emails()
                    if result["success"]:
                        st.session_state.todays_emails = result["emails"]
                        st.success(f"✅ {result['count']}개의 메일을 로드했습니다!")
                    else:
                        st.error(f"❌ 메일 로드 실패: {result.get('error', '알 수 없는 오류')}")
        
        with col2:
            email_count = len(st.session_state.get("todays_emails", []))
            st.metric("메일 수", email_count)
        
        # 메일 목록 표시
        emails = st.session_state.get("todays_emails", [])
        
        if emails:
            for idx, email in enumerate(emails):
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.write(f"**From:** {email['from_name']} <{email['from_address']}>")
                        st.write(f"**Subject:** {email['subject']}")
                        
                        # 첨부 파일 표시
                        if email.get('attachments'):
                            attachment_count = len(email['attachments'])
                            st.caption(f"📎 첨부 파일 {attachment_count}개")
                        
                        st.caption(f"📅 {email['received_date']}")
                        with st.expander("📄 본문 미리보기"):
                            # 개행 문자를 유지하면서 깔끔하게 표시
                            preview_text = email['body'][:500]
                            if len(email['body']) > 500:
                                preview_text += "\n\n[... 더 있음]"
                            st.text(preview_text)
                    
                    with col2:
                        if st.button("✏️ 답변하기", key=f"reply_{idx}", use_container_width=True):
                            st.session_state.selected_email = {
                                "email_id": email["email_id"],
                                "from_name": email["from_name"],
                                "from_address": email["from_address"],
                                "subject": email["subject"],
                                "body": email["body"],
                                "attachments": email.get("attachments", [])
                            }
                            st.session_state.email_tab = 1  # 탭 2로 이동
                            st.rerun()
        else:
            st.info("📭 오늘 온 메일이 없습니다.")
    
    # ========================
    # 탭 2: 답변 작성 & 검토
    # ========================
    with tab2:
        st.subheader("메일 답변 작성 및 검토")
        
        if st.session_state.selected_email:
            email = st.session_state.selected_email
            
            # 원본 메일 표시
            st.markdown("### 📧 원본 메일")
            with st.container(border=True):
                st.write(f"**From:** {email['from_name']} <{email['from_address']}>")
                st.write(f"**Subject:** {email['subject']}")
                st.divider()
                st.markdown("**본문:**")
                # 마크다운으로 렌더링하되, 개행은 유지
                body_text = email['body'].replace('\n', '  \n')  # Markdown에서 개행 유지
                st.markdown(body_text)
            
            # 첨부 파일 표시
            if email.get('attachments'):
                st.markdown("### 📎 첨부 파일")
                with st.container(border=True):
                    for idx, attachment in enumerate(email['attachments']):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            filename = attachment.get('filename', '알 수 없는 파일')
                            st.write(f"📄 {filename}")
                        with col2:
                            size_kb = attachment.get('size', 0) / 1024
                            st.caption(f"{size_kb:.1f} KB")
                        with col3:
                            if st.download_button(
                                label="⬇️",
                                data=attachment.get('data', b''),
                                file_name=filename,
                                key=f"download_attachment_{idx}"
                            ):
                                pass  # 다운로드 처리는 Streamlit에서 자동
            
            # 답변 생성 버튼
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🤖 AI 답변 생성", use_container_width=True):
                    with st.spinner("AI가 답변을 작성 중입니다..."):
                        result = st.session_state.email_server.generate_response_for_email(
                            email_id=email["email_id"],
                            from_address=email["from_address"],
                            subject=email["subject"],
                            body=email["body"]
                        )
                        
                        if result["success"]:
                            st.session_state.draft_response = result["response"]
                            st.session_state.draft_subject = result["subject"]
                            st.session_state.ai_generated = True
                            st.success("✅ 답변이 생성되었습니다!")
                            st.rerun()
                        else:
                            st.error(f"❌ 답변 생성 실패: {result.get('error')}")
            
            with col2:
                if st.button("💾 임시 저장", use_container_width=True):
                    if st.session_state.draft_response:
                        result = st.session_state.email_server.save_draft(
                            to_address=email["from_address"],
                            subject=st.session_state.get("draft_subject", f"Re: {email['subject']}"),
                            body=st.session_state.draft_response,
                            original_email_id=email["email_id"]
                        )
                        if result["success"]:
                            st.success("✅ 메일이 임시 저장되었습니다!")
                        else:
                            st.error(f"❌ 저장 실패: {result.get('message')}")
                    else:
                        st.warning("⚠️ 저장할 내용이 없습니다.")
            
            with col3:
                if st.button("🔄 처음으로", use_container_width=True):
                    st.session_state.selected_email = None
                    st.session_state.draft_response = ""
                    st.session_state.ai_generated = False
                    st.rerun()
            
            # AI 생성된 답변 미리보기
            if st.session_state.draft_response:
                st.markdown("### 📋 AI 생성 답변 초안")
                with st.container(border=True):
                    # 제목 표시 (f-string 중첩 문제 해결)
                    draft_subject = st.session_state.get('draft_subject', f"Re: {email['subject']}")
                    st.markdown(f"**제목:** {draft_subject}")
                    st.divider()
                    st.markdown("**본문:**")
                    # 개행 유지
                    body_preview = st.session_state.draft_response.replace('\n', '  \n')
                    st.markdown(body_preview)
                    st.divider()
                    st.caption("💡 아래 '답변 수정' 섹션에서 내용을 수정할 수 있습니다.")
            
            # 답변 내용 편집
            if st.session_state.draft_response:
                st.markdown("### ✏️ 답변 수정")
                
                subject = st.text_input(
                    "제목:",
                    value=st.session_state.get("draft_subject", f"Re: {email['subject']}"),
                    key="response_subject"
                )
                st.session_state.draft_subject = subject
                
                response_body = st.text_area(
                    "답변 내용:",
                    value=st.session_state.draft_response,
                    height=250,
                    key="response_body"
                )
                st.session_state.draft_response = response_body
                
                # 발송 버튼들
                st.markdown("### 🚀 발송")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📧 이 메일 발송하기", use_container_width=True):
                        if st.session_state.draft_response:
                            with st.spinner("메일을 발송 중입니다..."):
                                result = st.session_state.email_server.send_email(
                                    to_address=email["from_address"],
                                    subject=st.session_state.draft_subject,
                                    body=st.session_state.draft_response,
                                    original_email_id=email["email_id"]
                                )
                                
                                if result["success"]:
                                    st.success(f"✅ {result['message']}")
                                    # 상태 초기화
                                    st.session_state.selected_email = None
                                    st.session_state.draft_response = ""
                                    st.session_state.ai_generated = False
                                    st.balloons()
                                    st.rerun()
                                else:
                                    st.error(f"❌ 발송 실패: {result['message']}")
                        else:
                            st.warning("⚠️ 답변 내용을 입력해주세요.")
                
                with col2:
                    if st.button("⏭️ 다음 메일", use_container_width=True):
                        st.session_state.draft_response = ""
                        st.session_state.selected_email = None
                        st.session_state.ai_generated = False
                        st.rerun()
                
                with col3:
                    if st.button("🔍 메일 분류", use_container_width=True):
                        with st.spinner("메일을 분석 중입니다..."):
                            result = st.session_state.email_server.classify_email(
                                subject=email["subject"],
                                body=email["body"]
                            )
                            
                            if result["success"]:
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("분류", result["category"])
                                with col2:
                                    st.metric("응답 필요", "예" if result["requires_response"] else "아니요")
                                with col3:
                                    st.metric("우선순위", result["priority"])
                            else:
                                st.error("분류 실패")
            else:
                st.info("🤖 위의 '🤖 AI 답변 생성' 버튼을 클릭하여 답변을 생성해주세요.")
        else:
            st.info("📭 메일을 선택해주세요. (📬 메일 수신 탭에서 '답변하기' 버튼을 클릭하세요)")
    
    # ========================
    # 탭 3: 발송 기록
    # ========================
    with tab3:
        st.subheader("발송 기록 및 임시 저장")
        
        sub_tab1, sub_tab2 = st.tabs(["📤 발송 완료", "📋 임시 저장"])
        
        with sub_tab1:
            if st.button("🔄 새로고침", use_container_width=True, key="refresh_history"):
                with st.spinner("발송 기록을 로드 중입니다..."):
                    result = st.session_state.email_server.get_email_history()
                    if result["success"]:
                        st.session_state.send_logs = result["logs"]
                        st.success(f"✅ {result['count']}개의 발송 기록을 로드했습니다!")
                    else:
                        st.error("❌ 기록 로드 실패")
            
            logs = st.session_state.get("send_logs", [])
            
            if logs:
                # 통계
                col1, col2, col3 = st.columns(3)
                success_count = sum(1 for log in logs if log["status"] == "success")
                with col1:
                    st.metric("총 발송", len(logs))
                with col2:
                    st.metric("성공", success_count)
                with col3:
                    st.metric("실패", len(logs) - success_count)
                
                # 발송 기록 표 형식
                st.markdown("### 발송 기록")
                for log in logs:
                    status_emoji = "✅" if log["status"] == "success" else "❌"
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"{status_emoji} **To:** {log['to_address']}")
                            st.write(f"**Subject:** {log['subject']}")
                            st.caption(f"⏰ {log['timestamp']}")
                        with col2:
                            st.markdown(f"<p style='text-align: center; color: {'green' if log['status'] == 'success' else 'red'};'><b>{log['status'].upper()}</b></p>", unsafe_allow_html=True)
            else:
                st.info("📭 발송 기록이 없습니다.")
        
        with sub_tab2:
            if st.button("🔄 새로고침", use_container_width=True, key="refresh_drafts"):
                with st.spinner("임시 저장 메일을 로드 중입니다..."):
                    result = st.session_state.email_server.get_drafts()
                    if result["success"]:
                        st.session_state.drafts = result["drafts"]
                        st.success(f"✅ {result['count']}개의 임시 저장 메일을 로드했습니다!")
                    else:
                        st.error("❌ 로드 실패")
            
            drafts = st.session_state.get("drafts", [])
            
            if drafts:
                st.markdown("### 임시 저장 메일")
                for draft in drafts:
                    with st.container(border=True):
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.write(f"**To:** {draft['to_address']}")
                            st.write(f"**Subject:** {draft['subject']}")
                            with st.expander("📄 미리보기"):
                                st.text(draft['body'][:300])
                        
                        with col2:
                            if st.button("✏️ 편집", key=f"edit_draft_{draft['id']}", use_container_width=True):
                                st.session_state.selected_email = {
                                    "email_id": draft.get("original_email_id", ""),
                                    "from_address": draft["to_address"],
                                    "subject": draft["subject"],
                                    "body": ""
                                }
                                st.session_state.draft_response = draft["body"]
                                st.session_state.draft_subject = draft["subject"]
                                st.session_state.email_tab = 1  # 탭 2로 이동
                                st.rerun()
                        
                        with col3:
                            if st.button("🗑️ 삭제", key=f"delete_draft_{draft['id']}", use_container_width=True):
                                if st.session_state.email_server.db.delete_draft(draft['id']):
                                    st.success("✅ 삭제되었습니다!")
                                    st.rerun()
                                else:
                                    st.error("❌ 삭제 실패")
            else:
                st.info("💾 임시 저장된 메일이 없습니다.")

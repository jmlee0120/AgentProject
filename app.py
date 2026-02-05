import streamlit as st
import os
import shutil
import hashlib
import asyncio
import json
from datetime import datetime
from email_mcp_server import EmailMCPServer
from email_ui import email_automation_page
from rag_module import (
    create_rag_chain,
    query_expansion,
    add_confidence_score,
    retrieve_docs_for_queries,
    format_docs_with_pages,
)

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(
    page_title="World Vision AI Assistant",
    page_icon="🌎",
    layout="wide",
)

# ---------------------------
# Full Optimized CSS
# ---------------------------
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background */
    .stApp {
        background-color: #f8f9fa;
    }
    
    .block-container {
        padding-top: 1rem !important;
        max-width: 1200px;
    }

    /* Main Header */
    .main-header {
    position: relative;              /* 추가 */
    overflow: hidden;                /* 추가 */
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    padding: 1.5rem 2rem;
    border-radius: 16px;
    border-bottom: 4px solid #ff6b00;
    margin-bottom: 2rem;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
}

    /* 오버레이 추가: 텍스트 대비 안정화 */
.main-header::before {
    content: "";
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.30); /* 0.25~0.4 사이에서 조절 */
    z-index: 0;
}

/* header 내부 텍스트가 오버레이 위로 오게 */
.main-header * {
    position: relative;
    z-index: 1;
}

    .page-nav-buttons {
        display: flex;
        gap: 10px;
        margin-bottom: 2rem;
        justify-content: center;
    }
    
    .page-nav-buttons button {
        padding: 0.7rem 1.5rem !important;
        border-radius: 12px !important;
        border: 2px solid #ff6b00 !important;
        background-color: white !important;
        color: #ff6b00 !important;
        font-weight: 700 !important;
        transition: all 0.3s !important;
        cursor: pointer;
    }
    
    .page-nav-buttons button:hover {
        background-color: #ff6b00 !important;
        color: white !important;
        transform: translateY(-2px) !important;
    }
    
    .page-nav-buttons button.active {
        background-color: #ff6b00 !important;
        color: white !important;
    }

    .header-title {
        color: #ffffff !important;
        opacity: 1 !important;
        font-size: 1.9rem;
        font-weight: 800;
        margin: 0;
        text-align: center;
        text-shadow: 0 2px 10px rgba(0,0,0,0.35); /* 가독성 보조 */
    }

    .header-subtitle {
        color: #d1d5db !important;       /* 흰색보다 살짝 톤다운 */
        opacity: 1 !important;
        font-size: 0.95rem;
        margin-top: 6px;
        text-align: center;
        text-shadow: 0 1px 8px rgba(0,0,0,0.25);
    }

    /* Status Card */
    .status-card {
        background: white;
        padding: 2.2rem;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }

    /* Badge */
    .badge {
        padding: 6px 14px;
        border-radius: 30px;
        font-size: 0.8rem;
        font-weight: 700;
        background-color: #fff7ed;
        color: #ea580c;
        border: 1.5px solid #fdba74;
    }

    /* System Buttons */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #ff6b00 0%, #ff8c3a 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 700 !important;
        transition: all 0.2s;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255, 107, 0, 0.3);
    }

    @keyframes rotate {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
    
    .rotating-earth {
        font-size: 5rem;
        display: inline-block;
        animation: rotate 3s linear infinite;
    }
    
    .main-center {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .main-title {
        color: #0f172a;     /* 또는 #111827 */
        font-size: 2.5rem;
        font-weight: 900;
        text-align: center;
        margin: 0;
    }
    
    .setup-section {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 2.5rem;
        max-width: 700px;
        width: 100%;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin: 0 auto;
    }
    
    .setup-title {
        color: #0f172a;
        font-size: 1.3rem;
        font-weight: 700;
        margin: 0 0 1.5rem 0;
        text-align: center;
    }
    
    .setup-guide {
        border-left: 3px solid #ff6b00;
        padding: 12px 0 12px 15px;
        margin-bottom: 1.5rem;
        background: #fff7ed;
        border-radius: 8px;
        padding: 15px 15px 15px 15px;
    }
    
    .setup-guide p {
        font-size: 0.95rem;
        color: #92400e;
        margin: 0;
        line-height: 1.6;
    }

    .input-form {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 1.5rem;
    }

    .form-section {
        margin-bottom: 1.5rem;
    }

    .form-label {
        color: #0f172a;
        font-weight: 700;
        font-size: 1rem;
        margin-bottom: 0.5rem;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------
# Session State 초기화
# ---------------------------
def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()


if "current_page" not in st.session_state:
    st.session_state.current_page = "문서 챗봇"

if "emphasize" not in st.session_state:
    st.session_state.emphasize = True
if "show_confidence" not in st.session_state:
    st.session_state.show_confidence = True
if "enable_query_expansion" not in st.session_state:
    st.session_state.enable_query_expansion = False

# ---------------------------
# Header with Page Navigation
# ---------------------------
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown(
        """
        <div class="main-header">
            <h1 class="header-title">🌎 월드비전 AI ASSISTANT</h1>
            <p class="header-subtitle">World Vision AI Assistant Platform</p>
        </div>
        """,
        unsafe_allow_html=True
    )

# 페이지 선택 버튼
pages = ["문서 챗봇", "보고서 작성기", "📧 이메일 자동화"]
page_cols = st.columns(3)

for idx, page in enumerate(pages):
    with page_cols[idx]:
        if st.button(
            f"{'📄 ' if page == '문서 챗봇' else '📝 ' if page == '보고서 작성기' else '📧 '}{page}",
            use_container_width=True,
            key=f"page_btn_{page}"
        ):
            st.session_state.current_page = page
            st.rerun()

st.markdown("---")

# ---------------------------
# PAGE 1: 문서 챗봇
# ---------------------------
if st.session_state.current_page == "문서 챗봇":
    
    # 제목 표시
    st.markdown(
        """
        <div class="main-center" style="margin: 1rem 0;">
            <h1 class="main-title">문서 챗봇</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # File upload at top center
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown(
            """
            <div class="setup-section" style="padding: 2rem;">
                <h3 class="setup-title">📄 PDF 문서 업로드</h3>
                <div class="setup-guide">
                    <p><b>📚 문서를 업로드하면</b><br>AI가 내용을 학습하여 복잡한 질문에도 정확하게 답변합니다.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        uploaded_file = st.file_uploader("", type=["pdf"], label_visibility="collapsed", key="main_uploader")
    
    if uploaded_file:
        temp_path = f"temp_{uploaded_file.name}"
        
        # 파일 내용의 해시값 계산
        file_hash = hashlib.md5(uploaded_file.getvalue()).hexdigest()
        
        # 이전 파일과 현재 파일이 다른지 확인
        file_changed = False
        if "current_file_hash" not in st.session_state:
            st.session_state.current_file_hash = None
            st.session_state.current_file_name = None
        
        # 파일이 변경되었는지 확인 (해시값으로 정확히 감지)
        if st.session_state.current_file_hash != file_hash:
            file_changed = True
            st.session_state.current_file_hash = file_hash
            st.session_state.current_file_name = uploaded_file.name
            
            # 이전 rag_chain과 messages 삭제
            if "rag_chain" in st.session_state:
                del st.session_state.rag_chain
            st.session_state.messages = []
            
            # 이전 임시 파일 정리
            import glob
            for old_file in glob.glob("temp_*"):
                try:
                    os.remove(old_file)
                except:
                    pass
        
        # 임시 파일 저장
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 파일 업로드 상단에 시스템 설정 배치
        st.markdown("## 📚 업로드된 문서")
        st.success(f"✅ 연결됨: {uploaded_file.name}")
        
        # 파일 업로드 경고
        st.warning("⚠️ **새 문서 업로드 시 주의사항**\n\n새로운 문서를 업로드하면:\n• 이전 대화 기록이 삭제됩니다\n• 이전 문서 기반 답변은 불가능합니다")
        
        st.markdown("---")
        st.markdown("## ⚙️ 시스템 설정")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.emphasize = st.checkbox("출처 근거 강조 표시", value=st.session_state.emphasize)
        with col2:
            st.session_state.show_confidence = st.checkbox("신뢰도 표시", value=st.session_state.show_confidence)
        
        with st.expander("🚀 고급 옵션 (성능 개선)", expanded=False):
            st.session_state.enable_query_expansion = st.checkbox(
                "쿼리 확장 활성화",
                value=st.session_state.enable_query_expansion,
                help="같은 의도의 다양한 표현으로 검색하여 정확도 향상 (응답 시간 증가)"
            )
        
        if st.button("🔄 대화 기록 초기화", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")

        # RAG Chain 생성 (새 파일이거나 rag_chain이 없을 때)
        if "rag_chain" not in st.session_state:
            with st.status("🚀 AI가 지식 베이스를 생성하고 있습니다...", expanded=True) as status:
                rag_chain, retriever = create_rag_chain(temp_path)
                st.session_state.rag_chain = rag_chain
                st.session_state.retriever = retriever
                status.update(label="준비 완료! 질문을 입력하세요.", state="complete", expanded=False)
            
            # 새 파일 로드 시 알림
            if file_changed and st.session_state.current_file_name:
                st.info(f"✅ '{uploaded_file.name}' 파일을 기반으로 업데이트되었습니다. 이전 대화 기록은 초기화됩니다.")

        if "messages" not in st.session_state:
            st.session_state.messages = []

        st.subheader("💬 무엇이든 물어보세요")
        
        # Message Display
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat Input
        if prompt := st.chat_input("업로드한 문서에 대해 질문하세요..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("답변 생성 중..."):
                    # 쿼리 확장 옵션
                    if st.session_state.enable_query_expansion:
                        with st.spinner("다양한 관점에서 검색 중..."):
                            expanded_queries = query_expansion(prompt)
                            docs = run_async(
                                retrieve_docs_for_queries(
                                    st.session_state.retriever,
                                    expanded_queries,
                                )
                            )
                            combined_context = format_docs_with_pages(docs)
                            response = st.session_state.rag_chain.invoke(
                                {"question": prompt, "context": combined_context}
                            )
                    else:
                        response = st.session_state.rag_chain.invoke(prompt)
                    
                    # 신뢰도 표시 추가
                    if st.session_state.show_confidence:
                        # 간단한 신뢰도 평가: 컨텍스트 길이 기반
                        context_length = len(response)
                        context_quality = min(1.0, context_length / 1500)  # 1500자 이상이면 높은 신뢰도
                        response_with_confidence = add_confidence_score(response, context_quality)
                        full_response = f"**[문서 기반 답변]**\n\n{response_with_confidence}" if st.session_state.emphasize else response_with_confidence
                    else:
                        full_response = f"**[문서 기반 답변]**\n\n{response}" if st.session_state.emphasize else str(response)
                    
                    st.markdown(full_response)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        # 정리: 임시 파일 삭제 (옵션)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

    else:
        # Landing Page
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 환영 문구
        st.markdown(
            """
            <div class="status-card">
                <h2 style="margin-top:0;">환영합니다! 👋</h2>
                <p style="font-size: 1.1rem; color: #334155;"><b>월드비전 사내 AI Assistant</b>는 임직원 여러분의 업무 효율을 위해 개발되었습니다.</p>
                <p style="color: #64748b; line-height: 1.6;">
                PDF 문서를 업로드하면 AI가 해당 문서의 내용을 즉시 파악하여<br>
                복잡한 질문에도 정확하게 답변해 드립니다.
                </p>
                <div style="margin-top: 30px; padding: 15px; background: #f1f5f9; border-radius: 12px; border-left: 5px solid #cbd5e1;">
                    <span style="color: #475569; font-size: 0.9rem;">📌 <b>개인정보 유의</b>: 본 시스템은 사내 보안망 내에서만 활용하시길 권장합니다.</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ---------------------------
# PAGE 2: 보고서 작성기
# ---------------------------
elif st.session_state.current_page == "보고서 작성기":
    
    st.markdown(
        """
        <div class="main-center">
            <div style="font-size: 4rem;">📝</div>
            <h1 class="main-title">보고서 작성기</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown(
            """
            <div class="input-form">
                <div class="form-section">
                    <p class="form-label">📋 보고서 제목</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        report_title = st.text_input("", placeholder="예: 2025년 Q1 프로젝트 성과 보고서", label_visibility="collapsed")
        
        st.markdown(
            """
            <div class="input-form">
                <div class="form-section">
                    <p class="form-label">📊 보고서 유형</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        report_type = st.selectbox("", 
            ["프로젝트 보고서", "성과 보고서", "분석 보고서", "재정 보고서", "월간 보고서", "기타"],
            label_visibility="collapsed"
        )
        
        st.markdown(
            """
            <div class="input-form">
                <div class="form-section">
                    <p class="form-label">📝 주요 내용 요약</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        content_summary = st.text_area("", 
            placeholder="보고서에 포함할 주요 사항들을 입력하세요...",
            height=150,
            label_visibility="collapsed"
        )
        
        st.markdown(
            """
            <div class="input-form">
                <div class="form-section">
                    <p class="form-label">🎯 핵심 성과 및 지표</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        kpi = st.text_area("", 
            placeholder="주요 지표, 수치, 목표 달성도 등을 입력하세요...",
            height=120,
            label_visibility="collapsed"
        )
        
        if st.button("🤖 AI로 보고서 작성", use_container_width=True):
            if report_title and content_summary:
                st.info("💡 보고서 생성 중입니다. 잠시만 기다려주세요...")
                
                # 프로토타입: 자동 생성된 보고서 샘플
                ai_generated_report = f"""
## {report_title}

### 1. 개요
{report_type}로 제시되는 본 보고서는 주요 성과와 향후 개선 방향을 담고 있습니다.

### 2. 주요 내용
{content_summary}

### 3. 핵심 성과 지표
{kpi}

### 4. 결론 및 향후 계획
- 지속적인 개선을 통한 성과 극대화
- 팀 역량 강화 및 협업 확대
- 다음 기간 목표 설정 및 실행 계획 수립

---
*본 보고서는 AI Assistant에 의해 자동 생성되었습니다. 내용 검토 후 필요시 수정하시기 바랍니다.*
"""
                
                st.success("✅ 보고서가 생성되었습니다!")
                st.markdown(ai_generated_report)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.download_button(
                        label="📥 마크다운 다운로드",
                        data=ai_generated_report,
                        file_name=f"{report_title}.md",
                        mime="text/markdown"
                    )
                with col2:
                    st.button("✏️ 편집 모드")
                with col3:
                    st.button("🔄 다시 생성")
            else:
                st.warning("⚠️ 보고서 제목과 주요 내용을 입력해주세요.")
    
    with col2:
        st.markdown(
            """
            <div class="status-card">
                <h3 style="margin-top:0;">💡 팁</h3>
                <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 10px;">자세한 정보를 입력할수록 더 정확한 보고서가 생성됩니다.</p>
                <p style="font-size: 0.85rem; color: #94a3b8; margin: 0;">
                    <b>지원 형식:</b><br>
                    • 프로젝트 보고서<br>
                    • 성과 보고서<br>
                    • 분석 보고서<br>
                    • 재정 보고서<br>
                    • 월간 보고서
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

# ---------------------------
# PAGE 3: 이메일 Assistant
# ---------------------------
elif st.session_state.current_page == "📧 이메일 자동화":
    email_automation_page()

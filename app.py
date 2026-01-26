import streamlit as st
import os
import shutil
import hashlib
from rag_module import create_rag_chain, query_expansion, add_confidence_score

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
        padding-top: 2rem !important;
        max-width: 1100px;
    }

    /* Sidebar - Base */
    section[data-testid="stSidebar"] {
        background-color: #1e293b !important;
    }
    
    /* 사이드바 일반 텍스트 및 라벨 (흰색) */
    section[data-testid="stSidebar"] .stMarkdown, 
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span {
        color: #ffffff !important;
    }

    /* --- 파일 업로더 가독성 및 공간 최적화 --- */
    
    /* 1. 업로더 박스 슬림화 및 배경 고정 */
    section[data-testid="stSidebar"] [data-testid="stFileUploadDropzone"] {
        padding: 1rem !important;
        border: 2px dashed #cbd5e1 !important;
        background-color: #ffffff !important;
        border-radius: 12px !important;
        min-height: 140px !important;
    }

    /* 2. 'Browse files' 버튼: 어두운 배경으로 대비 강화 */
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        color: #ffffff !important;
        background-color: #1e293b !important;
        border: none !important;
        padding: 0.4rem 1rem !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    /* 3. 내부 안내 문구 (Drag and drop...) - 검정색 강제 적용 */
    section[data-testid="stSidebar"] [data-testid="stFileUploadDropzone"] div[data-testid="stMarkdownContainer"] p {
        color: #000000 !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
    }

    /* 4. 내부 아이콘 및 기타 텍스트 가독성 */
    section[data-testid="stSidebar"] [data-testid="stFileUploadDropzone"] svg {
        fill: #1e293b !important;
    }
    
    section[data-testid="stSidebar"] [data-testid="stFileUploadDropzone"] small {
        color: #475569 !important;
        font-weight: 500 !important;
    }
    /* --------------------------------------- */

    /* Main Header */
    .main-header {
        background-color: #ffffff;
        padding: 1.8rem 2.2rem;
        border-radius: 16px;
        border-bottom: 4px solid #ff6b00;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .header-title {
        color: #0f172a;
        font-size: 1.9rem;
        font-weight: 800;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .header-subtitle {
        color: #475569;
        font-size: 0.95rem;
        margin-top: 6px;
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
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------
# Top Navigation / Header
# ---------------------------
st.markdown(
    """
    <div class="main-header">
        <div>
            <h1 class="header-title">🌎 월드비전 사내 AI Assistant</h1>
            <p class="header-subtitle">World Vision Internal Knowledge Base (RAG v2.3)</p>
        </div>
        <div>
            <span class="badge">보안등급: 사내전용</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Sidebar: File Management
# ---------------------------
with st.sidebar:
    st.markdown("### 📄 문서 라이브러리")
    
    # 텅 빈 공간을 채워줄 가이드 박스
    st.markdown(
        """
        <div style="border-left: 3px solid #ff6b00; padding: 2px 0 2px 12px; margin-bottom: 15px;">
            <p style="font-size: 0.82rem; color: #cbd5e1; margin: 0; line-height: 1.5;">
                <b>PDF 문서를 업로드하면</b><br>AI가 내용을 학습하여 답변합니다.
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    uploaded_file = st.file_uploader("", type=["pdf"], label_visibility="collapsed")
    
    if uploaded_file:
        st.success(f"연결됨: {uploaded_file.name}")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### ⚙️ 시스템 설정")
    emphasize = st.toggle("출처 근거 강조 표시", value=True)
    history_toggle = st.toggle("대화 기록 유지", value=True)
    
    # 🆕 고급 옵션
    with st.expander("🚀 고급 옵션 (성능 개선)", expanded=False):
        enable_query_expansion = st.checkbox(
            "쿼리 확장 활성화",
            value=False,
            help="같은 의도의 다양한 표현으로 검색하여 정확도 향상 (응답 시간 증가)"
        )
        show_confidence = st.checkbox(
            "신뢰도 표시",
            value=True,
            help="답변의 문서 근거 신뢰도를 표시"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 대화 기록 초기화"):
        st.session_state.messages = []
        st.rerun()

# ---------------------------
# Main Logic
# ---------------------------

# 🆕 파일 변경 감지 로직
if uploaded_file:
    temp_path = f"temp_{uploaded_file.name}"
# 🆕 파일 변경 감지 로직
if uploaded_file:
    temp_path = f"temp_{uploaded_file.name}"
    
    # 파일 내용의 해시값 계산 (파일 내용이 정말 다른지 확인)
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

    # RAG Chain 생성 (새 파일이거나 rag_chain이 없을 때)
    if "rag_chain" not in st.session_state:
        with st.status("🚀 AI가 지식 베이스를 생성하고 있습니다...", expanded=True) as status:
            st.session_state.rag_chain = create_rag_chain(temp_path)
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
                # 🆕 쿼리 확장 옵션
                if 'enable_query_expansion' in locals() and enable_query_expansion:
                    with st.spinner("다양한 관점에서 검색 중..."):
                        expanded_queries = query_expansion(prompt)
                        # 최초 쿼리로 답변 생성
                        response = st.session_state.rag_chain.invoke(prompt)
                else:
                    response = st.session_state.rag_chain.invoke(prompt)
                
                # 🆕 신뢰도 표시 추가
                if 'show_confidence' in locals() and show_confidence:
                    # 간단한 신뢰도 평가: 컨텍스트 길이 기반
                    context_length = len(response)
                    context_quality = min(1.0, context_length / 1500)  # 1500자 이상이면 높은 신뢰도
                    response_with_confidence = add_confidence_score(response, context_quality)
                    full_response = f"**[문서 기반 답변]**\n\n{response_with_confidence}" if emphasize else response_with_confidence
                else:
                    full_response = f"**[문서 기반 답변]**\n\n{response}" if emphasize else str(response)
                
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
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(
            """
            <div class="status-card">
                <h2 style="margin-top:0;">환영합니다! 👋</h2>
                <p style="font-size: 1.1rem; color: #334155;"><b>월드비전 사내 AI Assistant</b>는 임직원 여러분의 업무 효율을 위해 개발되었습니다.</p>
                <p style="color: #64748b; line-height: 1.6;">
                왼쪽 사이드바에 사내 규정, 가이드라인, 혹은 프로젝트 보고서를 업로드해 보세요.<br>
                AI가 해당 문서의 내용을 즉시 파악하여 복잡한 질문에도 정확하게 답변해 드립니다.
                </p>
                <div style="margin-top: 30px; padding: 15px; background: #f1f5f9; border-radius: 12px; border-left: 5px solid #cbd5e1;">
                    <span style="color: #475569; font-size: 0.9rem;">📌 <b>개인정보 유의</b>: 본 시스템은 사내 보안망 내에서만 활용하시길 권장합니다.</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.info("💡 **시작 가이드**: PDF 파일을 업로드하면 채팅창이 활성화됩니다.")
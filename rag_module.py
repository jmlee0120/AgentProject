import os
from dotenv import load_dotenv

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableBranch
from langchain_core.output_parsers import StrOutputParser

# .env 파일에 저장된 API 키 로드
load_dotenv()

# =========================
# 파라미터 조정 (파일 내부 수정 방식)
# =========================
CHUNK_SIZE = 800 # 한 조각에 담기는 문맥의 길이 (너무 크면 LLM 입력 제한 걸림)
CHUNK_OVERLAP = 120  # 청크를 자를 때 겹치는 부분 (문맥 단절 최소화 목적)

RETRIEVER_K = 6  # 최종적으로 LLM에 넣을 청크 개수 / 너무 작으면 근거 부족
RETRIEVER_FETCH_K = 40 # 후보로 더 많이 뽑아놓고 그중에서 다양하게 고르는 폭
RETRIEVER_LAMBDA = 0.5  # 유사도 vs 다양성 균형 조정 (0~1, 1에 가까울수록 유사도 편중)

MODEL_NAME = "gpt-4o"
TEMPERATURE = 0
# =========================


def create_rag_chain(pdf_path: str):
    # [1단계] 문서 로드 (Document Load) - PyMuPDFLoader는 보통 페이지 단위 Document를 반환
    loader = PyMuPDFLoader(pdf_path)
    docs = loader.load()

    # [2단계] 문서 분할 (Text Split) - QA/요약(RAG)용
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    split_documents = text_splitter.split_documents(docs)

    # [3~4단계] 임베딩 및 벡터 DB 저장
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents=split_documents, embedding=embeddings)

    # [5단계] 검색기(Retriever) 생성
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": RETRIEVER_K,
            "fetch_k": RETRIEVER_FETCH_K,
            "lambda_mult": RETRIEVER_LAMBDA,
        },
    )

    # [6~7단계] LLM
    llm = ChatOpenAI(model_name=MODEL_NAME, temperature=TEMPERATURE)

    # -------------------------
    # 컨텍스트 포맷팅(페이지 표기 포함)
    # -------------------------
    def format_docs(docs_list):
        blocks = []
        for d in docs_list:
            page = d.metadata.get("page", None)
            # 사람이 보기 좋게 1부터 표기
            page_str = f"{page + 1}" if isinstance(page, int) else "?"
            text = (d.page_content or "").strip()
            if not text:
                continue
            blocks.append(f"[p.{page_str}]\n{text}")
        return "\n\n---\n\n".join(blocks)

    format_docs_runnable = RunnableLambda(format_docs)
    context_chain = retriever | format_docs_runnable

    
    # 1) QA 프롬프트 (문서 근거 기반)
    qa_template = """
너는 '월드비전 사내 문서' 기반 Q&A 어시스턴트야.
아래 <Context>에 포함된 내용만 근거로 답해. 외부지식/추측/인터넷 정보는 절대 사용하지 마.

[규칙]
1) <Context>에 근거가 없으면 답을 만들지 말고 "문서에서 확인되지 않음"이라고 말해.
2) 사용자의 질문 의도를 문서 관점에서 재구성해서(한 줄) 먼저 제시해.
3) 답변은 사용자가 바로 행동/결정할 수 있게 정리해. 단, 문서에 있는 범위에서만.
4) 근거에는 p.번호를 포함해.
5) 질문이 모호해도, 문서에 관련될 수 있는 항목들을 묶어서 제시하고,
   정말로 핵심 정보가 부족할 때만 확인 질문을 1~2개만 해.

[출력 형식]
## 질문 의도(재구성)
- (질문의 목적을 한 줄로 재정의)

## 답변(핵심 결론)
- (짧게)

## 세부 설명(문서 기반 정리)
- (필요하면 항목화/단계화/조건-예외 형태로 정리)

## 근거(문서기반)
- (p.번호 포함, 1~4개)

## 추가로 확인하면 좋은 점(문서 범위 내)
- (문서에 존재하는 체크포인트/필요 서류/기한/예외 등을 2~5개)

## 문서에서 확인되지 않음
- (없으면 '없음')

<Context>
{context}

질문: {question}

한국어로 답변해.
"""

    qa_prompt = ChatPromptTemplate.from_template(qa_template)

    qa_chain = (
        {"context": context_chain, "question": RunnablePassthrough()}
        | qa_prompt
        | llm
        | StrOutputParser()
    )

    
    # 2) 요약/정리 프롬프트 (RAG 기반 "보고서" 요약)
    #    ※ 문서 전체를 완벽히 페이지 순서로 훑는 게 아니라,
    #      retriever가 뽑아준 컨텍스트 기반으로 정리하는 모드
    summary_template = """
너는 월드비전 사내 문서를 '요약·정리·보고'하는 AI 어시스턴트야.
아래 <Context>에 포함된 내용만 근거로 사용해. 외부지식/추측/인터넷 정보는 절대 사용하지 마.

[규칙]
1) <Context>에 근거가 없는 내용은 절대 만들어내지 마.
2) 문서에 없는 내용은 "문서에서 확인되지 않음"에 넣어.
3) 보고서처럼 깔끔하고 구조적으로 작성해.
4) 가능하면 p.번호를 언급해.

[출력 형식]
## 문서 핵심요약
- (3~6개)

## 상세정리
- (요청한 관점/항목 기준으로 체계적으로 정리)

## 근거(문서기반)
- (근거 요약 + p.번호, 2~6개)

## 문서에서 확인되지 않음
- (없으면 '없음')

<Context>
{context}

사용자 요청: {question}

한국어로 답변해.
"""
    summary_prompt = ChatPromptTemplate.from_template(summary_template)

    summary_chain = (
        {"context": context_chain, "question": RunnablePassthrough()}
        | summary_prompt
        | llm
        | StrOutputParser()
    )

    
    # 3) 페이지별 요약 모드 (read-all, 누락 최소화)
    #    ※ "페이지별로 핵심 요약" 요청일 때는 retriever를 쓰지 않고
    #      전체 페이지를 순서대로 읽어서 요약함.
    page_prompt = ChatPromptTemplate.from_template("""
너는 업로드된 문서의 '해당 페이지'만 요약하는 어시스턴트야.
외부지식/추측/인터넷 정보는 절대 사용하지 마. 이 페이지에 없는 내용은 쓰지 마.

[출력 형식]
- 핵심 요지 3개
- 중요한 규정/절차/수치/예외/주의사항(있으면 bullet)

페이지 내용:
{page_text}

한국어로 작성:
""")

    def summarize_pages_to_text(_question: str) -> str:
        """docs(페이지 단위)를 순회하며 p.별 요약을 만들고 문자열로 합침"""
        items = []
        for d in docs:
            page = d.metadata.get("page", None)
            page_no = page + 1 if isinstance(page, int) else None

            text = (d.page_content or "").strip()
            if not text:
                continue

            summary = llm.invoke(page_prompt.format(page_text=text)).content
            if page_no is None:
                items.append((10**9, summary))
            else:
                items.append((page_no, summary))

        items.sort(key=lambda x: x[0])

        out_lines = []
        for p, s in items:
            if p == 10**9:
                out_lines.append("## p.?\n" + s.strip())
            else:
                out_lines.append(f"## p.{p}\n{s.strip()}")
        return "\n\n".join(out_lines)

    pagewise_chain = RunnableLambda(summarize_pages_to_text)

    # -------------------------
    # 모드 감지/라우팅
    # -------------------------
    SUMMARY_HINTS = ("요약", "정리", "보고", "리포트", "개요", "핵심", "전반", "전체", "구조", "목차")
    PAGEWISE_HINTS = ("페이지별", "page by page", "페이지 단위", "쪽별", "p별")

    def route(question: str) -> str:
        q = (question or "").strip().lower()
        if any(k in q for k in PAGEWISE_HINTS):
            return "pagewise"
        if any(k in q for k in SUMMARY_HINTS):
            return "summary"
        return "qa"

    def is_pagewise(q: str) -> bool:
        return route(q) == "pagewise"

    def is_summary(q: str) -> bool:
        return route(q) == "summary"

    rag_chain = RunnableBranch(
        (is_pagewise, pagewise_chain),
        (is_summary, summary_chain),
        qa_chain,  # default
    )

    return rag_chain

import os
import asyncio
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
CHUNK_SIZE = 1000  # 한 조각에 담기는 문맥의 길이 (충분한 맥락을 담기 위해 확대)
CHUNK_OVERLAP = 200  # 청크를 자를 때 겹치는 부분 (문맥 단절 최소화 + 연결성 강화)

RETRIEVER_K = 10  # 최종적으로 LLM에 넣을 청크 개수 (더 풍부한 근거)
RETRIEVER_FETCH_K = 60  # 후보로 더 많이 뽑아놓고 그중에서 다양하게 고르는 폭
RETRIEVER_LAMBDA = 0.6  # 유사도 vs 다양성 균형 조정 (더 높은 유사도 비중)

MODEL_NAME = "gpt-4o"
TEMPERATURE = 0.1  # 약간의 창의성으로 자연스러운 한국어 표현
# =========================


def format_docs_with_pages(docs_list):
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


async def retrieve_docs_for_queries(retriever, queries: list[str]) -> list:
    async def _retrieve(query: str):
        if hasattr(retriever, "ainvoke"):
            return await retriever.ainvoke(query)
        if hasattr(retriever, "aget_relevant_documents"):
            return await retriever.aget_relevant_documents(query)
        return await asyncio.to_thread(retriever.get_relevant_documents, query)

    tasks = [_retrieve(q) for q in queries]
    results = await asyncio.gather(*tasks)

    seen = set()
    merged = []
    for docs in results:
        for d in docs:
            key = (d.metadata.get("source"), d.metadata.get("page"), d.page_content)
            if key in seen:
                continue
            seen.add(key)
            merged.append(d)
    return merged


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
    # 컨텍스트 포맷팅(페이지 표기 포함) & Rerank 적용
    # -------------------------
    def extract_question(inp):
        if isinstance(inp, dict):
            return inp.get("question", "")
        return inp

    def has_context(inp):
        return isinstance(inp, dict) and inp.get("context") is not None

    def extract_context(inp):
        return inp.get("context", "")

    # Rerank를 적용하는 함수
    def rerank_and_format(inp):
        """검색된 문서를 rerank한 후 포맷팅"""
        if isinstance(inp, dict):
            query = inp.get("question", "")
            docs = inp.get("docs", [])
        else:
            # inp가 문서 리스트인 경우
            query = ""
            docs = inp if isinstance(inp, list) else []
        
        if docs and query:
            # rerank 적용
            reranked_docs = rerank_results(query, docs, llm)
            return format_docs_with_pages(reranked_docs)
        return format_docs_with_pages(docs)

    question_selector = RunnableLambda(extract_question)
    format_docs_runnable = RunnableLambda(format_docs_with_pages)
    
    # 검색 후 rerank를 거치는 체인
    def retrieve_with_rerank(inp):
        """질문을 받아 retriever로 검색하고 rerank 적용"""
        query = extract_question(inp)
        if hasattr(retriever, "invoke"):
            docs = retriever.invoke(query)
        else:
            docs = retriever.get_relevant_documents(query)
        
        # rerank 적용
        reranked_docs = rerank_results(query, docs, llm)
        return format_docs_with_pages(reranked_docs)
    
    retriever_with_rerank = RunnableLambda(retrieve_with_rerank)
    context_chain = question_selector | retriever_with_rerank
    context_selector = RunnableBranch(
        (has_context, RunnableLambda(extract_context)),
        context_chain,
    )

    
    # 1) QA 프롬프트 (문서 근거 기반)
    qa_template = """당신은 '월드비전 사내 문서' 기반 Q&A 어시스턴트입니다.
아래 <Context>에 포함된 내용만 근거로 답하세요. 외부지식/추측/인터넷 정보는 절대 사용하지 마세요.

[핵심 규칙]
1. <Context>에 근거가 없으면 답을 만들지 말고 "문서에서 확인되지 않는 사항"이라고 명확히 말할 것
2. 사용자의 질문 의도를 정확히 이해한 후 한 줄로 재구성 제시
3. 답변은 사용자가 바로 이해하고 행동/결정할 수 있도록 구조화할 것
4. 모든 근거에는 p.(페이지번호)를 포함할 것
5. 핵심 정보 우선으로, 필요한 경우만 세부사항 추가
6. 질문이 모호한 경우 문서에서 찾을 수 있는 관련 항목들을 제시

[출력 형식 (엄격히 준수)]
## 질문 재구성
(질문의 실제 목적과 의도를 한 문장으로 정의)

## 핵심 답변
(직결된 답변, 가장 중요한 정보 먼저)

## 상세 설명
(필요한 배경정보, 조건, 예외사항 등 - bullet list 형식)

## 근거 (출처 명시)
- p.번호: (해당 내용 요약)
(2~4개의 핵심 근거)

## 확인하면 좋은 추가 정보
(문서에 존재하는 관련 체크포인트/서류/기한 등, 있으면 2~3개)

---
*※ 이 섹션이 비어있을 경우 문서에서 확인되지 않는 사항입니다.*

<Context>
{context}

질문: {question}

한국어로 친절하고 명확하게 답변하세요.
"""

    qa_prompt = ChatPromptTemplate.from_template(qa_template)

    qa_chain = (
        {"context": context_selector, "question": question_selector}
        | qa_prompt
        | llm
        | StrOutputParser()
    )

    
    # 2) 요약/정리 프롬프트 (RAG 기반 "보고서" 요약)
    summary_template = """당신은 월드비전 사내 문서를 구조적으로 '요약·정리·보고'하는 AI 어시스턴트입니다.
아래 <Context>에 포함된 내용만 근거로 사용하세요. 외부지식/추측/인터넷 정보는 절대 사용하지 마세요.
는 사항"에 명시할 것
3. 보고서처럼 깔끔하고 구조적으로 작성
4. 가능하면 p.번호를 함께 표기
5. 사용자의 요청 관점에 맞춰 핵심 정보 우선 정렬

[출력 형식 (엄격히 준수)]
## 📋 핵심 요약 (3~5개)
- (가장 중요한 내용부터 단계별로)

## 📊 상세 정리
(사용자 요청 관점으로 체계적 정리)

## 🔍 문서 기반 근거
- p.번호: (내용요약)
(2~5개의 주요 근거)

---
*※ 문서에서 확인되지 않는 사항: *
(없으면 '없음')

<Context>
{context}

사용자 요청: {question}

한국어로 친절하고 명확하게 작성하세요.
"""
    summary_prompt = ChatPromptTemplate.from_template(summary_template)

    summary_chain = (
        {"context": context_selector, "question": question_selector}
        | summary_prompt
        | llm
        | StrOutputParser()
    )

    
    # 3) 페이지별 요약 모드 (read-all, 누락 최소화)
    page_prompt = ChatPromptTemplate.from_template("""당신은 업로드된 문서의 '해당 페이지'만 정확히 요약하는 어시스턴트입니다.
이 페이지에 없는 내용은 절대 쓰지 마세요. 외부지식/추측/인터넷 정보도 사용하지 마세요.

[출력 형식]
## 핵심 요지 (3가지)
1. (가장 중요한 내용)
2. (부가 정보)
3. (주의/예외사항)

## 중요 규정·절차·수치·주의사항
- 항목 1
- 항목 2
(있으면 2~4개)

페이지 내용:
{page_text}

한국어로 명확하게 작성하세요.
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

    def route(question_or_input) -> str:
        q = extract_question(question_or_input)
        q = (q or "").strip().lower()
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

    return rag_chain, retriever

# =========================
# 추가 유틸리티 함수
# =========================

def query_expansion(query: str) -> list[str]:
    """
    사용자의 원본 질문을 여러 관점에서 재구성하여
    검색 정확도를 높입니다. (Hybrid Search 기초)
    """
    llm = ChatOpenAI(model_name=MODEL_NAME, temperature=0.7)
    
    expansion_prompt = ChatPromptTemplate.from_template("""
당신은 사용자의 질문을 다양한 관점에서 재구성하는 전문가입니다.

원본 질문: {query}

아래 5가지 관점에서 각각 다시 쓰세요. 한 줄씩만.
1. 직설적 표현 (원문과 거의 같되, 더 명확하게)
2. 관련 개념 포함 (동의어, 유사 개념을 섞어서)
3. 배경/맥락 강화 (why/how를 포함해서)
4. 실무 관점 (실제 업무 상황에서 어떻게 쓰일지)
5. 역질문 (핵심 의도를 역으로 표현)

형식: 마크다운 번호 리스트로, 각 항목은 한 줄씩만 제공하세요.
""")
    
    chain = expansion_prompt | llm | StrOutputParser()
    result = chain.invoke({"query": query})
    
    # 응답을 리스트로 파싱
    lines = [line.strip() for line in result.split('\n') if line.strip() and line[0].isdigit()]
    queries = [line.split('. ', 1)[-1] if '. ' in line else line for line in lines]
    
    return [query] + queries[:4]  # 원본 + 4가지


def rerank_results(query: str, retrieved_docs: list, llm=None) -> list:
    """
    검색된 문서들을 사용자 질문과의 관련성으로 재정렬합니다.
    (답변 품질 향상)
    """
    if llm is None:
        llm = ChatOpenAI(model_name=MODEL_NAME, temperature=0)
    
    if not retrieved_docs:
        return retrieved_docs
    
    rerank_prompt = ChatPromptTemplate.from_template("""
당신은 문서 관련성 평가 전문가입니다.

질문: {query}

아래 문서들을 질문과의 관련도로 정렬하세요.
가장 관련도 높은 것부터 순서대로 인덱스만 제공하세요. (예: 2, 0, 3, 1)

{docs_text}
""")
    
    # 문서 텍스트 준비
    docs_text = "\n\n".join([
        f"[Index {i}] (p.{doc.metadata.get('page', '?')})\n{doc.page_content[:200]}..."
        for i, doc in enumerate(retrieved_docs[:10])  # 상위 10개만
    ])
    
    chain = rerank_prompt | llm | StrOutputParser()
    result = chain.invoke({"query": query, "docs_text": docs_text})
    
    # 결과 파싱
    try:
        indices = [int(x.strip()) for x in result.split(',') if x.strip().isdigit()]
        return [retrieved_docs[i] for i in indices if i < len(retrieved_docs)]
    except:
        return retrieved_docs  # 파싱 실패시 원본 반환


def add_confidence_score(response: str, context_quality: float) -> str:
    """
    LLM의 답변에 신뢰도 점수를 표기합니다.
    
    Args:
        response: LLM 답변
        context_quality: 0~1 사이의 문맥 품질 점수
    """
    if context_quality > 0.8:
        badge = "✅ **높은 신뢰도** (충분한 문서 근거)"
    elif context_quality > 0.5:
        badge = "⚠️ **중간 신뢰도** (제한된 근거)"
    else:
        badge = "❌ **낮은 신뢰도** (불충분한 근거)"
    
    return f"{badge}\n\n{response}"

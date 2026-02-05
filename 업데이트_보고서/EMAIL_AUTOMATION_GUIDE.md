# 📧 이메일 자동화 시스템 가이드

## 개요

**MCP(Model Context Protocol) 기반 이메일 자동화 시스템**이 통합되었습니다. 이 시스템은 다음 기능을 제공합니다:

- 📬 **메일 수신**: IMAP을 통해 오늘 온 메일 자동 로드
- 🤖 **AI 답변 생성**: LLM(Claude/GPT-4o)이 자동으로 답변 작성
- ✏️ **검토 및 수정**: 발송 전에 답변 내용 수정 가능
- 📧 **메일 발송**: SMTP를 통한 안전한 메일 발송 (수동 확인 후)
- 📊 **발송 기록**: 모든 발송 기록 조회 및 임시 저장 관리

---

## 설정 방법

### 1️⃣ Gmail 설정 (권장)

**Gmail의 경우 앱 비밀번호를 생성해야 합니다.**

#### Step 1: 2단계 인증 활성화
1. [Google 계정](https://myaccount.google.com/) 방문
2. 왼쪽 메뉴에서 "보안" 클릭
3. "2단계 인증" 활성화

#### Step 2: 앱 비밀번호 생성
1. Google 계정 > 보안 > 앱 비밀번호 클릭
2. "Windows 컴퓨터" / "메일" 선택
3. 생성된 16자리 비밀번호 복사

#### Step 3: .env 파일 수정
```bash
# .env 파일 열기
nano .env
```

다음과 같이 수정:
```
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=xxxx xxxx xxxx xxxx  # 16자리 앱 비밀번호 (띄어쓰기 포함)
IMAP_SERVER=imap.gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
COMPANY_CONTEXT=당사는 세계비전 한국의 국제 구호 기구입니다.
```

---

### 2️⃣ Outlook 설정

```
EMAIL_ADDRESS=your-email@outlook.com
EMAIL_PASSWORD=your-password
IMAP_SERVER=imap-mail.outlook.com
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

---

### 3️⃣ Naver 메일 설정

```
EMAIL_ADDRESS=your-email@naver.com
EMAIL_PASSWORD=your-password
IMAP_SERVER=imap.naver.com
SMTP_SERVER=smtp.naver.com
SMTP_PORT=587
```

---

## 사용 방법

### 📬 탭 1: 메일 수신

1. **🔄 새로고침** 버튼 클릭
   - IMAP 서버에 연결하여 오늘 온 메일 목록 로드
   - 발신자, 제목, 수신 시간 표시
   
2. **메일 선택**
   - 답변하고 싶은 메일의 **✏️ 답변하기** 버튼 클릭
   - "📝 답변 작성 & 검토" 탭으로 자동 이동

---

### 📝 탭 2: 답변 작성 & 검토

#### A) AI 답변 자동 생성
1. **🤖 AI 답변 생성** 클릭
2. AI가 메일의 내용을 분석하여 전문적인 답변 자동 작성
3. "제목"과 "답변 내용" 텍스트 필드에 자동 입력

#### B) 답변 검토 및 수정
1. 자동 생성된 답변 확인
2. 필요시 텍스트 에어리어에서 직접 수정
3. 제목도 원하는 형태로 조정 가능

#### C) 메일 분류 (선택사항)
- **🔍 메일 분류** 클릭
- 메일의 분류, 응답 필요 여부, 우선순위 자동 분석

#### D) 임시 저장 (나중에 보내기)
- **💾 임시 저장** 클릭
- 메일을 데이터베이스에 임시 저장
- 나중에 "📋 임시 저장" 탭에서 다시 편집 가능

#### E) 메일 발송
**⚠️ 중요: 발송 전 항상 내용 검토!**

1. **📧 이 메일 발송하기** 클릭
   - 현재 선택된 메일에만 답변 발송
   
2. **⏭️ 다음 메일** 클릭
   - 다음 메일로 이동하여 답변 작성

---

### ✅ 탭 3: 발송 기록

#### 📤 발송 완료
- 지난 7일간 발송한 모든 메일 목록 표시
- **총 발송**, **성공**, **실패** 통계
- 발송 시간, 수신자, 제목 조회

#### 📋 임시 저장
- 아직 발송하지 않은 메일 목록
- **✏️ 편집** 버튼으로 다시 작성
- **🗑️ 삭제** 버튼으로 제거

---

## 핵심 기능 설명

### 🤖 AI 답변 생성 과정

```
원본 메일
  ↓
회사 정보 + 메일 내용 분석
  ↓
LLM (Claude/GPT-4o)
  ↓
전문적이고 정중한 답변 생성
  ↓
사용자 검토 후 발송
```

### 🔒 안전 장치

- ✅ **검토 기반 워크플로우**: AI가 자동 생성하지만 발송 전 항상 사람이 검토
- ✅ **수동 발송**: 버튼을 명시적으로 눌러야만 발송 (실수 방지)
- ✅ **임시 저장**: 급할 때는 임시 저장 후 나중에 검토 가능
- ✅ **발송 기록**: 모든 발송 내역 추적 가능

---

## 아키텍처

### 파일 구조

```
app.py                      # Streamlit 메인 앱
├── email_ui.py             # 이메일 자동화 UI 컴포넌트
│   └── email_automation_page()
│
email_mcp_server.py         # MCP 서버 (핵심 기능)
├── EmailDatabase           # SQLite 기반 데이터 저장
├── IMAPEmailClient         # 메일 수신 (IMAP)
├── SMTPEmailClient         # 메일 발송 (SMTP)
├── EmailResponseGenerator  # LLM 기반 답변 생성
└── EmailMCPServer          # 모든 기능 통합

requirements.txt            # 필요 패키지
  ├── mcp                   # Model Context Protocol
  ├── pydantic              # 데이터 검증
  ├── langchain-openai      # LLM 통합
  └── (기타 기존 패키지)

.env                        # 환경 변수 (이메일 설정)
```

### MCP 서버 도구 (Tools)

| 도구 | 설명 | 입력 | 출력 |
|------|------|------|------|
| `fetch_todays_emails()` | 오늘 온 메일 조회 | - | 메일 목록 (Email[]) |
| `generate_response_for_email()` | 메일 답변 자동 생성 | 메일 ID, 발신자, 제목, 본문 | 답변 제목, 본문 |
| `send_email()` | SMTP로 메일 발송 | 수신자, 제목, 본문 | 발송 결과 |
| `save_draft()` | 임시 저장 | 수신자, 제목, 본문 | 저장 결과 |
| `get_email_history()` | 발송 기록 조회 | 조회 기간 (일) | 발송 로그 |
| `get_drafts()` | 임시 저장 메일 조회 | - | 임시 저장 목록 |
| `classify_email()` | 메일 자동 분류 | 제목, 본문 | 분류, 응답 필요 여부, 우선순위 |

---

## 데이터베이스

### SQLite 테이블

#### 1. send_logs (발송 기록)
```sql
CREATE TABLE send_logs (
  id INTEGER PRIMARY KEY,
  timestamp TEXT,           -- 발송 시간
  to_address TEXT,          -- 수신자 이메일
  subject TEXT,             -- 메일 제목
  status TEXT,              -- success/failed
  original_email_id TEXT    -- 답변한 원본 메일 ID
)
```

#### 2. draft_emails (임시 저장)
```sql
CREATE TABLE draft_emails (
  id INTEGER PRIMARY KEY,
  to_address TEXT,          -- 수신자 이메일
  subject TEXT,             -- 제목
  body TEXT,                -- 본문
  original_email_id TEXT    -- 원본 메일 ID
)
```

---

## 문제 해결

### ❌ "IMAP 서버 연결 실패"

**원인:**
- 이메일 주소/비밀번호 오류
- 2단계 인증이 활성화되지 않음 (Gmail의 경우)
- 앱 비밀번호 대신 일반 비밀번호 사용

**해결:**
1. .env 파일의 EMAIL_ADDRESS와 EMAIL_PASSWORD 재확인
2. Gmail: 앱 비밀번호 재생성 및 적용
3. 띄어쓰기 포함 16자리 비밀번호 확인

---

### ❌ "SMTP 서버 연결 실패"

**원인:**
- SMTP 포트 설정 오류
- 보안 설정으로 차단됨

**해결:**
1. SMTP_PORT=587 (권장) 또는 465 확인
2. Gmail의 경우 "보안 수준이 낮은 앱 액세스" 허용

---

### ❌ "AI 답변 생성 실패"

**원인:**
- OpenAI API 키 오류
- API 할당량 초과
- 네트워크 연결 문제

**해결:**
1. OPENAI_API_KEY 확인
2. OpenAI 대시보드에서 잔여 크레딧 확인
3. 인터넷 연결 확인

---

## 향후 계획 (v2.1.0+)

- [ ] 메일 일정 자동화 (특정 시간에 답변 생성)
- [ ] 메일 템플릿 기능 (자주 쓰는 문구 저장)
- [ ] 메일 분류 자동 라우팅 (우선순위별 처리)
- [ ] Outlook 캘린더 연동
- [ ] 메일 첨부 파일 처리
- [ ] 멀티 계정 지원

---

## 참고 사항

⚠️ **보안 유의사항:**
- .env 파일에 실제 비밀번호 포함 (GitHub에 절대 업로드 하지 말 것)
- 사내 보안망 내에서만 사용 권장
- 정기적으로 .env 파일 보안 점검

💡 **성능 팁:**
- IMAP 로드 시간: 약 2~3초 (메일 개수에 따라)
- AI 답변 생성: 약 3~5초
- 메일 발송: 약 1~2초

---

## 지원

질문이나 문제가 생기면:
1. 📖 이 문서의 "문제 해결" 섹션 확인
2. 📧 시스템 관리자에 문의
3. 💬 개발팀에 피드백

---

**마지막 업데이트: 2026년 2월 3일**

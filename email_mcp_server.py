"""
이메일 자동화 MCP 서버

기능:
1. IMAP을 통한 메일 수신 (오늘 메일만)
2. LLM 기반 자동 답변 생성
3. SMTP를 통한 메일 발송
4. 발송 기록 관리
"""

import json
import os
import smtplib
import imaplib
import sqlite3
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.parser import Parser
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


# ========================
# 데이터 모델
# ========================

class Email(BaseModel):
    """이메일 데이터 모델"""
    email_id: str = Field(description="이메일 고유 ID")
    from_address: str = Field(description="발신자 이메일")
    from_name: str = Field(description="발신자 이름")
    subject: str = Field(description="제목")
    body: str = Field(description="본문")
    received_date: str = Field(description="수신 시간")
    is_reply: bool = Field(description="답변 여부", default=False)
    attachments: List[Dict[str, Any]] = Field(description="첨부 파일 목록", default_factory=list)


class EmailResponse(BaseModel):
    """메일 답변 데이터"""
    to_address: str = Field(description="수신자 이메일")
    to_name: str = Field(description="수신자 이름")
    subject: str = Field(description="응답 제목")
    body: str = Field(description="응답 본문")
    original_email_id: Optional[str] = Field(description="원본 메일 ID", default=None)
    draft_status: bool = Field(description="발송 대기 상태", default=True)


class EmailSendLog(BaseModel):
    """메일 발송 기록"""
    timestamp: str = Field(description="발송 시간")
    to_address: str = Field(description="수신자 이메일")
    subject: str = Field(description="제목")
    status: str = Field(description="발송 상태 (success/failed)")
    original_email_id: Optional[str] = Field(description="원본 메일 ID", default=None)


# ========================
# 데이터베이스 관리
# ========================

class EmailDatabase:
    """SQLite 기반 이메일 데이터베이스"""

    def __init__(self, db_path: str = "email_records.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 발송 기록 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS send_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    to_address TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    status TEXT NOT NULL,
                    original_email_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 임시 저장 메일 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS draft_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    to_address TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    original_email_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")

    def save_send_log(self, log: EmailSendLog) -> bool:
        """발송 기록 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO send_logs 
                    (timestamp, to_address, subject, status, original_email_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    log.timestamp,
                    log.to_address,
                    log.subject,
                    log.status,
                    log.original_email_id
                ))
                conn.commit()
                logger.info(f"Send log saved: {log.to_address}")
                return True
        except Exception as e:
            logger.error(f"Failed to save log: {e}")
            return False

    def save_draft(self, draft: EmailResponse) -> bool:
        """임시 저장 메일 저장"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO draft_emails
                    (to_address, subject, body, original_email_id)
                    VALUES (?, ?, ?, ?)
                """, (
                    draft.to_address,
                    draft.subject,
                    draft.body,
                    draft.original_email_id
                ))
                conn.commit()
                logger.info(f"Draft saved: {draft.to_address}")
                return True
        except Exception as e:
            logger.error(f"Failed to save draft: {e}")
            return False

    def get_send_logs(self, days: int = 7) -> List[Dict]:
        """발송 기록 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT timestamp, to_address, subject, status
                    FROM send_logs
                    WHERE created_at > datetime('now', '-' || ? || ' days')
                    ORDER BY created_at DESC
                """, (days,))
                
                columns = [description[0] for description in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
        except Exception as e:
            logger.error(f"Failed to get logs: {e}")
            return []

    def get_drafts(self) -> List[Dict]:
        """임시 저장 메일 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, to_address, subject, body, original_email_id
                    FROM draft_emails
                    ORDER BY created_at DESC
                """)
                
                columns = [description[0] for description in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results
        except Exception as e:
            logger.error(f"Failed to get drafts: {e}")
            return []

    def delete_draft(self, draft_id: int) -> bool:
        """임시 저장 메일 삭제"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM draft_emails WHERE id = ?", (draft_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to delete draft: {e}")
            return False


# ========================
# IMAP 메일 클라이언트
# ========================

class IMAPEmailClient:
    """IMAP을 통한 메일 수신"""

    def __init__(self, email: str, password: str, imap_server: str = "imap.gmail.com"):
        self.email = email
        self.password = password
        self.imap_server = imap_server
        self.connection = None

    def connect(self) -> bool:
        """IMAP 서버 연결"""
        try:
            self.connection = imaplib.IMAP4_SSL(self.imap_server)
            self.connection.login(self.email, self.password)
            logger.info(f"Connected to {self.imap_server}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IMAP: {e}")
            return False

    def disconnect(self):
        """IMAP 연결 종료"""
        if self.connection:
            self.connection.close()

    def get_todays_emails(self) -> List[Email]:
        """오늘 온 메일 조회"""
        if not self.connection:
            logger.error("Not connected to IMAP server")
            return []

        try:
            # INBOX 선택
            self.connection.select("INBOX")
            
            # 오늘 날짜로 검색
            today = datetime.now().strftime("%d-%b-%Y")
            status, messages = self.connection.search(None, f"SINCE {today}")
            
            if status != "OK":
                logger.error("Failed to search emails")
                return []

            email_ids = messages[0].split()
            emails = []

            for email_id in email_ids[::-1]:  # 최신순 정렬
                try:
                    status, msg_data = self.connection.fetch(email_id, "(RFC822)")
                    if status != "OK":
                        continue

                    msg = Parser().parsestr(msg_data[0][1].decode("utf-8"))
                    
                    # 메일 정보 추출
                    from_header = msg.get("From", "")
                    from_name = self._parse_email_header(from_header)[0]
                    from_address = self._parse_email_header(from_header)[1]
                    
                    subject = msg.get("Subject", "(제목 없음)")
                    body = self._get_email_body(msg)
                    attachments = self._get_email_attachments(msg)
                    received_date = msg.get("Date", "")

                    emails.append(Email(
                        email_id=email_id.decode(),
                        from_address=from_address,
                        from_name=from_name,
                        subject=subject,
                        body=body,
                        received_date=received_date,
                        is_reply=False,
                        attachments=attachments
                    ))

                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue

            logger.info(f"Retrieved {len(emails)} emails from today")
            return emails

        except Exception as e:
            logger.error(f"Failed to get emails: {e}")
            return []

    @staticmethod
    def _parse_email_header(header: str) -> tuple:
        """이메일 헤더에서 이름과 주소 추출"""
        if "<" in header and ">" in header:
            name = header.split("<")[0].strip().strip('"')
            address = header.split("<")[1].split(">")[0].strip()
            return name, address
        else:
            return "", header.strip()

    @staticmethod
    def _html_to_text(html: str) -> str:
        """HTML을 순수 텍스트로 변환"""
        # 스크립트와 스타일 태그 제거
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # HTML 태그 제거
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<p[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<div[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        
        # HTML 엔티티 디코딩
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        # 여러 줄바꿈을 한 개로
        text = re.sub(r'\n\n+', '\n\n', text)
        
        return text.strip()

    @staticmethod
    def _get_email_body(msg) -> str:
        """이메일 본문 추출 (HTML 지원)"""
        body = ""
        html_body = ""
        
        if msg.is_multipart():
            # multipart 메일은 모든 부분을 순회
            for part in msg.walk():
                content_type = part.get_content_type()
                
                try:
                    # text/plain을 우선으로
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
                    # text/plain이 없으면 text/html 저장
                    elif content_type == "text/html" and not html_body:
                        html_body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception as e:
                    logger.warning(f"Error decoding body: {e}")
                    continue
        else:
            # 단일 부분 메일
            try:
                content_type = msg.get_content_type()
                payload = msg.get_payload(decode=True)
                
                if isinstance(payload, bytes):
                    payload = payload.decode("utf-8", errors="ignore")
                
                if content_type == "text/html":
                    html_body = payload
                else:
                    body = payload
            except Exception as e:
                logger.warning(f"Error getting payload: {e}")
        
        # text/plain이 없으면 HTML을 텍스트로 변환
        if not body and html_body:
            body = IMAPEmailClient._html_to_text(html_body)
        
        return body.strip()[:1000]  # 최대 1000자까지만

    @staticmethod
    def _get_email_attachments(msg) -> List[Dict[str, Any]]:
        """이메일 첨부 파일 추출"""
        attachments = []
        
        if not msg.is_multipart():
            return attachments
        
        for part in msg.walk():
            # Content-Disposition 헤더 확인 (attachment 여부)
            if part.get_content_disposition() == "attachment":
                try:
                    filename = part.get_filename()
                    if filename:
                        # 한글 파일명 디코딩
                        if isinstance(filename, str):
                            # header.decode() 시도 (인코딩된 경우)
                            try:
                                filename = filename.encode('latin1').decode('utf-8')
                            except (UnicodeDecodeError, UnicodeEncodeError):
                                pass
                        
                        content_type = part.get_content_type()
                        payload = part.get_payload(decode=True)
                        
                        # 파일 크기 계산 (바이트)
                        file_size = len(payload) if payload else 0
                        
                        attachments.append({
                            "filename": filename,
                            "content_type": content_type,
                            "data": payload,
                            "size": file_size
                        })
                        logger.info(f"Extracted attachment: {filename} ({file_size} bytes)")
                except Exception as e:
                    logger.warning(f"Error extracting attachment: {e}")
                    continue
        
        return attachments


# ========================
# SMTP 메일 클라이언트
# ========================

class SMTPEmailClient:
    """SMTP을 통한 메일 발송"""

    def __init__(self, email: str, password: str, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587):
        self.email = email
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.connection = None

    def connect(self) -> bool:
        """SMTP 서버 연결"""
        try:
            self.connection = smtplib.SMTP(self.smtp_server, self.smtp_port)
            self.connection.starttls()
            self.connection.login(self.email, self.password)
            logger.info(f"Connected to {self.smtp_server}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SMTP: {e}")
            return False

    def disconnect(self):
        """SMTP 연결 종료"""
        if self.connection:
            self.connection.quit()

    def send_email(self, to_address: str, subject: str, body: str) -> bool:
        """메일 발송"""
        if not self.connection:
            logger.error("Not connected to SMTP server")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email
            msg["To"] = to_address
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain", "utf-8"))

            self.connection.sendmail(self.email, to_address, msg.as_string())
            logger.info(f"Email sent to {to_address}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


# ========================
# LLM 기반 응답 생성
# ========================

class EmailResponseGenerator:
    """LLM을 활용한 자동 답변 생성"""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(model=model, temperature=0.7)

    def generate_response(self, original_email: Email, company_context: str = "") -> str:
        """원본 메일에 대한 답변 생성"""
        
        prompt = ChatPromptTemplate.from_template("""
당신은 회사의 메일 담당자입니다. 다음 메일에 대한 전문적인 답변을 작성하세요.

회사 정보:
{company_context}

원본 메일:
발신자: {from_name} ({from_address})
제목: {subject}
본문:
{body}

다음 조건을 지켜서 답변을 작성하세요:
1. 정중하고 전문적인 톤 사용
2. 명확하고 간결한 내용 (300자 이내)
3. 구체적인 답변 제공
4. 필요시 다음 단계 제시

답변만 작성하세요 (인사말 없이):
""")

        chain = prompt | self.llm

        try:
            response = chain.invoke({
                "company_context": company_context or "일반 기업",
                "from_name": original_email.from_name,
                "from_address": original_email.from_address,
                "subject": original_email.subject,
                "body": original_email.body
            })

            return response.content.strip()

        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return "죄송합니다. 현재 답변을 생성할 수 없습니다. 잠시 후 다시 시도해주세요."

    def generate_subject(self, original_subject: str) -> str:
        """응답 제목 생성 (Re: 붙이기)"""
        if not original_subject.startswith("Re:"):
            return f"Re: {original_subject}"
        return original_subject


# ========================
# MCP 서버 메인 클래스
# ========================

class EmailMCPServer:
    """이메일 자동화 MCP 서버"""

    def __init__(self):
        self.email = os.getenv("EMAIL_ADDRESS")
        self.password = os.getenv("EMAIL_PASSWORD")
        self.imap_server = os.getenv("IMAP_SERVER", "imap.gmail.com")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.company_context = os.getenv("COMPANY_CONTEXT", "")
        
        self.imap_client = IMAPEmailClient(self.email, self.password, self.imap_server)
        self.smtp_client = SMTPEmailClient(self.email, self.password, self.smtp_server)
        self.response_generator = EmailResponseGenerator()
        self.db = EmailDatabase()

    def fetch_todays_emails(self) -> Dict[str, Any]:
        """
        오늘 온 메일 목록 조회
        
        Returns:
            {
                "success": bool,
                "emails": List[Email],
                "count": int
            }
        """
        try:
            if not self.imap_client.connect():
                return {
                    "success": False,
                    "emails": [],
                    "count": 0,
                    "error": "IMAP 서버 연결 실패"
                }

            emails = self.imap_client.get_todays_emails()
            self.imap_client.disconnect()

            return {
                "success": True,
                "emails": [email.model_dump() for email in emails],
                "count": len(emails)
            }

        except Exception as e:
            logger.error(f"Error in fetch_todays_emails: {e}")
            return {
                "success": False,
                "emails": [],
                "count": 0,
                "error": str(e)
            }

    def generate_response_for_email(self, email_id: str, from_address: str, subject: str, body: str) -> Dict[str, Any]:
        """
        특정 메일에 대한 답변 생성
        
        Args:
            email_id: 원본 메일 ID
            from_address: 발신자 이메일
            subject: 제목
            body: 본문
            
        Returns:
            {
                "success": bool,
                "subject": str,
                "response": str
            }
        """
        try:
            email = Email(
                email_id=email_id,
                from_address=from_address,
                from_name=from_address.split("@")[0],
                subject=subject,
                body=body,
                received_date=datetime.now().isoformat(),
                is_reply=True
            )

            response_subject = self.response_generator.generate_subject(subject)
            response_body = self.response_generator.generate_response(email, self.company_context)

            return {
                "success": True,
                "subject": response_subject,
                "response": response_body
            }

        except Exception as e:
            logger.error(f"Error in generate_response_for_email: {e}")
            return {
                "success": False,
                "subject": "",
                "response": "",
                "error": str(e)
            }

    def send_email(self, to_address: str, subject: str, body: str, original_email_id: Optional[str] = None) -> Dict[str, Any]:
        """
        메일 발송
        
        Args:
            to_address: 수신자 이메일
            subject: 제목
            body: 본문
            original_email_id: 원본 메일 ID (선택)
            
        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        try:
            if not self.smtp_client.connect():
                return {
                    "success": False,
                    "message": "SMTP 서버 연결 실패"
                }

            success = self.smtp_client.send_email(to_address, subject, body)
            self.smtp_client.disconnect()

            # 발송 기록 저장
            if success:
                log = EmailSendLog(
                    timestamp=datetime.now().isoformat(),
                    to_address=to_address,
                    subject=subject,
                    status="success",
                    original_email_id=original_email_id
                )
                self.db.save_send_log(log)

                return {
                    "success": True,
                    "message": f"메일이 {to_address}로 발송되었습니다."
                }
            else:
                return {
                    "success": False,
                    "message": "메일 발송 실패"
                }

        except Exception as e:
            logger.error(f"Error in send_email: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def save_draft(self, to_address: str, subject: str, body: str, original_email_id: Optional[str] = None) -> Dict[str, Any]:
        """
        메일 임시 저장 (발송 전)
        
        Args:
            to_address: 수신자 이메일
            subject: 제목
            body: 본문
            original_email_id: 원본 메일 ID (선택)
            
        Returns:
            {
                "success": bool,
                "message": str
            }
        """
        try:
            draft = EmailResponse(
                to_address=to_address,
                to_name="",
                subject=subject,
                body=body,
                original_email_id=original_email_id,
                draft_status=True
            )

            if self.db.save_draft(draft):
                return {
                    "success": True,
                    "message": "메일이 임시 저장되었습니다."
                }
            else:
                return {
                    "success": False,
                    "message": "임시 저장 실패"
                }

        except Exception as e:
            logger.error(f"Error in save_draft: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def get_email_history(self, days: int = 7) -> Dict[str, Any]:
        """
        발송 기록 조회
        
        Args:
            days: 조회 기간 (일)
            
        Returns:
            {
                "success": bool,
                "logs": List[Dict]
            }
        """
        try:
            logs = self.db.get_send_logs(days)
            return {
                "success": True,
                "logs": logs,
                "count": len(logs)
            }
        except Exception as e:
            logger.error(f"Error in get_email_history: {e}")
            return {
                "success": False,
                "logs": [],
                "error": str(e)
            }

    def get_drafts(self) -> Dict[str, Any]:
        """
        임시 저장 메일 조회
        
        Returns:
            {
                "success": bool,
                "drafts": List[Dict]
            }
        """
        try:
            drafts = self.db.get_drafts()
            return {
                "success": True,
                "drafts": drafts,
                "count": len(drafts)
            }
        except Exception as e:
            logger.error(f"Error in get_drafts: {e}")
            return {
                "success": False,
                "drafts": [],
                "error": str(e)
            }

    def classify_email(self, subject: str, body: str) -> Dict[str, Any]:
        """
        메일 분류 (자동 응답 필요도 판단)
        
        Args:
            subject: 제목
            body: 본문
            
        Returns:
            {
                "success": bool,
                "category": str,
                "requires_response": bool,
                "priority": str
            }
        """
        try:
            prompt = ChatPromptTemplate.from_template("""
다음 이메일을 분석하고 분류하세요.

제목: {subject}
본문: {body}

다음 형식으로 JSON 응답을 제공하세요:
{{
    "category": "일반/문의/불만/긴급",
    "requires_response": true/false,
    "priority": "높음/중간/낮음"
}}

JSON만 응답하세요:
""")

            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
            chain = prompt | llm

            response = chain.invoke({
                "subject": subject,
                "body": body
            })

            result = json.loads(response.content)
            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"Error in classify_email: {e}")
            return {
                "success": False,
                "category": "일반",
                "requires_response": False,
                "priority": "낮음",
                "error": str(e)
            }


# ========================
# 테스트 코드
# ========================

if __name__ == "__main__":
    # 테스트
    server = EmailMCPServer()
    
    # 1. 오늘 메일 조회
    print("=== 오늘 메일 조회 ===")
    result = server.fetch_todays_emails()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 2. 발송 기록 조회
    print("\n=== 발송 기록 조회 ===")
    history = server.get_email_history()
    print(json.dumps(history, ensure_ascii=False, indent=2))

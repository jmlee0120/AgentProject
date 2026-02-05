#!/usr/bin/env python3
"""
첨부 파일을 포함한 테스트 메일 발송
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def send_test_email_with_attachment():
    """첨부 파일이 있는 테스트 메일 발송"""
    
    # 환경 변수에서 이메일 정보 로드
    sender_email = os.getenv("EMAIL_ADDRESS")
    email_password = os.getenv("EMAIL_PASSWORD")
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    
    if not sender_email or not email_password:
        print("❌ EMAIL_ADDRESS 또는 EMAIL_PASSWORD가 설정되지 않았습니다.")
        return False
    
    try:
        # SMTP 연결
        print("📧 Gmail SMTP 서버에 연결 중...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, email_password)
        print("✅ SMTP 서버에 연결되었습니다")
        
        # 메일 구성
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = sender_email  # 자신에게 발송
        msg["Subject"] = "🧪 테스트: 첨부 파일이 있는 메일"
        
        # 본문
        body = """
안녕하세요!

이것은 첨부 파일 테스트를 위한 메일입니다.
아래 첨부 파일을 다운로드할 수 있습니다.

감사합니다.
"""
        msg.attach(MIMEText(body, "plain"))
        
        # 테스트 파일 생성
        test_files = [
            ("test_document.txt", "이것은 테스트 파일입니다.\n첨부 파일 다운로드 기능을 테스트합니다."),
            ("sample.csv", "이름,이메일,회사\n김철수,kim@example.com,Example Corp\n이영희,lee@example.com,Tech Inc"),
        ]
        
        # 파일 첨부
        print("📎 테스트 파일을 첨부 중...")
        for filename, content in test_files:
            # 메모리에 바이트 객체 생성
            attachment = MIMEBase("application", "octet-stream")
            attachment.set_payload(content.encode())
            encoders.encode_base64(attachment)
            attachment.add_header("Content-Disposition", f"attachment; filename= {filename}")
            msg.attach(attachment)
            print(f"   ✅ {filename} 첨부됨")
        
        # 메일 발송
        print("🚀 메일 발송 중...")
        server.send_message(msg)
        server.quit()
        print("✅ 메일이 성공적으로 발송되었습니다!")
        print(f"📬 {sender_email}로 메일을 확인하면 첨부 파일을 보실 수 있습니다.")
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("📧 첨부 파일 테스트 메일 발송")
    print("="*60 + "\n")
    
    success = send_test_email_with_attachment()
    
    print("\n" + "="*60)
    if success:
        print("✅ 작업 완료!")
        print("💡 이제 앱을 실행하고 '🔄 새로고침'을 눌러")
        print("   첨부 파일 다운로드 기능을 테스트하세요.")
    else:
        print("❌ 메일 발송 실패")
    print("="*60)

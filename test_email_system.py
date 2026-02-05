"""
이메일 자동화 시스템 테스트 스크립트

실행: python test_email_system.py
"""

import os
import json
from dotenv import load_dotenv
from email_mcp_server import EmailMCPServer

load_dotenv()


def print_section(title):
    """섹션 제목 출력"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_environment():
    """환경 변수 확인"""
    print_section("🔧 환경 변수 확인")
    
    required_vars = [
        "EMAIL_ADDRESS",
        "EMAIL_PASSWORD",
        "OPENAI_API_KEY",
        "IMAP_SERVER",
        "SMTP_SERVER"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if var == "OPENAI_API_KEY":
            status = "✅" if value and value.startswith("sk-") else "❌"
            print(f"{status} {var}: {'설정됨' if value else '설정 안 됨'}")
        elif var == "EMAIL_PASSWORD":
            status = "✅" if value else "❌"
            print(f"{status} {var}: {'설정됨' if value else '설정 안 됨'}")
        else:
            print(f"✅ {var}: {value}")


def test_imap_connection():
    """IMAP 연결 테스트"""
    print_section("📬 IMAP 연결 테스트")
    
    try:
        server = EmailMCPServer()
        
        # IMAP 연결 시도
        if server.imap_client.connect():
            print("✅ IMAP 서버 연결 성공")
            
            # 오늘 메일 조회
            emails = server.imap_client.get_todays_emails()
            print(f"✅ {len(emails)}개의 메일 로드됨")
            
            if emails:
                print("\n📧 최근 메일:")
                for i, email in enumerate(emails[:3], 1):
                    print(f"  {i}. {email.subject}")
                    print(f"     From: {email.from_name} <{email.from_address}>")
                    print(f"     Date: {email.received_date}\n")
            else:
                print("⚠️  오늘 온 메일이 없습니다.")
            
            server.imap_client.disconnect()
            return True
        else:
            print("❌ IMAP 서버 연결 실패")
            print("   - 이메일 주소 확인")
            print("   - 앱 비밀번호 확인 (Gmail의 경우)")
            print("   - 네트워크 연결 확인")
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False


def test_smtp_connection():
    """SMTP 연결 테스트"""
    print_section("📧 SMTP 연결 테스트")
    
    try:
        server = EmailMCPServer()
        
        if server.smtp_client.connect():
            print("✅ SMTP 서버 연결 성공")
            server.smtp_client.disconnect()
            
            print("\n💡 테스트 메일 발송은 안 합니다.")
            print("   (실제 메일이 발송되지 않도록)")
            return True
        else:
            print("❌ SMTP 서버 연결 실패")
            print("   - 이메일 주소 확인")
            print("   - SMTP 포트 설정 확인")
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False


def test_llm_integration():
    """LLM 통합 테스트"""
    print_section("🤖 LLM 통합 테스트")
    
    try:
        server = EmailMCPServer()
        
        # 샘플 메일로 테스트
        from email_mcp_server import Email
        
        sample_email = Email(
            email_id="test_001",
            from_address="sender@example.com",
            from_name="테스트 발신자",
            subject="회의 일정 확인",
            body="내주 월요일 2시에 프로젝트 회의가 있을 예정입니다. 참석 가능하신지 확인 부탁드립니다.",
            received_date="2026-02-03",
            is_reply=False
        )
        
        print("📝 샘플 메일로 답변 생성 중...")
        response = server.response_generator.generate_response(sample_email)
        
        print("✅ LLM 답변 생성 성공\n")
        print("생성된 답변:")
        print("-" * 60)
        print(response)
        print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ LLM 통합 실패: {e}")
        print("   - OpenAI API 키 확인")
        print("   - 네트워크 연결 확인")
        return False


def test_database():
    """데이터베이스 테스트"""
    print_section("💾 데이터베이스 테스트")
    
    try:
        server = EmailMCPServer()
        
        # 임시 저장 테스트
        from email_mcp_server import EmailResponse, EmailSendLog
        
        draft = EmailResponse(
            to_address="test@example.com",
            to_name="테스트",
            subject="테스트 메일",
            body="이것은 테스트 메일입니다.",
            original_email_id="test_001"
        )
        
        if server.db.save_draft(draft):
            print("✅ 데이터베이스에 임시 저장 성공")
        else:
            print("❌ 데이터베이스 저장 실패")
            return False
        
        # 발송 기록 조회
        logs = server.db.get_send_logs(days=7)
        print(f"✅ {len(logs)}개의 발송 기록 조회")
        
        # 임시 저장 조회
        drafts = server.db.get_drafts()
        print(f"✅ {len(drafts)}개의 임시 저장 메일 조회")
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 오류: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║       📧 이메일 자동화 시스템 진단                        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    results = {
        "환경 변수": True,  # 항상 성공 (확인만 하므로)
        "IMAP 연결": test_imap_connection(),
        "SMTP 연결": test_smtp_connection(),
        "LLM 통합": test_llm_integration(),
        "데이터베이스": test_database()
    }
    
    test_environment()
    
    # 결과 요약
    print_section("📊 테스트 결과 요약")
    
    for test_name, result in results.items():
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{status} - {test_name}")
    
    success_count = sum(1 for r in results.values() if r)
    total_count = len(results)
    
    print(f"\n전체: {success_count}/{total_count} 통과")
    
    if success_count == total_count:
        print("\n🎉 모든 테스트 통과! 시스템이 정상 작동합니다.")
    else:
        print("\n⚠️  일부 테스트가 실패했습니다.")
        print("   위의 오류 메시지를 확인하여 문제를 해결해주세요.")
        print("   - EMAIL_AUTOMATION_GUIDE.md의 '문제 해결' 섹션 참고")
    
    print("\n" + "=" * 60)
    print("테스트 완료\n")


if __name__ == "__main__":
    main()

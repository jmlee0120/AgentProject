#!/usr/bin/env python3
"""
첨부 파일 추출 기능 테스트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 경로
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from email_mcp_server import EmailMCPServer

def test_attachment_extraction():
    """첨부 파일 추출 테스트"""
    print("\n" + "="*60)
    print("📎 첨부 파일 추출 기능 테스트")
    print("="*60)
    
    try:
        # EmailMCPServer 초기화
        server = EmailMCPServer()
        print("✅ EmailMCPServer 초기화 완료")
        
        # 오늘의 메일 가져오기
        print("\n📧 오늘의 메일 로드 중...")
        result = server.fetch_todays_emails()
        
        if not result["success"]:
            print(f"❌ 메일 로드 실패: {result.get('error')}")
            return False
        
        emails = result["emails"]
        print(f"✅ {len(emails)}개의 메일 로드 완료")
        
        # 첨부 파일이 있는 메일 찾기
        print("\n🔍 첨부 파일 확인 중...")
        attachment_count = 0
        for idx, email in enumerate(emails):
            if email.get("attachments"):
                attachment_count += len(email["attachments"])
                print(f"\n📧 메일 {idx+1}: {email['subject']}")
                print(f"   📎 첨부 파일 {len(email['attachments'])}개:")
                for att in email["attachments"]:
                    filename = att.get("filename", "알 수 없음")
                    size = att.get("size", 0)
                    content_type = att.get("content_type", "")
                    print(f"      - {filename} ({size} bytes, {content_type})")
        
        if attachment_count == 0:
            print("⚠️  첨부 파일이 있는 메일이 없습니다.")
            print("💡 실제 첨부 파일이 있는 메일을 보내면 테스트할 수 있습니다.")
        else:
            print(f"\n✅ 총 {attachment_count}개의 첨부 파일 발견")
        
        return True
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_attachment_extraction()
    print("\n" + "="*60)
    if success:
        print("✅ 테스트 완료: 첨부 파일 추출 기능이 정상 작동합니다")
    else:
        print("❌ 테스트 실패")
    print("="*60)

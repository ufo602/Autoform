import os
from hwpx_filler import fill_meeting_minutes_hwpx

template_path = os.path.join('양식', '회의록 양식.hwpx')
with open(template_path, 'rb') as f:
    tpl_bytes = f.read()

sample_data = {
    "title": "2026 AI 데이터 플랫폼 개발 주간 회의",
    "datetime": "2026년 9월 10일 14:00 ~ 15:30",
    "place": "본관 3층 스마트 회의실",
    "attendees": "김철수 팀장, 이영희 선임, 박민수 책임",
    "host": "김철수 팀장",
    "agenda": "1. 양식 채우기 자동화 서비스 아키텍처 점검\n2. OpenRouter STT 및 텍스트 모델 연동 방안",
    "discussion": "(김철수) 이번 주 개발 목표인 회의록 양식 채우기 서비스 프로토타입 상태를 점검하겠습니다.\n(이영희) HWPX XML 파싱 및 셀 매핑 로직 작성을 완료하였으며, 다중 문단 및 발화자 형식 표기가 정상 반영됩니다.\n(박민수) OpenRouter 음성 STT 파이프라인과 프론트엔드 연동이 원활하게 진행되고 있습니다.",
    "schedule": "- 9월 12일: 1차 내부 기능 테스트\n- 9월 15일: 사용자 피드백 수렴 및 UI 고도화"
}

output_bytes = fill_meeting_minutes_hwpx(tpl_bytes, sample_data)
out_path = '테스트_회의록_완성본.hwpx'
with open(out_path, 'wb') as f:
    f.write(output_bytes)

print(f"Generated {out_path} ({len(output_bytes)} bytes)")

# Verify XML inside
import zipfile, xml.etree.ElementTree as ET
with zipfile.ZipFile(out_path, 'r') as z:
    sec = z.read('Contents/section0.xml')
    root = ET.fromstring(sec)
    ns = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph'}
    texts = [t.text for t in root.findall('.//hp:t', ns) if t.text]
    print("\nTotal text elements in output:", len(texts))
    for t in texts:
        print(" -", t)

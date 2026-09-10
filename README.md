# Autoform (AI 회의록 자동 작성 & HWPX 양식 채우기 서비스)

사용자가 텍스트 또는 음성(실시간 녹음 / 오디오 파일 업로드)으로 회의 내용을 입력하면, **Google Gemini API** 또는 **OpenRouter AI 모델**을 통해 한글 회의록 양식(`양식/회의록 양식.hwpx`)에 맞게 회의록을 자동으로 작성하고 완성된 `.hwpx` 파일로 다운로드할 수 있는 웹 서비스입니다.

---

## 주요 기능

1. **음성 인식 (STT)**:
   - 마이크 실시간 녹음 및 오디오 파일(MP3, WAV, M4A, WEBM 등) 드래그 & 드롭 업로드 지원
   - Gemini 멀티모달 오디오 처리 또는 OpenRouter Whisper-large-v3를 통한 한국어 텍스트 전사
2. **회의록 양식 자동 구조화**:
   - 회의제목, 일시, 장소, 참석자, 주최자, 안건, 논의 내용, 추후 일정 자동 추출
   - **논의 내용의 경우 `(발화자) 내용` 필수 양식** 준수
3. **HWPX 템플릿 보존 및 자동 채우기**:
   - 한글 표준 XML(HWPX) 구조를 파싱하여 기존 서식(표 크기, 정렬, 글꼴 등)을 보존한 채 줄바꿈 문단을 주입
4. **모던 웹 UI (HTML/CSS/JS)**:
   - 프리미엄 다크 글래스모피즘 인터페이스
   - 추출된 회의록 실시간 인라인 편집 지원
   - 원클릭 HWPX 다운로드
5. **다양한 AI API 지원**:
   - Google Gemini 직접 연결 (`gemini-3.6-flash` 등)
   - OpenRouter 연결 (`gemini`, `claude-3.5-sonnet`, `gpt-4o` 등)

---

## 실행 방법

### 1. 필수 라이브러리 설치
```bash
pip install fastapi uvicorn requests python-multipart
```

### 2. 서비스 실행
```bash
python app.py
# 또는
uvicorn app:app --host 127.0.0.1 --port 8080
```

### 3. 웹 브라우저 접속
- 주소: `http://127.0.0.1:8080`
- 우측 상단 **[API 설정]**에서 본인의 **Google Gemini API Key** 또는 **OpenRouter API Key**를 입력 후 회의록 생성을 진행하세요.

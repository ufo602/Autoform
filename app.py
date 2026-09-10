import os
import json
import base64
import requests
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
from typing import Optional
from hwpx_filler import fill_meeting_minutes_hwpx

app = FastAPI(title="회의록 자동 작성 & HWPX 양식 채우기 서비스")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "양식", "회의록 양식.hwpx")

@app.get("/api/config")
async def get_server_config():
    """
    서버 환경변수(.env 또는 OS 환경변수)에서 설정된 기본 API Key 및 모델 정보를 반환
    클라이언트 초기 로딩 시 자동 입력용으로 사용됨
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or ""
    openrouter_key = os.getenv("OPENROUTER_API_KEY") or ""
    provider = "gemini" if gemini_key or not openrouter_key else "openrouter"

    return {
        "gemini_api_key": gemini_key,
        "gemini_model": os.getenv("GEMINI_MODEL") or "gemini-3.6-flash",
        "openrouter_api_key": openrouter_key,
        "openrouter_model": os.getenv("OPENROUTER_MODEL") or "google/gemini-2.5-flash",
        "openrouter_stt_model": os.getenv("OPENROUTER_STT_MODEL") or "openai/whisper-large-v3",
        "default_provider": provider
    }

class GenerateRequest(BaseModel):
    text: str
    provider: Optional[str] = "gemini" # "gemini" or "openrouter"
    api_key: Optional[str] = None
    model: Optional[str] = "gemini-3.6-flash"

class MinutesData(BaseModel):
    title: str = ""
    datetime: str = ""
    place: str = ""
    attendees: str = ""
    host: str = ""
    agenda: str = ""
    discussion: str = ""
    schedule: str = ""


SYSTEM_PROMPT = """당신은 기업 및 공공기관의 공식 회의록 작성 전문가입니다.
사용자가 제공하는 회의 내용(대화록, 음성 전사 텍스트, 메모 등)을 분석하여 아래의 HWPX 회의록 양식에 맞춘 정형화된 JSON 객체를 반환해야 합니다.

[중요 필수 요구사항]
1. discussion(논의 내용) 항목은 반드시 "(발화자) 내용" 양식으로 작성해야 합니다.
   예시:
   (홍길동) 이번 프로젝트 1차 배포 일정에 대해 의견을 듣고 싶습니다.
   (김철수) 프론트엔드 작업은 마무리 단계이며, 백엔드 연동 테스트가 목요일까지 진행됩니다.
   (이영희) 보안 점검 체크리스트 검토를 금요일까지 완료하겠습니다.
   만약 발화자 이름이 명시되지 않았다면 문맥상 직책이나 '참석자A', '발언자' 등으로 합리적으로 지정하세요.
2. title: 명확하고 공식적인 회의 제목 (예: '2026 AI 데이터 플랫폼 개발 회의')
3. datetime: 회의 일시 (문맥에 언급된 시간, 없으면 현재 시점 기준 형식 예: '2026년 9월 10일 14:00 ~ 15:30')
4. place: 회의 장소 (언급 없으면 '온라인 회의' 또는 '회의실')
5. attendees: 참석자 명단 (쉼표 구분)
6. host: 회의 주최자 또는 주관자/팀장
7. agenda: 회의 주요 안건 (개조식 번호 1., 2. 형태)
8. schedule: 회의 결과에 따른 추후 일정 및 액션 아이템 (- 항목별 형태)

반드시 마크다운 코드블록(```json ... ```)을 포함하여 오직 유효한 JSON 형식으로만 응답하세요:
{
  "title": "...",
  "datetime": "...",
  "place": "...",
  "attendees": "...",
  "host": "...",
  "agenda": "...",
  "discussion": "...",
  "schedule": "..."
}
"""


@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>회의록 서비스 초기화 중...</h1>")


@app.post("/api/stt")
async def process_audio_stt(
    audio: UploadFile = File(...),
    provider: Optional[str] = Form("gemini"),
    api_key: Optional[str] = Form(None),
    model: Optional[str] = Form(None)
):
    """
    Google Gemini API 직접 호출 또는 OpenRouter API를 통해 오디오 파일을 한국어 텍스트로 변환 (STT)
    """
    audio_bytes = await audio.read()
    filename = audio.filename or "recording.webm"
    content_type = audio.content_type or "audio/webm"

    # Normalize mime type
    mime = content_type
    lower_fn = filename.lower()
    if lower_fn.endswith('.wav'):
        mime = 'audio/wav'
    elif lower_fn.endswith('.mp3'):
        mime = 'audio/mp3'
    elif lower_fn.endswith('.m4a'):
        mime = 'audio/m4a'
    elif lower_fn.endswith('.webm'):
        mime = 'audio/webm'
    elif lower_fn.endswith('.ogg'):
        mime = 'audio/ogg'

    # 1. Google Gemini Provider
    if provider == "gemini":
        active_key = api_key or os.getenv("GEMINI_API_KEY")
        if not active_key:
            raise HTTPException(status_code=400, detail="Gemini API Key가 입력되지 않았습니다. 우측 상단 [API 설정]에서 키를 입력해주세요.")

        gemini_model = model or "gemini-3.6-flash"
        # If user passed older deprecated model name, automatically upgrade
        if "gemini-2.5" in gemini_model or "gemini-1.5" in gemini_model:
            gemini_model = "gemini-3.6-flash"
        # Call Gemini REST API directly using generateContent
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={active_key}"

        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        prompt_instruction = "당신은 한국어 음성 인식 및 전사 전문가입니다. 제공된 오디오를 듣고 발화된 한국어 내용을 누락 없이 정확하게 텍스트로 전사하세요. 발화자가 구분될 경우 '(이름/직책) 발언내용' 형태로 작성하세요. 사족 없이 순수 텍스트만 출력하세요."

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt_instruction},
                        {
                            "inline_data": {
                                "mime_type": mime,
                                "data": base64_audio
                            }
                        }
                    ]
                }
            ]
        }

        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code != 200:
                err_text = res.text
                try:
                    err_text = res.json().get("error", {}).get("message", res.text)
                except Exception:
                    pass
                raise HTTPException(status_code=res.status_code, detail=f"Gemini API 오류: {err_text}")

            res_json = res.json()
            candidates = res_json.get("candidates", [])
            if not candidates or "content" not in candidates[0]:
                raise HTTPException(status_code=500, detail="Gemini에서 음성 인식 결과를 반환하지 못했습니다.")

            text_result = "".join([part.get("text", "") for part in candidates[0]["content"].get("parts", [])])
            return {"text": text_result.strip()}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini 음성 처리 중 오류: {str(e)}")

    # 2. OpenRouter Provider
    else:
        active_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not active_key:
            raise HTTPException(status_code=400, detail="OpenRouter API Key가 입력되지 않았습니다. 설정에서 API Key를 입력해주세요.")

        headers = {
            "Authorization": f"Bearer {active_key}",
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "Meeting Minutes Filler"
        }

        # Try whisper transcription first
        try:
            files = {"file": (filename, audio_bytes, content_type)}
            data = {"model": model or "openai/whisper-large-v3", "language": "ko"}
            res = requests.post("https://openrouter.ai/api/v1/audio/transcriptions", headers=headers, files=files, data=data, timeout=60)
            if res.status_code == 200:
                return {"text": res.json().get("text", "")}
        except Exception:
            pass

        # Fallback to multimodal chat completion
        base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
        stt_payload = {
            "model": "google/gemini-2.5-flash",
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 한국어 음성 인식 및 전사 전문 AI입니다. 제공된 오디오를 듣고 발화된 한국어 내용을 누락 없이 정확하게 텍스트로 옮겨 적으세요. 발화자가 여러 명일 경우 가급적 화자를 구분하여 적어주세요. 부가적인 설명 없이 순수 전사 텍스트만 출력하세요."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이 오디오의 내용을 정확하게 한국어 텍스트로 전사해 주세요."},
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": base64_audio,
                                "format": mime.split('/')[-1] if '/' in mime else "webm"
                            }
                        }
                    ]
                }
            ]
        }
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={
            "Authorization": f"Bearer {active_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "Meeting Minutes Filler"
        }, json=stt_payload, timeout=60)

        if res.status_code == 200:
            content = res.json()["choices"][0]["message"]["content"]
            return {"text": content.strip()}
        else:
            err_msg = res.text
            try:
                err_msg = res.json().get("error", {}).get("message", res.text)
            except Exception:
                pass
            raise HTTPException(status_code=res.status_code, detail=f"OpenRouter 음성 인식 실패: {err_msg}")


@app.post("/api/generate")
async def generate_meeting_minutes(req: GenerateRequest):
    """
    텍스트 또는 전사된 음성 텍스트를 바탕으로 회의록 양식 데이터(JSON) 생성
    논의 내용은 반드시 "(발화자) 내용" 형식으로 정제
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="회의 내용(텍스트)을 입력해주세요.")

    provider = req.provider or "gemini"

    # 1. Direct Gemini API
    if provider == "gemini":
        active_key = req.api_key or os.getenv("GEMINI_API_KEY")
        if not active_key:
            raise HTTPException(status_code=400, detail="Gemini API Key가 입력되지 않았습니다. 우측 상단 [API 설정]에서 키를 입력해주세요.")

        gemini_model = req.model or "gemini-3.6-flash"
        if "gemini-2.5" in gemini_model or "gemini-1.5" in gemini_model:
            gemini_model = "gemini-3.6-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={active_key}"

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "parts": [{"text": f"다음 회의 내용을 바탕으로 양식에 맞춘 회의록 JSON을 작성해주세요:\n\n{req.text}"}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json"
            }
        }

        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code != 200:
                err_msg = res.text
                try:
                    err_msg = res.json().get("error", {}).get("message", res.text)
                except Exception:
                    pass
                raise HTTPException(status_code=res.status_code, detail=f"Gemini API 오류: {err_msg}")

            res_json = res.json()
            candidates = res_json.get("candidates", [])
            if not candidates:
                raise HTTPException(status_code=500, detail="Gemini 응답 결과가 비어 있습니다.")

            raw_text = "".join([part.get("text", "") for part in candidates[0]["content"].get("parts", [])])
            return json.loads(raw_text)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Gemini 응답을 JSON으로 파싱하지 못했습니다.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini 회의록 생성 중 오류: {str(e)}")

    # 2. OpenRouter Provider
    else:
        active_key = req.api_key or os.getenv("OPENROUTER_API_KEY")
        if not active_key:
            raise HTTPException(status_code=400, detail="OpenRouter API Key가 입력되지 않았습니다. 설정에서 API Key를 입력해주세요.")

        model_name = req.model or "google/gemini-2.5-flash"
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"다음 회의 내용을 바탕으로 양식에 맞춘 회의록 JSON을 작성해주세요:\n\n{req.text}"}
            ],
            "temperature": 0.3
        }
        headers = {
            "Authorization": f"Bearer {active_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "Meeting Minutes Filler"
        }

        try:
            res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
            if res.status_code != 200:
                err_msg = res.text
                try:
                    err_msg = res.json().get("error", {}).get("message", res.text)
                except Exception:
                    pass
                raise HTTPException(status_code=res.status_code, detail=f"OpenRouter API 오류: {err_msg}")

            result = res.json()
            raw_content = result["choices"][0]["message"]["content"].strip()

            json_str = raw_content
            if "```json" in raw_content:
                json_str = raw_content.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_content:
                json_str = raw_content.split("```")[1].split("```")[0].strip()

            return json.loads(json_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="LLM 응답을 JSON으로 파싱하지 못했습니다.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"회의록 생성 중 오류: {str(e)}")


@app.post("/api/export-hwpx")
async def export_hwpx(data: MinutesData):
    """
    회의록 데이터를 HWPX 템플릿에 채워넣고 완성된 파일 스트림 반환
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=500, detail="서버에 '회의록 양식.hwpx' 파일이 존재하지 않습니다.")

    try:
        with open(TEMPLATE_PATH, "rb") as f:
            template_bytes = f.read()

        payload_dict = data.dict()
        filled_bytes = fill_meeting_minutes_hwpx(template_bytes, payload_dict)

        filename = f"{data.title or '회의록'}.hwpx"
        # Sanitize filename
        filename = filename.replace('\r', '').replace('\n', '').replace('"', '').strip()
        import urllib.parse
        encoded_filename = urllib.parse.quote(filename)
        fallback_filename = "meeting_minutes.hwpx"

        headers = {
            "Content-Disposition": f"attachment; filename=\"{fallback_filename}\"; filename*=UTF-8''{encoded_filename}",
            "Content-Type": "application/hwp+zip",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
        return Response(content=filled_bytes, media_type="application/hwp+zip", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HWPX 생성 실패: {str(e)}")


app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)

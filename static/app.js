// Application Logic for AI Meeting Minutes Filler (Gemini & OpenRouter Support)

let currentMode = 'text'; // 'text' | 'audio'
let currentProvider = 'gemini'; // 'gemini' | 'openrouter'
let mediaRecorder = null;
let audioChunks = [];
let recordedBlob = null;
let timerInterval = null;
let recordSeconds = 0;
let uploadedFile = null;

// DOM Elements
const tabTextBtn = document.getElementById('tabTextBtn');
const tabAudioBtn = document.getElementById('tabAudioBtn');
const panelText = document.getElementById('panelText');
const panelAudio = document.getElementById('panelAudio');
const activeInputModeBadge = document.getElementById('activeInputModeBadge');

const rawTextInput = document.getElementById('rawTextInput');
const btnSampleInsert = document.getElementById('btnSampleInsert');

const btnRecordToggle = document.getElementById('btnRecordToggle');
const recordBtnText = document.getElementById('recordBtnText');
const recTimer = document.getElementById('recTimer');
const recorderBox = document.getElementById('recorderBox');

const audioDropZone = document.getElementById('audioDropZone');
const audioFileInput = document.getElementById('audioFileInput');
const selectedAudioStatus = document.getElementById('selectedAudioStatus');
const audioFileNameText = document.getElementById('audioFileNameText');
const btnClearAudio = document.getElementById('btnClearAudio');
const sttResultBox = document.getElementById('sttResultBox');
const sttResultText = document.getElementById('sttResultText');

const btnGenerate = document.getElementById('btnGenerate');
const progressContainer = document.getElementById('progressContainer');
const progressMessage = document.getElementById('progressMessage');
const progressPercent = document.getElementById('progressPercent');

const emptyPreviewState = document.getElementById('emptyPreviewState');
const editorContainer = document.getElementById('editorContainer');
const btnDownloadHwpx = document.getElementById('btnDownloadHwpx');

// Hancom Toolbar & Paper Elements
const hwpPaper = document.getElementById('hwpPaper');
const docFontFamily = document.getElementById('docFontFamily');
const docFontSize = document.getElementById('docFontSize');
const docLineHeight = document.getElementById('docLineHeight');
const docParagraphGap = document.getElementById('docParagraphGap');
const docPagePadding = document.getElementById('docPagePadding');
const btnResetStyles = document.getElementById('btnResetStyles');

// Form fields
const fTitle = document.getElementById('fTitle');
const fDateTime = document.getElementById('fDateTime');
const fPlace = document.getElementById('fPlace');
const fAttendees = document.getElementById('fAttendees');
const fHost = document.getElementById('fHost');
const fAgenda = document.getElementById('fAgenda');
const fDiscussion = document.getElementById('fDiscussion');
const fSchedule = document.getElementById('fSchedule');

// Settings Modal Elements
const btnSettings = document.getElementById('btnSettings');
const settingsModal = document.getElementById('settingsModal');
const btnCloseSettings = document.getElementById('btnCloseSettings');
const btnCancelSettings = document.getElementById('btnCancelSettings');
const btnSaveSettings = document.getElementById('btnSaveSettings');

const btnSelectGemini = document.getElementById('btnSelectGemini');
const btnSelectOpenRouter = document.getElementById('btnSelectOpenRouter');
const geminiSettingsSection = document.getElementById('geminiSettingsSection');
const openrouterSettingsSection = document.getElementById('openrouterSettingsSection');

const geminiApiKey = document.getElementById('geminiApiKey');
const geminiModel = document.getElementById('geminiModel');
const openRouterApiKey = document.getElementById('openRouterApiKey');
const openRouterModel = document.getElementById('openRouterModel');
const openRouterSttModel = document.getElementById('openRouterSttModel');

const geminiEnvBadge = document.getElementById('geminiEnvBadge');
const openrouterEnvBadge = document.getElementById('openrouterEnvBadge');

let serverHasGeminiKey = false;
let serverHasOpenRouterKey = false;

const toast = document.getElementById('toast');

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  setupEventListeners();
  applyDocumentStyles();
});

function showToast(msg, type = 'info') {
  toast.textContent = msg;
  toast.className = `toast show ${type}`;
  setTimeout(() => {
    toast.className = 'toast';
  }, 3500);
}

async function loadSettings() {
  currentProvider = localStorage.getItem('ai_provider') || 'gemini';
  
  geminiApiKey.value = localStorage.getItem('gemini_api_key') || '';
  let savedGeminiModel = localStorage.getItem('gemini_model') || 'gemini-3.6-flash';
  if (savedGeminiModel.includes('2.5') || savedGeminiModel.includes('1.5')) {
    savedGeminiModel = 'gemini-3.6-flash';
    localStorage.setItem('gemini_model', savedGeminiModel);
  }
  geminiModel.value = savedGeminiModel;

  openRouterApiKey.value = localStorage.getItem('openrouter_api_key') || '';
  openRouterModel.value = localStorage.getItem('openrouter_model') || 'google/gemini-2.5-flash';
  openRouterSttModel.value = localStorage.getItem('openrouter_stt_model') || 'openai/whisper-large-v3';

  // Check server environment variables status
  try {
    const res = await fetch('/api/config');
    if (res.ok) {
      const cfg = await res.json();
      serverHasGeminiKey = !!cfg.has_gemini_key;
      serverHasOpenRouterKey = !!cfg.has_openrouter_key;

      if (serverHasGeminiKey && geminiEnvBadge) {
        geminiEnvBadge.style.display = 'inline-block';
      }
      if (serverHasOpenRouterKey && openrouterEnvBadge) {
        openrouterEnvBadge.style.display = 'inline-block';
      }

      if (!localStorage.getItem('ai_provider') && cfg.default_provider) {
        currentProvider = cfg.default_provider;
      }
    }
  } catch (err) {
    console.warn("서버 환경변수 상태 확인 실패:", err);
  }

  updateProviderUI();
}

function updateProviderUI() {
  if (currentProvider === 'gemini') {
    btnSelectGemini.classList.add('active');
    btnSelectOpenRouter.classList.remove('active');
    geminiSettingsSection.style.display = 'block';
    openrouterSettingsSection.style.display = 'none';
  } else {
    btnSelectOpenRouter.classList.add('active');
    btnSelectGemini.classList.remove('active');
    openrouterSettingsSection.style.display = 'block';
    geminiSettingsSection.style.display = 'none';
  }
}

function saveSettings() {
  localStorage.setItem('ai_provider', currentProvider);
  localStorage.setItem('gemini_api_key', geminiApiKey.value.trim());
  let gMdl = geminiModel.value.trim() || 'gemini-3.6-flash';
  if (gMdl.includes('2.5') || gMdl.includes('1.5')) {
    gMdl = 'gemini-3.6-flash';
  }
  localStorage.setItem('gemini_model', gMdl);

  localStorage.setItem('openrouter_api_key', openRouterApiKey.value.trim());
  localStorage.setItem('openrouter_model', openRouterModel.value.trim() || 'google/gemini-2.5-flash');
  localStorage.setItem('openrouter_stt_model', openRouterSttModel.value.trim() || 'openai/whisper-large-v3');

  settingsModal.classList.remove('show');
  showToast(`[${currentProvider === 'gemini' ? 'Google Gemini' : 'OpenRouter'}] 설정이 저장되었습니다.`, 'success');
}

function setupEventListeners() {
  // Tabs (Text vs Audio)
  tabTextBtn.addEventListener('click', () => switchTab('text'));
  tabAudioBtn.addEventListener('click', () => switchTab('audio'));

  // Settings modal
  btnSettings.addEventListener('click', () => settingsModal.classList.add('show'));
  btnCloseSettings.addEventListener('click', () => settingsModal.classList.remove('show'));
  btnCancelSettings.addEventListener('click', () => settingsModal.classList.remove('show'));
  btnSaveSettings.addEventListener('click', saveSettings);

  // Provider tabs in Settings Modal
  btnSelectGemini.addEventListener('click', () => {
    currentProvider = 'gemini';
    updateProviderUI();
  });
  btnSelectOpenRouter.addEventListener('click', () => {
    currentProvider = 'openrouter';
    updateProviderUI();
  });

  // Sample text insertion
  btnSampleInsert.addEventListener('click', () => {
    rawTextInput.value = `2026년 9월 10일 목요일 14:00 본사 대회의실에서 3분기 프로젝트 정기 회의를 진행함.
주최자: 김철수 팀장
참석자: 김철수 팀장, 이영희 선임, 박민수 책임, 최현우 연구원
주요 안건:
1. 양식 채우기 서비스 프로토타입 기능 검토
2. Gemini API 및 OpenRouter STT/LLM 연동 검증
3. 차기 배포 일정 수립

[회의 대화 내용]
(김철수) 오늘 회의에서는 개발 중인 회의록 양식 자동 작성 프로토타입 점검을 진행하겠습니다. 이 선임님, HWPX 생성 쪽 상황은 어떤가요?
(이영희) 네, HWPX 템플릿의 테이블 셀에 직접 문단을 주입하는 모듈이 완성되었습니다. 특히 논의 내용의 경우 각 발언자별로 '(발화자) 내용' 양식을 완벽히 지켜 출력하도록 구현되었습니다.
(박민수) Gemini API 키를 직접 입력받아 오디오 멀티모달 STT와 회의록 구조화를 즉시 실행할 수 있게 연동을 마쳤습니다.
(최현우) 음성 인식률 향상을 위해 회의 전문 용어 프롬프트를 보강해 두었습니다.
(김철수) 좋습니다. 다음 주 월요일까지 전사 테스트를 진행하고 목요일에 최종 보고를 준비해 주세요.

추후 일정:
- 9월 14일(월): 전사 1차 파일럿 테스트
- 9월 17일(목): 최종 결과 보고 및 배포`;
    showToast('예시 회의록 내용이 입력되었습니다.');
  });

  // Audio Drop Zone & File Upload
  audioDropZone.addEventListener('click', () => audioFileInput.click());
  audioFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleAudioFileSelected(e.target.files[0]);
    }
  });

  audioDropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    audioDropZone.classList.add('dragover');
  });
  audioDropZone.addEventListener('dragleave', () => audioDropZone.classList.remove('dragover'));
  audioDropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    audioDropZone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleAudioFileSelected(e.dataTransfer.files[0]);
    }
  });

  btnClearAudio.addEventListener('click', clearSelectedAudio);

  // Recording
  btnRecordToggle.addEventListener('click', toggleRecording);

  // Generate Minutes
  btnGenerate.addEventListener('click', handleGenerateMinutes);

  // Download HWPX
  btnDownloadHwpx.addEventListener('click', handleDownloadHwpx);

  // Hancom Styling Toolbar Listeners
  if (docFontFamily) docFontFamily.addEventListener('change', applyDocumentStyles);
  if (docFontSize) docFontSize.addEventListener('change', applyDocumentStyles);
  if (docLineHeight) docLineHeight.addEventListener('change', applyDocumentStyles);
  if (docParagraphGap) docParagraphGap.addEventListener('change', applyDocumentStyles);
  if (docPagePadding) docPagePadding.addEventListener('change', applyDocumentStyles);
  if (btnResetStyles) btnResetStyles.addEventListener('click', resetDocumentStyles);

  // Auto-expand inline textareas on user typing
  [fAgenda, fDiscussion, fSchedule].forEach(textarea => {
    if (textarea) {
      textarea.addEventListener('input', () => autoResizeTextarea(textarea));
    }
  });
}

function applyDocumentStyles() {
  if (!hwpPaper) return;

  const font = docFontFamily ? docFontFamily.value : "'Nanum Myeongjo', serif";
  const size = docFontSize ? docFontSize.value : "10pt";
  const lineH = docLineHeight ? docLineHeight.value : "1.6";
  const gap = docParagraphGap ? docParagraphGap.value : "6px";
  const padding = docPagePadding ? docPagePadding.value : "42px 48px";

  // Apply to paper container
  hwpPaper.style.fontFamily = font;
  hwpPaper.style.fontSize = size;
  hwpPaper.style.lineHeight = lineH;
  hwpPaper.style.padding = padding;

  // Apply font and size to inputs/textareas
  const inputs = hwpPaper.querySelectorAll('.hwp-inline-input, .hwp-inline-textarea');
  inputs.forEach(el => {
    el.style.fontFamily = font;
    el.style.fontSize = size;
    el.style.lineHeight = lineH;
  });

  // Apply paragraph gap
  const textareas = hwpPaper.querySelectorAll('.hwp-inline-textarea');
  textareas.forEach(el => {
    el.style.marginBottom = gap;
  });

  // Re-adjust textarea sizes
  textareas.forEach(autoResizeTextarea);
}

function resetDocumentStyles() {
  if (docFontFamily) docFontFamily.value = "'Nanum Myeongjo', serif";
  if (docFontSize) docFontSize.value = "10pt";
  if (docLineHeight) docLineHeight.value = "1.6";
  if (docParagraphGap) docParagraphGap.value = "6px";
  if (docPagePadding) docPagePadding.value = "42px 48px";
  applyDocumentStyles();
  showToast("문서 서식이 기본값으로 초기화되었습니다.", "info");
}

function autoResizeTextarea(el) {
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = (el.scrollHeight + 4) + 'px';
}

function switchTab(mode) {
  currentMode = mode;
  if (mode === 'text') {
    tabTextBtn.classList.add('active');
    tabAudioBtn.classList.remove('active');
    panelText.classList.add('active');
    panelAudio.classList.remove('active');
    activeInputModeBadge.textContent = '텍스트 모드';
  } else {
    tabAudioBtn.classList.add('active');
    tabTextBtn.classList.remove('active');
    panelAudio.classList.add('active');
    panelText.classList.remove('active');
    activeInputModeBadge.textContent = '음성 모드';
  }
}

function handleAudioFileSelected(file) {
  uploadedFile = file;
  recordedBlob = null;
  audioFileNameText.textContent = `${file.name} (${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
  selectedAudioStatus.style.display = 'flex';
  showToast(`파일 선택됨: ${file.name}`);
}

function clearSelectedAudio() {
  uploadedFile = null;
  recordedBlob = null;
  audioFileInput.value = '';
  selectedAudioStatus.style.display = 'none';
  sttResultBox.style.display = 'none';
  sttResultText.value = '';
}

// MediaRecorder Live Recording
async function toggleRecording() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop();
    return;
  }

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showToast('브라우저에서 마이크 녹음을 지원하지 않거나 권한이 없습니다.', 'danger');
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      stream.getTracks().forEach(track => track.stop());
      clearInterval(timerInterval);
      recTimer.classList.remove('recording');
      recorderBox.classList.remove('recording');
      recordBtnText.textContent = '실시간 녹음 시작';
      btnRecordToggle.className = 'btn btn-danger';

      recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
      uploadedFile = null;
      audioFileNameText.textContent = `실시간 녹음본 (${(recordedBlob.size / 1024).toFixed(1)} KB)`;
      selectedAudioStatus.style.display = 'flex';
      showToast('녹음이 완료되었습니다.');
    };

    mediaRecorder.start();
    recordSeconds = 0;
    updateTimerDisplay();
    timerInterval = setInterval(() => {
      recordSeconds++;
      updateTimerDisplay();
    }, 1000);

    recTimer.classList.add('recording');
    recorderBox.classList.add('recording');
    recordBtnText.textContent = '녹음 중지하기';
    btnRecordToggle.className = 'btn btn-secondary';
  } catch (err) {
    console.error('Microphone error:', err);
    showToast('마이크 접근 실패: ' + err.message, 'danger');
  }
}

function updateTimerDisplay() {
  const m = String(Math.floor(recordSeconds / 60)).padStart(2, '0');
  const s = String(recordSeconds % 60).padStart(2, '0');
  recTimer.textContent = `${m}:${s}`;
}

// Main Flow: Generate Minutes
async function handleGenerateMinutes() {
  const provider = localStorage.getItem('ai_provider') || 'gemini';
  const geminiKey = localStorage.getItem('gemini_api_key') || '';
  const geminiMdl = localStorage.getItem('gemini_model') || 'gemini-2.5-flash';

  const openRouterKey = localStorage.getItem('openrouter_api_key') || '';
  const openRouterMdl = localStorage.getItem('openrouter_model') || 'google/gemini-2.5-flash';
  const openRouterSttMdl = localStorage.getItem('openrouter_stt_model') || 'openai/whisper-large-v3';

  const apiKey = provider === 'gemini' ? geminiKey : openRouterKey;
  const activeModel = provider === 'gemini' ? geminiMdl : openRouterMdl;
  const activeSttModel = provider === 'gemini' ? geminiMdl : openRouterSttMdl;

  const hasKey = apiKey || (provider === 'gemini' ? serverHasGeminiKey : serverHasOpenRouterKey);

  if (!hasKey) {
    showToast(`${provider === 'gemini' ? 'Gemini' : 'OpenRouter'} API Key가 등록되지 않았습니다. 우측 상단 [API 설정]을 클릭해 등록하세요.`, 'danger');
    settingsModal.classList.add('show');
    return;
  }

  let inputText = '';

  if (currentMode === 'text') {
    inputText = rawTextInput.value.trim();
    if (!inputText) {
      showToast('회의 내용을 입력해주세요.', 'danger');
      rawTextInput.focus();
      return;
    }
  } else {
    // Audio mode
    const audioTarget = uploadedFile || recordedBlob;
    if (!audioTarget && !sttResultText.value.trim()) {
      showToast('녹음을 진행하거나 오디오 파일을 선택해주세요.', 'danger');
      return;
    }

    if (sttResultText.value.trim() && !audioTarget) {
      inputText = sttResultText.value.trim();
    } else {
      // Perform STT
      try {
        const providerName = provider === 'gemini' ? 'Google Gemini' : 'OpenRouter';
        showProgress(true, `1단계: ${providerName} STT 음성 인식 및 한국어 전사 중...`);
        btnGenerate.disabled = true;

        const formData = new FormData();
        const filename = uploadedFile ? uploadedFile.name : 'recording.webm';
        formData.append('audio', audioTarget, filename);
        formData.append('provider', provider);
        formData.append('api_key', apiKey);
        formData.append('model', activeSttModel);

        const sttRes = await fetch('/api/stt', {
          method: 'POST',
          body: formData
        });

        if (!sttRes.ok) {
          const errData = await sttRes.json().catch(() => ({}));
          throw new Error(errData.detail || '음성 인식(STT) 실패');
        }

        const sttJson = await sttRes.json();
        inputText = sttJson.text || '';
        sttResultText.value = inputText;
        sttResultBox.style.display = 'block';
        showToast('음성이 텍스트로 성공적으로 전사되었습니다.', 'success');
      } catch (err) {
        showProgress(false);
        btnGenerate.disabled = false;
        showToast(err.message, 'danger');
        return;
      }
    }
  }

  // Next: Generate Formatted Minutes with LLM
  try {
    const providerName = provider === 'gemini' ? 'Google Gemini' : 'OpenRouter';
    showProgress(true, `2단계: ${providerName} 모델이 회의록 양식 및 (발화자) 내용 형식으로 작성 중...`);
    btnGenerate.disabled = true;

    const genRes = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: inputText,
        provider: provider,
        api_key: apiKey,
        model: activeModel
      })
    });

    if (!genRes.ok) {
      const errData = await genRes.json().catch(() => ({}));
      throw new Error(errData.detail || '회의록 구조화 실패');
    }

    const data = await genRes.json();
    populateForm(data);

    showToast('회의록 작성이 완료되었습니다! 수정 후 HWPX를 다운로드하세요.', 'success');
  } catch (err) {
    showToast(err.message, 'danger');
  } finally {
    showProgress(false);
    btnGenerate.disabled = false;
  }
}

function showProgress(show, message = '') {
  if (show) {
    progressContainer.style.display = 'block';
    progressMessage.textContent = message;
  } else {
    progressContainer.style.display = 'none';
  }
}

function populateForm(data) {
  fTitle.value = data.title || '';
  fDateTime.value = data.datetime || '';
  fPlace.value = data.place || '';
  fAttendees.value = data.attendees || '';
  fHost.value = data.host || '';
  fAgenda.value = data.agenda || '';
  fDiscussion.value = data.discussion || '';
  fSchedule.value = data.schedule || '';

  emptyPreviewState.style.display = 'none';
  editorContainer.style.display = 'flex';
  btnDownloadHwpx.disabled = false;

  // Apply chosen typography & page styles and resize multiline textareas
  applyDocumentStyles();
  [fAgenda, fDiscussion, fSchedule].forEach(autoResizeTextarea);
}

// Download Filled HWPX
async function handleDownloadHwpx() {
  const data = {
    title: fTitle.value.trim(),
    datetime: fDateTime.value.trim(),
    place: fPlace.value.trim(),
    attendees: fAttendees.value.trim(),
    host: fHost.value.trim(),
    agenda: fAgenda.value.trim(),
    discussion: fDiscussion.value.trim(),
    schedule: fSchedule.value.trim()
  };

  btnDownloadHwpx.disabled = true;
  btnDownloadHwpx.textContent = 'HWPX 생성 중...';

  try {
    const res = await fetch('/api/export-hwpx', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'HWPX 파일 생성에 실패했습니다.');
    }

    const rawBlob = await res.blob();
    // Explicitly enforce HWPX mime type
    const hwpxBlob = new Blob([rawBlob], { type: 'application/hwp+zip' });
    const downloadUrl = window.URL.createObjectURL(hwpxBlob);
    
    let cleanTitle = (data.title || '회의록').replace(/[\r\n\t\\/:*?"<>|]/g, '_').trim();
    if (!cleanTitle) cleanTitle = '회의록';
    const downloadName = cleanTitle.endsWith('.hwpx') ? cleanTitle : cleanTitle + '.hwpx';

    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = downloadName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    setTimeout(() => {
      window.URL.revokeObjectURL(downloadUrl);
    }, 2000);

    showToast(`'${downloadName}' 다운로드가 완료되었습니다!`, 'success');
  } catch (err) {
    showToast(err.message, 'danger');
  } finally {
    btnDownloadHwpx.disabled = false;
    btnDownloadHwpx.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
      HWPX 다운로드
    `;
  }
}

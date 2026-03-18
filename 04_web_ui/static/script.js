import { initializeApp } from "https://www.gstatic.com/firebasejs/9.22.1/firebase-app.js";
import { getDatabase, ref, set, onValue } from "https://www.gstatic.com/firebasejs/9.22.1/firebase-database.js";

// 1. Firebase 설정
const firebaseConfig = {
    databaseURL: "https://cobot1-v2-default-rtdb.asia-southeast1.firebasedatabase.app"
};

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

/**
 * [메인 페이지] 공정 모드 선택 및 페이지 이동
 * @param {number} mode - 선택한 공정 번호 (1: Square, 2: Zigzag 등)
 * @param {string} pageName - 이동할 페이지 이름
 */
window.startProcess = (mode, pageName) => {
    const startRef = ref(db, '/command/start');
    set(startRef, mode)
        .then(() => {
            console.log("Firebase 명령 전송 성공: Mode", mode);
            window.location.href = `/process/${pageName}`; 
        })
        .catch((e) => console.error("전송 에러:", e));
};

/**
 * [서브 페이지] 실시간 로그 처리 로직
 * Firebase의 '/logs' 경로를 감시하여 최신 로그를 테이블에 업데이트합니다.
 */
const logBody = document.getElementById('log-body');

if (logBody) {
    const logRef = ref(db, '/logs');
    
    onValue(logRef, (snapshot) => {
        const data = snapshot.val();
        if (!data) return;

        // 테이블 초기화 후 최신순으로 다시 그림
        logBody.innerHTML = "";
        const keys = Object.keys(data).reverse();

        keys.forEach(key => {
            const logEntry = data[key];
            let displayMsg = "";
            let displayTime = "";

            if (typeof logEntry === 'object') {
                displayMsg = logEntry.message || JSON.stringify(logEntry);
                displayTime = logEntry.timestamp || "N/A"; 
            } else {
                displayMsg = logEntry;
                displayTime = new Date().toLocaleString();
            }

            const row = `<tr>
                <td style="color: #8899af; font-size: 0.8rem; white-space: nowrap; padding-right: 15px;">${displayTime}</td>
                <td style="color: #58a6ff; font-weight: 600;">${displayMsg}</td>
            </tr>`;
            logBody.insertAdjacentHTML('beforeend', row);
        });
    });
}

/**
 * [AI 요약 페이지] Gemini API 호출 및 마크다운 렌더링
 * 사용자가 버튼을 클릭하면 대기 애니메이션을 보여주고 AI 결과를 마크다운으로 파싱하여 출력합니다.
 */
window.requestAiSummary = async () => {
    const initialUi = document.getElementById('ai-initial-ui');
    const loadingUi = document.getElementById('ai-loading-ui');
    const resultUi = document.getElementById('ai-result-ui');

    // 1. UI 전환: 버튼 숨기고 로딩 스피너 표시
    initialUi.style.display = 'none';
    loadingUi.style.display = 'block';

    try {
        // 2. Flask 백엔드 API 호출
        const response = await fetch('/api/get_ai_summary');
        const data = await response.json();
        
        // 3. [핵심 수정] Marked.js를 이용한 마크다운 파싱 적용
        // 기존: resultUi.innerHTML = data.summary.replace(/\n/g, '<br>');
        resultUi.innerHTML = marked.parse(data.summary); 
        
        // 4. UI 최종 전환: 로딩 숨기고 결과 표시
        loadingUi.style.display = 'none';
        resultUi.style.display = 'block';
    } catch (error) {
        console.error("Gemini 연동 에러:", error);
        loadingUi.innerHTML = "<p style='color: #ff4d4d;'>Gemini 서버와 연결할 수 없습니다. 다시 시도해 주세요.</p>";
    }
};
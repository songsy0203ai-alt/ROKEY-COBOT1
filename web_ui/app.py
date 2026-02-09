import cv2
import time
import os
from datetime import datetime
from flask import Flask, render_template, Response, jsonify  # [수정] jsonify 추가
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# 1. Firebase 설정 (경로 및 URL 확인 필수)
if not firebase_admin._apps:
    cred_path = '/home/ssy/cobot_ws/src/web_monitor_v5/cobot1-v2_serviceAccountKey.json'
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://cobot1-v2-default-rtdb.asia-southeast1.firebasedatabase.app'
    })

# 2. Gemini API 설정
my_key = os.environ.get('GEMINI_API_KEY')
genai.configure(api_key=my_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. 카메라 스트리밍 로직 (try...finally 구조)
def gen_frames():  
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print(">>> [ERROR] 카메라 1번을 열 수 없습니다.")
        return
    try:
        while True:
            success, frame = cap.read()
            if not success: break 
            frame = cv2.resize(frame, (640, 480))
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    except GeneratorExit:
        print(">>> [INFO] 스트리밍 중단")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(">>> [SUCCESS] 카메라 자원 해제 완료")

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.html')

# --- [중요] 구체적인 주소(/summary)를 동적 주소(<mode_name>)보다 위에 배치합니다 ---

# 4. AI 공정 요약 서브페이지 라우트
@app.route('/process/summary')
def summary_view():
    # 오늘 날짜 기준 데이터(생산량, 특이사항)만 먼저 집계하여 렌더링
    today_str = datetime.now().strftime('%Y-%m-%d')
    all_logs = db.reference('/logs').get()
    
    today_logs = [v for k, v in all_logs.items() if today_str in v.get('timestamp', '')] if all_logs else []
    
    # "=== 제작 공정 완료 ===" 로그 개수 카운트
    prod_count = sum(1 for log in today_logs if "=== 부품 제작 완료 ===" in log.get('message', ''))
    
    issue_keywords = ["에러", "오류", "실패", "SAFE_STOP", "EMERGENCY"]
    special_notes = [log.get('message') for log in today_logs if any(k in log.get('message', '') for k in issue_keywords)]
    
    return render_template('summary.html', today=today_str, count=prod_count, notes=special_notes)

# 5. 실제로 Gemini API를 호출하는 비동기 API 엔드포인트
@app.route('/api/get_ai_summary')
def get_ai_summary():
    try:
        all_logs = db.reference('/logs').get()
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_logs = [v for k, v in all_logs.items() if today_str in v.get('timestamp', '')] if all_logs else []

        if not today_logs:
            return jsonify({"summary": "오늘 기록된 공정 로그가 없어 요약할 수 없습니다."})

        full_text = "\n".join([f"{l.get('timestamp')} - {l.get('message')}" for l in today_logs])
        # Gemini 2.5 flash(또는 1.5)를 이용한 요약 요청
        prompt = f"다음 로봇 공정 로그를 분석하여 한국어로 요약해줘: {full_text}"
        
        response = model.generate_content(prompt)
        return jsonify({"summary": response.text})
    except Exception as e:
        print(f">>> [AI ERROR] {e}")
        return jsonify({"summary": f"요약 중 오류 발생: {str(e)}"}), 500

# 6. 일반 공정 모니터링 주소 (가장 아래에 위치)
@app.route('/process/<mode_name>')
def process_view(mode_name):
    display_titles = {
        'square': 'LINEAR-ZIGZAG GLUE PROCESS',
        'zigzag': 'ARC-ZIGZAG GLUE PROCESS',
        'circle': 'CIRCLE GLUE PROCESS',
        'spiral': 'SPIRAL GLUE PROCESS'
    }
    title = display_titles.get(mode_name, 'ROBOTIC PROCESS')
    return render_template('process.html', process_title=title)
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
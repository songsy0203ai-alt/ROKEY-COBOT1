import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32, String  # String 추가
import firebase_admin
from firebase_admin import credentials, db
import datetime

class DbBridgeNode(Node):
    def __init__(self):
        super().__init__('db_bridge_node_v5')

        # 1. Firebase 초기화 (경로 수정: v5)
        cred_path = '/home/ssy/cobot_ws/src/web_monitor_v5/cobot1-v2_serviceAccountKey.json'
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://cobot1-v2-default-rtdb.asia-southeast1.firebasedatabase.app'
        })

        # 2. ROS 2 퍼블리셔 및 서브스크라이버 설정
        # 타입을 Bool에서 Int32로 변경 (모드 번호 1~4 전달을 위함)
        self.start_pub = self.create_publisher(Int32, 'start_signal', 10)
        self.log_sub = self.create_subscription(String, 'process_logs', self.log_callback, 10)

        # 3. Firebase 리스너 설정 (명령 감시)
        self.db_ref = db.reference('/command/start')
        self.db_ref.listen(self.on_command_change)

        self.get_logger().info(">>> [SUCCESS] DB Bridge Node v5 initialized.")

    def on_command_change(self, event):
        """Firebase의 /command/start 값이 변경될 때 호출되는 콜백"""
        # 데이터가 존재하고 0보다 큰 경우 (1, 2, 3, 4) 처리
        if event.data and event.data > 0:
            mode = int(event.data)
            self.get_logger().info(f"Firebase: 공정 시작 명령 감지 (모드: {mode})")
            
            # Int32 메시지에 모드 번호를 담아 전송
            msg = Int32()
            msg.data = mode
            self.start_pub.publish(msg)

            # 명령 중복 실행 방지를 위해 0으로 리셋
            self.db_ref.set(0)
            self.get_logger().info("Firebase: 명령 확인 후 0으로 리셋 완료")

    def log_callback(self, msg):
        """Control Node로부터 받은 로그를 Firebase에 기록"""
        log_data = msg.data
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_ref = db.reference('/logs')
        log_ref.push({
            'message': log_data,
            'timestamp': timestamp
        })
        self.get_logger().info(f"Firebase 로그 기록 완료: {log_data}")

def main(args=None):
    rclpy.init(args=args)
    node = DbBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
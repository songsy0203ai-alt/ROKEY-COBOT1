import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from cobot1_action.action import Assembly
from std_msgs.msg import Bool, String, Int32  # 토픽 통신을 위한 메시지 타입 추가

# control_node_v5.py 상단
import sys
import os
import inspect
from cobot1_action_v5.action import Assembly

# 1. 클래스가 정의된 실제 파일 위치 추적
try:
    # Assembly 클래스가 정의된 모듈의 경로를 찾습니다.
    target_path = inspect.getfile(Assembly)
    print(f"\n>>> [DEBUG] Assembly Class Location: {target_path}")
except Exception as e:
    print(f"\n>>> [DEBUG] Path find error: {e}")

# 2. 현재 파이썬이 참조하는 경로 목록 출력
print(">>> [DEBUG] Current Python Sys Paths:")
for p in sys.path:
    if 'cobot1' in p:
        print(f"    - {p}")
print("-" * 50)

class ControlNode(Node):
    def __init__(self):
        super().__init__('control_node')
        
        # 1. 액션 클라이언트 설정 (통합 노드 제어용)
        self._action_client = ActionClient(self, Assembly, '/dsr01/assembly_process')

        # 2. [추가] 토픽 구독 설정 (DB 브릿지 노드로부터 시작 신호 수신)
        self.subscription = self.create_subscription(
            Int32,
            'start_signal',
            self.start_signal_callback,
            10
        )

        # 3. [추가] 토픽 발행 설정 (DB 브릿지 노드로 로그 전송용)
        self.log_publisher = self.create_publisher(String, 'process_logs', 10)

        self.get_logger().info(">>> [SUCCESS] Control Node (Mediator) initialized.")

    def publish_to_db(self, log_text):
        """Firebase로 보낼 로그를 토픽으로 발행하는 헬퍼 함수"""
        msg = String()
        msg.data = log_text
        self.log_publisher.publish(msg)

    def start_signal_callback(self, msg):
        # Firebase에서 온 데이터가 True/False(bool)일 경우 0/1로, 
        # 문자열일 경우 숫자로 변환하여 안전하게 처리합니다.
        try:
            glue_mode = msg.data
            self.get_logger().info(f"[명령 수신] 공정 시작 신호 감지. 접착 모드 번호: {glue_mode}")
            self.send_goal(glue_mode)
        except Exception as e:
            self.get_logger().error(f"데이터 변환 에러: {e}")

    def send_goal(self, glue_mode):
        # 액션 클라이언트가 서버에 보낼 Goal 메시지 생성
        goal_msg = Assembly.Goal()
        
        # .action 파일의 'int32 glue_type'과 반드시 일치해야 합니다.
        goal_msg.glue_type = int(glue_mode)
        
        self.get_logger().info(f"액션 서버로 Goal 전송: {glue_mode}")
        self._action_client.wait_for_server()
        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg, 
            feedback_callback=self.feedback_callback
        )
        self._send_goal_future.add_done_callback(self.goal_response_callback)
        
    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        step_log = f"{feedback.completed_step}"
        self.get_logger().info(f"[피드백 수신] {step_log}")
        
        # [수정] 피드백을 받을 때마다 DB 브릿지로 토픽 발행
        self.publish_to_db(step_log)

    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('[Goal 거부] 서버가 요청을 거절했습니다.')
            self.publish_to_db("오류: 공정 시작 요청이 거부되었습니다.")
            return
        
        self.get_logger().info('[Goal 수락] 공정 수행 중...')
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        result = future.result().result
        status = "성공" if result.success else "실패"
        result_log = f"최종 공정 결과: {status}"
        
        self.get_logger().info(result_log)
        # [수정] 최종 결과를 DB 브릿지로 토픽 발행
        self.publish_to_db(result_log)

def main(args=None):
    rclpy.init(args=args)
    node = ControlNode()
    # [주의] 이제 main에서 바로 send_goal()을 호출하지 않습니다. 
    # 대신 rclpy.spin(node)를 통해 Firebase 신호(토픽)를 기다립니다.
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
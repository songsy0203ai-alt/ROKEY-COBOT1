# integration_node_v5.py

import rclpy
import DR_init
import time
from rclpy.action import ActionServer
from cobot1_action_v5.action import Assembly


# 로봇 설정 상수 (필요에 따라 수정)
ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"
ROBOT_TOOL = "Tool Weight"
ROBOT_TCP = "GripperDA_v1"

# 이동 속도 및 가속도 (필요에 따라 수정)
VELOCITY = 80
ACC = 80

# DR_init 설정
DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL


def initialize_robot():
    """로봇의 Tool과 TCP를 설정"""
    from DSR_ROBOT2 import set_tool, set_tcp,get_tool,get_tcp,ROBOT_MODE_MANUAL,ROBOT_MODE_AUTONOMOUS  # 필요한 기능만 임포트
    from DSR_ROBOT2 import get_robot_mode,set_robot_mode

    # Tool과 TCP 설정시 매뉴얼 모드로 변경해서 진행
    set_robot_mode(ROBOT_MODE_MANUAL)
    set_tool(ROBOT_TOOL)
    set_tcp(ROBOT_TCP)
    
    set_robot_mode(ROBOT_MODE_AUTONOMOUS)
    time.sleep(2)  # 설정 안정화를 위해 잠시 대기
    # 설정된 상수 출력
    print("#" * 50)
    print("Initializing robot with the following settings:")
    print(f"ROBOT_ID: {ROBOT_ID}")
    print(f"ROBOT_MODEL: {ROBOT_MODEL}")
    print(f"ROBOT_TCP: {get_tcp()}") 
    print(f"ROBOT_TOOL: {get_tool()}")
    print(f"ROBOT_MODE 0:수동, 1:자동 : {get_robot_mode()}")
    print(f"VELOCITY: {VELOCITY}")
    print(f"ACC: {ACC}")
    print("#" * 50)




# 초기 위치 및 목표 위치 설정
JReady = [0, 0, 90, 0, 90, 0]
'''
P1_BOT     = [388.27, -39.640, 97.63, 174.09, 180.00, 175.21]
P1_TOP     = [388.27, -39.640, 141.63, 174.09, 180.00, 175.21]
p1_c       = ([425.76, -77.14, 41.63, 143.10, 180.00, 143.32])
p1_c_top   = ([425.76, -77.64, 56, 143.10, 180.00, 143.32])
p1_c_place = ([425.76, -77.64, 17, 143.10, 180.00, 143.32])
P2_TOP     = [261.43, 235.65, 141.63, 41.60, 180.00, 41.52]
P2         = [261.43, 235.65, 86.57, 41.60, 180.00, 41.52]
p5_c = posx([700.59 , 18.84, 7.71, 171.29, 180.00, 170.92]) 
p5_c_top = posx([700.59 , 18.84, 56.71, 171.29, 180.00, 170.92])
'''

# 내부 함수 
def grasp():
    from DSR_ROBOT2 import set_digital_output, wait
    set_digital_output(1, 1)
    set_digital_output(2, 0)
    set_digital_output(3, 0)
    wait(0.5)

def release():
    from DSR_ROBOT2 import set_digital_output, wait
    set_digital_output(1, 0)
    set_digital_output(2, 1)
    set_digital_output(3, 0)
    wait(0.5)

def grasp_w():
    from DSR_ROBOT2 import set_digital_output, wait
    set_digital_output(1, 1)
    set_digital_output(2, 1)
    set_digital_output(3, 1)
    wait(0.5)

def release_w():
    from DSR_ROBOT2 import set_digital_output, wait
    set_digital_output(1, 0)
    set_digital_output(2, 1)
    set_digital_output(3, 1)
    wait(0.5)

# =========================
# Safety constants
# =========================
STATE_STANDBY = 1
STATE_SAFE_OFF = 3
STATE_SAFE_STOP = 5
STATE_EMERGENCY = 6

CONTROL_RESET_SAFE_STOP = 2
CONTROL_RESET_SAFE_OFF = 3


# =========================
# Low-level helpers
# =========================
def call_set_robot_control(control_value, goal_handle=None):
    from dsr_msgs2.srv import SetRobotControl
    from cobot1_action.action import Assembly # 피드백 메시지 타입을 위해 임포트

    node = DR_init.__dsr__node
    # ROBOT_ID가 전역 변수로 설정되어 있어야 합니다.
    srv_name = f'/{ROBOT_ID}/system/set_robot_control'
    cli = node.create_client(SetRobotControl, srv_name)

    if not cli.wait_for_service(timeout_sec=1.0):
        raise RuntimeError("set_robot_control service not available")

    req = SetRobotControl.Request()
    req.robot_control = control_value

    future = cli.call_async(req)

    start = time.time()
    while not future.done():
        # rclpy.spin_once를 통해 서비스 응답을 기다림
        rclpy.spin_once(node, timeout_sec=0.01)
        if time.time() - start > 5.0:
            raise RuntimeError("set_robot_control timeout")

    # 결과 확인
    result = future.result()
    if not result or not result.success:
        raise RuntimeError("set_robot_control rejected")

    # --- 서비스 성공 시 피드백 발행 ---
    if goal_handle is not None:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== 안전 복구 완료 ==="
        goal_handle.publish_feedback(feedback_msg)
        print(f">>> [ACTION FEEDBACK] {feedback_msg.completed_step}")

def pnp_low(goal_handle=None):
    from DSR_ROBOT2 import posx, set_digital_output, wait

    print("=== PNP LOW START ===")

    j_ready = [0, 0, 90, 0, 90, 0]

    p5_c = posx([700.59, 18.84, 7.71, 171.29, 180.00, 170.92])
    p5_c_top = posx([700.59, 18.84, 56.71, 171.29, 180.00, 170.92])

    p1_c_top = posx([425.76, -77.64, 56, 143.10, 180.00, 143.32])
    p1_c_place = posx([425.76, -77.64, 17, 143.10, 180.00, 143.32])

    movej_safe(j_ready, vel=VELOCITY, acc=ACC) # 래핑 함수 사용

    movel_safe(p5_c_top, vel=VELOCITY, acc=ACC) # 래핑 함수 사용
    set_digital_output(1, 0)
    set_digital_output(2, 1)
    set_digital_output(3, 1)
    wait(0.5)

    movel_safe(p5_c, vel=VELOCITY, acc=ACC) # 래핑 함수 사용
    set_digital_output(1, 1)
    set_digital_output(2, 1)
    set_digital_output(3, 1)
    wait(0.5)

    movel_safe(p5_c_top, vel=VELOCITY, acc=ACC) # 래핑 함수 사용
    movel_safe(p1_c_top, vel=VELOCITY, acc=ACC) # 래핑 함수 사용
    movel_safe(p1_c_place, vel=VELOCITY, acc=ACC) # 래핑 함수 사용

    set_digital_output(1, 0)
    set_digital_output(2, 1)
    set_digital_output(3, 1)
    wait(0.5)

    movej_safe(j_ready, vel=VELOCITY, acc=ACC) # 래핑 함수 사용

    print("=== PNP LOW DONE ===")

def wait_until_safe(goal_handle=None):
    from DSR_ROBOT2 import (
        get_robot_state,
        drl_script_stop,
        DR_QSTOP_STO,
        get_last_alarm,
    )

    while True:
        state = get_robot_state()

        if state == STATE_STANDBY:
            return

        if state == STATE_SAFE_STOP:
            print("!!! SAFE STOP detected → recovering !!!")
            drl_script_stop(DR_QSTOP_STO)
            time.sleep(2.0)
            call_set_robot_control(CONTROL_RESET_SAFE_STOP)
            time.sleep(2.0)
            continue

        if state == STATE_SAFE_OFF:
            print("!!! SAFE OFF detected → servo ON !!!")
            drl_script_stop(DR_QSTOP_STO)
            time.sleep(1.0)
            call_set_robot_control(CONTROL_RESET_SAFE_OFF)
            time.sleep(3.0)
            continue

        if state == STATE_EMERGENCY:
            alarm = get_last_alarm()
            raise RuntimeError(f"EMERGENCY STOP: {alarm}")

        time.sleep(0.2)


# =========================
# Motion wrapper
# =========================
def movej_safe(*args, **kwargs):
    from DSR_ROBOT2 import movej
    wait_until_safe()
    movej(*args, **kwargs)

def movel_safe(*args, **kwargs):
    from DSR_ROBOT2 import movel
    wait_until_safe()
    movel(*args, **kwargs)

def pick_glue(goal_handle=None):
    """Glue 작업 수행 (P3에서 집어서 P1으로 이동)"""
    from DSR_ROBOT2 import (movel, movej, wait, set_digital_output, 
                        DR_BASE, DR_MV_MOD_ABS, posx)

    # 1. 좌표 정의
    HOME_JOINT = [0, 0, 90, 0, 90, 0]
    
    # P3: Glue 공급처 (Pick)
    P3_TOP     = [249.61, -216.32, 141.63, 137.88, 180.00, 138.59]
    P3         = [249.61, -216.32, 58.8, 137.88, 180.00, 138.59] #z = edited +0.3
    
    # P1: 작업 위치 (Work Location)
    P1_TOP     = [388.27, -39.640, 141.63, 174.09, 180.00, 175.21]
    # P1_BOT     = [388.27, -39.640, 96.53, 174.09, 180.00, 175.21]

    # --- 실제 동작 시퀀스 ---
    try:
        # (1) 초기화: 그리퍼 열고 홈 위치로 이동
        print("Step 1: Moving to HOME position")
        release()
        movej(HOME_JOINT, vel=VELOCITY, acc=ACC)

        # (2) P3 지점에서 Glue 집기
        print("Step 2: Picking Glue at P3")
        movel(P3_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
        movel(P3,     vel=20, acc=40, ref=DR_BASE, mod=DR_MV_MOD_ABS) # 하강 시 감속
        grasp()
        movel(P3_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

        # (3) P1 지점으로 이동 (잡은 상태 유지)
        print("Step 3: Moving to P1 Work Location")
        movel(P1_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
        # movel(P1_BOT, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

        # 피드백 발행
        if goal_handle:
            feedback_msg = Assembly.Feedback()
            feedback_msg.completed_step = "=== pick_glue 완료 ==="
            goal_handle.publish_feedback(feedback_msg)
        
        print("Reached P1. Glue picking task complete.")

    except Exception as e:
        print(f"Error during task execution: {e}")

def glue_trj_square(goal_handle=None):
    from DSR_ROBOT2 import (movel, movej, wait, set_digital_output, 
                        DR_BASE, DR_MV_MOD_ABS, posx, DR_MV_MOD_REL)
    # w1 = posx([325, -114, 84, 162, 180, 163])
    pos1 = posx(7.5,-7.5,0,0,0,0)   # + -
    pos2 = posx(7.5,7.5,0,0,0,0)    # + +
    pos3 = posx(-7.5,-7.5,0,0,0,0)  # - -
    pos4 = posx(-7.5,7.5,0,0,0,0)   # - +
    
    w1 = posx(388.27,-39.64, 96.59, 175, 180, 175)
    P1_TOP     = [388.27, -39.640, 141.63, 174.09, 180.00, 175.21]
    # w1j = posj([-6.47, 7.77, 106.25, 0, 65.98,-6.58]) # right at the point without grabbing anything
    
    # Home
    # movej(JReady, v=VELOCITY, acc=ACC)
    
    # w1
    movel(w1, v=VELOCITY, acc=ACC,mod=DR_MV_MOD_ABS)
    
    # 반복 동작 수행
    while True:       
        # 이동 명령 실행
        for _ in range(5):
            movel(pos1, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL, radius=5)
            movel(pos2, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL, radius=5)
        for _ in range(5):
            movel(pos3, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL, radius=5)
            movel(pos1, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL, radius=5)
        for _ in range(5):
            movel(pos4, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL, radius=5)
            movel(pos3, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL, radius=5)
        for _ in range(5):
            movel(pos2, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL, radius=5)
            movel(pos4, vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL, radius=5)
        break
    movel(P1_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # 피드백 발행
    if goal_handle:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== glue_trj_square 완료 ==="
        goal_handle.publish_feedback(feedback_msg)
    
def place_glue(goal_handle=None):
    from DSR_ROBOT2 import (movel, movej, wait, set_digital_output, 
                        DR_BASE, DR_MV_MOD_ABS, posx, DR_MV_MOD_REL)
    P1_TOP     = [388.27, -39.640, 141.63, 174.09, 180, 175.21]
    P1_BOT     = [388.27, -39.640, 96.53, 174.09, 180, 175.21] 
    
    # P3: 물건을 놓을 지점 (Place)
    P3_TOP     = [249.61, -216.32, 141.63, 137.88, 180.00, 138.59]
    P3         = [249.61, -216.32, 58.56, 137.88, 180.00, 138.59]

    try:
        # (1) 초기 상태: 물건을 이미 잡고 있다고 가정
        print("Initial State: Maintaining grasp at start")
        grasp()

        # (2) P1 지점 경유 (BOT -> TOP)
        print("Step 1: Moving to P1 BOT")
        #movel(P1_BOT, vel=20, acc=40, ref=DR_BASE, mod=DR_MV_MOD_ABS)
        #wait(0.5)
        #movel(P1_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

        # (3) P3 지점으로 이동하여 물건 놓기
        print("Step 2: Moving to P3 TOP and Place")
        movel(P3_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
        movel(P3,     vel=20, acc=40, ref=DR_BASE, mod=DR_MV_MOD_ABS)
        
        print("Releasing object at P3...")
        release()
        
        movel(P3_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

        # (4) 홈으로 복귀
        print("Step 3: Task Complete. Returning HOME")
        movej(JReady, vel=60, acc=60)

        # 피드백 발행
        if goal_handle:
            feedback_msg = Assembly.Feedback()
            feedback_msg.completed_step = "=== place_glue 완료 ==="
            goal_handle.publish_feedback(feedback_msg)

    except Exception as e:
        print(f"Error during task execution: {e}")

def pnp_top(goal_handle=None):
    from DSR_ROBOT2 import (movel, movej, wait, set_digital_output, 
                        DR_BASE, DR_MV_MOD_ABS, posx, DR_MV_MOD_REL)
    print("상단 부품 Pick & Place 중...")

    # =======================================
    # 0. 초기 위치 및 목표 위치 정리
    # =======================================
    j_ready = [0, 0, 90, 0, 90, 0]
    # p5_c_low = posx([698.06 , 19.44, -6.98, 5.47, -179.33, 5.0])
    p5_c_low = posx([700.59, 18.84, -6.98, 5.47, -179.33, 5.0]) # 작업 구역에서 쌓여있는 것들 중 더 낮은 층에 있던 부품을 가져오는 과정 -> low라는 변수명 접미사를 붙임
    p5_c_low_top = posx([700.59, 18.84, 56.71, 5.47, -179.33, 5.0])

    # p1_c_place_low = posx([360.65, -150.84, 7.53, 132.70, -179.99, 128.53]) 
    # p1_c_low_top = posx([360.65, -150.84, 56.71, 132.70, -179.99, 128.53])

    #p1 = ([388.26, -39.64, 41.63, 143.10, 180.00, 143.32])
    # p1_c = ([425.76, -77.14, 41.63, 143.10, 180.00, 143.32])
    # p1_c_top = ([425.76, -77.64, 56, 143.10, 180.00, 143.32])
    # p1_c_place = ([425.76, -77.64, 17, 143.10, 180.00, 143.32])

    p1_c_place_low = ([425.76, -77.64, 30, 143.10, 180.00, 143.32])
    p1_c_low_top = ([425.76, -77.64, 70, 143.10, 180.00, 143.32])

        # ===============================
    # 2. 상단 부품을 가지러 가는 단계
    # ===============================
    # 재료 준비 구역으로 이동
    movel(p5_c_low_top, vel=VELOCITY, acc=ACC) 
    # 그리퍼 열기 (3번 OFF)
    release_w()
    # 재료에게 가까이 다가가기
    movel(p5_c_low, vel=VELOCITY, acc=ACC) 
    # 그리퍼 닫기 (3번 ON) 
    grasp_w()

    # ===============================
    # 3. 작업 구역으로 이동하는 단계
    # ===============================
    movel(p5_c_low_top, vel=VELOCITY, acc=ACC) 
    movel(p1_c_low_top, vel=VELOCITY, acc=ACC)
    movel(p1_c_place_low, vel=VELOCITY, acc=ACC)
    # 그리퍼 열기 (3번 OFF)
    release_w()

    movel(p1_c_low_top, vel=VELOCITY, acc=ACC)

    # 피드백 발행
    if goal_handle:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== pnp_top 완료 ==="
        goal_handle.publish_feedback(feedback_msg)

    

def glue_fix(goal_handle=None):
    from DSR_ROBOT2 import (movel, movej, wait, set_digital_output, 
                        DR_BASE, DR_MV_MOD_ABS, posx, DR_MV_MOD_REL, task_compliance_ctrl, set_stiffnessx, set_desired_force, get_tool_force, release_compliance_ctrl)
    
    # =======================================
    # 0. 초기 위치 및 목표 위치 정리
    # =======================================
    # p1_c_glue_top = posx([425.76, -77.14, 58, 143.10, 180.00, 143.32])
    # movel([0,0,50,0,0,0], vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL) 
    grasp()

    # ===============================
    # 3. 접착 고정
    # ===============================
    task_compliance_ctrl() # default 강성으로 시작
    set_stiffnessx([100, 100, 300, 100, 100, 100], time=10) 
    fd = [0, 0, -30, 0, 0, 0]
    fctrl_dir = [0, 0, 1, 0, 0, 0]
    set_desired_force(fd, dir=fctrl_dir, time=10, mod=1)

    # 2초 동안 0.2초 간격으로 현재 힘 상태 출력
    for _ in range(10):
        current_force = get_tool_force()
        # current_force[2] 가 Z축 방향의 힘입니다.
        print(f"현재 측정된 Z축 힘: {current_force[2]:.2f} N")
        wait(0.2)

    wait(5.0)
    release_compliance_ctrl()

    movel([0,0,50,0,0,0], vel=VELOCITY, acc=ACC, mod=DR_MV_MOD_REL) 

    # 피드백 발행
    if goal_handle:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== glue_fix 완료 ==="
        goal_handle.publish_feedback(feedback_msg)

def pick_seal(goal_handle=None):
    from DSR_ROBOT2 import (movel, movej, wait, set_digital_output, 
                        DR_BASE, DR_MV_MOD_ABS, posx, DR_MV_MOD_REL, task_compliance_ctrl, set_stiffnessx, set_desired_force, get_tool_force, release_compliance_ctrl)
    # P2: Seal 공급처 (Pick)
    P2_TOP     = [261.43, 235.65, 141.63, 41.60, 180.00, 41.52]
    P2         = [261.43, 235.65, 91.8, 41.60, 180.00, 41.52]
    
    # P1: 작업 위치 (Place)
    P1_BOT     = [388.27, -39.640, 97.63, 174.09, 180.00, 175.21] # z축으로 96~97 정도
    P1_TOP     = [388.27, -39.640, 141.63, 174.09, 180.00, 175.21]

    release()

    # (2) P2 지점에서 Seal 집기
    print("Step 2: Picking Seal at P2")
    movel(P2_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    movel(P2,     vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    grasp()
    movel(P2_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # (3) P1 지점으로 이동 (잡은 상태 유지)
    # print("Step 3: Moving to P1 for Seal Work")
    # movel(P1_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    # movel(P1_BOT, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # 피드백 발행
    if goal_handle:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== pick_seal 완료 ==="
        goal_handle.publish_feedback(feedback_msg)
    
    print("Task at P1 reached.")

def seal_trj_square(goal_handle=None):

    print("Performing task...")
    from DSR_ROBOT2 import posx,movej,movel,DR_BASE,DR_MV_MOD_REL, DR_MV_MOD_ABS, set_tcp, set_robot_mode, ROBOT_MODE_AUTONOMOUS, ROBOT_MODE_MANUAL, wait
    set_robot_mode(ROBOT_MODE_MANUAL)
    set_tcp("GripperDA_v1_seal")
    set_robot_mode(ROBOT_MODE_AUTONOMOUS)
    wait(2)

    
    # 초기 위치 및 목표 위치 설정
    JReady = [0, 0, 90, 0, 90, 0]
    pos1 = posx([375, -39.640, 51.970, 180, -180, 180])
    #pos2 = posx([384.520,-47.410,41.770,180,-148,180])
    pos2 = posx([382.520,-47.410,42.770,180,-147.5,180])

    # p1 marker startpoint
    ## ([381.260,-39.640,51.970,174.44, -150, 174.65]) # make sure angle matches 180
    
    # 반복 동작 수행 # z 12 x -4
        
    #이동 명령 실행
    print("movej")
    movej(JReady, vel=VELOCITY, acc=ACC)

    print("setup position")
    movel(pos1, vel=VELOCITY, acc=ACC)

    print("Going toward..")
    movel(pos2, vel=VELOCITY, acc=ACC, time=4)

    # print("movel")
    # movel(posx([0,-75,0,0,0,0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)
    print("moving..")
    movel(posx([0,-75,0,0,0,0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)

    print("changing_angle")
    #movel(posx([0,0,0,0,0,90]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)
    movel(posx([395.470, -118.470, 41.25, 90, 147.5, 0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_ABS) # +0.5y 
    #movel(posx([75,0,0,0,0,0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)
    movel(posx([470.470, -118.470, 41.25, 90, 147.5, 0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # print("movel")
    # movel(posx([75,0,0,0,0,0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)

    print("changing_angle")
    #movel(posx([0,0,0,0,0,90]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)
    movel(posx([468.140,-109.220,41.450,180,148,0]), vel=VELOCITY, acc=ACC, time=4 ,ref=DR_BASE, mod=DR_MV_MOD_ABS) # +4 z
    #movel(posx([0,75,0,0,0,0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)
    movel(posx([468.140,-34.220,41.450,180,148,0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # print("movel")
    # movel(posx([0,75,0,0,0,0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)

    print("changing_angle")
    #movel(posx([0,0,0,0,0,90]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)
    movel(posx([456.01,-34.880,41.720,90,-148,180]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_ABS) #+1 z
    #movel(posx([-75,0,0,0,0,0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)
    movel(posx([378.580,-35.550,41.720,90,-148,180]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # print("movel")
    # movel(posx([-75,0,0,0,0,0]), vel=VELOCITY, acc=ACC, time=4, ref=DR_BASE, mod=DR_MV_MOD_REL)

    print("hands off..")
    movel(posx([0,10,0,0,0,0]), vel=VELOCITY, acc=ACC, time=3, ref=DR_BASE, mod=DR_MV_MOD_REL)

    print("movej")
    movej(JReady, vel=VELOCITY, acc=ACC)

    # 피드백 발행
    if goal_handle:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== seal_trj_square 완료 ==="
        goal_handle.publish_feedback(feedback_msg)

    set_robot_mode(ROBOT_MODE_MANUAL)
    set_tcp("GripperDA_v1")
    set_robot_mode(ROBOT_MODE_AUTONOMOUS)

def place_seal(goal_handle=None):
    from DSR_ROBOT2 import (movel, movej, wait, set_digital_output, 
                        DR_BASE, DR_MV_MOD_ABS, posx, DR_MV_MOD_REL, task_compliance_ctrl, set_stiffnessx, set_desired_force, get_tool_force, release_compliance_ctrl)
    P2_TOP     = [261.43, 235.65, 141.63, 41.60, 180.00, 41.52]
    P2         = [261.43, 235.65, 86.57, 41.60, 180.00, 41.52]
    # (3) P2로 이동하여 물건 놓기
    print("Step 3: Moving to P2 to Place/Release")
    movel(P2_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    movel(P2,     vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    
    # 물건 놓기
    release()
    movel(P2_TOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # (4) 홈으로 복귀
    print("Step 4: Returning HOME")
    movej(JReady, vel=VELOCITY, acc=ACC)
    print("Place Seal Task Successfully Finished.")

    if goal_handle:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== place_seal 완료 ==="
        goal_handle.publish_feedback(feedback_msg)

def pnp_pass(goal_handle=None):
    from DSR_ROBOT2 import (movel, movej, wait, set_digital_output, 
                        DR_BASE, DR_MV_MOD_ABS, posx, DR_MV_MOD_REL, task_compliance_ctrl, set_stiffnessx, set_desired_force, get_tool_force, release_compliance_ctrl)
    release_w()
    # 1. 좌표 정의
    P1         = [388.27, -39.640, 42.63, 174.09, 180.00, 175.21]
    P1_TOP     = [388.27, -39.640, 141.63, 174.09, 180, 175.21]
    
    # 물체 중심까지의 상대 거리 (74.5mm 정사각형 기준)
    REL_CENTER = [37.25, -37.25, 0, 0, 0, 0] 
    
    P4_C       = [648.34, -194.70, 4, 138.36, 180.00, 138.04]
    P4_CTOP    = [648.34, -194.70, 100.00, 138.36, 180.00, 138.04]

    # (2) P1 기준점에서 상대 좌표로 중점 이동하여 집기
    print("Step 2: Moving to P1 and Calculating Center")
    movej(P1_TOP, vel=VELOCITY, acc=ACC) 
    
    # P1 모서리 기준점으로 하강
    movel(P1, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS) 
                                                                                                                                                                                                        
    # 상대 좌표 모드로 물체 중점 이동
    print(f"Moving to relative center: {REL_CENTER}")
    movel(REL_CENTER, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_REL)
    
    # 물체를 잡기 위해 아래로 추가 하강 (상대 좌표)
    print("Descending to grasp object...")
    movel([0, 0, -21.0, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_REL)
    grasp_w()
    
    # 집은 후 안전 높이로 수직 상승 (상대 좌표)
    movel([0, 0, 125, 0, 0, 0], vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_REL)

    # (3) P4 지점으로 이동하여 놓기
    print("Step 3: Moving to P4 TOP")
    movej(P4_CTOP, vel=VELOCITY, acc=ACC) 

    print("Step 4: Placing at P4")
    movel(P4_C, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    release_w()
    # movel(P4_CTOP, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # (4) 홈으로 최종 복귀
    print("Step 5: Task Complete. Returning HOME")
    movej(JReady, vel=VELOCITY, acc=ACC)

    if goal_handle:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== pnp_pass 완료 ==="
        goal_handle.publish_feedback(feedback_msg)

    if goal_handle:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== 부품 제작 완료 ==="
        goal_handle.publish_feedback(feedback_msg)
        print(f">>> [ACTION FEEDBACK] {feedback_msg.completed_step}")

def zigzag_onearc(goal_handle=None):
    """사각형 가장자리 원호(Arc Chain) 도포 작업 수행"""
    from DSR_ROBOT2 import (movel, movej, movec, wait, set_digital_output, 
                        posx, DR_BASE, DR_MV_MOD_ABS)

    # 1. 좌표 정의
    P1_BOT         = [388.27, -39.640, 96.53, 174.09, 180, 175.21]
    P1_TOP         = [388.27, -39.640, 141.63, 174.09, 180, 175.21]
    HOME_JOINT     = [0, 0, 90, 0, 90, 0]

    # 상수 정의
    SIDE = 75.0      # 정사각형 변 길이 (mm)
    PITCH = 15.0      # 원호 1개당 진행 길이 (mm)  (75/15 = 5개 생성)
    AMP = 10.0        # 원호 진폭 (좌우 튐 정도, mm) <-- 원 크기 결정값
    Y_MAX = 0.0      # Y축 안전 경계선

    # # 내부 함수: 잡기
    # def grasp():
    #     set_digital_output(1, 1)
    #     set_digital_output(2, 0)
    #     wait(0.5)


    # [내부 함수] 단방향 원호 체인 이동 로직
    def draw_arc_side(start_pose, axis, direction, bulge_sign):
        x0, y0, z0, rx0, ry0, rz0 = start_pose
        n = int(SIDE // PITCH)
        amp_val = abs(AMP) * bulge_sign
        cur_x, cur_y = x0, y0

        for _ in range(n):
            if axis == 'y': # Y축 진행, X축 튐
                mid_y = cur_y + direction * (PITCH / 2.0)
                end_y = cur_y + direction * PITCH
                mid_p = posx([x0 + amp_val, mid_y, z0, rx0, ry0, rz0])
                end_p = posx([x0, end_y, z0, rx0, ry0, rz0])

            else: # X축 진행, Y축 튐
                mid_x = cur_x + direction * (PITCH / 2.0)
                end_x = cur_x + direction * PITCH
                mid_y = y0 + amp_val
                if Y_MAX is not None: mid_y = min(mid_y, Y_MAX)
                mid_p = posx([mid_x, mid_y, z0, rx0, ry0, rz0])
                end_p = posx([end_x, y0, z0, rx0, ry0, rz0])
            
            movec(mid_p, end_p, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS,radius=5)
            cur_x, cur_y = (end_x, y0) if axis == 'x' else (x0, end_y)
        return [cur_x, cur_y, z0, rx0, ry0, rz0]

    # --- 실제 동작 시퀀스 ---

    # (1) 초기 파지 및 홈 이동
    print("Step 1: Grasp & Home")
    grasp()
    movej(HOME_JOINT, vel=VELOCITY, acc=ACC)

    # (2) 시작점 P1 진입
    print("Step 2: Approach P1")
    movel(posx(P1_TOP), vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    movel(posx(P1_BOT), vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # (3) 4변 원호 도포 (안쪽 방향으로만 볼록하게 진행)
    print("Step 3: Edge Coating Start")
    curr_pose = P1_BOT[:]
    curr_pose = draw_arc_side(curr_pose, 'y', -1, +1) # Edge 1: Y- 방향 (X+ 내부 볼록)
    curr_pose = draw_arc_side(curr_pose, 'x', +1, +1) # Edge 2: X+ 방향 (Y+ 내부 볼록)
    curr_pose = draw_arc_side(curr_pose, 'y', +1, -1) # Edge 3: Y+ 방향 (X- 내부 볼록)
    curr_pose = draw_arc_side(curr_pose, 'x', -1, -1) # Edge 4: X- 방향 (Y- 내부 볼록)

    # (4) 종료 및 홈 복귀
    print("Step 4: Finish & Return")
    movel(posx(P1_TOP), vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    movej(HOME_JOINT, vel=VELOCITY, acc=ACC)

    if goal_handle:
        feedback_msg = Assembly.Feedback()
        feedback_msg.completed_step = "=== zigzag_onearc 완료 ==="
        goal_handle.publish_feedback(feedback_msg)

def circle_stack(goal_handle=None):
    """정사각형 4변을 돌며 원을 찍고 이동하는(Stamp) 작업"""
    from DSR_ROBOT2 import (movel, movej, movec, wait, set_digital_output,
                            posx, DR_BASE, DR_MV_MOD_ABS)

    # 기준 좌표
    P1_BOT = [388.27, -39.640, 96.58, 174.09, 180.0, 175.21]
    P1_TOP = [388.27, -39.640, 141.63, 174.09, 180.0, 175.21]
    HOME_JOINT = [0, 0, 90, 0, 90, 0]

    
    VELOCITY, ACC = 80, 60
    VEL_SLOW, ACC_SLOW = 40, 40

    SIDE = 75.0      # 정사각형 블록 한 변 (75mm)
    R = 6.0          # 원의 반지름
    GAP = 2.0        # 원과 원 사이의 여유 간격
    LIFT = 15.0      # 이동 시 안전하게 들어올릴 높이

    # 원이 밖으로 나가지 않게 중심이 이동할 수 있는 유효 길이 계산
    SIDE_EFF = SIDE - (2.0 * R)  # 양쪽 끝 반지름만큼 제외
    STEP = (2.0 * R) + GAP       # 원 중심 간의 이동 거리



    # 초기화 및 홈 이동
    def grasp():
        set_digital_output(1, 1)
        set_digital_output(2, 0)
        set_digital_output(3, 0)
        wait(0.5)


    def draw_single_circle(center):
        """중심점(center)을 기준으로 원 하나를 완성"""
        cx, cy, cz, rx, ry, rz = center
        
        # 원의 시작점 (중심에서 +R 지점)
        start_p = posx([cx + R, cy, cz, rx, ry, rz])
        # 공중 대기점 (이동 시 높이)
        wait_p  = posx([cx + R, cy, cz + LIFT, rx, ry, rz])

        # 1. 공중 이동 후 하강
        movel(wait_p, vel=VELOCITY, acc=ACC)
        movel(start_p, vel=VEL_SLOW, acc=ACC_SLOW)

        # 2. 360도 원 그리기 (반원 2개 조합)
        mid1 = posx([cx, cy + R, cz, rx, ry, rz])
        end1 = posx([cx - R, cy, cz, rx, ry, rz])
        mid2 = posx([cx, cy - R, cz, rx, ry, rz])
        end2 = posx([cx + R, cy, cz, rx, ry, rz])

        movec(mid1, end1, vel=VEL_SLOW, acc=ACC_SLOW, ref=DR_BASE, mod=DR_MV_MOD_ABS)
        movec(mid2, end2, vel=VEL_SLOW, acc=ACC_SLOW, ref=DR_BASE, mod=DR_MV_MOD_ABS)

        # 3. 그린 후 즉시 상승 (Stamp 동작의 핵심)
        movel(wait_p, vel=VELOCITY, acc=ACC)

    def process_edge(start_c, axis, direct):
        """한 변을 따라 여러 개의 원을 도장 찍듯 그림"""
        x0, y0, z0, rx0, ry0, rz0 = start_c
        n = int(SIDE_EFF // STEP) + 1  # 이 변에 들어갈 원의 개수

        curr_c = [x0, y0, z0, rx0, ry0, rz0]
        for i in range(n):
            if axis == 'y':
                curr_c[1] = y0 + direct * (i * STEP)
            else:
                curr_c[0] = x0 + direct * (i * STEP)
            
            draw_single_circle(curr_c)
        
        return curr_c # 마지막 원의 중심 반환


    # =========================
    # 실제 시퀀스
    # =========================
    print("Step 1: Grasp & Home")
    grasp()
    movej(HOME_JOINT, vel=VELOCITY, acc=ACC)

    # P1 시작점으로 이동 (R만큼 안쪽에서 시작하여 밖으로 안 나가게 함)
    # y- 방향 진행을 위해 초기 중심 설정
    init_center = [P1_BOT[0] + R, P1_BOT[1] - R, P1_BOT[2], P1_BOT[3], P1_BOT[4], P1_BOT[5]]

    print("Step: Drawing Circles on 4 Edges...")
    # Edge 1 (y-) -> Edge 2 (x+) -> Edge 3 (y+) -> Edge 4 (x-) 순차 진행
    p = process_edge(init_center, 'y', -1)
    p = process_edge(p,           'x', 1)
    p = process_edge(p,           'y', 1)
    p = process_edge(p,           'x', -1)

    # 복귀
    movel(posx(P1_TOP), vel=VELOCITY, acc=ACC)
    movej(HOME_JOINT, vel=VELOCITY, acc=ACC)

def spiral_wave_stacks(goal_handle=None):
    """
    4변 모두에 "골뱅이(@) 스파이럴"을 여러 개 그림.
    진행 순서(사용자 요청):
    Edge1: y- 방향 이동하면서 찍기
    Edge2: x+ 방향 이동하면서 찍기
    Edge3: y+ 방향 이동하면서 찍기
    Edge4: x- 방향 이동하면서 찍기

    특징:
    - 스파이럴 1개는 movec로 원호들을 이어서 "연속"으로 그림
    - 스파이럴 끝나면 옆으로 STEP만큼 이동해서 다음 스파이럴
    - Z로 들어올림(LIFT) 없음 (원하면 옵션으로 넣을 수 있음)
    """
    from DSR_ROBOT2 import (
        movel, movej, movec, wait, set_digital_output,
        posx, DR_BASE, DR_MV_MOD_ABS
    )

    import math


    VELOCITY, ACC = 100, 100

    # =========================
    # 블록/패턴 파라미터
    # =========================
    SIDE = 75.0            # 블록 한 변(mm)

    # "골뱅이(@)" 스파이럴 파라미터
    R_START = 8.0          # 스파이럴 시작 반지름(mm)  (크게할수록 @가 큼)
    R_END   = 2.0          # 스파이럴 끝 반지름(mm)
    TURNS   = 2.0          # 몇 바퀴 감을지 (2.0이면 두바퀴)
    SEG_PER_TURN = 8       # 한 바퀴를 몇 조각(원호)으로 나눌지 (8~16 권장)
                        # movec는 1개가 "원호 1개"라서, 조각이 많을수록 더 부드러움

    # 스파이럴(원)들 간 간격
    GAP = 3.0              # 스파이럴 중심 간격 여유(mm)

    # 바깥 경계 밖으로 나가지 않게 "안쪽으로 들어올" 여유
    FUDGE = 1.0
    MARGIN = R_START + FUDGE

    # 변을 따라 스파이럴 "중심"이 이동 가능한 유효 길이
    SIDE_EFF = SIDE - 2.0 * MARGIN

    # 스파이럴 중심 이동 STEP (원 하나 크기 + 갭)
    STEP = 2.0 * R_START + GAP

    # =========================
    # 기준 좌표(사용자 제공)
    # =========================
    P1_BOT     = [388.27, -39.640, 96.57, 174.09, 180.0, 175.21]
    P1_TOP     = [388.27, -39.640, 141.63, 174.09, 180.0, 175.21]
    HOME_JOINT = [0, 0, 90, 0, 90, 0]

    if SIDE_EFF <= 0:
        raise ValueError(
            f"SIDE_EFF <= 0 입니다. R_START={R_START}가 너무 큼. "
            f"R_START 또는 FUDGE를 줄이거나 SIDE를 키워야 합니다."
        )

    def grasp():
        set_digital_output(1, 1)
        set_digital_output(2, 0)
        set_digital_output(3, 0)
        wait(0.5)

    # -------------------------
    # 스파이럴(@) 1개 그리기
    # - 중심(cx,cy)에서 반지름을 줄여가며 원호(quarter-ish)를 연속 movec로 그림
    # -------------------------
    def draw_spiral_at_center(center_pose):
        """
        center_pose = [cx, cy, cz, rx, ry, rz]
        """
        cx, cy, cz, rx, ry, rz = center_pose

        total_seg = int(TURNS * SEG_PER_TURN)
        if total_seg < 4:
            total_seg = 4

        # 시작 각도(0에서 시작하면 (cx+R, cy)에서 시작)
        theta0 = 0.0
        dtheta = (2.0 * math.pi * TURNS) / total_seg

        # 시작점으로 접근
        r0 = R_START
        sx = cx + r0 * math.cos(theta0)
        sy = cy + r0 * math.sin(theta0)
        movel(posx([sx, sy, cz, rx, ry, rz]), vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

        # 원호들을 연속으로 이어서 스파이럴 생성
        for i in range(total_seg):
            # i -> i+1 로 갈 때 반지름을 선형으로 줄임
            t1 = i / total_seg
            t2 = (i + 1) / total_seg

            r1 = R_START + (R_END - R_START) * t1
            r2 = R_START + (R_END - R_START) * t2

            th1 = theta0 + dtheta * i
            th2 = theta0 + dtheta * (i + 1)
            thm = (th1 + th2) * 0.5

            # 중간점(원호 via), 끝점(end)
            mx = cx + ((r1 + r2) * 0.5) * math.cos(thm)
            my = cy + ((r1 + r2) * 0.5) * math.sin(thm)

            ex = cx + r2 * math.cos(th2)
            ey = cy + r2 * math.sin(th2)

            mid_p = posx([mx, my, cz, rx, ry, rz])
            end_p = posx([ex, ey, cz, rx, ry, rz])

            movec(mid_p, end_p, vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS, radius=10)

        # 스파이럴 끝점 반환(다음 이동 시작점으로 사용)
        return [ex, ey, cz, rx, ry, rz]

    # -------------------------
    # 한 변을 따라 "스파이럴 중심"을 STEP씩 이동하며 반복
    # -------------------------
    def process_edge_spirals(start_center, axis, direction):
        """
        start_center: [cx, cy, cz, rx, ry, rz]  (첫 스파이럴 중심)
        axis: 'x' or 'y'    (변 진행 축)
        direction: +1/-1    (진행 방향)
        """
        cx0, cy0, cz0, rx0, ry0, rz0 = start_center

        n = int(SIDE_EFF // STEP) + 1  # 이 변에 들어갈 스파이럴 개수
        print(f"[EDGE] axis={axis}, dir={direction}, spirals={n}")

        cur_end = None
        for i in range(n):
            if axis == 'x':
                cx = cx0 + direction * (i * STEP)
                cy = cy0
            else:
                cx = cx0
                cy = cy0 + direction * (i * STEP)

            # 스파이럴을 그림(@)
            cur_end = draw_spiral_at_center([cx, cy, cz0, rx0, ry0, rz0])

            # 스파이럴 끝난 상태에서 "그대로" 다음 중심으로 평면 이동(리프트 없음)
            # 다음 중심의 "시작점"으로 자연스럽게 연결되도록, 다음 스파이럴은 내부에서 다시 접근(movel)함.
            # (연결이 너무 거칠면 여기서 movel을 SLOW로 한번 더 써도 됨)

        # 마지막 중심 반환 (다음 변 시작점 만들 때 사용)
        if axis == 'x':
            return [cx0 + direction * ((n - 1) * STEP), cy0, cz0, rx0, ry0, rz0]
        else:
            return [cx0, cy0 + direction * ((n - 1) * STEP), cz0, rx0, ry0, rz0]

    # =========================
    # 실행 시퀀스
    # =========================
    grasp()
    movej(HOME_JOINT, vel=VELOCITY, acc=ACC)

    movel(posx(P1_TOP), vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    movel(posx(P1_BOT), vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)

    # 시작 스파이럴 "중심"을 블록 안쪽(MARGIN)으로 잡음
    xC, yC, zC, rxC, ryC, rzC = P1_BOT
    start_center = [xC + MARGIN, yC - MARGIN, zC, rxC, ryC, rzC]

    print("== Draw spiral(@) stamps on 4 edges ==")
    p = process_edge_spirals(start_center, axis='y', direction=-1)  # Edge1: y-
    p = process_edge_spirals(p,            axis='x', direction=+1)  # Edge2: x+
    p = process_edge_spirals(p,            axis='y', direction=+1)  # Edge3: y+
    p = process_edge_spirals(p,            axis='x', direction=-1)  # Edge4: x-

    movel(posx(P1_TOP), vel=VELOCITY, acc=ACC, ref=DR_BASE, mod=DR_MV_MOD_ABS)
    movej(HOME_JOINT, vel=VELOCITY, acc=ACC)



# pnp_low()
# pick_glue()
# glue_trj_square()
# zigzag_onearc()
# place_glue()
# pnp_top()
# glue_fix()
# pick_seal()
# seal_trj_square()
# place_seal()
# pnp_pass()



async def execute_callback(goal_handle):
    print(">>> [액션 서버] 조립 공정 시작 명령 수신")

    # 1. 클라이언트가 보낸 접착 모드 번호 확인 (1~4)
    glue_mode = goal_handle.request.glue_type
    print(f">>> 선택된 접착 모드 번호: {glue_mode}")

    # --- 초기 피드백 발행 ---
    if goal_handle:
        feedback_msg = Assembly.Feedback()
        # f 접두사 추가
        feedback_msg.completed_step = f"선택된 접착 모드 번호: {glue_mode}"
        goal_handle.publish_feedback(feedback_msg)
        print(f">>> [ACTION FEEDBACK] {feedback_msg.completed_step}")

    try:
        # 2. 번호에 따른 함수 매핑
        glue_functions = {
            1: glue_trj_square,
            2: zigzag_onearc,
            3: circle_stack,
            4: spiral_wave_stacks
        }

        # 3. 공정 시퀀스 실행
        pnp_low(goal_handle)
        pick_glue(goal_handle)

        # 선택된 모드의 접착 함수 실행
        selected_func = glue_functions.get(glue_mode, glue_trj_square)
        print(f">>> 실행 중인 모드: {selected_func.__name__}")
        selected_func(goal_handle)

        place_glue(goal_handle)
        pnp_top(goal_handle)
        glue_fix(goal_handle)
        pick_seal(goal_handle)
        seal_trj_square(goal_handle)
        place_seal(goal_handle)
        pnp_pass(goal_handle)

        # --- 최종 성공 피드백 발행 (succeed 호출 전 수행) ---
        if goal_handle:
            feedback_msg = Assembly.Feedback()
            feedback_msg.completed_step = "=== 제작 공정 완료 ==="
            goal_handle.publish_feedback(feedback_msg)
            print(f">>> [ACTION FEEDBACK] {feedback_msg.completed_step}")

        # 4. 액션 성공 처리 및 결과 반환
        goal_handle.succeed()
        result = Assembly.Result()
        result.success = True
        return result

    except Exception as e:
        print(f">>> [에러 발생] 공정 중단: {e}")
        # 에러 발생 시 액션 중단 처리
        goal_handle.abort()
        result = Assembly.Result()
        result.success = False
        return result

    except Exception as e:
        print(f">>> [에러 발생] 공정 중단: {e}")
        goal_handle.abort()
        result = Assembly.Result()
        result.success = False
        return result

def main(args=None):
    rclpy.init(args=args)
    node = rclpy.create_node("move_basic", namespace=ROBOT_ID)

    # DR_init 설정
    DR_init.__dsr__node = node

    # --- 액션 서버 추가 지점 ---
    action_server = ActionServer(
        node,
        Assembly,
        'assembly_process',
        execute_callback
    )
    # -----------------------

    print(">>> 액션 서버가 준비되었습니다. 명령을 기다립니다.")

    try:
        # 초기화 1회 수행
        initialize_robot()
        
        # rclpy.spin을 통해 액션 명령을 계속 대기함
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(BASE_DIR)
sys.path.append(BASE_DIR)
sys.path.append(BASE_DIR+"/ModelTrain/")
import cv2
import time
from dataclasses import dataclass
import numpy as np
import tyro
import threading
import queue
from backend.dobot_xtrainer.dobot_control.env import RobotEnv
from backend.dobot_xtrainer.dobot_control.robots.robot_node import ZMQClientRobot
from backend.dobot_xtrainer.dobot_control.cameras.realsense_camera import RealSenseCamera

from backend.dobot_xtrainer.scripts.manipulate_utils import load_ini_data_camera

from ModelTrain.module.model_module import Imitate_Model

@dataclass
class Args:
    robot_port: int = 6001
    hostname: str = "127.0.0.1"
    show_img: bool = False

image_left,image_right,image_top,thread_run=None,None,None,None
lock = threading.Lock()

def run_thread_cam(rs_cam, which_cam):
    global image_left, image_right, image_top, thread_run
    if which_cam==1:
        while thread_run:
            image_left, _ = rs_cam.read()
            image_left = image_left[:, :, ::-1]
    elif which_cam==2:
        while thread_run:
            image_right, _ = rs_cam.read()
            image_right = image_right[:, :, ::-1]
    elif which_cam==0:
        while thread_run:
            image_top_src, _ = rs_cam.read()
            image_top_src = image_top_src[150:420,220:480, ::-1]
            image_top = cv2.resize(image_top_src,(640,480))

    else:
        print("Camera index error! ")


def main(args):

   # camera init
    global image_left, image_right, image_top, thread_run
    thread_run=True
    camera_dict = load_ini_data_camera()

    rs1 = RealSenseCamera(flip=True, device_id=camera_dict["top"])
    rs2 = RealSenseCamera(flip=False, device_id=camera_dict["left"])
    rs3 = RealSenseCamera(flip=True, device_id=camera_dict["right"])
    thread_cam_top = threading.Thread(target=run_thread_cam, args=(rs1, 0))
    thread_cam_left = threading.Thread(target=run_thread_cam, args=(rs2, 1))
    thread_cam_right = threading.Thread(target=run_thread_cam, args=(rs3, 2))

    thread_cam_left.start()
    thread_cam_right.start()
    thread_cam_top.start()
    show_canvas = np.zeros((480, 640 * 3, 3), dtype=np.uint8)
    time.sleep(2)
    print("camera thread init success...")

   # robot init
    robot_client = ZMQClientRobot(port=args.robot_port, host=args.hostname)
    env = RobotEnv(robot_client)
    env.set_do_status([1, 0])
    env.set_do_status([2, 0])
    env.set_do_status([3, 0])
    print("robot init success...")

    # go to the safe position
   # 将机械臂移动到安全位置
   # 定义左右机械臂的安全位置关节角度（单位：度），并使用deg2rad函数转换为弧度制
    reset_joints_left = np.deg2rad([-90, 30, -110, 20, 90, 90, 0])
    reset_joints_right = np.deg2rad([90, -30, 110, -20, -90, -90, 0])
    reset_joints = np.concatenate([reset_joints_left, reset_joints_right])
    curr_joints = env.get_obs()["joint_positions"]
    max_delta = (np.abs(curr_joints - reset_joints)).max()
    steps = min(int(max_delta / 0.001), 150)
    for jnt in np.linspace(curr_joints, reset_joints, steps):
        env.step(jnt,np.array([1,1]))
    time.sleep(1)

    # go to the initial photo position
    reset_joints_left = np.deg2rad([-90, 0, -90, 0, 90, 90, 57])  # 用夹爪
    reset_joints_right = np.deg2rad([90, 0, 90, 0, -90, -90, 57])
    reset_joints = np.concatenate([reset_joints_left, reset_joints_right])
    curr_joints = env.get_obs()["joint_positions"]
    max_delta = (np.abs(curr_joints - reset_joints)).max()
    steps = min(int(max_delta / 0.001), 150)
    for jnt in np.linspace(curr_joints, reset_joints, steps):
        env.step(jnt,np.array([1,1]))

    # Initialize the model
    model_name = 'policy_last.ckpt'
    model = Imitate_Model(ckpt_dir='./ckpt/ckpt_move_cube_new', ckpt_name=model_name)

    model.loadModel()
    print("model init success...")

    # Initialize the parameters
    episode_len = 9000  # The total number of steps to complete the task. Note that it must be less than or equal to parameter 'episode_len' of the corresponding task in file 'ModelTrain.constants'
    t=0
    last_time = 0
    observation = {'qpos': [], 'images': {'left_wrist': [], 'right_wrist': [], 'top': []}}
    obs = env.get_obs()
    obs["joint_positions"][6] = 1.0  # Initial position of the gripper
    obs["joint_positions"][13] = 1.0
    observation['qpos'] = obs["joint_positions"]  # Initial value of the joint
    last_action = observation['qpos'].copy()

    first = True

    print("The robot begins to perform tasks autonomously...")
    while t < episode_len:
        # Obtain the current images
        time0 = time.time()
        # with lock:
        observation['images']['left_wrist'] = image_left
        observation['images']['right_wrist'] = image_right
        observation['images']['top'] = image_top
        if args.show_img:
            imgs = np.hstack((observation['images']['top'],observation['images']['left_wrist'],observation['images']['right_wrist']))
            cv2.imshow("imgs",imgs)
            cv2.waitKey(1)
        time1 = time.time()
        print("read images time(ms)：",(time1-time0)*1000)

        # Model inference,output joint value (radian)
        action = model.predict(observation,t)
        # print("infer_action:",action)
        if action[6]>1:
            action[6]=1
        elif action[6]<0:
            action[6] = 0
        if action[13]>1:
            action[13]=1
        elif action[13]<0:
            action[13]=0
        time2 = time.time()
        print("Model inference time(ms)：", (time2 - time1) * 1000)

        # ×××××××××××××××××××××××××××××Security protection×××××××××××××××××××××××××××××××××××××××××××
        # 机器人安全保护模块 - 多层安全检测机制
        # 该模块实现机械臂运动的全方位安全监控，包含运动增量、关节限位和工作空间边界三类保护[1,2](@ref)

        # [Note]: Modify the protection parameters in this section carefully !
        # 注意：此部分的保护参数需要根据具体机械臂型号和任务需求谨慎调整[3](@ref)

        # 初始化保护错误标志位，用于汇总各类安全检测结果
        protect_err = False

        # 计算当前动作指令与上一时刻动作指令的差值（关节角度变化量）
        delta = action - last_action
        # 打印关节角度增量，用于实时监控和调试
        print("Joint increment：", delta)

        # 关节运动增量安全检查：检测单步运动幅度是否过大[2](@ref)
        # 阈值0.17弧度约等于10度，防止关节运动速度过快造成冲击或失控[1](@ref)
        if max(delta[0:6]) > 0.17 or max(delta[7:13]) > 0.17:  # 增量大于10度
            # 输出警告信息，提示用户干预
            print("Note! If the joint increment is larger than 10 degrees!!!")
            print(
                "Do you want to continue running? Press the 'Y' key to continue, otherwise press the other button to stop the program!")

            # 创建临时图像窗口用于捕获键盘输入（使cv2.waitKey(0)生效）
            temp_img = np.zeros(shape=(640, 480))
            cv2.imshow("waitKey", temp_img)  # 显示临时窗口以接收键盘输入
            # 等待用户按键决策（0表示无限期等待）
            key = cv2.waitKey(0)

            # 检查用户按键选择
            if key == ord('y') or key == ord('Y'):  # 如果用户按下'Y'键确认继续
                # 关闭临时窗口
                cv2.destroyWindow("waitKey")
                # 采用平滑方式缓慢移动到目标位置，避免突变[2](@ref)
                # 计算最大关节角度偏差
                max_delta = (np.abs(last_action - action)).max()
                # 计算需要的步数，限制最大步数不超过100步
                steps = min(int(max_delta / 0.001), 100)
                # 生成从当前位置到目标位置的平滑轨迹点
                for jnt in np.linspace(last_action, action, steps):
                    # 逐步执行轨迹点，np.array([1,1])表示双机械臂使能
                    env.step(jnt, np.array([1, 1]))
                # 重置首次运行标志（此处first变量可能在其他地方定义）
                first = False
            else:  # 用户选择停止程序
                # 设置保护错误标志为True
                protect_err = True
                # 关闭所有OpenCV窗口
                cv2.destroyAllWindows()

        # 关节角度安全限位检查[3](@ref)
        # 左机械臂关节角度限制（单位已转换为弧度）：J3 ∈ (-2.6, 0) 对应 approximately (-149°, 0°)，J4 > -0.6 对应 approximately > -34.4°
        # 右机械臂关节角度限制（单位已转换为弧度）：J3 ∈ (0, 2.6) 对应 approximately (0°, 149°)，J4 < 0.6 对应 approximately < 34.4°
        # 这些限制保护机械臂不会运动到可能导致机械碰撞或损坏的关节角度[5](@ref)
        if not ((action[2] > -2.6 and action[2] < 0 and action[3] > -0.6) and \
                (action[9] < 2.6 and action[9] > 0 and action[10] < 0.6)):
            # 输出关节超限警告信息
            print("[Warn]: The J3 or J4 joints of the robotic arm are out of the safe position! ")
            # 打印当前危险动作指令用于调试
            print(action)
            # 设置保护错误标志
            protect_err = True

        # 工作空间边界安全检查[3](@ref)
        # 左机械臂末端执行器（夹爪尖端）安全工作空间：
        #   X轴范围：-410mm 到 300mm（左右方向）
        #   Y轴范围：-700mm 到 -210mm（前后方向）
        #   Z轴最低安全高度：42mm（垂直方向）
        # 右机械臂末端执行器（夹爪尖端）安全工作空间：
        #   X轴范围：-250mm 到 410mm（左右方向）
        #   Y轴范围：-700mm 到 -210mm（前后方向）
        #   Z轴最低安全高度：42mm（垂直方向）
        # 这些边界防止机械臂与工作环境发生碰撞[1](@ref)
        # 记录开始时间用于性能监控
        t1 = time.time()
        # 获取机械臂末端执行器的当前位姿（XYZ坐标和旋转矢量）
        pos = env.get_XYZrxryrz_state()
        # 检查左右机械臂是否都在安全工作空间内
        if not ((pos[0] > -410 and pos[0] < 300 and pos[1] > -700 and pos[1] < -210 and pos[2] > 42) and \
                (pos[6] < 410 and pos[6] > -250 and pos[7] > -700 and pos[7] < -210 and pos[8] > 42)):
            # 输出工作空间越界警告信息
            print("[Warn]: The robot arm XYZ is out of the safe position! ")
            # 打印当前位置信息用于调试
            print(pos)
            # 设置保护错误标志
            protect_err = True
        # 记录结束时间并计算位姿查询耗时
        t2 = time.time()
        # 打印获取位姿所需时间（毫秒），用于性能分析和优化
        print("get pos time(ms):", (t2 - t1) * 1000)

        # 安全错误处理：如果任何保护检测失败，执行紧急停止流程[1](@ref)
        if protect_err:
            # 关闭黄灯（数字输出3设为0） - 表示警告状态清除
            env.set_do_status([3, 0])
            # 关闭绿灯（数字输出2设为0） - 表示正常运行状态清除
            env.set_do_status([2, 0])
            # 开启红灯（数字输出1设为1） - 表示紧急停止状态激活
            env.set_do_status([1, 1])
            # 暂停1秒，确保状态稳定且操作员有足够时间反应
            time.sleep(1)
            # 安全退出程序，防止进一步的危险操作
            exit()
        # ×××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××

        if first:
            max_delta = (np.abs(last_action - action)).max()
            steps = min(int(max_delta / 0.001), 100)
            for jnt in np.linspace(last_action, action, steps):
                env.step(jnt,np.array([1,1]))
            first = False

        last_action = action.copy()

        # Control robot movement
        time3 = time.time()
        obs = env.step(action,np.array([1,1]))
        time4 = time.time()

        # Obtain the current joint value of the robots (including the gripper)
        obs["joint_positions"][6] = action[6]   # In order to decrease acquisition time, the last action of the gripper is taken as its current observation
        obs["joint_positions"][13] = action[13]
        observation['qpos'] = obs["joint_positions"]

        print("Read joint value time(ms)：", (time4 - time3) * 1000)
        t +=1

        # Reset t when the robot returns to its initial position to achieve infinite loop execution of tasks
        threshold = np.deg2rad(10)
        if t>1200 and np.all(np.abs((action- np.deg2rad([-90, 0, -90, 0, 90, 90, 57,90, 0, 90, 0, -90, -90, 57])))<threshold):
            print("Reset t=0")
            t=0

        print("The total time(ms):", (time4 - time0) * 1000)


    thread_run = False
    print("Task accomplished")

    # Return to the starting position
    # ...


if __name__ == "__main__":
    main(tyro.cli(Args))


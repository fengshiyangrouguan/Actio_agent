import pickle
import glob
import numpy as np
import time
import os
import sys


ROBOT_IP = "192.168.5.1"  # 或 "192.168.5.2"，根据要控制的机械臂

# 1. 引入您的机器人控制类
from backend.dobot_xtrainer.dobot_control.robots.dobot import DobotRobot  # 根据您的实际项目结构调整导入路径

def load_trajectory(observation_dir):
    """
    从observation目录加载所有.pkl文件，并按键值排序。
    返回一个按时间顺序排列的关节角度列表。
    """
    # 获取所有.pkl文件路径
    pkl_files = glob.glob(os.path.join(observation_dir, "*.pkl"))
    # 关键：按文件名中的数字部分排序，而不是字符串排序（避免 10.pkl 排在 2.pkl 前面）
    pkl_files.sort(key=lambda x: int(os.path.basename(x).split('.')[0]))
    
    joint_positions_list = []
    
    for file_path in pkl_files:
        with open(file_path, 'rb') as f:
            obs = pickle.load(f)  # 加载保存的数据
            
        # 从obs中提取关节角度。根据您的数据结构，关节位置在 obs["joint_positions"]
        if 'joint_positions' in obs:
            joint_positions = obs['joint_positions']
        else:
            # 尝试其他可能的键名
            print(f"警告：文件 {file_path} 中未找到预期的 'joint_positions' 键。可用的键有：{list(obs.keys())}")
            continue
            
        joint_positions_list.append(joint_positions)
    
    print(f"成功加载 {len(joint_positions_list)} 个轨迹点。")
    return joint_positions_list

def replay_trajectory(target_id):
    """
    主复现函数
    :param robot_ip: 机械臂IP地址，如 "192.168.5.1"
    :param observation_dir: 保存的observation文件夹路径，例如 "/media/ubuntu22/.../collect_data/20240507161455/observation/"
    :param replay_speed_factor: 回放速度因子，1.0为原速，>1.0为加快，<1.0为减慢
    """

    # 1. 初始化机械臂
    replay_speed_factor=0.6
    robot_ip = "192.168.5.1"
    print("正在连接机械臂...")
    robot = DobotRobot(robot_ip=robot_ip, no_gripper=False)  # 假设使用夹爪
    '''
    执行这行robot = DobotRobot代码后，你将获得一个名为 robot的、完全初始化好的机器人控制对象。此时机械臂已经：

    处于上电使能状态。
    全局速度、加速度已按代码设置。
    工具坐标系已配置。
    夹爪已连接并完成自检。
    错误监控线程已在后台运行。
    可以通过 robot对象的各种方法（如 get_joint_state, command_joint_state, moveJ等）对机械臂进行控制和状态查询。

    '''
    print("机械臂连接成功。")

    obs = robot.get_joint_state()
    print(obs)
    obs[6] = 1.0
    last_action = obs.copy()
    
    first = True

    # 2. 加载轨迹数据
    print(f"正在从 {observation_dir} 加载轨迹数据...")
    trajectory_1 = load_trajectory(observation_dir)
    print(trajectory_1[7:14])
    trajectory = [i[7:14] for i in trajectory_1]
    if not trajectory:
        print("错误：未加载到任何轨迹数据！")
        return
    
    # 3. 【可选，但建议】移动到轨迹起始点
    # 使用 moveJ 可以确保机械臂以安全、规划好的路径移动到起始位置，避免跳跃。
    print("正在移动至轨迹起始点...")

    action =trajectory[0]

    if first:
            max_delta = (np.abs(last_action - action)).max()
            steps = min(int(max_delta / 0.001), 100)
            for jnt in np.linspace(last_action, action, steps):
                # jnt是一个 NumPy 数组，其形状和维度与 last_action和 action完全相同，即一个14维的数组，包含了左右机械臂（各6个关节+1个夹爪）在当前插值步下的目标关节角度。
                robot.command_joint_state(jnt)
            first = False
    # start_joints = trajectory[0]
    # start_joints =  start_joints[6:13]
    # robot.moveJ(start_joints)  # moveJ 是阻塞的，会等待运动完成
    # time.sleep(0.5)  # 短暂稳定
    
    # 4. 开始复现
    print("开始复现轨迹...")
    # 计算一个近似的时间间隔。原始数据保存频率由 run_control.py 的主循环控制。
    # 从 run_control.py 的循环末尾可以看到 'total_time = toc-tic' 并打印，这个时间通常在几十毫秒。
    # 您可以设置一个固定的、与录制时相近的间隔，例如0.04秒（~25Hz）。
    base_interval = 0.04  # 单位：秒。请根据您实际采集时的循环时间调整。
    actual_interval = base_interval / replay_speed_factor
    
    for i, joint_pos in enumerate(trajectory):
        # 使用 command_joint_state 发送目标状态。其内部调用 ServoJ，适合连续、实时的轨迹跟随。
        success = robot.command_joint_state(np.array(joint_pos))
        
        if not success:
            print(f"警告：第 {i} 个点发送失败。")
        
        # 等待下一个周期
        time.sleep(actual_interval)
        
        # 打印进度
        if i % 50 == 0:
            print(f"已复现 {i}/{len(trajectory)} 个点...")
    
    print("轨迹复现完成！")
    robot.r_inter.StopDrag()  # 确保退出任何可能的状态

if __name__ == "__main__":
    # 使用示例

    
    replay_trajectory(robot_ip=ROBOT_IP, observation_dir=OBSERVATION_DIR, replay_speed_factor=0.6)
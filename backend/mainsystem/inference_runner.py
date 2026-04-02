from __future__ import annotations

import sys
import os
import time
import threading
import asyncio
import cv2
import numpy as np
from typing import Optional, Dict, Any
from threading import Event, Lock

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append(BASE_DIR + "/ModelTrain/")

from backend.dobot_xtrainer.dobot_control.env import RobotEnv
from backend.dobot_xtrainer.dobot_control.robots.robot_node import ZMQClientRobot
from backend.dobot_xtrainer.dobot_control.cameras.realsense_camera import RealSenseCamera
from backend.dobot_xtrainer.scripts.manipulate_utils import load_ini_data_camera
from backend.dobot_xtrainer.ModelTrain.module.model_module import Imitate_Model



class InferenceRunner:
    """
    推理运行器 - 封装所有推理逻辑
    
    所有配置硬编码，对外只提供简单的异步接口  
    """
    
    # 硬编码配置
    ROBOT_PORT = 6001
    ROBOT_HOST = "127.0.0.1"
    EPISODE_LEN = 9000
    MODEL_DIR = os.path.join(BASE_DIR, "data", "model")
    
    def __init__(self):
        """初始化推理运行器"""
        self.stop_event = Event()
        self.running = Event()
        self.running.set()
        
        # 图像缓存（4个摄像头：top, left, right, bottom）
        self.images = {"top": None, "left": None, "right": None, "bottom": None}
        self.image_lock = Lock()
        self.image_ready = Event() # 等待图像就绪
        self._ready_count = 0
        self._ready_lock = Lock()
        
        self.camera_threads = []
        self.model = None
        self.env = None
        self.current_model_name = None
        
    def _run_camera_thread(self, rs_cam, which_cam: int):
        """
        摄像头采集线程
        
        Args:
            which_cam: 0=顶部, 1=左腕, 2=右腕, 3=底部
        """
        while self.running.is_set():
            try:
                # 读取图像
                img, _ = rs_cam.read()
                if img is None:
                    time.sleep(0.001)
                    continue
                
                # 根据摄像头类型处理
                if which_cam == 0:  # 顶部摄像头
                    # 裁剪并调整大小
                    img = img[150:420, 220:480, ::-1]
                    img = cv2.resize(img, (640, 480))
                    with self.image_lock:
                        self.images["top"] = img
                        
                elif which_cam == 1:  # 左腕摄像头
                    img = img[:, :, ::-1]
                    with self.image_lock:
                        self.images["left"] = img
                        
                elif which_cam == 2:  # 右腕摄像头
                    img = img[:, :, ::-1]
                    with self.image_lock:
                        self.images["right"] = img
                
                elif which_cam == 3:  # 底部摄像头
                    img = img[:, :, ::-1]
                    with self.image_lock:
                        self.images["bottom"] = img
                
                # 标记图像已就绪（仅第一次）（需要4个摄像头都就绪）
                with self._ready_lock:
                    if self._ready_count < 4:
                        self._ready_count += 1
                        if self._ready_count == 4:
                            self.image_ready.set()
                            
            except Exception as e:
                print(f"Camera {which_cam} error: {e}")
                time.sleep(0.1)
                continue
    
    def _get_images(self) -> Dict[str, np.ndarray | None]:
        """安全获取当前图像"""
        with self.image_lock:
            return {
                'top': self.images["top"].copy() if self.images["top"] is not None else None,
                'left': self.images["left"].copy() if self.images["left"] is not None else None,
                'right': self.images["right"].copy() if self.images["right"] is not None else None,
                'bottom': self.images["bottom"].copy() if self.images["bottom"] is not None else None
            }
    
    def _move_to_joint_target(self, target_joints: np.ndarray, 
                               steps_scale: float = 0.001, 
                               max_steps: int = 150) -> bool:
        """平滑移动到目标关节位置"""
        curr_joints = self.env.get_obs()["joint_positions"]
        max_delta = float(np.abs(curr_joints - target_joints).max())
        steps = max(1, min(int(max_delta / steps_scale), max_steps))
        
        for joints in np.linspace(curr_joints, target_joints, steps):
            if self.stop_event.is_set():
                return False
            self.env.step(joints, np.array([1, 1]))
        return True
    
    def _move_to_start_pose(self) -> bool:
        """移动到起始位置（安全位置 → 拍照位置）"""
        # 安全位置
        safe_left = np.deg2rad([-90, 30, -110, 20, 90, 90, 0])
        safe_right = np.deg2rad([90, -30, 110, -20, -90, -90, 0])
        if not self._move_to_joint_target(np.concatenate([safe_left, safe_right])):
            return False
        time.sleep(1)
        
        # 拍照位置
        photo_left = np.deg2rad([-90, 0, -90, 0, 90, 90, 57])
        photo_right = np.deg2rad([90, 0, 90, 0, -90, -90, 57])
        if not self._move_to_joint_target(np.concatenate([photo_left, photo_right])):
            return False
        return True
    
    def _check_action_safety(self, action: np.ndarray, last_action: np.ndarray) -> tuple[bool, str]:
        """
        检查动作安全性

        Returns:
            (是否安全, 错误信息)
        """
        # 检查关节增量是否过大
        delta = action - last_action
        if max(delta[0:6]) > 0.17 or max(delta[7:13]) > 0.17:
            return False, "关节增量超过10度"
        
        # 检查关节3和关节4是否在安全位置
        joints_safe = (
            (action[2] > -2.6 and action[2] < 0 and action[3] > -0.6)
            and (action[9] < 2.6 and action[9] > 0 and action[10] < 0.6)
        )
        if not joints_safe:
            return False, "J3或J4关节超出安全位置"
        
        # 检查工作空间
        try:
            pos = self.env.get_XYZrxryrz_state()
            workspace_safe = (
                (pos[0] > -410 and pos[0] < 300 and pos[1] > -700 and pos[1] < -210 and pos[2] > 42)
                and (pos[6] < 410 and pos[6] > -250 and pos[7] > -700 and pos[7] < -210 and pos[8] > 42)
            )
            if not workspace_safe:
                return False, "机械臂超出工作空间"
        except Exception:
            return False, "获取机械臂位姿失败"
        
        return True, ""
    
    def _run_sync(self, target_id: str) -> Dict[str, Any]:
        """
        同步运行推理（内部方法）
        
        Args:
            target_id: 目标商品ID，模型路径为 data/model/{target_id}/
            
        Returns:
            执行结果字典
        """
        # 构建模型目录路径：data/model/{target_id}/
        model_dir = os.path.join(self.MODEL_DIR, target_id)
        model_name = f"{target_id}.ckpt"
        model_path = os.path.join(model_dir, model_name)
        
        try:
            # ========== 1. 检查模型文件是否存在 ==========
            if not os.path.exists(model_path):
                return {
                    "success": False, 
                    "status": "model_not_found", 
                    "message": f"模型文件不存在: {model_path}",
                    "target_id": target_id
                }
            print(f"模型路径: {model_path}")
            self.current_model_name = model_name
            
            # ========== 2. 初始化摄像头（4个：顶、左、右、底） ==========
            print("正在初始化摄像头...")
            camera_dict = load_ini_data_camera()
            rs_top = RealSenseCamera(flip=True, device_id=camera_dict["top"])
            rs_left = RealSenseCamera(flip=False, device_id=camera_dict["left"])
            rs_right = RealSenseCamera(flip=True, device_id=camera_dict["right"])
            rs_bottom = RealSenseCamera(flip=True, device_id=camera_dict["bottom"])
            
            # 启动4个摄像头线程
            camera_specs = [
                (rs_top, 0),      # 顶部
                (rs_left, 1),     # 左腕
                (rs_right, 2),    # 右腕
                (rs_bottom, 3),   # 底部
            ]
            for camera, index in camera_specs:
                thread = threading.Thread(
                    target=self._run_camera_thread,
                    args=(camera, index),
                    daemon=True
                )
                thread.start()
                self.camera_threads.append(thread)
            
            # 等待所有4个摄像头就绪（最多10秒）
            if not self.image_ready.wait(timeout=10):
                return {
                    "success": False, 
                    "status": "camera_timeout", 
                    "message": "摄像头初始化超时，请检查4个摄像头连接",
                    "target_id": target_id
                }
            print("所有摄像头就绪！(顶部、左腕、右腕、底部)")
            
            # ========== 3. 连接到机器人服务器 ==========
            print(f"正在连接机器人服务器 {self.ROBOT_HOST}:{self.ROBOT_PORT}...")
            robot_client = ZMQClientRobot(port=self.ROBOT_PORT, host=self.ROBOT_HOST)
            self.env = RobotEnv(robot_client)
            
            # 初始化数字输出
            self.env.set_do_status([1, 0])  # 红灯关
            self.env.set_do_status([2, 0])  # 绿灯关
            self.env.set_do_status([3, 0])  # 黄灯关
            print("机器人连接成功！")
            
            # ========== 4. 移动到起始位置 ==========
            print("正在移动到起始位置...")
            if not self._move_to_start_pose():
                return {
                    "success": False, 
                    "status": "move_failed", 
                    "message": "机械臂移动到起始位置失败",
                    "target_id": target_id
                }
            print("已就绪于起始位置")
            
            # ========== 5. 加载模型 ==========
            print(f"正在加载模型: {model_path}")
            self.model = Imitate_Model(
                ckpt_dir=model_dir,
                ckpt_name=model_name
            )
            self.model.loadModel()
            print("模型加载成功！")
            
            # ========== 6. 准备推理 ==========
            obs = self.env.get_obs()
            obs["joint_positions"][6] = 1.0
            obs["joint_positions"][13] = 1.0
            
            # 注意：模型需要4个摄像头输入
            observation = {
                "qpos": obs["joint_positions"],
                "images": {
                    "left_wrist": None,
                    "right_wrist": None, 
                    "top": None,
                    "bottom": None,    
                },
            }
            last_action = observation["qpos"].copy()
            first = True
            steps_executed = 0
            
            print(f"开始推理，目标商品: {target_id}...")
            
            # ========== 7. 主推理循环 ==========
            while steps_executed < self.EPISODE_LEN and not self.stop_event.is_set():
                # 获取当前图像（4个摄像头）
                images = self._get_images()
                if (images["top"] is None or images["left"] is None or 
                    images["right"] is None or images["bottom"] is None):
                    time.sleep(0.01)
                    continue
                
                # 更新观测（4个图像）
                observation["images"]["top"] = images["top"]
                observation["images"]["left_wrist"] = images["left"]
                observation["images"]["right_wrist"] = images["right"]
                observation["images"]["bottom"] = images["bottom"]
                
                # 模型预测
                action = self.model.predict(observation, steps_executed)
                
                # 限制夹爪范围
                action[6] = np.clip(action[6], 0, 1)
                action[13] = np.clip(action[13], 0, 1)
                
                # 安全检查
                is_safe, safety_msg = self._check_action_safety(action, last_action)
                if not is_safe:
                    self.env.set_do_status([3, 0])  # 关闭黄灯
                    self.env.set_do_status([2, 0])  # 关闭绿灯
                    self.env.set_do_status([1, 1])  # 开启红灯
                    return {
                        "success": False,
                        "status": "safety_stop",
                        "steps_executed": steps_executed,
                        "message": safety_msg,
                        "target_id": target_id
                    }
                
                # 执行动作
                if first:
                    # 第一次执行使用平滑移动
                    self._move_to_joint_target(action, max_steps=100)
                    first = False
                else:
                    obs = self.env.step(action, np.array([1, 1]))
                    obs["joint_positions"][6] = action[6]
                    obs["joint_positions"][13] = action[13]
                    observation["qpos"] = obs["joint_positions"]
                
                last_action = action.copy()
                steps_executed += 1
                
                # 检查是否需要重置计数器
                threshold = np.deg2rad(10)
                reset_pose = np.deg2rad([-90, 0, -90, 0, 90, 90, 57, 90, 0, 90, 0, -90, -90, 57])
                if steps_executed > 1200 and np.all(np.abs(action - reset_pose) < threshold):
                    print("任务周期完成，重置计数器")
                    steps_executed = 0
            
            # ========== 8. 推理完成 ==========
            self.env.set_do_status([2, 1]) # 绿灯
            return {
                "success": True,
                "status": "completed" if not self.stop_event.is_set() else "stopped",
                "steps_executed": steps_executed,
                "model_name": model_name,
                "model_path": model_path,
                "target_id": target_id
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "success": False, 
                "status": "error", 
                "message": str(e),
                "target_id": target_id
            }
            
        finally:
            print("正在清理资源...")
            self.running.clear()
            for thread in self.camera_threads:
                thread.join(timeout=1)
            cv2.destroyAllWindows()
            print("清理完成")
    
    async def run(self, target_id: str) -> Dict[str, Any]:
        """
        异步运行推理（对外接口）
        
        Args:
            target_id: 目标商品ID（自动添加 .ckpt 后缀）
            
        Returns:
            推理结果字典
        """
        # 重置状态
        self.stop_event.clear()
        self.running.set()
        self._ready_count = 0
        self.image_ready.clear()
        
        # 使用 asyncio.to_thread 将同步推理转为异步
        result = await asyncio.to_thread(self._run_sync, target_id)
        return result
    
    def stop(self):
        """停止推理"""
        self.stop_event.set()
        self.running.clear()
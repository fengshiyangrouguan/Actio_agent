from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import logging
import os
import glob
import pickle
import numpy as np
import time

import toml

from backend.common.config.config_service import ConfigService
from backend.common.di.container import container
from backend.mainsystem.base_tool import BaseTool, ToolExecutionContext
from backend.dobot_xtrainer.dobot_control.robots.dobot import DobotRobot
import time
import sys
import cv2
import threading
from backedn.dobot_xtrainer.dobot_control.cameras.realsense_camera import RealSenseCamera
from backedn.dobot_xtrainer.scripts.manipulate_utils import load_ini_data_camera


logger = logging.getLogger(__name__)
# 摄像头图像全局变量
image_left, image_right, image_top, image_bottom, thread_run = None, None, None, None, None

def run_thread_cam(rs_cam, which_cam):
    """摄像头线程函数，持续读取相机图像"""
    global image_left, image_right, image_top, image_bottom, thread_run
    
    if which_cam == 1:  # 左侧相机
        while thread_run:
            image_left, _ = rs_cam.read()
            image_left = image_left[:, :, ::-1]  # RGB转换为BGR
    elif which_cam == 2:  # 右侧相机
        while thread_run:
            image_right, _ = rs_cam.read()
            image_right = image_right[:, :, ::-1]  # RGB转换为BGR
    elif which_cam == 0:  # 顶部相机
        while thread_run:
            image_top_src, _ = rs_cam.read()
            image_top_src = image_top_src[150:420, 220:480, ::-1]  
            image_top = cv2.resize(image_top_src, (640, 480))
    elif which_cam == 3:  # 底部相机
        while thread_run:
            image_bottom, _ = rs_cam.read()
            image_bottom = image_bottom[:, :, ::-1]  # RGB转换为BGR
    else:
        print("Camera index error!")


class PickUpTool(BaseTool):
    """控制机械臂抓取指定商品的工具"""

    @property
    def scopes(self) -> List[str]:
        return ["main"]

    @property
    def name(self) -> str:
        return "pick_up"

    @property
    def description(self) -> str:
        return "危险操作：机械臂物理抓取。必须传入商品的target_id"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_id": {"type": "string", "description": "商品唯一ID"},
            },
            "required": ["target_id"]
        }

    async def execute(self, context: ToolExecutionContext, **kwargs: Any) -> Dict[str, Any]:
        """
        执行抓取操作
        
        Args:
            context: 执行上下文
            **kwargs: 参数，包含 target_id
            
        Returns:
            抓取结果字典
        """
        # 获取目标ID
        target_id = kwargs.get("target_id")
        
        if not target_id:
            logger.error("缺少 target_id 参数")
            return {
                "status": "error",
                "success": False,
                "message": "缺少商品ID参数",
                "item_grabbed": None,
                "safety_check": "失败"
            }
        
        logger.info(f"开始抓取商品: {target_id}")
        
        try:
            # 执行轨迹复现
            result = self.replay_trajectory(target_id)
            
            if result["success"]:
                status = "success"
                item_grabbed = target_id
                safety_check = "通过"
                message = f"商品 {target_id} 抓取成功"
            else:
                status = "error"
                item_grabbed = None
                safety_check = "失败 - 轨迹复现错误"
                message = result.get("message", "抓取执行失败")
            
            logger.info(f"抓取完成 - 商品: {target_id}, 状态: {status}")
            
            # 返回结果
            return {
                "status": status,
                "item_grabbed": item_grabbed,
                "safety_check": safety_check,
                "success": result["success"],
                "steps_executed": result.get("steps_executed", 0),
                "message": message,
                "model_name": result.get("model_name"),
                "target_id": target_id,
                "model_path": result.get("model_path")
            }
            
        except Exception as e:
            logger.exception(f"抓取商品 {target_id} 时发生异常: {e}")
            return {
                "status": "error",
                "success": False,
                "message": f"抓取执行失败：{str(e)}",
                "item_grabbed": None,
                "safety_check": "失败 - 系统异常",
                "target_id": target_id
            }

    def load_trajectory(self, observation_dir: str) -> List[np.ndarray]:
        """
        从observation目录加载所有.pkl文件，并按键值排序。
        返回一个按时间顺序排列的关节角度列表。
        
        Args:
            observation_dir: 观测数据目录路径
            
        Returns:
            关节角度列表
        """
        if not os.path.exists(observation_dir):
            logger.error(f"观测数据目录不存在: {observation_dir}")
            return []
            
        # 获取所有.pkl文件路径
        pkl_files = glob.glob(os.path.join(observation_dir, "*.pkl"))
        if not pkl_files:
            logger.warning(f"目录 {observation_dir} 中没有找到.pkl文件")
            return []
        
        # 关键：按文件名中的数字部分排序，而不是字符串排序（避免 10.pkl 排在 2.pkl 前面）
        pkl_files.sort(key=lambda x: int(os.path.basename(x).split('.')[0]))
        
        joint_positions_list = []
        
        for file_path in pkl_files:
            try:
                with open(file_path, 'rb') as f:
                    obs = pickle.load(f)  # 加载保存的数据
                    
                # 从obs中提取关节角度。根据您的数据结构，关节位置在 obs["joint_positions"]
                if 'joint_positions' in obs:
                    joint_positions = obs['joint_positions']
                else:
                    # 尝试其他可能的键名
                    logger.warning(f"文件 {file_path} 中未找到 'joint_positions' 键。可用的键有：{list(obs.keys())}")
                    if 'joint_angles' in obs:
                        joint_positions = obs['joint_angles']
                    else:
                        continue
                        
                joint_positions_list.append(joint_positions)
            except Exception as e:
                logger.error(f"加载文件 {file_path} 时出错: {e}")
                continue
        
        logger.info(f"成功加载 {len(joint_positions_list)} 个轨迹点。")
        return joint_positions_list

    def replay_trajectory(self, target_id: str) -> Dict[str, Any]:
        """
        主复现函数
        
        Args:
            target_id: 商品ID
            
        Returns:
            轨迹复现结果字典
        """
        try:
            # 1. 构建观察数据目录
            current_file = os.path.abspath(__file__)  # /your_project/backend/tools/pickup.py
            project_root = Path(current_file).parent.parent.parent
            data_root = project_root / "data"
            observation_dir = data_root / target_id / "observation"
            # observation_dir = os.path.join("/data", target_id, "observation")
            
            # 检查目录是否存在
            if not os.path.exists(observation_dir):
                logger.error(f"观察数据目录不存在: {observation_dir}")
                return {
                    "success": False,
                    "message": f"未找到商品 {target_id} 的轨迹数据",
                    "steps_executed": 0
                }
            
            # 2. 加载轨迹数据
            logger.info(f"加载轨迹数据从: {observation_dir}")
            trajectory_1 = self.load_trajectory(observation_dir)
            
            if not trajectory_1:
                logger.error("未加载到任何轨迹数据！")
                return {
                    "success": False,
                    "message": "轨迹数据为空或加载失败",
                    "steps_executed": 0
                }
            
            # 提取所需的关节角度（第7到14个元素，对应索引7:14）
            trajectory = [i[7:14] for i in trajectory_1]
            
            if not trajectory:
                logger.error("轨迹数据转换失败！")
                return {
                    "success": False,
                    "message": "轨迹数据格式错误",
                    "steps_executed": 0
                }
            
            logger.info(f"加载了 {len(trajectory)} 个轨迹点")
            
            # 3. 初始化机械臂
            replay_speed_factor = 0.6
            logger.info("正在连接机械臂...")
            robot = container.resolve(DobotRobot)
            logger.info("机械臂连接成功。")
            
            # 4. 获取当前状态并初始化
            obs = robot.get_joint_state()
            logger.info(f"当前关节状态: {obs}")
            
            # 设置夹爪状态（第7个元素，索引6）
            obs[6] = 1.0  # 假设1.0表示夹爪关闭或特定状态
            last_action = obs.copy()
            
            first = True
            
            # 5. 移动到轨迹起始点
            logger.info("正在移动至轨迹起始点...")
            start_action = trajectory[0]
            
            if first:
                # 插值移动到起始点
                max_delta = (np.abs(last_action - start_action)).max()
                steps = min(int(max_delta / 0.001), 100)
                
                for jnt in np.linspace(last_action, start_action, steps):
                    success = robot.command_joint_state(jnt)
                    if not success:
                        logger.warning("插值移动过程中发送关节状态失败")
                        return {
                            "success": False,
                            "message": "移动到起始点失败",
                            "steps_executed": 0
                        }
                first = False
            
            # 等待稳定
            time.sleep(0.5)
            
            # 6. 开始复现轨迹
            logger.info("开始复现轨迹...")
            base_interval = 0.04  # 单位：秒，原始采集间隔
            actual_interval = base_interval / replay_speed_factor
            
            steps_executed = 0
            for i, joint_pos in enumerate(trajectory):
                # 发送关节状态
                success = robot.command_joint_state(np.array(joint_pos))
                
                if not success:
                    logger.warning(f"第 {i} 个点发送失败")
                    # 继续执行，但记录失败
                else:
                    steps_executed += 1
                
                # 等待下一个周期
                time.sleep(actual_interval)
                
                # 打印进度
                if i % 50 == 0 and i > 0:
                    logger.info(f"已复现 {i}/{len(trajectory)} 个点...")
            
            # 7. 完成清理
            robot.r_inter.StopDrag()  # 确保退出任何可能的状态
            
            logger.info("轨迹复现完成！")
            
            return {
                "success": True,
                "message": f"成功复现 {steps_executed}/{len(trajectory)} 个轨迹点",
                "steps_executed": steps_executed,
                "model_name": "dobot_trajectory_replay",
                "model_path": str(observation_dir) 
            
        except Exception as e:
            logger.exception(f"轨迹复现过程中发生异常: {e}")
            return {
                "success": False,
                "message": f"轨迹复现异常: {str(e)}",
                "steps_executed": 0
            }
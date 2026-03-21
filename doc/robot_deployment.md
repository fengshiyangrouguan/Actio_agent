# 机器人部署指南

## 1. 硬件准备
    
    略

## 2. 机械臂连接与配置

### 2.1 端口查找

使用端口查找脚本识别机械臂连接的串口：

```bash
cd Actio_agent
python backend/dobot_xtrainer/scripts/1_find_port.py
```

### 2.2 偏移量校准

机械臂安装后需要进行偏移量校准，确保双臂坐标系对齐：

```bash
python backend/dobot_xtrainer/scripts/3_just_buttonA.py
python backend/dobot_xtrainer/scripts/2_get_offset.py
```

**校准步骤**：

1. 运行`3_just_buttonA.py`
1. 控制左臂移动到参考点，锁住
2. 控制右臂移动到相同参考点，锁住
3. 停止`3_just_buttonA.py`，运行`2_get_offset.py`

### 2.3 配置文件生成

校准完成后，配置自动保存到 `backend/dobot_xtrainer/scripts/dobot_config/dobot_settings.ini`：

```ini
[Dobot]
left_arm_port = COM3
right_arm_port = COM5
baudrate = 115200

[Offset]
left_to_right_x = -0.5
left_to_right_y = 0.2
left_to_right_z = 0.0

[Safety]
joint_limit_min = -180
joint_limit_max = 180
velocity_limit = 100
acceleration_limit = 100
```

## 3 相机参数配置

配置文件位置：`backend/dobot_xtrainer/vision/camera_config.yaml`

示例：
```yaml
# 左眼相机配置
left_camera:
  serial: "840312060153"
  resolution:
    width: 1280
    height: 720
  fps: 30
  exposure: 100
  gain: 16
  
# 右眼相机配置
right_camera:
  serial: "840312060154"
  resolution:
    width: 1280
    height: 720
  fps: 30
  exposure: 100
  gain: 16

# 深度参数
depth:
  enabled: true
  min_distance: 0.2   # 米
  max_distance: 2.0   # 米
```

## 4. 夹爪配置

### 4.1 夹爪参数设置

配置文件：`backend/dobot_xtrainer/controllers/gripper_config.yaml`

示例：
```yaml
left_gripper:
  type: "electric"           # electric / pneumatic
  port: "COM3"
  baudrate: 115200
  max_force: 100             # 最大夹持力 (N)
  max_width: 80              # 最大开口宽度 (mm)
  min_width: 0               # 最小开口宽度 (mm)
  speed: 50                  # 夹持速度 (mm/s)
  
right_gripper:
  type: "electric"
  port: "COM5"
  baudrate: 115200
  max_force: 100
  max_width: 80
  min_width: 0
  speed: 50
```

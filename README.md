# Actio Agent

> **Actio** — 源自拉丁语 *"actio"*，意为"行动"与"驱动"。这个名字体现了项目的核心使命：将大语言模型的推理能力转化为物理世界中的精确行动，让智能体不仅能够"思考"，更能够"执行"。

Actio Agent 是一个面向物理交互场景的智能体编排框架。它通过大语言模型进行任务规划与推理，调度视觉-语言-动作（VLA）模型执行具体的机器人操作，实现从自然语言指令到物理世界动作的完整闭环。

项目最初为**零售场景的自动售货机器人**设计，支持商品识别、抓取等典型任务。得益于其可扩展的工具系统与技能框架，开发者只需添加相应的工具集和技能描述，即可快速适配仓储物流、家庭服务、工业装配等不同应用场景。

## 核心设计理念

- **编排优先**：LLM 负责任务分解与流程编排，VLA 模型负责底层视觉-动作映射，各司其职
- **工具可扩展**：通过简单的工具注册机制，即可为智能体增加新的物理操作能力
- **技能解耦**：技能提示词与执行逻辑分离，便于调试与迭代
- **对话即控制**：保持自然语言交互体验，复杂物理操作对用户透明

## 与现有范式的区别

Actio Agent 尝试在 VLA 与传统 Agent 之间开辟了一条新的路径：

| 范式 | 工作方式 | 局限性 |
|------|----------|--------|
| **端到端 VLA** | 视觉输入 → 神经网络 → 动作输出 | 黑盒执行，难以干预和调试；任务泛化能力弱；每个新任务需重新训练 |
| **传统 Agent** | LLM 推理 → API 调用 → 数字输出 | 局限于虚拟环境，无法操作物理设备；输出止于文本/API 调用 |
| **Actio Agent** | LLM 编排 → 原子 Action 组合 → 物理执行 | 透明可控，易于调试；Action 可复用可组合；真正驱动物理世界 |

### 核心差异化

**1. 不是端到端 VLA 的黑盒**
- VLA 将感知-决策-执行封装为一个不可分割的神经网络
- Actio Agent 将任务拆解为可组合的原子 Action
- LLM 负责高层编排，底层 Action 可灵活选择实现方式
- 每个环节透明可控，便于调试、干预和优化

**2. 不是传统 Agent 的虚拟边界**
- 传统 Agent 输出止于文本回复或 API 调用
- Actio Agent 通过机器人模块驱动真实机械臂、相机、夹爪
- 从"对话"延伸至"行动"，真正改变物理世界

**3. 混合执行引擎：多种模型与方法统一编排**

Actio Agent 的原子 Action 并非单一实现方式，而是支持混合多种模型和方法的统一执行引擎：

| Action 类型 | 实现方式 | 特点 |
|------------|----------|------|
| **长程操作** | Pi0、OpenVLA 等端到端模型 | 一次性执行完整操作链，适合复杂连续任务 |
| **精细操作** | ACT | 高频、高精度动作生成，适合抓取、装配等精细任务 |
| **确定性动作** | 硬编码运动路径 | 稳定可靠，适合重复性、标准化操作 |
| **移动导航** | SLAM + 底盘控制 | 环境感知与自主导航，扩展操作空间 |

```text
用户指令: "去仓库A区取一个红色盒子，放到传送带上"
    │
    ▼
LLM 编排混合 Action:
    ├─ nav_to(zone="A")              # SLAM 导航 Action
    ├─ pick_up(target="red_box")     # ACT 精细抓取 Action
    ├─ nav_to(target="conveyor")     # SLAM 导航 Action
    └─ place()                       # 硬编码放置 Action
    │
    ▼
物理执行: 底盘导航 → 机械臂抓取 → 底盘移动 → 机械臂放置
```

**4. 显式可调、可编排、可干预**

与端到端 VLA 的黑盒特性不同，Actio Agent 提供完整的可控性：

- **显式调节**：每个 Action 的执行参数可独立配置
- **灵活编排**：LLM 可根据任务需求动态组合不同 Action，设计SKILL即可实现复杂的条件校验/判断，行动链路设计
- **人工干预**：可在任意环节插入人工校验、条件判断或替代路径
- **边界控制**：可直接在SKILL中为 Agent 显式定义行为边界，或者直接写入代码

```text
可干预的执行流程:
    │
    ▼
[LLM 编排] → [人工确认] → [Action 执行] → [安全检查] → [条件分支]
                    ↑                              ↓
                    └──────── [异常干预] ←────────┘
```

## 当前能力

### 基础交互

| 能力 | 说明 |
|------|------|
| 文本对话 | 支持自然语言指令输入 |
| 语音识别 | 浏览器麦克风语音输入，支持通话模式自动启停 |
| 实时反馈 | SSE 流式返回任务状态与执行过程 |
| 人格定制 | 首次使用可配置机器人名称与性格 |

### 智能编排

| 能力 | 说明 |
|------|------|
| 任务规划 | LLM 根据用户意图生成结构化执行计划 |
| 工具调度 | 自动发现并调用注册的工具函数 |
| 模式切换 | `setup` / `main` 双模式，支持初始化agent个性引导 |
| 会话记忆 | 维护对话窗口与任务上下文 |

## 快速开始

### 1. 环境准备

```bash
# Python 3.10+ 虚拟环境
python -m venv venv
source venv/bin/activate

# 安装后端依赖
pip install -r requirements.txt

# 安装前端依赖
cd frontend && npm install && cd ..
```
或直接使用依赖构建脚本
```bash
./build.sh
```

### 2. 配置大模型

编辑 `configs/llm_api_config.toml`，填入有效的 API 信息：

```toml
[[api_providers]]
name = "YourProvider"
base_url = "https://your-api-base/v1"
api_key = "your-api-key"
client_type = "openai"
```

### 3. 启动服务

### 方式一：一键启动脚本（推荐 Linux）

Linux 用户可以使用提供的 `start.sh` 脚本一键启动所有服务：

```bash
# 给脚本添加执行权限
chmod +x start.sh

# 以 root 权限运行（自动配置串口权限）
sudo ./start.sh
```

脚本会自动完成以下操作：
- ✅ 配置机械臂串口权限
- ✅ 查找并确认机械臂端口
- ✅ 启动 launch_nodes 机器人控制节点
- ✅ 启动 Actio Agent 主程序
- ✅ 监控服务运行状态

访问 http://127.0.0.1:8080 开始使用。

**启动成功后会显示：**
```
============================================================
[INFO] Actio Agent 启动完成！
============================================================
后端服务: http://127.0.0.1:8000
前端服务: http://127.0.0.1:8080
============================================================
按 Ctrl+C 停止所有服务
```

**手动启动（不使用一键脚本）**

如果不想使用一键脚本，可以分步启动：

```bash
# 1. 配置串口权限（如需要）
sudo chmod 666 /dev/ttyUSB*

# 2. 启动机器人控制节点
python backend/dobot_xtrainer/experiments/launch_nodes.py

# 3. 新开终端，启动 Actio Agent
python main.py

# 4. 新开终端，启动前端（可选）
cd frontend && npm run dev
```

### 方式二：Windows 启动

```bash
python main.py
```

> **注意**：
> - Linux 用户使用 `start.sh` 可获得完整的自动化体验
> - `main.py` 针对 Windows 进行了优化，Linux/macOS 用户建议使用 `start.sh` 或手动分步启动
> - 如不使用机械臂，可跳过 `launch_nodes.py` 启动步骤

### 验证服务状态

服务启动后，可以通过以下方式验证：

```bash
# 检查后端 API
curl http://127.0.0.1:8000/health

# 检查前端服务
curl http://127.0.0.1:8080
```

### 常见问题

**Q: 提示串口权限不足怎么办？**
```bash
# 临时授权
sudo chmod 666 /dev/ttyUSB*

# 永久授权（将用户添加到 dialout 组）
sudo usermod -a -G dialout $USER
# 需要重新登录生效
```

**Q: 找不到串口设备？**
```bash
# 检查串口是否识别
ls -la /dev/ttyUSB*
ls -la /dev/ttyACM*

# 查看串口信息
dmesg | grep -i tty
```

**Q: launch_nodes 启动失败？**
- 确保机械臂已连接并上电
- 检查串口权限是否正确
- 查看日志：`tail -f logs/launch_nodes.log`（如果使用 start.sh）

**Q: 端口被占用？**
```bash
# 查看端口占用
sudo lsof -i :8000
sudo lsof -i :8080

# 杀死占用进程
kill -9 <PID>
```


## 扩展新能力

### 添加新工具

1. 在 `backend/tools/` 下创建新文件
2. 继承 `BaseTool` 并实现 `execute` 方法
3. 工具会被自动发现并注册

```python
from backend.tools.base import BaseTool

class MyNewTool(BaseTool):
    name = "my_tool"
    description = "工具功能描述"
    
    async def execute(self, **kwargs):
        # 实现具体逻辑
        return {"status": "success"}
```

### 添加新技能

在技能提示词目录中添加对应描述，LLM 会在规划阶段自动识别并调用相关工具组合。

## 文档索引

详细文档请参阅 `doc/` 目录：

- [架构设计详解](doc/architecture.md) — 系统模块与数据流说明
- [机器人部署指南](doc/robot_deployment.md) — 硬件连接、端口配置、偏移校准
- [API 参考](doc/api_reference.md) — 接口定义与事件格式

---

> **Actio Agent** — 让智能体走出终端。

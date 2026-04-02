#!/usr/bin/env python3
"""
测试从根目录导入 Imitate_Model
放置位置：项目根目录（/home/grvauun/Actio_agent/）
"""

import sys
import os
from pathlib import Path

def setup_import_path():
    """
    设置导入路径，确保从项目根目录可以导入
    """
    # 获取当前脚本所在目录（项目根目录）
    current_dir = Path(__file__).parent.absolute()
    print(f"当前目录: {current_dir}")
    
    # 将项目根目录添加到sys.path的第一个位置
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
        print(f"已将项目根目录添加到sys.path: {current_dir}")
    
    # 检查必要的目录是否存在
    expected_dirs = [
        "backend/dobot_xtrainer/ModelTrain/module",
        "backend/mainsystem"
    ]
    
    for rel_dir in expected_dirs:
        full_path = current_dir / rel_dir
        if full_path.exists():
            print(f"✓ 目录存在: {rel_dir}")
        else:
            print(f"✗ 目录不存在: {rel_dir}")

def test_import_statement():
    """
    测试导入语句
    """
    print("\n" + "="*50)
    print("开始测试导入语句")
    print("="*50)
    
    try:
        # 确保项目根目录在sys.path中
        current_dir = str(Path(__file__).parent.absolute())
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # 尝试绝对导入
        from backend.dobot_xtrainer.ModelTrain.module.model_module import Imitate_Model
        print("✓ 导入成功: Imitate_Model")
        
        # 尝试查看模块信息
        module = Imitate_Model.__module__
        print(f"  - 模块: {module}")
        print(f"  - 类名: {Imitate_Model.__name__}")
        
        return True, Imitate_Model
        
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        print("\n可能的原因:")
        print("1. 当前目录不是项目根目录")
        print("2. backend 目录下缺少 __init__.py 文件")
        print("3. 模块路径不正确")
        print("4. Python 版本不匹配")
        return False, None
    except Exception as e:
        print(f"✗ 其他错误: {type(e).__name__}: {e}")
        return False, None

def test_relative_import():
    """
    测试相对导入（备用方案）
    """
    print("\n" + "="*50)
    print("测试相对导入")
    print("="*50)
    
    try:
        # 切换到backend目录，使用相对导入
        original_dir = os.getcwd()
        backend_dir = Path(__file__).parent / "backend"
        
        if backend_dir.exists():
            os.chdir(backend_dir)
            from dobot_xtrainer.ModelTrain.module.model_module import Imitate_Model
            os.chdir(original_dir)
            print("✓ 相对导入成功")
            return True
        else:
            print("✗ backend目录不存在")
            return False
    except Exception as e:
        print(f"✗ 相对导入失败: {e}")
        return False

def list_pyc_files():
    """
    列出项目中所有的.pyc文件
    """
    print("\n" + "="*50)
    print("查找.pyc文件")
    print("="*50)
    
    root_dir = Path(__file__).parent
    pyc_files = list(root_dir.rglob("*.pyc"))
    
    if pyc_files:
        print(f"找到 {len(pyc_files)} 个.pyc文件:")
        for pyc_file in pyc_files[:10]:  # 只显示前10个
            print(f"  - {pyc_file.relative_to(root_dir)}")
        if len(pyc_files) > 10:
            print(f"  ... 还有 {len(pyc_files)-10} 个")
        
        # 检查是否有model_module.pyc
        model_module_pyc = root_dir / "backend" / "dobot_xtrainer" / "ModelTrain" / "module" / "model_module.pyc"
        if model_module_pyc.exists():
            print(f"\n找到目标.pyc文件: {model_module_pyc.relative_to(root_dir)}")
            # 检查.pyc文件头部
            with open(model_module_pyc, 'rb') as f:
                header = f.read(4)
                print(f"  文件头: {header} (hex: {header.hex()})")
                
                # 检查是否是Python 3.8的魔术数字
                if header == b'U\r\r\n':
                    print("  ✓ 这是Python 3.8的.pyc文件")
                else:
                    print(f"  ✗ 这不是Python 3.8的.pyc文件，请检查Python版本")
    else:
        print("未找到.pyc文件")

def check_python_version():
    """
    检查Python版本
    """
    print("\n" + "="*50)
    print("检查Python环境")
    print("="*50)
    
    import platform
    
    print(f"Python版本: {platform.python_version()}")
    print(f"Python实现: {platform.python_implementation()}")
    print(f"解释器路径: {sys.executable}")
    print(f"sys.path 前5个路径:")
    for i, path in enumerate(sys.path[:5]):
        print(f"  [{i}] {path}")

def check_directory_structure():
    """
    检查目录结构
    """
    print("\n" + "="*50)
    print("检查目录结构")
    print("="*50)
    
    root_dir = Path(__file__).parent
    target_path = root_dir / "backend" / "dobot_xtrainer" / "ModelTrain" / "module" / "model_module.py"
    
    # Check for missing __init__.py files
    init_paths = [
        root_dir / "backend" / "__init__.py",
        root_dir / "backend" / "dobot_xtrainer" / "__init__.py",
        root_dir / "backend" / "dobot_xtrainer" / "ModelTrain" / "__init__.py",
        root_dir / "backend" / "dobot_xtrainer" / "ModelTrain" / "module" / "__init__.py",
    ]
    
    print("检查__init__.py文件:")
    for init_path in init_paths:
        if init_path.exists():
            print(f"  ✓ {init_path.relative_to(root_dir)}")
        else:
            print(f"  ✗ 缺少: {init_path.relative_to(root_dir)}")
    
    if target_path.exists():
        print(f"✓ 找到目标文件: {target_path.relative_to(root_dir)}")
        
        # 检查是否有对应的.py文件
        if target_path.with_suffix('.pyc').exists():
            print(f"  - 存在.pyc文件")
        else:
            print(f"  - 不存在.pyc文件（可能需要编译）")
            
        # 检查文件大小
        print(f"  - 文件大小: {target_path.stat().st_size} 字节")
        
        # 读取前几行查看内容
        with open(target_path, 'r', encoding='utf-8') as f:
            first_lines = [f.readline().strip() for _ in range(5) if f.readline()]
        print(f"  - 文件前几行: {first_lines[:3]}")
    else:
        print(f"✗ 未找到目标文件: {target_path.relative_to(root_dir)}")
        print("\n尝试查找可能的路径:")
        for path in root_dir.rglob("*model_module*"):
            print(f"  - {path.relative_to(root_dir)}")

def try_alternative_imports():
    """
    尝试多种导入方式
    """
    print("\n" + "="*50)
    print("尝试多种导入方式")
    print("="*50)
    
    import_methods = [
        ("标准导入", "from backend.dobot_xtrainer.ModelTrain.module.model_module import Imitate_Model"),
        ("模块导入", "import backend.dobot_xtrainer.ModelTrain.module.model_module"),
        ("直接导入模块", "import sys; sys.path.insert(0, '.'); from backend.dobot_xtrainer.ModelTrain.module import model_module"),
    ]
    
    for method_name, import_code in import_methods:
        print(f"\n尝试: {method_name}")
        print(f"代码: {import_code}")
        try:
            exec(import_code)
            print("✓ 成功")
        except Exception as e:
            print(f"✗ 失败: {type(e).__name__}: {e}")

def clean_pycache():
    """
    清理__pycache__目录
    """
    print("\n" + "="*50)
    print("清理__pycache__和.pyc文件")
    print("="*50)


def main():
    """
    主函数
    """
    print("Imitate_Model导入测试脚本")
    print(f"运行时间: {__import__('datetime').datetime.now()}")
    
    # 1. 设置导入路径
    setup_import_path()
    
    # 2. 检查Python环境
    check_python_version()
    
    # 3. 检查目录结构
    check_directory_structure()
    
    # 4. 列出.pyc文件
    list_pyc_files()
    
    # 5. 测试导入
    success, model_class = test_import_statement()
    
    if not success:
        print("\n" + "="*50)
        print("尝试清理缓存后重新导入")
        print("="*50)
        
        # 清理缓存
        clean_pycache()
        
        # 重新导入
        success, model_class = test_import_statement()
    
    if not success:
        # 尝试其他导入方式
        try_alternative_imports()
        
        # 尝试相对导入
        test_relative_import()
    
    print("\n" + "="*50)
    if success:
        print("✓ 导入测试通过！")
        print(f"✓ 成功导入: {model_class}")
    else:
        print("✗ 导入测试失败")
        print("\n建议:")
        print("1. 确保当前在项目根目录运行此脚本")
        print("2. 运行: python -m compileall backend/")
        print("3. 检查backend目录下是否有__init__.py文件")
        print("4. 检查Python版本: 需要Python 3.8")
    
    return success

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='测试Imitate_Model导入')
    parser.add_argument('--clean', action='store_true', help='清理缓存文件')
    parser.add_argument('--list', action='store_true', help='列出.pyc文件')
    
    args = parser.parse_args()
    
    if args.clean:
        clean_pycache()
    
    if args.list:
        list_pyc_files()
    
    if not args.clean and not args.list:
        result = main()
        sys.exit(0 if result else 1)
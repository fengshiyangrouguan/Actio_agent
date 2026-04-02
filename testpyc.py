import binascii
import struct

# 读取有问题的 .pyc 文件
with open('backend/dobot_xtrainer/ModelTrain/module/model_module.pyc', 'rb') as f:
    magic = f.read(4)
    print(f"魔数: {binascii.hexlify(magic)}")
    
    # 常见 Python 版本的魔数
    magic_numbers = {
        b'\x03\xf3\x0d\x0a': 'Python 3.2-3.7',
        b'\xee\x0c\x0d\x0a': 'Python 3.8',
        b'\x61\x0d\x0d\x0a': 'Python 3.9',  # 你的期望值
        b'\x6f\x0d\x0d\x0a': 'Python 3.10',
        b'\x55\x0d\x0d\x0a': 'Python 3.11',  # 看起来像这个
    }
    
    for magic_byte, version in magic_numbers.items():
        if magic == magic_byte:
            print(f"检测到: {version}")
            break
    else:
        print("未知的 Python 版本")
"""
Kiwi 语音助手 - 主程序入口

使用新架构的完整语音助手系统
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.gui.kiwi_assistant_gui import main

if __name__ == "__main__":
    main()

"""
VAD模块异常定义
"""


class VADError(Exception):
    """VAD基础异常"""
    pass


class VADInitError(VADError):
    """VAD初始化错误"""
    pass


class VADProcessError(VADError):
    """VAD处理错误"""
    pass

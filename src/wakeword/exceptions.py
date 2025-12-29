"""
唤醒词模块异常定义
"""


class WakeWordError(Exception):
    """唤醒词基础异常"""
    pass


class WakeWordInitError(WakeWordError):
    """唤醒词初始化错误"""
    pass


class WakeWordDetectionError(WakeWordError):
    """唤醒词检测错误"""
    pass

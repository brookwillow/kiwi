"""
音频模块异常定义
"""


class AudioError(Exception):
    """音频模块基础异常"""
    pass


class AudioDeviceError(AudioError):
    """音频设备相关错误"""
    pass


class RecorderNotStartedError(AudioError):
    """录音未启动错误"""
    pass


class ConfigError(AudioError):
    """配置错误"""
    pass


class BufferOverflowError(AudioError):
    """缓冲区溢出错误"""
    pass

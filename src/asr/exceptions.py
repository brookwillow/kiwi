"""
ASR 模块异常定义
"""


class ASRError(Exception):
    """ASR 模块基础异常"""
    pass


class ModelNotFoundError(ASRError):
    """模型文件未找到"""
    pass


class RecognitionError(ASRError):
    """识别错误"""
    pass


class AudioFormatError(ASRError):
    """音频格式错误"""
    pass

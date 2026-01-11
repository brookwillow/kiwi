"""
LLM模块异常定义

统一的异常处理
"""


class LLMError(Exception):
    """LLM基础异常"""
    pass


class LLMProviderError(LLMError):
    """Provider级别的错误"""
    def __init__(self, provider: str, message: str, original_error: Exception = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"[{provider}] {message}")


class LLMConfigError(LLMError):
    """配置错误"""
    pass


class LLMAPIError(LLMProviderError):
    """API调用错误"""
    def __init__(self, provider: str, status_code: int, message: str, original_error: Exception = None):
        self.status_code = status_code
        super().__init__(provider, f"API Error ({status_code}): {message}", original_error)


class LLMAuthenticationError(LLMProviderError):
    """认证错误（API Key无效等）"""
    pass


class LLMRateLimitError(LLMProviderError):
    """速率限制错误"""
    pass


class LLMTimeoutError(LLMProviderError):
    """超时错误"""
    pass


class LLMNetworkError(LLMProviderError):
    """网络错误"""
    pass


class LLMProviderUnavailableError(LLMProviderError):
    """Provider不可用"""
    pass


class LLMAllProviderFailedError(LLMError):
    """所有Provider都失败"""
    def __init__(self, errors: dict):
        self.errors = errors
        error_msgs = [f"{provider}: {str(error)}" for provider, error in errors.items()]
        super().__init__(f"所有Provider均失败: {'; '.join(error_msgs)}")

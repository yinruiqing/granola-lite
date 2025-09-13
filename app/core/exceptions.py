"""
自定义异常类
"""

from fastapi import HTTPException, status


class GranolaException(Exception):
    """Granola应用基础异常"""
    
    def __init__(self, message: str, code: str = "GENERAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class DatabaseException(GranolaException):
    """数据库异常"""
    
    def __init__(self, message: str = "数据库操作失败"):
        super().__init__(message, "DATABASE_ERROR")


class AIServiceException(GranolaException):
    """AI服务异常"""
    
    def __init__(self, message: str = "AI服务调用失败"):
        super().__init__(message, "AI_SERVICE_ERROR")


class FileProcessingException(GranolaException):
    """文件处理异常"""
    
    def __init__(self, message: str = "文件处理失败"):
        super().__init__(message, "FILE_PROCESSING_ERROR")


class ValidationException(GranolaException):
    """数据验证异常"""
    
    def __init__(self, message: str = "数据验证失败"):
        super().__init__(message, "VALIDATION_ERROR")


class ResourceNotFoundException(GranolaException):
    """资源未找到异常"""
    
    def __init__(self, resource: str = "资源"):
        message = f"{resource}不存在"
        super().__init__(message, "RESOURCE_NOT_FOUND")


class PermissionDeniedException(GranolaException):
    """权限不足异常"""
    
    def __init__(self, message: str = "权限不足"):
        super().__init__(message, "PERMISSION_DENIED")


class RateLimitException(GranolaException):
    """速率限制异常"""
    
    def __init__(self, message: str = "请求过于频繁，请稍后重试"):
        super().__init__(message, "RATE_LIMIT_EXCEEDED")


class ConfigurationException(GranolaException):
    """配置错误异常"""
    
    def __init__(self, message: str = "配置错误"):
        super().__init__(message, "CONFIGURATION_ERROR")


# HTTP异常映射
def granola_exception_to_http_exception(exc: GranolaException) -> HTTPException:
    """将Granola异常转换为HTTP异常"""
    
    status_code_mapping = {
        "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
        "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
        "CONFIGURATION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "AI_SERVICE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
        "FILE_PROCESSING_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
    }
    
    status_code = status_code_mapping.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return HTTPException(
        status_code=status_code,
        detail={
            "error": True,
            "code": exc.code,
            "message": exc.message,
            "type": type(exc).__name__
        }
    )
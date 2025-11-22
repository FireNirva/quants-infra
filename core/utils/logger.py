"""
日志管理模块

此模块提供了统一的日志管理功能，包括：
1. 日志文件的创建和管理
2. 日志格式的统一配置
3. 控制台和文件双重输出
4. 单例模式确保日志配置的一致性

使用方法:
    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("这是一条日志消息")
"""

import logging
import os
from datetime import datetime
from typing import Optional


class LoggerSetup:
    """
    日志设置类

    负责日志系统的初始化和配置，使用单例模式确保全局只有一个日志配置实例。

    属性:
        module_root (str): 模块根目录路径
        log_dir (str): 日志文件存储目录
        _instance (Optional[LoggerSetup]): 单例实例
        _initialized (bool): 是否已初始化标志
    """

    _instance: Optional['LoggerSetup'] = None
    _initialized: bool = False

    def __new__(cls) -> 'LoggerSetup':
        """
        实现单例模式

        Returns:
            LoggerSetup: 日志设置类的唯一实例
        """
        if cls._instance is None:
            cls._instance = super(LoggerSetup, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """初始化日志设置"""
        if not self._initialized:
            # 获取模块根目录（deployment/ansible）
            self.module_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.log_dir = os.path.join(self.module_root, 'logs')
            self._initialized = True

    def setup(self) -> logging.Logger:
        """
        设置并配置日志系统

        功能：
        1. 创建日志目录
        2. 配置日志格式
        3. 设置文件和控制台输出
        4. 设置日志级别

        Returns:
            logging.Logger: 配置完成的根日志记录器

        Raises:
            OSError: 如果创建日志目录失败
            Exception: 其他配置过程中的错误
        """
        try:
            # 创建日志目录
            os.makedirs(self.log_dir, exist_ok=True)

            # 生成日志文件名（包含时间戳）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = os.path.join(self.log_dir, f"deployment_{timestamp}.log")

            # 配置日志格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

            # 配置文件处理器
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.INFO)

            # 配置控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)

            # 获取并配置根日志记录器
            logger = logging.getLogger()
            logger.setLevel(logging.INFO)

            # 清除现有的处理器（避免重复）
            logger.handlers.clear()

            # 添加处理器
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

            return logger

        except OSError as e:
            raise OSError(f"创建日志目录失败: {str(e)}")
        except Exception as e:
            raise Exception(f"日志系统配置失败: {str(e)}")

    def get_logger(self, name: str) -> logging.Logger:
        """
        获取指定名称的日志记录器

        Args:
            name (str): 日志记录器名称，通常使用 __name__

        Returns:
            logging.Logger: 指定名称的日志记录器
        """
        return logging.getLogger(name)


# 创建全局的logger实例
_logger_setup = LoggerSetup()


def setup_logger() -> logging.Logger:
    """
    设置并返回根日志记录器

    Returns:
        logging.Logger: 配置完成的根日志记录器

    Raises:
        Exception: 日志系统配置过程中的错误
    """
    return _logger_setup.setup()


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器

    Args:
        name (str): 日志记录器名称，通常使用 __name__

    Returns:
        logging.Logger: 指定名称的日志记录器

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("这是一条信息日志")
        >>> logger.error("这是一条错误日志")
    """
    return _logger_setup.get_logger(name) 
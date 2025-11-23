"""
Pytest configuration for Infrastructure tests
"""

import pytest


def pytest_addoption(parser):
    """添加自定义 pytest 选项"""
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="运行 E2E 测试（会创建真实 AWS 资源并产生费用）"
    )


def pytest_configure(config):
    """配置 pytest"""
    config.addinivalue_line(
        "markers",
        "e2e: marks tests as E2E tests that create real resources (deselect with '-m \"not e2e\"')"
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


"""Utility functions"""
import platform
import sys
from pathlib import Path


def is_container():
    root = Path('/')
    if (root / '.dockerenv').exists():
        return 'docker'
    if (root / 'singularity').exists():
        return 'apptainer'
    return 'unknown'


def get_platform_info() -> dict:
    return {
        # 'language_implementation': platform.python_implementation(),
        'language': "python",
        'language_version': platform.python_version(),
        'platform': sys.platform,
    }


def compile_info() -> dict:
    from ci_info import is_ci

    data = get_platform_info()
    data['container'] = is_container()
    data['is_ci'] = is_ci()
    return data

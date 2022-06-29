"""Utility functions"""
from pathlib import Path
import platform
import sys


def is_ci():
    ...

def is_container():
    root = Path('/')
    if (root / '.dockerenv').exists():
        return 'docker'
    if (root / 'singularity').exists():
        return 'apptainer'
    return 'unknown'


def get_platform_info() -> dict:
    return {
        'python_version': platform.python_version(),
        'python_implementation': platform.python_implementation(),
        'platform': sys.platform,
    }


def compile_info() -> dict:
    data = get_platform_info()
    data['container'] = is_container()
    return data

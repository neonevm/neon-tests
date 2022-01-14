import pytest


def pytest_addoption(parser):
    parser.addoption(
        '--env', action='store', default='night', help='Which stand use'
    )

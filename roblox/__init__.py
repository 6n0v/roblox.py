"""
:copyright: (c) 2026-present 6n0v
:license: MIT, see LICENSE for more details.
"""

__title__ = 'arawe'
__author__ = '6n0v'
__license__ = 'MIT'
__copyright__ = 'Copyright 2026-present 6n0v'

__all__ = (
    'Forbidden',
    'Gamepass',
    'InternalServerError',
    'NotFound',
    'PartialGamepass',
    'PartialUser',
    'PendingTransactionAlreadyExists',
    'Roblox',
    'Unauthorized',
    'UnknownStatus',
    'User',
    'WrongDataPassed',
    '__version__',
)

try:
    from ._version import __version__  # type: ignore
except ImportError:
    __version__ = 'unknown'

from . import abc as abc
from .client import Roblox
from .errors import (
    Forbidden,
    InternalServerError,
    NotFound,
    PendingTransactionAlreadyExists,
    Unauthorized,
    UnknownStatus,
    WrongDataPassed,
)
from .gamepass import Gamepass, PartialGamepass
from .user import PartialUser, User

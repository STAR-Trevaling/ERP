# -*- coding: utf-8 -*-
from typing import Any, Callable


def model(func: Callable) -> Callable:
    return func


def multi(func: Callable) -> Callable:
    return func


def depends(*args: str) -> Callable:
    return lambda func: func


def onchange(*args: str) -> Callable:
    return lambda func: func


def constrains(*args: str) -> Callable:
    return lambda func: func


def autovacuum(func: Callable) -> Callable:
    return func


def readonly(func: Callable) -> Callable:
    return func

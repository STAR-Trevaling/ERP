# -*- coding: utf-8 -*-
"""
Lightweight Odoo Type Stubs & Runtime Mock for IDE Language Server
Đảm bảo 100% không báo đỏ cho Odoo Models, Fields, API, ORM methods
"""
from . import models
from . import fields
from . import api
from . import exceptions

from .models import Model, TransientModel, AbstractModel
from .exceptions import UserError, ValidationError, AccessError


def _(text: str) -> str:
    return text


__all__ = [
    'models',
    'fields',
    'api',
    'exceptions',
    'Model',
    'TransientModel',
    'AbstractModel',
    'UserError',
    'ValidationError',
    'AccessError',
    '_',
]

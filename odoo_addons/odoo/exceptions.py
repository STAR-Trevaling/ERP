# -*- coding: utf-8 -*-
class UserError(Exception):
    pass


class ValidationError(Exception):
    pass


class AccessError(Exception):
    pass


class AccessDenied(Exception):
    pass


class MissingError(Exception):
    pass

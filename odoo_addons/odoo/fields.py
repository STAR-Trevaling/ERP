# -*- coding: utf-8 -*-
from typing import Any, Optional, Tuple


class Field:
    def __init__(self, string: Optional[str] = None, **kwargs: Any) -> None:
        pass

    def __get__(self, instance: Any, owner: Any) -> Any:
        return self

    def __set__(self, instance: Any, value: Any) -> None:
        pass


class Boolean(Field):
    pass


class Integer(Field):
    pass


class Float(Field):
    pass


class Char(Field):
    pass


class Text(Field):
    pass


class Html(Field):
    pass


class Date(Field):
    pass


class Datetime(Field):
    pass


class Binary(Field):
    pass


class Selection(Field):
    def __init__(self, selection: Any = None, string: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(string=string, **kwargs)


class Many2one(Field):
    def __init__(self, comodel_name: Optional[str] = None, string: Optional[str] = None, **kwargs: Any) -> None:
        super().__init__(string=string, **kwargs)


class One2many(Field):
    def __init__(
        self,
        comodel_name: Optional[str] = None,
        inverse_name: Optional[str] = None,
        string: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(string=string, **kwargs)


class Many2many(Field):
    def __init__(
        self,
        comodel_name: Optional[str] = None,
        relation: Optional[str] = None,
        column1: Optional[str] = None,
        column2: Optional[str] = None,
        string: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(string=string, **kwargs)


class Monetary(Field):
    pass


class Command:
    @classmethod
    def create(cls, values: dict) -> Tuple[int, int, dict]:
        return (0, 0, values)

    @classmethod
    def update(cls, id: int, values: dict) -> Tuple[int, int, dict]:
        return (1, id, values)

    @classmethod
    def delete(cls, id: int) -> Tuple[int, int, int]:
        return (2, id, 0)

    @classmethod
    def unlink(cls, id: int) -> Tuple[int, int, int]:
        return (3, id, 0)

    @classmethod
    def link(cls, id: int) -> Tuple[int, int, int]:
        return (4, id, 0)

    @classmethod
    def clear(cls) -> Tuple[int, int, int]:
        return (5, 0, 0)

    @classmethod
    def set(cls, ids: list) -> Tuple[int, int, list]:
        return (6, 0, ids)

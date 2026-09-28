# -*- coding: utf-8 -*-
from typing import Any, List, Dict, Optional, Union, Callable


class Environment(dict):
    cr: Any
    uid: int
    context: Dict[str, Any]
    user: Any
    company: Any
    companies: Any

    def __getitem__(self, key: str) -> Any:
        return Model()

    def __getattr__(self, name: str) -> Any:
        return None


class BaseQuerySet:
    def __iter__(self) -> Any:
        return iter([])

    def __len__(self) -> int:
        return 1

    def __bool__(self) -> bool:
        return True

    def __getitem__(self, item: Any) -> Any:
        return self


class Model(BaseQuerySet):
    _name: str = ""
    _inherit: Any = None
    _description: str = ""
    _order: str = "id"

    id: int = 1
    display_name: str = ""
    env: Environment = Environment()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def search(
        self,
        domain: Any = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
    ) -> Any:
        return self

    def search_read(
        self,
        domain: Any = None,
        fields: Optional[List[str]] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return []

    def search_count(self, domain: Any = None) -> int:
        return 0

    def browse(self, ids: Any = None) -> Any:
        return self

    def create(self, vals: Any) -> Any:
        return self

    def write(self, vals: Dict[str, Any]) -> bool:
        return True

    def unlink(self) -> bool:
        return True

    def exists(self) -> Any:
        return self

    def filtered(self, func: Callable[[Any], bool]) -> Any:
        return self

    def mapped(self, func: Union[str, Callable[[Any], Any]]) -> List[Any]:
        return []

    def sorted(
        self,
        key: Optional[Callable[[Any], Any]] = None,
        reverse: bool = False
    ) -> Any:
        return self

    def ensure_one(self) -> Any:
        return self

    def copy(self, default: Optional[Dict[str, Any]] = None) -> Any:
        return self

    def __getattr__(self, name: str) -> Any:
        return None

    def __setattr__(self, name: str, value: Any) -> None:
        pass


class TransientModel(Model):
    _transient: bool = True


class AbstractModel(Model):
    _abstract: bool = True

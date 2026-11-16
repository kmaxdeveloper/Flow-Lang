"""
Flow Language — Array Standard Library Methods
===============================================
Array (massiv) turlari uchun o'rnatilgan metodlar.
"""
from typing import Any, List, Optional
from src.vm.memory import _to_flow_str


def arr_pop(arr: List[Any]) -> Any:
    """Massivning oxirgi elementini sug'urib oladi va qaytaradi."""
    if not arr:
        return None
    return arr.pop()


def arr_contains(arr: List[Any], val: Any) -> bool:
    """Massivda berilgan element mavjudligini tekshiradi."""
    return val in arr


def arr_join(arr: List[Any], sep: Any = "") -> str:
    """Massiv elementlarini berilgan ajratuvchi bilan bitta satrga birlashtiradi."""
    sep_str = str(sep) if sep is not None else ""
    return sep_str.join(_to_flow_str(x) for x in arr)


def arr_slice(arr: List[Any], start: Any = 0, end: Any = None) -> List[Any]:
    """Massivdan [start:end] oraliqdagi nusxani qaytaradi."""
    s = int(start) if start is not None else 0
    if end is not None:
        e = int(end)
        return arr[s:e]
    return arr[s:]


def arr_push(arr: List[Any], val: Any) -> None:
    """Massiv oxiriga element qo'shadi."""
    arr.append(val)


ARRAY_METHODS = {
    "pop": lambda arr, args: arr_pop(arr),
    "contains": lambda arr, args: arr_contains(arr, args[0] if args else None),
    "join": lambda arr, args: arr_join(arr, str(args[0]) if args else ""),
    "slice": lambda arr, args: arr_slice(arr, args[0] if len(args) > 0 else 0, args[1] if len(args) > 1 else None),
    "push": lambda arr, args: arr_push(arr, args[0] if args else None),
    "length": lambda arr, args: len(arr),
}


def has_array_method(method_name: str) -> bool:
    return method_name in ARRAY_METHODS


def call_array_method(arr: List[Any], method_name: str, args: List[Any]) -> Any:
    if method_name not in ARRAY_METHODS:
        raise AttributeError(f"Array ob'ektida '{method_name}' metodi topilmadi")
    return ARRAY_METHODS[method_name](arr, args)

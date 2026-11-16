"""
Flow Language — Standart Kutubxona (Standard Library)
=====================================================
1-bosqich: Built-in Type Methods (String, Int, Float, Array).
"""
from typing import Any, List, Optional
from .string_methods import (
    STRING_METHODS,
    has_string_method,
    call_string_method,
    str_trim,
    str_split,
    str_replace,
    str_contains,
    str_starts_with,
    str_ends_with,
)
from .number_methods import (
    NUMBER_METHODS,
    has_number_method,
    call_number_method,
    num_abs,
    num_round,
    num_ceil,
    num_floor,
    num_clamp,
)
from .array_methods import (
    ARRAY_METHODS,
    has_array_method,
    call_array_method,
    arr_pop,
    arr_contains,
    arr_join,
    arr_slice,
    arr_push,
)


def has_builtin_method(obj: Any, method_name: str) -> bool:
    """Obyekt turiga qarab metod mavjudligini aniqlaydi."""
    if isinstance(obj, str):
        return has_string_method(method_name)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return has_number_method(method_name)
    elif isinstance(obj, list):
        return has_array_method(method_name)
    return False


def call_builtin_method(obj: Any, method_name: str, args: List[Any]) -> Any:
    """Obyekt turiga qarab mos metodni chaqiradi."""
    if isinstance(obj, str):
        return call_string_method(obj, method_name, args)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return call_number_method(obj, method_name, args)
    elif isinstance(obj, list):
        return call_array_method(obj, method_name, args)
    raise AttributeError(f"'{type(obj).__name__}' tipida '{method_name}' metodi topilmadi")


def get_builtin_property(obj: Any, prop_name: str) -> Any:
    """Obyekt turiga qarab o'rnatilgan xususiyat (property) qiymatini qaytaradi."""
    if isinstance(obj, (str, list)):
        if prop_name == "length":
            return len(obj)
    raise AttributeError(f"'{type(obj).__name__}' tipida '{prop_name}' xususiyati topilmadi")


__all__ = [
    "STRING_METHODS",
    "NUMBER_METHODS",
    "ARRAY_METHODS",
    "has_builtin_method",
    "call_builtin_method",
    "get_builtin_property",
    "has_string_method",
    "call_string_method",
    "has_number_method",
    "call_number_method",
    "has_array_method",
    "call_array_method",
]

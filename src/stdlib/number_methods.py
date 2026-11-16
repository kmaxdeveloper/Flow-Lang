"""
Flow Language — Number (Int / Float) Standard Library Methods
=============================================================
Int va Float son turlari uchun o'rnatilgan metodlar.
"""
import math
from typing import Any, List, Union

Number = Union[int, float]


def num_abs(n: Number) -> Number:
    """Sonning absolyut qiymati (moduli)."""
    return abs(n)


def num_round(n: Number, *args: Any) -> Number:
    """Sonni eng yaqin butun songa (yoki berilgan xonagacha) yaxlitlaydi."""
    if args:
        digits = int(args[0])
        return round(n, digits)
    return round(n)


def num_ceil(n: Number) -> int:
    """Sonni yuqoriga qarab eng yaqin butun songa yaxlitlaydi."""
    return math.ceil(n)


def num_floor(n: Number) -> int:
    """Sonni pastga qarab eng yaqin butun songa yaxlitlaydi."""
    return math.floor(n)


def num_clamp(n: Number, min_val: Number, max_val: Number) -> Number:
    """Sonni [min_val, max_val] oralig'ida chegaralaydi."""
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    if n < min_val:
        return min_val
    if n > max_val:
        return max_val
    return n


NUMBER_METHODS = {
    "abs": lambda n, args: num_abs(n),
    "round": lambda n, args: num_round(n, *args),
    "ceil": lambda n, args: num_ceil(n),
    "floor": lambda n, args: num_floor(n),
    "clamp": lambda n, args: num_clamp(n, args[0], args[1]) if len(args) >= 2 else n,
}


def has_number_method(method_name: str) -> bool:
    return method_name in NUMBER_METHODS


def call_number_method(n: Number, method_name: str, args: List[Any]) -> Any:
    if method_name not in NUMBER_METHODS:
        t_name = "Float" if isinstance(n, float) else "Int"
        raise AttributeError(f"{t_name} tipida '{method_name}' metodi topilmadi")
    return NUMBER_METHODS[method_name](n, args)

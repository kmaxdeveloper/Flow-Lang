"""
Flow Language — String Standard Library Methods
================================================
String (satr) turlari uchun o'rnatilgan metodlar.
"""
from typing import Any, List


def str_trim(s: str) -> str:
    """Satr boshi va oxiridagi bo'sh joylarni olib tashlaydi."""
    return s.strip()


def str_split(s: str, sep: Any = " ") -> List[str]:
    """Satrni ajratuvchi (separator) bo'yicha massivga ajratadi."""
    sep_str = str(sep) if sep is not None else " "
    return s.split(sep_str)


def str_replace(s: str, old: Any, new: Any) -> str:
    """Satrdagi eski qismni yangisiga almashtiradi."""
    return s.replace(str(old), str(new))


def str_contains(s: str, sub: Any) -> bool:
    """Satr ichida berilgan qism-satr mavjudligini tekshiradi."""
    return str(sub) in s


def str_starts_with(s: str, prefix: Any) -> bool:
    """Satr berilgan prefiks bilan boshlanishini tekshiradi."""
    return s.startswith(str(prefix))


def str_ends_with(s: str, suffix: Any) -> bool:
    """Satr berilgan suffiks bilan tugashini tekshiradi."""
    return s.endswith(str(suffix))


def str_upper(s: str) -> str:
    """Satrni bosh harflarga o'tkazadi."""
    return s.upper()


def str_lower(s: str) -> str:
    """Satrni kichik harflarga o'tkazadi."""
    return s.lower()


STRING_METHODS = {
    "trim": lambda s, args: str_trim(s),
    "split": lambda s, args: str_split(s, args[0] if args else " "),
    "replace": lambda s, args: str_replace(s, args[0], args[1]) if len(args) >= 2 else s,
    "contains": lambda s, args: str_contains(s, args[0] if args else ""),
    "startsWith": lambda s, args: str_starts_with(s, args[0] if args else ""),
    "endsWith": lambda s, args: str_ends_with(s, args[0] if args else ""),
    "upper": lambda s, args: str_upper(s),
    "lower": lambda s, args: str_lower(s),
    "length": lambda s, args: len(s),
}


def has_string_method(method_name: str) -> bool:
    return method_name in STRING_METHODS


def call_string_method(s: str, method_name: str, args: List[Any]) -> Any:
    if method_name not in STRING_METHODS:
        raise AttributeError(f"String ob'ektida '{method_name}' metodi topilmadi")
    return STRING_METHODS[method_name](s, args)

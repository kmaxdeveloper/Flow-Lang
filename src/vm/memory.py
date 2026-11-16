from typing import Dict, Any, Optional, Set, List


class FlowObject:
    """Flow tilidagi ob'ekt (class instansiyasi)."""

    def __init__(self, class_name: str, fields: Dict[str, Any]):
        self.class_name = class_name
        self.fields = dict(fields)  # {field_name: value}
        self._class_def: Optional[Dict[str, Any]] = None  # metodlar ro'yxati

    def get_field(self, name: str) -> Any:
        if name in self.fields:
            return self.fields[name]
        raise AttributeError(f"'{self.class_name}' klassida '{name}' maydoni topilmadi")

    def set_field(self, name: str, value: Any):
        self.fields[name] = value

    def get_method(self, name: str) -> Optional[Dict[str, Any]]:
        if self._class_def:
            for method in self._class_def.get("methods", []):
                if method["name"] == name:
                    return method
        return None

    def __repr__(self) -> str:
        fields_str = ", ".join(f"{k}={repr(v)}" for k, v in self.fields.items())
        return f"{self.class_name}({fields_str})"

    def __str__(self) -> str:
        return self.__repr__()


class ExpiredVariableError(RuntimeError):
    """Muddati tugagan live o'zgaruvchiga murojaat xatosi."""
    pass


class CallFrame:
    def __init__(
        self,
        name: str,
        code: List[Dict[str, Any]],
        parent: Optional["CallFrame"] = None,
        this_obj: Optional[FlowObject] = None,  # OOP uchun 'this'
    ):
        self.name = name
        self.code = code
        self.ip = 0  # Instruction pointer
        self.variables: Dict[str, Any] = {}
        self.constants: Set[str] = set()  # 'val' (immutable) o'zgaruvchilar nomi
        self.live_vars: Dict[str, int] = {}  # name -> remaining accesses
        self.expired_vars: Set[str] = set()  # o'chirilgan (expired) o'zgaruvchilar
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.classes: Dict[str, Dict[str, Any]] = {}  # OOP uchun klass ta'riflari
        self.parent = parent
        self.this_obj = this_obj  # Joriy 'this' ob'ekt

    def is_val(self, name: str) -> bool:
        if name in self.constants:
            return True
        if self.parent:
            return self.parent.is_val(name)
        return False

    def is_expired(self, name: str) -> bool:
        if name in self.expired_vars:
            return True
        if self.parent:
            return self.parent.is_expired(name)
        return False

    def has_var(self, name: str) -> bool:
        if name in self.variables:
            return True
        if self.parent:
            return self.parent.has_var(name)
        return False

    def get_live_counter(self, name: str) -> Optional[int]:
        if name in self.live_vars:
            return self.live_vars[name]
        if self.parent:
            return self.parent.get_live_counter(name)
        return None

    def access_live_var(self, name: str) -> bool:
        if name in self.live_vars:
            self.live_vars[name] -= 1
            if self.live_vars[name] <= 0:
                del self.live_vars[name]
                if name in self.variables:
                    del self.variables[name]
                self.expired_vars.add(name)
            return True
        if self.parent:
            return self.parent.access_live_var(name)
        return False

    def lookup_var(self, name: str) -> Optional[Any]:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup_var(name)
        return None

    def update_var(self, name: str, value: Any) -> bool:
        """Mavjud o'zgaruvchini o'z scopeda yangilash."""
        if name in self.variables:
            self.variables[name] = value
            return True
        if self.parent:
            return self.parent.update_var(name, value)
        return False

    def lookup_func(self, name: str) -> Optional[Dict[str, Any]]:
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.lookup_func(name)
        return None

    def lookup_class(self, name: str) -> Optional[Dict[str, Any]]:
        if name in self.classes:
            return self.classes[name]
        if self.parent:
            return self.parent.lookup_class(name)
        return None

    def get_this(self) -> Optional[FlowObject]:
        if self.this_obj is not None:
            return self.this_obj
        if self.parent:
            return self.parent.get_this()
        return None


def _to_flow_str(v: Any) -> str:
    """Flow tilida qiymatni string ko'rinishga o'tkazish."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, FlowObject):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_to_flow_str(e) for e in v) + "]"
    return str(v)


def resolve_property(obj: Any, prop_name: str) -> Any:
    """Obyekt turiga qarab (FlowObject, String, List, Int, Float) property qiymatini aniqlaydi."""
    if isinstance(obj, FlowObject):
        try:
            return obj.get_field(prop_name)
        except AttributeError:
            method = obj.get_method(prop_name)
            if method:
                return {"__bound_method__": True, "obj": obj, "method": method}
            raise AttributeError(f"'{obj.class_name}' ob'ektida '{prop_name}' topilmadi")

    from src.stdlib import get_builtin_property, has_builtin_method
    if isinstance(obj, (str, list)):
        if prop_name == "length":
            return get_builtin_property(obj, prop_name)
        if has_builtin_method(obj, prop_name):
            return {"__bound_builtin_method__": True, "obj": obj, "method": prop_name}
        raise AttributeError(f"'{type(obj).__name__}' ob'ektida '{prop_name}' topilmadi")

    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if has_builtin_method(obj, prop_name):
            return {"__bound_builtin_method__": True, "obj": obj, "method": prop_name}
        t_name = "Float" if isinstance(obj, float) else "Int"
        raise AttributeError(f"{t_name} ob'ektida '{prop_name}' topilmadi")

    raise TypeError(f"'{type(obj).__name__}' tipida property murojaat mumkin emas")


import sys
import pickle
import zlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from src.compiler.opcodes import OpCode, FLOWC_MAGIC
from src.vm.memory import FlowObject, ExpiredVariableError, CallFrame, _to_flow_str, resolve_property
from src.stdlib import call_builtin_method, has_builtin_method, get_builtin_property


class VirtualMachine:
    def __init__(self):
        self.stack: List[Any] = []
        self.frames: List[CallFrame] = []
        self.global_vars: Dict[str, Any] = {}
        self.global_vals: Set[str] = set()
        self.global_live_vars: Dict[str, int] = {}
        self.global_expired_vars: Set[str] = set()
        self.global_funcs: Dict[str, Dict[str, Any]] = {}
        self.global_classes: Dict[str, Dict[str, Any]] = {}  # OOP

        # Standart built-in (stdlib) funksiyalar
        self.builtins = {
            "len": self._builtin_len,
            "str": self._builtin_str,
            "toInt": self._builtin_to_int,
            "input": self._builtin_input,
            "print": self._builtin_print,
            "type": self._builtin_type,
        }

    def _builtin_len(self, obj: Any) -> int:
        if isinstance(obj, (list, tuple, str, dict)):
            return len(obj)
        raise TypeError(f"'{type(obj).__name__}' tipidagi ob'ekt uchun len() mavjud emas")

    def _builtin_str(self, obj: Any) -> str:
        return _to_flow_str(obj)

    def _builtin_to_int(self, obj: Any) -> int:
        try:
            if isinstance(obj, str):
                return int(float(obj))
            return int(obj)
        except (ValueError, TypeError):
            raise ValueError(f"'{obj}' qiymatini Integer'ga o'girib bo'lmadi")

    def _builtin_input(self, prompt: Any = "") -> str:
        prompt_str = "" if prompt is None else str(prompt)
        sys.stdout.flush()
        return input(prompt_str)

    def _builtin_print(self, *args: Any) -> None:
        parts = [_to_flow_str(a) for a in args]
        print(" ".join(parts))

    def _builtin_type(self, obj: Any) -> str:
        if obj is None:
            return "Null"
        if isinstance(obj, bool):
            return "Boolean"
        if isinstance(obj, int):
            return "Int"
        if isinstance(obj, float):
            return "Float"
        if isinstance(obj, str):
            return "String"
        if isinstance(obj, list):
            return "Array"
        if isinstance(obj, FlowObject):
            return obj.class_name
        return type(obj).__name__

    def load_bytecode(self, filepath_or_data) -> Dict[str, Any]:
        if isinstance(filepath_or_data, (str, Path)):
            p = Path(filepath_or_data)
            if not p.exists():
                raise FileNotFoundError(f"Bytecode fayli topilmadi: {p}")

            raw_bytes = p.read_bytes()

            # Binary formatni tekshirish
            if raw_bytes.startswith(FLOWC_MAGIC):
                compressed = raw_bytes[len(FLOWC_MAGIC):]
                pickled = zlib.decompress(compressed)
                data = pickle.loads(pickled)
                return data

            # Eski JSON formati bilan moslik (backward compatibility)
            try:
                data = json.loads(raw_bytes.decode("utf-8"))
                if data.get("magic") == "FLOWC":
                    return data
            except Exception:
                pass

            raise ValueError("Noto'g'ri bayt-kod: FLOWC binary magic header topilmadi!")

        elif isinstance(filepath_or_data, dict):
            return filepath_or_data
        else:
            raise TypeError("Noto'g'ri bytecode formati")

    def run_bytecode(self, bytecode: Dict[str, Any]):
        instructions = bytecode.get("instructions", [])
        top_frame = CallFrame(name="<global>", code=instructions)
        self.frames.append(top_frame)

        while self.frames:
            current_frame = self.frames[-1]

            if current_frame.ip >= len(current_frame.code):
                self.frames.pop()
                continue

            instr = current_frame.code[current_frame.ip]
            current_frame.ip += 1

            op = instr.get("op")
            arg = instr.get("arg")
            line = instr.get("line", 1)

            try:
                self._execute_instruction(op, arg, current_frame, line)
            except Exception as e:
                self._report_runtime_error(e, line, current_frame)
                sys.exit(1)

    def _report_runtime_error(self, error: Exception, line: int, frame: CallFrame):
        RED = "\033[91m"
        BOLD = "\033[1m"
        RESET = "\033[0m"

        err_name = type(error).__name__
        err_msg = str(error)

        print(
            f"\n{RED}{BOLD}[Flow Runtime Error - Qator {line}]{RESET}: "
            f"{RED}{err_name}: {err_msg}{RESET}",
            file=sys.stderr
        )
        if frame.name != "<global>":
            print(f"  {RED}Joylashuv: funksiya '{frame.name}()'{RESET}", file=sys.stderr)

    def _execute_instruction(self, op: str, arg: Any, frame: CallFrame, line: int):
        if op == OpCode.PUSH_CONST:
            self.stack.append(arg)

        elif op == OpCode.PUSH_NULL:
            self.stack.append(None)

        elif op == OpCode.STORE_VAL:
            val_name = arg
            if not self.stack:
                raise RuntimeError(f"Evaluation stack bo'sh, '{val_name}' ga qiymat berib bo'lmadi")
            value = self.stack.pop()

            if frame.is_val(val_name) or val_name in self.global_vals:
                raise RuntimeError(f"Cannot mutate immutable 'val' variable '{val_name}'")

            frame.variables[val_name] = value
            frame.constants.add(val_name)

        elif op == OpCode.STORE_VAR:
            var_name = arg
            if not self.stack:
                raise RuntimeError(f"Evaluation stack bo'sh, '{var_name}' ga qiymat berib bo'lmadi")
            value = self.stack.pop()

            if frame.is_val(var_name) or var_name in self.global_vals:
                raise RuntimeError(f"Cannot mutate immutable 'val' variable '{var_name}'")

            if not frame.update_var(var_name, value):
                if var_name in self.global_vars:
                    self.global_vars[var_name] = value
                else:
                    frame.variables[var_name] = value

        elif op == OpCode.STORE_LIVE:
            var_name = arg["name"]
            limit = int(arg["limit"])
            if not self.stack:
                raise RuntimeError(f"Evaluation stack bo'sh, '{var_name}' ga qiymat berib bo'lmadi")
            value = self.stack.pop()

            if frame.is_val(var_name) or var_name in self.global_vals:
                raise RuntimeError(f"Cannot mutate immutable 'val' variable '{var_name}'")

            frame.expired_vars.discard(var_name)
            self.global_expired_vars.discard(var_name)

            frame.variables[var_name] = value
            frame.live_vars[var_name] = limit
            if frame.name == "<global>":
                self.global_vars[var_name] = value
                self.global_live_vars[var_name] = limit

        elif op == OpCode.LOAD_VAR:
            var_name = arg

            # Avval muddati tugaganligini tekshiramiz
            if frame.is_expired(var_name) or var_name in self.global_expired_vars:
                raise ExpiredVariableError(f"Live variable '{var_name}' has expired!")

            val = frame.lookup_var(var_name)

            if val is None and var_name not in frame.variables:
                if var_name in self.global_vars:
                    val = self.global_vars[var_name]
                else:
                    raise NameError(f"O'zgaruvchi topilmadi: '{var_name}'")

            # Live bo'lsa hisoblagichni kamaytiramiz va 0 bo'lsa o'chiramiz
            if not frame.access_live_var(var_name):
                if var_name in self.global_live_vars:
                    self.global_live_vars[var_name] -= 1
                    if self.global_live_vars[var_name] <= 0:
                        del self.global_live_vars[var_name]
                        if var_name in self.global_vars:
                            del self.global_vars[var_name]
                        self.global_expired_vars.add(var_name)

            self.stack.append(val)

        elif op == OpCode.CHECK_EXPIRED:
            var_name = arg
            if not var_name:
                self.stack.append(True)
            elif frame.is_expired(var_name) or var_name in self.global_expired_vars:
                self.stack.append(True)
            elif frame.has_var(var_name):
                counter = frame.get_live_counter(var_name)
                if counter is not None and counter <= 0:
                    self.stack.append(True)
                else:
                    self.stack.append(False)
            elif var_name in self.global_vars:
                counter = self.global_live_vars.get(var_name)
                if counter is not None and counter <= 0:
                    self.stack.append(True)
                else:
                    self.stack.append(False)
            else:
                # O'zgaruvchi topilmadi
                self.stack.append(True)

        elif op == OpCode.LOAD_THIS:
            this = frame.get_this()
            if this is None:
                raise RuntimeError("'this' kalit so'zi faqat klass metodlari ichida ishlatilishi mumkin")
            self.stack.append(this)

        # ==========================================
        # OOP OpCode'lar
        # ==========================================
        elif op == OpCode.DEF_CLASS:
            class_data = arg
            class_name = class_data["name"]
            frame.classes[class_name] = class_data
            if frame.name == "<global>":
                self.global_classes[class_name] = class_data

        elif op == OpCode.NEW_OBJ:
            class_name = arg["class_name"]
            arg_count = arg.get("arg_count", 0)
            named_arg_keys = arg.get("named_args", [])

            # Klass ta'rifini topish
            class_def = frame.lookup_class(class_name)
            if not class_def:
                class_def = self.global_classes.get(class_name)
            if not class_def:
                raise NameError(f"Klass topilmadi: '{class_name}'")

            # Stekdan named args ni olish (oxirgi push qilinganlar)
            named_arg_values = {}
            for key in reversed(named_arg_keys):
                named_arg_values[key] = self.stack.pop()

            # Stekdan positional args ni olish
            positional_args = []
            for _ in range(arg_count):
                positional_args.append(self.stack.pop())
            positional_args.reverse()

            # Field'larni to'ldirish
            fields_def = class_def.get("fields", [])
            fields: Dict[str, Any] = {}

            # Default qiymatlarni hisoblash
            field_defaults_code = class_def.get("field_defaults", {})
            for field_info in fields_def:
                fname = field_info["name"]
                if fname in field_defaults_code:
                    # Default qiymatni run-time da hisoblash
                    temp_vm = VirtualMachine()
                    temp_vm.global_vars = self.global_vars
                    temp_vm.global_funcs = self.global_funcs
                    temp_vm.global_classes = self.global_classes
                    default_bytecode = {"magic": "FLOWC", "instructions": field_defaults_code[fname]}
                    temp_vm.run_bytecode(default_bytecode)
                    fields[fname] = temp_vm.stack[-1] if temp_vm.stack else None
                else:
                    fields[fname] = None

            # Named args ni qo'llash
            for k, v in named_arg_values.items():
                fields[k] = v

            # Positional args ni field tartibiga ko'ra qo'llash
            for i, val in enumerate(positional_args):
                if i < len(fields_def):
                    fields[fields_def[i]["name"]] = val

            # FlowObject yaratish
            obj = FlowObject(class_name=class_name, fields=fields)
            obj._class_def = class_def
            self.stack.append(obj)

        elif op == OpCode.GET_PROP:
            prop_name = arg
            if not self.stack:
                raise RuntimeError("GET_PROP uchun stack bo'sh")
            obj = self.stack.pop()
            val = resolve_property(obj, prop_name)
            self.stack.append(val)


        elif op == OpCode.SET_PROP:
            prop_name = arg
            if len(self.stack) < 2:
                raise RuntimeError("SET_PROP uchun stekda yetarli qiymat yo'q")
            value = self.stack.pop()
            obj = self.stack.pop()

            if not isinstance(obj, FlowObject):
                raise TypeError(f"Property o'zgartirish faqat ob'ekt uchun mumkin")
            obj.set_field(prop_name, value)

        elif op == OpCode.CALL_METHOD:
            method_name = arg["method"]
            arg_count = arg.get("arg_count", 0)

            # Args ni stekdan olish
            args = []
            for _ in range(arg_count):
                args.append(self.stack.pop())
            args.reverse()

            # obj ni stekdan olish
            obj = self.stack.pop()

            if isinstance(obj, FlowObject):
                method_data = obj.get_method(method_name)
                if not method_data:
                    # Built-in FlowObject metodlari yoki xato
                    result = self._call_builtin_method(obj, method_name, args)
                    if result is not None:
                        self.stack.append(result)
                    return

                # Metod uchun yangi frame yaratish (this = obj)
                new_frame = CallFrame(
                    name=f"{obj.class_name}.{method_name}",
                    code=method_data["code"],
                    parent=frame,
                    this_obj=obj,
                )

                param_names = method_data.get("params", [])
                for p_name, val in zip(param_names, args):
                    new_frame.variables[p_name] = val

                self.frames.append(new_frame)
            else:
                # str, list va boshqa built-in tiplar uchun
                result = self._call_builtin_method(obj, method_name, args)
                if result is not None:
                    self.stack.append(result)

        # ==========================================
        # Arifmetik amallar & String konkatenatsiyasi
        # ==========================================
        elif op == OpCode.ADD:
            if len(self.stack) < 2:
                raise RuntimeError("ADD amali uchun stekda yetarli qiymat yo'q")
            b = self.stack.pop()
            a = self.stack.pop()

            if isinstance(a, str) or isinstance(b, str):
                self.stack.append(_to_flow_str(a) + _to_flow_str(b))
            else:
                self.stack.append(a + b)

        elif op == OpCode.SUB:
            if len(self.stack) < 2:
                raise RuntimeError("SUB amali uchun stekda yetarli qiymat yo'q")
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a - b)

        elif op == OpCode.MUL:
            if len(self.stack) < 2:
                raise RuntimeError("MUL amali uchun stekda yetarli qiymat yo'q")
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a * b)

        elif op == OpCode.DIV:
            if len(self.stack) < 2:
                raise RuntimeError("DIV amali uchun stekda yetarli qiymat yo'q")
            b = self.stack.pop()
            a = self.stack.pop()
            if b == 0:
                raise ZeroDivisionError("Nolga bo'lish xatosi (division by zero)")
            res = a / b if (isinstance(a, float) or isinstance(b, float) or a % b != 0) else a // b
            self.stack.append(res)

        elif op == OpCode.MOD:
            if len(self.stack) < 2:
                raise RuntimeError("MOD (%) amali uchun stekda yetarli qiymat yo'q")
            b = self.stack.pop()
            a = self.stack.pop()
            if b == 0:
                raise ZeroDivisionError("Nolga qoldiqli bo'lish xatosi (modulo by zero)")
            self.stack.append(a % b)

        # Taqqoslash amallari
        elif op == OpCode.GT:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a > b)

        elif op == OpCode.LT:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a < b)

        elif op == OpCode.GTE:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a >= b)

        elif op == OpCode.LTE:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a <= b)

        elif op == OpCode.EQ:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a == b)

        elif op == OpCode.NEQ:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(a != b)

        # Mantiqiy amallar
        elif op == OpCode.AND:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(bool(a and b))

        elif op == OpCode.OR:
            b = self.stack.pop()
            a = self.stack.pop()
            self.stack.append(bool(a or b))

        elif op == OpCode.NOT:
            a = self.stack.pop()
            self.stack.append(not a)

        # Massivlar va Kolleksiyalar
        elif op == OpCode.MAKE_ARRAY:
            count = arg
            elements = []
            for _ in range(count):
                elements.append(self.stack.pop())
            elements.reverse()
            self.stack.append(elements)

        elif op == OpCode.LOAD_INDEX:
            if len(self.stack) < 2:
                raise RuntimeError("LOAD_INDEX uchun stekda yetarli qiymat yo'q")
            idx = self.stack.pop()
            arr = self.stack.pop()
            if not isinstance(arr, (list, tuple, str)):
                raise TypeError(f"'{type(arr).__name__}' tipidagi ob'ekt indekslanmaydi")
            if not isinstance(idx, int):
                raise TypeError("Massiv indeksi butun son (Int) bo'lishi kerak")
            if idx < 0 or idx >= len(arr):
                raise IndexError(f"Massiv indeksi chegaradan tashqarida (Index {idx}, Hajm {len(arr)})")
            self.stack.append(arr[idx])

        elif op == OpCode.STORE_INDEX:
            array_name = arg
            if len(self.stack) < 2:
                raise RuntimeError("STORE_INDEX uchun stekda yetarli qiymat yo'q")
            idx = self.stack.pop()
            val = self.stack.pop()

            arr = frame.lookup_var(array_name)
            if arr is None:
                if array_name in self.global_vars:
                    arr = self.global_vars[array_name]
                else:
                    raise NameError(f"O'zgaruvchi topilmadi: '{array_name}'")

            if frame.is_val(array_name) or array_name in self.global_vals:
                raise RuntimeError(f"Cannot mutate immutable 'val' variable '{array_name}'")

            if not isinstance(arr, list):
                raise TypeError(f"'{type(arr).__name__}' massiv emas, indeksga yozib bo'lmaydi")
            if not isinstance(idx, int):
                raise TypeError("Massiv indeksi butun son (Int) bo'lishi kerak")
            if idx < 0 or idx >= len(arr):
                raise IndexError(f"Massiv indeksi chegaradan tashqarida (Index {idx}, Hajm {len(arr)})")

            arr[idx] = val

        elif op == OpCode.MAKE_RANGE:
            if len(self.stack) < 2:
                raise RuntimeError("MAKE_RANGE uchun stekda yetarli qiymat yo'q")
            end = self.stack.pop()
            start = self.stack.pop()
            self.stack.append(list(range(int(start), int(end))))

        elif op == OpCode.GET_LEN:
            if not self.stack:
                raise RuntimeError("GET_LEN uchun stekda qiymat yo'q")
            arr = self.stack.pop()
            self.stack.append(len(arr))

        # Control Flow
        elif op == OpCode.JUMP:
            frame.ip = arg

        elif op == OpCode.JUMP_IF_FALSE:
            if not self.stack:
                raise RuntimeError("JUMP_IF_FALSE uchun shart qiymati yo'q")
            cond = self.stack.pop()
            if not cond:
                frame.ip = arg

        elif op == OpCode.DEF_FUNC:
            func_data = arg
            func_name = func_data["name"]
            frame.functions[func_name] = func_data
            if frame.name == "<global>":
                self.global_funcs[func_name] = func_data

        elif op == OpCode.CALL_FUNC:
            func_name = arg["name"]
            arg_count = arg["arg_count"]
            is_pipeline = arg.get("pipeline", False)

            # Pipeline: arg_count da left qiymat ham kiritilgan (arg_count = extra_args + 1)
            # Stack holati: [left, extra_arg1, extra_arg2, ...]
            # Barchasini bir vaqtda olamiz
            if is_pipeline:
                # Stack: tepasida extra args, pastda left value
                # arg_count = len(right.args) + 1 (left ham kiritilgan)
                pass  # Hech narsa alohida qilmaymiz

            # 1. Foydalanuvchi funksiyasini qidirish
            func_data = frame.lookup_func(func_name)
            if not func_data:
                func_data = self.global_funcs.get(func_name)

            # 2. Agar foydalanuvchi funksiyasi topilmasa, Builtin (Stdlib) funksiyalaridan tekshirish
            if not func_data and func_name in self.builtins:
                if len(self.stack) < arg_count:
                    raise RuntimeError(f"'{func_name}' funksiyasi uchun argumentlar yetarli emas")
                args = []
                for _ in range(arg_count):
                    args.append(self.stack.pop())
                args.reverse()

                res = self.builtins[func_name](*args)
                if res is not None:
                    self.stack.append(res)
                return

            if not func_data:
                raise NameError(f"Funksiya aniqlanmagan: '{func_name}'")

            if len(self.stack) < arg_count:
                raise RuntimeError(f"'{func_name}' chaqiruvi uchun stekda yetarli argument yo'q")

            args = []
            for _ in range(arg_count):
                args.append(self.stack.pop())
            args.reverse()

            parent_frame = frame if func_data.get("is_inner") else None
            new_frame = CallFrame(
                name=func_name,
                code=func_data["code"],
                parent=parent_frame,
            )

            param_names = func_data.get("params", [])
            for p_name, val in zip(param_names, args):
                new_frame.variables[p_name] = val

            self.frames.append(new_frame)

        elif op == OpCode.RETURN:
            has_value = bool(arg)
            ret_val = self.stack.pop() if (has_value and self.stack) else None

            self.frames.pop()

            if has_value:
                self.stack.append(ret_val)

        elif op == OpCode.PRINT:
            if not self.stack:
                raise RuntimeError("PRINT uchun stekda qiymat yo'q")
            val = self.stack.pop()
            print(_to_flow_str(val))

        else:
            raise NotImplementedError(f"Noma'lum VM OpCode: {op}")

    def _call_builtin_method(self, obj: Any, method_name: str, args: List[Any]) -> Any:
        """Built-in metodlarni stdlib orqali chaqirish."""
        return call_builtin_method(obj, method_name, args)



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


def run_file(flowc_path: str):
    vm = VirtualMachine()
    bytecode = vm.load_bytecode(flowc_path)
    vm.run_bytecode(bytecode)

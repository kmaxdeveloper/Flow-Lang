from typing import Any, Dict, Optional


FLOWC_MAGIC = b"FLOWC\x01\x00"


class OpCode:
    PUSH_CONST = "PUSH_CONST"
    STORE_VAR = "STORE_VAR"
    STORE_LIVE = "STORE_LIVE"
    STORE_VAL = "STORE_VAL"
    LOAD_VAR = "LOAD_VAR"
    CHECK_EXPIRED = "CHECK_EXPIRED"
    DEF_FUNC = "DEF_FUNC"
    CALL_FUNC = "CALL_FUNC"
    RETURN = "RETURN"
    PRINT = "PRINT"

    # Arithmetic
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL"
    DIV = "DIV"
    MOD = "MOD"

    # Comparison
    GT = "GT"
    LT = "LT"
    GTE = "GTE"
    LTE = "LTE"
    EQ = "EQ"
    NEQ = "NEQ"

    # Logical
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

    # Control Flow
    JUMP = "JUMP"
    JUMP_IF_FALSE = "JUMP_IF_FALSE"

    # Arrays & Collections
    MAKE_ARRAY = "MAKE_ARRAY"
    LOAD_INDEX = "LOAD_INDEX"
    STORE_INDEX = "STORE_INDEX"
    MAKE_RANGE = "MAKE_RANGE"
    GET_LEN = "GET_LEN"

    # OOP
    DEF_CLASS = "DEF_CLASS"          # Klass ta'rifini ro'yxatdan o'tkazish
    NEW_OBJ = "NEW_OBJ"              # new ClassName(args...)
    GET_PROP = "GET_PROP"            # obj.field
    SET_PROP = "SET_PROP"            # obj.field = value
    CALL_METHOD = "CALL_METHOD"      # obj.method(args...)
    LOAD_THIS = "LOAD_THIS"          # this
    PUSH_NULL = "PUSH_NULL"          # null

    # Pipeline
    PIPELINE = "PIPELINE"            # |>


class Instruction:
    def __init__(self, op: str, arg: Any = None, line: int = 1):
        self.op = op
        self.arg = arg
        self.line = line

    def to_dict(self) -> Dict[str, Any]:
        data = {"op": self.op, "line": self.line}
        if self.arg is not None:
            data["arg"] = self.arg
        return data

    def __repr__(self) -> str:
        if self.arg is not None:
            return f"{self.op} {repr(self.arg)} (L{self.line})"
        return f"{self.op} (L{self.line})"

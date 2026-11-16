"""
Flow Language — Statik Tahlilchi (Static Analyzer)
==================================================
Kodni ishga tushirmasdan avval xato va ogohlantirishlarni aniqlaydi.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Set, Dict, Optional
from enum import Enum


class Severity(Enum):
    ERROR   = "error"
    WARNING = "warning"
    INFO    = "info"


@dataclass
class Diagnostic:
    """Bitta xato yoki ogohlantirish."""
    severity: Severity
    message: str
    line: int        # 1-indexed
    col_start: int   # 0-indexed (VS Code uchun)
    col_end: int     # 0-indexed (VS Code uchun)

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "message":  self.message,
            "line":     self.line,
            "colStart": self.col_start,
            "colEnd":   self.col_end,
        }

    def __str__(self) -> str:
        sev = self.severity.value.upper()
        return f"[{sev}] Qator {self.line}:{self.col_start} — {self.message}"


# ============================================================
# Scope — o'zgaruvchi/funksiya/klass kuzatuvchi
# ============================================================

class Scope:
    def __init__(self, parent: Optional["Scope"] = None, name: str = "<global>"):
        self.parent = parent
        self.name = name
        self.vars: Dict[str, int] = {}        # name -> line
        self.used_vars: Set[str] = set()
        self.functions: Set[str] = set()
        self.classes: Set[str] = set()

    def define_var(self, name: str, line: int):
        self.vars[name] = line

    def define_func(self, name: str):
        self.functions.add(name)

    def define_class(self, name: str):
        self.classes.add(name)

    def has_var(self, name: str) -> bool:
        if name in self.vars:
            return True
        if self.parent:
            return self.parent.has_var(name)
        return False

    def has_func(self, name: str) -> bool:
        if name in self.functions:
            return True
        if self.parent:
            return self.parent.has_func(name)
        return False

    def has_class(self, name: str) -> bool:
        if name in self.classes:
            return True
        if self.parent:
            return self.parent.has_class(name)
        return False

    def mark_used(self, name: str):
        if name in self.vars:
            self.used_vars.add(name)
        elif self.parent:
            self.parent.mark_used(name)

    def unused_vars(self) -> List[tuple]:
        """Ishlatilmagan o'zgaruvchilar: [(name, line), ...]"""
        result = []
        for name, line in self.vars.items():
            if name not in self.used_vars and not name.startswith("_"):
                result.append((name, line))
        return result

    def child(self, name: str = "<block>") -> "Scope":
        return Scope(parent=self, name=name)


# ============================================================
# Analyzer
# ============================================================

# Global built-in funksiyalar va o'zgaruvchilar
BUILTIN_FUNCTIONS = {
    "print", "len", "str", "toInt", "input", "type", "isExpired",
}

BUILTIN_STRING_METHODS = {
    "trim", "split", "replace", "contains", "startsWith", "endsWith",
    "upper", "lower", "length",
}

BUILTIN_NUMBER_METHODS = {
    "abs", "round", "ceil", "floor", "clamp",
}

BUILTIN_ARRAY_METHODS = {
    "pop", "contains", "join", "slice", "push", "length",
}

ALL_BUILTIN_METHODS = BUILTIN_STRING_METHODS | BUILTIN_NUMBER_METHODS | BUILTIN_ARRAY_METHODS

BUILTIN_VARS = set()



class Analyzer:
    def __init__(self):
        self.diagnostics: List[Diagnostic] = []
        self.global_scope = Scope(name="<global>")
        # Built-in funksiyalarni qo'shamiz
        for fn in BUILTIN_FUNCTIONS:
            self.global_scope.define_func(fn)

    # --------------------------------------------------------
    # Diagnostik yozish
    # --------------------------------------------------------
    def _error(self, msg: str, line: int, col_start: int = 0, col_end: int = 1):
        self.diagnostics.append(Diagnostic(Severity.ERROR, msg, line, col_start, col_end))

    def _warn(self, msg: str, line: int, col_start: int = 0, col_end: int = 1):
        self.diagnostics.append(Diagnostic(Severity.WARNING, msg, line, col_start, col_end))

    def _info(self, msg: str, line: int, col_start: int = 0, col_end: int = 1):
        self.diagnostics.append(Diagnostic(Severity.INFO, msg, line, col_start, col_end))

    # --------------------------------------------------------
    # Asosiy tahlil
    # --------------------------------------------------------
    def analyze(self, program) -> List[Diagnostic]:
        """Program AST'ni tahlil qilib, diagnostika ro'yxatini qaytaradi."""
        from src.parser.ast import (
            Program, FunctionDef, VarDecl, ValDecl, AssignStmt,
            IndexAssignStmt, SetPropertyStmt, ReturnStmt,
            IfStmt, WhileStmt, StepWhileStmt, ForInStmt, BinaryOp, UnaryOp,
            RangeExpr, ArrayLiteralExpr, IndexAccessExpr,
            CallExpr, ClassDeclStmt, NewExpr, GetPropertyExpr,
            MethodCallExpr, ThisExpr, NullLiteral, PipelineExpr,
            Identifier, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral,
            MatchExpr,
        )
        self._Program    = Program
        self._FunctionDef = FunctionDef
        self._VarDecl    = VarDecl
        self._ValDecl    = ValDecl
        self._AssignStmt = AssignStmt
        self._IndexAssignStmt = IndexAssignStmt
        self._SetPropertyStmt = SetPropertyStmt
        self._ReturnStmt = ReturnStmt
        self._IfStmt     = IfStmt
        self._WhileStmt  = WhileStmt
        self._StepWhileStmt = StepWhileStmt
        self._ForInStmt  = ForInStmt
        self._BinaryOp   = BinaryOp
        self._UnaryOp    = UnaryOp
        self._RangeExpr  = RangeExpr
        self._ArrayLiteralExpr = ArrayLiteralExpr
        self._IndexAccessExpr  = IndexAccessExpr
        self._CallExpr   = CallExpr
        self._ClassDeclStmt = ClassDeclStmt
        self._NewExpr    = NewExpr
        self._GetPropertyExpr = GetPropertyExpr
        self._MethodCallExpr  = MethodCallExpr
        self._ThisExpr   = ThisExpr
        self._NullLiteral     = NullLiteral
        self._PipelineExpr    = PipelineExpr
        self._Identifier = Identifier
        self._IntLiteral = IntLiteral
        self._FloatLiteral = FloatLiteral
        self._StringLiteral  = StringLiteral
        self._BoolLiteral    = BoolLiteral
        self._MatchExpr      = MatchExpr

        scope = self.global_scope

        # 1-o'tish: Barcha funksiya va klasslarni ro'yxatdan o'tkazish
        for stmt in program.statements:
            if isinstance(stmt, FunctionDef):
                scope.define_func(stmt.name)
            elif isinstance(stmt, ClassDeclStmt):
                scope.define_class(stmt.name)

        # 2-o'tish: To'liq tahlil
        for stmt in program.statements:
            self._analyze_stmt(stmt, scope)

        # 3-o'tish: Ishlatilmagan o'zgaruvchilar ogohlantirishlari (global scope)
        for name, line in scope.unused_vars():
            self._warn(
                f"O'zgaruvchi '{name}' e'lon qilindi lekin ishlatilmadi",
                line, 0, len(name)
            )

        return self.diagnostics

    # --------------------------------------------------------
    # Statement tahlili
    # --------------------------------------------------------
    def _analyze_stmt(self, stmt, scope: Scope):
        if isinstance(stmt, self._FunctionDef):
            self._analyze_function_def(stmt, scope)

        elif isinstance(stmt, self._ClassDeclStmt):
            self._analyze_class_decl(stmt, scope)

        elif isinstance(stmt, (self._VarDecl, self._ValDecl)):
            line = getattr(stmt, "line", 1)
            self._analyze_expr(stmt.value, scope)
            scope.define_var(stmt.name, line)

        elif isinstance(stmt, self._AssignStmt):
            line = getattr(stmt, "line", 1)
            self._analyze_expr(stmt.value, scope)
            if not scope.has_var(stmt.name):
                self._error(
                    f"Aniqlanmagan o'zgaruvchi: '{stmt.name}'",
                    line, 0, len(stmt.name)
                )
            else:
                scope.mark_used(stmt.name)

        elif isinstance(stmt, self._IndexAssignStmt):
            line = getattr(stmt, "line", 1)
            self._analyze_expr(stmt.index, scope)
            self._analyze_expr(stmt.value, scope)
            if not scope.has_var(stmt.array_name):
                self._error(
                    f"Aniqlanmagan massiv o'zgaruvchisi: '{stmt.array_name}'",
                    line, 0, len(stmt.array_name)
                )

        elif isinstance(stmt, self._SetPropertyStmt):
            self._analyze_expr(stmt.obj, scope)
            self._analyze_expr(stmt.value, scope)

        elif isinstance(stmt, self._ReturnStmt):
            if stmt.value is not None:
                self._analyze_expr(stmt.value, scope)

        elif isinstance(stmt, self._IfStmt):
            self._analyze_expr(stmt.condition, scope)
            child_scope = scope.child("if")
            for s in stmt.then_branch:
                self._analyze_stmt(s, child_scope)
            if stmt.elif_branches:
                for cond, body in stmt.elif_branches:
                    self._analyze_expr(cond, scope)
                    elif_scope = scope.child("elif")
                    for s in body:
                        self._analyze_stmt(s, elif_scope)
            if stmt.else_branch:
                else_scope = scope.child("else")
                for s in stmt.else_branch:
                    self._analyze_stmt(s, else_scope)

        elif isinstance(stmt, (self._WhileStmt, self._StepWhileStmt)):
            self._analyze_expr(stmt.condition, scope)
            child_scope = scope.child("while")
            for s in stmt.body:
                self._analyze_stmt(s, child_scope)

        elif isinstance(stmt, self._ForInStmt):
            line = getattr(stmt, "line", 1)
            self._analyze_expr(stmt.iterable, scope)
            child_scope = scope.child("for")
            child_scope.define_var(stmt.variable, line)
            child_scope.mark_used(stmt.variable)  # loop variable always used
            for s in stmt.body:
                self._analyze_stmt(s, child_scope)

        elif isinstance(stmt, (self._CallExpr, self._MethodCallExpr, self._PipelineExpr, self._MatchExpr)):
            self._analyze_expr(stmt, scope)

        else:
            # Noma'lum statement — expression sifatida tahlil
            try:
                self._analyze_expr(stmt, scope)
            except Exception:
                pass

    def _analyze_function_def(self, func: object, scope: Scope):
        func_scope = scope.child(f"fn:{func.name}")

        # Parametrlarni ro'yxatdan o'tkazish
        for param in func.params:
            func_scope.define_var(param.name, getattr(func, "line", 1))
            func_scope.mark_used(param.name)  # param har doim ishlatilgan hisoblanadi

        # Ichki funksiya va klasslarni avval ro'yxatdan o'tkazish
        for s in func.body:
            if isinstance(s, self._FunctionDef):
                func_scope.define_func(s.name)
            elif isinstance(s, self._ClassDeclStmt):
                func_scope.define_class(s.name)

        # Expression body
        if func.expr_body is not None:
            self._analyze_expr(func.expr_body, func_scope)
        else:
            for s in func.body:
                self._analyze_stmt(s, func_scope)

        # Ishlatilmagan o'zgaruvchilar (funksiya ichida)
        for name, line in func_scope.unused_vars():
            self._warn(
                f"O'zgaruvchi '{name}' e'lon qilindi lekin ishlatilmadi",
                line, 0, len(name)
            )

    def _analyze_class_decl(self, cls: object, scope: Scope):
        class_scope = scope.child(f"class:{cls.name}")

        # Constructor field'larini qo'shish
        for field_def in cls.constructor_fields:
            class_scope.define_var(field_def.name, getattr(cls, "line", 1))
            class_scope.mark_used(field_def.name)  # field'lar this. orqali ishlatiladi

        # Metodlarni tahlil qilish
        for method in cls.methods:
            method_scope = class_scope.child(f"method:{method.name}")
            # this va parametrlar
            for param in method.params:
                method_scope.define_var(param.name, getattr(method, "line", 1))
                method_scope.mark_used(param.name)

            if method.expr_body is not None:
                self._analyze_expr(method.expr_body, method_scope)
            else:
                for s in method.body:
                    self._analyze_stmt(s, method_scope)

    # --------------------------------------------------------
    # Expression tahlili
    # --------------------------------------------------------
    def _analyze_expr(self, expr, scope: Scope):
        if expr is None:
            return

        if isinstance(expr, (self._IntLiteral, self._FloatLiteral,
                              self._StringLiteral, self._BoolLiteral,
                              self._NullLiteral)):
            return

        elif isinstance(expr, self._Identifier):
            name = expr.name
            line = getattr(expr, "line", 1)
            if not scope.has_var(name) and not scope.has_func(name) and not scope.has_class(name):
                self._error(
                    f"Aniqlanmagan identifikator: '{name}'",
                    line, 0, len(name)
                )
            else:
                scope.mark_used(name)

        elif isinstance(expr, self._ThisExpr):
            pass  # this — har doim to'g'ri

        elif isinstance(expr, self._BinaryOp):
            self._analyze_expr(expr.left, scope)
            self._analyze_expr(expr.right, scope)

        elif isinstance(expr, self._UnaryOp):
            self._analyze_expr(expr.operand, scope)

        elif isinstance(expr, self._CallExpr):
            line = getattr(expr, "line", 1)
            callee = expr.callee
            if not scope.has_func(callee):
                self._error(
                    f"Aniqlanmagan funksiya: '{callee}'",
                    line, 0, len(callee)
                )
            for arg in expr.args:
                self._analyze_expr(arg, scope)

        elif isinstance(expr, self._MethodCallExpr):
            self._analyze_expr(expr.obj, scope)
            for arg in expr.args:
                self._analyze_expr(arg, scope)
            line = getattr(expr, "line", 1)
            method = expr.method_name
            # Literal ob'ektlar uchun metod mosligini tekshirish
            if isinstance(expr.obj, self._StringLiteral):
                if method not in BUILTIN_STRING_METHODS and method != "isExpired":
                    self._error(f"String turida '{method}' metodi mavjud emas", line)
            elif isinstance(expr.obj, (self._IntLiteral, self._FloatLiteral)):
                if method not in BUILTIN_NUMBER_METHODS and method != "isExpired":
                    self._error(f"Son (Number) turida '{method}' metodi mavjud emas", line)
            elif isinstance(expr.obj, self._ArrayLiteralExpr):
                if method not in BUILTIN_ARRAY_METHODS and method != "isExpired":
                    self._error(f"Massiv (Array) turida '{method}' metodi mavjud emas", line)

        elif isinstance(expr, self._GetPropertyExpr):
            self._analyze_expr(expr.obj, scope)
            line = getattr(expr, "line", 1)
            prop = expr.property_name
            if isinstance(expr.obj, (self._StringLiteral, self._ArrayLiteralExpr)):
                if prop != "length" and prop not in ALL_BUILTIN_METHODS:
                    self._error(f"'{prop}' xususiyati topilmadi", line)


        elif isinstance(expr, self._NewExpr):
            line = getattr(expr, "line", 1)
            if not scope.has_class(expr.class_name):
                self._error(
                    f"Aniqlanmagan klass: '{expr.class_name}'",
                    line, 0, len(expr.class_name)
                )
            for arg in expr.args:
                self._analyze_expr(arg, scope)
            for val in expr.named_args.values():
                self._analyze_expr(val, scope)

        elif isinstance(expr, self._PipelineExpr):
            self._analyze_expr(expr.left, scope)
            self._analyze_expr(expr.right, scope)

        elif isinstance(expr, self._ArrayLiteralExpr):
            for elem in expr.elements:
                self._analyze_expr(elem, scope)

        elif isinstance(expr, self._IndexAccessExpr):
            self._analyze_expr(expr.array, scope)
            self._analyze_expr(expr.index, scope)

        elif isinstance(expr, self._RangeExpr):
            self._analyze_expr(expr.start, scope)
            self._analyze_expr(expr.end, scope)

        elif isinstance(expr, self._MatchExpr):
            if expr.expr is not None:
                self._analyze_expr(expr.expr, scope)
            for pattern, result in expr.cases:
                self._analyze_expr(pattern, scope)
                self._analyze_expr(result, scope)
            if expr.default_case is not None:
                self._analyze_expr(expr.default_case, scope)

        else:
            # Noma'lum expression — o'tkazib yuboramiz
            pass


# ============================================================
# Qulaylik funksiyalari
# ============================================================

def analyze_source(source_code: str) -> List[Diagnostic]:
    """
    Manba kodni to'liq tahlil qiladi.
    Lexer, Parser va Analyzer xatolarini ham qaytaradi.
    """
    diagnostics: List[Diagnostic] = []

    # 1. Lexer xatolari
    try:
        from src.lexer.lexer import Lexer
        tokens = Lexer(source_code).tokenize()
    except SyntaxError as e:
        msg = str(e)
        line = _extract_line(msg)
        diagnostics.append(Diagnostic(Severity.ERROR, f"Leksik xato: {msg}", line, 0, 1))
        return diagnostics

    # 2. Parser xatolari
    try:
        from src.parser.parser import Parser
        ast = Parser(tokens).parse()
    except SyntaxError as e:
        msg = str(e)
        line = _extract_line(msg)
        col = _extract_col(msg)
        diagnostics.append(Diagnostic(Severity.ERROR, f"Sintaksis xatosi: {msg}", line, col, col + 1))
        return diagnostics

    # 3. Semantic analyzer
    try:
        analyzer = Analyzer()
        diagnostics.extend(analyzer.analyze(ast))
    except Exception as e:
        diagnostics.append(Diagnostic(Severity.ERROR, f"Tahlil xatosi: {e}", 1, 0, 1))

    return diagnostics


def analyze_file(filepath: str) -> List[Diagnostic]:
    """Fayl yo'li bo'yicha tahlil qiladi."""
    from pathlib import Path
    try:
        source = Path(filepath).read_text(encoding="utf-8")
        return analyze_source(source)
    except FileNotFoundError:
        return [Diagnostic(Severity.ERROR, f"Fayl topilmadi: {filepath}", 1, 0, 1)]
    except Exception as e:
        return [Diagnostic(Severity.ERROR, f"Fayl o'qishda xato: {e}", 1, 0, 1)]


def _extract_line(msg: str) -> int:
    """Xato xabaridan qator raqamini chiqarish."""
    import re
    m = re.search(r'\[(\d+):', msg) or re.search(r'qator\s+(\d+)', msg, re.I)
    if m:
        return int(m.group(1))
    return 1


def _extract_col(msg: str) -> int:
    """Xato xabaridan ustun raqamini chiqarish."""
    import re
    m = re.search(r':\s*(\d+)\]', msg)
    if m:
        return int(m.group(1))
    return 0


# ============================================================
# CLI: --check rejimi (extension.js tomonidan chaqiriladi)
# ============================================================

def main_check(filepath: str):
    """
    `flow --check file.flw` uchun JSON formatida diagnostika chiqaradi.
    VS Code extension.js bu chiqishni parse qiladi.
    """
    import json
    diags = analyze_file(filepath)
    output = [d.to_dict() for d in diags]
    print(json.dumps(output, ensure_ascii=False))

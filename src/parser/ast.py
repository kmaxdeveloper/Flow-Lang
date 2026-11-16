from typing import List, Optional, Any


# ==========================================
# AST (Abstract Syntax Tree) Tugunlari
# ==========================================

class ASTNode:
    """Barcha AST tugunlari uchun asosiy sinf."""
    line: int = 1

    def to_dict(self) -> dict:
        raise NotImplementedError


class Program(ASTNode):
    def __init__(self, statements: List[ASTNode]):
        self.statements = statements

    def to_dict(self) -> dict:
        return {
            "type": "Program",
            "body": [stmt.to_dict() for stmt in self.statements]
        }

    def __repr__(self) -> str:
        return f"Program(body={self.statements})"


class Param(ASTNode):
    def __init__(self, name: str, type_name: str, default_value: Optional[ASTNode] = None):
        self.name = name
        self.type_name = type_name
        self.default_value = default_value

    def to_dict(self) -> dict:
        return {
            "type": "Param",
            "name": self.name,
            "param_type": self.type_name,
            "default_value": self.default_value.to_dict() if self.default_value else None
        }

    def __repr__(self) -> str:
        dv = f" = {self.default_value}" if self.default_value else ""
        return f"Param({self.name}: {self.type_name}{dv})"


class FunctionDef(ASTNode):
    def __init__(
        self,
        name: str,
        params: List[Param],
        return_type: Optional[str],
        body: List[ASTNode],
        is_inner: bool = False,
        expr_body: Optional[ASTNode] = None,  # => expression body
    ):
        self.name = name
        self.params = params
        self.return_type = return_type
        self.body = body
        self.is_inner = is_inner
        self.expr_body = expr_body

    def to_dict(self) -> dict:
        return {
            "type": "FunctionDef",
            "name": self.name,
            "is_inner": self.is_inner,
            "params": [p.to_dict() for p in self.params],
            "return_type": self.return_type,
            "body": [stmt.to_dict() for stmt in self.body],
            "expr_body": self.expr_body.to_dict() if self.expr_body else None,
        }

    def __repr__(self) -> str:
        inner_prefix = "inner " if self.is_inner else ""
        return (
            f"{inner_prefix}FunctionDef({self.name}, params={self.params}, "
            f"return_type={self.return_type}, body={self.body})"
        )


# ==========================================
# OOP AST Tugunlari
# ==========================================

class ClassField(ASTNode):
    """Klass maydoni: var name: String = 'default'"""
    def __init__(self, name: str, type_name: Optional[str], default_value: Optional[ASTNode] = None, is_mutable: bool = True):
        self.name = name
        self.type_name = type_name
        self.default_value = default_value
        self.is_mutable = is_mutable

    def to_dict(self) -> dict:
        return {
            "type": "ClassField",
            "name": self.name,
            "field_type": self.type_name,
            "default_value": self.default_value.to_dict() if self.default_value else None,
            "is_mutable": self.is_mutable,
        }

    def __repr__(self) -> str:
        return f"ClassField({'var' if self.is_mutable else 'val'} {self.name}: {self.type_name})"


class ClassDeclStmt(ASTNode):
    """Klass e'loni: class User(var name: String, var age: Int = 18) { ... }"""
    def __init__(self, name: str, constructor_fields: List[ClassField], methods: List[FunctionDef]):
        self.name = name
        self.constructor_fields = constructor_fields
        self.methods = methods

    def to_dict(self) -> dict:
        return {
            "type": "ClassDeclStmt",
            "name": self.name,
            "constructor_fields": [f.to_dict() for f in self.constructor_fields],
            "methods": [m.to_dict() for m in self.methods],
        }

    def __repr__(self) -> str:
        return f"ClassDeclStmt({self.name})"


class NewExpr(ASTNode):
    """Yangi obyekt yaratish: new User(name = 'Ali', age = 22) yoki User('Ali', 22)"""
    def __init__(self, class_name: str, args: List[ASTNode], named_args: Optional[dict] = None):
        self.class_name = class_name
        self.args = args
        self.named_args = named_args or {}

    def to_dict(self) -> dict:
        return {
            "type": "NewExpr",
            "class_name": self.class_name,
            "args": [a.to_dict() for a in self.args],
            "named_args": {k: v.to_dict() for k, v in self.named_args.items()},
        }

    def __repr__(self) -> str:
        return f"NewExpr({self.class_name}(...))"


class GetPropertyExpr(ASTNode):
    """Maydon/metod murojaat: user.name, user.greet()"""
    def __init__(self, obj: ASTNode, property_name: str):
        self.obj = obj
        self.property_name = property_name

    def to_dict(self) -> dict:
        return {
            "type": "GetPropertyExpr",
            "obj": self.obj.to_dict(),
            "property": self.property_name,
        }

    def __repr__(self) -> str:
        return f"GetPropertyExpr({self.obj}.{self.property_name})"


class SetPropertyStmt(ASTNode):
    """Maydon qiymatini o'zgartirish: user.name = 'Vali'"""
    def __init__(self, obj: ASTNode, property_name: str, value: ASTNode):
        self.obj = obj
        self.property_name = property_name
        self.value = value

    def to_dict(self) -> dict:
        return {
            "type": "SetPropertyStmt",
            "obj": self.obj.to_dict(),
            "property": self.property_name,
            "value": self.value.to_dict(),
        }

    def __repr__(self) -> str:
        return f"SetPropertyStmt({self.obj}.{self.property_name} = {self.value})"


class MethodCallExpr(ASTNode):
    """Metod chaqiruvi: user.greet() yoki user.getName()"""
    def __init__(self, obj: ASTNode, method_name: str, args: List[ASTNode]):
        self.obj = obj
        self.method_name = method_name
        self.args = args

    def to_dict(self) -> dict:
        return {
            "type": "MethodCallExpr",
            "obj": self.obj.to_dict(),
            "method": self.method_name,
            "args": [a.to_dict() for a in self.args],
        }

    def __repr__(self) -> str:
        return f"MethodCallExpr({self.obj}.{self.method_name}(...))"


class ThisExpr(ASTNode):
    """this kalit so'zi"""
    def to_dict(self) -> dict:
        return {"type": "ThisExpr"}

    def __repr__(self) -> str:
        return "ThisExpr()"


class NullLiteral(ASTNode):
    """null qiymati"""
    def to_dict(self) -> dict:
        return {"type": "NullLiteral"}

    def __repr__(self) -> str:
        return "NullLiteral()"


class PipelineExpr(ASTNode):
    """|> pipeline operator: x |> square() |> print()"""
    def __init__(self, left: ASTNode, right: ASTNode):
        self.left = left
        self.right = right

    def to_dict(self) -> dict:
        return {
            "type": "PipelineExpr",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }

    def __repr__(self) -> str:
        return f"PipelineExpr({self.left} |> {self.right})"


# ==========================================
# Existing AST nodes
# ==========================================

class VarDecl(ASTNode):
    def __init__(
        self,
        name: str,
        value: ASTNode,
        type_annotation: Optional[str] = None,
        is_live: bool = False,
        life_limit: Optional[int] = None,
    ):
        self.name = name
        self.value = value
        self.type_annotation = type_annotation
        self.is_live = is_live
        self.life_limit = life_limit

    def to_dict(self) -> dict:
        return {
            "type": "VarDecl",
            "name": self.name,
            "type_annotation": self.type_annotation,
            "value": self.value.to_dict() if self.value else None,
            "is_live": self.is_live,
            "life_limit": self.life_limit,
        }

    def __repr__(self) -> str:
        type_str = f": {self.type_annotation}" if self.type_annotation else ""
        live_str = f"live[{self.life_limit}] " if self.is_live else ""
        return f"{live_str}VarDecl({self.name}{type_str} = {self.value})"


VarDeclStmt = VarDecl


class ValDecl(ASTNode):
    def __init__(self, name: str, value: ASTNode, type_annotation: Optional[str] = None):
        self.name = name
        self.value = value
        self.type_annotation = type_annotation

    def to_dict(self) -> dict:
        return {
            "type": "ValDecl",
            "name": self.name,
            "type_annotation": self.type_annotation,
            "value": self.value.to_dict() if self.value else None
        }

    def __repr__(self) -> str:
        type_str = f": {self.type_annotation}" if self.type_annotation else ""
        return f"ValDecl({self.name}{type_str} = {self.value})"


class AssignStmt(ASTNode):
    def __init__(self, name: str, value: ASTNode, op: str = "="):
        self.name = name
        self.value = value
        self.op = op

    def to_dict(self) -> dict:
        return {
            "type": "AssignStmt",
            "name": self.name,
            "op": self.op,
            "value": self.value.to_dict()
        }

    def __repr__(self) -> str:
        return f"AssignStmt({self.name} {self.op} {self.value})"


class IndexAssignStmt(ASTNode):
    """Massiv elementiga qiymat berish: numbers[1] = 99"""
    def __init__(self, array_name: str, index: ASTNode, value: ASTNode):
        self.array_name = array_name
        self.index = index
        self.value = value

    def to_dict(self) -> dict:
        return {
            "type": "IndexAssignStmt",
            "array_name": self.array_name,
            "index": self.index.to_dict(),
            "value": self.value.to_dict()
        }

    def __repr__(self) -> str:
        return f"IndexAssignStmt({self.array_name}[{self.index}] = {self.value})"


class SetPropertyStmt(ASTNode):
    """Maydon qiymatini o'zgartirish: user.name = 'Vali'"""
    def __init__(self, obj: ASTNode, property_name: str, value: ASTNode):
        self.obj = obj
        self.property_name = property_name
        self.value = value

    def to_dict(self) -> dict:
        return {
            "type": "SetPropertyStmt",
            "obj": self.obj.to_dict(),
            "property": self.property_name,
            "value": self.value.to_dict(),
        }

    def __repr__(self) -> str:
        return f"SetPropertyStmt({self.obj}.{self.property_name} = {self.value})"


class ReturnStmt(ASTNode):
    def __init__(self, value: Optional[ASTNode]):
        self.value = value

    def to_dict(self) -> dict:
        return {
            "type": "ReturnStmt",
            "value": self.value.to_dict() if self.value else None
        }

    def __repr__(self) -> str:
        return f"ReturnStmt({self.value})"


class IfStmt(ASTNode):
    def __init__(self, condition: ASTNode, then_branch: List[ASTNode], elif_branches: Optional[List] = None, else_branch: Optional[List[ASTNode]] = None):
        self.condition = condition
        self.then_branch = then_branch
        self.elif_branches = elif_branches or []  # List of (condition, body) tuples
        self.else_branch = else_branch

    def to_dict(self) -> dict:
        return {
            "type": "IfStmt",
            "condition": self.condition.to_dict(),
            "then_branch": [s.to_dict() for s in self.then_branch],
            "elif_branches": [
                {"condition": cond.to_dict(), "body": [s.to_dict() for s in body]}
                for cond, body in self.elif_branches
            ],
            "else_branch": [s.to_dict() for s in self.else_branch] if self.else_branch else None
        }

    def __repr__(self) -> str:
        return f"IfStmt(condition={self.condition}, then={self.then_branch}, elif={self.elif_branches}, else={self.else_branch})"


class MatchExpr(ASTNode):
    """match ifodasi: match (expr) { val => expr, ..., else => expr } yoki match { cond => expr, ..., else => expr }"""
    def __init__(self, expr: Optional[ASTNode], cases: List, default_case: Optional[ASTNode] = None):
        self.expr = expr
        self.cases = cases
        self.default_case = default_case

    def to_dict(self) -> dict:
        return {
            "type": "MatchExpr",
            "expr": self.expr.to_dict() if self.expr else None,
            "cases": [
                {"pattern": cond.to_dict(), "result": res.to_dict()}
                for cond, res in self.cases
            ],
            "default_case": self.default_case.to_dict() if self.default_case else None,
        }

    def __repr__(self) -> str:
        return f"MatchExpr(expr={self.expr}, cases={self.cases}, default={self.default_case})"


class StepWhileStmt(ASTNode):
    """step[N] while (cond) { body }"""
    def __init__(self, limit: int, condition: ASTNode, body: List[ASTNode]):
        self.limit = limit
        self.condition = condition
        self.body = body

    def to_dict(self) -> dict:
        return {
            "type": "StepWhileStmt",
            "limit": self.limit,
            "condition": self.condition.to_dict(),
            "body": [s.to_dict() for s in self.body]
        }

    def __repr__(self) -> str:
        return f"StepWhileStmt(step[{self.limit}], condition={self.condition}, body={self.body})"


class WhileStmt(ASTNode):
    def __init__(self, condition: ASTNode, body: List[ASTNode]):
        self.condition = condition
        self.body = body

    def to_dict(self) -> dict:
        return {
            "type": "WhileStmt",
            "condition": self.condition.to_dict(),
            "body": [s.to_dict() for s in self.body]
        }

    def __repr__(self) -> str:
        return f"WhileStmt(condition={self.condition}, body={self.body})"


class ForInStmt(ASTNode):
    """for (i in 0..3) { ... } yoki for (item in numbers) { ... }"""
    def __init__(self, variable: str, iterable: ASTNode, body: List[ASTNode]):
        self.variable = variable
        self.iterable = iterable
        self.body = body

    def to_dict(self) -> dict:
        return {
            "type": "ForInStmt",
            "variable": self.variable,
            "iterable": self.iterable.to_dict(),
            "body": [s.to_dict() for s in self.body]
        }

    def __repr__(self) -> str:
        return f"ForInStmt({self.variable} in {self.iterable}, body={self.body})"


class BinaryOp(ASTNode):
    def __init__(self, left: ASTNode, op: str, right: ASTNode):
        self.left = left
        self.op = op
        self.right = right

    def to_dict(self) -> dict:
        return {
            "type": "BinaryOp",
            "op": self.op,
            "left": self.left.to_dict(),
            "right": self.right.to_dict()
        }

    def __repr__(self) -> str:
        return f"BinaryOp({self.left} {self.op} {self.right})"


class UnaryOp(ASTNode):
    def __init__(self, op: str, operand: ASTNode):
        self.op = op
        self.operand = operand

    def to_dict(self) -> dict:
        return {
            "type": "UnaryOp",
            "op": self.op,
            "operand": self.operand.to_dict()
        }

    def __repr__(self) -> str:
        return f"UnaryOp({self.op}{self.operand})"


class RangeExpr(ASTNode):
    """Diapazon ifodasi: 0..3"""
    def __init__(self, start: ASTNode, end: ASTNode):
        self.start = start
        self.end = end

    def to_dict(self) -> dict:
        return {
            "type": "RangeExpr",
            "start": self.start.to_dict(),
            "end": self.end.to_dict()
        }

    def __repr__(self) -> str:
        return f"RangeExpr({self.start}..{self.end})"


class ArrayLiteralExpr(ASTNode):
    """Massiv literali: [10, 20, 30]"""
    def __init__(self, elements: List[ASTNode]):
        self.elements = elements

    def to_dict(self) -> dict:
        return {
            "type": "ArrayLiteralExpr",
            "elements": [e.to_dict() for e in self.elements]
        }

    def __repr__(self) -> str:
        return f"ArrayLiteralExpr({self.elements})"


class IndexAccessExpr(ASTNode):
    """Massiv indeksiga murojaat: numbers[0]"""
    def __init__(self, array: ASTNode, index: ASTNode):
        self.array = array
        self.index = index

    def to_dict(self) -> dict:
        return {
            "type": "IndexAccessExpr",
            "array": self.array.to_dict(),
            "index": self.index.to_dict()
        }

    def __repr__(self) -> str:
        return f"IndexAccessExpr({self.array}[{self.index}])"


class CallExpr(ASTNode):
    def __init__(self, callee: str, args: List[ASTNode]):
        self.callee = callee
        self.args = args

    def to_dict(self) -> dict:
        return {
            "type": "CallExpr",
            "callee": self.callee,
            "args": [a.to_dict() for a in self.args]
        }

    def __repr__(self) -> str:
        return f"CallExpr({self.callee}({', '.join(repr(a) for a in self.args)}))"


class Identifier(ASTNode):
    def __init__(self, name: str):
        self.name = name

    def to_dict(self) -> dict:
        return {
            "type": "Identifier",
            "name": self.name
        }

    def __repr__(self) -> str:
        return f"Identifier('{self.name}')"


class IntLiteral(ASTNode):
    def __init__(self, value: int):
        self.value = value

    def to_dict(self) -> dict:
        return {
            "type": "IntLiteral",
            "value": self.value
        }

    def __repr__(self) -> str:
        return f"IntLiteral({self.value})"


class FloatLiteral(ASTNode):
    def __init__(self, value: str):
        self.value = value

    def to_dict(self) -> dict:
        return {
            "type": "FloatLiteral",
            "value": self.value
        }

    def __repr__(self) -> str:
        return f"FloatLiteral({self.value})"


class StringLiteral(ASTNode):
    def __init__(self, value: str):
        self.value = value

    def to_dict(self) -> dict:
        return {
            "type": "StringLiteral",
            "value": self.value
        }

    def __repr__(self) -> str:
        return f"StringLiteral({repr(self.value)})"


class BoolLiteral(ASTNode):
    def __init__(self, value: bool):
        self.value = value

    def to_dict(self) -> dict:
        return {
            "type": "BoolLiteral",
            "value": self.value
        }

    def __repr__(self) -> str:
        return f"BoolLiteral({self.value})"

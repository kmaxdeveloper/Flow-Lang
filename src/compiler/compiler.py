import pickle
import zlib
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.compiler.opcodes import OpCode, Instruction, FLOWC_MAGIC
from src.parser.ast import (
    ASTNode,
    Program,
    FunctionDef,
    VarDecl,
    VarDeclStmt,
    ValDecl,
    AssignStmt,
    IndexAssignStmt,
    SetPropertyStmt,
    ReturnStmt,
    IfStmt,
    WhileStmt,
    StepWhileStmt,
    ForInStmt,
    BinaryOp,
    UnaryOp,
    RangeExpr,
    ArrayLiteralExpr,
    IndexAccessExpr,
    CallExpr,
    ClassDeclStmt,
    ClassField,
    NewExpr,
    GetPropertyExpr,
    MethodCallExpr,
    ThisExpr,
    NullLiteral,
    PipelineExpr,
    MatchExpr,
    Identifier,
    IntLiteral,
    FloatLiteral,
    StringLiteral,
    BoolLiteral,
)


class Compiler:
    def __init__(self):
        self.instructions: List[Instruction] = []
        self._temp_counter = 0
        self.current_line = 1

    def emit(self, op: str, arg: Any = None, line: Optional[int] = None) -> int:
        idx = len(self.instructions)
        target_line = line if line is not None else self.current_line
        self.instructions.append(Instruction(op, arg, target_line))
        return idx

    def _next_temp(self) -> int:
        self._temp_counter += 1
        return self._temp_counter

    def compile(self, program: Program) -> Dict[str, Any]:
        has_main = False

        for stmt in program.statements:
            if isinstance(stmt, FunctionDef) and stmt.name == "main":
                has_main = True
            self._compile_statement(stmt)

        # Agar main() funksiyasi mavjud bo'lsa, uni ishga tushirish ko'rsatmasini qo'shamiz
        if has_main:
            self.emit(OpCode.CALL_FUNC, {"name": "main", "arg_count": 0}, line=1)

        bytecode_data = {
            "magic": "FLOWC",
            "version": 2,
            "instructions": [ins.to_dict() for ins in self.instructions],
        }
        return bytecode_data

    def _compile_statement(self, stmt: ASTNode):
        if hasattr(stmt, "line") and stmt.line:
            self.current_line = stmt.line

        if isinstance(stmt, ClassDeclStmt):
            self._compile_class_decl(stmt)

        elif isinstance(stmt, FunctionDef):
            inner_compiler = Compiler()
            inner_compiler.current_line = getattr(stmt, "line", 1)

            # Expression body: fn isAdult(): Boolean => this.age >= 18
            if stmt.expr_body is not None:
                inner_compiler._compile_expression(stmt.expr_body)
                inner_compiler.emit(OpCode.RETURN, True, line=getattr(stmt, "line", 1))
            else:
                for s in stmt.body:
                    inner_compiler._compile_statement(s)
                if not inner_compiler.instructions or inner_compiler.instructions[-1].op != OpCode.RETURN:
                    inner_compiler.emit(OpCode.RETURN, False, line=getattr(stmt, "line", 1))

            func_data = {
                "name": stmt.name,
                "params": [p.name for p in stmt.params],
                "defaults": {p.name: None for p in stmt.params if p.default_value is None},
                "code": [ins.to_dict() for ins in inner_compiler.instructions],
                "is_inner": stmt.is_inner,
            }
            self.emit(OpCode.DEF_FUNC, func_data, line=getattr(stmt, "line", 1))

        elif isinstance(stmt, VarDecl):
            line = getattr(stmt, "line", self.current_line)
            self._compile_expression(stmt.value)
            if getattr(stmt, "is_live", False):
                limit = getattr(stmt, "life_limit", 3) or 3
                self.emit(OpCode.STORE_LIVE, {"name": stmt.name, "limit": limit}, line=line)
            else:
                self.emit(OpCode.STORE_VAR, stmt.name, line=line)

        elif isinstance(stmt, ValDecl):
            self._compile_expression(stmt.value)
            self.emit(OpCode.STORE_VAL, stmt.name, line=getattr(stmt, "line", self.current_line))

        elif isinstance(stmt, AssignStmt):
            line = getattr(stmt, "line", self.current_line)
            if stmt.op == "=":
                self._compile_expression(stmt.value)
                self.emit(OpCode.STORE_VAR, stmt.name, line=line)
            elif stmt.op == "+=":
                self.emit(OpCode.LOAD_VAR, stmt.name, line=line)
                self._compile_expression(stmt.value)
                self.emit(OpCode.ADD, line=line)
                self.emit(OpCode.STORE_VAR, stmt.name, line=line)
            elif stmt.op == "-=":
                self.emit(OpCode.LOAD_VAR, stmt.name, line=line)
                self._compile_expression(stmt.value)
                self.emit(OpCode.SUB, line=line)
                self.emit(OpCode.STORE_VAR, stmt.name, line=line)
            elif stmt.op == "*=":
                self.emit(OpCode.LOAD_VAR, stmt.name, line=line)
                self._compile_expression(stmt.value)
                self.emit(OpCode.MUL, line=line)
                self.emit(OpCode.STORE_VAR, stmt.name, line=line)
            elif stmt.op == "/=":
                self.emit(OpCode.LOAD_VAR, stmt.name, line=line)
                self._compile_expression(stmt.value)
                self.emit(OpCode.DIV, line=line)
                self.emit(OpCode.STORE_VAR, stmt.name, line=line)
            else:
                raise NotImplementedError(f"Qo'llab-quvvatlanmagan o'zlashtirish operatori: {stmt.op}")

        elif isinstance(stmt, IndexAssignStmt):
            line = getattr(stmt, "line", self.current_line)
            self._compile_expression(stmt.value)
            self._compile_expression(stmt.index)
            self.emit(OpCode.STORE_INDEX, stmt.array_name, line=line)

        elif isinstance(stmt, SetPropertyStmt):
            line = getattr(stmt, "line", self.current_line)
            # Stack: [obj, value]
            self._compile_expression(stmt.obj)
            self._compile_expression(stmt.value)
            self.emit(OpCode.SET_PROP, stmt.property_name, line=line)

        elif isinstance(stmt, ReturnStmt):
            line = getattr(stmt, "line", self.current_line)
            if stmt.value is not None:
                self._compile_expression(stmt.value)
                self.emit(OpCode.RETURN, True, line=line)
            else:
                self.emit(OpCode.RETURN, False, line=line)

        elif isinstance(stmt, IfStmt):
            line = getattr(stmt, "line", self.current_line)
            self._compile_expression(stmt.condition)
            jump_false_idx = self.emit(OpCode.JUMP_IF_FALSE, None, line=line)

            for s in stmt.then_branch:
                self._compile_statement(s)

            if stmt.elif_branches or stmt.else_branch:
                # JUMP past all elif/else from the end of then_branch
                jump_exit_indices = [self.emit(OpCode.JUMP, None, line=line)]
                # Patch jump_false to point to first elif (or else)
                self.instructions[jump_false_idx].arg = len(self.instructions)

                for elif_cond, elif_body in stmt.elif_branches:
                    self._compile_expression(elif_cond)
                    elif_false_idx = self.emit(OpCode.JUMP_IF_FALSE, None, line=line)

                    for s in elif_body:
                        self._compile_statement(s)

                    jump_exit_indices.append(self.emit(OpCode.JUMP, None, line=line))
                    self.instructions[elif_false_idx].arg = len(self.instructions)

                if stmt.else_branch:
                    for s in stmt.else_branch:
                        self._compile_statement(s)

                exit_ip = len(self.instructions)
                for idx in jump_exit_indices:
                    self.instructions[idx].arg = exit_ip
            else:
                exit_ip = len(self.instructions)
                self.instructions[jump_false_idx].arg = exit_ip

        elif isinstance(stmt, WhileStmt):
            line = getattr(stmt, "line", self.current_line)
            loop_start_ip = len(self.instructions)
            self._compile_expression(stmt.condition)
            jump_false_idx = self.emit(OpCode.JUMP_IF_FALSE, None, line=line)

            for s in stmt.body:
                self._compile_statement(s)

            self.emit(OpCode.JUMP, loop_start_ip, line=line)
            exit_ip = len(self.instructions)
            self.instructions[jump_false_idx].arg = exit_ip

        elif isinstance(stmt, StepWhileStmt):
            line = getattr(stmt, "line", self.current_line)
            counter_var = f"__step_cnt_{self._next_temp()}"

            # 1. __step_cnt = 0
            self.emit(OpCode.PUSH_CONST, 0, line=line)
            self.emit(OpCode.STORE_VAR, counter_var, line=line)

            # 2. Sikl boshlanish joyi
            loop_start_ip = len(self.instructions)

            # 3. Step limiti: if __step_cnt >= limit: break
            self.emit(OpCode.LOAD_VAR, counter_var, line=line)
            self.emit(OpCode.PUSH_CONST, stmt.limit, line=line)
            self.emit(OpCode.LT, line=line)
            jump_limit_exit = self.emit(OpCode.JUMP_IF_FALSE, None, line=line)

            # 4. Asosiy shart: while (condition)
            self._compile_expression(stmt.condition)
            jump_cond_exit = self.emit(OpCode.JUMP_IF_FALSE, None, line=line)

            # 5. Hisoblagichni oshirish: __step_cnt += 1
            self.emit(OpCode.LOAD_VAR, counter_var, line=line)
            self.emit(OpCode.PUSH_CONST, 1, line=line)
            self.emit(OpCode.ADD, line=line)
            self.emit(OpCode.STORE_VAR, counter_var, line=line)

            # 6. Body statementlari
            for s in stmt.body:
                self._compile_statement(s)

            # 7. Sikl boshiga sakrash
            self.emit(OpCode.JUMP, loop_start_ip, line=line)

            # 8. Chiqish nuqtalarini patch qilish
            exit_ip = len(self.instructions)
            self.instructions[jump_limit_exit].arg = exit_ip
            self.instructions[jump_cond_exit].arg = exit_ip

        elif isinstance(stmt, ForInStmt):
            line = getattr(stmt, "line", self.current_line)
            t_id = self._next_temp()
            iter_var = f"__iter_{t_id}"
            idx_var = f"__idx_{t_id}"

            # 1. Iterable ni hisoblab saqlash
            self._compile_expression(stmt.iterable)
            self.emit(OpCode.STORE_VAR, iter_var, line=line)

            # 2. Indeksni 0 dan boshlash
            self.emit(OpCode.PUSH_CONST, 0, line=line)
            self.emit(OpCode.STORE_VAR, idx_var, line=line)

            # 3. Sikl sharti: idx < len(iter)
            loop_start_ip = len(self.instructions)
            self.emit(OpCode.LOAD_VAR, idx_var, line=line)
            self.emit(OpCode.LOAD_VAR, iter_var, line=line)
            self.emit(OpCode.GET_LEN, line=line)
            self.emit(OpCode.LT, line=line)
            jump_false_idx = self.emit(OpCode.JUMP_IF_FALSE, None, line=line)

            # 4. Elementni olish: var = iter[idx]
            self.emit(OpCode.LOAD_VAR, iter_var, line=line)
            self.emit(OpCode.LOAD_VAR, idx_var, line=line)
            self.emit(OpCode.LOAD_INDEX, line=line)
            self.emit(OpCode.STORE_VAR, stmt.variable, line=line)

            # 5. Tana (body) ni bajarish
            for s in stmt.body:
                self._compile_statement(s)

            # 6. Indeksni oshirish: idx += 1
            self.emit(OpCode.LOAD_VAR, idx_var, line=line)
            self.emit(OpCode.PUSH_CONST, 1, line=line)
            self.emit(OpCode.ADD, line=line)
            self.emit(OpCode.STORE_VAR, idx_var, line=line)

            # 7. Boshiga qaytish
            self.emit(OpCode.JUMP, loop_start_ip, line=line)
            exit_ip = len(self.instructions)
            self.instructions[jump_false_idx].arg = exit_ip

        else:
            # Barcha ifodalar (CallExpr, PipelineExpr, MatchExpr, StringLiteral, BinaryOp va h.k.)
            self._compile_expression(stmt)

    def _compile_class_decl(self, stmt: ClassDeclStmt):
        """Klass ta'rifini DEF_CLASS opcode sifatida saqlash."""
        line = getattr(stmt, "line", self.current_line)

        methods_data = []
        for method in stmt.methods:
            method_compiler = Compiler()
            method_compiler.current_line = getattr(method, "line", 1)

            if method.expr_body is not None:
                method_compiler._compile_expression(method.expr_body)
                method_compiler.emit(OpCode.RETURN, True, line=getattr(method, "line", 1))
            else:
                for s in method.body:
                    method_compiler._compile_statement(s)
                if not method_compiler.instructions or method_compiler.instructions[-1].op != OpCode.RETURN:
                    method_compiler.emit(OpCode.RETURN, False, line=getattr(method, "line", 1))

            methods_data.append({
                "name": method.name,
                "params": [p.name for p in method.params],
                "code": [ins.to_dict() for ins in method_compiler.instructions],
                "is_inner": method.is_inner,
            })

        class_data = {
            "name": stmt.name,
            "fields": [
                {
                    "name": f.name,
                    "type": f.type_name,
                    "is_mutable": f.is_mutable,
                    "has_default": f.default_value is not None,
                }
                for f in stmt.constructor_fields
            ],
            "field_defaults": {},  # default qiymatlar run-time da hisoblanadi
            "methods": methods_data,
        }

        # Default qiymatlarni bytecode sifatida saqlash
        for f in stmt.constructor_fields:
            if f.default_value is not None:
                default_compiler = Compiler()
                default_compiler._compile_expression(f.default_value)
                class_data["field_defaults"][f.name] = [ins.to_dict() for ins in default_compiler.instructions]

        self.emit(OpCode.DEF_CLASS, class_data, line=line)

    def _compile_expression(self, expr: ASTNode):
        line = getattr(expr, "line", self.current_line)

        if isinstance(expr, NullLiteral):
            self.emit(OpCode.PUSH_NULL, line=line)

        elif isinstance(expr, IntLiteral):
            self.emit(OpCode.PUSH_CONST, expr.value, line=line)

        elif isinstance(expr, FloatLiteral):
            clean_val = expr.value.rstrip("fF")
            try:
                num = float(clean_val)
            except ValueError:
                num = 0.0
            self.emit(OpCode.PUSH_CONST, num, line=line)

        elif isinstance(expr, StringLiteral):
            self.emit(OpCode.PUSH_CONST, expr.value, line=line)

        elif isinstance(expr, BoolLiteral):
            self.emit(OpCode.PUSH_CONST, expr.value, line=line)

        elif isinstance(expr, Identifier):
            self.emit(OpCode.LOAD_VAR, expr.name, line=line)

        elif isinstance(expr, ThisExpr):
            self.emit(OpCode.LOAD_THIS, line=line)

        elif isinstance(expr, ArrayLiteralExpr):
            for elem in expr.elements:
                self._compile_expression(elem)
            self.emit(OpCode.MAKE_ARRAY, len(expr.elements), line=line)

        elif isinstance(expr, IndexAccessExpr):
            self._compile_expression(expr.array)
            self._compile_expression(expr.index)
            self.emit(OpCode.LOAD_INDEX, line=line)

        elif isinstance(expr, RangeExpr):
            self._compile_expression(expr.start)
            self._compile_expression(expr.end)
            self.emit(OpCode.MAKE_RANGE, line=line)

        elif isinstance(expr, UnaryOp):
            line = getattr(expr, "line", self.current_line)
            if expr.op == "-":
                self.emit(OpCode.PUSH_CONST, 0, line=line)
                self._compile_expression(expr.operand)
                self.emit(OpCode.SUB, line=line)
            elif expr.op == "!":
                self._compile_expression(expr.operand)
                self.emit(OpCode.NOT, line=line)
            else:
                raise NotImplementedError(f"Qo'llab-quvvatlanmagan unar operator: {expr.op}")

        elif isinstance(expr, BinaryOp):
            self._compile_expression(expr.left)
            self._compile_expression(expr.right)

            op_map = {
                "+": OpCode.ADD,
                "-": OpCode.SUB,
                "*": OpCode.MUL,
                "/": OpCode.DIV,
                "%": OpCode.MOD,
                ">": OpCode.GT,
                "<": OpCode.LT,
                ">=": OpCode.GTE,
                "<=": OpCode.LTE,
                "==": OpCode.EQ,
                "!=": OpCode.NEQ,
                "&&": OpCode.AND,
                "||": OpCode.OR,
            }

            if expr.op in op_map:
                self.emit(op_map[expr.op], line=line)
            else:
                raise NotImplementedError(f"Qo'llab-quvvatlanmagan operator: {expr.op}")

        elif isinstance(expr, NewExpr):
            # Positional args - stack ga push
            for arg in expr.args:
                self._compile_expression(arg)
            # Named args
            for val in expr.named_args.values():
                self._compile_expression(val)
            # NEW_OBJ arglarni o'zida o'qiydi
            self.emit(OpCode.NEW_OBJ, {
                "class_name": expr.class_name,
                "arg_count": len(expr.args),
                "named_args": list(expr.named_args.keys()),
            }, line=line)

        elif isinstance(expr, GetPropertyExpr):
            self._compile_expression(expr.obj)
            self.emit(OpCode.GET_PROP, expr.property_name, line=line)

        elif isinstance(expr, MethodCallExpr):
            if expr.method_name == "isExpired":
                var_name = expr.obj.name if isinstance(expr.obj, Identifier) else None
                self.emit(OpCode.CHECK_EXPIRED, var_name, line=line)
                return
            self._compile_expression(expr.obj)
            for arg in expr.args:
                self._compile_expression(arg)
            self.emit(OpCode.CALL_METHOD, {
                "method": expr.method_name,
                "arg_count": len(expr.args),
            }, line=line)

        elif isinstance(expr, PipelineExpr):
            right = expr.right
            if isinstance(right, CallExpr) and right.callee == "isExpired":
                var_name = expr.left.name if isinstance(expr.left, Identifier) else None
                self.emit(OpCode.CHECK_EXPIRED, var_name, line=line)
                return
            if isinstance(right, MethodCallExpr) and right.method_name == "isExpired":
                var_name = expr.left.name if isinstance(expr.left, Identifier) else None
                self.emit(OpCode.CHECK_EXPIRED, var_name, line=line)
                return

            # x |> f() -> f(x)
            # Stack ga avval left push qilamiz, keyin right ni chaqiramiz
            self._compile_expression(expr.left)
            right = expr.right

            if isinstance(right, CallExpr):
                # Avvalgi argumentlarni push
                for arg in right.args:
                    self._compile_expression(arg)
                # left argument birinchi bo'lib stack da edi
                # CALL_FUNC da arg_count + 1 beramiz
                self.emit(OpCode.CALL_FUNC, {
                    "name": right.callee,
                    "arg_count": len(right.args) + 1,
                    "pipeline": True,
                }, line=line)
            elif isinstance(right, MethodCallExpr):
                # obj |> method() - bu holda obj ning o'zi qoladi
                self._compile_expression(right.obj)
                for arg in right.args:
                    self._compile_expression(arg)
                self.emit(OpCode.CALL_METHOD, {
                    "method": right.method_name,
                    "arg_count": len(right.args),
                    "pipeline": True,
                }, line=line)
            else:
                raise NotImplementedError(f"|> o'ng tarafida faqat funksiya chaqiruvi bo'lishi kerak")

        elif isinstance(expr, MatchExpr):
            # match (expr) { pattern => result, ..., else => default }
            # yoki match { cond => result, ..., else => default }
            line = getattr(expr, "line", self.current_line)
            jump_exit_indices = []

            if expr.expr is not None:
                # Target ifodani bir marta hisoblab, vaqtinchalik o'zgaruvchiga saqlaymiz
                tmp_var = f"__match_val_{self._next_temp()}"
                self._compile_expression(expr.expr)
                self.emit(OpCode.STORE_VAR, tmp_var, line=line)

                for pattern, result in expr.cases:
                    self.emit(OpCode.LOAD_VAR, tmp_var, line=line)
                    self._compile_expression(pattern)
                    self.emit(OpCode.EQ, line=line)
                    false_idx = self.emit(OpCode.JUMP_IF_FALSE, None, line=line)
                    self._compile_expression(result)
                    jump_exit_indices.append(self.emit(OpCode.JUMP, None, line=line))
                    self.instructions[false_idx].arg = len(self.instructions)
            else:
                for cond, result in expr.cases:
                    self._compile_expression(cond)
                    false_idx = self.emit(OpCode.JUMP_IF_FALSE, None, line=line)
                    self._compile_expression(result)
                    jump_exit_indices.append(self.emit(OpCode.JUMP, None, line=line))
                    self.instructions[false_idx].arg = len(self.instructions)

            # default case (else =>)
            if expr.default_case is not None:
                self._compile_expression(expr.default_case)
            else:
                self.emit(OpCode.PUSH_NULL, line=line)

            exit_ip = len(self.instructions)
            for idx in jump_exit_indices:
                self.instructions[idx].arg = exit_ip

        elif isinstance(expr, CallExpr):
            self._compile_call_expr(expr)

        else:
            raise NotImplementedError(f"Kompilyatsiya qilinmagan ifoda: {type(expr).__name__}")

    def _compile_call_expr(self, call: CallExpr):
        line = getattr(call, "line", self.current_line)
        if call.callee == "isExpired":
            var_name = call.args[0].name if (call.args and isinstance(call.args[0], Identifier)) else None
            self.emit(OpCode.CHECK_EXPIRED, var_name, line=line)
            return

        if call.callee == "print":
            for arg in call.args:
                self._compile_expression(arg)
                self.emit(OpCode.PRINT, line=line)
            return

        for arg in call.args:
            self._compile_expression(arg)

        self.emit(OpCode.CALL_FUNC, {
            "name": call.callee,
            "arg_count": len(call.args)
        }, line=line)


def serialize_bytecode(bytecode: Dict[str, Any]) -> bytes:
    """Bayt-kodni zlib orqali siqilgan ikkilik (binary) formatga o'tkazish."""
    pickled = pickle.dumps(bytecode, protocol=pickle.HIGHEST_PROTOCOL)
    compressed = zlib.compress(pickled, level=9)
    return FLOWC_MAGIC + compressed


def compile_file(source_path: str, output_path: Optional[str] = None) -> str:
    """Manba kodni kompilatsiya qilib, build/ papkasiga binary .flowc qilib saqlaydi."""
    from src.lexer import Lexer
    from src.parser import Parser

    src_p = Path(source_path)
    if not src_p.exists():
        raise FileNotFoundError(f"Fayl topilmadi: {source_path}")

    source_code = src_p.read_text(encoding="utf-8")
    tokens = Lexer(source_code).tokenize()
    ast = Parser(tokens).parse()

    compiler = Compiler()
    bytecode = compiler.compile(ast)

    if output_path is None:
        build_dir = Path("build")
        build_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(build_dir / f"{src_p.stem}.flowc")
    else:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

    binary_data = serialize_bytecode(bytecode)
    Path(output_path).write_bytes(binary_data)

    return output_path

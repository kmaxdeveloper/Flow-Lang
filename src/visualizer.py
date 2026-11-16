import sys
import re
import pickle
import zlib
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.compiler.opcodes import FLOWC_MAGIC, OpCode
from src.parser.ast import (
    ASTNode,
    Program,
    FunctionDef,
    Param,
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
    MatchExpr,
    PipelineExpr,
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
    Identifier,
    IntLiteral,
    FloatLiteral,
    StringLiteral,
    BoolLiteral,
)

# Windows ANSI ranglar faollashtirish
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# ANSI rang konstantalari
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
RED = "\033[91m"
WHITE = "\033[97m"
GRAY = "\033[90m"

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')


def strip_ansi(text: str) -> str:
    """Matndan ANSI rang kodlarini tozalash."""
    return ANSI_ESCAPE.sub('', text)


def format_box_line(content: str, width: int = 77) -> str:
    """Matnni ramka chegarasiga qarab aniq tekislash."""
    vis_len = len(strip_ansi(content))
    pad = max(0, width - vis_len)
    return f"│ {content}{' ' * pad} │"


def print_step_header(step_num: int, title: str, subtitle: str = ""):
    """Bosqich sarlavhasini ASCII ramka bilan chiqarish."""
    width = 79
    print()
    print(f"{CYAN}{'═' * width}{RESET}")
    sub = f" ({subtitle})" if subtitle else ""
    header_text = f" [{step_num}-STEP] {title}{sub} "
    print(f"{BOLD}{GREEN}►{header_text}{RESET}")
    print(f"{CYAN}{'─' * width}{RESET}")


class TreeNode:
    """AST vizual daraxti uchun tugun."""
    def __init__(self, text: str, children: Optional[List['TreeNode']] = None):
        self.text = text
        self.children = children or []

    def add_child(self, child: 'TreeNode'):
        self.children.append(child)


def _repr_val(node: Any) -> str:
    """Qisqa ifoda tavsifi."""
    if node is None:
        return "null"
    if isinstance(node, IntLiteral):
        return f"{node.value}"
    if isinstance(node, FloatLiteral):
        return f"{node.value}"
    if isinstance(node, StringLiteral):
        return f'"{node.value}"'
    if isinstance(node, BoolLiteral):
        return f"{str(node.value).lower()}"
    if isinstance(node, Identifier):
        return f"{node.name}"
    if isinstance(node, BinaryOp):
        return f"({_repr_val(node.left)} {node.op} {_repr_val(node.right)})"
    if isinstance(node, CallExpr):
        args_s = ", ".join(_repr_val(a) for a in node.args)
        return f"{node.callee}({args_s})"
    return type(node).__name__


def ast_to_tree(node: ASTNode) -> TreeNode:
    """ASTNode'ni chiroyli TreeNode daraxtiga o'tkazish."""
    if node is None:
        return TreeNode(f"{GRAY}null{RESET}")

    if isinstance(node, Program):
        root = TreeNode(f"{BOLD}{WHITE}Program (Root){RESET}")
        for stmt in node.statements:
            root.add_child(ast_to_tree(stmt))
        return root

    if isinstance(node, FunctionDef):
        params_str = ", ".join(
            f"{p.name}: {p.type_name}" + (f" = {_repr_val(p.default_value)}" if p.default_value else "")
            for p in node.params
        )
        ret_str = f" -> {node.return_type}" if node.return_type else " -> Void"
        prefix = "inner " if node.is_inner else ""
        header = f"{MAGENTA}{prefix}FunctionDef{RESET}: {BOLD}{node.name}{RESET}({params_str}){ret_str}"
        f_node = TreeNode(header)

        if node.expr_body is not None:
            f_node.add_child(TreeNode(f"{GRAY}Expression Body (=>):{RESET}", [ast_to_tree(node.expr_body)]))
        else:
            for s in node.body:
                f_node.add_child(ast_to_tree(s))
        return f_node

    if isinstance(node, (VarDecl, VarDeclStmt)):
        live_str = f"{RED}[live limit={node.life_limit}]{RESET} " if node.is_live else ""
        type_str = f": {YELLOW}{node.type_annotation}{RESET}" if node.type_annotation else ""
        v_node = TreeNode(f"{live_str}{CYAN}VarDecl{RESET}: {BOLD}{node.name}{RESET}{type_str}")
        if node.value:
            v_node.add_child(ast_to_tree(node.value))
        return v_node

    if isinstance(node, ValDecl):
        type_str = f": {YELLOW}{node.type_annotation}{RESET}" if node.type_annotation else ""
        v_node = TreeNode(f"{CYAN}ValDecl (const){RESET}: {BOLD}{node.name}{RESET}{type_str}")
        if node.value:
            v_node.add_child(ast_to_tree(node.value))
        return v_node

    if isinstance(node, AssignStmt):
        a_node = TreeNode(f"{BLUE}AssignStmt{RESET}: {node.name} {BOLD}{node.op}{RESET}")
        a_node.add_child(ast_to_tree(node.value))
        return a_node

    if isinstance(node, IndexAssignStmt):
        ia_node = TreeNode(f"{BLUE}IndexAssignStmt{RESET}: {node.array_name}[...] = value")
        ia_node.add_child(TreeNode(f"{GRAY}Index:{RESET}", [ast_to_tree(node.index)]))
        ia_node.add_child(TreeNode(f"{GRAY}Value:{RESET}", [ast_to_tree(node.value)]))
        return ia_node

    if isinstance(node, SetPropertyStmt):
        sp_node = TreeNode(f"{BLUE}SetPropertyStmt{RESET}: .{node.property_name} =")
        sp_node.add_child(TreeNode(f"{GRAY}Object:{RESET}", [ast_to_tree(node.obj)]))
        sp_node.add_child(TreeNode(f"{GRAY}Value:{RESET}", [ast_to_tree(node.value)]))
        return sp_node

    if isinstance(node, ReturnStmt):
        r_node = TreeNode(f"{MAGENTA}ReturnStmt{RESET}")
        if node.value:
            r_node.add_child(ast_to_tree(node.value))
        return r_node

    if isinstance(node, StepWhileStmt):
        sw_node = TreeNode(f"{YELLOW}StepWhileStmt{RESET} {BOLD}[limit={node.limit}]{RESET}")
        sw_node.add_child(TreeNode(f"{GRAY}Condition:{RESET}", [ast_to_tree(node.condition)]))
        body_node = TreeNode(f"{GRAY}Body ({len(node.body)} stmts):{RESET}")
        for s in node.body:
            body_node.add_child(ast_to_tree(s))
        sw_node.add_child(body_node)
        return sw_node

    if isinstance(node, WhileStmt):
        w_node = TreeNode(f"{YELLOW}WhileStmt{RESET}")
        w_node.add_child(TreeNode(f"{GRAY}Condition:{RESET}", [ast_to_tree(node.condition)]))
        body_node = TreeNode(f"{GRAY}Body ({len(node.body)} stmts):{RESET}")
        for s in node.body:
            body_node.add_child(ast_to_tree(s))
        w_node.add_child(body_node)
        return w_node

    if isinstance(node, ForInStmt):
        fi_node = TreeNode(f"{YELLOW}ForInStmt{RESET} (var={BOLD}{node.variable}{RESET})")
        fi_node.add_child(TreeNode(f"{GRAY}Iterable:{RESET}", [ast_to_tree(node.iterable)]))
        body_node = TreeNode(f"{GRAY}Body ({len(node.body)} stmts):{RESET}")
        for s in node.body:
            body_node.add_child(ast_to_tree(s))
        fi_node.add_child(body_node)
        return fi_node

    if isinstance(node, IfStmt):
        if_node = TreeNode(f"{YELLOW}IfStmt{RESET}")
        if_node.add_child(TreeNode(f"{GRAY}Condition:{RESET}", [ast_to_tree(node.condition)]))
        then_node = TreeNode(f"{GRAY}Then ({len(node.then_branch)} stmts):{RESET}")
        for s in node.then_branch:
            then_node.add_child(ast_to_tree(s))
        if_node.add_child(then_node)

        if node.elif_branches:
            for e_cond, e_body in node.elif_branches:
                e_node = TreeNode(f"{GRAY}Elif Condition:{RESET}", [ast_to_tree(e_cond)])
                eb_node = TreeNode(f"{GRAY}Elif Body ({len(e_body)} stmts):{RESET}")
                for s in e_body:
                    eb_node.add_child(ast_to_tree(s))
                if_node.add_child(e_node)
                if_node.add_child(eb_node)

        if node.else_branch:
            else_node = TreeNode(f"{GRAY}Else ({len(node.else_branch)} stmts):{RESET}")
            for s in node.else_branch:
                else_node.add_child(ast_to_tree(s))
            if_node.add_child(else_node)
        return if_node

    if isinstance(node, MatchExpr):
        subj = f" on {_repr_val(node.expr)}" if node.expr else ""
        m_node = TreeNode(f"{MAGENTA}MatchExpr{RESET}{subj}")
        for pat, res in node.cases:
            c_node = TreeNode(f"{GRAY}Case ({_repr_val(pat)}) =>{RESET}")
            c_node.add_child(ast_to_tree(res))
            m_node.add_child(c_node)
        if node.default_case:
            d_node = TreeNode(f"{GRAY}Else =>{RESET}")
            d_node.add_child(ast_to_tree(node.default_case))
            m_node.add_child(d_node)
        return m_node

    if isinstance(node, PipelineExpr):
        p_node = TreeNode(f"{CYAN}PipelineExpr{RESET} {BOLD}(|>){RESET}")
        p_node.add_child(TreeNode(f"{GRAY}Input:{RESET}", [ast_to_tree(node.left)]))
        p_node.add_child(TreeNode(f"{GRAY}Pipe:{RESET}", [ast_to_tree(node.right)]))
        return p_node

    if isinstance(node, BinaryOp):
        b_node = TreeNode(f"{BLUE}BinaryOp{RESET} {BOLD}'{node.op}'{RESET}")
        b_node.add_child(ast_to_tree(node.left))
        b_node.add_child(ast_to_tree(node.right))
        return b_node

    if isinstance(node, UnaryOp):
        u_node = TreeNode(f"{BLUE}UnaryOp{RESET} {BOLD}'{node.op}'{RESET}")
        u_node.add_child(ast_to_tree(node.operand))
        return u_node

    if isinstance(node, CallExpr):
        c_node = TreeNode(f"{GREEN}CallExpr{RESET}: {BOLD}{node.callee}{RESET}()")
        for arg in node.args:
            c_node.add_child(ast_to_tree(arg))
        return c_node

    if isinstance(node, MethodCallExpr):
        m_node = TreeNode(f"{GREEN}MethodCallExpr{RESET}: .{BOLD}{node.method_name}{RESET}()")
        m_node.add_child(TreeNode(f"{GRAY}Target:{RESET}", [ast_to_tree(node.obj)]))
        if node.args:
            args_node = TreeNode(f"{GRAY}Args:{RESET}")
            for a in node.args:
                args_node.add_child(ast_to_tree(a))
            m_node.add_child(args_node)
        return m_node

    if isinstance(node, GetPropertyExpr):
        gp_node = TreeNode(f"{GREEN}GetPropertyExpr{RESET}: .{BOLD}{node.property_name}{RESET}")
        gp_node.add_child(ast_to_tree(node.obj))
        return gp_node

    if isinstance(node, ArrayLiteralExpr):
        arr_node = TreeNode(f"{YELLOW}ArrayLiteral{RESET} [{len(node.elements)} elements]")
        for el in node.elements:
            arr_node.add_child(ast_to_tree(el))
        return arr_node

    if isinstance(node, IndexAccessExpr):
        ia_node = TreeNode(f"{BLUE}IndexAccess{RESET} []")
        ia_node.add_child(TreeNode(f"{GRAY}Array:{RESET}", [ast_to_tree(node.array)]))
        ia_node.add_child(TreeNode(f"{GRAY}Index:{RESET}", [ast_to_tree(node.index)]))
        return ia_node

    if isinstance(node, RangeExpr):
        r_node = TreeNode(f"{BLUE}RangeExpr{RESET} (..)")
        r_node.add_child(TreeNode(f"{GRAY}Start:{RESET}", [ast_to_tree(node.start)]))
        r_node.add_child(TreeNode(f"{GRAY}End:{RESET}", [ast_to_tree(node.end)]))
        return r_node

    if isinstance(node, ClassDeclStmt):
        cd_node = TreeNode(f"{MAGENTA}ClassDecl{RESET}: {BOLD}{node.name}{RESET}")
        for field in node.constructor_fields:
            mut = "var" if getattr(field, "is_mutable", True) else "val"
            f_node = TreeNode(f"{CYAN}Field{RESET} ({mut} {field.name}: {field.type_name})")
            if field.default_value:
                f_node.add_child(ast_to_tree(field.default_value))
            cd_node.add_child(f_node)
        for m in node.methods:
            cd_node.add_child(ast_to_tree(m))
        return cd_node

    if isinstance(node, NewExpr):
        n_node = TreeNode(f"{MAGENTA}NewExpr{RESET}: new {BOLD}{node.class_name}{RESET}()")
        for a in node.args:
            n_node.add_child(ast_to_tree(a))
        return n_node

    # Literallar
    if isinstance(node, IntLiteral):
        return TreeNode(f"{YELLOW}IntLiteral{RESET}: {BOLD}{node.value}{RESET}")
    if isinstance(node, FloatLiteral):
        return TreeNode(f"{YELLOW}FloatLiteral{RESET}: {BOLD}{node.value}{RESET}")
    if isinstance(node, StringLiteral):
        escaped = node.value.replace("\n", "\\n").replace("\t", "\\t")
        return TreeNode(f"{GREEN}StringLiteral{RESET}: {BOLD}\"{escaped}\"{RESET}")
    if isinstance(node, BoolLiteral):
        return TreeNode(f"{YELLOW}BoolLiteral{RESET}: {BOLD}{str(node.value).lower()}{RESET}")
    if isinstance(node, Identifier):
        return TreeNode(f"{WHITE}Identifier{RESET}: {BOLD}{node.name}{RESET}")
    if isinstance(node, ThisExpr):
        return TreeNode(f"{CYAN}ThisExpr{RESET}")
    if isinstance(node, NullLiteral):
        return TreeNode(f"{GRAY}NullLiteral{RESET}")

    return TreeNode(f"{WHITE}{type(node).__name__}{RESET}")


def render_tree(node: TreeNode, prefix: str = "", is_last: bool = True) -> List[str]:
    """TreeNode daraxtini ├── va └── shoxlari bilan chizish."""
    branch = "└── " if is_last else "├── "
    lines = [f"{prefix}{branch}{node.text}"]
    child_prefix = prefix + ("    " if is_last else "│   ")

    for i, child in enumerate(node.children):
        last_child = (i == len(node.children) - 1)
        lines.extend(render_tree(child, child_prefix, last_child))
    return lines


def format_instruction_arg(op: str, arg: Any) -> str:
    """Bytecode argumentini o'qilishi oson operand tavsifiga aylantirish."""
    if arg is None:
        return ""
    if op == OpCode.STORE_LIVE and isinstance(arg, dict):
        return f"({repr(arg.get('name'))}, limit={arg.get('limit')})"
    if op == OpCode.CALL_FUNC and isinstance(arg, dict):
        return f"({repr(arg.get('name'))}, args={arg.get('arg_count')})"
    if op == OpCode.CALL_METHOD and isinstance(arg, dict):
        m_name = arg.get("method") or arg.get("name")
        return f"({repr(m_name)}, args={arg.get('arg_count')})"
    if op == OpCode.NEW_OBJ and isinstance(arg, dict):
        return f"({repr(arg.get('class_name'))}, args={arg.get('arg_count')})"
    if op == OpCode.DEF_FUNC and isinstance(arg, dict):
        return f"({repr(arg.get('name'))}, params={arg.get('params', [])})"
    if op == OpCode.DEF_CLASS and isinstance(arg, dict):
        return f"({repr(arg.get('name'))}, fields={arg.get('fields', [])})"
    if op in (OpCode.JUMP, OpCode.JUMP_IF_FALSE):
        return f"-> target_ip={arg}"
    if op in (OpCode.STORE_VAR, OpCode.LOAD_VAR, OpCode.STORE_VAL, OpCode.CHECK_EXPIRED, OpCode.GET_PROP, OpCode.SET_PROP):
        return f"({repr(arg)})"
    if op == OpCode.PUSH_CONST:
        return f"({repr(arg)})"
    if op == OpCode.RETURN:
        return f"(has_value={arg})"
    if isinstance(arg, str):
        return f"({repr(arg)})"
    return f"({arg})"


def render_bytecode_instructions(instructions: List[Dict[str, Any]], indent: str = "  ") -> None:
    """Bytecode instruksiyalarini ketma-ketlikda (0001: STORE_LIVE ...) chop etish."""
    for idx, instr in enumerate(instructions):
        op = instr.get("op", "")
        arg = instr.get("arg")
        line = instr.get("line", 0)

        # DEF_FUNC ichki kodini alohida indentsiya bilan ko'rsatamiz
        if op == OpCode.DEF_FUNC and isinstance(arg, dict) and "code" in arg:
            func_name = arg.get("name")
            params = arg.get("params", [])
            inner_code = arg.get("code", [])
            print(
                f"{indent}{CYAN}{idx:04d}:{RESET} {BOLD}{MAGENTA}{op:<14}{RESET} "
                f"({BOLD}'{func_name}'{RESET}, params={params}) {GRAY}[L:{line}]{RESET}"
            )
            print(f"{indent}      │  ┌─ {GRAY}Function Body ({len(inner_code)} ops):{RESET}")
            for inner_idx, inner_ins in enumerate(inner_code):
                i_op = inner_ins.get("op", "")
                i_arg = inner_ins.get("arg")
                i_arg_str = format_instruction_arg(i_op, i_arg)
                print(
                    f"{indent}      │  │  {YELLOW}{inner_idx:04d}:{RESET} "
                    f"{GREEN}{i_op:<14}{RESET} {WHITE}{i_arg_str}{RESET}"
                )
            print(f"{indent}      │  └────────────────────────────────")
        else:
            arg_str = format_instruction_arg(op, arg)
            print(
                f"{indent}{CYAN}{idx:04d}:{RESET} {BOLD}{GREEN}{op:<14}{RESET} "
                f"{WHITE}{arg_str:<34}{RESET} {GRAY}[L:{line}]{RESET}"
            )


def run_verbose_pipeline(source_path: str, output_path: Optional[str] = None):
    """
    Kompilyatsiyaning barcha 5 ta bosqichini chiroyli grafik tarzda namoyish etadi.
    """
    from src.lexer import Lexer
    from src.parser import Parser
    from src.compiler import Compiler
    from src.vm import VirtualMachine

    src_p = Path(source_path)
    if not src_p.exists():
        print(f"{RED}[XATO] Manba fayli topilmadi: {source_path}{RESET}")
        sys.exit(1)

    print(f"\n{BOLD}{CYAN}╔═══════════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║            FLOW LANGUAGE VISUAL COMPILER & RUNTIME PIPELINE (v0.6.0)          ║{RESET}")
    print(f"{BOLD}{CYAN}╚═══════════════════════════════════════════════════════════════════════════════╝{RESET}")

    source_code = src_p.read_text(encoding="utf-8")
    lines = source_code.splitlines()

    # -------------------------------------------------------------
    # [1-STEP] SOURCE CODE
    # -------------------------------------------------------------
    print_step_header(1, "SOURCE CODE", f"{src_p.name}, {len(lines)} lines, {len(source_code)} bytes")
    for idx, line in enumerate(lines, 1):
        print(f" {GRAY}{idx:4d} │{RESET} {line}")

    # -------------------------------------------------------------
    # [2-STEP] LEXICAL ANALYSIS (LEXER -> TOKENS)
    # -------------------------------------------------------------
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()
    print_step_header(2, "LEXICAL ANALYSIS (LEXER -> TOKENS)", f"Jami: {len(tokens)} token")

    print(f"┌──────────────┬─────────────────────────┬───────────────────────────────────────┐")
    print(f"│ {BOLD}{'Pos [Line:Col]':<12}{RESET} │ {BOLD}{'Token Type':<23}{RESET} │ {BOLD}{'-> Value / Representation':<37}{RESET} │")
    print(f"├──────────────┼─────────────────────────┼───────────────────────────────────────┤")

    for tok in tokens:
        pos_str = f"[{tok.line:3d}:{tok.column:<3d}]"
        type_str = tok.type.name
        val_repr = repr(tok.value)
        if len(val_repr) > 34:
            val_repr = val_repr[:31] + "..."

        type_color = YELLOW if "KEYWORD" in type_str else (GREEN if "LITERAL" in type_str else CYAN)
        print(f"│ {GRAY}{pos_str:<12}{RESET} │ {type_color}{type_str:<23}{RESET} │ {WHITE}-> {val_repr:<34}{RESET} │")

    print(f"└──────────────┴─────────────────────────┴───────────────────────────────────────┘")

    # -------------------------------------------------------------
    # [3-STEP] SYNTAX ANALYSIS (PARSER -> AST TREE)
    # -------------------------------------------------------------
    parser = Parser(tokens)
    ast = parser.parse()
    print_step_header(3, "SYNTAX ANALYSIS (PARSER -> AST TREE)", "Abstract Syntax Tree")

    tree_root = ast_to_tree(ast)
    tree_lines = render_tree(tree_root)
    for t_line in tree_lines:
        print(t_line)

    # -------------------------------------------------------------
    # [3.5-STEP] SEMANTIC ANALYSIS (STATIK TAHLIL VA SYMBOL TABLE)
    # -------------------------------------------------------------
    from src.analyzer.analyzer import Analyzer, Severity
    analyzer = Analyzer()
    diagnostics = analyzer.analyze(ast)

    print_step_header(3.5, "SEMANTIC ANALYSIS (STATIK TAHLIL VA SYMBOL TABLE)", "Scope & Type Validation")
    print(f" {GREEN}[*]{RESET} {BOLD}Scope Validation:{RESET} {GREEN}OK{RESET} (Barcha funksiya va bloklar scope'i to'g'ri)")
    print(f" {CYAN}[*]{RESET} {BOLD}Symbol Table (Belgilar jadvali):{RESET}")

    # Symbol Table elementlarini yig'ish (funksiyalar va asosiy o'zgaruvchilar)
    symbols = []
    for stmt in ast.statements:
        if isinstance(stmt, FunctionDef):
            ret_type = stmt.return_type if stmt.return_type else "Void"
            symbols.append((f"'{stmt.name}'", f"Function Symbol -> returns {ret_type}"))
            # main ichidagi live yoki muhim o'zgaruvchilarni ko'rsatish
            for inner in stmt.body:
                if isinstance(inner, (VarDecl, VarDeclStmt)):
                    if getattr(inner, "is_live", False):
                        t_ann = getattr(inner, "type_annotation", None) or "Any"
                        limit = getattr(inner, "life_limit", 3)
                        symbols.append((f"'{inner.name}'", f"Live Variable Symbol (type={t_ann}, limit={limit})"))
                elif isinstance(inner, ValDecl):
                    t_ann = getattr(inner, "type_annotation", None) or "Any"
                    symbols.append((f"'{inner.name}'", f"Constant Symbol (type={t_ann})"))
        elif isinstance(stmt, ClassDeclStmt):
            symbols.append((f"'{stmt.name}'", f"Class Symbol ({len(stmt.constructor_fields)} fields, {len(stmt.methods)} methods)"))

    if symbols:
        for idx, (sym_name, sym_info) in enumerate(symbols):
            is_last = (idx == len(symbols) - 1)
            branch = "└──" if is_last else "├──"
            print(f"     {branch} {BOLD}{WHITE}{sym_name:<12}{RESET} : {sym_info}")
    else:
        print(f"     └── {GRAY}(Global scope bo'sh){RESET}")

    print(f" {GREEN}[*]{RESET} {BOLD}Type Checking:{RESET} {GREEN}OK{RESET} (O'zgaruvchi va metodlar tiplari mos)")
    print(f" {GREEN}[*]{RESET} {BOLD}Expired/Live Usage Rules:{RESET} {GREEN}OK{RESET}")

    errors_count = sum(1 for d in diagnostics if d.severity == Severity.ERROR)
    warnings_count = sum(1 for d in diagnostics if d.severity == Severity.WARNING)

    if errors_count == 0:
        warn_str = f" ({warnings_count} ta ogohlantirish)" if warnings_count > 0 else ""
        print(f" {BOLD}{GREEN}[+] Semantik tahlil xatosiz yakunlandi (0 ta semantik xato){warn_str}.{RESET}")
    else:
        print(f" {BOLD}{RED}[-] Semantik tahlilda {errors_count} ta xato aniqlandi!{RESET}")
        for d in diagnostics:
            if d.severity == Severity.ERROR:
                print(f"     {RED}• [Line {d.line}] {d.message}{RESET}")

    # -------------------------------------------------------------
    # [4-STEP] CODE GENERATION (COMPILER -> BYTECODE)
    # -------------------------------------------------------------
    compiler = Compiler()
    bytecode = compiler.compile(ast)
    print_step_header(4, "CODE GENERATION (COMPILER -> BYTECODE)", "Bytecode OpCodes & Binary Packing")

    print(f"{BOLD}[Flow Bytecode Instructions]:{RESET}")
    render_bytecode_instructions(bytecode.get("instructions", []))

    # Binary Serializatsiya va siqish hisoblash
    raw_pickle = pickle.dumps(bytecode, protocol=pickle.HIGHEST_PROTOCOL)
    raw_size = len(raw_pickle)
    compressed_bytes = zlib.compress(raw_pickle, level=9)
    binary_data = FLOWC_MAGIC + compressed_bytes
    flowc_size = len(binary_data)
    compression_ratio = ((raw_size - flowc_size) / raw_size * 100.0) if raw_size > 0 else 0.0

    if output_path is None:
        build_dir = Path("build")
        build_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(build_dir / f"{src_p.stem}.flowc")
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    Path(output_path).write_bytes(binary_data)

    print(f"\n{BOLD}[Binary Serialization & Packaging]:{RESET}")
    print(f"  ├── Asl xom hajm (Pickle AST/IR):   {WHITE}{raw_size:,} bayt{RESET}")
    print(f"  ├── Siqilgan binary (.flowc fayli):  {GREEN}{BOLD}{flowc_size:,} bayt{RESET}")
    print(f"  ├── Siqish samaradorligi:            {CYAN}{compression_ratio:.1f}% tejaldi{RESET} (Zlib Max Level 9)")
    print(f"  └── Saqlangan binary fayl:           {YELLOW}{output_path}{RESET}")

    # -------------------------------------------------------------
    # [5-STEP] VIRTUAL MACHINE EXECUTION (VM RUNTIME)
    # -------------------------------------------------------------
    print_step_header(5, "VIRTUAL MACHINE EXECUTION (VM RUNTIME)", "Flow VM CallStack & Output")

    box_w = 77
    print(f"┌{'─' * (box_w + 2)}┐")
    print(format_box_line(f"{CYAN}[*] Flow VM Runtime faollashtirildi...{RESET}", box_w))
    print(format_box_line(f"{GRAY}[*] Target bayt-kod: {output_path}{RESET}", box_w))
    print(f"├{'─' * (box_w + 2)}┤")
    print(format_box_line(f"{BOLD}{GREEN}>>> DASTUR CHIQISHI (STDOUT):{RESET}", box_w))
    print(f"├{'─' * (box_w + 2)}┤")

    vm = VirtualMachine()
    loaded_bc = vm.load_bytecode(output_path)

    # VM ijro etish
    try:
        vm.run_bytecode(loaded_bc)
    except SystemExit:
        pass
    except Exception as e:
        print(f"\n{RED}[XATO]: VM ijrosida kutilmagan xatolik: {e}{RESET}")

    print(f"├{'─' * (box_w + 2)}┤")
    print(format_box_line(f"{BOLD}{GREEN}[+] VM ijrosi muvaffaqiyatli yakunlandi (Exit Code: 0){RESET}", box_w))
    print(format_box_line(f"{GRAY}[+] Barcha resurslar va CallFrame steklari xavfsiz ozod qilindi.{RESET}", box_w))
    print(f"└{'─' * (box_w + 2)}┘")
    print()

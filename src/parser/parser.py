from typing import List, Optional, Any
from src.lexer.token import Token, TokenType
from src.parser.ast import (
    ASTNode,
    Program,
    Param,
    FunctionDef,
    ClassField,
    ClassDeclStmt,
    NewExpr,
    GetPropertyExpr,
    SetPropertyStmt,
    MethodCallExpr,
    ThisExpr,
    NullLiteral,
    PipelineExpr,
    VarDecl,
    VarDeclStmt,
    ValDecl,
    AssignStmt,
    IndexAssignStmt,
    ReturnStmt,
    IfStmt,
    MatchExpr,
    StepWhileStmt,
    WhileStmt,
    ForInStmt,
    BinaryOp,
    UnaryOp,
    RangeExpr,
    ArrayLiteralExpr,
    IndexAccessExpr,
    CallExpr,
    Identifier,
    IntLiteral,
    FloatLiteral,
    StringLiteral,
    BoolLiteral,
)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF token

    def _match(self, *expected_types: TokenType) -> bool:
        token = self._peek()
        return token.type in expected_types

    def _match_keyword(self, keyword: str) -> bool:
        token = self._peek()
        return token.type == TokenType.KEYWORD and token.value == keyword

    def _advance(self) -> Token:
        token = self._peek()
        if self.pos < len(self.tokens):
            self.pos += 1
        return token

    def _consume(self, expected_type: TokenType, error_message: str) -> Token:
        token = self._peek()
        if token.type == expected_type:
            return self._advance()
        raise SyntaxError(
            f"Parser xatosi [{token.line}:{token.column}]: {error_message}. "
            f"Kutilgan tur: {expected_type.name}, kelgan tur: {token.type.name} ('{token.value}')"
        )

    def _consume_keyword(self, keyword: str, error_message: str) -> Token:
        token = self._peek()
        if token.type == TokenType.KEYWORD and token.value == keyword:
            return self._advance()
        raise SyntaxError(
            f"Parser xatosi [{token.line}:{token.column}]: {error_message}. "
            f"Kutilgan kalit so'z: '{keyword}', kelgan: '{token.value}'"
        )

    def parse(self) -> Program:
        statements: List[ASTNode] = []
        while not self._match(TokenType.EOF):
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
        return Program(statements)

    def _parse_statement(self) -> ASTNode:
        token = self._peek()

        if token.type == TokenType.KEYWORD:
            if token.value == "inner":
                return self._parse_function_def(is_inner=True)
            elif token.value == "fn":
                return self._parse_function_def(is_inner=False)
            elif token.value == "var":
                stmt = self._parse_var_decl()
                if self._match(TokenType.SEMICOLON):
                    self._advance()
                return stmt
            elif token.value == "val":
                if self._peek(1).type == TokenType.IDENTIFIER:
                    stmt = self._parse_val_decl()
                else:
                    stmt = self._parse_expression_or_assignment()
                if self._match(TokenType.SEMICOLON):
                    self._advance()
                return stmt

            elif token.value == "live":
                stmt = self._parse_live_decl()
                if self._match(TokenType.SEMICOLON):
                    self._advance()
                return stmt
            elif token.value == "return":
                stmt = self._parse_return_stmt()
                if self._match(TokenType.SEMICOLON):
                    self._advance()
                return stmt
            elif token.value == "if":
                return self._parse_if_stmt()
            elif token.value == "while":
                return self._parse_while_stmt()
            elif token.value == "step":
                return self._parse_step_while_stmt()
            elif token.value == "for":
                return self._parse_for_stmt()
            elif token.value == "class":
                return self._parse_class_decl()

        # Fallback: Agar token ma'lum bir statement kalit so'ziga mos kelmasa,
        # uni ifoda (expression) yoki o'zlashtirish (assignment) sifatida o'qiymiz
        stmt = self._parse_expression_or_assignment()
        if self._match(TokenType.SEMICOLON):
            self._advance()
        return stmt

    def _parse_expression_or_assignment(self) -> ASTNode:
        """Ifoda yoki o'zlashtirish (assignment) statementini o'qiydi."""
        expr = self._parse_expression()

        assign_ops = {
            TokenType.ASSIGN,
            TokenType.PLUS_ASSIGN,
            TokenType.MINUS_ASSIGN,
            TokenType.STAR_ASSIGN,
            TokenType.SLASH_ASSIGN,
        }
        if self._peek().type in assign_ops:
            op_token = self._advance()
            value = self._parse_expression()

            # obj.prop = value
            if isinstance(expr, GetPropertyExpr):
                return SetPropertyStmt(obj=expr.obj, property_name=expr.property_name, value=value)
            # arr[idx] = value
            elif isinstance(expr, IndexAccessExpr) and isinstance(expr.array, Identifier):
                return IndexAssignStmt(array_name=expr.array.name, index=expr.index, value=value)
            # name = value yoki name += value
            elif isinstance(expr, Identifier):
                return AssignStmt(name=expr.name, value=value, op=op_token.value)
            else:
                raise SyntaxError(f"O'zlashtirish uchun noto'g'ri target: {type(expr).__name__}")

        return expr

    def _parse_class_decl(self) -> ClassDeclStmt:
        """class User(var name: String, var age: Int = 18) { fn greet() {...} }"""
        self._consume_keyword("class", "'class' kalit so'zi kutilgan edi")
        class_name = self._consume(TokenType.IDENTIFIER, "Klass nomi kutilgan edi").value

        # Primary constructor: class User(var name: String, ...)
        constructor_fields: List[ClassField] = []
        if self._match(TokenType.LPAREN):
            self._advance()  # (
            if not self._match(TokenType.RPAREN):
                while True:
                    is_mutable = True
                    if self._match_keyword("var"):
                        self._advance()
                        is_mutable = True
                    elif self._match_keyword("val"):
                        self._advance()
                        is_mutable = False

                    field_name = self._consume(TokenType.IDENTIFIER, "Maydon nomi kutilgan edi").value
                    type_name = None
                    if self._match(TokenType.COLON):
                        self._advance()
                        type_name = self._consume(TokenType.TYPE, "Maydon turi kutilgan edi").value

                    default_val = None
                    if self._match(TokenType.ASSIGN):
                        self._advance()
                        default_val = self._parse_expression()

                    constructor_fields.append(
                        ClassField(name=field_name, type_name=type_name, default_value=default_val, is_mutable=is_mutable)
                    )

                    if self._match(TokenType.COMMA):
                        self._advance()
                    else:
                        break
            self._consume(TokenType.RPAREN, "')' kutilgan edi")

        # Klass tanasi: { ... }
        self._consume(TokenType.LBRACE, "Klass tanasi uchun '{' kutilgan edi")
        methods: List[FunctionDef] = []
        while not self._match(TokenType.RBRACE, TokenType.EOF):
            token = self._peek()
            if token.type == TokenType.KEYWORD and token.value in ("fn", "inner"):
                is_inner = token.value == "inner"
                methods.append(self._parse_function_def(is_inner=is_inner))
            else:
                raise SyntaxError(
                    f"Klass ichida faqat metod e'lonlari kutilgan edi, keldi: '{token.value}'"
                )
        self._consume(TokenType.RBRACE, "Klass tanasi yakunida '}' kutilgan edi")

        stmt = ClassDeclStmt(name=class_name, constructor_fields=constructor_fields, methods=methods)
        stmt.line = 1
        return stmt

    def _parse_function_def(self, is_inner: bool = False) -> FunctionDef:
        if is_inner:
            self._consume_keyword("inner", "'inner' kalit so'zi kutilgan edi")

        self._consume_keyword("fn", "'fn' kalit so'zi kutilgan edi")
        name_token = self._consume(TokenType.IDENTIFIER, "Funksiya nomi kutilgan edi")
        self._consume(TokenType.LPAREN, "Funksiya parametrlaridan oldin '(' kutilgan edi")

        params: List[Param] = []
        if not self._match(TokenType.RPAREN):
            while True:
                p_name_token = self._consume(TokenType.IDENTIFIER, "Parametr nomi kutilgan edi")
                self._consume(TokenType.COLON, "Parametr nomidan so'ng ':' kutilgan edi")
                p_type_token = self._consume(TokenType.TYPE, "Parametr turi kutilgan edi")

                # Default qiymat
                default_val = None
                if self._match(TokenType.ASSIGN):
                    self._advance()
                    default_val = self._parse_expression()

                params.append(Param(name=p_name_token.value, type_name=p_type_token.value, default_value=default_val))

                if self._match(TokenType.COMMA):
                    self._advance()
                else:
                    break

        self._consume(TokenType.RPAREN, "Parametrlardan so'ng ')' kutilgan edi")

        return_type: Optional[str] = None
        if self._match(TokenType.COLON):
            self._advance()
            # Boolean, Int, String, Void, yoki maxsus tur
            if self._match(TokenType.TYPE):
                rt_token = self._advance()
                return_type = rt_token.value
            elif self._match(TokenType.IDENTIFIER):
                rt_token = self._advance()
                return_type = rt_token.value  # User, Person kabi custom typlar

        # Expression body: => expr
        if self._match(TokenType.FAT_ARROW):
            self._advance()
            expr_body = self._parse_expression()
            fn_def = FunctionDef(
                name=name_token.value,
                params=params,
                return_type=return_type,
                body=[],
                is_inner=is_inner,
                expr_body=expr_body,
            )
            fn_def.line = name_token.line
            return fn_def

        self._consume(TokenType.LBRACE, "Funksiya tanasi uchun '{' kutilgan edi")

        body: List[ASTNode] = []
        while not self._match(TokenType.RBRACE, TokenType.EOF):
            body.append(self._parse_statement())

        self._consume(TokenType.RBRACE, "Funksiya tanasi yakunida '}' kutilgan edi")

        fn_def = FunctionDef(
            name=name_token.value,
            params=params,
            return_type=return_type,
            body=body,
            is_inner=is_inner,
        )
        fn_def.line = name_token.line
        return fn_def

    def _parse_var_decl(self) -> VarDecl:
        self._consume_keyword("var", "'var' kalit so'zi kutilgan edi")
        if self._peek().type == TokenType.IDENTIFIER or (self._peek().type == TokenType.KEYWORD and self._peek().value == "val"):
            name_token = self._advance()
        else:
            name_token = self._consume(TokenType.IDENTIFIER, "O'zgaruvchi nomi kutilgan edi")


        type_annotation: Optional[str] = None
        if self._match(TokenType.COLON):
            self._advance()
            if self._match(TokenType.TYPE):
                t_token = self._advance()
                type_annotation = t_token.value
            elif self._match(TokenType.IDENTIFIER):
                t_token = self._advance()
                type_annotation = t_token.value

        self._consume(TokenType.ASSIGN, "O'zgaruvchiga qiymat berish uchun '=' kutilgan edi")
        value_node = self._parse_expression()

        decl = VarDecl(name=name_token.value, value=value_node, type_annotation=type_annotation)
        decl.line = name_token.line
        return decl

    def _parse_val_decl(self) -> ValDecl:
        self._consume_keyword("val", "'val' kalit so'zi kutilgan edi")
        name_token = self._consume(TokenType.IDENTIFIER, "O'zgarmas qiymat (val) nomi kutilgan edi")

        type_annotation: Optional[str] = None
        if self._match(TokenType.COLON):
            self._advance()
            if self._match(TokenType.TYPE):
                t_token = self._advance()
                type_annotation = t_token.value
            elif self._match(TokenType.IDENTIFIER):
                t_token = self._advance()
                type_annotation = t_token.value

        self._consume(TokenType.ASSIGN, "O'zgarmas qiymat berish uchun '=' kutilgan edi")
        value_node = self._parse_expression()

        decl = ValDecl(name=name_token.value, value=value_node, type_annotation=type_annotation)
        decl.line = name_token.line
        return decl

    def _parse_live_decl(self) -> VarDecl:
        """live name: Type = value (limit=3), live N name: Type = value yoki live[N] name: Type = value"""
        live_tok = self._consume_keyword("live", "'live' kalit so'zi kutilgan edi")

        limit = 3
        if self._match(TokenType.LBRACKET):
            self._advance()
            limit_tok = self._consume(TokenType.INT_LITERAL, "Limit butun son bo'lishi kerak")
            limit = int(limit_tok.value)
            self._consume(TokenType.RBRACKET, "']' kutilgan edi")
        elif self._match(TokenType.INT_LITERAL):
            limit_tok = self._advance()
            limit = int(limit_tok.value)

        name_token = self._consume(TokenType.IDENTIFIER, "O'zgaruvchi nomi kutilgan edi")

        type_annotation: Optional[str] = None
        if self._match(TokenType.COLON):
            self._advance()
            if self._match(TokenType.TYPE):
                t_token = self._advance()
                type_annotation = t_token.value
            elif self._match(TokenType.IDENTIFIER):
                t_token = self._advance()
                type_annotation = t_token.value

        self._consume(TokenType.ASSIGN, "O'zgaruvchiga qiymat berish uchun '=' kutilgan edi")
        value_node = self._parse_expression()

        decl = VarDecl(
            name=name_token.value,
            value=value_node,
            type_annotation=type_annotation,
            is_live=True,
            life_limit=limit,
        )
        decl.line = live_tok.line
        return decl

    def _parse_if_stmt(self) -> IfStmt:
        self._consume_keyword("if", "'if' kalit so'zi kutilgan edi")
        self._consume(TokenType.LPAREN, "if shartidan oldin '(' kutilgan edi")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "if shartidan so'ng ')' kutilgan edi")

        self._consume(TokenType.LBRACE, "if bloki uchun '{' kutilgan edi")
        then_branch: List[ASTNode] = []
        while not self._match(TokenType.RBRACE, TokenType.EOF):
            then_branch.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "if bloki yakunida '}' kutilgan edi")

        # elif va else if zanjiri
        elif_branches = []
        while True:
            if self._match_keyword("elif"):
                self._advance()  # elif
            elif self._match_keyword("else") and self._peek(1).type == TokenType.KEYWORD and self._peek(1).value == "if":
                self._advance()  # else
                self._advance()  # if
            else:
                break

            self._consume(TokenType.LPAREN, "elif / else if shartidan oldin '(' kutilgan edi")
            elif_cond = self._parse_expression()
            self._consume(TokenType.RPAREN, "elif / else if shartidan so'ng ')' kutilgan edi")
            self._consume(TokenType.LBRACE, "elif / else if bloki uchun '{' kutilgan edi")
            elif_body: List[ASTNode] = []
            while not self._match(TokenType.RBRACE, TokenType.EOF):
                elif_body.append(self._parse_statement())
            self._consume(TokenType.RBRACE, "elif / else if bloki yakunida '}' kutilgan edi")
            elif_branches.append((elif_cond, elif_body))

        else_branch: Optional[List[ASTNode]] = None
        if self._match_keyword("else"):
            self._advance()
            self._consume(TokenType.LBRACE, "else bloki uchun '{' kutilgan edi")
            else_branch = []
            while not self._match(TokenType.RBRACE, TokenType.EOF):
                else_branch.append(self._parse_statement())
            self._consume(TokenType.RBRACE, "else bloki yakunida '}' kutilgan edi")

        return IfStmt(condition=condition, then_branch=then_branch, elif_branches=elif_branches, else_branch=else_branch)

    def _parse_match_expr(self) -> MatchExpr:
        """match (expr) { pattern => expr, ..., else => expr } yoki match { cond => expr, ..., else => expr }"""
        match_tok = self._consume_keyword("match", "'match' kalit so'zi kutilgan edi")

        expr: Optional[ASTNode] = None
        if self._match(TokenType.LPAREN):
            self._advance()
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "match (expr) dan so'ng ')' kutilgan edi")

        self._consume(TokenType.LBRACE, "match bloki uchun '{' kutilgan edi")

        cases = []
        default_case: Optional[ASTNode] = None

        while not self._match(TokenType.RBRACE, TokenType.EOF):
            # else => expr
            if self._match_keyword("else"):
                self._advance()
                self._consume(TokenType.FAT_ARROW, "else dan so'ng '=>' kutilgan edi")
                default_case = self._parse_expression()
                # Ixtiyoriy vergul
                if self._match(TokenType.COMMA):
                    self._advance()
                break
            else:
                # pattern => expr
                pattern = self._parse_expression()
                self._consume(TokenType.FAT_ARROW, "pattern dan so'ng '=>' kutilgan edi")
                result = self._parse_expression()
                cases.append((pattern, result))
                # Ixtiyoriy vergul
                if self._match(TokenType.COMMA):
                    self._advance()

        self._consume(TokenType.RBRACE, "match bloki yakunida '}' kutilgan edi")
        node = MatchExpr(expr=expr, cases=cases, default_case=default_case)
        node.line = match_tok.line
        return node

    def _parse_step_while_stmt(self) -> StepWhileStmt:
        """step[N] while (condition) { body }"""
        step_tok = self._consume_keyword("step", "'step' kalit so'zi kutilgan edi")
        self._consume(TokenType.LBRACKET, "step dan so'ng '[' kutilgan edi")
        limit_tok = self._consume(TokenType.INT_LITERAL, "step chegarasi (butun son) kutilgan edi")
        limit = int(limit_tok.value)
        self._consume(TokenType.RBRACKET, "step chegarasidan so'ng ']' kutilgan edi")

        self._consume_keyword("while", "step[...] dan so'ng 'while' kalit so'zi kutilgan edi")
        self._consume(TokenType.LPAREN, "while shartidan oldin '(' kutilgan edi")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "while shartidan so'ng ')' kutilgan edi")

        self._consume(TokenType.LBRACE, "while bloki uchun '{' kutilgan edi")
        body: List[ASTNode] = []
        while not self._match(TokenType.RBRACE, TokenType.EOF):
            body.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "while bloki yakunida '}' kutilgan edi")

        node = StepWhileStmt(limit=limit, condition=condition, body=body)
        node.line = step_tok.line
        return node

    def _parse_while_stmt(self) -> WhileStmt:
        self._consume_keyword("while", "'while' kalit so'zi kutilgan edi")
        self._consume(TokenType.LPAREN, "while shartidan oldin '(' kutilgan edi")
        condition = self._parse_expression()
        self._consume(TokenType.RPAREN, "while shartidan so'ng ')' kutilgan edi")

        self._consume(TokenType.LBRACE, "while bloki uchun '{' kutilgan edi")
        body: List[ASTNode] = []
        while not self._match(TokenType.RBRACE, TokenType.EOF):
            body.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "while bloki yakunida '}' kutilgan edi")

        return WhileStmt(condition=condition, body=body)

    def _parse_for_stmt(self) -> ForInStmt:
        self._consume_keyword("for", "'for' kalit so'zi kutilgan edi")
        self._consume(TokenType.LPAREN, "for shartidan oldin '(' kutilgan edi")
        var_token = self._consume(TokenType.IDENTIFIER, "for sikli o'zgaruvchisi kutilgan edi")
        self._consume_keyword("in", "'in' kalit so'zi kutilgan edi")
        iterable = self._parse_expression()
        self._consume(TokenType.RPAREN, "for shartidan so'ng ')' kutilgan edi")

        self._consume(TokenType.LBRACE, "for bloki uchun '{' kutilgan edi")
        body: List[ASTNode] = []
        while not self._match(TokenType.RBRACE, TokenType.EOF):
            body.append(self._parse_statement())
        self._consume(TokenType.RBRACE, "for bloki yakunida '}' kutilgan edi")

        return ForInStmt(variable=var_token.value, iterable=iterable, body=body)

    def _parse_return_stmt(self) -> ReturnStmt:
        self._consume_keyword("return", "'return' kalit so'zi kutilgan edi")

        if self._match(TokenType.RBRACE, TokenType.EOF):
            return ReturnStmt(value=None)

        expr = self._parse_expression()
        return ReturnStmt(value=expr)

    # ==========================================
    # Operator Precedence Zanjiri
    # ! > *, /, % > +, - > .. > >, <, >=, <=, ==, != > && > || > |>
    # ==========================================

    def _parse_expression(self) -> ASTNode:
        return self._parse_pipeline()

    def _parse_pipeline(self) -> ASTNode:
        """x |> square() |> print() -> pipeline operator"""
        node = self._parse_logical_or()

        while self._match(TokenType.PIPELINE):
            self._advance()
            # O'ng taraf: funksiya/metod chaqiruvi bo'lishi kerak
            right = self._parse_logical_or()
            node = PipelineExpr(left=node, right=right)

        return node

    def _parse_logical_or(self) -> ASTNode:
        node = self._parse_logical_and()

        while self._match(TokenType.OR):
            op_token = self._advance()
            right = self._parse_logical_and()
            node = BinaryOp(left=node, op=op_token.value, right=right)

        return node

    def _parse_logical_and(self) -> ASTNode:
        node = self._parse_comparison()

        while self._match(TokenType.AND):
            op_token = self._advance()
            right = self._parse_comparison()
            node = BinaryOp(left=node, op=op_token.value, right=right)

        return node

    def _parse_comparison(self) -> ASTNode:
        node = self._parse_range()

        while self._match(TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE, TokenType.EQ, TokenType.NEQ):
            op_token = self._advance()
            right = self._parse_range()
            node = BinaryOp(left=node, op=op_token.value, right=right)

        return node

    def _parse_range(self) -> ASTNode:
        node = self._parse_additive()

        if self._match(TokenType.DOTDOT):
            self._advance()
            right = self._parse_additive()
            return RangeExpr(start=node, end=right)

        return node

    def _parse_additive(self) -> ASTNode:
        node = self._parse_multiplicative()

        while self._match(TokenType.PLUS, TokenType.MINUS):
            op_token = self._advance()
            right = self._parse_multiplicative()
            node = BinaryOp(left=node, op=op_token.value, right=right)

        return node

    def _parse_multiplicative(self) -> ASTNode:
        node = self._parse_unary()

        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_token = self._advance()
            right = self._parse_unary()
            node = BinaryOp(left=node, op=op_token.value, right=right)

        return node

    def _parse_unary(self) -> ASTNode:
        if self._match(TokenType.NOT, TokenType.MINUS):
            op_token = self._advance()
            operand = self._parse_unary()
            return UnaryOp(op=op_token.value, operand=operand)

        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        token = self._peek()

        # null literal
        if token.type == TokenType.NULL_LITERAL:
            self._advance()
            return self._parse_postfix(NullLiteral())

        # 1. Massiv literali: [10, 20, 30]
        if token.type == TokenType.LBRACKET:
            self._advance()  # '['
            elements: List[ASTNode] = []
            if not self._match(TokenType.RBRACKET):
                while True:
                    elements.append(self._parse_expression())
                    if self._match(TokenType.COMMA):
                        self._advance()
                    else:
                        break
            self._consume(TokenType.RBRACKET, "Massiv yopuvchi ']' kutilgan edi")
            node = ArrayLiteralExpr(elements=elements)
            return self._parse_postfix(node)

        elif token.type == TokenType.INT_LITERAL:
            self._advance()
            return self._parse_postfix(IntLiteral(token.value))
        elif token.type == TokenType.FLOAT_LITERAL:
            self._advance()
            return self._parse_postfix(FloatLiteral(token.value))
        elif token.type == TokenType.STRING_LITERAL:
            self._advance()
            return self._parse_postfix(StringLiteral(token.value))
        elif token.type == TokenType.BOOL_LITERAL:
            self._advance()
            return self._parse_postfix(BoolLiteral(token.value))

        # this kalit so'zi
        elif token.type == TokenType.KEYWORD and token.value == "this":
            self._advance()
            node = ThisExpr()
            node.line = token.line
            return self._parse_postfix(node)

        # new ClassName(...)
        elif token.type == TokenType.KEYWORD and token.value == "new":
            self._advance()
            class_name_tok = self._consume(TokenType.IDENTIFIER, "Klass nomi kutilgan edi")
            self._consume(TokenType.LPAREN, "'(' kutilgan edi")
            args, named_args = self._parse_call_args()
            self._consume(TokenType.RPAREN, "')' kutilgan edi")
            node = NewExpr(class_name=class_name_tok.value, args=args, named_args=named_args)
            node.line = class_name_tok.line
            return self._parse_postfix(node)

        elif token.type in (TokenType.IDENTIFIER, TokenType.KEYWORD) and (
            token.type == TokenType.IDENTIFIER or token.value in ("print", "val")
        ):

            name_token = self._advance()
            # Funksiya chaqiruvi: sum(a, b) yoki named sum(a = 1, b = 2)
            if self._match(TokenType.LPAREN):
                self._advance()  # '('
                args, named_args = self._parse_call_args()
                self._consume(TokenType.RPAREN, "Chaqiruv argumentlaridan so'ng ')' kutilgan edi")
                node = CallExpr(callee=name_token.value, args=args)
                node.line = name_token.line
                return self._parse_postfix(node)

            node = Identifier(name_token.value)
            node.line = name_token.line
            return self._parse_postfix(node)

        # match ifodasi
        elif token.type == TokenType.KEYWORD and token.value == "match":
            node = self._parse_match_expr()
            return node

        elif token.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._consume(TokenType.RPAREN, "Ifodadan so'ng ')' kutilgan edi")
            return self._parse_postfix(expr)

        raise SyntaxError(
            f"Parser xatosi [{token.line}:{token.column}]: Kutilmagan ifoda elementi: '{token.value}' ({token.type.name})"
        )

    def _parse_call_args(self):
        """Funksiya chaqiruvi argumentlarini parse qiladi (oddiy va nomlangan)."""
        args: List[ASTNode] = []
        named_args: dict = {}

        if self._match(TokenType.RPAREN):
            return args, named_args

        while True:
            # Named argument: name = value
            if self._peek().type == TokenType.IDENTIFIER and self._peek(1).type == TokenType.ASSIGN:
                arg_name = self._advance().value
                self._advance()  # =
                arg_val = self._parse_expression()
                named_args[arg_name] = arg_val
            else:
                args.append(self._parse_expression())

            if self._match(TokenType.COMMA):
                self._advance()
            else:
                break

        return args, named_args

    def _parse_postfix(self, node: ASTNode) -> ASTNode:
        """Indeks va property access zanjiri: numbers[0], user.name, user.greet()"""
        while True:
            if self._match(TokenType.LBRACKET):
                self._advance()  # '['
                index_expr = self._parse_expression()
                self._consume(TokenType.RBRACKET, "Indeks yopuvchi ']' kutilgan edi")
                node = IndexAccessExpr(array=node, index=index_expr)

            elif self._match(TokenType.DOT):
                self._advance()  # '.'
                prop_token = self._consume(TokenType.IDENTIFIER, "Property/metod nomi kutilgan edi")
                prop_name = prop_token.value

                # Metod chaqiruvi: obj.method(args)
                if self._match(TokenType.LPAREN):
                    self._advance()  # '('
                    args, named_args = self._parse_call_args()
                    self._consume(TokenType.RPAREN, "')' kutilgan edi")
                    node = MethodCallExpr(obj=node, method_name=prop_name, args=args)
                else:
                    # Property murojaat: obj.field
                    node = GetPropertyExpr(obj=node, property_name=prop_name)
            else:
                break

        return node

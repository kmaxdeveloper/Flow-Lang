from typing import List, Optional
from src.lexer.token import TokenType, Token, KEYWORDS, TYPES


class Lexer:
    def __init__(self, source_code: str):
        self.source = source_code
        self.length = len(source_code)
        self.pos = 0
        self.line = 1
        self.column = 1

    def _peek(self, offset: int = 0) -> Optional[str]:
        target = self.pos + offset
        if target < self.length:
            return self.source[target]
        return None

    def _advance(self) -> Optional[str]:
        if self.pos >= self.length:
            return None
        char = self.source[self.pos]
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _skip_whitespace_and_comments(self):
        while self.pos < self.length:
            char = self.source[self.pos]

            if char in (" ", "\t", "\r", "\n"):
                self._advance()
                continue

            # Bir qatorli izoh: //
            if char == "/" and self._peek(1) == "/":
                while self.pos < self.length and self.source[self.pos] != "\n":
                    self._advance()
                continue

            # Ko'p qatorli izoh: /* ... */
            if char == "/" and self._peek(1) == "*":
                self._advance()  # /
                self._advance()  # *
                while self.pos < self.length:
                    if self.source[self.pos] == "*" and self._peek(1) == "/":
                        self._advance()  # *
                        self._advance()  # /
                        break
                    self._advance()
                continue

            break

    def _read_identifier_or_keyword(self) -> Token:
        start_col = self.column
        start_line = self.line
        chars = []

        while self.pos < self.length:
            char = self.source[self.pos]
            if char.isalnum() or char == "_":
                chars.append(self._advance())
            else:
                break

        val = "".join(chars)
        if val == "true":
            return Token(TokenType.BOOL_LITERAL, True, start_line, start_col)
        elif val == "false":
            return Token(TokenType.BOOL_LITERAL, False, start_line, start_col)
        elif val == "null":
            return Token(TokenType.NULL_LITERAL, None, start_line, start_col)
        elif val in KEYWORDS:
            return Token(TokenType.KEYWORD, val, start_line, start_col)
        elif val in TYPES:
            return Token(TokenType.TYPE, val, start_line, start_col)
        else:
            return Token(TokenType.IDENTIFIER, val, start_line, start_col)

    def _read_number(self) -> Token:
        start_col = self.column
        start_line = self.line
        chars = []
        is_float = False

        while self.pos < self.length:
            char = self.source[self.pos]
            # Agar 0..3 kelsa, '..' ni float nuqtasi deb adashtirmaslik kerak!
            if char == "." and self._peek(1) == ".":
                break

            if char.isdigit():
                chars.append(self._advance())
            elif char == "." and not is_float and (self._peek(1) is not None and self._peek(1).isdigit()):
                is_float = True
                chars.append(self._advance())
            else:
                break

        # Float suffiksi 'f' yoki 'F'
        if self.pos < self.length and self.source[self.pos] in ("f", "F"):
            is_float = True
            chars.append(self._advance())

        val_str = "".join(chars)
        if is_float:
            return Token(TokenType.FLOAT_LITERAL, val_str, start_line, start_col)
        else:
            return Token(TokenType.INT_LITERAL, int(val_str), start_line, start_col)

    def _read_string(self) -> Token:
        start_col = self.column
        start_line = self.line
        self._advance()

        chars = []
        while self.pos < self.length:
            char = self.source[self.pos]
            if char == '"':
                self._advance()
                break
            elif char == "\\":
                self._advance()
                escaped = self._advance()
                if escaped == "n":
                    chars.append("\n")
                elif escaped == "t":
                    chars.append("\t")
                elif escaped == "r":
                    chars.append("\r")
                elif escaped == '"':
                    chars.append('"')
                elif escaped == "\\":
                    chars.append("\\")
                else:
                    chars.append(escaped or "")
            else:
                chars.append(self._advance())

        return Token(TokenType.STRING_LITERAL, "".join(chars), start_line, start_col)

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []

        while self.pos < self.length:
            self._skip_whitespace_and_comments()
            if self.pos >= self.length:
                break

            char = self.source[self.pos]
            cur_line = self.line
            cur_col = self.column

            if char.isalpha() or char == "_":
                tokens.append(self._read_identifier_or_keyword())
            elif char.isdigit():
                tokens.append(self._read_number())
            elif char == '"':
                tokens.append(self._read_string())

            # 2 belgili operatorlar
            elif char == "." and self._peek(1) == ".":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.DOTDOT, "..", cur_line, cur_col))
            elif char == "=" and self._peek(1) == ">":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.FAT_ARROW, "=>", cur_line, cur_col))
            elif char == "|" and self._peek(1) == ">":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.PIPELINE, "|>", cur_line, cur_col))
            elif char == "+" and self._peek(1) == "=":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.PLUS_ASSIGN, "+=", cur_line, cur_col))
            elif char == "-" and self._peek(1) == "=":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.MINUS_ASSIGN, "-=", cur_line, cur_col))
            elif char == "*" and self._peek(1) == "=":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.STAR_ASSIGN, "*=", cur_line, cur_col))
            elif char == "/" and self._peek(1) == "=":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.SLASH_ASSIGN, "/=", cur_line, cur_col))

            elif char == "=" and self._peek(1) == "=":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.EQ, "==", cur_line, cur_col))
            elif char == "!" and self._peek(1) == "=":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.NEQ, "!=", cur_line, cur_col))
            elif char == ">" and self._peek(1) == "=":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.GTE, ">=", cur_line, cur_col))
            elif char == "<" and self._peek(1) == "=":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.LTE, "<=", cur_line, cur_col))

            elif char == "&" and self._peek(1) == "&":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.AND, "&&", cur_line, cur_col))
            elif char == "|" and self._peek(1) == "|":
                self._advance()
                self._advance()
                tokens.append(Token(TokenType.OR, "||", cur_line, cur_col))

            # 1 belgili operatorlar
            elif char == "=":
                self._advance()
                tokens.append(Token(TokenType.ASSIGN, "=", cur_line, cur_col))
            elif char == "!":
                self._advance()
                tokens.append(Token(TokenType.NOT, "!", cur_line, cur_col))
            elif char == ">":
                self._advance()
                tokens.append(Token(TokenType.GT, ">", cur_line, cur_col))
            elif char == "<":
                self._advance()
                tokens.append(Token(TokenType.LT, "<", cur_line, cur_col))
            elif char == "+":
                self._advance()
                tokens.append(Token(TokenType.PLUS, "+", cur_line, cur_col))
            elif char == "-":
                self._advance()
                tokens.append(Token(TokenType.MINUS, "-", cur_line, cur_col))
            elif char == "*":
                self._advance()
                tokens.append(Token(TokenType.STAR, "*", cur_line, cur_col))
            elif char == "/":
                self._advance()
                tokens.append(Token(TokenType.SLASH, "/", cur_line, cur_col))
            elif char == "%":
                self._advance()
                tokens.append(Token(TokenType.PERCENT, "%", cur_line, cur_col))

            # Belgilar (Punctuation)
            elif char == ".":
                self._advance()
                tokens.append(Token(TokenType.DOT, ".", cur_line, cur_col))
            elif char == ":":
                self._advance()
                tokens.append(Token(TokenType.COLON, ":", cur_line, cur_col))
            elif char == ";":
                self._advance()
                tokens.append(Token(TokenType.SEMICOLON, ";", cur_line, cur_col))
            elif char == ",":
                self._advance()
                tokens.append(Token(TokenType.COMMA, ",", cur_line, cur_col))
            elif char == "(":
                self._advance()
                tokens.append(Token(TokenType.LPAREN, "(", cur_line, cur_col))
            elif char == ")":
                self._advance()
                tokens.append(Token(TokenType.RPAREN, ")", cur_line, cur_col))
            elif char == "{":
                self._advance()
                tokens.append(Token(TokenType.LBRACE, "{", cur_line, cur_col))
            elif char == "}":
                self._advance()
                tokens.append(Token(TokenType.RBRACE, "}", cur_line, cur_col))
            elif char == "[":
                self._advance()
                tokens.append(Token(TokenType.LBRACKET, "[", cur_line, cur_col))
            elif char == "]":
                self._advance()
                tokens.append(Token(TokenType.RBRACKET, "]", cur_line, cur_col))
            else:
                raise SyntaxError(
                    f"Noma'lum belgi '{char}' qatorda {cur_line}, ustunda {cur_col}"
                )

        tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return tokens

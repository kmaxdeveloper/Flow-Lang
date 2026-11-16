from enum import Enum
from typing import Any


class TokenType(Enum):
    KEYWORD = "KEYWORD"
    KEYWORD_ELIF = "KEYWORD_ELIF"
    KEYWORD_MATCH = "KEYWORD_MATCH"
    KEYWORD_STEP = "KEYWORD_STEP"
    KEYWORD_LIVE = "KEYWORD_LIVE"
    TYPE = "TYPE"
    IDENTIFIER = "IDENTIFIER"
    INT_LITERAL = "INT_LITERAL"
    FLOAT_LITERAL = "FLOAT_LITERAL"
    STRING_LITERAL = "STRING_LITERAL"
    BOOL_LITERAL = "BOOL_LITERAL"

    # Punctuation & Assignment
    ASSIGN = "ASSIGN"               # =
    PLUS_ASSIGN = "PLUS_ASSIGN"     # +=
    MINUS_ASSIGN = "MINUS_ASSIGN"   # -=
    STAR_ASSIGN = "STAR_ASSIGN"     # *=
    SLASH_ASSIGN = "SLASH_ASSIGN"   # /=

    COLON = "COLON"                 # :
    SEMICOLON = "SEMICOLON"         # ;
    COMMA = "COMMA"                 # ,
    DOTDOT = "DOTDOT"               # ..
    DOT = "DOT"                     # .
    LPAREN = "LPAREN"               # (
    RPAREN = "RPAREN"               # )
    LBRACE = "LBRACE"               # {
    RBRACE = "RBRACE"               # }
    LBRACKET = "LBRACKET"           # [
    RBRACKET = "RBRACKET"           # ]

    # OOP & Functional
    FAT_ARROW = "FAT_ARROW"         # =>
    PIPELINE = "PIPELINE"           # |>
    NULL_LITERAL = "NULL_LITERAL"   # null

    # Arithmetic Operators
    PLUS = "PLUS"                   # +
    MINUS = "MINUS"                 # -
    STAR = "STAR"                   # *
    SLASH = "SLASH"                 # /
    PERCENT = "PERCENT"             # %

    # Comparison Operators
    EQ = "EQ"                       # ==
    NEQ = "NEQ"                     # !=
    GT = "GT"                       # >
    LT = "LT"                       # <
    GTE = "GTE"                     # >=
    LTE = "LTE"                     # <=

    # Logical Operators
    AND = "AND"                     # &&
    OR = "OR"                       # ||
    NOT = "NOT"                     # !

    EOF = "EOF"


KEYWORDS = {
    "fn",
    "inner",
    "var",
    "val",
    "return",
    "if",
    "elif",
    "else",
    "match",
    "while",
    "for",
    "in",
    "print",
    "class",
    "this",
    "new",
    "null",
    "step",
    "live",
}

TYPES = {
    "Int",
    "Double",
    "Float",
    "Short",
    "Byte",
    "Boolean",
    "String",
    "Void",
}


class Token:
    def __init__(self, token_type: TokenType, value: Any, line: int, column: int):
        self.type = token_type
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {repr(self.value)}, line={self.line}, col={self.column})"

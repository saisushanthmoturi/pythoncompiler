# Stage 1: Lexical Analysis
# Reads raw source text and breaks it into tokens (smallest meaningful pieces).
# Also builds a Symbol Table listing every identifier found.
#
# Example:  "let x = 10 + 5;"
# Tokens:   [LET, IDENT(x), ASSIGN, NUMBER(10), PLUS, NUMBER(5), SEMICOLON]

from dataclasses import dataclass, field
from typing import List, Dict


# ── All token type names ──────────────────────────────────────────────────────
class TokenType:
    NUMBER = "NUMBER"; STRING = "STRING"; BOOL = "BOOL"
    IDENT  = "IDENT"
    LET    = "LET";   IF     = "IF";    ELSE  = "ELSE"
    WHILE  = "WHILE"; PRINT  = "PRINT"
    TRUE   = "TRUE";  FALSE  = "FALSE"
    NOT    = "NOT";   AND    = "AND";   OR    = "OR"
    TYPE_INT = "INT"; TYPE_FLOAT = "FLOAT"
    TYPE_STRING = "STRING_TYPE"; TYPE_BOOL = "BOOL_TYPE"
    PLUS="+"; MINUS="-"; STAR="*"; SLASH="/"; PERCENT="%"
    EQ="=="; NEQ="!="; LT="<"; GT=">"; LEQ="<="; GEQ=">="
    ASSIGN = "ASSIGN"
    LPAREN="("; RPAREN=")"; LBRACE="{"; RBRACE="}"
    SEMICOLON=";"; COLON=":"; EOF="EOF"


@dataclass
class Token:
    type:  str
    value: object
    line:  int   # line number in source (for error messages)

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


# Keywords: map word → token type
KEYWORDS = {
    "let": TokenType.LET,    "if":    TokenType.IF,
    "else":TokenType.ELSE,   "while": TokenType.WHILE,
    "print":TokenType.PRINT, "true":  TokenType.TRUE,
    "false":TokenType.FALSE,  "not":   TokenType.NOT,
    "and": TokenType.AND,    "or":    TokenType.OR,
    "int": TokenType.TYPE_INT, "float": TokenType.TYPE_FLOAT,
    "string": TokenType.TYPE_STRING, "bool": TokenType.TYPE_BOOL,
}


# ── Symbol Table (Lexer level) ────────────────────────────────────────────────
# Tracks every identifier: name, whether it's a keyword, first line seen, count.

@dataclass
class SymbolEntry:
    name:       str
    category:   str        # "IDENTIFIER" or "KEYWORD"
    first_line: int
    lines:      List[int] = field(default_factory=list)

    @property
    def occurrences(self):
        return len(self.lines)


class LexerSymbolTable:
    def __init__(self):
        self._table: Dict[str, SymbolEntry] = {}

    def insert(self, name: str, category: str, line: int):
        if name not in self._table:
            self._table[name] = SymbolEntry(name, category, line, [line])
        else:
            self._table[name].lines.append(line)

    def entries(self) -> List[SymbolEntry]:
        return sorted(self._table.values(), key=lambda e: e.first_line)

    def display(self) -> str:
        rows = self.entries()
        if not rows:
            return "  (empty)"
        w = max(len(r.name) for r in rows)
        w = max(w, 6)
        out  = (f"  ┌{'─'*(w+2)}┬{'─'*14}┬{'─'*12}┬{'─'*13}┐\n"
                f"  │ {'Symbol':<{w}} │ {'Category':12} │ {'First Line':10} │ {'Occurrences':11} │\n"
                f"  ├{'─'*(w+2)}┼{'─'*14}┼{'─'*12}┼{'─'*13}┤\n")
        for r in rows:
            out += (f"  │ {r.name:<{w}} │ {r.category:12} │ "
                    f"{'line '+str(r.first_line):10} │ {r.occurrences:11} │\n")
        out += f"  └{'─'*(w+2)}┴{'─'*14}┴{'─'*12}┴{'─'*13}┘"
        return out


# ── Lexer ─────────────────────────────────────────────────────────────────────

class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.tokens: List[Token] = []
        self.symbol_table = LexerSymbolTable()

    # helpers: current char, peek ahead, advance, add token
    def _cur(self):  return self.source[self.pos] if self.pos < len(self.source) else ""
    def _peek(self): return self.source[self.pos+1] if self.pos+1 < len(self.source) else ""
    def _adv(self):
        ch = self.source[self.pos]; self.pos += 1
        if ch == "\n": self.line += 1
        return ch
    def _add(self, t, v): self.tokens.append(Token(t, v, self.line))

    def _skip(self):
        # skip spaces, tabs, newlines, and # comments
        while self.pos < len(self.source):
            c = self._cur()
            if c in " \t\r\n": self._adv()
            elif c == "#":
                while self.pos < len(self.source) and self._cur() != "\n": self._adv()
            else: break

    def _number(self):
        s = self.pos; is_float = False
        while self._cur().isdigit(): self._adv()
        if self._cur() == "." and self._peek().isdigit():
            is_float = True; self._adv()
            while self._cur().isdigit(): self._adv()
        raw = self.source[s:self.pos]
        self._add(TokenType.NUMBER, float(raw) if is_float else int(raw))

    def _string(self):
        self._adv(); chars = []     # skip opening "
        while self._cur() and self._cur() != '"':
            if self._cur() == "\\" and self._peek() == '"': self._adv()
            chars.append(self._adv())
        if not self._cur(): raise LexerError(f"Unterminated string at line {self.line}")
        self._adv()                 # skip closing "
        self._add(TokenType.STRING, "".join(chars))

    def _ident(self):
        s = self.pos
        while self._cur().isalnum() or self._cur() == "_": self._adv()
        name  = self.source[s:self.pos]
        ttype = KEYWORDS.get(name, TokenType.IDENT)

        if   ttype == TokenType.TRUE:  self._add(TokenType.BOOL, True)
        elif ttype == TokenType.FALSE: self._add(TokenType.BOOL, False)
        else:                          self._add(ttype, name)

        # record in symbol table
        cat = "KEYWORD" if name in KEYWORDS else "IDENTIFIER"
        self.symbol_table.insert(name, cat, self.line)

    def tokenize(self) -> List[Token]:
        # two-char operators
        TWO = {"==": TokenType.EQ, "!=": TokenType.NEQ,
               "<=": TokenType.LEQ, ">=": TokenType.GEQ}
        # single-char operators / delimiters
        ONE = {"=": TokenType.ASSIGN, "<": TokenType.LT, ">": TokenType.GT,
               "+": TokenType.PLUS,  "-": TokenType.MINUS,
               "*": TokenType.STAR,  "/": TokenType.SLASH, "%": TokenType.PERCENT,
               "(": TokenType.LPAREN,")" :TokenType.RPAREN,
               "{": TokenType.LBRACE,"}": TokenType.RBRACE,
               ";": TokenType.SEMICOLON, ":": TokenType.COLON}

        while self.pos < len(self.source):
            self._skip()
            if self.pos >= len(self.source): break
            c   = self._cur()
            two = c + self._peek()
            if   two in TWO:       self._adv(); self._adv(); self._add(TWO[two], two)
            elif c.isdigit():      self._number()
            elif c == '"':         self._string()
            elif c.isalpha() or c == "_": self._ident()
            elif c in ONE:         self._adv(); self._add(ONE[c], c)
            else: raise LexerError(f"Unknown character {c!r} at line {self.line}")

        self._add(TokenType.EOF, None)
        return self.tokens

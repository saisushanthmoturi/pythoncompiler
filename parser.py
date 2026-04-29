# Stage 2: Syntax Analysis
# Converts tokens into an Abstract Syntax Tree (AST).
from ast_nodes import *
from lexer import Token, TokenType
from typing import List, Optional

class ParseError(Exception):
    pass

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self._peek()
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _check(self, ttype: str) -> bool:
        return self._peek().type == ttype

    def _match(self, ttype: str) -> bool:
        if self._check(ttype):
            self._advance()
            return True
        return False

    def _consume(self, ttype: str, msg: str) -> Token:
        if self._check(ttype):
            return self._advance()
        tok = self._peek()
        raise ParseError(f"Line {tok.line}: {msg} (got {tok.type})")

    def parse(self) -> ProgramNode:
        prog = ProgramNode()
        while not self._check(TokenType.EOF):
            prog.statements.append(self._statement())
        return prog

    def _statement(self) -> ASTNode:
        if self._check(TokenType.LET):
            return self._var_decl()
        if self._check(TokenType.IF):
            return self._if_stmt()
        if self._check(TokenType.WHILE):
            return self._while_stmt()
        if self._check(TokenType.PRINT):
            return self._print_stmt()
        return self._assign_stmt()

    def _var_decl(self) -> VarDeclNode:
        self._consume(TokenType.LET, "Expected 'let'")
        name = self._consume(TokenType.IDENT, "Expected variable name").value
        vtype = None
        if self._match(TokenType.COLON):
            vtype = self._advance().value # int, float, etc
        self._consume(TokenType.ASSIGN, "Expected '='")
        val = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';'")
        return VarDeclNode(name, vtype, val)

    def _assign_stmt(self) -> AssignNode:
        name = self._consume(TokenType.IDENT, "Expected variable name").value
        self._consume(TokenType.ASSIGN, "Expected '='")
        val = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';'")
        return AssignNode(name, val)

    def _print_stmt(self) -> PrintNode:
        self._consume(TokenType.PRINT, "Expected 'print'")
        self._consume(TokenType.LPAREN, "Expected '('")
        expr = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')'")
        self._consume(TokenType.SEMICOLON, "Expected ';'")
        return PrintNode(expr)

    def _if_stmt(self) -> IfNode:
        self._consume(TokenType.IF, "Expected 'if'")
        self._consume(TokenType.LPAREN, "Expected '('")
        cond = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')'")
        then_b = self._block()
        else_b = []
        if self._match(TokenType.ELSE):
            else_b = self._block() if self._check(TokenType.LBRACE) else [self._statement()]
        return IfNode(cond, then_b, else_b)

    def _while_stmt(self) -> WhileNode:
        self._consume(TokenType.WHILE, "Expected 'while'")
        self._consume(TokenType.LPAREN, "Expected '('")
        cond = self._expression()
        self._consume(TokenType.RPAREN, "Expected ')'")
        body = self._block()
        return WhileNode(cond, body)

    def _block(self) -> List[ASTNode]:
        self._consume(TokenType.LBRACE, "Expected '{'")
        stmts = []
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            stmts.append(self._statement())
        self._consume(TokenType.RBRACE, "Expected '}'")
        return stmts

    # Expression parsing (recursive descent)
    def _expression(self) -> ASTNode: return self._or()

    def _or(self) -> ASTNode:
        node = self._and()
        while self._match(TokenType.OR):
            node = BinaryOpNode("or", node, self._and())
        return node

    def _and(self) -> ASTNode:
        node = self._equality()
        while self._match(TokenType.AND):
            node = BinaryOpNode("and", node, self._equality())
        return node

    def _equality(self) -> ASTNode:
        node = self._comparison()
        while self._peek().type in (TokenType.EQ, TokenType.NEQ):
            op = self._advance().value
            node = BinaryOpNode(op, node, self._comparison())
        return node

    def _comparison(self) -> ASTNode:
        node = self._addition()
        while self._peek().type in (TokenType.LT, TokenType.GT, TokenType.LEQ, TokenType.GEQ):
            op = self._advance().value
            node = BinaryOpNode(op, node, self._addition())
        return node

    def _addition(self) -> ASTNode:
        node = self._multiplication()
        while self._peek().type in (TokenType.PLUS, TokenType.MINUS):
            op = self._advance().value
            node = BinaryOpNode(op, node, self._multiplication())
        return node

    def _multiplication(self) -> ASTNode:
        node = self._unary()
        while self._peek().type in (TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op = self._advance().value
            node = BinaryOpNode(op, node, self._unary())
        return node

    def _unary(self) -> ASTNode:
        if self._peek().type in (TokenType.MINUS, TokenType.NOT):
            op = self._advance().value
            return UnaryOpNode(op, self._unary())
        return self._primary()

    def _primary(self) -> ASTNode:
        tok = self._peek()
        if self._match(TokenType.NUMBER): return NumberNode(tok.value, tok.line)
        if self._match(TokenType.STRING): return StringNode(tok.value, tok.line)
        if self._match(TokenType.BOOL):   return BoolNode(tok.value, tok.line)
        if self._match(TokenType.IDENT):  return IdentifierNode(tok.value, tok.line)
        if self._match(TokenType.LPAREN):
            node = self._expression()
            self._consume(TokenType.RPAREN, "Expected ')'")
            return node
        raise ParseError(f"Line {tok.line}: Expected expression, got {tok.type}")

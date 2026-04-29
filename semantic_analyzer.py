# Stage 3: Semantic Analysis
# Checks for errors like undefined variables or type mismatches.
from ast_nodes import *
from typing import Dict, List, Optional

class SemanticError(Exception):
    pass

class SymbolTable:
    # Stack of dicts to handle nested scopes
    def __init__(self):
        self._scopes: List[Dict[str, str]] = [{}]

    def push(self): self._scopes.append({})
    def pop(self):  self._scopes.pop()

    def define(self, name: str, dtype: str, line: int):
        if name in self._scopes[-1]:
            raise SemanticError(f"Line {line}: Variable '{name}' already defined in this scope")
        self._scopes[-1][name] = dtype

    def lookup(self, name: str) -> Optional[str]:
        for scope in reversed(self._scopes):
            if name in scope: return scope[name]
        return None

class SemanticAnalyzer:
    def __init__(self):
        self.symbols = SymbolTable()

    def analyze(self, node: ASTNode):
        self._visit(node)

    def _visit(self, node):
        method = f"_check_{type(node).__name__}"
        return getattr(self, method)(node)

    def _check_ProgramNode(self, n):
        for s in n.statements: self._visit(s)

    def _check_VarDeclNode(self, n):
        val_type = self._visit(n.value)
        decl_type = n.var_type or val_type
        if n.var_type and n.var_type != val_type:
            raise SemanticError(f"Line {n.line}: Cannot assign {val_type} to {n.var_type} variable '{n.name}'")
        self.symbols.define(n.name, decl_type, n.line)

    def _check_AssignNode(self, n):
        val_type = self._visit(n.value)
        var_type = self.symbols.lookup(n.name)
        if not var_type:
            raise SemanticError(f"Line {n.line}: Undefined variable '{n.name}'")
        if var_type != val_type:
            raise SemanticError(f"Line {n.line}: Cannot assign {val_type} to {var_type} variable '{n.name}'")

    def _check_PrintNode(self, n):
        self._visit(n.expression)

    def _check_IfNode(self, n):
        if self._visit(n.condition) != "bool":
            raise SemanticError(f"Line {n.line}: 'if' condition must be bool")
        self.symbols.push()
        for s in n.then_body: self._visit(s)
        self.symbols.pop()
        self.symbols.push()
        for s in n.else_body: self._visit(s)
        self.symbols.pop()

    def _check_WhileNode(self, n):
        if self._visit(n.condition) != "bool":
            raise SemanticError(f"Line {n.line}: 'while' condition must be bool")
        self.symbols.push()
        for s in n.body: self._visit(s)
        self.symbols.pop()

    def _check_BinaryOpNode(self, n):
        l, r = self._visit(n.left), self._visit(n.right)
        if n.operator in ("+", "-", "*", "/", "%"):
            if l not in ("int", "float") or r not in ("int", "float"):
                raise SemanticError(f"Line {n.line}: Math ops need numbers, got {l} and {r}")
            return "float" if (l == "float" or r == "float") else "int"
        if n.operator in ("<", ">", "<=", ">="):
            if l not in ("int", "float") or r not in ("int", "float"):
                raise SemanticError(f"Line {n.line}: Comparisons need numbers")
            return "bool"
        if n.operator in ("==", "!="):
            if l != r: raise SemanticError(f"Line {n.line}: Cannot compare {l} with {r}")
            return "bool"
        if n.operator in ("and", "or"):
            if l != "bool" or r != "bool": raise SemanticError(f"Line {n.line}: Logic ops need bools")
            return "bool"
        return "any"

    def _check_UnaryOpNode(self, n):
        t = self._visit(n.operand)
        if n.operator == "-":
            if t not in ("int", "float"): raise SemanticError(f"Line {n.line}: '-' needs a number")
            return t
        if n.operator == "not":
            if t != "bool": raise SemanticError(f"Line {n.line}: 'not' needs a bool")
            return "bool"
        return "any"

    def _check_NumberNode(self, n): return "float" if isinstance(n.value, float) else "int"
    def _check_StringNode(self, n): return "string"
    def _check_BoolNode(self, n):   return "bool"
    def _check_IdentifierNode(self, n):
        t = self.symbols.lookup(n.name)
        if not t: raise SemanticError(f"Line {n.line}: Undefined variable '{n.name}'")
        return t

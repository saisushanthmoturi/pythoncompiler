# Stage 1 data: every piece of source code becomes one of these nodes.

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ASTNode:
    pass  # base class for all tree nodes


# --- Literal values ---

@dataclass
class NumberNode(ASTNode):
    value: Any       # e.g. 42 or 3.14
    line: int = 0

@dataclass
class StringNode(ASTNode):
    value: str       # e.g. "hello"
    line: int = 0

@dataclass
class BoolNode(ASTNode):
    value: bool      # True or False
    line: int = 0

@dataclass
class IdentifierNode(ASTNode):
    name: str        # variable name, e.g. "x"
    line: int = 0


# --- Expressions ---

@dataclass
class BinaryOpNode(ASTNode):
    operator: str    # +, -, *, /, ==, <, >, etc.
    left: ASTNode
    right: ASTNode
    line: int = 0

@dataclass
class UnaryOpNode(ASTNode):
    operator: str    # - or not
    operand: ASTNode
    line: int = 0


# --- Statements ---

@dataclass
class VarDeclNode(ASTNode):
    name: str
    var_type: Optional[str]   # "int", "float", "string", "bool", or None
    value: ASTNode
    line: int = 0

@dataclass
class AssignNode(ASTNode):
    name: str
    value: ASTNode
    line: int = 0

@dataclass
class PrintNode(ASTNode):
    expression: ASTNode
    line: int = 0

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    then_body: List[ASTNode] = field(default_factory=list)
    else_body: List[ASTNode] = field(default_factory=list)
    line: int = 0

@dataclass
class WhileNode(ASTNode):
    condition: ASTNode
    body: List[ASTNode] = field(default_factory=list)
    line: int = 0

@dataclass
class BlockNode(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)

@dataclass
class ProgramNode(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)  # root of the tree

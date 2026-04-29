# Stage 4: Intermediate Code Generation
# Translates AST into Three-Address Code (TAC), Quadruples, and Triples.
from dataclasses import dataclass
from ast_nodes import *
from typing import List, Any, Optional

# --- TAC Instruction Types ---
class TACInstruction: pass

@dataclass
class TACAssign(TACInstruction):
    result: str; value: Any
    def __str__(self): return f"    {self.result} = {self.value}"

@dataclass
class TACBinOp(TACInstruction):
    result: str; left: Any; op: str; right: Any
    def __str__(self): return f"    {self.result} = {self.left} {self.op} {self.right}"

@dataclass
class TACUnaryOp(TACInstruction):
    result: str; op: str; operand: Any
    def __str__(self): return f"    {self.result} = {self.op}{self.operand}"

@dataclass
class TACLabel(TACInstruction):
    name: str
    def __str__(self): return f"{self.name}:"

@dataclass
class TACJump(TACInstruction):
    label: str
    def __str__(self): return f"    GOTO {self.label}"

@dataclass
class TACCondJump(TACInstruction):
    condition: Any; label: str
    def __str__(self): return f"    IF {self.condition} == 0 GOTO {self.label}"

@dataclass
class TACPrint(TACInstruction):
    operand: Any
    def __str__(self): return f"    PRINT {self.operand}"

@dataclass
class TACCopy(TACInstruction):
    dest: str; src: Any
    def __str__(self): return f"    {self.dest} = {self.src}"

# --- Quadruples and Triples tables ---
@dataclass
class Quadruple:
    index: int; op: str; arg1: str; arg2: str; result: str
    def row(self):
        return f"  │ {self.index:3d} │ {self.op:8} │ {str(self.arg1):8} │ {str(self.arg2):8} │ {str(self.result):8} │"

@dataclass
class Triple:
    index: int; op: str; arg1: str; arg2: str
    def row(self):
        return f"  │ {self.index:3d} │ {self.op:8} │ {str(self.arg1):8} │ {str(self.arg2):8} │"

def quad_header(): return "  ┌─────┬──────────┬──────────┬──────────┬──────────┐\n  │  #  │ Op       │ Arg1     │ Arg2     │ Result   │\n  ├─────┼──────────┼──────────┼──────────┼──────────┤"
def quad_footer(): return "  └─────┴──────────┴──────────┴──────────┴──────────┘"
def triple_header(): return "  ┌─────┬──────────┬──────────┬──────────┐\n  │  #  │ Op       │ Arg1     │ Arg2     │\n  ├─────┼──────────┼──────────┼──────────┤"
def triple_footer(): return "  └─────┴──────────┴──────────┴──────────┘"

def to_quadruples(instructions: List[TACInstruction]) -> List[Quadruple]:
    quads = []
    for i, ins in enumerate(instructions):
        if   isinstance(ins, TACAssign):  quads.append(Quadruple(i, "LOAD", str(ins.value), "_", ins.result))
        elif isinstance(ins, TACCopy):    quads.append(Quadruple(i, ":=", str(ins.src), "_", ins.dest))
        elif isinstance(ins, TACBinOp):   quads.append(Quadruple(i, ins.op, str(ins.left), str(ins.right), ins.result))
        elif isinstance(ins, TACUnaryOp): quads.append(Quadruple(i, ins.op.strip(), str(ins.operand), "_", ins.result))
        elif isinstance(ins, TACLabel):   quads.append(Quadruple(i, "LABEL", ins.name, "_", "_"))
        elif isinstance(ins, TACJump):    quads.append(Quadruple(i, "JMP", ins.label, "_", "_"))
        elif isinstance(ins, TACCondJump): quads.append(Quadruple(i, "JZ", str(ins.condition), ins.label, "_"))
        elif isinstance(ins, TACPrint):   quads.append(Quadruple(i, "PRINT", str(ins.operand), "_", "_"))
    return quads

def to_triples(instructions: List[TACInstruction]) -> List[Triple]:
    res_to_idx = {}
    triples = []
    def _ref(v): return f"({res_to_idx[v]})" if v in res_to_idx else str(v)
    for i, ins in enumerate(instructions):
        t = None
        if isinstance(ins, TACAssign):
            t = Triple(i, "LOAD", str(ins.value), "_"); res_to_idx[ins.result] = i
        elif isinstance(ins, TACCopy):
            t = Triple(i, ":=", _ref(str(ins.src)), "_"); res_to_idx[ins.dest] = i
        elif isinstance(ins, TACBinOp):
            t = Triple(i, ins.op, _ref(str(ins.left)), _ref(str(ins.right))); res_to_idx[ins.result] = i
        elif isinstance(ins, TACUnaryOp):
            t = Triple(i, ins.op.strip(), _ref(str(ins.operand)), "_"); res_to_idx[ins.result] = i
        elif isinstance(ins, TACLabel):   t = Triple(i, "LABEL", ins.name, "_")
        elif isinstance(ins, TACJump):    t = Triple(i, "JMP", ins.label, "_")
        elif isinstance(ins, TACCondJump): t = Triple(i, "JZ", _ref(str(ins.condition)), ins.label)
        elif isinstance(ins, TACPrint):   t = Triple(i, "PRINT", _ref(str(ins.operand)), "_")
        if t: triples.append(t)
    return triples

# --- IR Generator ---
class IRGenerator:
    def __init__(self):
        self.instructions: List[TACInstruction] = []
        self._tc = 0; self._lc = 0

    def _tmp(self): n = f"t{self._tc}"; self._tc += 1; return n
    def _lbl(self): n = f"L{self._lc}"; self._lc += 1; return n
    def _emit(self, i): self.instructions.append(i)

    def generate(self, node: ASTNode):
        self._visit(node); return self.instructions

    def _visit(self, node): return getattr(self, f"_gen_{type(node).__name__}")(node)

    def _gen_ProgramNode(self, n):
        for s in n.statements: self._visit(s)
    def _gen_VarDeclNode(self, n):
        src = self._visit(n.value); self._emit(TACCopy(n.name, src))
    def _gen_AssignNode(self, n):
        src = self._visit(n.value); self._emit(TACCopy(n.name, src))
    def _gen_PrintNode(self, n):
        op = self._visit(n.expression); self._emit(TACPrint(op))
    def _gen_IfNode(self, n):
        cond = self._visit(n.condition); else_l, end_l = self._lbl(), self._lbl()
        self._emit(TACCondJump(cond, else_l))
        for s in n.then_body: self._visit(s)
        self._emit(TACJump(end_l))
        self._emit(TACLabel(else_l))
        for s in n.else_body: self._visit(s)
        self._emit(TACLabel(end_l))
    def _gen_WhileNode(self, n):
        loop_l, end_l = self._lbl(), self._lbl()
        self._emit(TACLabel(loop_l))
        cond = self._visit(n.condition)
        self._emit(TACCondJump(cond, end_l))
        for s in n.body: self._visit(s)
        self._emit(TACJump(loop_l)); self._emit(TACLabel(end_l))
    def _gen_NumberNode(self, n):
        t = self._tmp(); self._emit(TACAssign(t, n.value)); return t
    def _gen_StringNode(self, n):
        t = self._tmp(); self._emit(TACAssign(t, repr(n.value))); return t
    def _gen_BoolNode(self, n):
        t = self._tmp(); self._emit(TACAssign(t, 1 if n.value else 0)); return t
    def _gen_IdentifierNode(self, n): return n.name
    def _gen_UnaryOpNode(self, n):
        op = self._visit(n.operand); t = self._tmp(); self._emit(TACUnaryOp(t, n.operator+" ", op)); return t
    def _gen_BinaryOpNode(self, n):
        l, r = self._visit(n.left), self._visit(n.right); t = self._tmp(); self._emit(TACBinOp(t, l, n.operator, r)); return t

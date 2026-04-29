# MiniPy Compiler Orchestrator
# Connects all 6 stages of the compiler pipeline.
import sys, os
from lexer import Lexer, LexerError
from parser import Parser, ParseError
from semantic_analyzer import SemanticAnalyzer, SemanticError
from ir_generator import *
from optimizer import Optimizer
from code_generator import AssemblyGenerator
from ast_nodes import *

DEMO = """
let a: int = 10;
let b: int = 3;
let msg: string = "Hello MiniPy!";
let sum = a + b;
print(msg);
print(sum);
if (a > b) { print(a); } else { print(b); }
let i = 1;
while (i <= 3) { print(i); i = i + 1; }
"""

def _banner(t): print(f"\n{'='*70}\n{t.center(70)}\n{'='*70}")
def _section(t): print(f"\n--- {t} {'-'*(65-len(t))}")

def _ast_tree(node, prefix="", last=True):
    # Prints a visual tree of the AST nodes
    conn = "└── " if last else "├── "
    cpref = prefix + ("    " if last else "│   ")
    def _lbl(n):
        if isinstance(n, VarDeclNode): return f"VarDecl({n.name}, {n.var_type})"
        if isinstance(n, AssignNode):  return f"Assign({n.name})"
        if isinstance(n, NumberNode):  return f"Number({n.value})"
        if isinstance(n, IdentifierNode): return f"Ident({n.name})"
        return type(n).__name__.replace("Node", "")
    print(f"{prefix}{conn}{_lbl(node)}")
    children = []
    if   isinstance(node, VarDeclNode):  children = [node.value]
    elif isinstance(node, AssignNode):   children = [node.value]
    elif isinstance(node, PrintNode):    children = [node.expression]
    elif isinstance(node, IfNode):       children = [node.condition] + node.then_body + node.else_body
    elif isinstance(node, WhileNode):    children = [node.condition] + node.body
    elif isinstance(node, BinaryOpNode): children = [node.left, node.right]
    elif isinstance(node, ProgramNode):  children = node.statements
    for i, c in enumerate(children): _ast_tree(c, cpref, i == len(children)-1)

def compile_source(source, verbose=True):
    _banner("MiniPy Compiler Pipeline")

    # Stage 1: Lexing
    _section("Stage 1: Lexical Analysis")
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    print(f"Produced {len(tokens)} tokens.")
    print(lexer.symbol_table.display())

    # Stage 2: Parsing
    _section("Stage 2: Syntax Analysis")
    parser = Parser(tokens)
    ast = parser.parse()
    _ast_tree(ast)

    # Stage 3: Semantic Analysis
    _section("Stage 3: Semantic Analysis")
    analyzer = SemanticAnalyzer(); analyzer.analyze(ast)
    print("Semantic checks passed.")

    # Stage 4: IR Generation
    _section("Stage 4: IR Generation")
    ir_gen = IRGenerator(); raw_ir = ir_gen.generate(ast)
    print(f"Generated {len(raw_ir)} TAC instructions.")
    for ins in raw_ir: print(ins)
    print("\nQuadruples Table:"); print(quad_header())
    for q in to_quadruples(raw_ir): print(q.row())
    print(quad_footer())

    # Stage 5: Optimization
    _section("Stage 5: Optimization")
    opt = Optimizer(); opt_ir = opt.optimize(raw_ir)
    for p in opt.PASSES:
        logs = opt.log.for_pass(p)
        if logs: print(f"[{p}] {' | '.join(logs)}")
    print(f"Optimized {len(raw_ir)} -> {len(opt_ir)} instructions.")

    # Stage 6: Code Generation
    _section("Stage 6: Code Generation")
    asm_gen = AssemblyGenerator(); asm = asm_gen.generate(opt_ir)
    print("FIFO Register Allocation Log:"); print(asm_gen.alloc.alloc_log_table())
    print("\nAssembly Output:"); print(asm)
    return asm

if __name__ == "__main__":
    src = DEMO
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1]) as f: src = f.read()
    compile_source(src)

# 🔬 MiniPy Compiler

A complete, educational mini-compiler written in **Python** that compiles a
simple custom language (MiniPy) through **all 6 classical stages** of a
compiler, producing executable Python as its target.

---

## 📁 Project Structure

```
compiler/
├── ast_nodes.py           # AST node dataclasses (all language constructs)
├── lexer.py               # Stage 1 — Lexical Analysis (Tokenizer)
├── parser.py              # Stage 2 — Syntax Analysis (Recursive-Descent Parser)
├── semantic_analyzer.py   # Stage 3 — Semantic Analysis (Type Checker)
├── ir_generator.py        # Stage 4 — Intermediate Code Generation (TAC)
├── optimizer.py           # Stage 5 — Code Optimization (2 passes)
├── code_generator.py      # Stage 6 — Code Generation (→ Python)
├── main.py                # Entry point — runs the full pipeline
└── sample.minipy          # Example MiniPy source file
```

---

## 🚀 Quick Start

```bash
# Run the built-in demo (shows all stages)
python main.py

# Compile your own file
python main.py sample.minipy

# Save generated code to output.py
python main.py sample.minipy --save
```

---

## 🗺️ The 6 Compiler Stages

### Stage 1 — Lexical Analysis (`lexer.py`)

> **Input:** raw source text  
> **Output:** flat list of `Token` objects

The **Lexer** (also called a *scanner* or *tokenizer*) reads the source
character by character and groups characters into the smallest meaningful
units called **tokens**.

```
Source:   let x = 10 + 5;
Tokens:   [LET, IDENT("x"), ASSIGN, NUMBER(10), PLUS, NUMBER(5), SEMICOLON]
```

Key concepts implemented:
- Keyword recognition (`let`, `if`, `while`, `print`, `true`, `false`, …)
- Number literals (integers and floats)
- String literals (double-quoted)
- Two-character operators (`==`, `!=`, `<=`, `>=`)
- Single-line comments (`# …`)
- Line number tracking for error messages

---

### Stage 2 — Syntax Analysis (`parser.py`)

> **Input:** list of tokens  
> **Output:** Abstract Syntax Tree (AST)

The **Parser** checks that tokens follow the grammar rules and builds a
hierarchical tree structure called the **Abstract Syntax Tree (AST)**.

```
Source:   a + b * 3
AST:
    BinOp(+)
    ├── Ident(a)
    └── BinOp(*)
        ├── Ident(b)
        └── Number(3)
```

This is a **hand-written Recursive-Descent Parser** — each grammar rule
has a corresponding method. Operator precedence is handled by the calling
order: `or → and → equality → comparison → addition → multiplication → unary → primary`.

---

### Stage 3 — Semantic Analysis (`semantic_analyzer.py`)

> **Input:** AST  
> **Output:** annotated AST (with type information) or error

The **Semantic Analyzer** enforces rules that cannot be expressed in a
context-free grammar:

| Check | Example Error |
|---|---|
| Scope — use before declaration | `print(x);` before `let x = 1;` |
| Duplicate declaration | `let x = 1; let x = 2;` |
| Type mismatch | `let x: int = "hello";` |
| Operator type rule | `"hello" - 3` |
| Condition type | `if (3.14) { … }` |

Uses a **scoped symbol table** (stack of dicts) to track variable names
and types across nested blocks.

---

### Stage 4 — IR Generation (`ir_generator.py`)

> **Input:** annotated AST  
> **Output:** list of Three-Address Code (TAC) instructions

The **IR Generator** walks the AST and emits flat **Three-Address Code**,
a classic Intermediate Representation where every instruction has at most
three operands: `result = operand1 OP operand2`.

```
Source:   area = pi * 5 * 5;
TAC:
    t0 = 5
    t1 = pi * t0
    t2 = 5
    t3 = t1 * t2
    area = t3
```

Control flow constructs like `if` and `while` become **labels** and
**conditional/unconditional jumps**:

```
Source:   if (x > 0) { print(x); }
TAC:
    t0 = x > 0
    IF t0 == 0 GOTO L0    ← jump if FALSE
    PRINT x
    GOTO L1
L0:
L1:
```

---

### Stage 5 — Optimization (`optimizer.py`)

> **Input:** raw TAC list  
> **Output:** optimized TAC list

Two classic optimization passes are applied:

#### Pass 1: Constant Folding
Evaluates constant expressions at **compile time** instead of runtime.

```
Before:  t0 = 3.14   t1 = 5   t2 = t0 * t1   t3 = 5   t4 = t2 * t3
After:   t0 = 3.14                             area = 78.5
```

**Safety:** Variables written more than once (e.g. loop counters) are
excluded from constant propagation to prevent incorrect optimizations.

#### Pass 2: Dead Code Elimination
Removes assignments to temporaries that are **never read** later.

```
Before:  t1 = 4   t2 = 7   PRINT t2    ← t1 never used
After:             t2 = 7   PRINT t2
```

---

### Stage 6 — Code Generation (`code_generator.py`)

> **Input:** optimized TAC list  
> **Output:** executable Python source code

The **Code Generator** translates TAC into clean Python. Since Python has
no `GOTO`, a **label-dispatch loop** with a `_goto` variable simulates
control flow:

```python
_goto = '_start'
while _goto != '_end':
    if _goto == '_start':
        _goto = None
        i = 1
        if _goto is None: _goto = 'L0'
    elif _goto == 'L0':
        _goto = None
        t0 = i <= 5
        if not t0: _goto = 'L1'
        if _goto is None:
            print(i)
            i = i + 1
            _goto = 'L0'
    elif _goto == 'L1':
        ...
```

Straight-line code (no branches) is emitted without the dispatch wrapper
for maximum readability.

---

## 🗣️ MiniPy Language Reference

### Variables
```
let x = 10;               # type inferred as int
let pi: float = 3.14;     # explicit type annotation
let name: string = "Bob"; # string variable
let flag: bool = true;    # boolean variable
```

### Types
| Type | Values |
|---|---|
| `int` | 0, 1, -5, 42 |
| `float` | 3.14, 2.0, -1.5 |
| `string` | "hello", "" |
| `bool` | true, false |

### Operators
| Category | Operators |
|---|---|
| Arithmetic | `+`, `-`, `*`, `/`, `%` |
| Comparison | `<`, `>`, `<=`, `>=`, `==`, `!=` |
| Logical | `and`, `or`, `not` |

### Control Flow
```
# If-else
if (x > 0) {
    print(x);
} else {
    print(0);
}

# While loop
let i = 1;
while (i <= 10) {
    print(i);
    i = i + 1;
}
```

### Print
```
print(x);
print(x + y * 2);
print("hello");
```

### Comments
```
# This is a comment
let x = 5;  # inline comment
```

---

## 🧪 Error Handling

The compiler gives clear, line-numbered error messages at each stage:

```
# Lexer Error
Unknown character '@' at line 3

# Parser Error
Line 5: Expected ';', got RBRACE ('}')

# Semantic Error
Line 8: Variable 'result' used before declaration.
Line 12: Type mismatch — declared 'int' but expression is 'string'.
```

---

## 📊 Example Output (Demo Program)

```
======================================================================
──────────  Program Output  (executing generated code)  ──────────────
======================================================================
Hello from MiniPy!
13
78.5
10
1
2
3
4
5
1
```

The optimizer reduced **57 → 39 TAC instructions** (18 removed) by
constant-folding arithmetic like `sum = a + b = 10 + 3 = 13` and
`area = pi × 5 × 5 = 78.5` entirely at compile time.

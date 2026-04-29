# Stage 6: Assembly Code Generation
# Translates TAC to RISC-style assembly using FIFO register allocation.
from collections import deque
from ir_generator import *
from typing import List, Dict, Optional, Tuple

NUM_REGS = 8
ALL_REGS = [f"R{i}" for i in range(NUM_REGS)]

class AllocEvent:
    def __init__(self, action, reg, name, fifo):
        self.action, self.reg, self.name, self.fifo = action, reg, name, list(fifo)
    def row(self):
        fstr = " -> ".join(self.fifo) if self.fifo else "(empty)"
        return f"  │ {self.action:6} │ {self.reg:4} │ {self.name:12} │ {fstr:<40} │"

class FIFOAllocator:
    # 8 registers (R0-R7). When full, evict oldest (FIFO).
    def __init__(self):
        self._free, self._fifo = deque(ALL_REGS), deque()
        self._var2reg, self._reg2var = {}, {}
        self.events, self.spills = [], []

    def _snap(self): return [f"{v}->{self._var2reg[v]}" for v in self._fifo if v in self._var2reg]

    def get(self, name: str) -> str:
        if name in self._var2reg:
            r = self._var2reg[name]; self.events.append(AllocEvent("REUSE", r, name, self._snap())); return r
        if self._free:
            r = self._free.popleft()
        else:
            old = self._fifo.popleft(); r = self._var2reg.pop(old); del self._reg2var[r]
            self.spills.append(old); self.events.append(AllocEvent("SPILL", r, old, self._snap()))
        self._var2reg[name], self._reg2var[r] = r, name; self._fifo.append(name)
        self.events.append(AllocEvent("ALLOC", r, name, self._snap())); return r

    def alloc_log_table(self):
        if not self.events: return "  (no allocations)"
        hdr = "  ┌────────┬──────┬──────────────┬──────────────────────────────────────────┐\n" \
              "  │ Action │ Reg  │ Variable     │ FIFO Queue (oldest -> newest)             │\n" \
              "  ├────────┼──────┼──────────────┼──────────────────────────────────────────┤\n"
        return hdr + "\n".join(e.row() for e in self.events) + "\n  └────────┴──────┴──────────────┴──────────────────────────────────────────┘"

class AssemblyGenerator:
    def __init__(self):
        self.alloc, self._lines, self._vars = FIFOAllocator(), [], set()

    def _emit(self, line, comment=""):
        self._lines.append(f"    {line:<35} ; {comment}" if comment else f"    {line}")

    def generate(self, instructions: List[TACInstruction]) -> str:
        for ins in instructions:
            if isinstance(ins, TACCopy) and not (ins.dest.startswith("t") and ins.dest[1:].isdigit()):
                self._vars.add(ins.dest)
        self._lines += ["; MiniPy Assembly Output", "", "section .data"]
        for v in sorted(self._vars): self._lines.append(f"    {v:<12} dw  0")
        self._lines += ["", "section .text", "    global _start", "", "_start:"]
        for ins in instructions: self._translate(ins)
        self._emit("HALT", "end")
        return "\n".join(self._lines) + "\n"

    def _operand(self, val):
        if isinstance(val, (int,float)): return f"#{val}"
        if isinstance(val, str) and val.startswith("'"): return val
        return self.alloc.get(str(val))

    def _translate(self, ins):
        if isinstance(ins, TACLabel): self._lines.append(f"{ins.name}:")
        elif isinstance(ins, TACAssign):
            r = self.alloc.get(ins.result); self._emit(f"MOV  {r}, #{ins.value}", f"{ins.result}={ins.value}")
        elif isinstance(ins, TACCopy):
            is_var = not (ins.dest.startswith("t") and ins.dest[1:].isdigit())
            if isinstance(ins.src, (int,float)):
                r = self.alloc.get(ins.dest); self._emit(f"MOV  {r}, #{ins.src}", f"{ins.dest}={ins.src}")
            else:
                rs = self.alloc.get(str(ins.src)); r = self.alloc.get(ins.dest)
                self._emit(f"MOV  {r}, {rs}", f"{ins.dest}={ins.src}")
                if is_var: self._emit(f"STORE [{ins.dest}], {r}")
        elif isinstance(ins, TACBinOp):
            rl, rr = self._operand(ins.left), self._operand(ins.right); rd = self.alloc.get(ins.result)
            if ins.op in {"<", ">", "<=", ">=", "==", "!="}:
                if rl.startswith("#"): t=self.alloc.get("_il"); self._emit(f"MOV  {t}, {rl}"); rl=t
                if rr.startswith("#"): t=self.alloc.get("_ir"); self._emit(f"MOV  {t}, {rr}"); rr=t
                smap = {"<":"SETLT", ">":"SETGT", "<=":"SETLE", ">=":"SETGE", "==":"SETEQ", "!=":"SETNE"}
                self._emit(f"CMP  {rl}, {rr}"); self._emit(f"{smap[ins.op]} {rd}", f"{ins.result}=comparison")
            else:
                m = {"+":"ADD","-":"SUB","*":"MUL","/":"DIV","%":"MOD","and":"AND","or":"OR"}.get(ins.op, ins.op.upper())
                if rl.startswith("#"): t=self.alloc.get("_il"); self._emit(f"MOV  {t}, {rl}"); rl=t
                if rr.startswith("#"): t=self.alloc.get("_ir"); self._emit(f"MOV  {t}, {rr}"); rr=t
                self._emit(f"{m:<4} {rd}, {rl}, {rr}", f"{ins.result}={ins.op}")
        elif isinstance(ins, TACUnaryOp):
            rs, rd = self._operand(ins.operand), self.alloc.get(ins.result)
            if rs.startswith("#"): t=self.alloc.get("_un"); self._emit(f"MOV  {t}, {rs}"); rs=t
            m = "NEG" if ins.op.strip() == "-" else "NOT"
            self._emit(f"{m}  {rd}, {rs}", f"{ins.result}=unary")
        elif isinstance(ins, TACCondJump):
            rc = self._operand(ins.condition)
            if rc.startswith("#"): t=self.alloc.get("_cj"); self._emit(f"MOV  {t}, {rc}"); rc=t
            self._emit(f"CMP  {rc}, #0"); self._emit(f"JZ   {ins.label}")
        elif isinstance(ins, TACJump): self._emit(f"JMP  {ins.label}")
        elif isinstance(ins, TACPrint):
            rc = self._operand(ins.operand)
            if rc.startswith("#"): t=self.alloc.get("_pr"); self._emit(f"MOV  {t}, {rc}"); rc=t
            self._emit(f"CALL print, {rc}")

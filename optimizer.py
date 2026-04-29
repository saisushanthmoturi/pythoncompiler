# Stage 5: Code Optimization
# Performs constant folding, propagation, CSE, and dead code elimination.
from ir_generator import *
from typing import Dict, List, Any, Optional, Tuple

def _write_counts(instructions: List[TACInstruction]) -> Dict[str, int]:
    wc = {}
    for ins in instructions:
        t = None
        if isinstance(ins, (TACAssign, TACBinOp, TACUnaryOp)): t = ins.result
        elif isinstance(ins, TACCopy): t = ins.dest
        if t: wc[t] = wc.get(t, 0) + 1
    return wc

def _used_names(instructions: List[TACInstruction]) -> set:
    used = set()
    for ins in instructions:
        if   isinstance(ins, TACBinOp):    used.update({str(ins.left), str(ins.right)})
        elif isinstance(ins, TACUnaryOp):  used.add(str(ins.operand))
        elif isinstance(ins, TACAssign):   used.add(str(ins.value))
        elif isinstance(ins, TACCopy):     used.add(str(ins.src))
        elif isinstance(ins, TACCondJump): used.add(str(ins.condition))
        elif isinstance(ins, TACPrint):    used.add(str(ins.operand))
    return used

class OptimizationLog:
    def __init__(self): self._entries = []
    def record(self, pass_name, desc): self._entries.append((pass_name, desc))
    def for_pass(self, pass_name): return [d for p, d in self._entries if p == pass_name]

class Optimizer:
    PASSES = ["Constant Folding", "Constant Propagation", "Copy Propagation", "CSE", "Dead Code Elimination"]
    def __init__(self):
        self.log = OptimizationLog()
        self.snapshots = {}

    def optimize(self, instructions: List[TACInstruction]) -> List[TACInstruction]:
        res = instructions
        res = self._pass_folding(res)
        res = self._pass_const_prop(res)
        res = self._pass_copy_prop(res)
        res = self._pass_cse(res)
        res = self._pass_dead_code(res)
        return res

    def _pass_folding(self, ins):
        ops = {"+":lambda a,b:a+b, "-":lambda a,b:a-b, "*":lambda a,b:a*b, "/":lambda a,b:a/b if b!=0 else None,
               "%":lambda a,b:a%b if b!=0 else None, "<":lambda a,b:int(a<b), ">":lambda a,b:int(a>b),
               "<=":lambda a,b:int(a<=b), ">=":lambda a,b:int(a>=b), "==":lambda a,b:int(a==b), "!=":lambda a,b:int(a!=b)}
        multi, consts, out = {k for k,v in _write_counts(ins).items() if v>1}, {}, []
        def _num(v):
            if isinstance(v, (int,float)): return v
            if v in consts and isinstance(consts[v], (int,float)): return consts[v]
            return None
        for i in ins:
            if isinstance(i, TACLabel):
                for k in list(consts): (consts.pop(k) if k in multi else None)
                out.append(i); continue
            if isinstance(i, TACAssign):
                v = i.value
                if v in consts: v = consts[v]; i = TACAssign(i.result, v)
                if isinstance(v, (int,float)) and i.result not in multi: consts[i.result] = v
                out.append(i)
            elif isinstance(i, TACCopy):
                s = i.src
                if s in consts: s = consts[s]; i = TACCopy(i.dest, s)
                if isinstance(s, (int,float)) and i.dest not in multi: consts[i.dest] = s
                elif i.dest in consts: del consts[i.dest]
                out.append(i)
            elif isinstance(i, TACBinOp):
                l, r = i.left, i.right
                if l in consts: l = consts[l]
                if r in consts: r = consts[r]
                nl, nr, fn = _num(l), _num(r), ops.get(i.op)
                if fn and nl is not None and nr is not None and i.result not in multi:
                    val = fn(nl, nr)
                    if val is not None:
                        if isinstance(val, float) and val.is_integer(): val = int(val)
                        self.log.record("Constant Folding", f"{i.result} = {l} {i.op} {r} -> {val}")
                        consts[i.result] = val; out.append(TACAssign(i.result, val)); continue
                if i.result in consts: del consts[i.result]
                out.append(TACBinOp(i.result, l, i.op, r))
            elif isinstance(i, TACCondJump):
                c = consts.get(i.condition, i.condition); out.append(TACCondJump(c, i.label))
            else: out.append(i)
        self.snapshots["Constant Folding"] = list(out); return out

    def _pass_const_prop(self, ins):
        multi, consts, out = {k for k,v in _write_counts(ins).items() if v>1}, {}, []
        _sub = lambda v: consts.get(v, v)
        for i in ins:
            if isinstance(i, TACLabel):
                for k in list(consts): (consts.pop(k) if k in multi else None)
                out.append(i); continue
            if isinstance(i, TACCopy):
                ns = _sub(i.src)
                if ns != i.src: self.log.record("Constant Propagation", f"{i.dest} = {i.src} -> {ns}")
                if isinstance(ns, (int,float)) and i.dest not in multi: consts[i.dest] = ns
                elif i.dest in consts: del consts[i.dest]
                out.append(TACCopy(i.dest, ns))
            elif isinstance(i, TACAssign):
                if isinstance(i.value, (int,float)) and i.result not in multi: consts[i.result] = i.value
                out.append(i)
            elif isinstance(i, TACBinOp):
                nl, nr = _sub(i.left), _sub(i.right)
                if nl != i.left or nr != i.right: self.log.record("Constant Propagation", f"{i.result} used {i.left},{i.right} -> {nl},{nr}")
                if i.result in consts: del consts[i.result]
                out.append(TACBinOp(i.result, nl, i.op, nr))
            elif isinstance(i, TACCondJump): out.append(TACCondJump(_sub(i.condition), i.label))
            elif isinstance(i, TACPrint): out.append(TACPrint(_sub(i.operand)))
            else: out.append(i)
        self.snapshots["Constant Propagation"] = list(out); return out

    def _pass_copy_prop(self, ins):
        multi, copies, out = {k for k,v in _write_counts(ins).items() if v>1}, {}, []
        _sub = lambda v: copies.get(v, v)
        for i in ins:
            if isinstance(i, TACLabel):
                copies = {k:v for k,v in copies.items() if k not in multi}; out.append(i); continue
            if isinstance(i, TACCopy):
                is_temp = i.dest.startswith("t") and i.dest[1:].isdigit()
                src = _sub(i.src) if isinstance(i.src, str) else i.src
                if is_temp and i.dest not in multi and isinstance(src, str): copies[i.dest] = src
                if i.dest in copies and copies[i.dest] != src: del copies[i.dest]
                out.append(TACCopy(i.dest, src))
            elif isinstance(i, TACBinOp):
                nl, nr = _sub(i.left), _sub(i.right)
                if nl != i.left or nr != i.right: self.log.record("Copy Propagation", f"{i.result} used {i.left},{i.right} -> {nl},{nr}")
                if i.result in copies: del copies[i.result]
                out.append(TACBinOp(i.result, nl, i.op, nr))
            elif isinstance(i, TACCondJump): out.append(TACCondJump(_sub(i.condition), i.label))
            elif isinstance(i, TACPrint): out.append(TACPrint(_sub(i.operand)))
            else: out.append(i)
        self.snapshots["Copy Propagation"] = list(out); return out

    def _pass_cse(self, ins):
        emap, out = {}, []
        for i in ins:
            if isinstance(i, TACLabel): emap.clear(); out.append(i); continue
            if isinstance(i, TACBinOp):
                key = (i.op, str(i.left), str(i.right))
                if key in emap:
                    old = emap[key]; self.log.record("CSE", f"{i.result} reused {old}")
                    out.append(TACCopy(i.result, old))
                else: emap[key] = i.result; out.append(i)
            else:
                if isinstance(i, TACCopy): emap = {k:v for k,v in emap.items() if i.dest not in k[1:]}
                out.append(i)
        self.snapshots["CSE"] = list(out); return out

    def _pass_dead_code(self, ins):
        used, out = _used_names(ins), []
        for i in ins:
            if isinstance(i, (TACAssign, TACBinOp, TACUnaryOp)): t = i.result
            elif isinstance(i, TACCopy): t = i.dest
            else: out.append(i); continue
            if t.startswith("t") and t[1:].isdigit() and t not in used:
                self.log.record("Dead Code Elimination", f"Removed {i}"); continue
            out.append(i)
        self.snapshots["Dead Code Elimination"] = list(out); return out

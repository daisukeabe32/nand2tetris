# SymbolTable.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Symbol:
    type: str
    kind: str   # "static" | "field" | "arg" | "var"
    index: int

class SymbolTable:
    """
    Two-level symbol table:
      - class scope:  static, field
      - subroutine scope: arg, var
    """
    CLASS_KINDS = {"static", "field"}
    SUB_KINDS = {"arg", "var"}

    def __init__(self) -> None:
        self.class_scope: dict[str, Symbol] = {}
        self.sub_scope: dict[str, Symbol] = {}
        self.counts: dict[str, int] = {"static": 0, "field": 0, "arg": 0, "var": 0}

    def reset(self) -> None:
        """Reset subroutine scope (called at the start of each subroutine)."""
        self.sub_scope.clear()
        self.counts["arg"] = 0
        self.counts["var"] = 0

    def define(self, name: str, type_: str, kind: str) -> None:
        """Define a new identifier and assign it an index in its kind."""
        if kind not in self.counts:
            raise ValueError(f"Unknown kind: {kind}")

        idx = self.counts[kind]
        self.counts[kind] += 1

        sym = Symbol(type=type_, kind=kind, index=idx)

        if kind in self.CLASS_KINDS:
            self.class_scope[name] = sym
        elif kind in self.SUB_KINDS:
            self.sub_scope[name] = sym
        else:
            raise ValueError(f"Invalid kind: {kind}")

    def varCount(self, kind: str) -> int:
        if kind not in self.counts:
            raise ValueError(f"Unknown kind: {kind}")
        return self.counts[kind]

    def _lookup(self, name: str) -> Optional[Symbol]:
        # subroutine scope shadows class scope
        return self.sub_scope.get(name) or self.class_scope.get(name)

    def kindOf(self, name: str) -> Optional[str]:
        sym = self._lookup(name)
        return sym.kind if sym else None

    def typeOf(self, name: str) -> Optional[str]:
        sym = self._lookup(name)
        return sym.type if sym else None

    def indexOf(self, name: str) -> Optional[int]:
        sym = self._lookup(name)
        return sym.index if sym else None
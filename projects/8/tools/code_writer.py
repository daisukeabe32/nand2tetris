import os

class CodeWriter:
    TEMP_BASE = 5
    SEG_BASE = {
        "local": "LCL",
        "argument": "ARG",
        "this": "THIS",
        "that": "THAT",
    }

    # ALU op mapping for binary ops that produce x op y
    _BIN_OP = {
        "add": "M=D+M",
        "sub": "M=M-D",   # x - y  (x in M, y in D)
        "and": "M=D&M",
        "or":  "M=D|M",
    }

    # unary ops apply to top of stack (in-place)
    _UNARY_OP = {
        "neg": "M=-M",
        "not": "M=!M",
    }

    # comparisons jump condition (after D = x - y)
    _CMP_JUMP = {
        "eq": "D;JEQ",
        "lt": "D;JLT",
        "gt": "D;JGT",
    }

    def __init__(self, asm_path: str):
        self.asm_path = asm_path
        self.out: list[str] = []
        self.label_id = 0
        self.file_stem: str | None = None
        self.current_function = ""
        self.call_id = 0
        
        # bootstrap
        self._emit_lines([
            "// Bootstrap",
            "@256",
            "D=A",
            "@SP",
            "M=D",
        ])

    def _new_id(self) -> int:
        uid = self.label_id
        self.label_id += 1
        return uid

    def _emit(self, line: str) -> None:
        self.out.append(line)

    def _emit_lines(self, lines: list[str]) -> None:
        self.out.extend(lines)

    def setFileName(self, vm_path: str) -> None:
        self.file_stem = os.path.splitext(os.path.basename(vm_path))[0]

    # ---------- for the functions ----------
    def _scoped_label(self, label: str) -> str:
        if self.current_function:
            return f"{self.current_function}${label}"
        return label
        
    # ---------- stack helpers ----------
    def _push_D(self) -> None:
        self._emit_lines([
            "@SP",
            "A=M",
            "M=D",
            "@SP",
            "M=M+1",
        ])

    def _pop_to_D(self) -> None:
        self._emit_lines([
            "@SP",
            "M=M-1",
            "A=M",
            "D=M",
        ])

    def _top_to_D(self) -> None:
        """D = *SP (top element) without popping."""
        self._emit_lines([
            "@SP",
            "A=M-1",
            "D=M",
        ])

    # ---------- addr helpers ----------
    def _compute_base_plus_index_to_R13(self, base_sym: str, index: int) -> None:
        self._emit_lines([
            f"@{base_sym}",
            "D=M",
            f"@{index}",
            "D=D+A",
            "@R13",
            "M=D",
        ])

    def _push_from_R13_addr(self) -> None:
        self._emit_lines([
            "@R13",
            "A=M",
            "D=M",
        ])
        self._push_D()

    def _pop_to_R13_addr(self) -> None:
        self._pop_to_D()
        self._emit_lines([
            "@R13",
            "A=M",
            "M=D",
        ])

    def _push_from_symbol(self, sym: str) -> None:
        self._emit_lines([f"@{sym}", "D=M"])
        self._push_D()

    def _pop_to_symbol(self, sym: str) -> None:
        self._pop_to_D()
        self._emit_lines([f"@{sym}", "M=D"])

    # ---------- arithmetic helpers ----------
    def _binary_op(self, op_line: str, comment: str = "") -> None:
        """
        Stack: [..., x, y] -> [..., (x op y)]
        Implementation:
          pop y -> D
          pop x -> M (A points to x)
          M = (x op y)   (using D and M)
          SP++
        """
        self._emit_lines([
            f"// {comment}",
            "@SP",
            "M=M-1",
            "A=M",
            "D=M",    # y
            "@SP",
            "M=M-1",
            "A=M",    # x at *SP
            op_line,  # compute into M
            "@SP",
            "M=M+1",
        ])

    def _unary_op(self, op_line: str, comment: str = "") -> None:
        """
        Stack: [..., x] -> [..., op(x)]
        in-place on top element
        """
        self._emit_lines([
            f"// {comment}",
            "@SP",
            "A=M-1",
            op_line,
        ])

    def _compare(self, jump_line: str, prefix: str) -> None:
        """
        Stack: [..., x, y] -> [..., (x ? y)]
        where true = -1, false = 0
        Implementation:
          pop y -> D
          pop x -> D = x - y
          if D ? 0 jump TRUE
          false: *SP = 0; goto END
          true:  *SP = -1
          END: SP++
        """
        uid = self._new_id()
        true_label = f"{prefix}_TRUE.{uid}"
        end_label  = f"{prefix}_END.{uid}"

        self._emit_lines([
            f"// {prefix}",
            "@SP",
            "M=M-1",
            "A=M",
            "D=M",        # y
            "@SP",
            "M=M-1",
            "A=M",
            "D=M-D",      # x - y
            f"@{true_label}",
            jump_line,
            "@SP",
            "A=M",
            "M=0",        # false
            f"@{end_label}",
            "0;JMP",
            f"({true_label})",
            "@SP",
            "A=M",
            "M=-1",       # true
            f"({end_label})",
            "@SP",
            "M=M+1",
        ])

    def writeArithmetic(self, command: str) -> None:
        # 1) binary ops
        if command in self._BIN_OP:
            self._binary_op(self._BIN_OP[command], comment=command.upper())
            return

        # 2) unary ops
        if command in self._UNARY_OP:
            self._unary_op(self._UNARY_OP[command], comment=command.upper())
            return

        # 3) comparisons
        if command in self._CMP_JUMP:
            self._compare(self._CMP_JUMP[command], prefix=command.upper())
            return

        raise ValueError(f"Unsupported arithmetic: {command}")

    def writePushPop(self, command: str, segment: str, index: int) -> None:
        if command not in ("push", "pop"):
            raise ValueError(f"Unknown command: {command}")

        # 1) constant
        if segment == "constant":
            if command != "push":
                raise ValueError("constant supports only push")
            self._emit_lines([f"@{index} // push constant", "D=A"])
            self._push_D()
            return

        # 2) local/argument/this/that (base + index)
        if segment in self.SEG_BASE:
            base_sym = self.SEG_BASE[segment]
            self._compute_base_plus_index_to_R13(base_sym, index)
            if command == "push":
                self._push_from_R13_addr()
            else:
                self._pop_to_R13_addr()
            return

        # 3) temp (direct address 5..12)
        if segment == "temp":
            if not (0 <= index <= 7):
                raise ValueError(f"temp index out of range: {index}")
            addr = self.TEMP_BASE + index
            sym = str(addr)
            if command == "push":
                self._push_from_symbol(sym)
            else:
                self._pop_to_symbol(sym)
            return

        # 4) pointer (0->THIS, 1->THAT)
        if segment == "pointer":
            if index == 0:
                sym = "THIS"
            elif index == 1:
                sym = "THAT"
            else:
                raise ValueError(f"pointer index must be 0 or 1: {index}")

            if command == "push":
                self._push_from_symbol(sym)
            else:
                self._pop_to_symbol(sym)
            return

        # 5) static (FileName.index)
        if segment == "static":
            if self.file_stem is None:
                raise RuntimeError("setFileName() must be called before using static segment")
            sym = f"{self.file_stem}.{index}"

            if command == "push":
                self._push_from_symbol(sym)
            else:
                self._pop_to_symbol(sym)
            return

        raise ValueError(f"Unsupported segment: {segment}")

    def writeLabel(self, label: str) -> None:
        self._emit_lines([f"({self._scoped_label(label)}) // label"])
        
    def writeGoto(self, label: str) -> None:
        self._emit_lines([
            f"@{self._scoped_label(label)} // goto",
            "0;JMP",
        ]) 
    
    def writeIf(self, label: str) -> None:
        self._emit("// if-goto")
        self._pop_to_D()
        self._emit_lines([
            f"@{self._scoped_label(label)}",
            "D;JNE",
        ])
        
    def writeFunction(self, x, y) -> None:
        pass
    
    def writeCall(self, x, y) -> None:
        pass
    
    def writeReturn(self) -> None:
        pass
    
    def close(self) -> None:
        with open(self.asm_path, "w", encoding="utf-8") as f:
            for line in self.out:
                f.write(line + "\n")
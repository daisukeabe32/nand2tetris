# code_writer.py

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

    # ---------- for functions/call ----------
    def _scoped_label(self, label: str) -> str:
        if self.current_function:
            return f"{self.current_function}${label}"
        return label
    
    def _new_call_ret_label(self, function_name: str) -> str:
        label = f"{function_name}$ret.{self.call_id}"
        self.call_id += 1
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

    def _push_A(self, value: int) -> None:
        self._emit_lines([f"@{value}", "D=A"])
        self._push_D()
        
    def _store_D_to_symbol(self, sym: str) -> None:
        self._emit_lines([f"@{sym}", "M=D"])
        
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
        self._emit_lines([
            f"// {comment}",
            "@SP",
            "A=M-1",
            op_line,
        ])

    def _compare(self, jump_line: str, prefix: str) -> None:
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
        
    def writeFunction(self, function_name: str, n_locals: int) -> None:
        self._emit_lines([f"({function_name}) // function {function_name}"])
        for _ in range(n_locals):
            self._emit_lines(["@0", "D=A"])
            self._push_D()
            
    def writeCall(self, function_name: str, n_args: int) -> None:
        # 1) push return-address
        ret_label = self._new_call_ret_label(function_name)
        self._emit(f"// call {function_name} {n_args}")
        self._emit_lines([f"@{ret_label}", "D=A"])
        self._push_D()

        # 2) push LCL, ARG, THIS, THAT
        for sym in ("LCL", "ARG", "THIS", "THAT"):
            self._emit_lines([f"@{sym} // push {sym}", "D=M"])
            self._push_D()

        # 3) ARG = SP - 5 - n_args
        # D = SP
        self._emit_lines(["@SP // update *ARG", "D=M"])
        # D = D - (5 + n_args)
        self._emit_lines([f"@{5 + n_args}", "D=D-A"])
        self._store_D_to_symbol("ARG")

        # 4) LCL = SP
        self._emit_lines(["@SP // update *LCL", "D=M"])
        self._store_D_to_symbol("LCL")

        # 5) goto function
        self._emit_lines([f"@{function_name} // goto function", "0;JMP"])

        # 6) (return-address)
        self._emit_lines([f"({ret_label})"])
    
    def writeReturn(self) -> None:
        self._emit("// return (R1: FRAME=LCL)")
        
        # FRAME = LCL  (R13 = LCL)
        self._emit_lines([
            "@LCL",
            "D=M",
            "@R13",
            "M=D"
        ])
        
        # RET = *(FRAME - 5)  (R14 = RAM[FRAME-5])
        self._emit_lines([
            "@R13",
            "D=M",       # D = FRAME
            "@5",
            "A=D-A",     # A = FRAME - 5
            "D=M",       # D = *(FRAME - 5)
            "@R14",
            "M=D",       # R14 = RET
        ])
        
        # *ARG = pop()   (return value to caller)
        self._emit_lines([
            "@SP",
            "M=M-1",
            "A=M",
            "D=M",       # D = return value
            "@ARG",
            "A=M",
            "M=D",       # *ARG = return value
        ])

        # SP = ARG + 1
        self._emit_lines([
            "@ARG",
            "D=M",
            "@1",
            "D=D+A",
            "@SP",
            "M=D",
        ])
        
        # Restore THAT, THIS, ARG, LCL from FRAME (R13)
        # Restore THAT = *(FRAME-1)
        self._emit_lines([
            "@R13",
            "D=M",
            "@1",
            "A=D-A",
            "D=M",
            "@THAT",
            "M=D",
        ])

        # Restore THIS = *(FRAME-2)
        self._emit_lines([
            "@R13",
            "D=M",
            "@2",
            "A=D-A",
            "D=M",
            "@THIS",
            "M=D",
        ])

        # Restore ARG = *(FRAME-3)
        self._emit_lines([
            "@R13",
            "D=M",
            "@3",
            "A=D-A",
            "D=M",
            "@ARG",
            "M=D",
        ])

        # Restore LCL = *(FRAME-4)
        self._emit_lines([
            "@R13",
            "D=M",
            "@4",
            "A=D-A",
            "D=M",
            "@LCL",
            "M=D",
        ])

        # goto RET
        self._emit_lines([
            "@R14",
            "A=M",
            "0;JMP",
        ])
    
    def close(self) -> None:
        with open(self.asm_path, "w", encoding="utf-8") as f:
            for line in self.out:
                f.write(line + "\n")
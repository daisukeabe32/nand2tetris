class CodeWriter:
    def __init__(self, asm_path: str):
        self.asm_path = asm_path
        self.out: list[str] = []
        self.label_id = 0
        
        # bootstrap
        self._emit_lines([
            "// Bootstrap",
            "@256",
            "D=A",
            "@SP",
            "M=D",
        ])
        
    def _emit(self, line: str) -> None:
        self.out.append(line)
        
    def _emit_lines(self, lines: list[str]) -> None:
        self.out.extend(lines)
    
    def _new_id(self) -> int:
        uid = self.label_id
        self.label_id += 1
        return uid
    
    def writeArithmetic(self, command: str) -> None:
        if command == "add":
            self._emit_lines([
                "@SP // ADD ",
                "M=M-1",
                "A=M",
                "D=M",
                "@SP",
                "M=M-1",
                "A=M",
                "M=D+M",
                "@SP",
                "M=M+1",
            ])
            return
        
        if command == "sub":
            self._emit_lines([
                "@SP // SUB ",
                "M=M-1",
                "A=M",
                "D=M",  # y
                "@SP",
                "M=M-1",
                "A=M",
                "M=M-D", # x -y
                "@SP",
                "M=M+1",
            ])
            return
        
        if command == "neg":
            self._emit_lines([
                "@SP // NEG ",
                "A=M-1",
                "M=-M",
            ])
            return
        
        if command == "and":
            self._emit_lines([
                "@SP // And ",
                "M=M-1",
                "A=M",
                "D=M",
                "@SP",
                "M=M-1",
                "A=M",
                "M=D&M",
                "@SP",
                "M=M+1",
            ])
            return

        if command == "or":
            self._emit_lines([
                "@SP // OR ",
                "M=M-1",
                "A=M",
                "D=M",
                "@SP",
                "M=M-1",
                "A=M",
                "M=D|M",
                "@SP",
                "M=M+1",
            ])
            return

        if command == "not":
            self._emit_lines([
                "@SP // NOT ",
                "A=M-1",
                "M=!M",
            ])
            return
        
        if command == "eq":
            uid = self._new_id()
            true_label = f"EQ_TRUE.{uid}"
            end_label = f"EQ_END.{uid}"
            
            self._emit_lines([
                #pop y --> D
                "@SP // EQ ",
                "M=M-1",
                "A=M",
                "D=M",
                
                # pop x, compute x - y -> D
                "@SP",
                "M=M-1",
                "A=M",
                "D=M-D",
                
                #if x-y == 0 jump TRUE
                f"@{true_label}",
                "D;JEQ",
                
                # false: *SP = 0
                "@SP",
                "A=M",
                "M=0",
                f"@{end_label}",
                "0;JMP",
                
                # true: *SP = -1
                f"({true_label})",
                "@SP",
                "A=M",
                "M=-1",
                
                # end: SP++
                f"({end_label})",
                "@SP",
                "M=M+1",   
            ])
            return
        
        if command == "lt":
            uid = self._new_id()
            true_label = f"LT_TRUE.{uid}"
            end_label = f"LT_END.{uid}"
            
            self._emit_lines([
                #pop y --> D
                "@SP // LT ",
                "M=M-1",
                "A=M",
                "D=M",
                
                # pop x, compute x - y -> D
                "@SP",
                "M=M-1",
                "A=M",
                "D=M-D",
                
                #if x-y < 0 jump TRUE
                f"@{true_label}",
                "D;JLT",
                
                # false: *SP = 0
                "@SP",
                "A=M",
                "M=0",
                f"@{end_label}",
                "0;JMP",
                
                # true: *SP = -1
                f"({true_label})",
                "@SP",
                "A=M",
                "M=-1",
                
                # end: SP++
                f"({end_label})",
                "@SP",
                "M=M+1",   
            ])
            return
        
        if command == "gt":
            uid = self._new_id()
            true_label = f"GT_TRUE.{uid}"
            end_label = f"GT_END.{uid}"
            
            self._emit_lines([
                #pop y --> D
                "@SP // GT ",
                "M=M-1",
                "A=M",
                "D=M",
                
                # pop x, compute x - y -> D
                "@SP",
                "M=M-1",
                "A=M",
                "D=M-D",
                
                #if x-y > 0 jump TRUE
                f"@{true_label}",
                "D;JGT",
                
                # false: *SP = 0
                "@SP",
                "A=M",
                "M=0",
                f"@{end_label}",
                "0;JMP",
                
                # true: *SP = -1
                f"({true_label})",
                "@SP",
                "A=M",
                "M=-1",
                
                # end: SP++
                f"({end_label})",
                "@SP",
                "M=M+1",   
            ])
            return
        
        raise ValueError(f"Unsupported arithmetic for now: {command}")
    
    def writePushPop(self, command: str, segment: str, index: int) -> None:
        if command == "push" and segment == "constant":
            self._emit_lines([
                f"@{index} // PUSH CONSTANT ",
                "D=A",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            ])
            return
        
        if command == "push" and segment == "local":
            self._emit_lines([
                "@LCL // PUSH LOCAL ",
                "D=M",
                f"@{index}",
                "D=D+A",
                "@R13",
                "M=D",
                "A=M",
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            ])
            return
        
        if command == "pop" and segment == "local":
            self._emit_lines([
                "@LCL // POP LOCAL",
                "D=M",
                f"@{index}",
                "D=D+A",
                "@R13",
                "M=D",
                "@SP",
                "M=M-1",
                "A=M",
                "D=M",
                "@R13",
                "A=M",
                "M=D",
            ])
            return
        
        if command == "push" and segment == "argument":
            self._emit_lines([
                "@ARG // PUSH ARG ",
                "D=M",
                f"@{index}",
                "D=D+A",
                "@R13",
                "M=D",
                "A=M",
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            ])
            return
        
        if command == "pop" and segment == "argument":
            self._emit_lines([
                "@ARG // POP ARG",
                "D=M",
                f"@{index}",
                "D=D+A",
                "@R13",
                "M=D",
                "@SP",
                "M=M-1",
                "A=M",
                "D=M",
                "@R13",
                "A=M",
                "M=D",
            ])
            return
        
        if command == "push" and segment == "this":
            self._emit_lines([
                "@THIS // PUSH THIS ",
                "D=M",
                f"@{index}",
                "D=D+A",
                "@R13",
                "M=D",
                "A=M",
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            ])
            return
        
        if command == "pop" and segment == "this":
            self._emit_lines([
                "@THIS // POP THIS",
                "D=M",
                f"@{index}",
                "D=D+A",
                "@R13",
                "M=D",
                "@SP",
                "M=M-1",
                "A=M",
                "D=M",
                "@R13",
                "A=M",
                "M=D",
            ])
            return
        
        if command == "push" and segment == "that":
            self._emit_lines([
                "@THAT // PUSH THAT ",
                "D=M",
                f"@{index}",
                "D=D+A",
                "@R13",
                "M=D",
                "A=M",
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            ])
            return
        
        if command == "pop" and segment == "that":
            self._emit_lines([
                "@THAT // POP THAT",
                "D=M",
                f"@{index}",
                "D=D+A",
                "@R13",
                "M=D",
                "@SP",
                "M=M-1",
                "A=M",
                "D=M",
                "@R13",
                "A=M",
                "M=D",
            ])
            return
        
        
        TEMP_BASE = 5
        if command == "push" and segment == "temp":
            if not (0 <= index <= 7):
                raise ValueError(f"temp index out of range: {index}")
            addr = TEMP_BASE + index
            self._emit_lines([
                f"@{addr} // PUSH TEMP {index}(RAM[{addr}]) ",
                "D=M",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            ])
            return
        
        if command == "pop" and segment == "temp":
            if not (0 <= index <= 7):
                raise ValueError(f"temp index out of range: {index}")
            addr = TEMP_BASE + index
            self._emit_lines([
                "@SP",
                "M=M-1",
                "A=M",
                "D=M",
                f"@{addr} // POP TEMP {index}(RAM[{addr}])",
                "M=D",
            ])
            return
        
        if segment == "pointer":
            if index == 0:
                sym = "THIS"
            elif index == 1:
                sym = "THAT"
            else:
                raise ValueError(f"pointer index must be 0 or 1: {index}")

            if command == "push":
                self._emit_lines([
                    f"@{sym} // PUSH POINTER {index}",
                    "D=M",
                    "@SP",
                    "A=M",
                    "M=D",
                    "@SP",
                    "M=M+1",
                ])
                return

            if command == "pop":
                self._emit_lines([
                    f"@SP // POP POINTER {index}",
                    "M=M-1",
                    "A=M",
                    "D=M",
                    f"@{sym}",
                    "M=D",
                ])
                return
            
        raise ValueError(f"Unsupported push/pop for now: {command} {segment} {index}")
    
    def close(self) -> None:
        with open(self.asm_path, "w", encoding="utf-8") as f:
            for line in self.out:
                f.write(line + "\n")


# if __name__ == "__main__":
#     w = CodeWriter("Mini.asm")
#     w.writePushPop("push", "constant", 7)
#     w.writeArithmetic("add")
#     w.close()
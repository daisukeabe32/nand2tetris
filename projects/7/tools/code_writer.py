class CodeWriter:
    def __init__(self, asm_path: str):
        self.asm_path = asm_path
        self.out: list[str] = []
        self.label_id = 0
        
    def _emit(self, line: str) -> None:
        self.out.append(line)
        
    def _emit_lines(self, lines: list[str]) -> None:
        self.out.extend(lines)
    
    def _new_label(self, prefix: str) -> str:
        label = f"{prefix}.{self.label_id}"
        self.label_id += 1
        return label
    def writeArithmetic(self, command: str) -> None:
        if command == "add":
            self._emit_lines([
                "@SP",
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
                "@SP",
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
                "@SP",
                "A=M-1",
                "M=-M",
            ])
            return
        
        if command == "and":
            self._emit_lines([
                "@SP",
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
                "@SP",
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
                "@SP",
                "A=M-1",
                "M=!M",
            ])
            return
    
        raise ValueError(f"Unsupported arithmetic for now: {command}")
    
    def writePushPop(self, command: str, segment: str, index: int) -> None:
        if command == "push" and segment == "constant":
            self._emit_lines([
                f"@{index}",
                "D=A",
                "@SP",
                "A=M",
                "M=D",
                "@SP",
                "M=M+1",
            ])
            return
        raise ValueError(f"Unsupported push/pop for now: {command} {segment} {index}")
    
    def close(self) -> None:
        with open(self.asm_path, "w", encoding="utf-8") as f:
            for line in self.out:
                f.write(line + "\n")
        print("DONE!!")


if __name__ == "__main__":
    w = CodeWriter("Mini.asm")
    w.writePushPop("push", "constant", 7)
    w.writeArithmetic("add")
    w.close()
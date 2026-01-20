C_ARITHMETIC = "C_ARITHMETIC"
C_PUSH = "C_PUSH"
C_POP = "C_POP"
C_LABEL = "C_LABEL"
C_GOTO = "C_GOTO"
C_IF = "C_IF"

ARITHMETIC_COMMANDS = {
    "add", "sub", "neg",
    "and", "or", "not",
    "eq", "lt", "gt",
}

class Parser:
    def __init__(self, vm_path: str):
        self.lines = []
        with open(vm_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.split("//", 1)[0].strip()
                if line:
                    self.lines.append(line)
                    
        self.current_index = -1
        self.current_line = ""
    
    def hasMoreLines(self) -> bool:
        return self.current_index + 1 < len(self.lines)
    
    def advance(self) -> None:
        self.current_index += 1
        self.current_line = self.lines[self.current_index]
    
    def commandType(self) -> str:
        parts = self.current_line.split()
        cmd = parts[0]
        
        if cmd in ARITHMETIC_COMMANDS:
            return C_ARITHMETIC
        elif cmd == "push":
            return C_PUSH
        elif cmd == "pop":
            return C_POP
        elif cmd == "label":
            return C_LABEL
        elif cmd == "goto":
            return C_GOTO
        elif cmd == "if-goto":
            return C_IF
        
        return ""
    
    def arg1(self) -> str:
        parts = self.current_line.split()
        ctype = self.commandType()
        
        if ctype == C_ARITHMETIC:
            return parts[0]
        elif ctype in (C_PUSH, C_POP, C_LABEL, C_GOTO, C_IF):
            return parts[1]

        raise RuntimeError(f"arg1() called on unknown type: {self.current_line}")
        
    def arg2(self) -> int:
        ctype = self.commandType()
        if ctype not in (C_PUSH, C_POP):
            raise RuntimeError(f"arg2() called on non push/pop: {self.current_line}")
        
        parts = self.current_line.split()
        
        return int(parts[2])



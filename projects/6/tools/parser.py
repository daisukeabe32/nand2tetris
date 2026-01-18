A_INSTRUCTION = "A_INSTRUCTION"
C_INSTRUCTION = "C_INSTRUCTION"
L_INSTRUCTION = "L_INSTRUCTION"  # 基本版では基本使わないが、形だけ用意

class Parser:
    def __init__(self, asm_path: str):
        with open(asm_path, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()
        self.lines = self._clean(raw_lines)
        self.current_index = -1
        self.current_line = None

    def _clean(self, raw_lines):
        out = []
        for line in raw_lines:
            line = line.split("//", 1)[0].strip()
            if line:
                out.append(line)
        return out

    def hasMoreLines(self) -> bool:
        return self.current_index + 1 < len(self.lines)

    def advance(self) -> None:
        self.current_index += 1
        self.current_line = self.lines[self.current_index]

    def instructionType(self) -> str:
        line = self.current_line
        if line.startswith("@"):
            return A_INSTRUCTION
        if line.startswith("(") and line.endswith(")"):
            return L_INSTRUCTION
        return C_INSTRUCTION

    def symbol(self) -> str:
        """
        A命令なら @xxx の xxx を返す。
        L命令なら (xxx) の xxx を返す。
        """
        t = self.instructionType()
        line = self.current_line
        if t == A_INSTRUCTION:
            return line[1:]
        if t == L_INSTRUCTION:
            return line[1:-1]
        raise ValueError("symbol() called on non A/L INSTRUCTION")

    def dest(self) -> str:
        """
        C命令 dest=comp;jump の dest を返す（無ければ ""）。
        """
        line = self.current_line
        if "=" in line:
            return line.split("=", 1)[0].strip()
        return ""

    def comp(self) -> str:
        """
        C命令 dest=comp;jump の comp を返す。
        """
        line = self.current_line
        # dest を除去
        if "=" in line:
            line = line.split("=", 1)[1]
        # jump を除去
        if ";" in line:
            line = line.split(";", 1)[0]
        return line.strip()

    def jump(self) -> str:
        """
        C命令 dest=comp;jump の jump を返す（無ければ ""）。
        """
        line = self.current_line
        if ";" in line:
            return line.split(";", 1)[1].strip()
        return ""
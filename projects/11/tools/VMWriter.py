class VMWriter:
    def __init__(self, out_path: str):
        self.out = open(out_path, "w", encoding="utf-8")

    def close(self):
        self.out.close()

    def write(self, line: str):
        self.out.write(line + "\n")

    def writeFunction(self, name: str, n_locals: int):
        self.write(f"function {name} {n_locals}")

    def writePush(self, segment: str, index: int):
        self.write(f"push {segment} {index}")

    def writePop(self, segment: str, index: int):
        self.write(f"pop {segment} {index}")

    def writeCall(self, name: str, n_args: int):
        self.write(f"call {name} {n_args}")

    def writeArithmetic(self, cmd: str):
        # cmd: add/sub/neg/eq/gt/lt/and/or/not
        self.write(cmd)

    def writeReturn(self):
        self.write("return")
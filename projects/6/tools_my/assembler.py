import sys

from parser import Parser, A_INSTRUCTION, C_INSTRUCTION, L_INSTRUCTION
from code import Code
from symbol_table import SymbolTable

def to_a_instruction(value: int) -> str:
    """0vvvvvvvvvvvvvvv の16bit文字列を返す (value: 0..32767)"""
    if not isinstance(value, int):
        raise TypeError(f"A-instruction value must be int, got {type(value)}")
    if not (0 <= value <= 32767):
        raise ValueError(f"A constant out of range: {value}")
    return "0" + format(value, "015b")

def to_c_instruction(dest_mn: str, comp_mn: str, jump_mn: str) -> str:
    return "111" + Code.comp(comp_mn) + Code.dest(dest_mn) + Code.jump(jump_mn)

def assemble(asm_path: str) -> list[str]:
    """完全版: 2パスで (LABEL) と @symbol(変数) を解決して .hack を生成する。"""

    # --------------------
    # Pass 1: label (L-instruction) を収集してシンボルテーブルへ
    # --------------------
    st = SymbolTable()
    p1 = Parser(asm_path)

    rom_address = 0  # A/C 命令だけを数えたときの次のROM番地
    while p1.hasMoreLines():
        p1.advance()
        t = p1.instructionType()

        if t == L_INSTRUCTION:
            label = p1.symbol()  # (xxx) の xxx
            # ラベルは "次に現れる実命令(A/C)のROMアドレス" に束縛される
            if not st.contains(label):
                st.addEntry(label, rom_address)
            continue

        # A/C 命令はROMを1語消費
        rom_address += 1

    # --------------------
    # Pass 2: 実際にバイナリ化。@xxx の xxx を数値へ解決
    # --------------------
    p2 = Parser(asm_path)
    out: list[str] = []
    next_address = 16
    while p2.hasMoreLines():
        p2.advance()
        t = p2.instructionType()

        if t == L_INSTRUCTION:
            continue  # (LABEL) はコードを出力しない

        if t == A_INSTRUCTION:
            sym = p2.symbol()  # @yyy の yyy

            # @123 のような数値はそのまま
            if sym.isdigit():
                out.append(to_a_instruction(int(sym)))
                continue

            # @SCREEN や @LOOP や @i など: シンボル解決
            if st.contains(sym):
                out.append(to_a_instruction(st.getAddress(sym)))
                continue

            # 未登録なら新しい変数として割り当て
            st.addEntry(sym, next_address)
            out.append(to_a_instruction(next_address))
            next_address += 1
            continue

        # C-instruction
        out.append(to_c_instruction(p2.dest(), p2.comp(), p2.jump()))

    return out

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 assembler.py Prog.asm")
        sys.exit(1)

    asm_path = sys.argv[1]
    hack_path = asm_path.replace(".asm", ".hack")

    machine_codes = assemble(asm_path)

    with open(hack_path, "w", encoding="utf-8") as f:
        for code in machine_codes:
            f.write(code + "\n")

    print("Wrote", hack_path)

if __name__ == "__main__":
    main()
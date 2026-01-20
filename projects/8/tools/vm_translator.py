from parser import Parser
from code_writer import CodeWriter
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 VMTranslator.py Prog.vm")
        sys.exit(1)
        
    vm_path = sys.argv[1]        
    asm_path = vm_path.replace(".vm", ".asm")
    
    parser = Parser(vm_path)
    writer = CodeWriter(asm_path)
    writer.setFileName(vm_path)
    
    while parser.hasMoreLines():
        parser.advance()
        ctype = parser.commandType()
        
        if ctype == "C_ARITHMETIC":
            writer.writeArithmetic(parser.arg1())
        
        elif ctype == "C_PUSH":
            writer.writePushPop(
                "push",
                parser.arg1(),
                parser.arg2()
            )
            
        elif ctype == "C_POP":
            writer.writePushPop(
                "pop",
                parser.arg1(),
                parser.arg2()
            )
        
        elif ctype == "C_LABEL":
            writer.writeLabel(parser.arg1())
            
        elif ctype == "C_GOTO":
            writer.writeGoto(parser.arg1())
        
        elif ctype == "C_IF":
            writer.writeIf(parser.arg1())
        
        elif ctype == "C_FUNCTION":
            writer.writeFunction(parser.arg1(), parser.arg2())
            
        elif ctype == "C_CALL":
            writer.writeCall(parser.arg1(), parser.arg2())
            
        elif ctype == "C_RETURN":
            writer.writeReturn()
            
        else:
            raise ValueError(f"Unknown command type: {ctype}")

    print("DEBUG out lines:", len(writer.out))
    writer.close()
    print("Wrote", asm_path)
        
if __name__ == "__main__":
    main()
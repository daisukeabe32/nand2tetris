# vm_translator.py

from parser import Parser
from code_writer import CodeWriter
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 VMTranslator.py Prog.vm")
        sys.exit(1)
    
    in_path = Path(sys.argv[1])
    
    if in_path.is_dir():
        vm_files = sorted(in_path.glob("*.vm"))       
        asm_path = in_path / (in_path.name + ".asm")
    else:
        vm_files = [in_path]
        asm_path = in_path.with_suffix(".asm")
        
    if not vm_files:
        raise RuntimeError("No .vm files found")
    
    writer = CodeWriter(str(asm_path))
    
    for vm_file in vm_files:
        writer.setFileName(vm_file)
        parser = Parser(vm_file)
    
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
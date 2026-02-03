from JackTokenizer import JackTokenizer
from VMWriter import VMWriter
from SymbolTable import SymbolTable

class CompilationEngine:
    OPS = {"+", "-", "*", "/", "&", "|", "<", ">", "="}
    UNARY_OPS = {"-", "~"}
    KEYWORD_CONSTANTS = {"true", "false", "null", "this"}
    KIND_TO_SEGMENT = {
        "static": "static",
        "field": "this",
        "arg": "argument",
        "var": "local"
    }

    # lifecycle
    def __init__(self, input_path: str, output_path: str):
        self.tok = JackTokenizer(input_path)
        self.vm = VMWriter(output_path)
        self.indent = 0
        self.st = SymbolTable()
        self.label_id = 0
        # Core idea (N2T style): keep current_token always valid by priming with advance()
        self.tok.advance()

        
    def close(self):
        self.vm.close()

    # low-level common utilities from project 10  
    
    # ---------- eat（assert-like） ----------
    def eat(self, expected_token=None, expected_type=None):
        if expected_token is not None and self.tok.current_token != expected_token:
            raise SyntaxError(
                f"expected token '{expected_token}', got '{self.tok.current_token}'"
            )
        if expected_type is not None and self.tok.current_type != expected_type:
            raise SyntaxError(
                f"expected type '{expected_type}', got '{self.tok.current_type}'"
            )
        
        if self.tok.has_more_tokens():
            self.tok.advance()

    # main public API (entry point)
    def compileClass(self):
        self.eat("class", "KEYWORD")
        self.class_name = self.tok.current_token
        self.eat(expected_type="IDENTIFIER")
        self.eat("{", "SYMBOL")

        while self.tok.current_token in ("static", "field"):
            self.compileClassVarDec()

        while self.tok.current_token in ("constructor", "function", "method"):
            self.compileSubroutine()

        self.eat("}", "SYMBOL")

    # big grammar units (class → subroutine → statements → expression → term)
    def compileClassVarDec(self):
        kind = self.tok.current_token   
        self.eat(expected_type="KEYWORD")  # static | field
        
        type_name = self.tok.current_token
        self.compileType()
        
        name = self.tok.current_token
        self.eat(expected_type="IDENTIFIER")
        self.st.define(name, type_name, kind)

        while self.tok.current_token == ",":
            self.eat(",", "SYMBOL")
            name = self.tok.current_token
            self.eat(expected_type="IDENTIFIER")
            self.st.define(name, type_name, kind)  
            
        self.eat(";", "SYMBOL")

    def compileType(self):
        # Precondition: a type token is expected at this point
        if self.tok.current_type == "KEYWORD":
            self.eat(expected_type="KEYWORD")
        else:
            self.eat(expected_type="IDENTIFIER")

    def compileSubroutine(self):
        self.st.reset()
        sub_kind = self.tok.current_token          # constructor | function | method
        self.eat(expected_type="KEYWORD")

        if self.tok.current_token == "void":
            self.eat("void", "KEYWORD")
        else:
            self.compileType()

        sub_name = self.tok.current_token
        self.eat(expected_type="IDENTIFIER")

        self.eat("(", "SYMBOL")
        self.compileParameterList()
        self.eat(")", "SYMBOL")

        self.eat("{", "SYMBOL")
        self.compileSubroutineBody(sub_kind, sub_name)
        self.eat("}", "SYMBOL")

    def compileParameterList(self):
        if self.tok.current_token == ")":
            return
        
        while True:
            type_name = self.tok.current_token
            self.compileType()
            
            name = self.tok.current_token            
            self.eat(expected_type="IDENTIFIER")
            
            self.st.define(name, type_name, "arg")

            if self.tok.current_token != ",":
                break
            self.eat(",", "SYMBOL")


    def compileSubroutineBody(self, sub_kind: str, sub_name: str):
        n_locals = 0
        while self.tok.current_token == "var":
            n_locals += self.compileVarDec()

        full_name = f"{self.class_name}.{sub_name}"
        self.vm.writeFunction(full_name, n_locals)
        
        if sub_kind == "constructor":
            n_fields = self.st.varCount("field")
            self.vm.writePush("constant", n_fields)
            self.vm.writeCall("Memory.alloc", 1)
            self.vm.writePop("pointer", 0)  # this = base address
        elif sub_kind == "method":
            self.vm.writePush("argument", 0)
            self.vm.writePop("pointer", 0)  # this = argument 0
            
        self.compileStatements()
        
    def compileVarDec(self):
        self.eat("var", "KEYWORD")
        
        type_name = self.tok.current_token
        self.compileType()
        
        name = self.tok.current_token
        self.eat(expected_type="IDENTIFIER")
        self.st.define(name, type_name, "var")

        count = 1
        
        while self.tok.current_token == ",":
            self.eat(",", "SYMBOL")
            name = self.tok.current_token
            self.eat(expected_type="IDENTIFIER")
            self.st.define(name, type_name, "var")
            count += 1
            
        self.eat(";", "SYMBOL")
        return count
    
    def compileStatements(self):
        while self.tok.current_token in ("let", "if", "while", "do", "return"):
            {
                "let": self.compileLet,
                "if": self.compileIf,
                "while": self.compileWhile,
                "do": self.compileDo,
                "return": self.compileReturn,
            }[self.tok.current_token]()

    def compileLet(self):
        self.eat("let", "KEYWORD")
        
        var_name = self.tok.current_token
        self.eat(expected_type="IDENTIFIER")

        # TODO: array handling later (varName[expression] = expression;)
        if self.tok.current_token == "[":
            raise NotImplementedError("Array assignment not implemented yet")

        self.eat("=", "SYMBOL")
        
        # RHS: leaves a value on the top of the stack
        self.compileExpression()
        
        self.eat(";", "SYMBOL")
        
        # Codegen: pop RHS value into the LHS variable
        self._writePopVar(var_name)

    def compileIf(self):
        self.eat("if", "KEYWORD")

        label_true = self._new_label("IF_TRUE")
        label_false = self._new_label("IF_FALSE")
        label_end = self._new_label("IF_END")

        self.eat("(", "SYMBOL")
        self.compileExpression()
        self.eat(")", "SYMBOL")

        self.vm.writeIf(label_true)
        self.vm.writeGoto(label_false)
        
        self.vm.writeLabel(label_true)
        self.eat("{", "SYMBOL")
        self.compileStatements()
        self.eat("}", "SYMBOL")

        if self.tok.current_token == "else":
            self.vm.writeGoto(label_end)
            self.vm.writeLabel(label_false)

            self.eat("else", "KEYWORD")
            self.eat("{", "SYMBOL")
            self.compileStatements()
            self.eat("}", "SYMBOL")

            self.vm.writeLabel(label_end)
        else:
            self.vm.writeLabel(label_false)

    def compileWhile(self):
        self.eat("while", "KEYWORD")
        
        label_exp = self._new_label("WHILE_EXP")
        label_end = self._new_label("WHILE_END")
        
        self.vm.writeLabel(label_exp)
        self.eat("(", "SYMBOL")
        self.compileExpression()
        self.eat(")", "SYMBOL")
        
        self.vm.writeArithmetic("not")
        self.vm.writeIf(label_end)

        self.eat("{", "SYMBOL")
        self.compileStatements()
        self.eat("}", "SYMBOL")
        
        self.vm.writeGoto(label_exp)
        self.vm.writeLabel(label_end)

    def compileDo(self):
        self.eat("do", "KEYWORD")
        
        name1 = self.tok.current_token
        self.eat(expected_type="IDENTIFIER")
        
        self.compileSubroutineCall(name1)
        
        self.eat(";", "SYMBOL")
        self.vm.writePop("temp", 0)

    def compileReturn(self):
        self.eat("return", "KEYWORD")

        if self.tok.current_token != ";":
            self.compileExpression()
        else:
            self.vm.writePush("constant", 0)

        self.eat(";", "SYMBOL")
        self.vm.writeReturn()

    def compileExpression(self):
        self.compileTerm()

        while self.tok.current_token in self.OPS:
            op = self.tok.current_token
            self.eat(expected_type="SYMBOL")
            self.compileTerm()
            
            if op == "+":
                self.vm.writeArithmetic("add")
            elif op == "-":
                self.vm.writeArithmetic("sub")
            elif op == "*":
                self.vm.writeCall("Math.multiply", 2)
            elif op == "/":
                self.vm.writeCall("Math.divide", 2)
            elif op == "&":
                self.vm.writeArithmetic("and")
            elif op == "|":
                self.vm.writeArithmetic("or")
            elif op == "<":
                self.vm.writeArithmetic("lt")
            elif op == ">":
                self.vm.writeArithmetic("gt")
            elif op == "=":
                self.vm.writeArithmetic("eq")
            else:
                raise NotImplementedError(f"Op not supported yet: {op}")

    def compileTerm(self):
        if self.tok.current_type == "INT_CONST":
            val = int(self.tok.current_token)
            self.eat(expected_type="INT_CONST")
            self.vm.writePush("constant", val)
            return

        elif self.tok.current_token in self.UNARY_OPS:
            op = self.tok.current_token
            self.eat(expected_type="SYMBOL")
            self.compileTerm()
            if op == "-":
                self.vm.writeArithmetic("neg")
            elif op == "~":
                self.vm.writeArithmetic("not")
            return
        
        elif self.tok.current_token == "(":
            self.eat("(", "SYMBOL")
            self.compileExpression()
            self.eat(")", "SYMBOL")
            return
        
        elif self.tok.current_type == "IDENTIFIER":
            var_name = self.tok.current_token
            self.eat(expected_type="IDENTIFIER")
            
            if self.tok.current_token in ("(", "."):
                # subroutine call
                self.compileSubroutineCall(var_name)
                return
            if self.tok.current_token == "[":
                raise NotImplementedError("Array access not implemented yet")

            self._writePushVar(var_name)
            return
        
        elif self.tok.current_type == "KEYWORD" and self.tok.current_token in self.KEYWORD_CONSTANTS:
            keyword = self.tok.current_token
            self.eat(expected_type="KEYWORD")
            if keyword == "true":
                self.vm.writePush("constant", 0)
                self.vm.writeArithmetic("not")
            elif keyword in ("false", "null"):
                self.vm.writePush("constant", 0)
            elif keyword == "this":
                self.vm.writePush("pointer", 0)
            return
        
        raise NotImplementedError(f"Term not supported yet: {self.tok.current_token}")

    def compileSubroutineCall(self, name1: str):
        n_args = 0

        if self.tok.current_token == ".":
            self.eat(".")
            name2 = self.tok.current_token
            self.eat(expected_type="IDENTIFIER")

            # name1 が変数なら method
            if self.st.kindOf(name1) is not None:
                seg, idx = self._var_segment_index(name1)
                self.vm.writePush(seg, idx)   # objectRef
                full_name = f"{self.st.typeOf(name1)}.{name2}"
                n_args = 1
            else:
                # Class.function()
                full_name = f"{name1}.{name2}"

        else:
            # ★ここが暗黙 this
            self.vm.writePush("pointer", 0)
            full_name = f"{self.class_name}.{name1}"
            n_args = 1

        self.eat("(")
        n_args += self.compileExpressionList()
        self.eat(")")
        self.vm.writeCall(full_name, n_args)

    def compileExpressionList(self):
        n = 0
        if self.tok.current_token != ")":
            self.compileExpression()
            n = 1
            while self.tok.current_token == ",":
                self.eat(",", "SYMBOL")
                self.compileExpression()
                n += 1
        return n
    
    def _writePop(self, var_name: str) -> None:
        kind = self.st.kindOf(var_name)
        index = self.st.indexOf(var_name)
        
        if kind is None or index is None:
            raise ValueError(f"Undefined variable: {var_name}")
        
        segment = {
            "static": "static",
            "field": "this",
            "arg": "argument",
            "var": "local"
        }.get(kind)
        
        if segment is None:
            raise ValueError(f"Unknown kind for variable {var_name}: {kind}")
        
        self.vm.writePop(segment, index)
        
    def _var_segment_index(self, name: str) -> tuple[str, int]:
        kind = self.st.kindOf(name)
        index = self.st.indexOf(name)
        if kind is None or index is None:
            raise ValueError(f"Undefined variable: {name}")
        return self.KIND_TO_SEGMENT[kind], index

    def _writePushVar(self, name: str) -> None:
        seg, idx = self._var_segment_index(name)
        self.vm.writePush(seg, idx)

    def _writePopVar(self, name: str) -> None:
        seg, idx = self._var_segment_index(name)
        self.vm.writePop(seg, idx)
        
    def _new_label(self, prefix: str) -> str:
        lab = f"{prefix}{self.label_id}"
        self.label_id += 1
        return lab
from JackTokenizer import JackTokenizer
from VMWriter import VMWriter

class CompilationEngine:
    OPS = {"+", "-", "*", "/", "&", "|", "<", ">", "="}
    UNARY_OPS = {"-", "~"}
    KEYWORD_CONSTANTS = {"true", "false", "null", "this"}

    # lifecycle
    def __init__(self, input_path: str, output_path: str):
        self.tok = JackTokenizer(input_path)
        self.vm = VMWriter(output_path)
        self.indent = 0

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
        self._open("class")

        self.eat("class", "KEYWORD")
        self.class_name = self.tok.current_token
        self.eat(expected_type="IDENTIFIER")
        self.eat("{", "SYMBOL")

        while self.tok.current_token in ("static", "field"):
            self.compileClassVarDec()

        while self.tok.current_token in ("constructor", "function", "method"):
            self.compileSubroutine()

        self.eat("}", "SYMBOL")
        self._close("class")

    # big grammar units (class → subroutine → statements → expression → term)
    def compileClassVarDec(self):
        self._open("classVarDec")

        self.eat(expected_type="KEYWORD")  # static | field
        self.compileType()
        self.eat(expected_type="IDENTIFIER")

        while self.tok.current_token == ",":
            self.eat(",", "SYMBOL")
            self.eat(expected_type="IDENTIFIER")

        self.eat(";", "SYMBOL")
        self._close("classVarDec")

    def compileType(self):
        # Precondition: a type token is expected at this point
        if self.tok.current_type == "KEYWORD":
            self.eat(expected_type="KEYWORD")
        else:
            self.eat(expected_type="IDENTIFIER")

    def compileSubroutine(self):

        self._open("subroutineDec")

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

        self.compileSubroutineBody(sub_kind, sub_name)
                
        self._close("subroutineDec")

    def compileParameterList(self):
        self._open("parameterList")

        if self.tok.current_token != ")":
            self.compileType()
            self.eat(expected_type="IDENTIFIER")

            while self.tok.current_token == ",":
                self.eat(",", "SYMBOL")
                self.compileType()
                self.eat(expected_type="IDENTIFIER")

        self._close("parameterList")

    def compileSubroutineBody(self, sub_kind: str, sub_name: str):
        self.eat("{", "SYMBOL")

        n_locals = 0
        while self.tok.current_token == "var":
            n_locals += self._consumeVarDecAndCount()

        full_name = f"{self.class_name}.{sub_name}"
        self.vm.writeFunction(full_name, n_locals)
        self.compileStatements()
        self.eat("}", "SYMBOL")
        
    def _consumeVarDecAndCount(self) -> int:
        self.eat("var", "KEYWORD")
        self.compileType()
        self.eat(expected_type="IDENTIFIER")
        count = 1
        while self.tok.current_token == ",":
            self.eat(",", "SYMBOL")
            self.eat(expected_type="IDENTIFIER")
            count += 1
        self.eat(";", "SYMBOL")
        return count

    def compileVarDec(self):
        self._open("varDec")

        self.eat("var", "KEYWORD")
        self.compileType()
        self.eat(expected_type="IDENTIFIER")

        while self.tok.current_token == ",":
            self.eat(",", "SYMBOL")
            self.eat(expected_type="IDENTIFIER")

        self.eat(";", "SYMBOL")
        self._close("varDec")

    def compileStatements(self):
        self._open("statements")

        while self.tok.current_token in ("let", "if", "while", "do", "return"):
            {
                "let": self.compileLet,
                "if": self.compileIf,
                "while": self.compileWhile,
                "do": self.compileDo,
                "return": self.compileReturn,
            }[self.tok.current_token]()

        self._close("statements")

    def compileLet(self):
        self._open("letStatement")

        self.eat("let", "KEYWORD")
        self.eat(expected_type="IDENTIFIER")

        if self.tok.current_token == "[":
            self.eat("[", "SYMBOL")
            self.compileExpression()
            self.eat("]", "SYMBOL")

        self.eat("=", "SYMBOL")
        self.compileExpression()
        self.eat(";", "SYMBOL")

        self._close("letStatement")

    def compileIf(self):
        self._open("ifStatement")

        self.eat("if", "KEYWORD")
        self.eat("(", "SYMBOL")
        self.compileExpression()
        self.eat(")", "SYMBOL")

        self.eat("{", "SYMBOL")
        self.compileStatements()
        self.eat("}", "SYMBOL")

        if self.tok.current_token == "else":
            self.eat("else", "KEYWORD")
            self.eat("{", "SYMBOL")
            self.compileStatements()
            self.eat("}", "SYMBOL")

        self._close("ifStatement")

    def compileWhile(self):
        self._open("whileStatement")

        self.eat("while", "KEYWORD")
        self.eat("(", "SYMBOL")
        self.compileExpression()
        self.eat(")", "SYMBOL")

        self.eat("{", "SYMBOL")
        self.compileStatements()
        self.eat("}", "SYMBOL")

        self._close("whileStatement")

    def compileDo(self):
        self.eat("do", "KEYWORD")
        self.compileSubroutineCall()
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
            elif op == "*":
                self.vm.writeCall("Math.multiply", 2)
            else:
                raise NotImplementedError(f"Op not supported yet: {op}")

    def compileTerm(self):
        if self.tok.current_type == "INT_CONST":
            val = int(self.tok.current_token)
            self.eat(expected_type="INT_CONST")
            self.vm.writePush("constant", val)
            return

        elif self.tok.current_token == "(":
            self.eat("(", "SYMBOL")
            self.compileExpression()
            self.eat(")", "SYMBOL")
            return
        
        raise NotImplementedError(f"Term not supported yet: {self.tok.current_token}")

    def compileSubroutineCall(self):
        name1 = self.tok.current_token
        self.eat(expected_type="IDENTIFIER")
        
        full_name = None
        
        if self.tok.current_token == ".":
            self.eat(".", "SYMBOL")
            name2 = self.tok.current_token
            self.eat(expected_type="IDENTIFIER")
            full_name = f"{name1}.{name2}"
        else:
            full_name = f"{self.class_name}.{name1}"
            
        self.eat("(", "SYMBOL")
        n_args = self.compileExpressionList()
        self.eat(")", "SYMBOL")
        
        self.vm.writeCall(full_name, n_args)

    # def compileSubroutineCallRest(self):
    #     if self.tok.current_token == ".":
    #         self.eat(".", "SYMBOL")
    #         self.eat(expected_type="IDENTIFIER")

    #     self.eat("(", "SYMBOL")
    #     self.compileExpressionList()
    #     self.eat(")", "SYMBOL")

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
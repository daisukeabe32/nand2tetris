from JackTokenizer import JackTokenizer


class CompilationEngine_ref:
    OPS = {"+", "-", "*", "/", "&", "|", "<", ">", "="}
    UNARY_OPS = {"-", "~"}
    KEYWORD_CONSTANTS = {"true", "false", "null", "this"}

    def __init__(self, input_path: str, output_path: str):
        self.tok = JackTokenizer(input_path)
        self.out = open(output_path, "w", encoding="utf-8")
        self.indent = 0

        # Core idea (N2T style): keep current_token always valid by priming with advance()
        self.tok.advance()

    def close(self):
        self.out.close()

    # ---------- XML helpers ----------
    def _w(self, line: str):
        self.out.write(" " * self.indent + line + "\n")

    def _open(self, tag: str):
        self._w(f"<{tag}>")
        self.indent += 2

    def _close(self, tag: str):
        self.indent -= 2
        self._w(f"</{tag}>")

    def _write_current_token(self):
        tok = self.tok.current_token
        typ = self.tok.current_type
        tag = JackTokenizer.TYPE_TO_TAG[typ]

        if typ == "SYMBOL":
            tok = JackTokenizer.escape_xml(tok)

        self._w(f"<{tag}> {tok} </{tag}>")

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

        self._write_current_token()
        
        if self.tok.has_more_tokens():
            self.tok.advance()

    # ---------- Grammar ----------

    def compileClass(self):
        self._open("class")

        self.eat("class", "KEYWORD")
        self.eat(expected_type="IDENTIFIER")
        self.eat("{", "SYMBOL")

        while self.tok.current_token in ("static", "field"):
            self.compileClassVarDec()

        while self.tok.current_token in ("constructor", "function", "method"):
            self.compileSubroutine()

        self.eat("}", "SYMBOL")
        self._close("class")

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

        self.eat(expected_type="KEYWORD")  # constructor | function | method

        if self.tok.current_token == "void":
            self.eat("void", "KEYWORD")
        else:
            self.compileType()

        self.eat(expected_type="IDENTIFIER")
        self.eat("(", "SYMBOL")
        self.compileParameterList()
        self.eat(")", "SYMBOL")

        self.compileSubroutineBody()

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

    def compileSubroutineBody(self):
        self._open("subroutineBody")

        self.eat("{", "SYMBOL")

        while self.tok.current_token == "var":
            self.compileVarDec()

        self.compileStatements()
        self.eat("}", "SYMBOL")

        self._close("subroutineBody")

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
        self._open("doStatement")

        self.eat("do", "KEYWORD")
        self.compileSubroutineCall()
        self.eat(";", "SYMBOL")

        self._close("doStatement")

    def compileReturn(self):
        self._open("returnStatement")

        self.eat("return", "KEYWORD")

        if self.tok.current_token != ";":
            self.compileExpression()

        self.eat(";", "SYMBOL")
        self._close("returnStatement")

    def compileExpression(self):
        self._open("expression")

        self.compileTerm()

        while self.tok.current_token in self.OPS:
            self.eat(expected_type="SYMBOL")
            self.compileTerm()

        self._close("expression")

    def compileTerm(self):
        self._open("term")

        if self.tok.current_type in ("INT_CONST", "STRING_CONST"):
            self.eat(expected_type=self.tok.current_type)

        elif self.tok.current_type == "KEYWORD":
            self.eat(expected_type="KEYWORD")

        elif self.tok.current_token == "(":
            self.eat("(", "SYMBOL")
            self.compileExpression()
            self.eat(")", "SYMBOL")

        elif self.tok.current_token in self.UNARY_OPS:
            self.eat(expected_type="SYMBOL")
            self.compileTerm()

        else:
            self.eat(expected_type="IDENTIFIER")

            if self.tok.current_token == "[":
                self.eat("[", "SYMBOL")
                self.compileExpression()
                self.eat("]", "SYMBOL")

            elif self.tok.current_token in ("(", "."):
                self.compileSubroutineCallRest()

        self._close("term")

    def compileSubroutineCall(self):
        self.eat(expected_type="IDENTIFIER")
        self.compileSubroutineCallRest()

    def compileSubroutineCallRest(self):
        if self.tok.current_token == ".":
            self.eat(".", "SYMBOL")
            self.eat(expected_type="IDENTIFIER")

        self.eat("(", "SYMBOL")
        self.compileExpressionList()
        self.eat(")", "SYMBOL")

    def compileExpressionList(self):
        self._open("expressionList")

        if self.tok.current_token != ")":
            self.compileExpression()
            while self.tok.current_token == ",":
                self.eat(",", "SYMBOL")
                self.compileExpression()

        self._close("expressionList")
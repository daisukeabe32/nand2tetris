from JackTokenizer import JackTokenizer

class CompilationEngine:
    
    OPS = {"+", "-", "*", "/", "&", "|", "<", ">", "="}
    UNARY_OPS = {"-", "~"}
    KEYWORD_CONSTANTS = {"true", "false", "null", "this"}
    
    def __init__(self, input_path: str, output_path: str):
        self.tok = JackTokenizer(input_path)
        self.out = open(output_path, "w", encoding="utf-8")
        self.indent = 0

    def close(self):
        self.out.close()

    def _w(self, line: str):
        self.out.write(" " * self.indent + line + "\n")

    def _open(self, tag: str):
        self._w(f"<{tag}>")
        self.indent += 2

    def _close(self, tag: str):
        self.indent -= 2
        self._w(f"</{tag}>")

    def _write_current_token(self):
        # Serialize current_token/current_type as a single XML line
        tok = self.tok.current_token
        typ = self.tok.current_type
        tag = JackTokenizer.TYPE_TO_TAG[typ]

        if typ == "SYMBOL":
            tok = JackTokenizer.escape_xml(tok)

        self._w(f"<{tag}> {tok} </{tag}>")

    def eat(self, expected_token=None, expected_type=None):
        # 1) Consume the next token
        self.tok.advance()

        # 2) Optionally validate (mismatch => error)
        if expected_token is not None and self.tok.current_token != expected_token:
            raise ValueError(f"Expected token {expected_token}, got {self.tok.current_token}")
        if expected_type is not None and self.tok.current_type != expected_type:
            raise ValueError(f"Expected type {expected_type}, got {self.tok.current_type}")

        # 3) Emit the token as XML
        self._write_current_token()
        
    def compileClassVarDec(self):
        self._open("classVarDec")

        # ('static' | 'field')
        tok, typ = self.tok.peek()
        if tok not in ("static", "field"):
            raise ValueError(f"Expected static/field, got {tok}")
        self.eat(expected_token=tok, expected_type="KEYWORD")

        # type
        self.compileType()

        # varName
        self.eat(expected_type="IDENTIFIER")

        # (',' varName)*
        while True:
            tok, typ = self.tok.peek()
            if tok != ",":
                break
            self.eat(expected_token=",", expected_type="SYMBOL")
            self.eat(expected_type="IDENTIFIER")

        # ';'
        self.eat(expected_token=";", expected_type="SYMBOL")

        self._close("classVarDec")
        
    def compileType(self):
        tok, typ = self.tok.peek()

        if typ == "KEYWORD":
            if tok in ("int", "char", "boolean"):
                self.eat(expected_type="KEYWORD")   # or expected_token=tok
            else:
                raise ValueError(f"Expected type keyword, got {tok}")
        elif typ == "IDENTIFIER":
            self.eat(expected_type="IDENTIFIER")    # className
        else:
            raise ValueError(f"Expected type, got {typ}:{tok}")

    def compileReturnType(self):
        tok, typ = self.tok.peek()
        if tok == "void":
            self.eat(expected_token="void", expected_type="KEYWORD")
        else:
            self.compileType()
            
    def compileParameterList(self):
        self._open("parameterList")

        tok, typ = self.tok.peek()
        if tok != ")":
            # type varName
            self.compileType()
            self.eat(expected_type="IDENTIFIER")

            # (',' type varName)*
            while True:
                tok, typ = self.tok.peek()
                if tok != ",":
                    break
                self.eat(expected_token=",", expected_type="SYMBOL")
                self.compileType()
                self.eat(expected_type="IDENTIFIER")

        self._close("parameterList")
        
    def compileSubroutineBody(self):
        self._open("subroutineBody")

        self.eat(expected_token="{", expected_type="SYMBOL")

        # varDec*
        while True:
            tok, typ = self.tok.peek()
            if tok == "var":
                self.compileVarDec()   # varDec*
            else:
                break

        # statements (parsed as a sequence of statement nodes until '}' is reached)
        self.compileStatements()

        self.eat(expected_token="}", expected_type="SYMBOL")

        self._close("subroutineBody")
    
    def compileExpression(self):
        """
        Temporary: do not parse expression grammar strictly; consume tokens until a stop token appears.
        until_tokens examples: {")"}, {"]"}, {";", ","}
        """

        self._open("expression")
        
        self.compileTerm()
        
        while True:
            tok, typ = self.tok.peek()
            if tok in self.OPS:
                self.eat(expected_token=tok, expected_type="SYMBOL")
                self.compileTerm()
            else:
                break
        self._close("expression")
    
    def compileTerm(self):
        self._open("term")

        tok, typ = self.tok.peek()

        # integerConstant / stringConstant
        if typ in ("INT_CONST", "STRING_CONST"):
            self.eat(expected_type=typ)

        # keywordConstant: true/false/null/this
        elif typ == "KEYWORD" and tok in self.KEYWORD_CONSTANTS:
            self.eat(expected_token=tok, expected_type="KEYWORD")

        # ( expression )
        elif tok == "(":
            self.eat("(", "SYMBOL")
            self.compileExpression()
            self.eat(")", "SYMBOL")

        # unaryOp term
        elif tok in self.UNARY_OPS:
            self.eat(expected_token=tok, expected_type="SYMBOL")  # '-' or '~' is SYMBOL in your tokenizer
            self.compileTerm()

        # identifier: varName | varName[expr] | subroutineCall
        elif typ == "IDENTIFIER":
            # まず identifier を食う（varName or subroutineName or className/varName）
            self.eat(expected_type="IDENTIFIER")

            # 次の1トークンで分岐
            tok2, typ2 = self.tok.peek()

            # varName [ expression ]
            if tok2 == "[":
                self.eat("[", "SYMBOL")
                self.compileExpression()
                self.eat("]", "SYMBOL")

            # subroutineCall: name '(' ... ')'  OR  name '.' name '(' ... ')'
            elif tok2 in ("(", "."):
                self._compileSubroutineCall_after_first_name()

            # else: plain varName (already consumed)

        else:
            raise ValueError(f"Invalid term start: {typ}:{tok}")

        self._close("term")
            
    def _compileSubroutineCall_after_first_name(self):
        # ここに来た時点で、先頭の IDENTIFIER は eat 済み

        tok, typ = self.tok.peek()

        # subroutineName '(' expressionList ')'
        if tok == "(":
            self.eat("(", "SYMBOL")
            self.compileExpressionList()
            self.eat(")", "SYMBOL")
            return

        # (className|varName) '.' subroutineName '(' expressionList ')'
        if tok == ".":
            self.eat(".", "SYMBOL")
            self.eat(expected_type="IDENTIFIER")  # subroutineName
            self.eat("(", "SYMBOL")
            self.compileExpressionList()
            self.eat(")", "SYMBOL")
            return

        raise ValueError(f"Expected subroutine call, got {tok}")
    
    def compileExpressionList(self):
        self._open("expressionList")

        tok, typ = self.tok.peek()
        if tok != ")":
            self.compileExpression()

            while True:
                tok, typ = self.tok.peek()
                if tok != ",":
                    break
                self.eat(",", "SYMBOL")
                self.compileExpression()

        self._close("expressionList")
            
    # Statements    
    def compileStatements(self):
        self._open("statements")

        while True:
            tok, typ = self.tok.peek()
            if tok == "let":
                self.compileLet()
            elif tok == "if":
                self.compileIf()
            elif tok == "while":
                self.compileWhile()
            elif tok == "do":
                self.compileDo()
            elif tok == "return":
                self.compileReturn()
            else:
                break

        self._close("statements")
    
    def compileReturn(self):
        self._open("returnStatement")
        self.eat("return", "KEYWORD")

        tok, typ = self.tok.peek()
        if tok != ";":
            self.compileExpression()
            
        self.eat(";", "SYMBOL")
        self._close("returnStatement")

    def compileDo(self):
        self._open("doStatement")
        self.eat("do", "KEYWORD")

        self.eat(expected_type="IDENTIFIER")
        self._compileSubroutineCall_after_first_name()

        self.eat(";", "SYMBOL")
        self._close("doStatement")
        
    def compileLet(self):
        self._open("letStatement")
        self.eat("let", "KEYWORD")
        self.eat(expected_type="IDENTIFIER")  # varName

        # optional: [ ... ]
        tok, typ = self.tok.peek()
        if tok == "[":
            self.eat("[", "SYMBOL")
            self.compileExpression()
            self.eat("]", "SYMBOL")

        self.eat("=", "SYMBOL")
        self.compileExpression()
        self.eat(";", "SYMBOL")
        self._close("letStatement")
    
    def compileWhile(self):
        self._open("whileStatement")

        self.eat("while", "KEYWORD")
        
        # (expression)
        self.eat("(", "SYMBOL")
        self.compileExpression()
        self.eat(")", "SYMBOL")
        
        # {statements}
        self.eat("{", "SYMBOL")
        self.compileStatements()
        self.eat("}", "SYMBOL")
        
        self._close("whileStatement")
    
    def compileIf(self):
        self._open("ifStatement")

        self.eat("if", "KEYWORD")
        
        # (expression)
        self.eat("(", "SYMBOL")
        self.compileExpression()
        self.eat(")", "SYMBOL")
        
        # {statements}
        self.eat("{", "SYMBOL")
        self.compileStatements()
        self.eat("}", "SYMBOL")

        # optional else
        tok, typ = self.tok.peek()
        if tok == "else":
            self.eat("else", "KEYWORD")
            self.eat("{", "SYMBOL")
            self.compileStatements()
            self.eat("}", "SYMBOL")

        self._close("ifStatement")
    
    def compileVarDec(self):
        self._open("varDec")

        self.eat(expected_token="var", expected_type="KEYWORD")
        self.compileType()
        self.eat(expected_type="IDENTIFIER")

        while True:
            tok, typ = self.tok.peek()
            if tok != ",":
                break
            self.eat(expected_token=",", expected_type="SYMBOL")
            self.eat(expected_type="IDENTIFIER")

        self.eat(expected_token=";", expected_type="SYMBOL")
        self._close("varDec")
        
    def compileSubroutine(self):
        self._open("subroutineDec")

        # ('constructor'|'function'|'method')
        tok, typ = self.tok.peek()
        if tok not in ("constructor", "function", "method"):
            raise ValueError(f"Expected subroutine kind, got {tok}")
        self.eat(expected_token=tok, expected_type="KEYWORD")

        # ('void'|type)
        self.compileReturnType()

        # subroutineName
        self.eat(expected_type="IDENTIFIER")

        # '(' parameterList ')'
        self.eat(expected_token="(", expected_type="SYMBOL")
        self.compileParameterList()
        self.eat(expected_token=")", expected_type="SYMBOL")

        # subroutineBody
        self.compileSubroutineBody()

        self._close("subroutineDec")

    # main compiler entry point
    def compileClass(self):
        self._open("class")

        self.eat(expected_token="class", expected_type="KEYWORD")
        self.eat(expected_type="IDENTIFIER")  # className
        self.eat(expected_token="{", expected_type="SYMBOL")

        # classVarDec*
        while True:
            tok, typ = self.tok.peek()
            if tok in ("static", "field"):
                self.compileClassVarDec()   # class-level variable declarations
            else:
                break

        # subroutineDec*
        while True:
            tok, typ = self.tok.peek()
            if tok in ("constructor", "function", "method"):
                self.compileSubroutine()    # subroutine declarations
            else:
                break

        self.eat(expected_token="}", expected_type="SYMBOL")
        self._close("class")


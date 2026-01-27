from JackTokenizer import JackTokenizer

class CompilationEngine:
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
            # For now: consume tokens up to ';' (later: parse a proper expression)
            while True:
                tok, typ = self.tok.peek()
                if tok == ";":
                    break
                self.eat()

        self.eat(";", "SYMBOL")
        self._close("returnStatement")

    def compileDo(self):
        self._open("doStatement")
        self.eat("do", "KEYWORD")

        # For now: consume tokens up to ';' (later: parse a proper subroutineCall)
        while True:
            tok, typ = self.tok.peek()
            if tok == ";":
                break
            self.eat()

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
            # expression (for now: consume tokens up to ']')
            while True:
                tok, typ = self.tok.peek()
                if tok == "]":
                    break
                self.eat()
            self.eat("]", "SYMBOL")

        self.eat("=", "SYMBOL")

        # expression (for now: consume tokens up to ';')
        while True:
            tok, typ = self.tok.peek()
            if tok == ";":
                break
            self.eat()

        self.eat(";", "SYMBOL")
        self._close("letStatement")
    
    def compileWhile(self):
        self._open("whileStatement")

        self.eat("while", "KEYWORD")
        self.eat("(", "SYMBOL")

        # expression
        self.compileExpression(until_tokens={")"})

        self.eat(")", "SYMBOL")
        self.eat("{", "SYMBOL")

        # statements（再帰）
        self.compileStatements()

        self.eat("}", "SYMBOL")
        self._close("whileStatement")
    
    def compileIf(self):
        self._open("ifStatement")

        self.eat("if", "KEYWORD")
        self.eat("(", "SYMBOL")

        # expression
        self.compileExpression(until_tokens={")"})

        self.eat(")", "SYMBOL")
        self.eat("{", "SYMBOL")

        # statements（再帰）
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
        
    def compileExpression(self, until_tokens=None):
        """
        Temporary: do not parse expression grammar strictly; consume tokens until a stop token appears.
        until_tokens examples: {")"}, {"]"}, {";", ","}
        """
        if until_tokens is None:
            until_tokens = {")"}

        self._open("expression")
        while True:
            tok, typ = self.tok.peek()
            if tok in until_tokens:
                break
            self.eat()
        self._close("expression")
    
    
    
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


if __name__ == "__main__":
    ce = CompilationEngine("../Square/Main.jack", "../Square/Main.xml")
    ce.compileClass()
    ce.close()
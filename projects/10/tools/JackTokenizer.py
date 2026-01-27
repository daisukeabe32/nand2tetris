class JackTokenizer:
    KEYWORDS = {
    "class", "constructor", "function", "method", "field", "static", "var",
    "int", "char", "boolean", "void", "true", "false", "null", "this",
    "let", "do", "if", "else", "while", "return"
}

    SYMBOLS = set("{}()[].,;+-*/&|<>=~")
    
    TYPE_TO_TAG = {
    "KEYWORD": "keyword",
    "SYMBOL": "symbol",
    "IDENTIFIER": "identifier",
    "INT_CONST": "integerConstant",
    "STRING_CONST": "stringConstant",
}
        
    def __init__(self, input_file):
        self.input_file = input_file
        with open(input_file, "r", encoding="utf-8") as f:
            self.source = f.read()
        self.pos = 0
        self.current_token = None
        self.current_type = None
        
    def _skip_ignorable(self) -> None:
        while self.pos < len(self.source):
            # 1) whitespace
            if self.source[self.pos].isspace():
                self.pos += 1
                continue
            
            # 2) line comment: //
            if self.source.startswith("//", self.pos):
                newline = self.source.find("\n", self.pos)
                if newline == -1:
                    self.pos = len(self.source)
                else:
                    self.pos = newline + 1
                continue
            
            # 3) block comment: /* ... */
            if self.source.startswith("/*", self.pos):
                end = self.source.find("*/", self.pos + 2)
                if end == -1:
                    raise ValueError("Undeterminated block comment")
                self.pos = end + 2
                continue
            break    
    
    def has_more_tokens(self) -> bool:
        self._skip_ignorable()
        return self.pos < len(self.source)
    
    def peek(self) -> tuple:
        saved_pos = self.pos
        saved_token = self.current_token
        saved_type = self.current_type

        try:
            tok = self.advance()
            typ = self.current_type
        except StopIteration:
            tok = None
            typ = None

        self.pos = saved_pos
        self.current_token = saved_token
        self.current_type = saved_type

        return tok, typ            
    
    def advance(self) -> str:
        self._skip_ignorable()
        if self.pos >= len(self.source):
            raise StopIteration("No more tokens")
        
        ch = self.source[self.pos]
        
        # 0) string constant tokens
        if ch == '"':
            self.pos += 1
            start = self.pos
            while self.pos < len(self.source) and self.source[self.pos] != '"':
                self.pos += 1
            
            if self.pos >= len(self.source):
                raise ValueError("Unterminated string constant")
            
            self.current_token = self.source[start:self.pos]
            self.current_type = "STRING_CONST"
            self.pos += 1
            return self.current_token
        
        # 1) symbol tokens
        if ch in self.SYMBOLS:
            self.current_token = ch
            self.current_type = "SYMBOL"
            self.pos += 1
            return self.current_token
        
        # 2) word tokens
        start = self.pos
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch.isspace() or ch in self.SYMBOLS:
                break
            self.pos += 1
        self.current_token = self.source[start:self.pos]
        if self.current_token.isdigit():
            self.current_type = "INT_CONST"
        elif self.current_token in self.KEYWORDS:
            self.current_type = "KEYWORD"
        else:
            self.current_type = "IDENTIFIER"
        return self.current_token
            
    def token_type(self) -> str:
        return self.current_type
    
    @staticmethod
    def escape_xml(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    @staticmethod
    def write_tokens_xml(input_path: str, output_path: str) -> None:
        t = JackTokenizer(input_path)
        with open(output_path, "w", encoding="utf-8") as out:
            out.write("<tokens>\n")
            while t.has_more_tokens():
                tok = t.advance()
                typ = t.token_type()
                tag = JackTokenizer.TYPE_TO_TAG[typ]
                
                if typ == "SYMBOL":
                    tok = JackTokenizer.escape_xml(tok)
                    
                out.write(f"  <{tag}> {tok} </{tag}>\n")
            out.write("</tokens>\n")
                
                
                
if __name__ == "__main__":
    JackTokenizer.write_tokens_xml("../Square/Main.jack", "../Square/MainT.xml")
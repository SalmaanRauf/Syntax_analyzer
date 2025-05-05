from __future__ import annotations
from typing import List, Optional
import sys
import lexer

TRACE: bool = True
OUTFILE = None


tokens: List[lexer.Token] = []
pos: int = 0
error_count: int = 0  # Track the total number of errors found

def current() -> lexer.Token:
    global pos
    # Make sure pos is within valid range
    if pos >= len(tokens):
        # If we've consumed all real tokens, return a dummy EOF token
        # with the line number from the last real token
        last_line = tokens[-1].line_number if tokens else 1
        return lexer.Token("eof", "", last_line)
    return tokens[pos]

def advance() -> None:
    """
    Consume the current token.  *Must* be called only after ensuring it matches
    the expected grammar symbol.
    """
    global pos
    
    # print token / lexeme BEFORE advancing, per spec
    # Only print if this is not an EOF token
    if OUTFILE and current().kind != "eof":
        curr_token = current()
        OUTFILE.write(f"Token: {curr_token.kind:15s} Lexeme: {curr_token.lexeme:15s} Line: {curr_token.line_number}\n")
    
    # AFTER printing the token info, then advance the position
    pos += 1
    
    # Return early if we've moved to EOF to prevent multiple EOF prints
    # Note: This check happens AFTER advancing pos and AFTER printing the token
    if pos >= len(tokens):
        return

def expect(kind: str, lexeme: Optional[str] = None) -> None:
    tok = current()
    if tok.kind != kind or (lexeme is not None and tok.lexeme != lexeme):
        error(f"expected {kind}{' ' + lexeme if lexeme else ''}")
        # error() now calls advance(), so we don't need to do it again here
    else:
        # Only advance if the token matched
        advance()

def error(msg: str) -> None:
    global error_count
    tok = current()
    # Output to stderr with the [syntax-error] prefix
    print(f"[syntax-error] line {tok.line_number}: at token '{tok.lexeme}' ({tok.kind}) — {msg}", file=sys.stderr)
    
    # Also write to the OUTFILE if tracing is enabled
    if TRACE and OUTFILE:
        OUTFILE.write(f"[syntax-error] line {tok.line_number}: at token '{tok.lexeme}' ({tok.kind}) — {msg}\n")
    
    error_count += 1  # Increment the error count
    # Don't exit, so parsing can continue
    advance()  # Skip the problematic token to allow parsing to continue

def prod(rule: str) -> None:
    if TRACE and OUTFILE:
        line_num = current().line_number
        OUTFILE.write(f"\tline {line_num}: {rule}\n")

# Grammar procedures (after factoring) 

# R1  <Rat25S> ::= $$ <Opt Function Definitions> $$ <Opt Declaration List> $$ <Statement List> $$
def Rat25S() -> None:
    # First consume the $$ token - this will print the token
    expect("separator", "$$")
    
    # Then print the production rule
    prod("<Rat25S> -> $$ <OptFunctionDefinitions> $$ <OptDeclarationList> $$ <StatementList> $$")
    
    # Continue with the rest of the parsing
    OptFunctionDefinitions()
    expect("separator", "$$")
    OptDeclarationList()
    expect("separator", "$$")
    StatementList()
    expect("separator", "$$")
    
    # After consuming the final $$, check for EOF
    expect("eof")   # must reach end cleanly

# R2
def OptFunctionDefinitions() -> None:
    if current().lexeme == "function":
        prod("<OptFunctionDefinitions> -> <FunctionDefinitions>")
        FunctionDefinitions()
    else:
        prod("<OptFunctionDefinitions> -> ε")

# R3
def FunctionDefinitions() -> None:
    prod("<FunctionDefinitions> -> <Function> <FunctionDefinitionsPrime>")
    Function()
    FunctionDefinitionsPrime()

def FunctionDefinitionsPrime() -> None:
    if current().lexeme == "function":
        prod("<FunctionDefinitionsPrime> -> <FunctionDefinitions>")
        FunctionDefinitions()
    else:
        prod("<FunctionDefinitionsPrime> -> ε")

# R4
def Function() -> None:
    prod("<Function> -> function IDENTIFIER ( <OptParameterList> ) <OptDeclarationList> <Body>")
    expect("keyword", "function")
    expect("identifier")
    expect("separator", "(")
    OptParameterList()
    expect("separator", ")")
    OptDeclarationList()
    Body()

# R5, R6, R7, R8
def OptParameterList() -> None:
    if current().kind == "identifier":
        prod("<OptParameterList> -> <ParameterList>")
        ParameterList()
    else:
        prod("<OptParameterList> -> ε")

def ParameterList() -> None:
    prod("<ParameterList> -> <Parameter> <ParameterListPrime>")
    Parameter()
    ParameterListPrime()

def ParameterListPrime() -> None:
    if current().lexeme == ",":
        prod("<ParameterListPrime> -> , <Parameter> <ParameterListPrime>")
        expect("separator", ",")
        Parameter()
        if current().lexeme == ",":
            ParameterListPrime()
    else:
        prod("<ParameterListPrime> -> ε")

def Parameter() -> None:
    prod("<Parameter> -> <IDs> <Qualifier>")
    IDs()
    Qualifier()

def Qualifier() -> None:
    prod("<Qualifier> -> integer | boolean | real")
    if current().lexeme in {"integer", "boolean", "real"}:
        advance()
    else:
        error("qualifier (integer/boolean/real) expected")

# R9
def Body() -> None:
    prod("<Body> -> { <StatementList> }")
    expect("separator", "{")
    StatementList()
    expect("separator", "}")

# R10, R11, R12, R13
def OptDeclarationList() -> None:
    if current().lexeme in {"integer", "boolean", "real"}:
        prod("<OptDeclarationList> -> <DeclarationList>")
        DeclarationList()
    else:
        prod("<OptDeclarationList> -> ε")

def DeclarationList() -> None:
    prod("<DeclarationList> -> <Declaration> ; <DeclarationListPrime>")
    Declaration()
    expect("separator", ";")
    DeclarationListPrime()
        
def DeclarationListPrime() -> None:
    if current().lexeme in {"integer", "boolean", "real"}:
        prod("<DeclarationListPrime> -> <DeclarationList>")
        DeclarationList()
    else:
        prod("<DeclarationListPrime> -> ε")

def Declaration() -> None:
    prod("<Declaration> -> <Qualifier> <IDs>")
    Qualifier()
    IDs()

def IDs() -> None:
    prod("<IDs> -> IDENTIFIER <IDsPrime>")
    expect("identifier")
    IDsPrime()

def IDsPrime() -> None:
    if current().lexeme == ",":
        prod("<IDsPrime> -> , IDENTIFIER <IDsPrime>")
        expect("separator", ",")
        expect("identifier")
        if current().lexeme == ",":
            IDsPrime()
    else:
        prod("<IDsPrime> -> ε")

# R14, R15
def StatementList() -> None:
    # Check if we're at a token that can't start a statement (including the final $$)
    tok = current()
    if ((tok.kind == "separator" and tok.lexeme in {"}", "$$"}) or 
        tok.kind == "eof"):
        # Empty statement list
        prod("<StatementList> -> ε")
        return
        
    prod("<StatementList> -> <Statement> <StatementListPrime>")
    Statement()
    StatementListPrime()

def StatementListPrime() -> None:
    # Check for more statements
    starters = {"separator": "{", "identifier": None, "keyword": {
        "if","while","return","scan","print"}}
    
    tok = current()
    # Explicitly check for tokens that can't start a statement
    if ((tok.kind == "separator" and tok.lexeme in {"}", "$$"}) or 
        tok.kind == "eof"):
        prod("<StatementListPrime> -> ε")
        return
        
    # Standard statement starters
    if ((tok.kind == "separator" and tok.lexeme == "{") or
        tok.kind == "identifier" or
        (tok.kind == "keyword" and tok.lexeme in starters["keyword"])):
        prod("<StatementListPrime> -> <Statement> <StatementListPrime>")
        Statement()
        StatementListPrime()

def Statement() -> None:
    tok = current()
    if tok.kind == "separator" and tok.lexeme == "{":
        prod("<Statement> -> <Compound>")
        Compound()
    elif tok.kind == "identifier":
        prod("<Statement> -> <Assign>")
        Assign()
    elif tok.kind == "keyword":
        if tok.lexeme == "if":
            prod("<Statement> -> <If>")
            If()
        elif tok.lexeme == "while":
            prod("<Statement> -> <While>")
            While()
        elif tok.lexeme == "return":
            prod("<Statement> -> <Return>")
            Return()
        elif tok.lexeme == "print":
            prod("<Statement> -> <Print>")
            Print()
        elif tok.lexeme == "scan":
            prod("<Statement> -> <Scan>")
            Scan()
        else:
            error("unexpected keyword in statement")
    else:
        error("invalid statement start")

# R16
def Compound() -> None:
    prod("<Compound> -> { <StatementList> }")
    expect("separator", "{")
    StatementList()
    expect("separator", "}")

# R17
def Assign() -> None:
    prod("<Assign> -> IDENTIFIER = <Expression> ;")
    expect("identifier")
    expect("operator", "=")
    Expression()
    expect("separator", ";")

# R18
def If() -> None:
    prod("<If> -> if ( <Condition> ) <Statement> <IfPrime>")
    expect("keyword", "if")
    expect("separator", "(")
    Condition()
    expect("separator", ")")
    Statement()
    IfPrime()
        
def IfPrime() -> None:
    if current().lexeme == "else":
        prod("<IfPrime> -> else <Statement> endif")
        expect("keyword", "else")
        Statement()
        expect("keyword", "endif")
    else:
        # Handle the one-arm form
        prod("<IfPrime> -> endif")
        expect("keyword", "endif")

# R19
def Return() -> None:
    prod("<Return> -> return <ReturnPrime>")
    expect("keyword", "return")
    if current().lexeme != ";":
        ReturnPrime()
    else:
        prod("<ReturnPrime> -> ;")
        expect("separator", ";")
        
def ReturnPrime() -> None:
    prod("<ReturnPrime> -> <Expression> ;")
    Expression()
    expect("separator", ";")

# R21 (note duplicated number in spec for Print/Scan)
def Print() -> None:
    prod("<Print> -> print ( <Expression> ) ;")
    expect("keyword", "print")
    expect("separator", "(")
    Expression()
    expect("separator", ")")
    expect("separator", ";")

def Scan() -> None:
    prod("<Scan> -> scan ( <IDs> ) ;")
    expect("keyword", "scan")
    expect("separator", "(")
    IDs()
    expect("separator", ")")
    expect("separator", ";")

# R22
def While() -> None:
    prod("<While> -> while ( <Condition> ) <Statement> endwhile")
    expect("keyword", "while")
    expect("separator", "(")
    Condition()
    expect("separator", ")")
    Statement()
    expect("keyword", "endwhile")

# R23
def Condition() -> None:
    prod("<Condition> -> <Expression> <Relop> <Expression>")
    Expression()
    Relop()
    Expression()

# R24
def Relop() -> None:
    prod("<Relop> -> == | != | > | < | <= | =>")
    lex = current().lexeme
    if current().kind == "operator" and lex in {"==","!=","<",">","<=","=>"}:
        advance()
    else:
        error("relational operator expected")

# Expression, Term, Factor, Primary with left‑recursion removal
def Expression() -> None:
    prod("<Expression> -> <Term> <ExpressionPrime>")
    Term()
    ExpressionPrime()

def ExpressionPrime() -> None:
    if current().kind == "operator" and current().lexeme in {"+","-"}:
        prod("<ExpressionPrime> -> + <Term> <ExpressionPrime> | - <Term> <ExpressionPrime>")
        advance()
        Term()
        ExpressionPrime()
    else:
        prod("<ExpressionPrime> -> ε")

def Term() -> None:
    prod("<Term> -> <Factor> <TermPrime>")
    Factor()
    TermPrime()

def TermPrime() -> None:
    if current().kind == "operator" and current().lexeme in {"*","/"}:
        prod("<TermPrime> -> * <Factor> <TermPrime> | / <Factor> <TermPrime>")
        advance()
        Factor()
        TermPrime()
    else:
        prod("<TermPrime> -> ε")

def Factor() -> None:
    if current().lexeme == "-":
        prod("<Factor> -> - <Primary>")
        advance()
        Primary()
    else:
        prod("<Factor> -> <Primary>")
        Primary()

# R28 (Primary)
def Primary() -> None:
    tok = current()
    if tok.kind == "identifier":
        if tokens[pos+1].lexeme == "(":           # function call
            prod("<Primary> -> IDENTIFIER ( <IDs> )")
            expect("identifier")
            expect("separator", "(")
            IDs()
            expect("separator", ")")
        else:
            prod("<Primary> -> IDENTIFIER")
            expect("identifier")
    elif tok.kind in {"integer","real"}:
        if tok.kind == "integer":
            prod("<Primary> -> INTEGER")
        else:
            prod("<Primary> -> REAL")
        advance()
    elif tok.kind == "keyword" and tok.lexeme in {"true","false"}:
        prod("<Primary> -> true | false")
        advance()
    elif tok.kind == "separator" and tok.lexeme == "(":
        prod("<Primary> -> ( <Expression> )")
        expect("separator","(")
        Expression()
        expect("separator",")")
    else:
        error("invalid primary")

# Driver entry point
def parse(src_text: str, outfile_name: str = "sa_output.txt") -> None:
    global tokens, pos, OUTFILE, error_count
    tokens = lexer.tokenize(src_text)
    pos = 0
    error_count = 0  # Reset error count
    
    # Open the output file for the entire parsing process
    with open(outfile_name, "w") as out_file:
        global OUTFILE
        OUTFILE = out_file
        OUTFILE.write(f"{'Token':15s} {'Lexeme':15s}\n")
        OUTFILE.write("-"*35 + "\n")
        
        # Parse the entire program
        Rat25S()
        
        # Make sure OUTFILE is properly closed
        OUTFILE.flush()
    
    if error_count > 0:
        print(f"Parsing completed with {error_count} errors – output in {outfile_name}")
    else:
        print(f"Parsing completed successfully – output in {outfile_name}")

# Stand‑alone CLI
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parser.py <source_file>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        parse(f.read())

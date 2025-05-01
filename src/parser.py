from __future__ import annotations
from typing import List, Optional
import sys
import lexer

TRACE: bool = True
OUTFILE = None


tokens: List[lexer.Token] = []
pos: int = 0

def current() -> lexer.Token:
    return tokens[pos]

def advance() -> None:
    """
    Consume the current token.  *Must* be called only after ensuring it matches
    the expected grammar symbol.
    """
    global pos
    # print token / lexeme BEFORE advancing, per spec
    if OUTFILE:
        OUTFILE.write(f"Token: {current().kind:15s} Lexeme: {current().lexeme}\n")
    pos += 1

def expect(kind: str, lexeme: Optional[str] = None) -> None:
    tok = current()
    if tok.kind != kind or (lexeme is not None and tok.lexeme != lexeme):
        error(f"expected {kind}{' ' + lexeme if lexeme else ''}")
    advance()

def error(msg: str) -> None:
    tok = current()
    print(f"Syntax error at token '{tok.lexeme}' ({tok.kind}) — {msg}", file=sys.stderr)
    sys.exit(1)

def prod(rule: str) -> None:
    if TRACE and OUTFILE:
        OUTFILE.write(f"    {rule}\n")

# Grammar procedures (after factoring) 

# R1  <Rat25S> ::= $$ <Opt Function Definitions> $$ <Opt Declaration List> $$ <Statement List> $$
def Rat25S() -> None:
    prod("<Rat25S> -> $$ <OptFunctionDefinitions> $$ <OptDeclarationList> $$ <StatementList> $$")
    expect("separator", "$$")
    OptFunctionDefinitions()
    expect("separator", "$$")
    OptDeclarationList()
    expect("separator", "$$")
    StatementList()
    expect("separator", "$$")
    expect("eof")   # must reach end cleanly

# R2
def OptFunctionDefinitions() -> None:
    if current().lexeme == "function":
        prod("<OptFunctionDefinitions> -> <FunctionDefinitions>")
        FunctionDefinitions()
    else:
        prod("<OptFunctionDefinitions> -> epsilon")

# R3
def FunctionDefinitions() -> None:
    prod("<FunctionDefinitions> -> <Function> [<FunctionDefinitions>]")
    Function()
    if current().lexeme == "function":
        FunctionDefinitions()

# R4
def Function() -> None:
    prod("<Function> -> function id ( <OptParameterList> ) <OptDeclarationList> <Body>")
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
        prod("<OptParameterList> -> epsilon")

def ParameterList() -> None:
    prod("<ParameterList> -> <Parameter> [ , <ParameterList> ]")
    Parameter()
    if current().lexeme == ",":
        expect("separator", ",")
        ParameterList()

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
        prod("<OptDeclarationList> -> epsilon")

def DeclarationList() -> None:
    prod("<DeclarationList> -> <Declaration> ; [<DeclarationList>]")
    Declaration()
    expect("separator", ";")
    if current().lexeme in {"integer", "boolean", "real"}:
        DeclarationList()

def Declaration() -> None:
    prod("<Declaration> -> <Qualifier> <IDs>")
    Qualifier()
    IDs()

def IDs() -> None:
    prod("<IDs> -> id [ , <IDs> ]")
    expect("identifier")
    if current().lexeme == ",":
        expect("separator", ",")
        IDs()

# R14, R15
def StatementList() -> None:
    prod("<StatementList> -> <Statement> [<StatementList>]")
    Statement()
    starters = {"separator": "{", "identifier": None, "keyword": {
        "if","while","return","scan","print"}}
    while True:
        tok = current()
        if tok.kind == "separator" and tok.lexeme == "{":
            Statement()
        elif tok.kind == "identifier":
            Statement()
        elif tok.kind == "keyword" and tok.lexeme in starters["keyword"]:
            Statement()
        else:
            break

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
    prod("<Assign> -> id = <Expression> ;")
    expect("identifier")
    expect("operator", "=")
    Expression()
    expect("separator", ";")

# R18
def If() -> None:
    prod("<If> -> if ( <Condition> ) <Statement> [else <Statement>] endif")
    expect("keyword", "if")
    expect("separator", "(")
    Condition()
    expect("separator", ")")
    Statement()
    if current().lexeme == "else":
        expect("keyword", "else")
        Statement()
    expect("keyword", "endif")

# R19
def Return() -> None:
    prod("<Return> -> return ; | return <Expression> ;")
    expect("keyword", "return")
    if current().lexeme != ";":
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
        prod("<ExpressionPrime> -> (+|-) <Term> <ExpressionPrime>")
        advance()
        Term()
        ExpressionPrime()
    else:
        prod("<ExpressionPrime> -> epsilon")

def Term() -> None:
    prod("<Term> -> <Factor> <TermPrime>")
    Factor()
    TermPrime()

def TermPrime() -> None:
    if current().kind == "operator" and current().lexeme in {"*","/"}:
        prod("<TermPrime> -> (*|/) <Factor> <TermPrime>")
        advance()
        Factor()
        TermPrime()
    else:
        prod("<TermPrime> -> epsilon")

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
            prod("<Primary> -> id ( <IDs> )")
            expect("identifier")
            expect("separator", "(")
            IDs()
            expect("separator", ")")
        else:
            prod("<Primary> -> id")
            expect("identifier")
    elif tok.kind in {"integer","real"}:
        prod("<Primary> -> integer|real")
        advance()
    elif tok.kind == "keyword" and tok.lexeme in {"true","false"}:
        prod("<Primary> -> true|false")
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
    global tokens, pos, OUTFILE
    tokens = lexer.tokenize(src_text)
    pos = 0
    with open(outfile_name, "w") as OUTFILE:
        OUTFILE.write(f"{'Token':15s} {'Lexeme':15s}\n")
        OUTFILE.write("-"*35 + "\n")
        Rat25S()
    print(f"Parsing completed – output in {outfile_name}")

# Stand‑alone CLI
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python parser.py <source_file>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        parse(f.read())

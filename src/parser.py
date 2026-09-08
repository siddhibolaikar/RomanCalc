from errors import CompilerError
from lexer import TokenType

# Grammar (left-recursion-free, precedence encoded structurally):
#   Expr   -> Term (('+' | '-') Term)*
#   Term   -> Factor (('*' | '/') Factor)*
#   Factor -> '(' Expr ')' | ROMAN_NUM


class NumeralNode:
    def __init__(self, decimal_value, original_roman, position):
        self.decimal_value = decimal_value
        self.original_roman = original_roman
        self.position = position
        self.val = None  # synthesized attribute, filled in during semantic analysis

    def __repr__(self):
        return f"Numeral({self.original_roman}={self.decimal_value})"


class BinaryOpNode:
    def __init__(self, op, left, right, position):
        self.op = op
        self.left = left
        self.right = right
        self.position = position
        self.val = None

    def __repr__(self):
        return f"({self.left!r} {self.op} {self.right!r})"


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, type_):
        tok = self.current()
        if tok.type != type_:
            raise CompilerError(
                "syntax",
                f"expected {type_} but found {tok.type} ('{tok.lexeme}')",
                tok.position,
                tok.lexeme,
            )
        return self.advance()

    def parse(self):
        node = self.parse_expr()
        self.expect(TokenType.EOF)  # ensures no trailing garbage, e.g. "XII IV"
        return node

    def parse_expr(self):
        node = self.parse_term()
        while self.current().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok = self.advance()
            right = self.parse_term()
            node = BinaryOpNode(op_tok.lexeme, node, right, op_tok.position)
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.current().type in (TokenType.STAR, TokenType.SLASH):
            op_tok = self.advance()
            right = self.parse_factor()
            node = BinaryOpNode(op_tok.lexeme, node, right, op_tok.position)
        return node

    def parse_factor(self):
        tok = self.current()

        if tok.type == TokenType.LPAREN:
            self.advance()
            node = self.parse_expr()
            self.expect(TokenType.RPAREN)
            return node

        if tok.type == TokenType.ROMAN_NUM:
            self.advance()
            return NumeralNode(tok.value, tok.lexeme, tok.position)

        raise CompilerError(
            "syntax",
            f"expected a Roman numeral or '(' but found {tok.type} ('{tok.lexeme}')",
            tok.position,
            tok.lexeme,
        )


def tree_to_str(node):
    """Fully parenthesized infix form, e.g. '(XII + (IV * II))'."""
    if isinstance(node, NumeralNode):
        return node.original_roman
    return f"({tree_to_str(node.left)} {node.op} {tree_to_str(node.right)})"


def tree_to_dict(node):
    """JSON-friendly tree for a frontend parse-tree viewer."""
    if isinstance(node, NumeralNode):
        return {"type": "Numeral", "roman": node.original_roman, "value": node.decimal_value}
    return {
        "type": "BinaryOp",
        "op": node.op,
        "left": tree_to_dict(node.left),
        "right": tree_to_dict(node.right),
    }

# PHASE 2: SYNTAX ANALYSIS
# Recursive descent parser. Checks the grammar and builds the parse tree.
#
#   Expr   ->  Term   ( ('+' | '-') Term   )*
#   Term   ->  Factor ( ('*' | '/') Factor )*
#   Factor ->  '(' Expr ')'  |  NUM
from errors import CompilerError


class NumeralNode:                       # a leaf of the tree: one number
    def __init__(self, value, roman, position):
        self.value = value
        self.roman = roman
        self.position = position
        self.val = None                  # filled in by semantic analysis


class BinaryOpNode:                      # an inner node: left  op  right
    def __init__(self, op, left, right, position):
        self.op = op
        self.left = left
        self.right = right
        self.position = position
        self.val = None                  # filled in by semantic analysis


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0                     # which token we are looking at

    def current(self):                   # look at the current token
        return self.tokens[self.pos]

    def advance(self):                   # use up the current token
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def expect(self, type):              # the next token MUST be this type
        token = self.current()
        if token.type != type:
            found = token.lexeme or "end of input"
            raise CompilerError("syntax", f"expected '{type}' but found '{found}'", token.position, token.lexeme)
        return self.advance()

    def parse(self):
        tree = self.parse_expr()
        token = self.current()
        if token.type != "END":          # something is left over, e.g. "XII IV"
            raise CompilerError("syntax", f"unexpected '{token.lexeme}' after the expression", token.position, token.lexeme)
        return tree

    def parse_expr(self):                # Expr -> Term (('+' | '-') Term)*
        node = self.parse_term()
        while self.current().type in ("+", "-"):
            op = self.advance()
            right = self.parse_term()
            node = BinaryOpNode(op.lexeme, node, right, op.position)
        return node

    def parse_term(self):                # Term -> Factor (('*' | '/') Factor)*
        node = self.parse_factor()
        while self.current().type in ("*", "/"):
            op = self.advance()
            right = self.parse_factor()
            node = BinaryOpNode(op.lexeme, node, right, op.position)
        return node

    def parse_factor(self):              # Factor -> '(' Expr ')' | NUM
        token = self.current()

        if token.type == "(":
            self.advance()
            node = self.parse_expr()
            self.expect(")")
            return node

        if token.type == "NUM":
            self.advance()
            return NumeralNode(token.value, token.lexeme, token.position)

        found = token.lexeme or "end of input"
        raise CompilerError("syntax", f"expected a number or '(' but found '{found}'", token.position, token.lexeme)


def tree_to_str(node):
    """The tree on one line, e.g. (XII + (IV * II))"""
    if isinstance(node, NumeralNode):
        return node.roman
    return f"({tree_to_str(node.left)} {node.op} {tree_to_str(node.right)})"


def tree_lines(node, show_val=False, indent=0):
    """The tree as indented lines, one node per line (optionally with its value)."""
    pad = "    " * indent
    tail = f"    (val = {node.val})" if show_val else ""
    if isinstance(node, NumeralNode):
        return [f"{pad}{node.roman}{tail}"]
    return ([f"{pad}{node.op}{tail}"]
            + tree_lines(node.left, show_val, indent + 1)
            + tree_lines(node.right, show_val, indent + 1))

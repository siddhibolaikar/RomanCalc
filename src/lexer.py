from errors import CompilerError

ROMAN_VALUES = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}

# Canonical greedy table, used for round-trip validation and for
# converting a final decimal result back to Roman numeral form.
_CANONICAL = [
    (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
    (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
    (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'),
]

ROMAN_LETTERS = set(ROMAN_VALUES.keys())


def roman_to_int(s):
    """Standard subtractive-notation scan. Assumes s is already known
    to contain only valid Roman letters; does NOT validate formation."""
    total = 0
    prev_value = 0
    for ch in reversed(s):
        value = ROMAN_VALUES[ch]
        if value < prev_value:
            total -= value
        else:
            total += value
            prev_value = value
    return total


def int_to_roman(n):
    """Canonical (strict) Roman numeral form for a decimal integer."""
    result = []
    for value, symbol in _CANONICAL:
        while n >= value:
            result.append(symbol)
            n -= value
    return ''.join(result)


def validate_roman(lexeme, position):
    """Validates formation rules and returns the decimal value.

    Rather than hand-coding every rule (repetition limits, legal
    subtractive pairs, ordering), we use a round-trip check: convert
    lexeme -> value -> canonical Roman form, and require an exact
    match. Any malformed numeral (IIII, VX, IC, IXIX, ...) fails this
    check because it does not equal its own canonical form.
    """
    if not lexeme or any(ch not in ROMAN_VALUES for ch in lexeme):
        raise CompilerError("lexical", f"'{lexeme}' is not composed of valid Roman numeral letters",
                             position, lexeme)

    value = roman_to_int(lexeme)

    if int_to_roman(value) != lexeme:
        raise CompilerError("lexical", f"'{lexeme}' is not a validly formed Roman numeral",
                             position, lexeme)

    if not (1 <= value <= 3999):
        raise CompilerError("lexical", f"'{lexeme}' is out of representable range (1-3999)",
                             position, lexeme)

    return value


class TokenType:
    ROMAN_NUM = "ROMAN_NUM"
    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    SLASH = "SLASH"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    EOF = "EOF"


_SINGLE_CHAR_TOKENS = {
    '+': TokenType.PLUS,
    '-': TokenType.MINUS,
    '*': TokenType.STAR,
    '/': TokenType.SLASH,
    '(': TokenType.LPAREN,
    ')': TokenType.RPAREN,
}


class Token:
    def __init__(self, type_, lexeme, value=None, position=0):
        self.type = type_
        self.lexeme = lexeme
        self.value = value      # decimal value, only set for ROMAN_NUM
        self.position = position

    def __repr__(self):
        val = f", value={self.value}" if self.value is not None else ""
        return f"Token({self.type}, '{self.lexeme}'{val}, pos={self.position})"

    def to_dict(self):
        return {"type": self.type, "lexeme": self.lexeme,
                "value": self.value, "position": self.position}


def tokenize(source):
    """Scans `source` into a list of Tokens, ending with an EOF token.
    Raises CompilerError('lexical', ...) on any invalid character or
    malformed Roman numeral.
    """
    tokens = []
    i = 0
    n = len(source)

    while i < n:
        ch = source[i]

        if ch.isspace():
            i += 1
            continue

        if ch in _SINGLE_CHAR_TOKENS:
            tokens.append(Token(_SINGLE_CHAR_TOKENS[ch], ch, position=i))
            i += 1
            continue

        if ch.upper() in ROMAN_LETTERS:
            start = i
            j = i
            while j < n and source[j].upper() in ROMAN_LETTERS:
                j += 1
            lexeme = source[start:j].upper()
            value = validate_roman(lexeme, start)
            tokens.append(Token(TokenType.ROMAN_NUM, lexeme, value=value, position=start))
            i = j
            continue

        raise CompilerError("lexical", f"unexpected character '{ch}'", i, ch)

    tokens.append(Token(TokenType.EOF, "", position=n))
    return tokens

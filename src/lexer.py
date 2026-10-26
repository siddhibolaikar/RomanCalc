# PHASE 1: LEXICAL ANALYSIS
# Splits the input text into tokens and checks every Roman numeral.
from errors import CompilerError

ROMAN_VALUES = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}

# Roman symbols from biggest to smallest. Used to WRITE a number in Roman form.
CANONICAL = [
    (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
    (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
    (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'),
]


def roman_to_int(s):
    """Read a Roman numeral right to left. A smaller letter before a bigger one is subtracted."""
    total = 0
    biggest = 0
    for ch in reversed(s):
        value = ROMAN_VALUES[ch]
        if value < biggest:
            total -= value
        else:
            total += value
            biggest = value
    return total


def int_to_roman(n):
    """Write a number in the one standard Roman form."""
    result = ""
    for value, symbol in CANONICAL:
        while n >= value:
            result += symbol
            n -= value
    return result


def validate_roman(lexeme, position):
    """Return the numeral's value, or raise an error if it is not written correctly."""
    value = roman_to_int(lexeme)

    # Round trip: write the value back in standard form. It must match what was typed.
    # IIII -> 4 -> IV (different, so rejected).  VX -> 5 -> V (different, so rejected).
    if int_to_roman(value) != lexeme:
        raise CompilerError("lexical", f"'{lexeme}' is not a correctly written Roman numeral", position, lexeme)

    if value > 3999:
        raise CompilerError("lexical", f"'{lexeme}' is bigger than 3999", position, lexeme)

    return value


class Token:
    def __init__(self, type, lexeme, value=None, position=0):
        self.type = type            # "NUM", "+", "-", "*", "/", "(", ")" or "END"
        self.lexeme = lexeme        # the text, e.g. "XII"
        self.value = value          # decimal value (numbers only)
        self.position = position    # character number in the input

    def show(self):
        text = f"{self.type:<4} '{self.lexeme}'"
        if self.value is not None:
            text += f"  value={self.value}"
        return text + f"  position={self.position}"


def tokenize(source):
    tokens = []
    i = 0
    while i < len(source):
        ch = source[i]

        if ch.isspace():                         # skip spaces
            i += 1

        elif ch in "+-*/()":                     # one-character tokens
            tokens.append(Token(ch, ch, position=i))
            i += 1

        elif ch.upper() in ROMAN_VALUES:         # a Roman numeral: take all its letters
            start = i
            while i < len(source) and source[i].upper() in ROMAN_VALUES:
                i += 1
            text = source[start:i].upper()
            tokens.append(Token("NUM", text, validate_roman(text, start), start))

        else:                                    # anything else is not allowed
            raise CompilerError("lexical", f"unexpected character '{ch}'", i, ch)

    tokens.append(Token("END", "", position=len(source)))
    return tokens

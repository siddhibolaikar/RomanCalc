# AI HELPERS (not part of the compiler)
# When a phase finds an error, this file does two things:
#   explain_error:  explains the mistake in plain English
#   suggest_fixes:  proposes a corrected input (main.py then CHECKS it with the compiler)
# It uses an AI model if ANTHROPIC_API_KEY is set; otherwise simple built-in rules.
import json
import os
import re
import urllib.request

from lexer import ROMAN_VALUES, roman_to_int, int_to_roman

LEGAL_PAIRS = ["IV", "IX", "XL", "XC", "CD", "CM"]


def explain_error(error, source):
    """Returns (explanation, who wrote it)."""
    text = ask_ai(error, source)
    if text:
        return text, "AI"
    return offline_explanation(error), "built-in rules"


def call_ai(question, max_tokens):
    """Sends one question to the AI model. Returns its answer, or None if that is not possible."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = json.dumps({
        "model": os.environ.get("ROMANCALC_MODEL", "claude-sonnet-5-5"),
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": question}],
    }).encode()
    request = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as reply:
            data = json.load(reply)
        return "".join(part.get("text", "") for part in data["content"]).strip() or None
    except Exception:
        return None                      # no internet, bad key, ...: use the built-in rules


def ask_ai(error, source):
    question = (f"Roman numeral calculator input: {source!r}\n"
                f"The compiler reported a {error.phase} error: {error.message}\n"
                "Explain the mistake in 3 short plain sentences and give a corrected input.")
    return call_ai(question, 300)


# ---------------------------------------------------------------- suggested fixes
def suggest_fixes(error, source):
    """Corrected inputs worth trying, best first, as (input, who suggested it).
    These are only suggestions. The compiler decides whether any of them is valid."""
    tries = [(ask_ai_for_fix(error, source), "AI"),
             (rule_fix(error, source), "built-in rules")]
    fixes = []
    for candidate, who in tries:
        if candidate and candidate != source and candidate not in [c for c, _ in fixes]:
            fixes.append((candidate, who))
    return fixes


def ask_ai_for_fix(error, source):
    question = (f"Roman numeral calculator input: {source!r}\n"
                f"The compiler reported a {error.phase} error: {error.message}\n"
                "Reply with ONLY the corrected input on one line. No explanation, no quotes.")
    text = call_ai(question, 60)
    if not text:
        return None
    return text.splitlines()[0].strip().strip("`'\"")        # first line only


def rule_fix(error, source):
    """Fixes that need no AI. Only clear-cut mistakes are fixed."""
    word = error.lexeme or ""
    where = error.position

    if error.phase == "lexical" and word and all(c in ROMAN_VALUES for c in word.upper()):
        value = roman_to_int(word.upper())               # IIII -> 4 -> IV
        if 1 <= value <= 3999:
            return source[:where] + int_to_roman(value) + source[where + len(word):]

    if error.phase == "syntax":
        if error.message.startswith("expected ')'") and error.message.endswith("'end of input'"):
            return source + ")" * (source.count("(") - source.count(")"))    # close the brackets
        if "after the expression" in error.message and word == ")":
            return source[:where] + source[where + 1:]                       # remove the extra ')'
    return None


# ---------------------------------------------------------------- explanations
def offline_explanation(error):
    word = error.lexeme or ""

    if error.phase == "lexical":
        if word and all(c in ROMAN_VALUES for c in word.upper()):
            return explain_numeral(word.upper())
        return f"'{word}' is not allowed. Use only the letters I V X L C D M, the symbols + - * / ( ) and spaces."

    if error.phase == "syntax":
        if error.message.startswith("expected ')'"):
            return "A bracket was opened but never closed. Add the matching ')'."
        if "after the expression" in error.message:
            if word == ")":
                return "There is a ')' without a matching '('. Remove it or add the '('."
            return "Two numbers are next to each other. Put an operator (+ - * /) between them."
        return "An operator or bracket must be followed by a Roman number. Add the missing number."

    if "does not fit in 16 bits" in error.message:
        if word.startswith("-"):
            return "A subtraction gives a negative number, and this 8085 program only holds numbers from 0 to 65535. Do not subtract a bigger number from a smaller one."
        return "The result is bigger than 65535, the largest number that fits in the 16-bit register pair HL. Use smaller numbers."

    if "division by zero" in error.message:
        return "The number you divide by works out to zero, and dividing by zero is not possible. Change the right side of the '/'."
    return error.message


def explain_numeral(w):
    value = roman_to_int(w)
    if re.search("V{2,}|L{2,}|D{2,}", w):
        return f"'{w}' repeats V, L or D. These letters can never be repeated. The correct form of {value} is {int_to_roman(value)}."
    if re.search("I{4,}|X{4,}|C{4,}|M{4,}", w):
        if value > 3999:
            return f"'{w}' is bigger than 3999, the largest Roman numeral allowed (MMMCMXCIX)."
        return f"'{w}' repeats a letter 4 or more times. At most 3 in a row are allowed. The correct form is {int_to_roman(value)}."
    for a, b in zip(w, w[1:]):
        if ROMAN_VALUES[a] < ROMAN_VALUES[b] and a + b not in LEGAL_PAIRS:
            return f"'{a}{b}' is not allowed. Only IV, IX, XL, XC, CD and CM may put a smaller letter before a bigger one."
    return f"'{w}' is not in standard form. Its value is {value}, which is written {int_to_roman(value)}."

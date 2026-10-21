# AI ERROR EXPLAINER (not part of the compiler)
# When a phase finds an error, this explains it in plain English.
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


def ask_ai(error, source):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    question = (f"Roman numeral calculator input: {source!r}\n"
                f"The compiler reported a {error.phase} error: {error.message}\n"
                "Explain the mistake in 3 short plain sentences and give a corrected input.")
    body = json.dumps({
        "model": os.environ.get("ROMANCALC_MODEL", "claude-sonnet-5-5"),
        "max_tokens": 300,
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

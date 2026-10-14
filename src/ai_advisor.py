"""AI ADVISORY LAYER - explanation/advice only, never part of compilation.

explain_error(...) gives a plain-English explanation of a compiler error
(lexical, syntax or semantic) and suggests the corrected form.

It calls the Anthropic API when ANTHROPIC_API_KEY is set. If the key is
missing or the call fails, it falls back to a deterministic offline
explainer so the demo never breaks. Every result is labelled with its
source ("llm" or "offline") so the UI is always honest about it.
"""
import json
import os
import re
import urllib.request

from lexer import ROMAN_VALUES, roman_to_int, int_to_roman

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("ROMANCALC_MODEL", "claude-sonnet-5-5")

_SYSTEM = (
    "You are a teaching assistant inside RomanCalc, a compiler for arithmetic on "
    "Roman numerals (valid numerals are 1-3999, standard subtractive notation only: "
    "IV, IX, XL, XC, CD, CM; I, X, C, M may repeat at most 3 times; V, L, D never repeat). "
    "Answer in plain English, 3-5 short sentences, no markdown, no bullet points."
)


def _call_llm(user_prompt, max_tokens=350):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": _SYSTEM,
        "messages": [{"role": "user", "content": user_prompt}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.load(resp)
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return text.strip() or None
    except Exception:
        return None


# ----------------------------------------------------------------- error explainer
def explain_error(error, source):
    prompt = (
        f"A user typed this Roman numeral expression: {source!r}\n"
        f"The compiler reported a {error['phase']} error: {error['message']}"
        f" (position {error.get('position')}, offending text {error.get('lexeme')!r}).\n"
        "Explain what is wrong in plain English and give a corrected expression."
    )
    text = _call_llm(prompt)
    if text:
        return {"source": "llm", "text": text}
    return {"source": "offline", "text": _offline_explain(error, source)}


def _explain_numeral(lex):
    if len(lex) > 1 and re.search(r"(V{2,}|L{2,}|D{2,})", lex):
        return (f"'{lex}' repeats V, L or D. These symbols can never be repeated because "
                "doubling them has its own symbol (VV is X, LL is C, DD is M). "
                f"Rewrite it as {int_to_roman(roman_to_int(lex)) if roman_to_int(lex) <= 3999 else 'a single larger symbol'}.")
    if re.search(r"(I{4,}|X{4,}|C{4,}|M{4,})", lex):
        v = roman_to_int(lex)
        if v > 3999:
            return (f"'{lex}' repeats a symbol more than three times and its value ({v}) is above "
                    "3999, the largest Roman numeral this calculator accepts (MMMCMXCIX).")
        return (f"'{lex}' repeats a symbol four or more times. A symbol may appear at most three "
                f"times in a row; the fourth is written with subtractive notation. "
                f"The correct form is {int_to_roman(v)}.")
    legal = {"IV", "IX", "XL", "XC", "CD", "CM"}
    for a, b in zip(lex, lex[1:]):
        if ROMAN_VALUES[a] < ROMAN_VALUES[b] and a + b not in legal:
            return (f"'{a}{b}' is not an allowed subtractive pair. Only six pairs are legal: "
                    "IV, IX, XL, XC, CD and CM (I may precede V or X, X may precede L or C, "
                    "C may precede D or M). Decide the number you mean and write it in standard "
                    "form, for example 5 is V, 10 is X and 15 is XV.")
    v = roman_to_int(lex)
    if 1 <= v <= 3999:
        return (f"'{lex}' is not written in standard form. Reading it gives {v}, "
                f"and the standard spelling of {v} is {int_to_roman(v)}.")
    return f"'{lex}' is outside the supported range 1-3999."


def _offline_explain(err, source):
    phase, msg, lex = err["phase"], err["message"], err.get("lexeme")
    if phase == "lexical":
        if lex and lex.upper() and set(lex.upper()) <= set(ROMAN_VALUES):
            return _explain_numeral(lex.upper())
        return (f"The character '{lex}' is not allowed. RomanCalc accepts only the letters "
                "I V X L C D M, the operators + - * /, parentheses and spaces. "
                "Digits such as 5 must be written as Roman numerals (V).")
    if phase == "syntax":
        if "expected RPAREN" in msg:
            return "A parenthesis was opened but never closed. Add the matching ')' at the end of the sub-expression."
        if "expected EOF" in msg:
            if "RPAREN" in msg.split("but found")[-1]:
                return "There is a closing ')' with no matching '('. Remove it or add the missing '('."
            return "Two numerals or groups appear next to each other with no operator between them. Put +, -, * or / between them."
        if "expected a Roman numeral or '('" in msg:
            tail = msg.split("but found")[-1]
            if "EOF" in tail:
                return "The expression ends unexpectedly. An operator or '(' must be followed by a Roman numeral or a parenthesised group."
            if "RPAREN" in tail:
                return "A ')' appeared where a number was expected, for example in empty parentheses '()'. Put an expression inside the parentheses."
            return "An operator appeared where a number was expected. Every +, -, *, / needs a Roman numeral (or group) on both sides."
        return "The expression does not follow the grammar: Expr -> Term (+|- Term)*, Term -> Factor (*|/ Factor)*."
    if phase in ("semantic", "runtime") and "division by zero" in msg:
        return ("The right-hand side of a division evaluates to zero, and division by zero is undefined. "
                "Change the divisor so it is not zero (for example II - I instead of II - II).")
    return f"The compiler reported: {msg}"

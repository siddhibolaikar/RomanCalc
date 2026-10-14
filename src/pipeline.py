"""Runs the full RomanCalc pipeline and returns every stage's output as
plain JSON-friendly data (used by both the CLI and the web frontend).

NOTE: the AI advisory layer (ai_advisor.py) is deliberately NOT imported
or called here. The compiler core never depends on AI.
"""
from errors import CompilerError
from lexer import tokenize, int_to_roman
from parser import Parser, tree_to_str, tree_to_dict
from semantic import analyze
from optimizer import optimize
from codegen import generate_code, VM, fmt


PHASE_INFO = [
    {"key": "lexical", "name": "Lexical Analysis",
     "does": "Scans the source text, groups letters into Roman numerals, checks that each numeral is correctly formed (IIII and VX are rejected) and converts it to decimal.",
     "output": "Token stream: type, lexeme, decimal value and position of every token."},
    {"key": "syntax", "name": "Syntax Analysis",
     "does": "A recursive-descent parser checks the tokens against the grammar and builds a parse tree in which * and / bind tighter than + and -.",
     "output": "Parse tree (also shown as a bracketed expression)."},
    {"key": "semantic", "name": "Semantic Analysis (SDT)",
     "does": "Walks the tree bottom-up and computes a value (val) for every node; checks meaning-level rules such as division by zero.",
     "output": "The same tree annotated with val at every node, and the value of the whole expression."},
    {"key": "codegen", "name": "Code Generation",
     "does": "Walks the tree in post-order and emits stack-machine instructions: PUSH for each number, ADD / SUB / MUL / DIV for each operator.",
     "output": "A stack-machine program (unoptimized)."},
    {"key": "optimize", "name": "Code Optimization",
     "does": "Constant folding on the stack program: PUSH a, PUSH b, OP is replaced by PUSH (a OP b), computed at compile time.",
     "output": "A shorter stack program, plus the list of folds that were performed."},
    {"key": "vm", "name": "Execution on the VM",
     "does": "A small virtual machine runs the program with an operand stack. Both the unoptimized and optimized programs are run and must agree with semantic analysis.",
     "output": "The result in decimal and as a Roman numeral, plus a step-by-step stack trace."},
]


def to_roman(value):
    """Returns (roman_string_or_None, note)."""
    if 1 <= value <= 3999:
        return int_to_roman(value), ""
    if value == 0:
        return None, "Roman numerals have no symbol for zero"
    if value < 0:
        return None, "Roman numerals cannot represent negative numbers"
    return None, "Result exceeds 3999, the largest standard Roman numeral (MMMCMXCIX)"


def run_pipeline(source):
    r = {"source": source, "stages_completed": [], "error": None, "phases": PHASE_INFO}
    try:
        # Phase 1: lexical analysis
        tokens = tokenize(source)
        r["tokens"] = [t.to_dict() for t in tokens]
        r["stages_completed"].append("lexical")

        # Phase 2: syntax analysis
        tree = Parser(tokens).parse()
        r["tree_str"] = tree_to_str(tree)
        r["tree"] = tree_to_dict(tree)          # val still None here
        r["stages_completed"].append("syntax")

        # Phase 3: SDT / semantic analysis
        value = analyze(tree)
        r["tree"] = tree_to_dict(tree)          # now decorated with val
        r["semantic_value"] = value
        r["stages_completed"].append("semantic")

        # Phase 4: code generation (tree -> stack-machine program)
        code = generate_code(tree)
        r["code"] = [fmt(i) for i in code]
        r["stages_completed"].append("codegen")

        # Phase 5: code optimization (constant folding on the stack program)
        opt_code, log = optimize(code)
        r["code_opt"] = [fmt(i) for i in opt_code]
        r["fold_log"] = log
        r["stages_completed"].append("optimize")

        # Execution: run both programs on the VM and cross-check with Phase 3
        run_before = VM().run(code)
        run_after = VM().run(opt_code)
        r["vm_before"] = run_before
        r["vm_after"] = run_after
        result = run_after["output"]
        roman, note = to_roman(result)
        r["result_decimal"] = result
        r["result_roman"] = roman
        r["result_note"] = note
        r["consistent"] = (run_before["output"] == run_after["output"] == value)
        r["stages_completed"].append("vm")
    except CompilerError as e:
        r["error"] = e.to_dict()
    return r

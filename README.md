# RomanCalc

A compiler for arithmetic expressions written in Roman numerals
(e.g. `XII + IV * II`). It validates numerals (rejects `IIII`, `VX`, ...),
respects operator precedence, generates and optimizes stack-machine code, and
runs it on a small VM. A web frontend shows, for every phase, what the phase
does and what it outputs.

## Pipeline: what each phase does and outputs

| # | Phase | File | What it does | Output |
|---|-------|------|--------------|--------|
| 1 | Lexical analysis | `src/lexer.py` | Groups letters into Roman numerals, validates their formation (round-trip check), converts to decimal | Token stream |
| 2 | Syntax analysis | `src/parser.py` | Recursive-descent parser checks the grammar; `*` `/` bind tighter than `+` `-` | Parse tree |
| 3 | Semantic analysis (SDT) | `src/semantic.py` | Bottom-up evaluation, a `val` for every node; division-by-zero check | Annotated tree + value |
| 4 | Code generation | `src/codegen.py` | Post-order walk of the tree emitting `PUSH`, `ADD`, `SUB`, `MUL`, `DIV` | Stack-machine program |
| 5 | Code optimization | `src/optimizer.py` | Constant folding: `PUSH a ; PUSH b ; OP` becomes `PUSH (a OP b)` | Shorter program + list of folds |
| - | Execution | `src/codegen.py` (VM) | Runs the program on a stack VM | Result in decimal and Roman |

Example, `XII + IV * II`:

```
Code generation (7)        Code optimization (3)
PUSH 12                    PUSH 20
PUSH 4                     PRINT
PUSH 2                     HALT
MUL
ADD                        folds:  PUSH 4 ; PUSH 2 ; MUL  ->  PUSH 8
PRINT                              PUSH 12 ; PUSH 8 ; ADD  ->  PUSH 20
HALT
```

The result is shown in decimal and converted back to Roman form (zero,
negatives and values above 3999 have no Roman form and are shown as decimal only).

## AI advisory layer (`src/ai_advisor.py`)

One feature: the **error explainer**. When the lexer, parser or semantic
analyzer reports an error, it explains the mistake in plain English and suggests
the corrected form (e.g. `IIII` -> `IV`). **No compiler module imports it**
(a test enforces this), so every compiler phase is hand-built.

It uses the Anthropic API when `ANTHROPIC_API_KEY` is set; otherwise it falls
back to a deterministic offline explainer. Every answer is labelled `LLM` or
`offline fallback` in the UI.

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."     # optional (PowerShell)
```

## Run it

Python 3.10+; the app itself needs no packages.

```powershell
# Web frontend
cd src
python server.py            # open http://localhost:8000

# Command line: every phase, with what it does and its output
python main.py "(XII + IV) * II"

# Step-by-step demo that pauses after each phase (good for presentations)
python demo.py "(XII + IV) * II"

# Tests
pip install pytest
cd ..
python -m pytest tests -v
```

## Grammar

```
Expr   -> Term (('+' | '-') Term)*
Term   -> Factor (('*' | '/') Factor)*
Factor -> '(' Expr ')' | ROMAN_NUM
```

## Layout

```
src/   errors.py lexer.py parser.py semantic.py codegen.py optimizer.py
       ops.py pipeline.py ai_advisor.py server.py main.py demo.py
web/   index.html          (frontend)
tests/ test_lexer.py test_parser.py test_semantic.py test_backend.py test_ai_advisor.py
```

## Design notes

- **Numeral validation**: value -> canonical Roman form -> must equal the input. One check catches `IIII`, `VX`, `IC`, `IXIX`, ...
- **Code generation** goes straight from the parse tree: a post-order walk gives exactly the order a stack machine needs (operands first, then the operator), so precedence is already correct in the code.
- **Optimizer**: in stack code, `PUSH a ; PUSH b ; OP` always computes a constant, so it is folded at compile time. A folded result is itself a `PUSH`, so chains collapse in a single pass. The unoptimized and optimized programs are both run and checked against the semantic phase.
- **Scope**: there is no separate intermediate-code phase; the tree is translated directly to stack code.
- **Division** is integer (floor) division; **division by zero** is a semantic error found during evaluation, not a syntax error.

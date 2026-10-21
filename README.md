# RomanCalc

A very small compiler. You type an arithmetic expression in Roman numerals
(for example `XII + IV * II`) and it compiles it to **assembly language**.

```
XII + IV * II   ->   PUSH 20
                     POP EAX
                     HLT
```

## The five stages

| # | Stage | File | Output |
|---|-------|------|--------|
| 1 | Lexical analysis | `src/lexer.py` | tokens (Roman numerals checked and converted) |
| 2 | Syntax analysis | `src/parser.py` | parse tree (recursive descent) |
| 3 | Semantic analysis | `src/semantic.py` | the tree with a value on every node |
| 4 | Code generation | `src/codegen.py` | assembly language |
| 5 | Code optimization | `src/optimizer.py` | shorter assembly (constant folding) |

The compiler prints the output of every stage in the terminal, ends with the
final assembly program, and saves it to `output.asm`.

If the input has a mistake (for example `IIII` or `XII +`), the stage that finds
it reports the error, and `src/ai_advisor.py` explains it in plain English.
The explainer is not part of the compiler: no stage imports it.
It uses an AI model if `ANTHROPIC_API_KEY` is set, otherwise built-in rules.

## Run it (VS Code terminal)

```powershell
cd src
python main.py "XII + IV * II"          # one expression
python main.py --step "XII + IV * II"   # pause after every stage (press Enter)
python main.py                          # type expressions one after another
```

Optional: a very small web page showing the same output.

```powershell
python ui.py        # then open http://localhost:8000
```

Tests:

```powershell
pip install pytest
cd ..
python -m pytest tests -q
```

## The assembly language

A simplified x86-style assembly for a stack machine. `EAX` and `EBX` are registers.

| Line | Meaning |
|------|---------|
| `PUSH n` | put the number n on the stack |
| `POP EBX` / `POP EAX` | take the top of the stack into a register |
| `ADD EAX, EBX` | EAX = EAX + EBX (likewise `SUB`, `MUL`, `DIV`) |
| `HLT` | stop (the answer is in EAX) |

## Grammar

```
Expr   -> Term   ( ('+' | '-') Term   )*
Term   -> Factor ( ('*' | '/') Factor )*
Factor -> '(' Expr ')'  |  NUM
```

## Files

```
src/   errors.py lexer.py parser.py semantic.py codegen.py optimizer.py
       main.py ai_advisor.py ui.py
tests/ test_lexer.py test_parser.py test_semantic.py test_codegen_optimizer.py
       test_main.py test_ai_advisor.py
```

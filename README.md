# RomanCalc

A very small compiler. You type an arithmetic expression in Roman numerals
(for example `XII + IV * II`) and it compiles it to **8085 assembly language**.

```
XII + IV * II   ->   LXI SP, 0FFFFH
                     LXI H, 0014H        ; HL = 20 (0014H is 20 in hexadecimal)
                     HLT
```

## The five stages

| # | Stage | File | Output |
|---|-------|------|--------|
| 1 | Lexical analysis | `src/lexer.py` | tokens (Roman numerals checked and converted) |
| 2 | Syntax analysis | `src/parser.py` | parse tree (recursive descent) |
| 3 | Semantic analysis | `src/semantic.py` | the tree with a value on every node |
| 4 | Code generation | `src/codegen.py` | 8085 assembly language |
| 5 | Code optimization | `src/optimizer.py` | shorter 8085 assembly (constant folding) |

The compiler prints the output of every stage in the terminal, ends with the
final 8085 program, and saves it to `output.asm`.

If the input has a mistake (for example `IIII` or `XII +`), the stage that finds
it reports the error, and then two AI helpers in `src/ai_advisor.py` take over:

1. **Error explainer:** explains the mistake in plain English.
2. **Suggested fix, verified by the compiler:** proposes a corrected input
   (`IIII + I` -> `IV + I`). The compiler then runs the corrected input through
   all five stages, and the fix is shown only if every stage passes
   (AI proposes, compiler decides). A bad suggestion is rejected with the reason.

The helpers are not part of the compiler: no stage imports them. They use an AI model
if `ANTHROPIC_API_KEY` is set, otherwise built-in rules (which fix a badly written
numeral, a missing `)` and an extra `)`). A verified fix is a valid program, which is
not always what the user meant (`VX - II` becomes `V - II`).

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

## The 8085 program

The 8085 works on bytes and has no multiply or divide instruction, so:

- every number is kept in a **16-bit register pair** (HL or DE), which holds 0 to 65535;
- the left number goes in HL, the right number in DE, and the answer comes back in HL;
- `+ - * /` are small subroutines (`ADD16`, `SUB16`, `MUL16`, `DIV16`) written in 8085 assembly
  (multiply = repeated addition, divide = repeated subtraction).

| Line | Meaning |
|------|---------|
| `LXI SP, 0FFFFH` | set the stack pointer |
| `LXI H, 000CH` | load HL with a number (000CH is 12) |
| `PUSH H` / `POP D` / `POP H` | stack moves of register pairs |
| `CALL MUL16` | HL = HL * DE (likewise `ADD16`, `SUB16`, `DIV16`) |
| `HLT` | stop; the answer is in HL |

Because of the 16-bit registers, every value in an expression must stay between
0 and 65535. Semantic analysis reports an error if a result is negative
(`II - X`) or too big (`MMMCMXCIX * MMMCMXCIX`).

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
       test_main.py test_ai_advisor.py test_fix.py sim8085.py
```

`tests/sim8085.py` is a tiny 8085 simulator used only by the tests: it runs the
generated 8085 programs and checks that HL holds the value semantic analysis computed.

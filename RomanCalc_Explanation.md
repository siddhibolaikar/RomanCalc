# RomanCalc — Explanation Guide (Lexical → Syntax → Semantic Analysis)

Use this as your script for walking your guide through the project. It's
structured the way a compiler-design viva usually goes: problem →
architecture → phase-by-phase (what it does → how the code does it →
show it running) → testing → what's left.

---

## 1. The one-line pitch

"Roman numerals have no native arithmetic support — you can't just add
XII + IV in a calculator. RomanCalc is a compiler that takes an
expression written entirely in Roman numerals, like `XII + IV * II`,
and runs it through the standard compiler pipeline — lexer, parser,
semantic analysis, code generation and code optimization, with a small
VM to run the result — to validate it and compute the answer, respecting
operator precedence and rejecting malformed numerals like `IIII` or `VX`."

If he asks "why is this a compiler and not just a calculator?" — the
answer: because you're not writing an if-else evaluator, you're
building the actual pipeline (tokens → parse tree → decorated tree →
stack-machine code → optimized code → execution), and validating numeral *syntax*
itself (not just doing the arithmetic) is a real lexical-analysis
problem, not a trivial one.

---

## 2. Architecture overview (say this before diving into code)

```
source  ->  LEXER  ->  tokens  ->  PARSER  ->  parse tree  ->  SEMANTIC (SDT)  ->  tree with values
"XII + IV * II"                                                                          |
                                                                                         v
        result  <-  VM runs it  <-  OPTIMIZER (constant folding)  <-  CODE GENERATOR (stack code)
         20 = XX                     PUSH 20 ; PRINT ; HALT            PUSH 12; PUSH 4; PUSH 2; MUL; ADD; ...
```

What each phase takes in and puts out:

| Phase | In | Out |
|---|---|---|
| Lexical | source text | tokens (with decimal values) |
| Syntax | tokens | parse tree |
| Semantic (SDT) | parse tree | tree with a `val` on every node, final value |
| Code generation | annotated tree | stack-machine program |
| Code optimization | stack program | shorter stack program + list of folds |
| VM execution | stack program | result (decimal and Roman) + stack trace |

Each phase is a **pure function**: takes one data structure in, produces
the next one out, or raises a structured error. No shared global state.
This is deliberate — it means each phase can be tested in total
isolation (show him the separate test files as evidence of this).

Files:
- `src/errors.py` — one shared error type used by all phases
- `src/lexer.py` — Phase 1
- `src/parser.py` — Phase 2
- `src/semantic.py` — Phase 3
- `src/codegen.py` — Phase 4 (and the VM), `src/optimizer.py` — Phase 5
- `src/pipeline.py` — runs all phases and returns every phase's output
- `src/main.py`, `src/demo.py`, `src/server.py` — CLI, step-by-step demo, web frontend

---

## 3. Phase 1 — Lexical Analysis (`lexer.py`)

### What this phase's job is
Convert a raw string into a stream of tokens, and — this is the
project-specific part — validate that every Roman numeral in the
string is *legally formed* before it's even allowed to become a token.

### The two sub-problems
1. **Scanning**: walking the string character by character, grouping
   runs of `IVXLCDM` letters together, and recognizing `+ - * / ( )`
   as single-character tokens.
2. **Validation**: a numeral like `IIII` or `VX` scans fine
   character-by-character, but it's not a *real* Roman numeral. This
   needs actual formation rules:
   - I, X, C, M may repeat up to 3 times; V, L, D never repeat.
   - Only six subtractive pairs are legal: IV, IX, XL, XC, CD, CM.
   - Symbols must appear in non-increasing value order except for
     those six pairs.

### The key design decision: round-trip validation
Rather than hand-coding all three rules above as separate checks, I
used one trick that catches all of them at once:

1. Convert the candidate string to a decimal value using the standard
   subtractive-notation scan (`roman_to_int`).
2. Convert that decimal value *back* to Roman numerals using the
   canonical greedy algorithm (`int_to_roman`) — this always produces
   the one "correct" spelling for that number.
3. If the original string doesn't match this canonical form exactly,
   it was malformed.

**Why this works**: `IIII` converts to 4, but the canonical form of 4
is `IV` — mismatch, rejected. `VX` doesn't even scan to something
whose canonical form is `VX` — mismatch, rejected. One check replaces
three separate rule implementations. This is worth explicitly
mentioning — it shows a design trade-off (simplicity/correctness vs.
writing out every individual rule), which examiners like to hear you
justify.

### Walk through the code with him
Open `lexer.py` and point at, in this order:
1. `ROMAN_VALUES` and `_CANONICAL` — the two lookup tables.
2. `roman_to_int()` — explain the algorithm: scan right to left, if a
   symbol's value is less than the value to its right, subtract it,
   else add it.
3. `int_to_roman()` — greedy: repeatedly subtract the largest table
   entry that fits.
4. `validate_roman()` — the round-trip check, plus the range check
   (1–3999).
5. `tokenize()` — the actual scanner loop: skip whitespace, match
   single-char operators, greedily consume Roman letters and hand them
   to `validate_roman`, raise `CompilerError("lexical", ...)` on
   anything else.

### Trace one example live
Run:
```powershell
cd src
python main.py "XII + IV * II"
```
Show him the printed token list and narrate it:
```
Token(ROMAN_NUM, 'XII', value=12, pos=0)
Token(PLUS, '+', pos=4)
Token(ROMAN_NUM, 'IV', value=4, pos=6)
Token(STAR, '*', pos=9)
Token(ROMAN_NUM, 'II', value=2, pos=11)
Token(EOF, '', pos=13)
```
Point out: each numeral token already carries its **decimal value** —
the lexer isn't just splitting text, it's doing the Roman→decimal
conversion as part of tokenizing.

### Then show a rejection
```powershell
python main.py "IIII + I"
```
Output: `[LEXICAL ERROR] 'IIII' is not a validly formed Roman numeral (position 0)`
— this demonstrates the validation actually firing.

---

## 4. Phase 2 — Syntax Analysis (`parser.py`)

### What this phase's job is
Take the flat token list and build a **tree** that reflects the
grammar — specifically, one that respects operator precedence
(`*`/`/` before `+`/`-`) and parentheses, and reject anything that
isn't a valid expression (unbalanced parens, missing operators,
trailing operators, etc.).

### The grammar (write this on the board / show it directly)
```
Expr   → Term (('+' | '-') Term)*
Term   → Factor (('*' | '/') Factor)*
Factor → '(' Expr ')' | ROMAN_NUM
```
Explain **why this shape encodes precedence without needing a separate
precedence table**: `Expr` is built from `Term`s, and `Term` is built
from `Factor`s — so by the time you're inside a `Term`, you've already
"locked in" that `*`/`/` bind tighter, because a `Term` can only be
broken apart by `*`/`/`, never by `+`/`-`. This is the single most
important thing to be able to explain clearly — it's the classic
follow-up question ("how does your parser know precedence?").

### Recursive descent, one function per rule
This is the core technique: each grammar rule becomes one function,
and each function calls the *next tighter-precedence* function first.
Walk through `parse_expr()`, `parse_term()`, `parse_factor()` in that
order and point out the mirror between the grammar and the code — it's
almost line-for-line.

Also point out `parse_factor()` handling `(`: it recursively calls
`parse_expr()` again for whatever's inside the parens — this is what
lets parentheses override precedence, and it's naturally
self-similar/recursive rather than a special case bolted on.

### The parse tree data structure
Two node types: `NumeralNode` (a leaf, holds a decimal value) and
`BinaryOpNode` (an internal node, holds an operator and two children).
Show `tree_to_str()` — this renders the tree as a fully-parenthesized
string, which is the easiest way to *prove* precedence worked without
drawing a diagram.

### Trace it live
```powershell
python main.py "XII + IV * II"
```
Point at the printed line: `Parse tree: (XII + (IV * II))` — the
multiplication got grouped into its own subtree on the right, even
though it appeared after the `+` in the source text. That's precedence
working, visible directly in the tree shape.

### Show a syntax error
```powershell
python main.py "XII +"
```
This should raise a syntax error because `parse_term()` gets called
looking for the right-hand operand after `+` and finds `EOF` instead.

---

## 5. Phase 3 — SDT / Semantic Analysis (`semantic.py`)

### What this phase's job is
Two things, cleanly separated:
1. **Evaluate** the parse tree to get the final numeric result
   (syntax-directed translation).
2. **Catch errors that can only be detected at evaluation time** —
   specifically division by zero, which you cannot know about just
   from looking at the tree's *shape*; you need the actual computed
   values of both operands.

### The technique: S-attributed SDT, post-order traversal
Every node gets a synthesized attribute called `val`. For a leaf
(`NumeralNode`), `val` is just its decimal value. For an internal node
(`BinaryOpNode`), `val` is computed *after* recursively computing both
children's `val` — that's the "bottom-up" part. Walk through
`analyze()` and point out this is exactly a post-order tree traversal:
recurse left, recurse right, *then* combine.

### Why division-by-zero belongs here and not earlier
This is a good question to preempt: "why didn't you catch this in the
parser?" Answer: the parser only knows the *shape* — it doesn't know
that `II - II` evaluates to `0` until semantic analysis actually
computes it. This is the textbook distinction between syntax
(structure) and semantics (meaning/values) — a great line to say
directly if asked.

### Trace it live
```powershell
python main.py "X / (II - II)"
```
Output: `[SEMANTIC ERROR] division by zero (position 2)` — note this
only fires *after* the parser successfully built a perfectly valid
tree for `X / (II - II)`. The tree is syntactically fine; the problem
only appears once you evaluate it.

### The optional stricter check
Mention `check_representable()` — not wired into the default pipeline,
but available for the design question of "should `MMMCMXCIX * II`
(=7998, which is a fine integer but can't be written as a Roman
numeral) be an error, or should the calculator just show it in
decimal?" This shows you thought about an edge case beyond what was
strictly required.

---

## 6. Error handling as a cross-cutting design choice

Show `errors.py`. One `CompilerError` class used by *all three*
phases, carrying `phase`, `message`, `position`, `lexeme`. Explain the
reasoning: it means every error, regardless of which phase raised it,
can be handled the same way by whatever consumes it — right now that's
just `main.py` printing it, but this is also exactly the shape you'll
hand to the planned AI error-explainer layer later (structured data in,
plain-English explanation out) without changing anything in the
compiler itself.

---

## 7. Testing strategy

37 tests across three files, one per phase — mention this maps
directly to the phase separation. Run them live:
```powershell
cd D:\RomanCalc\romancalc
python -m pytest tests/ -v
```
Talking points:
- `test_lexer.py` — valid numerals across the full useful range, every
  invalid pattern you can think of (`IIII`, `VX`, `IC`, `IXIX`, ...),
  and a brute-force round-trip check across **all 3999 possible
  values** — this is worth highlighting, it's not just a few examples,
  it's exhaustive.
- `test_parser.py` — precedence, associativity, and every syntax error
  shape (trailing operator, unbalanced parens, empty parens, missing
  operator between two numerals).
- `test_semantic.py` — correct evaluation across several expressions,
  division by zero, and the representability check.

---

## 8. Suggested live demo order (5 minutes)

1. `python main.py "XII + IV * II"` — happy path, narrate tokens →
   tree → result.
2. `python main.py "(XII + IV) * II"` — same numbers, different
   parens, different (larger) result — proves precedence/parens both
   work correctly.
3. `python main.py "IIII + I"` — lexical error.
4. `python main.py "XII +"` — syntax error.
5. `python main.py "X / (II - II)"` — semantic error.
6. `python -m pytest tests/ -v` — 37 passing, closing note.

---

## 9. Phase 4 - Code Generation (`codegen.py`)

**What it does:** translates the annotated parse tree straight into a
**stack-machine program**. A stack machine needs operands first, then the operator,
which is exactly what a post-order walk of the tree produces:

- numeral leaf -> `PUSH <value>`
- operator node -> code for the left child, code for the right child, then `ADD` / `SUB` / `MUL` / `DIV`
- the program ends with `PRINT` (output the top of the stack) and `HALT`

**Output** for `XII + IV * II`:
```
PUSH 12
PUSH 4
PUSH 2
MUL        <- pops 4 and 2, pushes 8
ADD        <- pops 12 and 8, pushes 20
PRINT
HALT
```
Say: "precedence is already decided by the shape of the tree, so the generated code
is in the right order with no extra logic: the multiplication appears before the
addition because it is deeper in the tree."

## 10. Phase 5 - Code Optimization (`optimizer.py`)

**What it does:** constant folding on the stack program. In postfix code the
pattern `PUSH a ; PUSH b ; OP` always computes a constant, so it is replaced by a
single `PUSH (a OP b)` at compile time. The folded result is itself a `PUSH`, so it
can fold again with the next instruction: chains collapse in one left-to-right pass.

**Output** for `XII + IV * II`:
```
PUSH 4 ; PUSH 2 ; MUL    ->  PUSH 8
PUSH 12 ; PUSH 8 ; ADD   ->  PUSH 20
optimized program:  PUSH 20 ; PRINT ; HALT      (7 instructions -> 3)
```
The page shows the program before and after, the list of folds, and the instruction
count. Be ready to say: since every operand in this language is a literal, every
expression folds down to one `PUSH`. The pass is still a real optimization: it
removes work the VM would do at run time (7 VM steps become 3).

## 11. Execution on the VM (`codegen.py`, class `VM`)

Operand stack, one instruction at a time, with a trace (pc, instruction, stack
after). Both the unoptimized and the optimized program are run, and the
pipeline checks that both results equal the value from semantic analysis, which
cross-validates code generation and optimization. The result is shown in decimal
and converted back to Roman (zero, negatives and values above 3999 have no Roman
form, so only decimal is shown). Runtime errors (stack underflow, divide by zero)
are reported with phase `runtime`.

## 12. The AI layer (`ai_advisor.py`) - how to answer "where is AI used?"

- One feature: the **error explainer**. When a phase reports an error, it explains
  the mistake in plain English and suggests the correct form (e.g. `IIII` -> `IV`).
- It is **advisory**: no compiler module imports it
  (`test_core_compiler_never_imports_ai_layer` proves it). Delete the file and the
  compiler still works.
- Uses the Anthropic API if `ANTHROPIC_API_KEY` is set, otherwise a deterministic
  offline explainer. The UI tags each answer `LLM` or `offline fallback`.

## 13. Web frontend (`server.py` + `web/index.html`)

Standard-library HTTP server, one page. `POST /api/compile` runs the pipeline and
returns every phase's output as JSON, plus a description of each phase
(`PHASE_INFO` in `pipeline.py`). Every card shows **what the phase does** and its
**output**: tokens, parse tree (SVG), the tree with `val` on every node, the stack
program, before/after optimization with the folds, and the VM trace and result.
`/api/explain-error` serves the AI layer. The strip at the top turns green phase
by phase and red at the phase that failed.

## 14. Scope note (if asked)

The pipeline is lexical -> syntax -> semantic/SDT -> code generation -> code
optimization, then execution on the VM. There is no separate intermediate-code
phase: the tree is translated directly to stack code, because a post-order walk
already yields the order a stack machine needs.

## 15. Final demo order (5-6 minutes)

1. `python server.py`, open http://localhost:8000, run `XII + IV * II` and walk the cards top to bottom, reading each "What it does / Output" box.
2. `(XII + IV) * II`: parentheses change the tree, the code and the result (32).
3. `IIII + I`: lexical error plus AI explanation.  `XII +`: syntax error.  `X / (II - II)`: semantic error.
4. `MMMCMXCIX * II`: valid program, result 7998 has no Roman form.
5. `python demo.py "XII + IV * II"` for the terminal version (pauses after every phase), then `python -m pytest tests -v` (63 passing).

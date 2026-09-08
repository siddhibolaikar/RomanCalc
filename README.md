# RomanCalc

A compiler that parses, validates, and evaluates arithmetic expressions
written in Roman numerals (e.g. `XII + IV * II`), respecting operator
precedence and rejecting invalid numeral formations (`IIII`, `VX`, ...).

This repo currently implements the first three compiler phases:

1. **Lexical analysis** (`src/lexer.py`) — scans the input, validates
   Roman numeral formation via a round-trip check (numeral → decimal
   → canonical numeral, must match exactly), and emits a token stream.
2. **Syntax analysis** (`src/parser.py`) — a recursive descent parser
   over the grammar below, producing a binary parse tree with
   precedence already structural.
3. **Syntax-directed translation / semantic analysis**
   (`src/semantic.py`) — a bottom-up (post-order) evaluation that
   synthesizes a `val` attribute on every node, and semantic checks
   (division by zero, representable range).

Planned next: intermediate code generation (three-address code /
quadruples), constant-folding optimization, and a stack-machine code
generator + VM.

## Grammar

```
Expr   -> Term (('+' | '-') Term)*
Term   -> Factor (('*' | '/') Factor)*
Factor -> '(' Expr ')' | ROMAN_NUM
```

## Usage

```bash
cd src
python main.py "XII + IV * II"
```

```
Tokens:
  Token(ROMAN_NUM, 'XII', value=12, pos=0)
  Token(PLUS, '+', pos=4)
  Token(ROMAN_NUM, 'IV', value=4, pos=6)
  Token(STAR, '*', pos=9)
  Token(ROMAN_NUM, 'II', value=2, pos=11)
  Token(EOF, '', pos=13)

Parse tree: (XII + (IV * II))

Decimal result: 20
```

Errors from any phase are raised as a structured `CompilerError`
(`src/errors.py`) carrying `{phase, message, position, lexeme}`, so a
later error-explainer layer (or a frontend) can consume them directly
rather than parsing error text.

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

37 tests covering:
- valid/invalid Roman numeral formation (including a full 1-3999
  round-trip check)
- operator precedence and left-associativity
- syntax errors (unbalanced parens, missing operators, empty input)
- semantic errors (division by zero, out-of-range results)

## Project structure

```
romancalc/
├── src/
│   ├── errors.py     # shared CompilerError type
│   ├── lexer.py       # tokenizer + Roman numeral validation
│   ├── parser.py      # recursive descent parser + parse tree
│   ├── semantic.py    # SDT evaluation + semantic checks
│   └── main.py        # CLI driver, runs all three phases
└── tests/
    ├── test_lexer.py
    ├── test_parser.py
    └── test_semantic.py
```

## Design notes

- **Roman numeral validation** uses a round-trip trick instead of
  hand-coded regex rules: convert the lexeme to a decimal value using
  standard subtractive-notation scanning, then re-render that value
  using the canonical greedy algorithm. If the two strings don't match
  exactly, the numeral is malformed. This catches `IIII`, `VX`, `IC`,
  `IXIX`, etc. in one check instead of enumerating every rule.
- **Precedence** is encoded structurally in the grammar (`Expr` calls
  `Term` calls `Factor`), so the recursive descent parser needs no
  separate precedence-climbing logic.
- **Division by zero** is deliberately a semantic-phase check, not a
  lexical or syntax one — it can only be detected once both operand
  values are known, which requires walking the tree.
- **Range/representability** (1-3999) is checked at the lexer for
  every literal numeral. `semantic.check_representable()` is provided
  separately for checking *computed results* (e.g. `MMMCMXCIX * II`
  produces a valid integer that's out of Roman numeral range) — call
  it explicitly if your design treats that as an error rather than a
  decimal-only output.

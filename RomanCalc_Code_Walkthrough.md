# RomanCalc: Code Walkthrough for the ISE

How to use this guide: read it top to bottom once. Then keep **section 2 (one example through every phase)**
and **section 11 (likely questions)** open while you present. Every code block is copied from your real
files (comments inside the code are kept, docstrings removed), and every output is from really running the compiler.

**Contents**
1. The big picture
2. One example followed through every phase
3. `errors.py`: how errors are reported
4. Phase 1, Lexical analysis (`lexer.py`)
5. Phase 2, Syntax analysis (`parser.py`)
6. Phase 3, Semantic analysis (`semantic.py`)
7. Phase 4, Code generation (`codegen.py`), the assembly language
8. Phase 5, Code optimization (`optimizer.py`)
9. `main.py` (the terminal driver), the AI explainer, the backup UI
10. How to present it to sir
11. Questions sir may ask, with answers
12. One-page cheat sheet

---

## 1. The big picture

A compiler turns text a human writes into a program a machine can follow, in small steps (phases).
Each phase takes the output of the previous one. **RomanCalc takes a Roman numeral expression and produces assembly language.**

```
"XII + IV * II"
      |  Phase 1  LEXICAL ANALYSIS     reads the characters, makes tokens        lexer.py
      v
   tokens
      |  Phase 2  SYNTAX ANALYSIS      checks the grammar, builds a tree         parser.py
      v
 parse tree
      |  Phase 3  SEMANTIC ANALYSIS    works out the value of every node         semantic.py
      v
 tree with values
      |  Phase 4  CODE GENERATION      writes assembly language                  codegen.py
      v
 assembly (13 lines)
      |  Phase 5  CODE OPTIMIZATION    does the constant sums at compile time    optimizer.py
      v
 shorter assembly (3 lines)  =  THE FINAL OUTPUT  (printed, and saved to output.asm)
```

In one line each:
- **Lexical analysis** is like reading words: it splits the text into tokens and checks each Roman numeral is spelled correctly.
- **Syntax analysis** is like checking the grammar of a sentence: is `XII +` a complete expression? It also decides what is grouped with what, which is precedence.
- **Semantic analysis** is about meaning: it works out values and catches things like division by zero.
- **Code generation** writes the instructions (assembly) a machine can follow.
- **Code optimization** makes those instructions shorter without changing the answer.

There is no virtual machine: the compiler's job ends with the assembly program.

**Files**

| File | What it contains |
|---|---|
| `errors.py` | The one error type every phase uses |
| `lexer.py` | Phase 1, plus the Roman numeral conversion helpers |
| `parser.py` | Phase 2, plus the tree node classes |
| `semantic.py` | Phase 3 |
| `codegen.py` | Phase 4 |
| `optimizer.py` | Phase 5 |
| `main.py` | Runs the phases in order and prints each one's output in the terminal |
| `ai_advisor.py` | The AI error explainer (not part of the compiler) |
| `ui.py` | A very small web page showing the same output (backup) |

---

## 2. One example followed through every phase

Input: `XII + IV * II`   (that is 12 + 4 x 2, and `*` goes before `+`).

**Phase 1, Lexical analysis, output = tokens**
```
NUM  'XII'  value=12  position=0
+    '+'  position=4
NUM  'IV'  value=4  position=6
*    '*'  position=9
NUM  'II'  value=2  position=11
END  ''  position=13
```
Each Roman numeral already carries its decimal value, and a special `END` token marks the end of the input.

**Phase 2, Syntax analysis, output = parse tree** (each line is one node, children are indented under their operator)
```
+
    XII
    *
        IV
        II
```
As a picture:
```
        +
       / \
     XII   *
          / \
         IV  II
```
The multiplication sits inside the addition. That is how precedence shows up in a tree: the deeper an operation is, the earlier it happens.

**Phase 3, Semantic analysis, output = the same tree with a value (`val`) on every node**
```
+    (val = 20)
    XII    (val = 12)
    *    (val = 8)
        IV    (val = 4)
        II    (val = 2)
```
The values are worked out from the bottom up: IV and II are known, then `*` gives 8, then `+` gives 20.

**Phase 4, Code generation, output = assembly (13 lines)**
```
PUSH 12
PUSH 4
PUSH 2
POP EBX
POP EAX
MUL EAX, EBX
PUSH EAX
POP EBX
POP EAX
ADD EAX, EBX
PUSH EAX
POP EAX
HLT
```

**Phase 5, Code optimization, output = shorter assembly (3 lines)**
```
PUSH 4, PUSH 2, MUL   ->   PUSH 8
PUSH 12, PUSH 8, ADD   ->   PUSH 20
13 lines of assembly  ->  3 lines
```

**Final output = the assembly program** (the answer, 20, is left in register EAX)
```
PUSH 20
POP EAX
HLT
```

What the three kinds of error look like:
```
lexical error: 'IIII' is not a correctly written Roman numeral (position 0)
syntax error: expected a number or '(' but found 'end of input' (position 5)
semantic error: division by zero (position 2)
```
Each phase can only fail on its own kind of problem: bad numeral spelling in Phase 1, a broken sentence in Phase 2, bad meaning (division by zero) in Phase 3. After an error, the pipeline stops, and the AI explainer says in plain English what went wrong.

---

## 3. `errors.py`: how errors are reported

Every phase needs a way to say "something is wrong, here is what and where". They all raise one error type:

```python
# errors.py
class CompilerError(Exception):

    def __init__(self, phase, message, position=None, lexeme=None):
        super().__init__(message)
        self.phase = phase          # "lexical", "syntax" or "semantic"
        self.message = message      # what is wrong
        self.position = position    # character number in the input
        self.lexeme = lexeme        # the offending text
```

- `phase` says which phase found the problem: `"lexical"`, `"syntax"` or `"semantic"`.
- `message` describes the problem, `position` is the character number in the input, and `lexeme` is the offending text.
- `super().__init__(message)` lets Python treat it as a normal error.

When a phase raises this, `main.py` catches it and shows it. The later phases never run on bad input.

---

## 4. Phase 1, Lexical analysis (`lexer.py`)

**Job:** turn the raw text into a list of tokens, and reject badly written Roman numerals.

A **token** is one meaningful piece of the input: a number, an operator, or a bracket. A **lexeme** is the actual text of that piece (for example `XII`).

### 4.1 The lookup tables
```python
# lexer.py
ROMAN_VALUES = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
```
```python
# lexer.py
CANONICAL = [
    (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
    (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
    (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I'),
]
```

- `ROMAN_VALUES` says what each letter is worth.
- `CANONICAL` is the list used to **write** a number in Roman form, biggest first. It includes the six subtractive pairs (`CM`=900, `CD`=400, `XC`=90, `XL`=40, `IX`=9, `IV`=4), so the writing is always in the standard form.

### 4.2 Roman to number: `roman_to_int`
```python
# lexer.py
def roman_to_int(s):
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
```

It reads the numeral **from right to left**, remembering the biggest value seen so far.
- If a letter is **smaller** than a letter already seen to its right, it is a subtraction (like the `I` in `IV`), so subtract it.
- Otherwise add it and update `biggest`.

Example `XIV`, right to left: `V`=5, total 5. `I`=1 is smaller than 5, so subtract: total 4. `X`=10 is not smaller, so add: total 14.

### 4.3 Number to Roman: `int_to_roman`
```python
# lexer.py
def int_to_roman(n):
    result = ""
    for value, symbol in CANONICAL:
        while n >= value:
            result += symbol
            n -= value
    return result
```

Greedy method: take the biggest table entry that still fits, write its symbol, subtract it, repeat.
Example 1994: `M` leaves 994, `CM` leaves 94, `XC` leaves 4, `IV` leaves 0, so `MCMXCIV`.

This always gives **the one standard way** to write a number. That is the key to the validator.

### 4.4 Checking a numeral is spelled correctly: `validate_roman`
```python
# lexer.py
def validate_roman(lexeme, position):
    value = roman_to_int(lexeme)

    # Round trip: write the value back in standard form. It must match what was typed.
    # IIII -> 4 -> IV (different, so rejected).  VX -> 5 -> V (different, so rejected).
    if int_to_roman(value) != lexeme:
        raise CompilerError("lexical", f"'{lexeme}' is not a correctly written Roman numeral", position, lexeme)

    if value > 3999:
        raise CompilerError("lexical", f"'{lexeme}' is bigger than 3999", position, lexeme)

    return value
```

Two checks:
1. **Round trip.** Convert to a number, write that number back in standard form, and require the result to be **exactly the same text** as the input. If not, the input was badly formed.
2. **Range.** The value must not be above 3999 (`MMMM` is spelled "correctly" but is 4000).

Why the round trip works:
- `IIII` is read as 4. The standard spelling of 4 is `IV`, which is not `IIII`, so it is rejected.
- `VX` is read as 5 (right to left: `X`=10, then `V` is smaller so it is subtracted: 5). The standard spelling of 5 is `V`, not `VX`, so it is rejected.
- `XIV` is read as 14, and the standard spelling of 14 is `XIV`, so it is accepted.

One simple check replaces writing out every rule (no more than three repeats, `V L D` never repeat, only six legal subtractive pairs, correct order). The tests check all 3999 numbers go round the trip correctly.

### 4.5 The token class
```python
# lexer.py
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
```

- A token stores its `type`, its `lexeme` (text), its `value` (only numbers have one) and its `position`.
- The token type is just a string: `"NUM"` for a number, the symbol itself (`"+"`, `"*"`, `"("` ...) for operators and brackets, and `"END"` for the end of the input.
- `show()` makes the line that is printed in the terminal.

### 4.6 The scanner: `tokenize`

It walks through the input one character at a time using the index `i`.

Set-up and the loop:
```python
# lexer.py
tokens = []
i = 0
while i < len(source):
    ch = source[i]
```
- `tokens` collects the result, `i` is the current position, and `ch` is the current character.

Case 1, spaces are skipped:
```python
# lexer.py
if ch.isspace():                         # skip spaces
    i += 1
```

Case 2, one-character tokens (`+ - * / ( )`):
```python
# lexer.py
elif ch in "+-*/()":                     # one-character tokens
    tokens.append(Token(ch, ch, position=i))
    i += 1
```
- A token is made (its type is the symbol itself) and `i` moves on by one.

Case 3, a Roman numeral:
```python
# lexer.py
elif ch.upper() in ROMAN_VALUES:         # a Roman numeral: take all its letters
    start = i
    while i < len(source) and source[i].upper() in ROMAN_VALUES:
        i += 1
    text = source[start:i].upper()
    tokens.append(Token("NUM", text, validate_roman(text, start), start))
```
- `start` remembers where the numeral begins, then `i` moves forward for as long as the characters are Roman letters, so `XII` is taken as one piece.
- `text` is that piece in capitals. `validate_roman` checks it and returns its value; a bad numeral raises the error right here.
- A `NUM` token is made carrying the value.

Case 4, anything else is an error:
```python
# lexer.py
else:                                    # anything else is not allowed
    raise CompilerError("lexical", f"unexpected character '{ch}'", i, ch)
```
Digits like `5` and letters like `A` end up here.

The end:
```python
# lexer.py
tokens.append(Token("END", "", position=len(source)))
return tokens
```
The `END` token marks the end of the input, so the parser can tell "finished" from "something is missing".

**Phase 1 summary:** input is text, output is a list of tokens. It catches wrong characters and wrongly written numerals.

---

## 5. Phase 2, Syntax analysis (`parser.py`)

**Job:** check the tokens follow the grammar and build the parse tree.

### 5.1 The grammar
```
Expr   -> Term   ( ('+' | '-') Term   )*
Term   -> Factor ( ('*' | '/') Factor )*
Factor -> '(' Expr ')'  |  NUM
```
Read it as:
- An **Expr** is one Term, followed by any number of (`+` or `-` and another Term).
- A **Term** is one Factor, followed by any number of (`*` or `/` and another Factor).
- A **Factor** is a number, or a whole Expr inside brackets.

**How the grammar gives precedence:** an Expr is made of Terms, and a Term is made of Factors. So `4 * 2` is bound together **inside** a Term before the Expr ever sees a `+`. That makes `*` bind tighter than `+` without any precedence table. Brackets work because a Factor can contain a whole Expr again.

**Why `( ... )*` and not `Expr -> Expr + Term`:** a recursive-descent parser cannot handle a rule that starts by calling itself (it would loop forever). The `( ... )*` form becomes a simple `while` loop.

### 5.2 The tree nodes
```python
# parser.py
class NumeralNode:                       # a leaf of the tree: one number
    def __init__(self, value, roman, position):
        self.value = value
        self.roman = roman
        self.position = position
        self.val = None                  # filled in by semantic analysis
```
```python
# parser.py
class BinaryOpNode:                      # an inner node: left  op  right
    def __init__(self, op, left, right, position):
        self.op = op
        self.left = left
        self.right = right
        self.position = position
        self.val = None                  # filled in by semantic analysis
```

- A `NumeralNode` is a **leaf**: the number and the original Roman text.
- A `BinaryOpNode` is an **inner node**: an operator with a `left` and a `right` child.
- Both have a `val` that starts as `None`. Phase 3 fills it in.

### 5.3 The Parser class: small helper methods
```python
# parser.py
def __init__(self, tokens):
    self.tokens = tokens
    self.pos = 0                     # which token we are looking at
```
```python
# parser.py
def current(self):                   # look at the current token
    return self.tokens[self.pos]
```
```python
# parser.py
def advance(self):                   # use up the current token
    token = self.tokens[self.pos]
    self.pos += 1
    return token
```
```python
# parser.py
def expect(self, type):              # the next token MUST be this type
    token = self.current()
    if token.type != type:
        found = token.lexeme or "end of input"
        raise CompilerError("syntax", f"expected '{type}' but found '{found}'", token.position, token.lexeme)
    return self.advance()
```

- `tokens` is the list from Phase 1, and `pos` is which token we are looking at.
- `current()` looks at the current token without using it up.
- `advance()` returns the current token and moves to the next one.
- `expect(type)` says "the next token **must** be this type". If it is, it is consumed; if not, a syntax error says what was expected and what was found.

### 5.4 One function per grammar rule

**Expr:**
```python
# parser.py
def parse_expr(self):                # Expr -> Term (('+' | '-') Term)*
    node = self.parse_term()
    while self.current().type in ("+", "-"):
        op = self.advance()
        right = self.parse_term()
        node = BinaryOpNode(op.lexeme, node, right, op.position)
    return node
```
- Parse one Term first. That is the left side so far.
- `while` the next token is `+` or `-`: use up the operator, parse another Term for the right side, and build a new `BinaryOpNode` with the old node on the left and the new Term on the right.
- This loop is what `( ... )*` in the grammar means.

**Why subtraction goes left to right:** for `X - V - II` the loop first builds `(X - V)`, then uses that as the left side of the next `-` to give `((X - V) - II)` = 3. That is correct.

**Term** is the same shape, one level tighter:
```python
# parser.py
def parse_term(self):                # Term -> Factor (('*' | '/') Factor)*
    node = self.parse_factor()
    while self.current().type in ("*", "/"):
        op = self.advance()
        right = self.parse_factor()
        node = BinaryOpNode(op.lexeme, node, right, op.position)
    return node
```
- It calls `parse_factor` for its pieces and loops on `*` and `/`.

**Factor** is the base case:
```python
# parser.py
def parse_factor(self):              # Factor -> '(' Expr ')' | NUM
    token = self.current()

    if token.type == "(":
        self.advance()
        node = self.parse_expr()
        self.expect(")")
        return node

    if token.type == "NUM":
        self.advance()
        return NumeralNode(token.value, token.lexeme, token.position)

    found = token.lexeme or "end of input"
    raise CompilerError("syntax", f"expected a number or '(' but found '{found}'", token.position, token.lexeme)
```
- If the token is `(`: use it up, parse a whole Expr inside (recursion!), then `expect` the closing `)`.
- If the token is a number: use it up and make a leaf node.
- Otherwise it is a syntax error ("expected a number or '('"). This catches `XII +` (after `+` it finds the end where a number should be) and `()`.

**Starting the parse:**
```python
# parser.py
def parse(self):
    tree = self.parse_expr()
    token = self.current()
    if token.type != "END":          # something is left over, e.g. "XII IV"
        raise CompilerError("syntax", f"unexpected '{token.lexeme}' after the expression", token.position, token.lexeme)
    return tree
```
- It parses one Expr, then checks the next token is `END`. If something is left over, such as `XII IV` (two numbers, no operator) or an extra `)`, it is a syntax error.

### 5.5 How the parser handles `XII + IV * II`, call by call
```
parse()
 └ parse_expr()
    ├ parse_term()
    │   └ parse_factor()  -> sees XII, makes leaf XII
    │   (next token is +, not * or /, so the Term ends)
    ├ sees '+', uses it up
    ├ parse_term()
    │   ├ parse_factor()  -> sees IV, makes leaf IV
    │   ├ sees '*', uses it up
    │   ├ parse_factor()  -> sees II, makes leaf II
    │   └ builds node  IV * II
    ├ builds node  XII + (IV * II)
    └ next token is END, so the loop ends
 └ the END check passes
```
This is **recursive descent**: each grammar rule is a function, and the functions call each other down the grammar ("descent"), calling themselves again for brackets ("recursive").

**Phase 2 summary:** tokens in, parse tree out. It catches broken structure (missing operand, missing bracket, missing operator) and gives `*` `/` priority over `+` `-`.

---

## 6. Phase 3, Semantic analysis (`semantic.py`)

**Job:** give every node of the tree a value, and catch errors that depend on meaning.

**Syntax-directed translation (SDT)** means attaching rules to the grammar and evaluating them over the tree. Here every node gets an attribute `val`, computed from its children's `val`. An attribute computed **from the children upwards** is called a **synthesized attribute**; a scheme that only uses these is **S-attributed**.

| Tree node | Rule |
|---|---|
| number | `val = the number's value` |
| `E1 + E2` | `val = E1.val + E2.val` |
| `E1 - E2` | `val = E1.val - E2.val` |
| `E1 * E2` | `val = E1.val * E2.val` |
| `E1 / E2` | `val = E1.val // E2.val`, and **error if E2.val = 0** |

```python
# semantic.py
def calculate(op, a, b):
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    return a // b
```
```python
# semantic.py
def analyze(node):
    if isinstance(node, NumeralNode):            # a number's value is itself
        node.val = node.value
        return node.val

    left = analyze(node.left)                    # first the children (bottom-up)
    right = analyze(node.right)

    if node.op == "/" and right == 0:
        raise CompilerError("semantic", "division by zero", node.position, f"{left} / {right}")

    node.val = calculate(node.op, left, right)   # then this node
    return node.val
```

Line by line:
- `calculate` does one arithmetic operation. `//` is whole-number division (Roman numerals have no fractions).
- In `analyze`, a number's `val` is just its value.
- For an operator node, it first calls `analyze` on the **left child and the right child**. The recursion goes down to the leaves first. Children first, parent last, is **post-order** (bottom-up).
- Then, if the operator is `/` and the right value is 0, it raises a semantic error.
- Finally `node.val = calculate(...)` stores the answer on the node, and `return` hands it to the parent.

**Why division by zero is checked here and not in the parser:** the parser only sees the shape of the expression. For `X / (II - II)` the shape is perfectly valid. Only after working out `II - II = 0` do we know there is a problem. Syntax is about structure; semantics is about meaning.

**Phase 3 summary:** tree in, tree with values out. It catches division by zero.

---

## 7. Phase 4, Code generation (`codegen.py`)

**Job:** translate the tree into **assembly language**, the language closest to the machine.

The target is a simple **stack machine** with two **registers** (`EAX` and `EBX`, tiny storage cells inside the processor). The whole assembly language we use is these lines:

| Assembly line | What it does |
|---|---|
| `PUSH n` | put the number n on top of the stack |
| `POP EBX` / `POP EAX` | take the top of the stack and put it in that register |
| `ADD EAX, EBX` | EAX = EAX + EBX (likewise `SUB`, `MUL`, `DIV`) |
| `PUSH EAX` | put the register's value on the stack |
| `HLT` | stop |

To do `4 * 2` the machine needs: `PUSH 4`, `PUSH 2` (get both numbers on the stack), then `POP EBX` (the right number), `POP EAX` (the left number), `MUL EAX, EBX` (multiply), `PUSH EAX` (keep the result on the stack). Notice the numbers come **before** their operator. That order is called **postfix**, and a post-order walk of the tree produces it directly.

```python
# codegen.py
MNEMONIC = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}
```
```python
# codegen.py
def generate_code(tree):
    return gen(tree) + ["POP EAX", "HLT"]       # the final answer is left in EAX
```
```python
# codegen.py
def gen(node):
    if isinstance(node, NumeralNode):
        return [f"PUSH {node.value}"]

    return (gen(node.left)                      # code for the left side
            + gen(node.right)                   # code for the right side
            + ["POP EBX",                       # right operand
               "POP EAX",                       # left operand
               f"{MNEMONIC[node.op]} EAX, EBX", # EAX = EAX op EBX
               "PUSH EAX"])                     # keep the result on the stack
```

Line by line:
- `MNEMONIC` maps each operator to its assembly name.
- `gen(node)` returns the list of assembly lines for one node:
  - For a **number**: just `["PUSH value"]`.
  - For an **operator**: the lines for the left side, plus the lines for the right side, plus the four lines that do the operation (`POP EBX`, `POP EAX`, the operator line, `PUSH EAX`). Left, right, then operator: that is post-order.
- `generate_code` adds `POP EAX` (the final answer ends up in EAX) and `HLT` at the end.

**Why precedence comes out right:** the tree already has `IV * II` below the `+`, and `gen` writes the children's code before the parent's, so the multiplication code appears before the addition code. No extra logic is needed.

**There is no separate intermediate-code phase.** Assembly is written straight from the tree, because a post-order walk of the tree already gives the order the machine needs.

**About this assembly:** it is a simplified, x86-style teaching assembly. The stack (`PUSH`/`POP`) and the registers `EAX`/`EBX` are the same ideas as real x86, but `MUL EAX, EBX` and `DIV EAX, EBX` are written with two operands to keep it simple (real x86 has `IMUL`, and `IDIV` needs extra setup). The compiler writes the program; it does not assemble or run it.

**Phase 4 summary:** tree in, assembly out.

---

## 8. Phase 5, Code optimization (`optimizer.py`)

**Job:** make the assembly shorter without changing what it computes.

**The optimization is constant folding:** if both numbers of an operation are already known, do the sum now (at compile time) instead of leaving it for the machine. In our assembly, these six lines always mean "compute a op b":

```
PUSH a
PUSH b
POP EBX
POP EAX
<ADD|SUB|MUL|DIV> EAX, EBX
PUSH EAX
```
so they can be replaced by the single line `PUSH (a op b)`.

```python
# optimizer.py
OPERATORS = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/"}
```
```python
# optimizer.py
def is_number_push(line):
    parts = line.split()                          # e.g. ["PUSH", "12"]
    return len(parts) == 2 and parts[0] == "PUSH" and parts[1].lstrip("-").isdigit()
```
```python
# optimizer.py
def can_fold(six):
    return (is_number_push(six[0])                # PUSH a
            and is_number_push(six[1])            # PUSH b
            and six[2] == "POP EBX"
            and six[3] == "POP EAX"
            and six[4].split()[0] in OPERATORS    # ADD / SUB / MUL / DIV
            and six[5] == "PUSH EAX")
```
```python
# optimizer.py
def optimize(asm):
    out = []
    folds = []
    for line in asm:
        out.append(line)
        if len(out) >= 6 and can_fold(out[-6:]):          # do the last 6 lines form a fold?
            six = out[-6:]
            a = int(six[0].split()[1])
            b = int(six[1].split()[1])
            result = calculate(OPERATORS[six[4].split()[0]], a, b)
            folds.append(f"PUSH {a}, PUSH {b}, {six[4].split()[0]}   ->   PUSH {result}")
            del out[-6:]
            out.append(f"PUSH {result}")           # the new PUSH can fold again later
    return out, folds
```

Line by line:
- `is_number_push(line)` is true for lines like `PUSH 12` (also `PUSH -8`) but not `PUSH EAX`, because the second word must be a number.
- `can_fold(six)` checks that six lines have exactly the pattern above: two `PUSH number` lines, `POP EBX`, `POP EAX`, an arithmetic line, and `PUSH EAX`.
- In `optimize`, `out` is the new, shorter program and `folds` records each fold.
- It copies the lines one by one. After each line is added, it asks: do the **last six lines** of `out` form a fold?
- If yes: read `a` and `b` from the two `PUSH` lines, find the operator from the arithmetic line, work out `result` with `calculate` (the same function Phase 3 uses), delete the six lines, and add `PUSH result` in their place.

**Why one pass is enough:** the new `PUSH result` is a number push, so it can combine with the next lines that arrive. For our example:
```
PUSH 12, PUSH 4, PUSH 2, POP EBX, POP EAX, MUL, PUSH EAX      ... the last six fold: 4 * 2
   becomes   PUSH 12, PUSH 8                                  (so far)
then POP EBX, POP EAX, ADD, PUSH EAX are added                ... the last six fold: 12 + 8
   becomes   PUSH 20
```

**Why this is safe:** a fold only replaces lines that were certain to compute `a op b` with a `PUSH` of that same number. The program's meaning does not change. The tests also check that, for many expressions, the optimized assembly is exactly `PUSH <the value Phase 3 computed>`.

**Honest note:** every number in this language is written in the program, so every expression folds all the way down to a single `PUSH`. It is still a real optimization: `XII + IV * II` goes from 13 lines to 3.

**Phase 5 summary:** assembly in, shorter assembly out, with a list of the folds.

---

## 9. `main.py` (the terminal driver), the AI explainer, the backup UI

### 9.1 `main.py`
```python
# main.py
def compile_source(source):
    stages = []
    asm = None
    try:
        tokens = tokenize(source)
        stages.append(("PHASE 1: LEXICAL ANALYSIS",
                       "Splits the text into tokens and checks every Roman numeral.",
                       [t.show() for t in tokens]))

        tree = Parser(tokens).parse()
        stages.append(("PHASE 2: SYNTAX ANALYSIS",
                       "Checks the grammar and builds the parse tree.",
                       tree_lines(tree)))

        analyze(tree)
        stages.append(("PHASE 3: SEMANTIC ANALYSIS",
                       "Works out the value of every node, from the bottom up.",
                       tree_lines(tree, show_val=True)))

        asm = generate_code(tree)
        stages.append(("PHASE 4: CODE GENERATION",
                       "Walks the tree and writes assembly language.",
                       asm))

        before = len(asm)
        asm, folds = optimize(asm)
        stages.append(("PHASE 5: CODE OPTIMIZATION",
                       "Constant folding: does the sums at compile time.",
                       folds + [f"{before} lines of assembly  ->  {len(asm)} lines"]))

        stages.append(("FINAL OUTPUT: ASSEMBLY PROGRAM",
                       "Result is left in register EAX.",
                       asm))

    except CompilerError as e:
        where = f" (position {e.position})" if e.position is not None else ""
        stages.append((e.phase.upper() + " ERROR", "", [e.message + where]))
        text, who = explain_error(e, source)
        stages.append((f"AI EXPLANATION ({who})", "", [text]))
        asm = None
    return stages, asm
```

- `compile_source` runs the phases **in order**. After each phase succeeds, it adds a **stage** to the `stages` list: (title, what the phase does, output lines).
- Everything is inside one `try`. If any phase raises a `CompilerError`, control jumps to `except`, which adds the error and the AI explanation as stages. The remaining phases are skipped, which is why an error stops the pipeline at the failing phase.
- It returns the stages and the final assembly (`None` if there was an error).

```python
# main.py
def stage_text(stage):
    title, what, lines = stage
    text = "=" * 62 + "\n" + title + "\n"
    if what:
        text += what + "\n"
    text += "=" * 62 + "\n"
    return text + "".join("  " + line + "\n" for line in lines)
```
```python
# main.py
def run(source, step=False):
    stages, asm = compile_source(source)
    for stage in stages:
        print(stage_text(stage))
        if step:
            input("  Press Enter for the next stage...\n")
    if asm:
        with open("output.asm", "w") as f:
            f.write("\n".join(asm) + "\n")
        print("Assembly saved to output.asm\n")
```

- `stage_text` formats one stage as text (title, what it does, output lines).
- `run` prints every stage in the terminal. With `--step` it waits for Enter after each stage, so you can explain one phase at a time. On success it also saves the assembly to `output.asm`.

How to run it in the VS Code terminal:
```
cd src
python main.py "XII + IV * II"          one expression
python main.py --step "XII + IV * II"   pause after every stage
python main.py                          type expressions one after another
```

### 9.2 The AI error explainer (`ai_advisor.py`)
```python
# ai_advisor.py
def explain_error(error, source):
    text = ask_ai(error, source)
    if text:
        return text, "AI"
    return offline_explanation(error), "built-in rules"
```

- It takes the error and the original input, and first tries `ask_ai`, which asks an AI model to explain the mistake in plain English and suggest a fix. That only works if an API key is set.
- If there is no key or no internet, it uses `offline_explanation`, a set of fixed rules (for example, for `IIII` it says the correct form is `IV`).
- The result says who wrote the explanation, `AI` or `built-in rules`, and `main.py` shows that in the stage title.

**Important point for sir:** none of the five phases imports `ai_advisor.py` (a test checks this). The compiler works completely without it. The AI only explains an error **after** the compiler has found it; it never decides whether a program is valid.

### 9.3 The backup UI (`ui.py`)
A tiny web page: a text box, a Compile button, and a box that shows the same text the terminal shows. It calls the same `compile_source`, so there is no second implementation. Start it with `python ui.py` and open `http://localhost:8000`. It is only a backup; the terminal is the main way to run the compiler.

---

## 10. How to present it to sir

1. **Run it in the terminal first** so he sees the whole flow:
   `cd src` then `python main.py --step "XII + IV * II"` (press Enter after each stage).
2. `main.py`, `compile_source`: "these are the five phases in order, and each one's output feeds the next."
3. `lexer.py`: `validate_roman` (the round trip), then `tokenize`.
4. `parser.py`: the grammar, then `parse_expr`, `parse_term`, `parse_factor`.
5. `semantic.py`: `analyze` (bottom-up, division by zero).
6. `codegen.py`: `gen` (post-order, the assembly lines).
7. `optimizer.py`: `optimize` (constant folding).
8. Show the three error kinds: `IIII + I`, `XII +`, `X / (II - II)`.
9. Mention `output.asm` (the compiler's output file), and `python -m pytest tests -q` for the tests.
10. Only if asked: `python ui.py` and open the web page.

---

## 11. Questions sir may ask, with answers

**Q1. What is the difference between a token and a lexeme?**
A lexeme is the actual text (`XII`). A token is that text classified, with extra information: type `NUM`, value 12, position 0.

**Q2. How do you check that a Roman numeral is valid?**
`validate_roman` converts the numeral to a number and then writes that number back in standard form (`int_to_roman`). If the two texts are not identical, it is badly formed. `IIII` becomes 4, which is written `IV`, so it is rejected. It also rejects values above 3999.

**Q3. Why not use a regular expression?**
A regex for valid Roman numerals is possible but long and hard to read. The round trip is a short check built from two functions we need anyway, and it is easy to test (all 3999 values are tested).

**Q4. What technique is your parser?**
Recursive descent, top-down. Each grammar rule is one function (`parse_expr`, `parse_term`, `parse_factor`).

**Q5. How does your parser handle operator precedence?**
In the grammar. Expr is built from Terms and Term from Factors, so `*` and `/` are grouped inside a Term before Expr sees `+` or `-`. No precedence table is needed.

**Q6. How do you handle associativity?**
The `while` loops build the tree to the left, so `X - V - II` becomes `((X - V) - II)`.

**Q7. Why is your grammar written with `( ... )*` instead of `Expr -> Expr + Term`?**
That rule is left-recursive, and a recursive-descent parser would call itself forever. The repetition form becomes a loop and also gives left associativity.

**Q8. What is syntax-directed translation? What kind of attributes do you use?**
Rules attached to the grammar and evaluated over the tree. We use one synthesized attribute, `val`, computed from the children, so it is S-attributed. It is evaluated bottom-up (post-order).

**Q9. Why is division by zero a semantic error and not a syntax error?**
The expression `X / (II - II)` is grammatically correct. We only learn the divisor is 0 after evaluating it, which is a matter of meaning, not structure.

**Q10. What is post-order traversal and where do you use it?**
Visit the left child, then the right child, then the node itself. It is used twice: in semantic analysis (a node's value needs its children's values first) and in code generation (both numbers must be pushed before the operator's lines).

**Q11. What is the output of your compiler, and why assembly?**
The final output is an assembly language program. Assembly is the last step before machine code, and it is what a real compiler's code generator produces. Ours is a simplified x86-style assembly using a stack (`PUSH`/`POP`) and two registers (`EAX`, `EBX`).

**Q12. Why is there no intermediate code generation phase?**
It is optional. For a stack-based target, the parse tree already works as the intermediate form, since a post-order walk of it gives the instruction order. An intermediate form such as three-address code would be an extra step between the tree and the assembly.

**Q13. What optimization do you do, and why is it correct?**
Constant folding: six lines of assembly that compute `a op b` from two known numbers are replaced by `PUSH (a op b)`. It is correct because those six lines always produce exactly that value. The tests check that the optimized program is `PUSH` of the value that semantic analysis computed.

**Q14. What other optimizations could you add?**
Algebraic simplification (`x * 1`, `x + 0`), turning `PUSH n` followed by `POP EAX` into `MOV EAX, n`, strength reduction, common sub-expression elimination, dead code elimination. Most of those matter when programs have variables; here every operand is a constant, so folding covers everything.

**Q15. Does your assembly run on a real machine?**
Not as it is. It is a simplified teaching assembly in the style of x86. The stack and the registers work the same way, but `MUL EAX, EBX` and `DIV EAX, EBX` are simplified (real x86 uses `IMUL` and `IDIV` with extra setup), and we do not model the 32-bit size of registers. The compiler's job ends at writing the assembly; an assembler would be the next tool.

**Q16. How do you know the generated assembly is correct?**
Two ways. By hand: `PUSH`/`POP` follow the stack, and the 13-line program for `XII + IV * II` can be traced to 20. In the tests: for many expressions, the optimized assembly must equal `PUSH` of the value computed by Phase 3, which is computed separately from the tree.

**Q17. Where is AI used?**
Only to explain errors in plain English. It sits outside the compiler (none of the five phases imports it), and if it is unavailable, built-in rules take over. All five phases are written by hand.

**Q18. What happens when there is an error?**
The phase raises a `CompilerError` with the phase, message and position. `main.py` stops the pipeline there, shows the error and the explanation. We stop at the first error and do no error recovery.

**Q19. What is the time complexity?**
Each phase makes one pass over its input, so it is roughly linear in the length of the input.

**Q20. What are the limitations?**
Whole-number arithmetic only (division is integer division), numerals 1 to 3999 only, no unary minus, no variables, and a simplified assembly that is not run or assembled.

**Q21. How would you add a new operator, say `%` (modulo)?**
Five small edits, one per file:
1. `lexer.py`: add `%` to the one-character symbols in `tokenize` (`"+-*/%()"`).
2. `parser.py`: in `parse_term`, also loop on `"%"`.
3. `semantic.py`: in `calculate`, handle `%` (and check for zero like `/`).
4. `codegen.py`: add `"%": "MOD"` to `MNEMONIC`.
5. `optimizer.py`: add `"MOD": "%"` to `OPERATORS`.

---

## 12. One-page cheat sheet

| # | Phase | File and key function | Input | Output | Technique | Errors it catches |
|---|---|---|---|---|---|---|
| 1 | Lexical | `lexer.py`, `tokenize`, `validate_roman` | text | tokens | character scan, round-trip check | bad character, bad numeral (`IIII`, `VX`) |
| 2 | Syntax | `parser.py`, `Parser.parse_*` | tokens | parse tree | recursive descent | missing operand, bracket or operator |
| 3 | Semantic | `semantic.py`, `analyze` | tree | tree with `val` | S-attributed SDT, post-order | division by zero |
| 4 | Code generation | `codegen.py`, `gen` | tree | assembly | post-order walk | none |
| 5 | Optimization | `optimizer.py`, `optimize` | assembly | shorter assembly | constant folding | none |

**Three sentences to remember:**
1. *Each phase takes the output of the previous one, and any phase can stop the pipeline with an error.*
2. *Precedence comes from the grammar, the tree carries it, and post-order walks (for values and for code) respect it.*
3. *The AI only explains errors; every compiler phase is hand-written.*

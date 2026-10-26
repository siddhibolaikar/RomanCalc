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
9. `main.py` (the terminal driver), the AI helpers (explainer and verified fix), the backup UI
10. How to present it to sir
11. Questions sir may ask, with answers
12. One-page cheat sheet

---

## 1. The big picture

A compiler turns text a human writes into a program a machine can follow, in small steps (phases).
Each phase takes the output of the previous one. **RomanCalc takes a Roman numeral expression and produces 8085 assembly language.**

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
      |  Phase 4  CODE GENERATION      writes 8085 assembly language             codegen.py
      v
 8085 assembly (31 lines for the example)
      |  Phase 5  CODE OPTIMIZATION    does the constant sums at compile time    optimizer.py
      v
 shorter 8085 assembly (3 lines)  =  THE FINAL OUTPUT  (printed, and saved to output.asm)
```

In one line each:
- **Lexical analysis** is like reading words: it splits the text into tokens and checks each Roman numeral is spelled correctly.
- **Syntax analysis** is like checking the grammar of a sentence: is `XII +` a complete expression? It also decides what is grouped with what, which is precedence.
- **Semantic analysis** is about meaning: it works out values and catches things like division by zero.
- **Code generation** writes 8085 assembly language, the instructions a microprocessor follows.
- **Code optimization** makes those instructions shorter without changing the answer.

There is no virtual machine: the compiler's job ends with the assembly program.

**Files**

| File | What it contains |
|---|---|
| `errors.py` | The one error type every phase uses |
| `lexer.py` | Phase 1, plus the Roman numeral conversion helpers |
| `parser.py` | Phase 2, plus the tree node classes |
| `semantic.py` | Phase 3 |
| `codegen.py` | Phase 4 (8085 assembly) |
| `optimizer.py` | Phase 5 |
| `main.py` | Runs the phases in order and prints each one's output in the terminal |
| `ai_advisor.py` | The AI helpers: error explainer and fix suggester (not part of the compiler) |
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

**Phase 4, Code generation, output = 8085 assembly (31 lines, including the two subroutines it calls)**
```
LXI SP, 0FFFFH
LXI H, 000CH
PUSH H
LXI H, 0004H
PUSH H
LXI H, 0002H
PUSH H
POP D
POP H
CALL MUL16
PUSH H
POP D
POP H
CALL ADD16
PUSH H
POP H
HLT
ADD16:
DAD D          ; HL = HL + DE
RET
MUL16:
MOV B, H       ; BC = the left number
MOV C, L
LXI H, 0000H   ; HL = 0, the running total
MULLP:
MOV A, D       ; DE counts how many times to add
ORA E          ; DE = 0 ?
RZ             ; yes: finished
DAD B          ; HL = HL + BC
DCX D          ; DE = DE - 1
JMP MULLP
```

**Phase 5, Code optimization, output = the folds and clean-ups it did, then 3 lines left**
```
4 * 2 = 8   ->   LXI H, 0008H
12 + 8 = 20   ->   LXI H, 0014H
PUSH H followed by POP H does nothing: removed
subroutine ADD16 is never called: removed
subroutine MUL16 is never called: removed
31 lines of assembly  ->  3 lines
```

**Final output = the 8085 assembly program** (the answer is left in register pair HL: `0014H` is 20 in hexadecimal)
```
LXI SP, 0FFFFH
LXI H, 0014H
HLT
```

What the three kinds of error look like:
```
lexical error: 'IIII' is not a correctly written Roman numeral (position 0)
syntax error: expected a number or '(' but found 'end of input' (position 5)
semantic error: division by zero (position 2)
```
Each phase can only fail on its own kind of problem: bad numeral spelling in Phase 1, a broken sentence in Phase 2, bad meaning (division by zero) in Phase 3. After an error, the pipeline stops. The AI then explains in plain English what went wrong and proposes a corrected input, which the compiler checks by recompiling it.

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
| any node | **error if val is not between 0 and 65535** (it must fit in 16 bits) |

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

    if not 0 <= node.val <= 65535:               # the 8085 register pair HL holds 0 to 65535
        raise CompilerError("semantic", f"result {node.val} does not fit in 16 bits (0 to 65535)", node.position, str(node.val))
    return node.val
```

Line by line:
- `calculate` does one arithmetic operation. `//` is whole-number division (Roman numerals have no fractions).
- In `analyze`, a number's `val` is just its value.
- For an operator node, it first calls `analyze` on the **left child and the right child**. The recursion goes down to the leaves first. Children first, parent last, is **post-order** (bottom-up).
- Then, if the operator is `/` and the right value is 0, it raises a semantic error.
- `node.val = calculate(...)` stores the answer on the node.
- Then it checks the value is between 0 and 65535. The 8085 program keeps every number in a 16-bit register pair, so a number outside that range could not be stored. A negative result such as `II - X`, or a huge one such as `MMMCMXCIX * MMMCMXCIX`, is a semantic error.
- Finally `return` hands the value to the parent.

**Why division by zero is checked here and not in the parser:** the parser only sees the shape of the expression. For `X / (II - II)` the shape is perfectly valid. Only after working out `II - II = 0` do we know there is a problem. Syntax is about structure; semantics is about meaning.

**Phase 3 summary:** tree in, tree with values out. It catches division by zero and numbers that do not fit in 16 bits.

---

## 7. Phase 4, Code generation (`codegen.py`), the 8085 assembly

**Job:** translate the tree into **8085 assembly language**.

### 7.1 A very short 8085 primer
- The 8085 is an 8-bit microprocessor. It has 8-bit registers `A, B, C, D, E, H, L`.
- Two registers can be used together as a 16-bit **register pair**: `B` means the pair BC, `D` means DE, and `H` means HL. We keep every number in a register pair, so it can be 0 to 65535 (all Roman numerals up to 3999 fit).
- It has a **stack** in memory, used with `PUSH` and `POP`, and a stack pointer `SP`.
- It can **add and subtract** but has **no multiply or divide instruction**. So we write those as small subroutines (section 7.3).
- Numbers in 8085 programs are written in **hexadecimal** with an `H` at the end: `000CH` is 12, `0014H` is 20. A hexadecimal number that starts with a letter gets a `0` in front (`0FFF8H`).

The lines our compiler writes:

| Assembly line | What it does |
|---|---|
| `LXI SP, 0FFFFH` | set the stack pointer to the top of memory (first line of every program) |
| `LXI H, 000CH` | load the pair HL with the number 12 |
| `PUSH H` | put HL on the stack |
| `POP D` / `POP H` | take the top of the stack into DE / into HL |
| `CALL ADD16` | call the subroutine that does HL = HL + DE (likewise `SUB16`, `MUL16`, `DIV16`) |
| `HLT` | stop. The answer is in HL |

To work out `4 * 2` the program does:
```
LXI H, 0004H     HL = 4
PUSH H           put 4 on the stack
LXI H, 0002H     HL = 2
PUSH H           put 2 on the stack
POP D            DE = 2  (the right number)
POP H            HL = 4  (the left number)
CALL MUL16       HL = HL * DE = 8
PUSH H           put the result on the stack
```
Notice both numbers are pushed **before** their operator. That order is called **postfix**, and a post-order walk of the tree produces it directly.

### 7.2 The code generator
```python
# codegen.py
ROUTINE = {"+": "ADD16", "-": "SUB16", "*": "MUL16", "/": "DIV16"}
```
```python
# codegen.py
def hex16(n):
    text = f"{n:04X}H"
    return "0" + text if text[0] in "ABCDEF" else text
```
```python
# codegen.py
def generate_code(tree):
    program = ["LXI SP, 0FFFFH"]                  # the stack starts at the top of memory
    program += gen(tree)
    program += ["POP H", "HLT"]                   # the final answer is left in HL
    for name, routine in LIBRARY.items():         # add the subroutines the program calls
        if "CALL " + name in program:
            program += routine
    return program
```
```python
# codegen.py
def gen(node):
    if isinstance(node, NumeralNode):
        return ["LXI H, " + hex16(node.value), "PUSH H"]

    return (gen(node.left)                        # code for the left side
            + gen(node.right)                     # code for the right side
            + ["POP D",                           # right number into DE
               "POP H",                           # left number into HL
               "CALL " + ROUTINE[node.op],        # HL = HL op DE
               "PUSH H"])                         # keep the result on the stack
```

Line by line:
- `ROUTINE` maps each operator to the name of its subroutine.
- `hex16(n)` writes a number the way an 8085 program does: `f"{n:04X}H"` gives four hexadecimal digits and an `H`, and a `0` is put in front if the first character is a letter.
- `gen(node)` returns the assembly lines for one node:
  - For a **number**: `LXI H, <number>` and `PUSH H`.
  - For an **operator**: the lines for the left side, plus the lines for the right side, plus four lines that do the operation (`POP D`, `POP H`, `CALL <subroutine>`, `PUSH H`). Left, right, then operator: that is post-order.
- `generate_code` starts with `LXI SP, 0FFFFH`, adds the lines from `gen`, then `POP H` (the final answer goes into HL) and `HLT`. At the end it appends the subroutines the program actually calls.

**Why precedence comes out right:** the tree already has `IV * II` below the `+`, and `gen` writes the children's code before the parent's, so the multiplication code appears before the addition code. No extra logic is needed.

**There is no separate intermediate-code phase.** Assembly is written straight from the tree, because a post-order walk of the tree already gives the order the machine needs.

### 7.3 The subroutines: how the 8085 adds, subtracts, multiplies and divides

Each subroutine takes the left number in **HL** and the right number in **DE** and leaves the answer in **HL**.

```python
# codegen.py
LIBRARY = {
    "ADD16": [
        "ADD16:",
        "DAD D          ; HL = HL + DE",
        "RET",
    ],
    "SUB16": [
        "SUB16:",
        "MOV A, L       ; low bytes:  L - E",
        "SUB E",
        "MOV L, A",
        "MOV A, H       ; high bytes: H - D - borrow",
        "SBB D",
        "MOV H, A",
        "RET",
    ],
    "MUL16": [
        "MUL16:",
        "MOV B, H       ; BC = the left number",
        "MOV C, L",
        "LXI H, 0000H   ; HL = 0, the running total",
        "MULLP:",
        "MOV A, D       ; DE counts how many times to add",
        "ORA E          ; DE = 0 ?",
        "RZ             ; yes: finished",
        "DAD B          ; HL = HL + BC",
        "DCX D          ; DE = DE - 1",
        "JMP MULLP",
    ],
    "DIV16": [
        "DIV16:",
        "LXI B, 0000H   ; BC = quotient, starts at 0",
        "DIVLP:",
        "MOV A, L       ; is HL - DE negative?",
        "SUB E",
        "MOV A, H",
        "SBB D",
        "JC DIVEND      ; yes: finished",
        "MOV A, L       ; no: HL = HL - DE",
        "SUB E",
        "MOV L, A",
        "MOV A, H",
        "SBB D",
        "MOV H, A",
        "INX B          ; quotient = quotient + 1",
        "JMP DIVLP",
        "DIVEND:",
        "MOV H, B       ; HL = quotient",
        "MOV L, C",
        "RET",
    ],
}
```

- **`ADD16`**: `DAD D` is an 8085 instruction that adds the pair DE to HL. One line.
- **`SUB16`**: the 8085 subtracts one byte at a time. First the low bytes (`SUB E`), then the high bytes **with the borrow** (`SBB D`). `MOV` moves a value between registers.
- **`MUL16`** (repeated addition): copy the left number into BC, set HL to 0, then add BC to HL `DE` times. At the top of the loop, `MOV A, D` and `ORA E` put D OR E in the accumulator, which is zero only if DE is zero. `RZ` returns when it is zero (finished). Otherwise `DAD B` adds BC to HL, `DCX D` counts DE down, and `JMP MULLP` repeats. For `4 * 2`: HL = 4, then 8, then DE reaches 0 and the routine returns with HL = 8.
- **`DIV16`** (repeated subtraction): BC counts the quotient. Each time, check whether HL - DE would go below zero (`SUB E` then `SBB D` set the carry flag when HL is smaller than DE). If so, `JC DIVEND` jumps out. If not, subtract DE from HL for real and add 1 to the count (`INX B`). At the end, the count in BC is moved into HL. For `10 / 5`: 10 becomes 5, then 0, with the count reaching 2.

Only the subroutines that the program calls are added at the end of the program.

### 7.4 How do we know it is correct?
The tests contain a tiny 8085 simulator (`tests/sim8085.py`). For many expressions, including large numbers, the test runs the **whole generated 8085 program** (subroutines included) on it and checks that HL ends up equal to the value Phase 3 computed. This simulator is only for testing; it is not part of the compiler. Before the exam it is also worth pasting `output.asm` into your lab's 8085 simulator.

### 7.5 Limits
- All numbers and results must be between 0 and 65535 (checked in Phase 3).
- Division is whole-number division, and the numbers are never negative.

**Phase 4 summary:** tree in, 8085 assembly out.

---

## 8. Phase 5, Code optimization (`optimizer.py`)

**Job:** make the assembly shorter without changing what it computes.

There are three small rules:

1. **Constant folding (the main one).** If both numbers of an operation are already known, do the sum now (at compile time) instead of leaving it for the processor. These eight lines always mean "compute a op b":
```
LXI H, a
PUSH H
LXI H, b
PUSH H
POP D
POP H
CALL <ADD16|SUB16|MUL16|DIV16>
PUSH H
```
so they are replaced by two lines: `LXI H, <a op b>` and `PUSH H`.
2. **`PUSH H` straight followed by `POP H` does nothing**, so both lines are removed.
3. **A subroutine that is never called any more is removed.**

```python
# optimizer.py
OPERATORS = {"CALL ADD16": "+", "CALL SUB16": "-", "CALL MUL16": "*", "CALL DIV16": "/"}
```
```python
# optimizer.py
def is_load(line):
    return line.startswith("LXI H, ")
```
```python
# optimizer.py
def number_in(line):
    return int(line[7:-1], 16)                    # "LXI H, 000CH" -> 12
```
```python
# optimizer.py
def can_fold(eight):
    return (is_load(eight[0]) and eight[1] == "PUSH H"
            and is_load(eight[2]) and eight[3] == "PUSH H"
            and eight[4] == "POP D" and eight[5] == "POP H"
            and eight[6] in OPERATORS
            and eight[7] == "PUSH H")
```
```python
# optimizer.py
def optimize(asm):
    out = []
    notes = []
    for line in asm:
        out.append(line)

        if len(out) >= 8 and can_fold(out[-8:]):              # rule 1: constant folding
            a = number_in(out[-8])
            b = number_in(out[-6])
            op = OPERATORS[out[-2]]
            result = calculate(op, a, b)
            notes.append(f"{a} {op} {b} = {result}   ->   LXI H, {hex16(result)}")
            del out[-8:]
            out += ["LXI H, " + hex16(result), "PUSH H"]      # the new number can fold again later

        if out[-2:] == ["PUSH H", "POP H"]:                   # rule 2: this pair does nothing
            notes.append("PUSH H followed by POP H does nothing: removed")
            del out[-2:]

    for name, routine in LIBRARY.items():                     # rule 3: remove unused subroutines
        if routine[0] in out and "CALL " + name not in out:
            start = out.index(routine[0])
            del out[start:start + len(routine)]
            notes.append(f"subroutine {name} is never called: removed")
    return out, notes
```

Line by line:
- `is_load(line)` is true for lines that start with `LXI H, `. (`LXI SP, ...` does not match.)
- `number_in(line)` reads the number back out of such a line: `LXI H, 000CH` gives 12 (the text between the first 7 characters and the final `H` is read as hexadecimal).
- `can_fold(eight)` checks that eight lines have exactly the pattern in rule 1.
- In `optimize`, `out` is the new, shorter program and `notes` records what was done.
- It copies the lines one by one. After each line is added, it asks: do the **last eight lines** of `out` form a fold? If yes: read `a` and `b`, find the operator from the `CALL` line, work out `result` with `calculate` (the same function Phase 3 uses), delete the eight lines, and add `LXI H, <result>` and `PUSH H` in their place.
- Then, if the last two lines are `PUSH H`, `POP H`, both are removed (rule 2).
- At the end, for each subroutine in `LIBRARY`: if its label is in the program but no `CALL` to it remains, the subroutine's lines are deleted (rule 3).

**Why one pass is enough:** the new `LXI H, result` / `PUSH H` can combine with the lines that arrive next. For our example:
```
... LXI H, 4 / PUSH H / LXI H, 2 / PUSH H / POP D / POP H / CALL MUL16 / PUSH H     <- the last eight lines fold: 4 * 2 = 8
    becomes   LXI H, 8 / PUSH H          (and the 12 that was pushed before it is still on the stack)
then POP D / POP H / CALL ADD16 / PUSH H arrive                                      <- the last eight lines fold: 12 + 8 = 20
    becomes   LXI H, 20 / PUSH H
then POP H arrives: PUSH H followed by POP H is removed
the subroutines ADD16 and MUL16 are no longer called, so they are removed
```
Result: `LXI SP, 0FFFFH`, `LXI H, 0014H`, `HLT`.

**Why this is safe:** each rule only removes lines whose effect is already known: the folded lines computed exactly `a op b`, a `PUSH H` / `POP H` pair leaves everything as it was, and an uncalled subroutine is never run. The tests check this: for many expressions the optimized program is exactly `LXI H, <the value Phase 3 computed>`, and both the unoptimized and the optimized programs give that value on the 8085 simulator.

**Honest note:** every number in this language is written in the program, so every expression folds all the way down to one `LXI H`. It is still a real optimization: `XII + IV * II` goes from 31 lines to 3.

**Phase 5 summary:** 8085 assembly in, shorter 8085 assembly out, with a list of what was done.

---

## 9. `main.py` (the terminal driver), the AI helpers (explainer and verified fix), the backup UI

### 9.1 `main.py`
```python
# main.py
def run_phases(source):
    stages = []
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
                       "Walks the tree and writes 8085 assembly language.",
                       asm))

        before = len(asm)
        asm, notes = optimize(asm)
        stages.append(("PHASE 5: CODE OPTIMIZATION",
                       "Constant folding (sums done at compile time) and removal of code that is no longer needed.",
                       notes + [f"{before} lines of assembly  ->  {len(asm)} lines"]))

        stages.append(("FINAL OUTPUT: 8085 ASSEMBLY PROGRAM",
                       "The result is left in register pair HL.",
                       asm))
        return stages, asm, None

    except CompilerError as e:
        return stages, None, e
```

- `run_phases` runs the five phases **in order**. After each phase succeeds, it adds a **stage** to the `stages` list: (title, what the phase does, output lines).
- Everything is inside one `try`. If any phase raises a `CompilerError`, control jumps to `except`, and `run_phases` returns the stages so far, no assembly, and the error. The remaining phases are skipped, which is why an error stops the pipeline at the failing phase.
- On success it returns the stages, the final assembly, and `None` for the error.

```python
# main.py
def compile_source(source):
    stages, asm, error = run_phases(source)
    if error:
        where = f" (position {error.position})" if error.position is not None else ""
        stages.append((error.phase.upper() + " ERROR", "", [error.message + where]))
        text, who = explain_error(error, source)
        stages.append((f"AI EXPLANATION ({who})", "", [text]))
        stages += fix_stages(source, error)
    return stages, asm
```

- `compile_source` calls `run_phases`. If there was an error, it adds three more stages: the error, the AI explanation, and the suggested fix (section 9.2). It returns the stages and the assembly (`None` when the input had an error).

```python
# main.py
def stage_text(stage):
    title, what, lines = stage
    text = "=" * 62 + "\n" + title + "\n"
    if what:
        text += what + "\n"
    text += "=" * 62 + "\n"
    for line in lines:
        pad = "  " if line.endswith(":") else "    "     # labels stand out from instructions
        text += pad + line + "\n"
    return text
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

### 9.2 The AI helpers (`ai_advisor.py`)

When a phase finds an error, the AI does two things, and **both happen after the compiler has already found the error**.

**Part 1: the error explainer**
```python
# ai_advisor.py
def explain_error(error, source):
    text = ask_ai(error, source)
    if text:
        return text, "AI"
    return offline_explanation(error), "built-in rules"
```

- It takes the error and the original input, and first tries `ask_ai`, which asks an AI model to explain the mistake in plain English. That only works if an API key is set.
- If there is no key or no internet, it uses `offline_explanation`, a set of fixed rules (for example, for `IIII` it says the correct form is `IV`).
- The result says who wrote the explanation, `AI` or `built-in rules`, and `main.py` shows that in the stage title.

**Part 2: a suggested fix, verified by the compiler (AI proposes, compiler decides)**

The AI proposes a corrected input. We do **not** trust it: the compiler recompiles the corrected input, and the fix is accepted only if all five phases pass.

```python
# main.py
def fix_stages(source, error):
    rejected = []
    for candidate, who in suggest_fixes(error, source):
        _, fixed_asm, fixed_error = run_phases(candidate)
        if fixed_error is None:                                  # the compiler accepted it
            return [(f"SUGGESTED FIX ({who})",
                     "The compiler checked this input by running all five phases on it.",
                     rejected + [f"{source}   ->   {candidate}"]),
                    ("VERIFIED: ALL 5 PHASES PASSED",
                     "8085 program for the corrected input. The result is left in register pair HL.",
                     fixed_asm)]
        rejected.append(f"{who} suggested '{candidate}', but the compiler rejected it: {fixed_error.message}")
    return [("NO VERIFIED FIX", "",
             rejected + ["No corrected input that passes all five phases was found."])]
```
```python
# ai_advisor.py
def suggest_fixes(error, source):
    tries = [(ask_ai_for_fix(error, source), "AI"),
             (rule_fix(error, source), "built-in rules")]
    fixes = []
    for candidate, who in tries:
        if candidate and candidate != source and candidate not in [c for c, _ in fixes]:
            fixes.append((candidate, who))
    return fixes
```
```python
# ai_advisor.py
def rule_fix(error, source):
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
```

- `suggest_fixes` returns candidate corrected inputs, best first: the AI's answer (`ask_ai_for_fix`, only if an API key is set), then the built-in rule. Candidates that are the same as the input, or repeated, are dropped.
- `fix_stages` tries each candidate by calling `run_phases(candidate)`, the same five phases that handled the original input.
- If no phase raises an error (`fixed_error is None`), the compiler has accepted it, and the stages show the fix and the 8085 program for the corrected input.
- If a phase rejects the candidate, the reason is recorded (`... but the compiler rejected it: ...`) and the next candidate is tried. If none passes, the output says `NO VERIFIED FIX`.
- `rule_fix` is the fix that needs no AI. It handles only three clear mistakes: a badly written numeral is rewritten in standard form (`IIII` is read as 4, and `int_to_roman(4)` writes `IV`), a missing `)` is added, and an extra `)` is removed. For anything unclear, such as `XII +`, it gives no fix.

What it looks like for `IIII + I`:
```
SUGGESTED FIX (built-in rules)
    IIII + I   ->   IV + I
VERIFIED: ALL 5 PHASES PASSED
    LXI SP, 0FFFFH
    LXI H, 0005H
    HLT
```

**Two important points for sir**
- None of the five phases imports `ai_advisor.py` (a test checks this). The compiler works completely without it, and the AI never decides whether a program is valid: the compiler does, by recompiling.
- The compiler checks that the fixed input is a **valid program**, not that it is what the user **meant**. For example `VX - II` is fixed to `V - II`, which compiles, but the user may have meant `XV - II`.

### 9.3 The backup UI (`ui.py`)
A tiny web page: a text box, a Compile button, and a box that shows the same text the terminal shows. It calls the same `compile_source`, so there is no second implementation. Start it with `python ui.py` and open `http://localhost:8000`. It is only a backup; the terminal is the main way to run the compiler.

---

## 10. How to present it to sir

1. **Run it in the terminal first** so he sees the whole flow:
   `cd src` then `python main.py --step "XII + IV * II"` (press Enter after each stage).
2. `main.py`, `compile_source`: "these are the five phases in order, and each one's output feeds the next."
3. `lexer.py`: `validate_roman` (the round trip), then `tokenize`.
4. `parser.py`: the grammar, then `parse_expr`, `parse_term`, `parse_factor`.
5. `semantic.py`: `analyze` (bottom-up, division by zero, 16-bit check).
6. `codegen.py`: `gen` (post-order), then the `LIBRARY` subroutines (this is the 8085 part).
7. `optimizer.py`: `optimize` (constant folding).
8. Show the error kinds: `IIII + I` (note the suggested fix that the compiler verifies), `XII +`, `X / (II - II)`, `II - X`.
9. Mention `output.asm` (the compiler's output file), and `python -m pytest tests -q` for the tests.
10. If he asks, paste `output.asm` (or the Phase 4 listing) into an 8085 simulator. Try this yourself once beforehand.
11. Only if asked: `python ui.py` and open the web page.

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

**Q11. What is the output of your compiler, and why 8085?**
The final output is an 8085 assembly language program (saved as `output.asm`). Assembly is the last step before machine code, and it is what a real compiler's code generator produces. The 8085 is a small, classic microprocessor, so its instructions are easy to explain: registers, a stack, `LXI`, `PUSH`, `POP`, `CALL`, `HLT`.

**Q12. Why is there no intermediate code generation phase?**
It is optional. For a stack-based target, the parse tree already works as the intermediate form, since a post-order walk of it gives the instruction order. An intermediate form such as three-address code would be an extra step between the tree and the assembly.

**Q13. What optimization do you do, and why is it correct?**
Constant folding: eight lines of assembly that compute `a op b` from two known numbers are replaced by `LXI H, <a op b>` and `PUSH H`. It is correct because those eight lines always produce exactly that value. Two clean-ups follow: `PUSH H` then `POP H` is removed, and subroutines that are no longer called are removed. The tests check the optimized program equals `LXI H, <the value from Phase 3>`.

**Q14. What other optimizations could you add?**
Algebraic simplification (`x * 1`, `x + 0`), strength reduction (for example multiplying by 2 with `DAD H`, which adds HL to itself), common sub-expression elimination, dead code elimination. Most matter when programs have variables; here every operand is a constant, so folding covers everything.

**Q15. Does your assembly really run?**
The compiler only writes it. It uses standard 8085 instructions (`LXI`, `PUSH`, `POP`, `CALL`, `RET`, `DAD`, `MOV`, `SUB`, `SBB`, `ORA`, `RZ`, `JC`, `JMP`, `INX`, `DCX`, `HLT`). The tests run the generated programs on a small 8085 simulator written for testing, and the results match. A real 8085 simulator would be the final check, so try the output in your lab's simulator.

**Q16. How do you know the generated assembly is correct?**
By hand: the stack works as push, push, pop, pop, operate, push, and the example traces to 20 (`0014H`). In the tests: for many expressions the whole generated program, including the multiply and divide subroutines, is run on the simulator and HL must equal the value Phase 3 computed from the tree.

**Q17. Where is AI used?**
In two places, both after the compiler has found an error. The AI explains the error in plain English, and it proposes a corrected input. The compiler then runs that corrected input through all five phases, and the fix is shown only if every phase passes, so the AI proposes and the compiler decides. The AI sits outside the compiler (none of the five phases imports it), and without an API key built-in rules take over. All five phases are written by hand.

**Q18. What happens when there is an error?**
The phase raises a `CompilerError` with the phase, message and position. `main.py` stops the pipeline there, shows the error and the explanation. We stop at the first error and do no error recovery.

**Q19. What is the time complexity of the compiler?**
Each phase makes one pass over its input, so it is roughly linear in the length of the input. (The generated multiply and divide routines take time proportional to the numbers, because they work by repeated addition and subtraction.)

**Q20. What are the limitations?**
Whole-number arithmetic only (division is whole-number division), numerals 1 to 3999 only, every value must stay between 0 and 65535 (so no negative results), no unary minus, no variables, and the assembly is written but not assembled or run by the compiler.

**Q21. How would you add a new operator, say `%` (modulo)?**
Six small edits:
1. `lexer.py`: add `%` to the one-character symbols in `tokenize` (`"+-*/%()"`).
2. `parser.py`: in `parse_term`, also loop on `"%"`.
3. `semantic.py`: in `calculate`, handle `%` (and check for zero like `/`).
4. `codegen.py`: add `"%": "MOD16"` to `ROUTINE`, and write a `MOD16` subroutine in `LIBRARY` (like `DIV16`, but return the remainder in HL).
5. `optimizer.py`: add `"CALL MOD16": "%"` to `OPERATORS`.
6. Add a test.

**Q22. The 8085 has no multiply instruction. How do you multiply?**
`MUL16` multiplies by repeated addition: it adds the left number to a running total as many times as the right number says, using `DAD B` and counting `DE` down with `DCX D` until it is zero. Division (`DIV16`) is repeated subtraction: it counts how many times the right number can be taken away from the left.

**Q23. Why do you use 16-bit register pairs and the stack?**
The 8085 registers are 8 bits (0 to 255), but Roman numerals go up to 3999 and results grow, so we use the 16-bit pairs HL and DE (0 to 65535). The stack (`PUSH` / `POP`) lets us keep intermediate results while we work on the other side of an expression, which matches the tree walk exactly.

**Q24. Why are negative numbers and results above 65535 errors?**
The 16-bit register pair can only hold 0 to 65535, and Roman numerals have no negatives. Instead of letting the program silently give a wrong answer, Phase 3 reports it as a semantic error before any code is written.

**Q25. How do you stop the AI from giving a wrong fix?**
I never use its answer directly. The suggestion goes back through `run_phases`, the same five phases as any input. If any phase rejects it, it is thrown away, the reason is shown (`... but the compiler rejected it`), and the next candidate is tried. If none passes, the output says `NO VERIFIED FIX`.

**Q26. Does a verified fix mean the fix is what the user meant?**
No. It only means the corrected input is a valid program. `VX - II` becomes `V - II`, which compiles, but the user may have meant `XV - II`. That is why it is called a suggested fix, and the original input is still reported as an error.

**Q27. What happens without an API key?**
The explainer and the fix suggester use built-in rules. The rules fix three clear mistakes (a badly written numeral, a missing `)`, an extra `)`), and the compiler still verifies the result. With a key, the AI's fix is tried first.

---

## 12. One-page cheat sheet

| # | Phase | File and key function | Input | Output | Technique | Errors it catches |
|---|---|---|---|---|---|---|
| 1 | Lexical | `lexer.py`, `tokenize`, `validate_roman` | text | tokens | character scan, round-trip check | bad character, bad numeral (`IIII`, `VX`) |
| 2 | Syntax | `parser.py`, `Parser.parse_*` | tokens | parse tree | recursive descent | missing operand, bracket or operator |
| 3 | Semantic | `semantic.py`, `analyze` | tree | tree with `val` | S-attributed SDT, post-order | division by zero, value outside 0 to 65535 |
| 4 | Code generation | `codegen.py`, `gen`, `LIBRARY` | tree | 8085 assembly | post-order walk, subroutines | none |
| 5 | Optimization | `optimizer.py`, `optimize` | 8085 assembly | shorter 8085 assembly | constant folding | none |

**The 8085 program in one picture:** left number in HL, right number in DE, `CALL` the subroutine, answer comes back in HL, `PUSH H` keeps it on the stack. At the end `POP H`, `HLT`: the answer is in HL.

**Three sentences to remember:**
1. *Each phase takes the output of the previous one, and any phase can stop the pipeline with an error.*
2. *Precedence comes from the grammar, the tree carries it, and post-order walks (for values and for code) respect it.*
3. *The AI explains errors and proposes fixes, but the compiler checks every fix; every compiler phase is hand-written.*

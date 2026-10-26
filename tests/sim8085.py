# A tiny 8085 simulator, used ONLY by the tests to check the generated assembly.
# It understands just the instructions RomanCalc writes.

PAIRS = {"B": ("B", "C"), "D": ("D", "E"), "H": ("H", "L")}


def run8085(lines, max_steps=3_000_000):
    """Runs an 8085 program and returns the 16-bit value in HL when HLT is reached."""
    code, labels = [], {}
    for line in lines:
        line = line.split(";")[0].strip()          # drop comments
        if not line:
            continue
        if line.endswith(":"):
            labels[line[:-1]] = len(code)
        else:
            code.append(line)

    reg = dict.fromkeys("ABCDEHL", 0)
    stack = []
    zero = carry = False

    def get(pair):
        hi, lo = PAIRS[pair]
        return reg[hi] * 256 + reg[lo]

    def put(pair, value):
        hi, lo = PAIRS[pair]
        reg[hi], reg[lo] = (value >> 8) & 0xFF, value & 0xFF

    pc = 0
    for _ in range(max_steps):
        op, _, rest = code[pc].partition(" ")
        args = [a.strip() for a in rest.split(",")] if rest else []
        pc += 1

        if op == "LXI":
            if args[0] != "SP":
                put(args[0], int(args[1][:-1], 16))
        elif op == "PUSH":
            stack.append(get(args[0]))
        elif op == "POP":
            put(args[0], stack.pop())
        elif op == "CALL":
            stack.append(pc)
            pc = labels[args[0]]
        elif op == "RET":
            pc = stack.pop()
        elif op == "RZ":
            if zero:
                pc = stack.pop()
        elif op == "JMP":
            pc = labels[args[0]]
        elif op == "JC":
            if carry:
                pc = labels[args[0]]
        elif op == "DAD":
            total = get("H") + get(args[0])
            carry = total > 0xFFFF
            put("H", total & 0xFFFF)
        elif op == "MOV":
            reg[args[0]] = reg[args[1]]
        elif op in ("SUB", "SBB"):
            result = reg["A"] - reg[args[0]] - (carry if op == "SBB" else 0)
            carry = result < 0
            reg["A"] = result & 0xFF
            zero = reg["A"] == 0
        elif op == "ORA":
            reg["A"] |= reg[args[0]]
            zero, carry = reg["A"] == 0, False
        elif op == "INX":
            put(args[0], (get(args[0]) + 1) & 0xFFFF)
        elif op == "DCX":
            put(args[0], (get(args[0]) - 1) & 0xFFFF)
        elif op == "HLT":
            return get("H")
        else:
            raise ValueError("unknown instruction: " + code[pc - 1])
    raise RuntimeError("program did not stop")

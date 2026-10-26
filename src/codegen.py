# PHASE 4: CODE GENERATION
# Walks the tree and writes assembly language for a simple stack-based machine.
#
#   PUSH n        put the number n on the stack
#   POP reg       take the top of the stack into a register (EAX or EBX)
#   ADD EAX, EBX  EAX = EAX + EBX      (likewise SUB, MUL, DIV)
#   HLT           stop
from parser import NumeralNode

MNEMONIC = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}


def generate_code(tree):
    return gen(tree) + ["POP EAX", "HLT"]       # the final answer is left in EAX


def gen(node):
    if isinstance(node, NumeralNode):
        return [f"PUSH {node.value}"]

    return (gen(node.left)                      # code for the left side
            + gen(node.right)                   # code for the right side
            + ["POP EBX",                       # right operand
               "POP EAX",                       # left operand
               f"{MNEMONIC[node.op]} EAX, EBX", # EAX = EAX op EBX
               "PUSH EAX"])                     # keep the result on the stack

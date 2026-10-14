"""CLI: runs an expression through the whole RomanCalc pipeline and prints,
for every phase, what the phase does and what it outputs.

    python main.py "XII + IV * II"
"""
import sys
from pipeline import run_pipeline


def block(info, lines):
    print(f"\n{'-' * 68}\n{info['name'].upper()}\n  does  : {info['does']}\n  output: {info['output']}\n")
    for line in lines:
        print("   ", line)


def show(r):
    info = {p["key"]: p for p in r["phases"]}
    if "tokens" in r:
        block(info["lexical"], [f"{t['type']:<10} '{t['lexeme']}'" + (f"  value={t['value']}" if t["value"] is not None else "") + f"  pos={t['position']}" for t in r["tokens"]])
    if "tree_str" in r:
        block(info["syntax"], [r["tree_str"]])
    if "semantic_value" in r:
        block(info["semantic"], [f"value of the expression = {r['semantic_value']}"])
    if "code" in r:
        block(info["codegen"], r["code"])
    if "code_opt" in r:
        block(info["optimize"], [f"fold: {x}" for x in r["fold_log"]] + ["", "optimized program:"] + r["code_opt"]
              + ["", f"{len(r['code'])} instructions -> {len(r['code_opt'])} instructions"])
    if "result_decimal" in r:
        block(info["vm"], [f"unoptimized: {r['vm_before']['steps']} VM steps   optimized: {r['vm_after']['steps']} VM steps",
                           f"RESULT = {r['result_decimal']}  =  {r['result_roman'] or 'n/a (' + r['result_note'] + ')'}"])
    if r["error"]:
        e = r["error"]
        pos = f" (position {e['position']})" if e["position"] is not None else ""
        print(f"\n[{e['phase'].upper()} ERROR] {e['message']}{pos}")


if __name__ == "__main__":
    show(run_pipeline(sys.argv[1] if len(sys.argv) > 1 else "XII + IV * II"))

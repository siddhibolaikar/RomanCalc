import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from main import compile_source, stage_text


def test_successful_compile_has_five_stages_and_the_final_output():
    stages, asm = compile_source("XII + IV * II")
    titles = [s[0] for s in stages]
    assert titles == ["PHASE 1: LEXICAL ANALYSIS", "PHASE 2: SYNTAX ANALYSIS", "PHASE 3: SEMANTIC ANALYSIS",
                      "PHASE 4: CODE GENERATION", "PHASE 5: CODE OPTIMIZATION", "FINAL OUTPUT: ASSEMBLY PROGRAM"]
    assert asm == ["PUSH 20", "POP EAX", "HLT"]
    assert stages[-1][2] == asm


def test_every_stage_says_what_it_does():
    stages, _ = compile_source("XII")
    assert all(what for _, what, _ in stages)


def test_error_stops_at_the_failing_phase():
    stages, asm = compile_source("XII +")
    assert [s[0] for s in stages][:2] == ["PHASE 1: LEXICAL ANALYSIS", "SYNTAX ERROR"]
    assert asm is None


def test_lexical_error_has_only_error_stages():
    stages, _ = compile_source("IIII")
    assert stages[0][0] == "LEXICAL ERROR"


def test_stage_text_format():
    text = stage_text(("TITLE", "what", ["line1", "line2"]))
    assert text.startswith("=" * 62 + "\nTITLE\nwhat\n") and "  line1\n  line2\n" in text

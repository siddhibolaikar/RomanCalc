class CompilerError(Exception):
    """Structured error raised by any compilation phase.

    Kept structured (not just a string) so a later AI-explainer layer
    can consume `to_dict()` directly instead of parsing error text.
    """

    def __init__(self, phase, message, position=None, lexeme=None):
        self.phase = phase          # "lexical" | "syntax" | "semantic"
        self.message = message
        self.position = position    # character offset in the source string
        self.lexeme = lexeme        # offending text, if applicable
        suffix = f" at position {position}" if position is not None else ""
        super().__init__(f"[{phase}] {message}{suffix}")

    def to_dict(self):
        return {
            "phase": self.phase,
            "message": self.message,
            "position": self.position,
            "lexeme": self.lexeme,
        }

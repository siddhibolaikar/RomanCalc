class CompilerError(Exception):
    """Raised by any phase when the input is wrong."""

    def __init__(self, phase, message, position=None, lexeme=None):
        super().__init__(message)
        self.phase = phase          # "lexical", "syntax" or "semantic"
        self.message = message      # what is wrong
        self.position = position    # character number in the input
        self.lexeme = lexeme        # the offending text

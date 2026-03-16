import re
from dataclasses import dataclass
from enum import Enum, auto


class TT(Enum):
    TEXT = auto()
    PRINT_ESCAPED = auto()
    PRINT_RAW = auto()
    COMMENT = auto()
    VERBATIM = auto()
    PYTHON = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    ENDIF = auto()
    FOR = auto()
    ENDFOR = auto()
    COMPONENT = auto()  # Component tag (both self-closing and opening)
    VITE = auto()


@dataclass
class Token:
    type: TT
    value: str = ""
    extra: dict[str, str] = None  # For storing additional regex groups

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


_BLOCK = re.MULTILINE | re.DOTALL
_LINE = re.MULTILINE

# Patterns are checked in order; the earliest match wins.
# Block patterns (VERBATIM, PYTHON) must come first so they consume
# their inner content before inline patterns (PRINT_*) can match inside them.
_PATTERNS: list[tuple[TT, re.Pattern]] = [
    (
        TT.VERBATIM,
        re.compile(
            r"^[ \t]*@verbatim[ \t]*\n(.*?)^[ \t]*@endverbatim[ \t]*\n?", _BLOCK
        ),
    ),
    (
        TT.PYTHON,
        re.compile(r"^[ \t]*@python[ \t]*\n(.*?)^[ \t]*@endpython[ \t]*\n?", _BLOCK),
    ),
    (TT.COMMENT, re.compile(r"{{--(.*?)--}}", _BLOCK)),
    # Component tags (both self-closing and paired)
    (
        TT.COMPONENT,
        re.compile(
            r'<x-([\w\-.]+)((?:\s+:?[\w\-]+(?:="[^"]*")?)*)\s*(?:/>|(>)(.*?)</x-\1>)',
            _BLOCK,
        ),
    ),
    (TT.PRINT_ESCAPED, re.compile(r"{{\s*(.*?)\s*}}")),
    (TT.PRINT_RAW, re.compile(r"{!!\s*(.*?)\s*!!}")),
    (TT.IF, re.compile(r"^[ \t]*@if\((.+)\)[ \t]*\n?", _LINE)),
    (TT.ELIF, re.compile(r"^[ \t]*@elif\((.+)\)[ \t]*\n?", _LINE)),
    (TT.ELSE, re.compile(r"^[ \t]*@else[ \t]*\n?", _LINE)),
    (TT.ENDIF, re.compile(r"^[ \t]*@endif[ \t]*\n?", _LINE)),
    (TT.FOR, re.compile(r"^[ \t]*@for\((.+)\)[ \t]*\n?", _LINE)),
    (TT.ENDFOR, re.compile(r"^[ \t]*@endfor[ \t]*\n?", _LINE)),
    (TT.VITE, re.compile(r"^[ \t]*@vite\((.+)\)[ \t]*\n?", _LINE)),
]

_DIRECTIVE_TYPES = {
    TT.IF,
    TT.ELIF,
    TT.ELSE,
    TT.ENDIF,
    TT.FOR,
    TT.ENDFOR,
    TT.PYTHON,
    TT.VERBATIM,
    TT.VITE,
}


def tokenize(template: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0

    while pos < len(template):
        best: re.Match | None = None
        best_type: TT | None = None

        for token_type, pattern in _PATTERNS:
            m = pattern.search(template, pos)
            if m and (best is None or m.start() < best.start()):
                best = m
                best_type = token_type

        if best is None:
            tokens.append(Token(TT.TEXT, template[pos:]))
            break

        if best.start() > pos:
            tokens.append(Token(TT.TEXT, template[pos : best.start()]))

        value = best.group(1) if best.lastindex else ""

        # For components, store all groups
        extra = {}
        if best_type == TT.COMPONENT:
            extra = {
                "name": best.group(1) or "",
                "attrs": best.group(2) or "",
                "is_paired": best.group(3) is not None,
                "slot": best.group(4) or "",
            }

        tokens.append(Token(best_type, value, extra))  # type: ignore[arg-type]
        pos = best.end()

    # Preserve existing behaviour: blank lines that follow directives are dropped.
    result = []
    for i, token in enumerate(tokens):
        if (
            token.type == TT.TEXT
            and not token.value.strip()
            and i > 0
            and tokens[i - 1].type in _DIRECTIVE_TYPES
        ):
            continue
        result.append(token)

    return result

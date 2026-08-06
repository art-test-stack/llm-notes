from __future__ import annotations

import builtins
import html
import io
import keyword
import re
import token
import tokenize

PYTHON_BLOCK_RE = re.compile(
    r'<pre><code class="language-python">(?P<code>.*?)</code></pre>',
    re.IGNORECASE | re.DOTALL,
)

BUILTIN_NAMES = frozenset(dir(builtins))
BUILTIN_TYPE_NAMES = frozenset(
    name for name in BUILTIN_NAMES if isinstance(getattr(builtins, name), type)
)
TYPE_NAMES = frozenset(
    {
        "Any",
        "Callable",
        "ClassVar",
        "Final",
        "Generic",
        "Iterable",
        "Iterator",
        "Literal",
        "Mapping",
        "NamedTuple",
        "Optional",
        "Protocol",
        "Sequence",
        "TypeAlias",
        "TypeVar",
        "Union",
        "Self",
        "Tensor",
        "Module",
        "Path",
        "DataLoader",
        "Dataset",
        "IterableDataset",
    }
)
CONSTANT_NAMES = frozenset({"True", "False", "None", "NotImplemented", "Ellipsis"})
IGNORED_TOKEN_TYPES = frozenset(
    {
        token.ENDMARKER,
        token.INDENT,
        token.DEDENT,
        token.NEWLINE,
        tokenize.NL,
        tokenize.ENCODING,
    }
)

SYNTAX_CSS = r'''
.chapter-content pre{position:relative;border:1px solid #263449;background:linear-gradient(145deg,#0b1220,#101a2d 70%,#0d1728);box-shadow:0 12px 30px rgba(15,23,42,.13),inset 0 1px 0 rgba(255,255,255,.04);padding:18px 20px;line-height:1.62;tab-size:4;scrollbar-color:#52627a transparent}.chapter-content pre.code-block{padding-top:44px}.chapter-content pre.code-block::before{content:attr(data-language);position:absolute;top:0;left:0;right:0;height:30px;display:flex;align-items:center;padding:0 14px;border-bottom:1px solid #263449;background:rgba(2,6,23,.52);color:#8fa2bd;font:700 .68rem/1 Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;letter-spacing:.11em;text-transform:uppercase}.chapter-content pre.code-block::after{content:"";position:absolute;top:10px;right:14px;width:7px;height:7px;border-radius:50%;background:#fb7185;box-shadow:-13px 0 #fbbf24,-26px 0 #4ade80}.chapter-content pre code{font-size:.88rem;color:#d8e2f0}.syntax-comment{color:#7f8da4;font-style:italic}.syntax-string{color:#a7d89b}.syntax-number{color:#f6bd60}.syntax-keyword{color:#c099ff}.syntax-declaration{color:#ff7ab2;font-weight:700}.syntax-function-def{color:#82aaff;font-weight:750}.syntax-class-def{color:#ffd580;font-weight:750}.syntax-function-call{color:#89ddff}.syntax-builtin{color:#ff9e64}.syntax-type{color:#ffd580}.syntax-constant{color:#ff966c;font-weight:650}.syntax-attribute{color:#addb67}.syntax-decorator{color:#c099ff}.syntax-operator{color:#89ddff}.syntax-error{color:#ff5370;text-decoration:underline;text-decoration-style:wavy}@media(max-width:580px){.chapter-content pre{padding:16px 14px}.chapter-content pre.code-block{padding-top:42px}.chapter-content pre.code-block::before{padding-left:12px}.chapter-content pre code{font-size:.84rem}}
'''


def _absolute_offset(line_offsets: list[int], position: tuple[int, int]) -> int:
    row, column = position
    return line_offsets[row - 1] + column


def _significant_indices(tokens: list[tokenize.TokenInfo]) -> tuple[list[int | None], list[int | None]]:
    previous: list[int | None] = [None] * len(tokens)
    following: list[int | None] = [None] * len(tokens)

    last: int | None = None
    for index, item in enumerate(tokens):
        previous[index] = last
        if item.type not in IGNORED_TOKEN_TYPES and item.type != tokenize.COMMENT:
            last = index

    next_index: int | None = None
    for index in range(len(tokens) - 1, -1, -1):
        following[index] = next_index
        item = tokens[index]
        if item.type not in IGNORED_TOKEN_TYPES and item.type != tokenize.COMMENT:
            next_index = index

    return previous, following


def _name_class(
    tokens: list[tokenize.TokenInfo],
    index: int,
    previous: list[int | None],
    following: list[int | None],
) -> str | None:
    value = tokens[index].string
    prev_index = previous[index]
    next_index = following[index]
    prev_value = tokens[prev_index].string if prev_index is not None else ""
    next_value = tokens[next_index].string if next_index is not None else ""

    if value in CONSTANT_NAMES:
        return "syntax-constant"
    if prev_value == "def":
        return "syntax-function-def"
    if prev_value == "class":
        return "syntax-class-def"
    if prev_value == "@" or (prev_value == "." and _inside_decorator(tokens, index, previous)):
        return "syntax-decorator"
    if keyword.iskeyword(value):
        return "syntax-declaration" if value in {"def", "class"} else "syntax-keyword"
    if value in TYPE_NAMES or value in BUILTIN_TYPE_NAMES or value[:1].isupper():
        return "syntax-type"
    if prev_value == ".":
        return "syntax-function-call" if next_value == "(" else "syntax-attribute"
    if value in BUILTIN_NAMES:
        return "syntax-builtin"
    if next_value == "(":
        return "syntax-function-call"
    return None


def _inside_decorator(
    tokens: list[tokenize.TokenInfo], index: int, previous: list[int | None]
) -> bool:
    del previous
    for current in range(index - 1, -1, -1):
        item = tokens[current]
        if item.type in {token.NEWLINE, tokenize.NL}:
            return False
        if item.string == "@":
            return True
    return False


def _token_class(
    tokens: list[tokenize.TokenInfo],
    index: int,
    previous: list[int | None],
    following: list[int | None],
) -> str | None:
    item = tokens[index]
    if item.type == tokenize.COMMENT:
        return "syntax-comment"
    if item.type == token.STRING:
        return "syntax-string"
    if item.type == token.NUMBER:
        return "syntax-number"
    if item.type == token.NAME:
        return _name_class(tokens, index, previous, following)
    if item.type == token.OP:
        return "syntax-operator"
    if item.type == token.ERRORTOKEN and not item.string.isspace():
        return "syntax-error"
    return None


def highlight_python(source: str) -> str:
    line_offsets = [0]
    for line in source.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (IndentationError, SyntaxError, tokenize.TokenError):
        return html.escape(source)

    previous, following = _significant_indices(tokens)
    result: list[str] = []
    cursor = 0

    for index, item in enumerate(tokens):
        start = _absolute_offset(line_offsets, item.start)
        end = _absolute_offset(line_offsets, item.end)
        if start < cursor:
            continue
        result.append(html.escape(source[cursor:start]))
        escaped = html.escape(source[start:end])
        css_class = _token_class(tokens, index, previous, following)
        if css_class and escaped:
            result.append(f'<span class="{css_class}">{escaped}</span>')
        else:
            result.append(escaped)
        cursor = end

    result.append(html.escape(source[cursor:]))
    return "".join(result)


def highlight_python_blocks(fragment: str) -> str:
    def replace(match: re.Match[str]) -> str:
        source = html.unescape(match.group("code"))
        highlighted = highlight_python(source)
        return (
            '<pre class="code-block" data-language="Python">'
            '<code class="language-python">'
            f"{highlighted}</code></pre>"
        )

    return PYTHON_BLOCK_RE.sub(replace, fragment)

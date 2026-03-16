from .tokens import TT, Token


def compile_tokens(tokens: list[Token]) -> list[str]:
    lines: list[str] = ['output = ""\n']
    depth = 0
    component_counter = 0

    for token in tokens:
        ind = "    " * depth

        if token.type in (TT.TEXT, TT.VERBATIM):
            if token.value:
                lines.append(f"{ind}output += {repr(token.value)}\n")

        elif token.type == TT.COMMENT:
            pass

        elif token.type == TT.PRINT_ESCAPED:
            # Special case: 'slot' should not be escaped (it's already rendered HTML)
            if token.value.strip() == "slot":
                lines.append(f"{ind}output += str({token.value})\n")
            else:
                lines.append(f"{ind}output += html.escape(str({token.value}))\n")

        elif token.type == TT.PRINT_RAW:
            lines.append(f"{ind}output += str({token.value})\n")

        elif token.type == TT.PYTHON:
            for stmt in token.value.splitlines():
                stripped = stmt.strip()
                if stripped:
                    lines.append(f"{ind}{stripped}\n")

        # Component handling
        elif token.type == TT.COMPONENT:
            comp_name = token.extra.get("name", "")
            attr_str = token.extra.get("attrs", "")
            slot = token.extra.get("slot", "")

            # Parse attributes
            static_attrs, dynamic_attrs = _parse_attributes(attr_str)

            # Build attributes dict at runtime
            attr_var = f"_comp_attrs_{component_counter}"
            slot_var = f"_comp_slot_{component_counter}"

            lines.append(f"{ind}{attr_var} = {{}}\n")

            # Add static attributes
            for name, value in static_attrs.items():
                lines.append(f"{ind}{attr_var}[{repr(name)}] = {repr(value)}\n")

            # Add dynamic attributes (evaluated)
            for name, expr in dynamic_attrs.items():
                lines.append(f"{ind}{attr_var}[{repr(name)}] = {expr}\n")

            # Render slot content with parent context
            lines.append(f"{ind}{slot_var} = _render_slot({repr(slot)}, globals())\n")

            # Render component
            lines.append(f"{ind}output += _render_component(\n")
            lines.append(f"{ind}    {repr(comp_name)},\n")
            lines.append(f"{ind}    {attr_var},\n")
            lines.append(f"{ind}    {slot_var},\n")
            lines.append(f"{ind}    globals()\n")
            lines.append(f"{ind})\n")

            component_counter += 1

        elif token.type == TT.IF:
            lines.append(f"{ind}if {token.value}:\n")
            depth += 1

        elif token.type == TT.ELIF:
            depth -= 1
            lines.append(f"{'    ' * depth}elif {token.value}:\n")
            depth += 1

        elif token.type == TT.ELSE:
            depth -= 1
            lines.append(f"{'    ' * depth}else:\n")
            depth += 1

        elif token.type == TT.ENDIF:
            depth -= 1

        elif token.type == TT.FOR:
            lines.append(f"{ind}for {token.value}:\n")
            depth += 1

        elif token.type == TT.ENDFOR:
            depth -= 1

        elif token.type == TT.VITE:
            lines.append(f"{ind}output += _vite({token.value})\n")

    lines.append("return output\n")
    return lines


def compile_template(template: str) -> str:
    from .tokens import tokenize

    tokens = tokenize(template)
    body = compile_tokens(tokens)

    output = "import html\n\ndef render():\n"
    for line in body:
        output += f"    {line}"
    return output


def _parse_attributes(attr_string: str) -> tuple[dict[str, str], dict[str, str]]:
    """
    Parse component attributes into static and dynamic dicts.
    Returns: (static_attrs, dynamic_attrs)
    """
    import re

    static: dict[str, str] = {}
    dynamic: dict[str, str] = {}

    # Match attributes: optional colon, name, optional ="value"
    attr_pattern = re.compile(r'(:)?([\w\-]+)(?:="([^"]*)")?')

    for match in attr_pattern.finditer(attr_string):
        is_dynamic = match.group(1) == ":"
        name = match.group(2)
        value = match.group(3) if match.group(3) is not None else ""

        if is_dynamic:
            dynamic[name] = value
        else:
            static[name] = value

    return static, dynamic

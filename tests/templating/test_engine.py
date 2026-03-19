import os
from pathlib import Path

import pytest

from crya.templating import render_from_string, set_cache_dir, set_component_base_dir

PROJECT_ROOT = Path(os.path.abspath(__file__)).parent.parent.parent

TEMPLATING_FIXTURES_DIR = Path(PROJECT_ROOT) / "tests" / "fixtures" / "templating"


@pytest.fixture(autouse=True)
def configure_cache_dir(tmp_path):
    set_cache_dir(tmp_path)


def test_it_renders_a_simple_template_without_context():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "hello_world.loom") as f:
        template = f.read()

    rendered = render_from_string(template, {})

    assert rendered == template


def test_it_renders_a_template_with_print():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "hello_name.loom") as f:
        template = f.read()

    rendered = render_from_string(template, {"name": "Alice"})

    expected = """<html>
    <head>
        <title>Hello Alice</title>
    </head>
    <body>
        <h1>Hello Alice</h1>
    </body>
</html>
"""

    assert rendered == expected


def test_it_renders_a_template_with_escaped_print():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "hello_name.loom") as f:
        template = f.read()

    rendered = render_from_string(template, {"name": "<script>alert('XSS')</script>"})

    expected = """<html>
    <head>
        <title>Hello &lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;</title>
    </head>
    <body>
        <h1>Hello &lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;</h1>
    </body>
</html>
"""

    assert rendered == expected


def test_it_renders_a_template_with_unsafe_print():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "hello_unsafe_name.loom") as f:
        template = f.read()

    rendered = render_from_string(template, {"name": "<script>alert('XSS')</script>"})

    expected = """<html>
    <head>
        <title>Hello <script>alert('XSS')</script></title>
    </head>
    <body>
        <h1>Hello <script>alert('XSS')</script></h1>
    </body>
</html>
"""

    assert rendered == expected


def test_it_renders_a_template_with_simple_if():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "simple_if.loom") as f:
        template = f.read()

    rendered = render_from_string(template, {"morning": True})

    expected = """<html>
    <body>
            <h1>Good morning</h1>
    </body>
</html>
"""

    assert rendered == expected

    rendered = render_from_string(template, {"morning": False})

    expected = """<html>
    <body>
    </body>
</html>
"""

    assert rendered == expected


def test_it_renders_a_template_with_if_else():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "if_else.loom") as f:
        template = f.read()

    rendered = render_from_string(template, {"morning": True})

    expected = """<html>
    <body>
            <h1>Good morning</h1>
    </body>
</html>
"""

    assert rendered == expected

    rendered = render_from_string(template, {"morning": False})

    expected = """<html>
    <body>
            <h1>Good evening</h1>
    </body>
</html>
"""

    assert rendered == expected


def test_it_renders_a_template_with_if_elif_else():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "if_elif.loom") as f:
        template = f.read()

    rendered = render_from_string(template, {"time": "morning"})

    expected = """<html>
    <body>
            <h1>Good morning</h1>
    </body>
</html>
"""

    assert rendered == expected

    rendered = render_from_string(template, {"time": "afternoon"})

    expected = """<html>
    <body>
            <h1>Good afternoon</h1>
    </body>
</html>
"""

    assert rendered == expected

    assert rendered == expected

    rendered = render_from_string(template, {"time": "evening"})

    expected = """<html>
    <body>
            <h1>Good evening</h1>
    </body>
</html>
"""

    assert rendered == expected


def test_it_renders_a_template_with_for():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "for.loom") as f:
        template = f.read()

    rendered = render_from_string(
        template, {"days": ["Monday", "Tuesday", "Wednesday"]}
    )

    expected = """<html>
    <body>
            <h1>Monday</h1>
            <h1>Tuesday</h1>
            <h1>Wednesday</h1>
    </body>
</html>
"""

    assert rendered == expected


def test_it_renders_a_template_with_python_statements():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "python.loom") as f:
        template = f.read()

    rendered = render_from_string(template)

    expected = """<html>
    <body>
            <h1>Monday</h1>
            <h1>Tuesday</h1>
            <h1>Wednesday</h1>
            <h1>Thursday</h1>
            <h1>Friday</h1>
    </body>
</html>
"""

    assert rendered == expected


def test_it_renders_a_template_with_verbatim_statements():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "verbatim.loom") as f:
        template = f.read()

    rendered = render_from_string(template)

    expected = """<html>
    <body>
        @python
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        @endpython

        @for(day in days)
            <h1>{{ day }}</h1>
        @endfor
    </body>
</html>
"""

    assert rendered == expected


def test_it_renders_a_template_with_comments():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "comments.loom") as f:
        template = f.read()

    rendered = render_from_string(template, {"name": "Alice"})

    expected = (
        "<html>\n"
        "    <body>\n"
        "        \n"
        "        <h1>Hello World</h1>\n"
        "        \n"
        "        <p>Alice</p>\n"
        "        \n"
        "    </body>\n"
        "</html>\n"
    )

    assert rendered == expected


def test_it_renders_a_template_with_python_block_ignored_in_comments():
    with open(TEMPLATING_FIXTURES_DIR / "templates" / "python_in_comments.loom") as f:
        template = f.read()

    rendered = render_from_string(template, {"name": "Alice"})

    expected = (
        "<html>\n"
        "    <body>\n"
        "        <h1>Hello World</h1>\n"
        "        \n"
        "        <p>Alice</p>\n"
        "    </body>\n"
        "</html>\n"
    )

    assert rendered == expected


def test_component_with_static_attributes():
    set_component_base_dir(TEMPLATING_FIXTURES_DIR / "components")

    template = '<x-alert type="danger">Error message</x-alert>'
    rendered = render_from_string(template)

    assert 'class="alert alert-danger"' in rendered
    assert "Error message" in rendered


def test_component_with_dynamic_attributes():
    set_component_base_dir(TEMPLATING_FIXTURES_DIR / "components")

    template = '<x-alert :type="alert_type">{{ message }}</x-alert>'
    context = {"alert_type": "warning", "message": "Be careful"}
    rendered = render_from_string(template, context)

    assert "alert-warning" in rendered
    assert "Be careful" in rendered


def test_nested_component_with_dot_notation():
    set_component_base_dir(TEMPLATING_FIXTURES_DIR / "components")

    template = '<x-card.header title="Welcome">Subtitle here</x-card.header>'
    rendered = render_from_string(template)

    assert "<h3>Welcome</h3>" in rendered
    assert "Subtitle here" in rendered


def test_self_closing_component():
    set_component_base_dir(TEMPLATING_FIXTURES_DIR / "components")

    template = '<x-alert type="info" />'
    rendered = render_from_string(template)

    assert "alert-info" in rendered


def test_component_inherits_parent_context():
    set_component_base_dir(TEMPLATING_FIXTURES_DIR / "components")

    template = '<x-alert type="info">{{ username }}</x-alert>'
    context = {"username": "Alice"}
    rendered = render_from_string(template, context)

    assert "Alice" in rendered

import html

def render():
    output = ""
    output += '<html>\n    <head>\n        <title>Welcome</title>\n    </head>\n\n    <body>\n        <h1>This is a '
    output += html.escape(str(name))
    output += ' app</h1>\n    </body>\n</html>\n'
    return output

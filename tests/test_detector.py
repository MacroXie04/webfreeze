from webfreeze.detector import should_render

def test_should_render_spa():
    spa_html = """
    <html>
        <head><title>SPA</title></head>
        <body>
            <div id="root"></div>
            <script src="app.js"></script>
        </body>
    </html>
    """
    assert should_render(spa_html) is True

def test_should_not_render_static():
    static_html = """
    <html>
        <head><title>Static</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is a static page with enough content.</p>
            <div>More content here to exceed the threshold.</div>
            <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
            Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
        </body>
    </html>
    """
    assert should_render(static_html) is False

def test_should_render_empty_body():
    empty_html = "<html><body></body></html>"
    assert should_render(empty_html) is True

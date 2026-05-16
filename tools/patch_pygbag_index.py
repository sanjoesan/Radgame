"""Post-Build-Patch fuer build/web/index.html.

pygbag setzt per Default einen 1280x720-Landscape-Framebuffer (fb_ar 1.77)
und stretcht das Canvas per CSS auf 100%x100% — auf Portrait-Handys quetscht
das unser Pygame-Surface in 16:9 und verzerrt sichtbar. Dieser Patch laeuft
nach `pygbag --build` und macht drei Dinge:

1. Doppelter <meta viewport>-Tag zusammengefasst (height-Override war Murks).
2. fb_width/fb_height/fb_ar werden direkt nach dem Config-Dict auf den
   tatsaechlichen window.innerWidth/innerHeight gesetzt, bevor pygbag init
   liest.
3. Canvas-CSS auf 100vw x 100vh, html/body overflow:hidden + Background.

Wird aus .github/workflows/pages.yml aufgerufen.
"""

from pathlib import Path


def patch(p: Path) -> None:
    html = p.read_text()

    html = html.replace(
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '    <meta name="viewport" content="height=device-height, initial-scale=1.0">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0, '
        'viewport-fit=cover, user-scalable=no">',
    )

    needle = 'fb_height : "720"\n}'
    if needle not in html:
        raise SystemExit(
            "Patch-Anker fb_height nicht gefunden — pygbag-Template hat sich geaendert"
        )
    inject = needle + (
        "\n;(function(){"
        "\n    const w = Math.max(320, window.innerWidth|0);"
        "\n    const h = Math.max(480, window.innerHeight|0);"
        "\n    config.fb_width = String(w);"
        "\n    config.fb_height = String(h);"
        "\n    config.fb_ar = w / h;"
        "\n})()"
    )
    html = html.replace(needle, inject)

    html = html.replace(
        "</head>",
        "<style>\n"
        "html, body { width: 100%; height: 100%; overflow: hidden; background: #14182a; }\n"
        "canvas.emscripten { width: 100vw !important; height: 100vh !important; "
        "max-width: 100vw; max-height: 100vh; display: block; }\n"
        "</style>\n</head>",
    )

    p.write_text(html)
    print("index.html gepatcht")


if __name__ == "__main__":
    patch(Path("build/web/index.html"))

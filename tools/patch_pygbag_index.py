"""Post-Build-Patch fuer build/web/index.html.

pygbag setzt per Default einen 1280x720-Landscape-Framebuffer (fb_ar 1.77).
Unser Pygame-Surface ist aber portrait — ohne Patch wird das Canvas in
Landscape gestretcht und auf Portrait-Handys gequetscht. Dieser Patch:

1. Doppelter <meta viewport>-Tag zusammengefasst (height-Override war Murks).
2. fb_width/fb_height/fb_ar werden direkt nach dem Config-Dict auf den
   tatsaechlichen window.innerWidth/innerHeight gesetzt, BEVOR pygbag init
   liest. Damit ist das Canvas innen passend portrait.
3. html/body auf 100% Hoehe + ohne Scrollbars + Hintergrund. Canvas-CSS
   wird NICHT angefasst — pygbags Default `width:100%; height:100%; top/
   bottom/left/right:0` fuellt das Viewport korrekt, sobald body 100%
   gross ist.

WICHTIG: KEIN 100vh benutzen! Auf Mobile ist 100vh > innerHeight, weil die
URL-Bar nicht abgezogen wird — das schiebt das Canvas ueber den sichtbaren
Bereich, oben/unten werden abgeschnitten und Touch-Buttons sind unsichtbar.

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
    # Sync-Funktion + ein Initial-Run + Listener auf resize/orientationchange.
    # Mobile URL-Bar kollabiert nach dem ersten Paint -> innerHeight waechst
    # -> ohne Re-Sync rechnet pygbag mit altem fb_ar und letterboxt grau.
    # Wir warten ein paar Frames per rAF, weil innerHeight direkt im Event
    # noch den alten Wert hat.
    inject = needle + (
        "\nwindow.__radgame_sync_fb = function(){"
        "\n    const w = Math.max(320, window.innerWidth|0);"
        "\n    const h = Math.max(480, window.innerHeight|0);"
        "\n    config.fb_width = String(w);"
        "\n    config.fb_height = String(h);"
        "\n    config.fb_ar = w / h;"
        "\n    if (typeof window.window_resize === 'function') {"
        "\n        try { window.window_resize(); } catch (e) {}"
        "\n    }"
        "\n};"
        "\nwindow.__radgame_sync_fb();"
        "\nfunction __radgame_sync_deferred(){"
        "\n    requestAnimationFrame(function(){"
        "\n        requestAnimationFrame(window.__radgame_sync_fb);"
        "\n    });"
        "\n}"
        "\nwindow.addEventListener('resize', __radgame_sync_deferred);"
        "\nwindow.addEventListener('orientationchange', function(){"
        "\n    setTimeout(window.__radgame_sync_fb, 250);"
        "\n});"
        "\nif (window.visualViewport) {"
        "\n    window.visualViewport.addEventListener('resize', __radgame_sync_deferred);"
        "\n}"
    )
    html = html.replace(needle, inject)

    # Nur html/body anfassen — Canvas-CSS bleibt wie pygbag es haben will.
    html = html.replace(
        "</head>",
        "<style>\n"
        "html, body { width: 100%; height: 100%; margin: 0; padding: 0; "
        "overflow: hidden; background: #14182a; }\n"
        "</style>\n</head>",
    )

    p.write_text(html)
    print("index.html gepatcht")


if __name__ == "__main__":
    patch(Path("build/web/index.html"))

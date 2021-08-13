import os
import webbrowser


# Open documentation in new browser tab
def open_documentation():
    webbrowser.open(
        "file://" + os.path.abspath(__file__ + "../../../html/reportlib/index.html"),
        new=2,
    )

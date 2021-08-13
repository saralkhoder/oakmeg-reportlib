"""General utilities"""
import os
import webbrowser


def open_documentation():
    """
    Open the reportlib documentation in new browser tab
    """
    webbrowser.open(
        "file://" + os.path.abspath(__file__ + "../../../html/reportlib/index.html"),
        new=2,
    )

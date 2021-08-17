"""General utilities"""
import os
import webbrowser
from enum import Enum


class Colors(Enum):
    BLUE = "#636EFA"
    LIGHTBLUE = "#55BDFF"
    ORANGE = "#F7C92F"
    GREEN = "#5DBD48"
    PINK = "#DE89FA"
    # px.colors.qualitative.T10[4]


def open_documentation():
    """
    Open the **reportlib documentation** in a new browser tab
    """
    webbrowser.open(
        "file://" + os.path.abspath(__file__ + "../../../html/reportlib/index.html"),
        new=2,
    )

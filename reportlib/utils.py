"""General utilities"""
import os
import webbrowser
from enum import Enum


class Color(Enum):
    LIGHTGREY = "#D0D6D9"
    BLUE = "#636EFA"
    LIGHTBLUE = "#55BDFF"
    ORANGE = "#F2C11F"
    GREEN = "#5DBD48"
    PINK = "#DE89FA"


def open_documentation():
    """
    Open the **reportlib documentation** in a new browser tab
    """
    webbrowser.open(
        "file://" + os.path.abspath(__file__ + "../../../html/reportlib/index.html"),
        new=2,
    )

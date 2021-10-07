"""General utilities"""
import os
import webbrowser
from enum import Enum


"""
class Color(Enum):
    LIGHTGREY = "#D0D6D9"
    GREY = "#9E9E9E"
    DARKGREY = "#5E5E5E"
    BLUE = "#636EFA"
    LIGHTBLUE = "#55BDFF"
    YELLOW = "#F2C11F"
    DARKYELLOW = "#DB9A00"
    ORANGE = "#F08935"
    GREEN = "#5DBD48"
    PINK = "#DE89FA"
"""

class Color(Enum):
    LIGHTGREY = "#D0D6D9"
    GREY = "#B8BFBF"
    DARKGREY = "#5E5E5E"
    BLUE = "#415AA3"
    LIGHTBLUE = "#55BDFF"
    YELLOW = "#E1D798"
    DARKYELLOW = "#DB9A00"
    ORANGE = "#F08935"
    GREEN = "#67A86B"
    PINK = "#DE89FA"
    BROWN = "#675645"


PALETTE = [
    Color.BLUE.value,
    Color.GREEN.value,
    Color.YELLOW.value,
    Color.BROWN.value,
    Color.LIGHTGREY.value,
    Color.LIGHTBLUE.value,
    Color.DARKGREY.value
]

#PALETTE = [
#    '#415AA3',
#    '#67A86B',
#    '#E1D798',
#    '#675645',
#    '#B8BFBF'
#]

PALETTE_BINARY = [
    Color.ORANGE.value,
    Color.GREEN.value,
]

PALETTE_SHADES = [
    Color.DARKYELLOW.value,
    Color.YELLOW.value,
    Color.BLUE.value,
    Color.LIGHTBLUE.value
]


def open_documentation():
    """
    Open the **reportlib documentation** in a new browser tab
    """
    webbrowser.open(
        "file://" + os.path.abspath(__file__ + "../../../html/reportlib/index.html"),
        new=2,
    )

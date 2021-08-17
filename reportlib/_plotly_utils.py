from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio

M0_LAYOUT = {"margin": dict(t=0, b=0, l=0, r=0)}

DEFAULT_LAYOUT = {"font_family": "AppleGothic"}

TRANSPARENT_LAYOUT = {"paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)"}


# Set default style for all plotly figures
def use_atom_style():
    pio.templates["atom"] = go.layout.Template(
        layout=go.Layout(font_family="AppleGothic", plot_bgcolor="#F0F4FA")
    )
    pio.templates.default = "plotly+atom"


def save_fig_to(fig, to, width=None, height=None):
    Path("generated").mkdir(parents=True, exist_ok=True)

    save_path = "generated/" + to + ".png"
    if width and height:
        fig.write_image(save_path, width=width, height=height, scale=4)
    else:
        fig.write_image(save_path, scale=4)

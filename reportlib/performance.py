"""Module for reporting on campaign performance"""
from enum import Enum
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from reportlib.utils import Colors
from reportlib._plotly_utils import save_fig_to, M0_LAYOUT, DEFAULT_LAYOUT


class _Palette(Enum):
    IMPRESSIONS = Colors.BLUE.value
    REACH = Colors.LIGHTBLUE.value
    CTR = Colors.GREEN.value


def plot_daily(
    df: pd.DataFrame,
    with_reach: bool = True,
    min_impressions: int = 20,
    size: list = [850, 400],
    legend_position: str = "left",
    save_to: str = None,
):
    """
    Plot a daily performance bar + line chart showing impressions, reach (optional) and ctr
        Args:
            df (DataFrame): input data, can be exploded or already aggrega
            with_reach (bool): include reach
            min_impressions (number): threshold under which impressions are not displayed
            size (list): figure size, formatted as [width, height]
            legend_position ('left' | 'right'): legend box horizontal position
            save_to (str): save as png, don't write any extension here

        Returns:
            figure (plotly.graph_object.Figure)
    """

    with_reach = with_reach and "mobile_id" in df

    # only add reach if MAIDs are available and with_reach is True
    by_day = df.groupby(["date_served"], as_index=False, dropna=False).agg(
        {
            **{
                "impressions": "sum",
                "clicks": "sum",
            },
            **({"mobile_id": lambda x: x.nunique()} if with_reach else dict()),
        }
    )
    by_day["ctr"] = by_day["clicks"] / by_day["impressions"]

    # Filter out dates with quasi zero impressions
    by_day = by_day[by_day["impressions"] > min_impressions]

    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
        figure=go.Figure(layout={**DEFAULT_LAYOUT, **M0_LAYOUT}),
    )

    w_basis = np.asarray([1000 * 3600 * 19] * len(by_day["date_served"]))

    # Impressions
    fig.add_trace(
        go.Bar(
            name="Impressions",
            x=by_day["date_served"],
            y=by_day["impressions"],
            marker_color=_Palette.IMPRESSIONS.value,
            offset=-w_basis / 2,
        ),
        secondary_y=False,
    )

    # Reach
    if with_reach:
        fig.add_trace(
            go.Bar(
                name="Reach",
                x=by_day["date_served"],
                y=by_day["mobile_id"],
                marker_color=_Palette.REACH.value,
                offset=-w_basis / 2,
            ),
            secondary_y=False,
        )

    # CTR
    fig.add_trace(
        go.Scatter(
            x=by_day["date_served"],
            y=by_day["ctr"],
            name="CTR",
            marker_color=_Palette.CTR.value,
            mode="lines+markers",
            line_shape="spline",
        ),
        secondary_y=True,
    )

    # Adjust layout
    fig.update_layout(
        yaxis=dict(tickformat="s"),
        yaxis2=dict(tickformat="0.2%", range=[0, by_day["ctr"].max() * 1.5]),
        xaxis=dict(tickformat="%b %d", tickmode="auto"),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01 if legend_position == "left" else 0.75,
        ),
        font_size=15,
        width=size[0],
        height=size[1],
    )

    if save_to:
        save_fig_to(fig, save_to)

    return fig

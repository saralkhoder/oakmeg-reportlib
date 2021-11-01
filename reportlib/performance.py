"""Module for reporting on campaign performance"""
from enum import Enum
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from reportlib.utils import Color
from reportlib._plotly_utils import save_fig_to, M0_LAYOUT


class _Palette(Enum):
    IMPRESSIONS = Color.BROWN.value
    REACH = Color.YELLOW.value
    CTR = Color.GREEN.value


def overview(df: pd.DataFrame, reach_ratio: float = None, by: str = None):
    """
    Compute **impressions**, **ctr** and **reach** (if reach ratio provided), aggregated or broken down

    Usage:
        ``performance.overview(data.dash, by='aoi')``

    Args:
        df (DataFrame): input data, can be exploded or already aggregated
        reach_ratio (float): the reach ratio from loaded mop data
        by (str): *optional*, the column name to break down by
    """

    if not reach_ratio:
        print('add reach ratio argument to display reach')

    if not by:
        result = df[["impressions", "clicks"]].sum()
        result["impressions"] = result["impressions"]
        result["clicks"] = result["clicks"]
        result["ctr"] = result["clicks"] / result["impressions"]
        if reach_ratio:
            result["reach"] = (reach_ratio * result["impressions"])

        typesdict = {'impressions': 'int', 'clicks': 'int'}
        if reach_ratio:
            typesdict['reach'] = 'int'
        return pd.DataFrame(result).transpose().astype(typesdict)

    else:
        # only add reach if MAIDs are available and with_reach is True
        grouped = df.groupby([by], as_index=False, dropna=False).agg(
            {
                **{"impressions": "sum"},
                **({"clicks": "sum"} if "clicks" in df else dict()),
            }
        )
        grouped["impressions"] = grouped["impressions"].astype("int")
        grouped["clicks"] = grouped["clicks"].astype("int")

        if "clicks" in df:
            grouped["ctr"] = grouped["clicks"] / grouped["impressions"]

        if reach_ratio:
            grouped["reach"] = (reach_ratio * grouped["impressions"]).astype("int")

        return grouped


def plot_by(
    column: str,
    dash: pd.DataFrame,
    reach_ratio: float = None,
    min_impressions: int = 20,
    size: list = [750, 350],
    sort_by: str = None,
    legend_position: str = "left",
    save_to: str = None,
):
    """
    Plot a performance bar + line chart showing **impressions** and **ctr**

    Can be plotted by day or by category like message

    Usage:
        ``performance.plot_by(data.dash, 'date_served', legend_position='right', save_to='perf_daily')``

    Args:
        column (str): the column name to plot by
        dash (DataFrame): dash data (for impressions and ctr)
        reach_ratio (float): *optional*, reach ratio for displaying reach
        min_impressions (number): *optional*, threshold under which impressions are not displayed
        size (list): *optional*, figure size, formatted as [width, height]
        sort_by (bool): *optional*, what column to sort the x-axis with
        legend_position ('left' | 'right'): *optional*, legend box horizontal position
        save_to (str, optional): *optional*, save as png, don't write any extension here

    Returns:
        figure (plotly.graph_object.Figure)
    """
    is_time_graph = column == "date_served"

    agg = dash.groupby(column, as_index=False).agg(
        {"impressions": "sum", "clicks": "sum"}
    )
    agg["ctr"] = agg["clicks"] / agg["impressions"]

    if reach_ratio:
        agg["mobile_id"] = agg["impressions"] * reach_ratio

    # Filter out dates with quasi zero impressions
    agg = agg[agg["impressions"] > min_impressions]

    # Optionally sort
    if not is_time_graph and sort_by:
        agg = agg.sort_values(sort_by, ascending=False)

    # Make figure
    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
        figure=go.Figure(layout=M0_LAYOUT),
    )

    w_basis = np.asarray([1000 * 3600 * 19] * len(agg[column]))

    # ADD TRACES
    # Impressions
    fig.add_trace(
        go.Bar(
            name="Impressions",
            x=agg[column],
            y=agg["impressions"],
            marker_color=_Palette.IMPRESSIONS.value,
            offset=-w_basis / 2 if is_time_graph else -0.4,
        ),
        secondary_y=False,
    )

    # Reach
    if "mobile_id" in agg.columns:
        fig.add_trace(
            go.Bar(
                name="Reach",
                x=agg[column],
                y=agg["mobile_id"],
                marker_color=_Palette.REACH.value,
                offset=-w_basis / 2 if is_time_graph else -0.4,
            ),
            secondary_y=False,
        )

    # CTR
    fig.add_trace(
        go.Scatter(
            x=agg[column],
            y=agg["ctr"],
            name="CTR",
            marker=dict(size=8)
            if is_time_graph
            else dict(
                size=18, symbol="line-ew", line=dict(color=_Palette.CTR.value, width=6)
            ),
            marker_color=_Palette.CTR.value,
            mode="lines+markers" if is_time_graph else "markers",
            line_shape="spline",
        ),
        secondary_y=True,
    )

    # Adjust layout
    fig.update_layout(
        yaxis=dict(tickformat="s"),
        yaxis2=dict(tickformat="0.2%", range=[0, agg["ctr"].max() * 1.5]),
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

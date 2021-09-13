"""Module for reporting on campaign performance"""
from enum import Enum
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from reportlib.utils import Color
from reportlib._plotly_utils import save_fig_to, M0_LAYOUT


class _Palette(Enum):
    IMPRESSIONS = Color.BLUE.value
    REACH = Color.LIGHTBLUE.value
    CTR = Color.GREEN.value


def overview(
    df: pd.DataFrame,
    by: str = None
):
    """
    Compute **impressions**, **ctr** and **reach** (if available), aggregated or broken down

    Usage:
        ``performance.overview(data.dash, by='aoi')``

    Args:
        df (DataFrame): input data, can be exploded or already aggregated
        by (str): *optional*, the column name to break down by
    """
    has_reach = "mobile_id" in df

    if not by:
        result = df[['impressions', 'clicks']].sum()
        result['ctr'] = result['clicks'] / result['impressions']
        if has_reach:
            result['reach'] = result['mobile_id'].nunique()

        return result

    else:
        # only add reach if MAIDs are available and with_reach is True
        grouped = df.groupby([by], as_index=False, dropna=False).agg(
            {
                **{"impressions": "sum"},
                **({"clicks": "sum"} if "clicks" in df else dict()),
                **({"mobile_id": lambda x: x.nunique()} if has_reach else dict()),
            }
        )
        if "clicks" in df:
            grouped["ctr"] = grouped["clicks"] / grouped["impressions"]

        return grouped


def plot_by(
    df: pd.DataFrame,
    column: str,
    with_reach: bool = True,
    min_impressions: int = 20,
    size: list = [750, 400],
    sort_by: str = None,
    legend_position: str = "left",
    save_to: str = None,
):
    """
    Plot a performance bar + line chart showing **impressions**, **reach** (optional) and **ctr**

    Can be plotted by day or by category like message

    Usage:
        ``performance.plot_by(data.dash, 'date_served', legend_position='right', save_to='perf_daily')``

    Args:
        df (DataFrame): input data, can be exploded or already aggregated
        column (str): the column name to plot by
        with_reach (bool): *optional*, include reach
        min_impressions (number): *optional*, threshold under which impressions are not displayed
        size (list): *optional*, figure size, formatted as [width, height]
        sort_by (bool): *optional*, what column to sort the x-axis with
        legend_position ('left' | 'right'): *optional*, legend box horizontal position
        save_to (str, optional): *optional*, save as png, don't write any extension here

    Returns:
        figure (plotly.graph_object.Figure)
    """
    is_time_graph = column == "date_served"
    has_clicks = "clicks" in df

    with_reach = with_reach and "mobile_id" in df

    # only add reach if MAIDs are available and with_reach is True
    grouped = df.groupby([column], as_index=False, dropna=False).agg(
        {
            **{"impressions": "sum"},
            **({"clicks": "sum"} if has_clicks else dict()),
            **({"mobile_id": lambda x: x.nunique()} if with_reach else dict()),
        }
    )
    if has_clicks:
        grouped["ctr"] = grouped["clicks"] / grouped["impressions"]

    if not is_time_graph and sort_by:
        grouped = grouped.sort_values(sort_by, ascending=False)

    # Filter out dates with quasi zero impressions
    grouped = grouped[grouped["impressions"] > min_impressions]

    fig = make_subplots(
        specs=[[{"secondary_y": True}]],
        figure=go.Figure(layout=M0_LAYOUT),
    )

    w_basis = np.asarray([1000 * 3600 * 19] * len(grouped[column]))

    # Impressions
    fig.add_trace(
        go.Bar(
            name="Impressions",
            x=grouped[column],
            y=grouped["impressions"],
            marker_color=_Palette.IMPRESSIONS.value,
            offset=-w_basis / 2 if is_time_graph else -0.4,
        ),
        secondary_y=False,
    )

    # Reach
    if with_reach:
        fig.add_trace(
            go.Bar(
                name="Reach",
                x=grouped[column],
                y=grouped["mobile_id"],
                marker_color=_Palette.REACH.value,
                offset=-w_basis / 2 if is_time_graph else -0.4,
            ),
            secondary_y=False,
        )

    # CTR
    if has_clicks:
        fig.add_trace(
            go.Scatter(
                x=grouped[column],
                y=grouped["ctr"],
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
        yaxis2=dict(tickformat="0.2%", range=[0, grouped["ctr"].max() * 1.5]) if has_clicks else dict(),
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

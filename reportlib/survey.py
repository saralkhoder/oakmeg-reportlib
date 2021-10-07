from plotly import graph_objects as go

from reportlib.utils import PALETTE
from reportlib._plotly_utils import save_fig_to, TRANSPARENT_LAYOUT


def plot_bar_analysis(
    df,
    question,
    by_answers_from,
    palette=PALETTE,
    size: list = [1000, 700],
    save_to=None,
):
    # Group to MultiIndex df and normalise copy
    grouped = (
        df[[question, by_answers_from]].groupby([by_answers_from, question]).size()
    )
    normalised = grouped.groupby(level=0).apply(lambda a: a / a.sum())

    # Compute unique values for both questions
    x = grouped.index.get_level_values(0).unique()
    unique_answers = grouped.index.get_level_values(1).unique()

    # Derive inner labels
    try:
        text = [
            [
                f"<b>{round(normalised[v, a]*100)}%</b> ({grouped[v, a]})"
                for i, v in enumerate(x)
            ]
            for _, a in enumerate(unique_answers)
        ]
    except:
        text = "a"

    # Create and fill figure
    fig = go.Figure(layout=TRANSPARENT_LAYOUT)

    # Traces are bars that will be stacked
    fig.add_traces(
        [
            go.Bar(
                x=x,
                y=normalised[:, a],
                name=a,
                marker_color=palette[i],
                text=text[i],
                textposition="auto",
            )
            for i, a in enumerate(unique_answers)
        ]
    )

    fig.update_layout(
        barmode="stack",
        yaxis={"visible": False, "showgrid": False, "zeroline": False},
        width=size[0],
        height=size[1],
    )

    if save_to:
        save_fig_to(fig, save_to)

    return fig

"""Charting survey answers"""
from plotly import graph_objects as go
import pandas as pd
from reportlib.utils import PALETTE, Color
from reportlib._plotly_utils import save_fig_to, TRANSPARENT_LAYOUT


def plot_answers_funnel(survey_df, question_columns, save_to=None):
    """
    Plots a funnel graph for surveys (public.new_survey_data data structure)

    Args:
        survey_df (DataFrame): from new_survey_data table
        question_columns (str[]): columns in which responses are stored, eg. 'q1','q2'...
        save_to (str): *optional*, save as png, don't write any extension here

    Returns:
        figure (plotly.graph_object.Figure)
    """
    questions = pd.DataFrame(columns=["name", "answers"])

    # Filter questions and count answers
    for idx, question_name in enumerate(question_columns):
        # only onsider a question if answers exist
        if survey_df[question_name].notna().sum() > 0:
            questions = questions.append(
                [
                    {
                        "name": question_name,
                        "answers": survey_df[question_name].notna().sum(),
                    }
                ]
            )

    print(questions["answers"])

    # Plot figure
    fig = go.Figure(
        go.Funnel(
            y=question_columns,
            x=questions["answers"],
            # textposition="inside",
            textinfo="none",
            # + ("+value" if show_values else "")
            # + ("+percent initial" if show_percentage else ""),
            marker={"color": Color.BROWN.value},
        )
    )

    fig.update_yaxes(showticklabels=False)
    fig.update_layout(
        # title={'text': "Answers volume funnel",
        #       'xanchor': "center", 'yanchor': "top",
        #       'y':0.9, 'x':0.5},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=0, b=0, l=0, r=0),
        font_family="AppleGothic",
    )

    if save_to:
        save_fig_to(fig, save_to)

    return fig


def plot_pie_analysis(
    value_counts, palette=PALETTE, size: list = [1000, 700], save_to=None
):
    """
    Plots a simple pie chart from value counts

    Args:
        value_counts (DataFrame): already aggregated data, eg. with .value_counts()
        palette (str[]): *optional*, list of colours
        size (int[]): *optional*, figure size
        save_to (str): *optional*, save as png, don't write any extension here

    Returns:
        figure (plotly.graph_object.Figure)
    """
    fig = go.Figure(
        data=[
            go.Pie(
                labels=value_counts.index,
                direction="clockwise",
                values=value_counts.values,
                sort=False,
                marker={"colors": palette},
                texttemplate="<b>%{percent:.0%}</b><br>(%{value})",
            )
        ]
    )

    fig.update_layout(font_size=18, width=size[0], height=size[1])

    if save_to:
        save_fig_to(fig, save_to)

    return fig


def plot_bar_analysis(
    df,
    question,
    by_answers_from,
    palette=PALETTE,
    size: list = [1000, 700],
    save_to=None,
):
    """
    Plots a stacked bar chart to analyse survey answers across two axes.

    Args:
        df (DataFrame): survey answers
        question (str): what question answers to analyse
        by_answers_from (str): second analysis dimension
        palette (str[]): *optional*, list of colours
        size (int[]): *optional*, figure size
        save_to (str): *optional*, save as png, don't write any extension here

    Returns:
        figure (plotly.graph_object.Figure)
    """
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
        font_size=18,
        barmode="stack",
        yaxis={"visible": False, "showgrid": False, "zeroline": False},
        width=size[0],
        height=size[1],
    )

    if save_to:
        save_fig_to(fig, save_to)

    return fig

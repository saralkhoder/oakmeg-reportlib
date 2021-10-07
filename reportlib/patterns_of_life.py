import pandas as pd
import pycountry
import plotly.express as px
import plotly.graph_objects as go

from reportlib._plotly_utils import save_fig_to
from reportlib.utils import PALETTE


def alpha3to2(alpha3: str) -> str:
    """
    Return alpha2 ISO country code, except for IRQ which is IZ instead of IQ

    Usage:
        ``alpha3to2('SYR')``

    Args:
        alpha3 (str): ISO Alpha 3 country code
    """
    try:
        alpha2 = pycountry.countries.get(alpha_3=alpha3).alpha_2
        if alpha2 == "IQ":
            return "IZ"
        else:
            return alpha2
    except:
        print("COUNTRY NOT FOUND:", alpha3)
        raise AssertionError()


def homecountry_pie(df: pd.DataFrame, countries: list = None, save_to: str = None):
    """
    Display pie chart of home countries.

    Usage:
        ``patterns_of_life.homecountry_pie(data.lifesight, countries=['IR', 'SY', 'IQ'])``

    Args:
        df (DataFrame): a dataframe with a 'homecountry' column
        countries (list): *optional*, the list of countries (iso alpha2) to include
        save_to (str): *optional*, save as png, don't write any extension here
    """
    homecountries = df["homecountry"].dropna().apply(alpha3to2)
    if countries:
        homecountries = homecountries[homecountries.isin(countries)]
    value_counts = homecountries.value_counts()

    fig = go.Figure(
        data=[
            go.Pie(
                labels=value_counts.index,
                values=value_counts.values,
                textinfo="label+value",
                insidetextorientation="horizontal",
                marker=dict(colors=PALETTE)
            )
        ]
    )

    if save_to:
        save_fig_to(fig, save_to)

    return fig


def _home_travel_data(df):
    life = df.dropna(subset=["travelcountries"]).drop_duplicates(subset=["mobile_id"])
    life = life.reset_index()

    def parse_travelcountries(s):
        return frozenset(s.strip("{}").split(","))

    life["travelcountry"] = life["travelcountries"].apply(parse_travelcountries)
    return life[["mobile_id", "homecountry", "travelcountry"]]


def travel_sunburst(df, home_countries=None, travel_countries=None, save_to=None):
    """
    Display pie chart of home countries.

    Usage:
        ``patterns_of_life.travel_sunburst(data.lifesight, home_countries=['IQ'], travel_countries= ['IR', 'SY'])``

    Args:
        df (DataFrame): a dataframe with a 'homecountry' column
        home_countries (list): *optional*, the list of home countries (iso alpha2) to include
        travel_countries (list): *optional*, the list of travel countries (iso alpha2) to include
        save_to (str): *optional*, save as png, don't write any extension here
    """
    exploded = _home_travel_data(df).explode("travelcountry")
    grouped = exploded.groupby(["homecountry", "travelcountry"], as_index=False).agg(
        "count"
    )
    grouped["homecountry"] = grouped["homecountry"].apply(alpha3to2)
    grouped["travelcountry"] = grouped["travelcountry"].apply(alpha3to2)

    # filter if demanded
    if home_countries:
        grouped = grouped[grouped["homecountry"].isin(home_countries)]

    if travel_countries:
        grouped = grouped[grouped["travelcountry"].isin(travel_countries)]

    # build labels
    sun_data = px.sunburst(
        grouped, path=["homecountry", "travelcountry"], values="mobile_id"
    )["data"][0]

    labels = sun_data["labels"]
    parents = sun_data["parents"]
    values = sun_data["values"]

    # remove numbers from inner circle
    mask_end = sum(p is not "" for p in parents)
    labels[:mask_end] = [
        l + f" ({str(v)})" for l, v in zip(labels[:mask_end], values[:mask_end])
    ]

    fig = go.Figure(
        go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            ids=sun_data["ids"],
            branchvalues="total",
            textinfo="label",
            insidetextorientation="horizontal",
            marker=dict(colors=PALETTE),
        ),
    )

    fig.update_layout(
        font_size=18, width=400, height=400, margin=dict(l=0, r=0, t=0, b=0)
    )

    if save_to:
        save_fig_to(fig, save_to)

    return fig

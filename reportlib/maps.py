"""Module for creating Atom maps"""
import io
import pandas as pd
from enum import Enum
from pathlib import Path
from PIL import Image
import folium
from folium import plugins


class Tile(Enum):
    TERRAIN = "Stamen Terrain"
    STREETS = "https://api.mapbox.com/styles/v1/gaspardfeuvray/ckpofztgc08ys17mlpwabqxhz/tiles/256/{z}/{x}/{y}@2x?\
access_token=pk.eyJ1IjoiZ2FzcGFyZGZldXZyYXkiLCJhIjoiY2p2YzdhMHZzMWZyMzN5bWo3dTUwY2UxcSJ9.MwgCkS-8xqvM9wjQI-vjgw"
    MONOCHROME = "https://api.mapbox.com/styles/v1/gaspardfeuvray/ckrap3uup0c9717o09tntz4or/tiles/256/{z}/{x}/{y}@2x?\
access_token=pk.eyJ1IjoiZ2FzcGFyZGZldXZyYXkiLCJhIjoiY2p2YzdhMHZzMWZyMzN5bWo3dTUwY2UxcSJ9.MwgCkS-8xqvM9wjQI-vjgw"


class Cmap(Enum):
    QUALITATIVE = [
        "#1f77b4",
        "#2ca02c",
        "#ff7f0e",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
    ]


class Palette(Enum):
    AOI = "blue"


class AtomMap:
    """
    A map object with multiple layers for displaying aois, points, geojson, chloropleth, ...
    Choose the base style from `reportlib.maps.Tile`

    Returns:
        A pandas DataFrame with the query result
    """

    def __init__(self, tile: Tile):
        self.fmap = create_map(tile)
        self.layers = []
        self.bounds = {"sw": [], "ne": []}

        # Init map
        self.fmap.add_child(folium.LayerControl())
        self.fmap.add_child(folium.plugins.MeasureControl(primary_length_unit="meters"))

    def _update_bounds(self, lat: list, lon: list) -> object:
        """
        Update SW/NE bounds to include new geodata

        Returns:
            self, for chaining
        """

        def update_bound(prop, func):
            if self.bounds[prop]:
                self.bounds[prop] = [
                    func(self.bounds[prop][0], func(list(lat))),
                    func(self.bounds[prop][1], func(list(lon))),
                ]
            else:
                self.bounds[prop] = [func(list(lat)), func(list(lon))]

        update_bound("sw", min)
        update_bound("ne", max)

    def add_aois(self, aois: pd.DataFrame) -> None:
        """
        Add a layer with AOIs to display

        Args:
            aois (DataFrame): The aois to display on the map
        """
        for index, aoi in aois.iterrows():
            popup = folium.Popup(
                html=f"<b>{aoi['name']}</b></br>",
                show=False,
                sticky=True,
                max_width=500,
            )
            folium.Circle(
                [aoi["latitude"], aoi["longitude"]],
                radius=aoi["radius_km"] * 1000,
                popup=popup,
                fill_color=Palette.AOI.value,
                color=Palette.AOI.value,
                opacity=0.3,
            ).add_to(self.fmap)

        self._update_bounds(aois["latitude"], aois["longitude"])
        return self  # for serialisation

    def show(self) -> object:
        """
        Show AOIs layer on the map

        Returns:
            self, for displaying / chaining
        """
        print("todo: compute bounds and feature groups")
        print(self.bounds)
        self.fmap.fit_bounds([self.bounds["sw"], self.bounds["ne"]])
        return self.fmap


def create_map(tile: Tile) -> folium.Map:
    """
    Create an empty folium map

    Args:
        tile (Tile): the base tile to use

    Returns:
        The created folium map
    """
    return folium.Map(tiles=None).add_child(
        folium.TileLayer(tile.value, name="base_map", attr="atom")
    )


def save_map(fmap: folium.Map, to: str) -> None:
    """
    Save the map in a generated folder. Note that the process takes ~5 seconds

    Args:
        fmap (folium.Map): the map to save
        to (str): the new file name, without extension

    Returns:
        The created folium map
    """
    Path("generated").mkdir(parents=True, exist_ok=True)
    img_data = fmap._to_png(5)
    img = Image.open(io.BytesIO(img_data))
    img.save("generated/" + to + ".png")

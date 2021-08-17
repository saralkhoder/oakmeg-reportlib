"""Module for creating Atom maps"""
import io
from pathlib import Path

from enum import Enum
import pandas as pd
import numpy as np
import pygeohash
from PIL import Image
import folium
from folium import plugins
from branca import colormap as cm

from reportlib.utils import Colors


class Tile(Enum):
    TERRAIN = "Stamen Terrain"
    STREETS = "https://api.mapbox.com/styles/v1/gaspardfeuvray/ckpofztgc08ys17mlpwabqxhz/tiles/256/{z}/{x}/{y}@2x?\
access_token=pk.eyJ1IjoiZ2FzcGFyZGZldXZyYXkiLCJhIjoiY2p2YzdhMHZzMWZyMzN5bWo3dTUwY2UxcSJ9.MwgCkS-8xqvM9wjQI-vjgw"
    MONOCHROME = "https://api.mapbox.com/styles/v1/gaspardfeuvray/ckrap3uup0c9717o09tntz4or/tiles/256/{z}/{x}/{y}@2x?\
access_token=pk.eyJ1IjoiZ2FzcGFyZGZldXZyYXkiLCJhIjoiY2p2YzdhMHZzMWZyMzN5bWo3dTUwY2UxcSJ9.MwgCkS-8xqvM9wjQI-vjgw"


class _Palette(Enum):
    AOI = Colors.BLUE.value


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
        Add a layer with AOIs

        Args:
            aois (DataFrame): The aois to display on the map
        Returns:
            self, for chaining
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
                fill_color=_Palette.AOI.value,
                color=_Palette.AOI.value,
                opacity=0.3,
            ).add_to(self.fmap)

        self._update_bounds(aois["latitude"], aois["longitude"])
        return self  # for serialisation

    def add_aois_perf(
        self,
        df,
    ):
        """
        Add a layer showing performance per AOI, color represents clickthrough rate and size impressions volume

        Args:
            df (DataFrame): The performance data, must have a geohash column to locate the aois
        Returns:
            self, for chaining
        """
        # Group and compute performance
        perf = df.groupby("geohash", as_index=False).agg(
            {"impressions": "sum", "clicks": "sum", "geohash": "first"}
        )
        perf["ctr"] = perf["clicks"] / perf["impressions"]
        perf["ctr_perc"] = perf["ctr"] * 100

        minctr = perf["ctr_perc"].min()
        maxctr = perf["ctr_perc"].max()

        # Print ctr and impressions range
        print("ctr:", minctr, "-", maxctr)
        print("impressions:", perf["impressions"].min(), "-", perf["impressions"].max())

        def linmap(v, mn, mx, mn_to=0, mx_to=1):
            return (v - mn) / (mx - mn) * (mx_to - mn_to) + mn_to

        colormap = cm.LinearColormap(
            colors=["#F5A331", "#F5E214", "#35CC3F"],
            index=[minctr - 0.15, (minctr - 0.15 + maxctr) / 2, maxctr],
            vmin=minctr - 0.15,
            vmax=maxctr,
        )

        # Creates the marker for an AOI
        def marker(geohash, size, intensity):
            return folium.CircleMarker(
                pygeohash.decode(geohash),
                radius=size,
                # color=matplotlib.colors.rgb2hex(colormap(intensity)),
                # fill_color=matplotlib.colors.rgb2hex(colormap(intensity)),
                color=colormap(intensity),
                fill_color=colormap(intensity),
                opacity=1,
                fill_opacity=0.4,
            )

        for _, aoi in perf.iterrows():
            size = linmap(
                aoi["impressions"],
                perf["impressions"].min(),
                perf["impressions"].max(),
                mn_to=10,
                mx_to=25,
            )
            intensity = aoi["ctr_perc"]
            self.fmap.add_child(marker(aoi["geohash"], size, intensity))

        # Update map boundaries
        aoi_centroids = np.array(
            list(perf["geohash"].apply(lambda g: pygeohash.decode(g)))
        )
        self._update_bounds(aoi_centroids[:, 0], aoi_centroids[:, 1])
        return self

    def show(self) -> object:
        """
        Display the map

        Returns:
            self, for chaining
        """
        self.fmap.fit_bounds([self.bounds["sw"], self.bounds["ne"]])
        return self.fmap

    def save(self, to: str) -> object:
        """
        Save the map in a generated folder

        Args:
            to (str): the new file name, without extension

        Returns:
            self, for chaining
        """
        _save_map(self.fmap, to=to)
        return self.fmap


def create_map(tile: Tile) -> folium.Map:
    return folium.Map(tiles=None).add_child(
        folium.TileLayer(tile.value, name="base_map", attr="atom")
    )


def _save_map(fmap: folium.Map, to: str) -> None:
    """
    Save the map in a generated folder. Note that the process takes ~5 seconds

    Args:
        fmap (folium.Map): the map to save
        to (str): *optional*, the new file name, without extension

    Returns:
        The created folium map
    """
    Path("generated").mkdir(parents=True, exist_ok=True)
    img_data = fmap._to_png(5)
    img = Image.open(io.BytesIO(img_data))
    img.save("generated/" + to + ".png")

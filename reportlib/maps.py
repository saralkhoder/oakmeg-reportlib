"""Create modular Atom maps"""
import io
import json
from pathlib import Path
from enum import Enum

import math
import pandas as pd
import numpy as np
import pygeohash
import geojson
from PIL import Image
import folium
from folium import plugins
from branca import colormap as cm

from reportlib.utils import Color


class Tile(Enum):
    """
    Available base tiles for `reportlib.maps.AtomMap`
    """

    TERRAIN = "Stamen Terrain"
    STREETS = "https://api.mapbox.com/styles/v1/gaspardfeuvray/ckpofztgc08ys17mlpwabqxhz/tiles/256/{z}/{x}/{y}@2x?\
access_token=pk.eyJ1IjoiZ2FzcGFyZGZldXZyYXkiLCJhIjoiY2p2YzdhMHZzMWZyMzN5bWo3dTUwY2UxcSJ9.MwgCkS-8xqvM9wjQI-vjgw"
    MONOCHROME = "https://api.mapbox.com/styles/v1/gaspardfeuvray/ckrap3uup0c9717o09tntz4or/tiles/256/{z}/{x}/{y}@2x?\
access_token=pk.eyJ1IjoiZ2FzcGFyZGZldXZyYXkiLCJhIjoiY2p2YzdhMHZzMWZyMzN5bWo3dTUwY2UxcSJ9.MwgCkS-8xqvM9wjQI-vjgw"


class _Palette(Enum):
    AOI = Color.BLUE.value
    CIRCLE = Color.BROWN.value


class AtomMap:
    """
    A map object with multiple layers for displaying aois, points, geojson, ...
    Choose the base style from `reportlib.maps.Tile`

    Returns:
        A pandas DataFrame with the query result
    """

    def __init__(self, tile: Tile):
        self.fmap = _create_map(tile)
        self.layers = []
        self.bounds = {"sw": [], "ne": []}

        # Init map
        # self.fmap.add_child(folium.LayerControl())

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
                opacity=0.5,
            ).add_to(self.fmap)

        self._update_bounds(aois["latitude"], aois["longitude"])
        return self  # for serialisation

    def add_circles(self, df: pd.DataFrame) -> None:
        """
        Add a layer with circles

        Args:
            df (DataFrame): Must have latitude, longitude and radius (in km) columns, optionally a name

        Returns:
            self, for chaining
        """

        for index, item in df.iterrows():
            folium.Circle(
                [item["latitude"], item["longitude"]],
                radius=item["radius"] * 1000,
                popup=folium.Popup(
                    html=f"<b>{item['name']}</b></br>",
                    show=False,
                    sticky=True,
                    max_width=500,
                )
                if "name" in df.columns
                else None,
                fill_color=_Palette.CIRCLE.value,
                color=_Palette.CIRCLE.value,
                opacity=0.5,
            ).add_to(self.fmap)

        self._update_bounds(df["latitude"], df["longitude"])
        return self  # for serialisation

    # TODO: make this work consistently, edit parameters
    def add_aois_perf(
        self,
        df: pd.DataFrame,
        ctr_color_offset: int = 0,
        markers_size_range: list = [10, 25],
    ):
        """
        Add a layer showing performance per AOI, color represents clickthrough rate and size impressions volume

        Args:
            df (DataFrame): The performance data, must have a geohash column to locate the aois
            ctr_color_offset (int): *optional*, by how much to offset the lower bound of the ctr range, will make
            all markers greener
            markers_size_range ([int, int]): *optional*, the range of marker size

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
        print("ctr range for color:", minctr - ctr_color_offset, "-", maxctr)
        print(
            "impressions range:",
            perf["impressions"].min(),
            "-",
            perf["impressions"].max(),
        )

        def linmap(v, mn, mx, mn_to=0, mx_to=1):
            return (v - mn) / (mx - mn) * (mx_to - mn_to) + mn_to

        colormap = cm.LinearColormap(
            colors=["#0047AB", "#F5E214", "#35CC3F"],
            index=[
                minctr - ctr_color_offset,
                (minctr - ctr_color_offset + maxctr) / 2,
                maxctr,
            ],
            vmin=minctr - ctr_color_offset,
            vmax=maxctr,
        )

        # Creates the marker for an AOI
        def marker(geohash, size, intensity):
            return folium.CircleMarker(
                pygeohash.decode(geohash),
                radius=math.sqrt(size),
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
                mn_to=markers_size_range[0],
                mx_to=markers_size_range[1],
            )
            intensity = aoi["ctr_perc"]
            self.fmap.add_child(marker(aoi["geohash"], size, intensity))

        # Update map boundaries
        aoi_centroids = np.array(
            list(perf["geohash"].apply(lambda g: pygeohash.decode(g)))
        )
        self._update_bounds(aoi_centroids[:, 0], aoi_centroids[:, 1])
        return self

    def add_points(
        self,
        df: pd.DataFrame,
        lat: str = "latitude",
        lon: str = "longitude",
        color: Color = Color.BLUE,
        size: int = 1,
        plot_max: int = 10000,
    ):
        """
        Add a layer showing points from a dataframe

        Args:
            df (DataFrame): The input data
            lat (str): *optional*, name of the column containing latitudes
            lon (str): *optional*, name of the column containing longitudes
            color (`reportlib.utils.Color`): *optional*, color of the points
            size (int): *optional*, size of the points
            plot_max (int): *optional*, cap on the number of points to print, sampled randomly if exceeded

        Returns:
            self, for chaining
        """
        if df.empty:
            return self

        assert (
            lat in df.columns and lon in df.columns
        ), "lat/lon not found, check dataframe or use lat and lon paramaters"
        df = df.dropna(subset=[lat, lon])

        # apply plot_max cap
        if len(df) > plot_max:
            print("df has", len(df), "rows, capping at", plot_max, "!")
            df = df.sample(plot_max)
        else:
            print(len(df), "points added")
            df = df

        # add points to the map
        df.apply(
            lambda row: folium.CircleMarker(
                [row[lat], row[lon]],
                radius=size,
                color=color.value,
                fill=True,
                fill_opacity=1,
                opacity=1,
                popup=folium.Popup(
                    html=f"MAID: {row['mobile_id']}, LAT/LON: {row[lat]}, {row[lon]}, {row['date_served']}",
                    max_width=620,
                ),  # TODO: remove {row['device id']}
            ).add_to(self.fmap),
            axis=1,
        )

        if not df.empty:
            self._update_bounds(df[lat], df[lon])
        return self

    def add_heatmap(
        self,
        df,
        lat="latitude",
        lon="longitude",
        radius=15,
        plot_max=2000000,
    ):
        """
        Add a heatmap layer from a set of points

        Args:
            df (DataFrame): The input data
            lat (str): *optional*, name of the column containing latitudes
            lon (str): *optional*, name of the column containing longitudes
            radius (int): *optional*, radius for the area of influence of each point
            plot_max (int): *optional*, cap on the number of points to print, sampled randomly if exceeded

        Returns:
            self, for chaining
        """
        if len(df) > plot_max:
            df = df.sample(plot_max)

        print("added", len(df), "points to heatmap")

        heat_data = df.dropna(subset=[lat, lon], axis=0)

        sw = heat_data[[lat, lon]].min().values.tolist()
        ne = heat_data[[lat, lon]].max().values.tolist()

        heat_data = [[row[lat], row[lon]] for index, row in heat_data.iterrows()]

        self.fmap.add_child(plugins.HeatMap(heat_data, radius=radius, control=False))

        if not df.empty:
            self._update_bounds(df[lat], df[lon])
        return self

    def add_geojson(self, obj: json, color: Color = Color.BLUE):
        """
        Add a layer with geojson file

        ! geojson polygons must follow the **right-hand rule** (counter-clockwise) !

        ! geojson format uses **(longitude, latitude)** in that order !

        Args:
            obj (json): The geojson object
            color (`reportlib.utils.Color`): *optional*, color of the geojson features

        Returns:
            self, for chaining
        """
        # handle case
        if not obj:
            print("None passed as geojson object")
            return self

        if "features" in obj and len(obj["features"]) == 0:
            print("Empty geojson")
            return self

        geo = folium.GeoJson(
            obj,
            name="blah",
            style_function=lambda x: {
                "fillColor": color.value,
                "color": color.value,
                "fillOpacity": 0.1,
            },
        )
        self.fmap.add_child(geo)

        # update bounds
        if "features" in obj:
            for f in obj["features"]:
                coords = np.array(list(geojson.utils.coords(f)))
                self._update_bounds(coords[:, 1], coords[:, 0])
        else:
            coords = np.array(list(geojson.utils.coords(obj)))
            self._update_bounds(coords[:, 1], coords[:, 0])
        return self

    def show(self) -> object:
        """
        Display the map

        Returns:
            self, for chaining
        """
        self.fmap.fit_bounds([self.bounds["sw"], self.bounds["ne"]])
        return self.fmap

    def save(self, to: str, html=False) -> object:
        """
        Save the map in a generated folder

        Args:
            to (str): the new file name, without extension
            html (bool): *optional*, wether to save the map as an html file

        Returns:
            self, for chaining
        """
        _save_map(self.fmap, to=to, html=html)
        return self


def _create_map(tile: Tile) -> folium.Map:
    return folium.Map(tiles=None).add_child(
        folium.TileLayer(tile.value, name="base_map", attr="atom")
    )


def _save_map(fmap: folium.Map, to: str, html=False) -> None:
    """
    Save the map in a generated folder. Note that the process takes ~5 seconds

    Args:
        fmap (folium.Map): the map to save
        to (str): *optional*, the new file name, without extension
        html (bool): *optional*, wether to save the map as an html file

    Returns:
        The created folium map
    """
    Path("generated").mkdir(parents=True, exist_ok=True)

    if html:
        fmap.save("generated/" + to + ".html")
    else:
        img_data = fmap._to_png(5)
        img = Image.open(io.BytesIO(img_data))
        img.save("generated/" + to + ".png")

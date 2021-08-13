import io
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


class AtomMap(folium.Map):
    def __init__(self, tile):
        self.fmap = create_map(tile)
        self.layers = []
        self.bounds = {"sw": [], "ne": []}

        # Init map
        self.fmap.add_child(folium.LayerControl())
        self.fmap.add_child(folium.plugins.MeasureControl(primary_length_unit="meters"))

    # Update SW/NE bounds to include new geodata
    def _update_bounds(self, lat, lon):
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

    def add_aois(self, aois):
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

    def show(self):
        print("todo: compute bounds and feature groups")
        print(self.bounds)
        self.fmap.fit_bounds([self.bounds["sw"], self.bounds["ne"]])
        return self.fmap


def create_map(tile):
    return folium.Map(tiles=None).add_child(
        folium.TileLayer(tile.value, name="base_map", attr="atom")
    )


def save_map(fmap, to):
    Path("generated").mkdir(parents=True, exist_ok=True)
    img_data = fmap._to_png(5)
    img = Image.open(io.BytesIO(img_data))
    img.save("generated/" + to + ".png")


# Oakmeg reporting library
## Installation
Install the oakmeg **reportlib** package 
```bash
pip install git+ssh://git@github.com/MCS-Atom/oakmeg-reportlib.git
```

## Usage
Import and open documentation
```python
from reportlib import datamodule, performance, maps, utils
utils.open_documentation()
```

Load **campaign data**
```python
data = datamodule.Data('path-to-secrets.yaml', 'NT28')
data.load_all()
```

Display **targeting map**
```python
maps.AtomMap(maps.Tile.TERRAIN).add_aois(data.aois).show()
```

Compute **overall performance** and **performance by AOI**
```python
performance.overview(data.dash)
```
```python
performance.overview(data.dash, by='aoi')
```

Display **daily impressions and CTR**
```python
performance.plot_by(data.dash, 'date_served')
```

Look in the documentation for a full list of functionalities.

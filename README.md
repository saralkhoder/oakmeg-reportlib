
# Oakmeg reporting library
## Installation
Install the oakmeg **reportlib** package 
```bash
pip install git+https://github.com/saralkhoder/oakmeg-reportlib.git
```

or in jupyter notebook

```python
import sys
!{sys.executable} -m pip install git+https://github.com/saralkhoder/oakmeg-reportlib.git
```

eventually use --ignore-installed after pip install


*If you have not switched to SSH authentication yet, follow [this page](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh) first*

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

secrets.yaml file structure
```yaml
rds:
  dbuser: <usr>
  dbpassword: <pwd>
  dbhost: <host>
  dbport: <port>
  dbdatabase: postgres
```

Display **targeting map**
```python
maps.AtomMap(maps.Tile.TERRAIN).add_aois(data.aois).show()
```

Compute campaign **overall performance**
```python
performance.overview(data.dash)
```

Display **daily impressions and CTR**
```python
performance.plot_by(data.dash, 'date_served')
```

Save performance per aoi as a **PowerPoint table**
```python
ppt.save_as_table(performance.overview(data.dash, by='aoi'), to='perf_by_aoi')
```

Look in the documentation for a full list of functionalities !

## Contributing
```bash
git clone git@github.com:MCS-Atom/oakmeg-reportlib.git
```

Create new branch (master is protected)
```bash
git checkout -b new_branch_name
```

Create and push one commit for each feature
```bash
git add file1 file2 file3
git commit -m 'blahblah'
git push
```

Create a pull request for this branch and submit code for review.

Got to [this page](https://docs.github.com/en/github/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-branches) to learn more about branches.

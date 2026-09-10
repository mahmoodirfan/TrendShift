# TrendShift
### Locate the strongest abrupt shift.

A QGIS Processing plugin that applies Pettitt’s non-parametric change-point test to time-ordered raster stacks and maps the timing, magnitude and direction of a candidate shift.

**QGIS 3.16+ declared in plugin metadata** · Python · QGIS Processing

[Detailed guide](docs/guide.md) · [Report a problem](https://github.com/mahmoodirfan/TrendShift/issues) · [Contribute](CONTRIBUTING.md)

## Start here

1. Load aligned rasters in chronological order. The algorithm reads **band 1 of each layer**.
2. Open **Processing Toolbox → TrendShift → Change Point Analysis → Raster Change Point Detection**.
3. Set the minimum segment length, significance threshold, first time value and time interval.
4. Choose a new output folder and run.
5. Inspect change magnitude and p-value alongside the change-time map. A candidate split is not automatically evidence of a real disturbance.

## Install

In QGIS, open **Plugins → Manage and Install Plugins** and search for **TrendShift**. If a compatible listing is unavailable, install from this repository:

1. Download and extract the source archive.
2. Rename the extracted plugin directory to `TrendShift` (remove a branch suffix such as `-main`).
3. In QGIS, open **Settings → User Profiles → Open Active Profile Folder**.
4. Copy the directory into `python/plugins/`, creating those subfolders if needed. `metadata.txt` and `__init__.py` must sit directly inside `python/plugins/TrendShift/`.
5. Restart QGIS and enable **TrendShift** in the plugin manager.

A GitHub source ZIP is not necessarily a correctly packaged QGIS install ZIP. Use the extracted-folder steps above for source downloads. Declared minimum versions are not a substitute for testing your QGIS build.

## What you get

| Output | Meaning |
| :--- | :--- |
| `change_step.tif` | First post-change layer, indexed from 1 |
| `change_time.tif` | First time value + (change step − 1) × interval |
| `change_magnitude.tif` | After-change mean minus before-change mean |
| `direction.tif` | −1 decrease, 0 no mean shift, +1 increase |
| `p_value.tif`, `significance_mask.tif` | Approximate p-value and thresholded mask |
| `pettitt_k.tif` | Pettitt K statistic |
| `before_mean.tif`, `after_mean.tif` | Means on either side of the candidate split |
| `trendshift_report.txt` | Processing settings and interpretation notes |

## Before interpreting results

- Use the same CRS, extent, dimensions and pixel alignment across rasters. TrendShift validates alignment before analysis.
- Two layers are accepted, but very short stacks are exploratory rather than strong statistical evidence.
- An infeasible minimum segment length is reduced automatically; read the Processing log.
- Pixels with a missing or non-finite observation are excluded.
- One dominant change point is estimated per pixel. This is not a multiple-breakpoint model or a causal attribution method.
- P-values are approximate; temporal dependence and spatial multiple testing need separate consideration.
- The stack is loaded into memory. Start with a small area.

## Documentation & support

The [detailed guide](docs/guide.md) contains extended settings, interpretation examples and workflow notes.

For a bug report, include your QGIS version, operating system, plugin version, parameters, Processing log and a small shareable example. See [contribution guidance](CONTRIBUTING.md).

## Related tools

[RasterTrend](https://github.com/mahmoodirfan/RasterTrend) · [TrendShift](https://github.com/mahmoodirfan/TrendShift) · [OpenGeoEnrich](https://github.com/mahmoodirfan/OpenGeoEnrich) · [spatialdrought](https://github.com/mahmoodirfan/spatialdrought)

## Author & license

**[Irfan Mahmood](https://github.com/mahmoodirfan)** · Remote Sensing & GIS Specialist  
[Email](mailto:irfan-mahmood@outlook.com) · [License](LICENSE)

For research use, cite the repository and record the version or commit you used. Existing citation details are retained in the detailed guide where provided.

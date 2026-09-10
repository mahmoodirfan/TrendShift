# Detailed guide

[← Back to the overview](../README.md)

Read the current implementation notes in the overview before interpreting results.

# TrendShift – Raster Change Point Detection for QGIS

[![QGIS](https://img.shields.io/badge/QGIS-3.16%2B-green)](https://qgis.org)
[![License](https://img.shields.io/badge/License-GPL--2.0-blue)](../LICENSE)

**TrendShift** is a QGIS Processing plugin for pixel-wise abrupt change point detection in raster time-series stacks. It uses **Pettitt's non-parametric change point test** to estimate where each pixel experienced its strongest temporal shift.

TrendShift is designed as a companion to **RasterTrend**:

- **RasterTrend** answers: *Is there a gradual monotonic trend?*
- **TrendShift** answers: *When did the strongest abrupt shift happen?*

---

## Version 1.1

This is a clean QGIS/GitHub-ready release. It supports raster stacks with 2 or more layers, uses a default minimum segment length of 1 for exploratory short-stack testing, automatically adjusts infeasible segment-length settings, validates raster alignment before processing, and writes all outputs as compressed GeoTIFFs.

---

## Key Features

- Pixel-wise abrupt change point detection from time-ordered raster stacks
- Pettitt's non-parametric test; no normality assumption required
- Change step and mapped change-time output
- Change magnitude output: after-change mean minus before-change mean
- Direction raster: decrease, no shift, increase
- P-value and significance mask outputs
- Before/after mean rasters for interpretation
- Raster alignment validation before analysis
- Integrated into the **QGIS Processing Toolbox**
- Works in QGIS batch mode and Model Builder

---

## Outputs

| File | Description |
|------|-------------|
| `change_step.tif` | First post-change raster step using 1-based indexing |
| `change_time.tif` | Time value of first post-change raster based on user-defined start value and interval |
| `change_magnitude.tif` | After-change mean minus before-change mean |
| `direction.tif` | -1 = decrease, 0 = no mean shift, +1 = increase |
| `p_value.tif` | Approximate Pettitt test p-value |
| `significance_mask.tif` | 1 = significant shift, 0 = not significant |
| `pettitt_k.tif` | Pettitt K statistic |
| `before_mean.tif` | Mean before detected change point |
| `after_mean.tif` | Mean after detected change point |
| `trendshift_report.txt` | Plain-text processing report and interpretation notes |

---

## Installation

### Manual Installation

1. Download the plugin zip file.
2. Open QGIS.
3. Go to **Plugins → Manage and Install Plugins → Install from ZIP**.
4. Select `TrendShift.zip`.
5. Enable **TrendShift** from the installed plugins list.

### Developer Installation

Copy the `TrendShift` folder to your QGIS plugin directory:

Use **Settings → User Profiles → Open Active Profile Folder**, then open or create `python/plugins/`. This handles custom profiles and OS-specific paths.

Restart QGIS and enable the plugin.

---

## Usage

1. Open **Processing Toolbox**.
2. Navigate to **TrendShift → Change Point Analysis → Raster Change Point Detection**.
3. Select input raster layers in chronological order.
4. Set:
   - **Minimum segment length**: minimum number of rasters before and after the change point.
   - **Significance threshold**: usually `0.05`.
   - **Time value of first raster**: e.g. `2001` for annual rasters starting in 2001.
   - **Time interval**: e.g. `1` for annual rasters, `0.083333` for monthly rasters represented in decimal years.
   - **Output folder**.
5. Click **Run**.

---

## Interpretation Example

Suppose the input rasters represent annual NDVI from 2001 to 2024.

- Set **Time value of first raster** = `2001`
- Set **Time interval** = `1`

If a pixel has:

- `change_step = 12`
- `change_time = 2012`
- `change_magnitude = -0.18`
- `direction = -1`
- `p_value = 0.02`

This means the strongest detected shift occurs at the first post-change layer corresponding to **2012**, the post-change mean is **0.18 NDVI units lower** than the pre-change mean, and the shift is statistically significant at p ≤ 0.05.

---

## Input Requirements

- All rasters must have the same:
  - CRS
  - extent
  - pixel size
  - rows and columns
  - grid alignment
- Input layers must be ordered chronologically.
- At least 2 rasters are allowed.
- Very short stacks (2–4 rasters) can run, but outputs should be treated as exploratory change indicators rather than strong statistical evidence.
- If the selected minimum segment length is too high for the number of rasters, TrendShift automatically reduces it to the maximum feasible value and reports this in the log.
- The method is intended for continuous or ordinal raster time series such as NDVI, precipitation, temperature, LST, water indices, or productivity metrics.
- For categorical land-cover class transitions, use a transition matrix or classified raster change workflow instead.

---

## Statistical Method

TrendShift uses **Pettitt's test**, a rank-based, non-parametric test for detecting a single abrupt change point in a time series. The method identifies the time step where the difference between the distributions before and after the split is strongest.

The plugin reports the candidate split with the largest absolute Pettitt statistic and estimates an approximate p-value.

---

## Example Applications

- NDVI disturbance year mapping
- Rangeland productivity shift detection
- Forest disturbance and recovery timing
- Vegetation collapse after drought
- Rainfall or temperature regime shift analysis
- Surface water index shift mapping
- Land surface temperature shift detection
- Environmental monitoring and early warning products

---

## Limitations

- Detects one dominant change point per pixel.
- Does not model multiple breakpoints in the same time series.
- Loads the raster stack into memory; very large stacks may require tiling in future versions.
- P-values are approximate and should be interpreted with domain knowledge.
- The plugin does not automatically correct for spatial multiple testing.

---

## Citation

If you use TrendShift in research or operational work, please cite:

```text
Mahmood, I. (2026). TrendShift: A QGIS Plugin for Pixel-wise Change Point Detection in Raster Time Series.
GitHub: https://github.com/mahmoodirfan/TrendShift
```

---

## Author

**Irfan Mahmood**  
Remote Sensing & GIS Specialist  
Email: irfan-mahmood@outlook.com  
GitHub: https://github.com/mahmoodirfan

---

## License

GNU General Public License v2.0 — see [LICENSE](../LICENSE)

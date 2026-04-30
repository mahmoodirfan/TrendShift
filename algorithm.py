import os
import numpy as np
from osgeo import gdal

from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFolderDestination,
    QgsProcessingException,
    QgsRasterLayer,
    QgsProject,
    QgsProcessingContext,
)


class TrendShiftAlgorithm(QgsProcessingAlgorithm):

    INPUT_LAYERS = 'INPUT_LAYERS'
    MIN_SEGMENT_LENGTH = 'MIN_SEGMENT_LENGTH'
    SIG_THRESHOLD = 'SIG_THRESHOLD'
    START_VALUE = 'START_VALUE'
    TIME_INTERVAL = 'TIME_INTERVAL'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                self.INPUT_LAYERS,
                'Input raster layers (time-ordered)',
                QgsProcessing.TypeRaster
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MIN_SEGMENT_LENGTH,
                'Minimum segment length before/after change point',
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=1,
                minValue=1,
                maxValue=10000
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.SIG_THRESHOLD,
                'Significance threshold (p-value)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.05,
                minValue=0.001,
                maxValue=0.5
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.START_VALUE,
                'Time value of first raster (e.g. 2001, 1, or 0)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.TIME_INTERVAL,
                'Time interval between rasters (e.g. 1 for annual, 0.0833 for monthly years)',
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0,
                minValue=0.000001
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER,
                'Output folder'
            )
        )

    def _open_reference(self, path):
        ds = gdal.Open(path)
        if ds is None:
            raise QgsProcessingException(f'Cannot open raster: {path}')
        info = {
            'cols': ds.RasterXSize,
            'rows': ds.RasterYSize,
            'geotransform': ds.GetGeoTransform(),
            'projection': ds.GetProjection(),
            'band_count': ds.RasterCount,
            'dtype': ds.GetRasterBand(1).DataType,
        }
        ds = None
        return info

    def _validate_raster_alignment(self, layers, ref_info, feedback):
        tolerance = 1e-9
        for i, layer in enumerate(layers):
            path = layer.source()
            ds = gdal.Open(path)
            if ds is None:
                raise QgsProcessingException(f'Cannot open raster: {path}')

            if ds.RasterXSize != ref_info['cols'] or ds.RasterYSize != ref_info['rows']:
                raise QgsProcessingException(
                    f'Raster size mismatch at layer {i + 1}: {os.path.basename(path)}. '
                    f'Expected {ref_info["cols"]} x {ref_info["rows"]}, got {ds.RasterXSize} x {ds.RasterYSize}.'
                )

            if ds.RasterCount < 1:
                raise QgsProcessingException(f'Raster has no bands: {path}')

            gt = ds.GetGeoTransform()
            for a, b in zip(gt, ref_info['geotransform']):
                if abs(a - b) > tolerance:
                    raise QgsProcessingException(
                        f'Raster geotransform mismatch at layer {i + 1}: {os.path.basename(path)}. '
                        'All rasters must have identical extent, origin, pixel size, and alignment.'
                    )

            proj = ds.GetProjection()
            if proj != ref_info['projection']:
                raise QgsProcessingException(
                    f'Raster CRS/projection mismatch at layer {i + 1}: {os.path.basename(path)}. '
                    'All rasters must use the same CRS.'
                )
            ds = None

        feedback.pushInfo('Raster alignment check passed: size, geotransform, and CRS match.')

    def _write_float_raster(self, path, array_flat, rows, cols, geotransform, projection, description):
        driver = gdal.GetDriverByName('GTiff')
        ds_out = driver.Create(
            path,
            cols,
            rows,
            1,
            gdal.GDT_Float32,
            options=['COMPRESS=LZW', 'TILED=YES', 'BIGTIFF=IF_SAFER']
        )
        ds_out.SetGeoTransform(geotransform)
        ds_out.SetProjection(projection)
        band = ds_out.GetRasterBand(1)
        band.WriteArray(array_flat.reshape(rows, cols).astype(np.float32))
        band.SetNoDataValue(-9999.0)
        band.SetDescription(description)
        band.FlushCache()
        ds_out.FlushCache()
        ds_out = None

    def _make_report(self, out_dir, n_layers, n_pixels, n_valid, sig_thr, min_seg, start_value, interval, outputs):
        report_path = os.path.join(out_dir, 'trendshift_report.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('TrendShift - Raster Change Point Detection Report\n')
            f.write('================================================\n\n')
            f.write('Method: Pettitt non-parametric change point test\n')
            f.write(f'Time steps: {n_layers}\n')
            f.write(f'Total pixels: {n_pixels}\n')
            f.write(f'Valid pixels: {n_valid}\n')
            f.write(f'Minimum segment length: {min_seg}\n')
            f.write(f'Significance threshold: {sig_thr}\n')
            f.write(f'First raster time value: {start_value}\n')
            f.write(f'Time interval: {interval}\n\n')
            f.write('Output files:\n')
            for filename, description in outputs:
                f.write(f'- {filename}: {description}\n')
            f.write('\nInterpretation notes:\n')
            f.write('- change_step.tif uses 1-based indexing and represents the first post-change raster.\n')
            f.write('- change_time.tif = first_time_value + (change_step - 1) * time_interval.\n')
            f.write('- change_magnitude.tif = after_mean - before_mean. Positive values indicate increase after the change point.\n')
            f.write('- direction.tif values: -1 = decrease, 0 = no mean shift, +1 = increase.\n')
            f.write('- p_value.tif is the approximate Pettitt test p-value.\n')
        return report_path

    def processAlgorithm(self, parameters, context, feedback):
        from .change_point_engine import pettitt_change_point_vectorized

        layers = self.parameterAsLayerList(parameters, self.INPUT_LAYERS, context)
        min_seg = self.parameterAsInt(parameters, self.MIN_SEGMENT_LENGTH, context)
        sig_thr = self.parameterAsDouble(parameters, self.SIG_THRESHOLD, context)
        start_value = self.parameterAsDouble(parameters, self.START_VALUE, context)
        interval = self.parameterAsDouble(parameters, self.TIME_INTERVAL, context)
        out_dir = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)

        if len(layers) < 2:
            raise QgsProcessingException('At least 2 raster layers are required. More layers are strongly recommended for reliable change-point inference.')

        requested_min_seg = min_seg
        max_feasible_min_seg = max(1, len(layers) // 2)
        if min_seg > max_feasible_min_seg:
            feedback.reportError(
                f'Minimum segment length={requested_min_seg} is too high for {len(layers)} rasters. '
                f'Using {max_feasible_min_seg} instead so the analysis can proceed.'
            )
            min_seg = max_feasible_min_seg

        ref_path = layers[0].source()
        ref = self._open_reference(ref_path)
        rows = ref['rows']
        cols = ref['cols']
        n_pixels = rows * cols
        n_layers = len(layers)

        feedback.pushInfo(f'Raster size: {cols} x {rows} = {n_pixels:,} pixels')
        feedback.pushInfo(f'Time steps : {n_layers}')
        feedback.pushInfo('Validating raster alignment...')
        self._validate_raster_alignment(layers, ref, feedback)

        estimated_mb = (n_layers * n_pixels * 4) / (1024 ** 2)
        feedback.pushInfo(f'Estimated stack memory: {estimated_mb:,.1f} MB before analysis overhead')
        feedback.pushInfo('Loading raster stack...')

        stack = np.full((n_layers, n_pixels), np.nan, dtype=np.float32)

        for i, layer in enumerate(layers):
            if feedback.isCanceled():
                return {}
            ds = gdal.Open(layer.source())
            if ds is None:
                raise QgsProcessingException(f'Cannot open raster: {layer.source()}')
            band = ds.GetRasterBand(1)
            arr = band.ReadAsArray().astype(np.float32).ravel()
            nd = band.GetNoDataValue()
            if nd is not None:
                arr[arr == nd] = np.nan
            arr[~np.isfinite(arr)] = np.nan
            stack[i, :] = arr
            ds = None
            feedback.setProgress(int(20 * (i + 1) / n_layers))

        valid_mask = ~np.any(np.isnan(stack), axis=0)
        n_valid = int(valid_mask.sum())
        feedback.pushInfo(f'Valid pixels: {n_valid:,} / {n_pixels:,}')

        if n_valid == 0:
            raise QgsProcessingException('No valid pixels found. Check NoData values and raster overlap.')

        data_valid = stack[:, valid_mask].astype(np.float64)

        feedback.pushInfo('Running Pettitt change point test...')
        feedback.setProgress(30)

        (
            change_step,
            k_stat,
            p_value,
            direction,
            magnitude,
            before_mean,
            after_mean,
        ) = pettitt_change_point_vectorized(data_valid, min_segment_length=min_seg)

        change_time = start_value + ((change_step - 1.0) * interval)
        significance = (p_value <= sig_thr).astype(np.float32)

        feedback.setProgress(75)
        feedback.pushInfo('Reconstructing spatial outputs...')

        outputs_arrays = {
            'change_step': np.full(n_pixels, -9999.0, dtype=np.float32),
            'change_time': np.full(n_pixels, -9999.0, dtype=np.float32),
            'change_magnitude': np.full(n_pixels, -9999.0, dtype=np.float32),
            'direction': np.full(n_pixels, -9999.0, dtype=np.float32),
            'p_value': np.full(n_pixels, -9999.0, dtype=np.float32),
            'significance_mask': np.full(n_pixels, -9999.0, dtype=np.float32),
            'pettitt_k': np.full(n_pixels, -9999.0, dtype=np.float32),
            'before_mean': np.full(n_pixels, -9999.0, dtype=np.float32),
            'after_mean': np.full(n_pixels, -9999.0, dtype=np.float32),
        }

        outputs_arrays['change_step'][valid_mask] = change_step.astype(np.float32)
        outputs_arrays['change_time'][valid_mask] = change_time.astype(np.float32)
        outputs_arrays['change_magnitude'][valid_mask] = magnitude.astype(np.float32)
        outputs_arrays['direction'][valid_mask] = direction.astype(np.float32)
        outputs_arrays['p_value'][valid_mask] = p_value.astype(np.float32)
        outputs_arrays['significance_mask'][valid_mask] = significance.astype(np.float32)
        outputs_arrays['pettitt_k'][valid_mask] = k_stat.astype(np.float32)
        outputs_arrays['before_mean'][valid_mask] = before_mean.astype(np.float32)
        outputs_arrays['after_mean'][valid_mask] = after_mean.astype(np.float32)

        os.makedirs(out_dir, exist_ok=True)

        output_specs = [
            ('change_step.tif', 'change_step', 'First post-change raster step, 1-based'),
            ('change_time.tif', 'change_time', 'Estimated time value of first post-change raster'),
            ('change_magnitude.tif', 'change_magnitude', 'After mean minus before mean'),
            ('direction.tif', 'direction', '-1 decrease, 0 no shift, +1 increase'),
            ('p_value.tif', 'p_value', 'Approximate Pettitt test p-value'),
            ('significance_mask.tif', 'significance_mask', f'Significant shift mask, p <= {sig_thr}'),
            ('pettitt_k.tif', 'pettitt_k', 'Pettitt K statistic'),
            ('before_mean.tif', 'before_mean', 'Mean before detected change point'),
            ('after_mean.tif', 'after_mean', 'Mean after detected change point'),
        ]

        feedback.pushInfo('Writing output rasters...')
        out_paths = []
        for filename, key, description in output_specs:
            if feedback.isCanceled():
                return {}
            path = os.path.join(out_dir, filename)
            self._write_float_raster(
                path,
                outputs_arrays[key],
                rows,
                cols,
                ref['geotransform'],
                ref['projection'],
                description
            )
            out_paths.append(path)
            feedback.pushInfo(f'  Written: {filename}')

        report_path = self._make_report(
            out_dir,
            n_layers,
            n_pixels,
            n_valid,
            sig_thr,
            min_seg,
            start_value,
            interval,
            [(filename, desc) for filename, _, desc in output_specs]
        )
        feedback.pushInfo(f'  Written: {os.path.basename(report_path)}')

        feedback.setProgress(92)
        for path in out_paths:
            name = os.path.splitext(os.path.basename(path))[0]
            layer = QgsRasterLayer(path, name)
            if layer.isValid():
                context.temporaryLayerStore().addMapLayer(layer)
                context.addLayerToLoadOnCompletion(
                    layer.id(),
                    QgsProcessingContext.LayerDetails(name, QgsProject.instance(), name)
                )

        feedback.setProgress(100)
        feedback.pushInfo('TrendShift analysis complete.')

        return {'OUTPUT_FOLDER': out_dir}

    def name(self):
        return 'raster_change_point_detection'

    def displayName(self):
        return 'Raster Change Point Detection'

    def group(self):
        return 'Change Point Analysis'

    def groupId(self):
        return 'change_point_analysis'

    def shortHelpString(self):
        return """
<h3>TrendShift – Raster Change Point Detection</h3>
<p>Detects abrupt temporal shifts in a time-ordered raster stack using Pettitt's non-parametric change point test.</p>

<h4>What it answers</h4>
<p>For each pixel, TrendShift estimates where the strongest abrupt shift occurs in the time series and whether that shift is statistically significant.</p>

<h4>Outputs</h4>
<ul>
  <li><b>change_step.tif</b> – first post-change raster step using 1-based indexing</li>
  <li><b>change_time.tif</b> – mapped time value based on first raster value and interval</li>
  <li><b>change_magnitude.tif</b> – after-change mean minus before-change mean</li>
  <li><b>direction.tif</b> – -1 decrease, 0 no mean shift, +1 increase</li>
  <li><b>p_value.tif</b> – approximate Pettitt test p-value</li>
  <li><b>significance_mask.tif</b> – 1 = significant shift, 0 = not significant</li>
  <li><b>pettitt_k.tif</b> – Pettitt K statistic</li>
  <li><b>before_mean.tif</b> and <b>after_mean.tif</b> – segment means around the detected shift</li>
</ul>

<h4>Input requirements</h4>
<ul>
  <li>All input rasters must have identical rows, columns, CRS, extent, pixel size, and alignment</li>
  <li>Input layers must be ordered chronologically</li>
  <li>At least 2 rasters are allowed. With very short stacks, results are exploratory only; 8+ rasters are recommended for reliable inference.</li>
  <li>The method is intended for continuous or ordinal raster time series, not categorical class-code transitions</li>
</ul>

<h4>Example applications</h4>
<ul>
  <li>NDVI disturbance year mapping</li>
  <li>Rangeland productivity shift detection</li>
  <li>Forest disturbance and recovery timing</li>
  <li>Rainfall, temperature, LST, or drought-index shift analysis</li>
  <li>Water-index regime shift mapping</li>
</ul>

<h4>Author</h4>
<p>Irfan Mahmood – Remote Sensing &amp; GIS Specialist<br>
<a href="https://github.com/mahmoodirfan">github.com/mahmoodirfan</a></p>
        """

    def createInstance(self):
        return TrendShiftAlgorithm()

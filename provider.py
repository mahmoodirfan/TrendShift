import os
from qgis.core import QgsProcessingProvider
from .algorithm import TrendShiftAlgorithm


class TrendShiftProvider(QgsProcessingProvider):

    def loadAlgorithms(self):
        self.addAlgorithm(TrendShiftAlgorithm())

    def id(self):
        return 'trendshift'

    def name(self):
        return 'TrendShift'

    def longName(self):
        return 'TrendShift - Raster Change Point Detection'

    def icon(self):
        from qgis.PyQt.QtGui import QIcon
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'icon.png')
        return QIcon(icon_path)

    def svgIconPath(self):
        return os.path.join(os.path.dirname(__file__), 'icons', 'icon.png')

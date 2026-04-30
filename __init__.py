def classFactory(iface):
    from .plugin import TrendShiftPlugin
    return TrendShiftPlugin(iface)

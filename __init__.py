# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SpeedyLayer
                                 A QGIS plugin
 Generate memory layer from vector layer. Speed up for analysis and rendering operations.
                             -------------------
        begin                : 2016-03-15
        copyright            : (C) 2016 by Mehmet Selim BILGIN
        email                : mselimbilgin@yahoo.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SpeedyLayer class from file SpeedyLayer.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .SpeedyLayer import SpeedyLayer
    return SpeedyLayer(iface)

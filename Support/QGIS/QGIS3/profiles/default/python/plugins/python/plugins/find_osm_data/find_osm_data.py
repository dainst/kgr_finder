# -*- coding: utf-8 -*-
"""
/***************************************************************************
 KgrFinder
                                 A QGIS plugin
Find KGR Data
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-09-11
        git sha              : $Format:%H$
        copyright            : (C) 2023 by cuprit gbr
        email                : toni.schoenbuchner@cuprit.net
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QVariant
from qgis.PyQt.QtGui import QIcon, QColor

from qgis.PyQt.QtWidgets import QAction, QVBoxLayout
from qgis.gui import QgsMapTool, QgsRubberBand
# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the DockWidget
from .kgr_finder_dockwidget import KgrFinderDockWidget
import os.path
from qgis.core import QgsSettings, QgsWkbTypes, QgsGeometry, QgsRectangle, QgsVectorLayer, QgsField, QgsProject, QgsPointXY, QgsFeature, QgsFields
from qgis.PyQt.QtWidgets import QHBoxLayout
from qgis.gui import QgsOptionsWidgetFactory, QgsOptionsPageWidget
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QFormLayout, QCheckBox, QLabel
import json
from qgis.gui import QgsCollapsibleGroupBox
from qgis.core import QgsCategorizedSymbolRenderer, QgsMarkerSymbol, QgsRendererCategory
from .data_apis import OverpassAPIQueryStrategy, iDAIGazetteerAPIQueryStrategy

import requests

class KgrFinderOptionsFactory(QgsOptionsWidgetFactory):

    def __init__(self):
        super().__init__()

    def icon(self):
        return QIcon(':/plugins/kgr_finder/icon.png')

    def createWidget(self, parent):
        return ConfigOptionsPage(parent)


class ConfigOptionsPage(QgsOptionsPageWidget):

    osm_tags = [
        "place_of_worship",
        "Historic",
        "Museum",
        "Memorial",
        "Artwork",
        "Castle",
        "Ruins",
        "Archaeological Site",
        "Monastery",
        "Cultural Centre",
        "Library",
        "heritage"
    ]

    additional_tags = [
        "Tag1",
        "Tag2",
        "Tag3"
    ]

    def __init__(self, parent):
        super().__init__(parent)
        layout = QFormLayout()
        self.setLayout(layout)

        self.section_checkboxes = {}  # Initialize as a class variable

        self.createCheckBoxes(layout, "OSM – Cultural Tags", self.osm_tags, "osm_tags")
        self.createCheckBoxes(layout, "Additional Tags", self.additional_tags, "additional_tags")

        self.loadAndSetCheckboxes()

    def createCheckBoxes(self, layout, group_title, tags, settings_key):
        group_box = QgsCollapsibleGroupBox(group_title)
        group_box_layout = QVBoxLayout()
        group_box.setLayout(group_box_layout)

        checkboxes = []

        for tag in tags:
            checkbox = QCheckBox(tag)
            checkbox.setStyleSheet("margin: 10px;")
            checkbox.stateChanged.connect(self.checkboxStateChanged)
            checkboxes.append((tag, checkbox))
            group_box_layout.addWidget(checkbox)

        layout.addWidget(group_box)

        # Save checkboxes in the dictionary
        self.section_checkboxes[settings_key] = checkboxes

        # Load selected tags from settings and set checkboxes
        osm_tags = QgsSettings().value(f"/KgrFinder/{settings_key}", []) 
        for tag, checkbox in checkboxes:
            checkbox.setChecked(tag in osm_tags)

    def apply(self):
        for settings_key, checkboxes in self.section_checkboxes.items():
            osm_tags = [tag for tag, checkbox in checkboxes if checkbox.isChecked()]
            QgsSettings().setValue(f"/KgrFinder/{settings_key}", osm_tags) 

    def loadAndSetCheckboxes(self):
        for settings_key, checkboxes in self.section_checkboxes.items():
            osm_tags = QgsSettings().value(f"/KgrFinder/{settings_key}", [])
            for tag, checkbox in checkboxes:
                checkbox.setChecked(tag in osm_tags)
        
    def checkboxStateChanged(self):
        for settings_key, checkboxes in self.section_checkboxes.items():
            osm_tags = [tag for tag, checkbox in checkboxes if checkbox.isChecked()]
            QgsSettings().setValue(f"/KgrFinder/{settings_key}", osm_tags)




class KgrFinder:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        # save reference to the QGIS interface
        self.iface = iface
        self.tool = None

    def initGui(self):
        # create action that will start plugin configuration
        self.action = QAction(QIcon(":/plugins/kgr_finder/icon.png"),
                            "KGR Finder",
                            self.iface.mainWindow())
        self.action.setObjectName("KGRAction")
        self.action.setWhatsThis("Configuration for KGR Finder")
        self.action.setStatusTip("This is status tip")
        self.action.setCheckable(True)  # Make the action checkable
        self.action.toggled.connect(self.toggleTool)

        # add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Test plugins", self.action)

        self.options_factory = KgrFinderOptionsFactory()
        self.options_factory.setTitle('OSM Finder')
        iface.registerOptionsWidgetFactory(self.options_factory)


    def unload(self):
        # remove the plugin menu item and icon
        self.iface.removePluginMenu("&Test plugins", self.action)
        self.iface.removeToolBarIcon(self.action)
        iface.unregisterOptionsWidgetFactory(self.options_factory)


    def toggleTool(self, checked):
        if checked:
            self.tool = KgrFinderTool(self.iface.mapCanvas())
            self.iface.mapCanvas().setMapTool(self.tool)
        else:
            self.iface.mapCanvas().unsetMapTool(self.tool)
            self.tool = None

    def run(self):
        # create and show a configuration dialog or something similar
        print("TestPlugin: run called!")


class KgrFinderTool(QgsMapTool):
    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setStrokeColor(QColor('red'))
        self.rubber_band.setWidth(1)
        self.is_drawing = False
        self.api_strategies = [OverpassAPIQueryStrategy(), iDAIGazetteerAPIQueryStrategy()]  # Add any additional strategies
        # self.api_strategies = [iDAIGazetteerAPIQueryStrategy()]  # Add any additional strategies

        # self.api_strategies = [OverpassAPIQueryStrategy()]  # Add any additional strategies

    def canvasPressEvent(self, event):
        if not self.is_drawing:
            self.is_drawing = True
            self.start_point = self.toMapCoordinates(event.pos())
            self.rubber_band.setToGeometry(QgsGeometry.fromRect(QgsRectangle(self.start_point, self.start_point)), None)
            self.rubber_band.show()

    def canvasMoveEvent(self, event):
        if self.is_drawing:
            self.end_point = self.toMapCoordinates(event.pos())
            self.rubber_band.setToGeometry(QgsGeometry.fromRect(QgsRectangle(self.start_point, self.end_point)), None)
            self.rubber_band.show()

    def canvasReleaseEvent(self, event):
        if self.is_drawing:
            self.is_drawing = False
            self.end_point = self.toMapCoordinates(event.pos())
            self.rubber_band.setToGeometry(QgsGeometry.fromRect(QgsRectangle(self.start_point, self.end_point)), None)
            self.rubber_band.show()
            self.showRectangleCoordinates()


    def showRectangleCoordinates(self):
        rect = self.rubber_band.asGeometry().boundingBox().toRectF()
        x_min, y_min, x_max, y_max = rect.getCoords()
        point_layer = self.createPointLayer()
        fields = point_layer.fields()

        for strategy in self.api_strategies:
            print(strategy)
            data = strategy.query(x_min, y_min, x_max, y_max)
            elements = strategy.extractElements(data)
            attribute_mappings = strategy.getAttributeMappings()
            
            for element in elements:
                feature = self.createFeature(element, fields, attribute_mappings, strategy)

                if feature is not None:
                    point_layer.dataProvider().addFeature(feature)

            categorized_renderer = self.createCategorizedRenderer(point_layer)

            point_layer.setRenderer(categorized_renderer)
            point_layer.triggerRepaint()

            QgsProject.instance().addMapLayer(point_layer)



    def createFeature(self, element, fields, attribute_mappings, strategy):
        lat, lon = strategy.extractLatLon(element)
        geometry_type = strategy.getGeometryType(element)

        print(lat,lon)
        if geometry_type == 'point' and lat is not None and lon is not None:
            point = QgsPointXY(lon, lat)
            geometry = QgsGeometry.fromPointXY(point)
        else:
            # Handle other element types or missing lat/lon
            # print(element)
            # print("no lon lat")
            return None

        feature = QgsFeature(fields)
        feature.setGeometry(geometry)


        # # Iterate over attribute_mappings and set attributes
        for attribute, mapping in attribute_mappings.items():
            if '.' in mapping:
                # Handle nested mappings like 'tags.name'
                parts = mapping.split('.')
                value = element
                for part in parts:
                    value = value.get(part, {})
            else:
                # Check if the mapping exists in the 'tags' dictionary
                if mapping.startswith('tags.'):
                    tag_key = mapping.split('tags.')[1]
                    value = element['tags'].get(tag_key, '')
                else:
                    value = element.get(mapping, '')
            value = str(value) if value else "-" 
            feature.setAttribute(attribute, value)
        
        feature.setAttribute('source', f"{strategy.source}")

        return feature


    def createPointLayer(self):
        fields = QgsFields()
        fields.append(QgsField('lon', QVariant.String))

        fields.append(QgsField('lat', QVariant.String))

        fields.append(QgsField('name', QVariant.String))
        fields.append(QgsField('source', QVariant.String))
        fields.append(QgsField('description', QVariant.String, 'string', 5000))
        fields.append(QgsField('type', QVariant.String))
        fields.append(QgsField('id', QVariant.String))
        fields.append(QgsField('tags', QVariant.String, 'json', 5000))
        fields.append(QgsField('building', QVariant.String))

        point_layer = QgsVectorLayer('Point?crs=EPSG:4326', 'OSM Data (Points)', 'memory')
        point_layer.dataProvider().addAttributes(fields)
        point_layer.updateFields()

        return point_layer

    def createCategorizedRenderer(self, layer):
        categorized_renderer = QgsCategorizedSymbolRenderer('source')

        osm_symbol = QgsMarkerSymbol.defaultSymbol(layer.geometryType())
        osm_symbol.setColor(QColor(255, 0, 0))  # Blue color
        osm_symbol.setSize(4)  # Increased size

        non_osm_symbol = QgsMarkerSymbol.defaultSymbol(layer.geometryType())
        non_osm_symbol.setColor(QColor(0, 0, 255))  # Red color
        non_osm_symbol.setSize(4)  # Increased size

        cat_osm = QgsRendererCategory('osm', osm_symbol, 'OSM Features')
        cat_non_osm = QgsRendererCategory('DAI', non_osm_symbol, 'DAI')

        categorized_renderer.addCategory(cat_osm)
        categorized_renderer.addCategory(cat_non_osm)

        return categorized_renderer


    def deactivate(self):
        self.rubber_band.reset()
        self.rubber_band.hide()
        QgsMapTool.deactivate(self)

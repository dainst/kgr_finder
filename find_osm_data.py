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
from qgis.PyQt.QtGui import QIcon

from qgis.PyQt.QtWidgets import QAction, QVBoxLayout
# Initialize Qt resources from file resources.py
from .resources import *

import os.path
from qgis.core import QgsSettings
from qgis.gui import QgsOptionsWidgetFactory, QgsOptionsPageWidget
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QFormLayout, QCheckBox
import json
from qgis.gui import QgsCollapsibleGroupBox

import requests 
from .tools import KgrFinderTool

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
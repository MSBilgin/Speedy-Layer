# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SpeedyLayer
                                 A QGIS plugin
 Generate memory layer from vector layer. Speed up for testing, analysis and rendering operations.
                              -------------------
        copyright            : (C) 2016 by Mehmet Selim BILGIN
        email                : mselimbilgin@yahoo.com
        web                  : cbsuygulama.wordpress.com
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

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant,QObject,SIGNAL
from PyQt4.QtGui import QAction, QIcon, QMessageBox
# Initialize Qt resources from file resources.py
import resources
from qgis.core import QgsMapLayerRegistry, QgsVectorLayer, QgsField, QgsMapLayerRegistry, QgsMapLayer
# Import the code for the dialog
from SpeedyLayer_dialog import SpeedyLayerDialog
from loader import Committer, Loader
import os.path
from collections import OrderedDict


class SpeedyLayer(object):
    def __init__(self, iface):
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SpeedyLayer_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        #this variable is used as wkbType enum
        self.wkbText = {0:"GeometryUnknown", 1:"Point", 2:"LineString", 3:"Polygon", 4:"MultiPoint", 5:"MultiLineString",
                        6:"MultiPolygon", 7:"NoGeometry", 8:"Point25D", 9:"LineString25D", 10:"Polygon25D",
                        11:"MultiPoint25D", 12:"MultiLineString25D", 13:"MultiPolygon25D", 100:"NoGeometry"}

        #sometime qgis cannot return geometry type truly. this bug is handling in here
        self.geometryText = {0:"Point", 1:"LineString", 2:"Polygon", 3:"GeometryUnknown", 4:"NoGeometry"}

        #this variable is useful for determining QVariant types as string
        self.QVariant_Dict = {}
        for i in QVariant.__dict__:
            if str(QVariant.__dict__[i])[0] != '<' and i[0] != '_':
                self.QVariant_Dict[QVariant.__dict__[i]] = i


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Speedy Layer')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'SpeedyLayer')
        self.toolbar.setObjectName(u'SpeedyLayer')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SpeedyLayer', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/SpeedyLayer/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Speedy Layer'),
            callback=self.run,
            parent=self.iface.mainWindow())
        #add contextual menu
        self.dup_to_memory_layer_action = QAction(QIcon(icon_path), "Duplicate to memory layer", self.iface.legendInterface() )
        self.iface.legendInterface().addLegendLayerAction(self.dup_to_memory_layer_action, "","01", QgsMapLayer.VectorLayer,True)
        self.dup_to_memory_layer_action.triggered.connect(self.run)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Speedy Layer'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
        # remove contextual menu
        self.iface.legendInterface().removeLegendLayerAction(self.dup_to_memory_layer_action)

    def process(self):
        if len(self.allVectorLayers) > 0:
            self.vectorLayer = self.allVectorLayers[self.dlg.cmbVectorLayer.currentIndex()]
            self.memoryLayer = self.generateMemoryLayer(self.vectorLayer,self.selectedLayerFields)
            self.loader = Loader(targetLayer=self.memoryLayer,sourceLayer=self.vectorLayer)
            self.loader.setOptions(onlySelected=self.dlg.checkBox.isChecked())
            self.dlg.btnStart.setEnabled(False)
            self.dlg.btnStop.setEnabled(True)
            self.dlg.btnStop.clicked.connect(self.loader.stop)
            self.iface.mapCanvas().setRenderFlag(False)#QGIS can not render dramatic changes in the target layer feature count and crashes down. So before starting we need to stop rendering.

            QObject.connect(self.loader, SIGNAL("progressLenght"), self.setProgressLength)
            QObject.connect(self.loader, SIGNAL("progress"), self.setProgress)
            QObject.connect(self.loader, SIGNAL("error"), self.error)
            QObject.connect(self.loader, SIGNAL("finished()"), self.done)
            QObject.connect(self.loader, SIGNAL('status'), self.setStatus)
            # QObject.connect(self.loader, SIGNAL('debug'), self.debug)
            self.loader.start()

        else:
            QMessageBox.warning(self.dlg, u'Error', u'There must be at least one vector layers added in QGIS canvas.')

    # def debug(self,msg):
    #     QMessageBox.information(None,'debug',msg)

    def setProgress(self, val):
        self.dlg.progressBar.setValue(val)

    def setProgressLength(self, val):
        self.dlg.progressBar.setMaximum(val)
        if val==0:
            self.dlg.btnStop.setEnabled(False)#this control may prevent errors when clicking stop button during saving changes.

    def error(self, exception):
        QMessageBox.critical(self.dlg, 'Error', str(exception) + '. All changes were rollbacked.')

    def done(self):
        #this function is used by loader class's finished() signal.
        if not self.loader.hasError:
            if not self.loader.isCancel:
                QgsMapLayerRegistry.instance().addMapLayer(self.memoryLayer)
                self.committer = Committer(self.memoryLayer)#this thread saves changes to datasource.
                QObject.connect(self.committer, SIGNAL("finished()"), self.commitFinished)
                QObject.connect(self.committer, SIGNAL('commitStarted'), self.commitStarted)
                self.memoryLayer.startEditing()

                self.dlg.btnStop.setEnabled(False)
                self.memoryLayer.addFeatures(self.loader.featureList, False)

                self.committer.start()
            else:
                QMessageBox.information(self.dlg,'Result','Operation was canceled by user')
                self.onStop()
        else:
            self.onStop()

    def commitStarted(self):
        self.dlg.lblStatus.setText(u'Please wait while memory allocation for new features...')
        self.dlg.progressBar.setMaximum(0)
        self.dlg.btnStop.setEnabled(False)

    def commitFinished(self):
        self.onStop()
        QMessageBox.information(self.dlg,'Result', "Selected layer was copied to memory and added to the Canvas")
        self.dlg.hide()

    def onStop(self):
        self.dlg.progressBar.setMaximum(1)
        self.dlg.progressBar.reset()
        self.dlg.lblStatus.clear()
        self.loader.terminate()
        try:
            del self.loader
            del self.committer
        except:
            pass
        self.dlg.btnStart.setEnabled(True)
        self.dlg.btnStop.setEnabled(False)
        self.iface.mapCanvas().setRenderFlag(True)
        self.iface.mapCanvas().refresh()

    def setStatus(self,message):
        self.dlg.lblStatus.setText(message)

    def generateMemoryLayer(self, targetLayer, fieldDict):
        epsg = 'EPSG:'+ str(targetLayer.crs().postgisSrid())
        if self.geometryText.has_key(targetLayer.wkbType()):
            geometry = self.wkbText[targetLayer.wkbType()]
        else:
            geometry = self.geometryText[targetLayer.geometryType()]
        name = targetLayer.name()
        memoryLayer = QgsVectorLayer(geometry + '?crs=' + epsg, name, "memory")
        memoryLayer.startEditing()#to add field it needs to be in editing mode
        for fieldName in fieldDict:
            field = QgsField(fieldName, fieldDict[fieldName])
            memoryLayer.dataProvider().addAttributes([field])
        memoryLayer.updateFields()
        memoryLayer.commitChanges()
        return  memoryLayer

    def listFields(self):
        #this function fills field comboboxes
        self.selectedLayerFields = OrderedDict() #holds fieldname:type of all fields in selected layer
        self.dlg.lstFields.clear() #clear
        if self.allVectorLayers:
            targetVectorLayer = self.allVectorLayers[self.dlg.cmbVectorLayer.currentIndex()]
            attributes = targetVectorLayer.dataProvider().fields().toList()
            for attribute in attributes:
                self.selectedLayerFields[attribute.name()] = attribute.type()
                self.dlg.lstFields.addItem(attribute.name() + '   (%s)' %(self.QVariant_Dict[attribute.type()]))

    def removeField(self):
        selectedFieldList = self.dlg.lstFields.selectedItems() #QWidgetItem List
        for field in selectedFieldList:
            index = self.dlg.lstFields.indexFromItem(field).row()
            fieldName = field.text()[:field.text().index('   (')]
            del self.selectedLayerFields[fieldName] #removing not only from listWidget but also from this dict
            self.dlg.lstFields.takeItem(index)


    def run(self):
        self.dlg = SpeedyLayerDialog()
        self.dlg.setFixedSize(self.dlg.size())

        self.allVectorLayers = []
        self.allMapLayers = QgsMapLayerRegistry.instance().mapLayers().items()

        for (notImportantForNow, layerObj) in self.allMapLayers:
            if layerObj.type() == 0:#0 is vectorlayer
                self.allVectorLayers.append(layerObj)
                if self.wkbText.has_key(layerObj.wkbType()):#Sometime qgis cannot return geomerty type truly. This bug is handling in here
                    cmbLabel = layerObj.name() + ' (%d) (%s)' % (layerObj.featureCount(), self.wkbText[layerObj.wkbType()])
                else:
                    cmbLabel = layerObj.name() + ' (%d) (%s)' % (layerObj.featureCount(), self.geometryText[layerObj.geometryType()])
                self.dlg.cmbVectorLayer.addItem(cmbLabel,layerObj.id())

        self.selectedLayerFields = {} #this dict holds selected fields name:QVariant.Type of target layer
        
        # pre-select current layer if selected in legend interface
        if self.iface.legendInterface().currentLayer():
            current_idx = self.dlg.cmbVectorLayer.findData(self.iface.legendInterface().currentLayer().id())
            if current_idx != -1:
                self.dlg.cmbVectorLayer.setCurrentIndex(current_idx)
        
        self.listFields()
        self.dlg.cmbVectorLayer.currentIndexChanged.connect(self.listFields)

        self.dlg.btnRemove.clicked.connect(self.removeField)
        self.dlg.btnReset.clicked.connect(self.listFields)


        self.dlg.btnStart.clicked.connect(self.process)
        self.dlg.show()

        result = self.dlg.exec_()
        # Closing control
        if not result:
            try:
                self.loader.stop()
                self.committer.terminate()
                del self.loader
                del self.committer
            except:
                pass
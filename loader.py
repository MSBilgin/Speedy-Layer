# -*- coding: utf-8 -*-
"""
/***************************************************************************
loader
                                 A QGIS plugin
 A loader tool for inserting new features to target vector layer
                             -------------------
        copyright            : (C) 2016 by Mehmet Selim BILGIN
        email                : mselimbilgin@yahoo.com
        web                  : http://cbsuygulama.wordpress.com
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

from PyQt4.QtCore import QThread, SIGNAL

class Loader(QThread):
    def __init__(self, targetLayer, sourceLayer):
        QThread.__init__(self)
        self.targetLayer = targetLayer
        self.sourceLayer = sourceLayer
        self.featureList = [] #this list holds features that will be loaded into target layer
        self.onlySelected = False
        self.isCancel = False
        self.hasError = False

    def setOptions(self, onlySelected):
        self.onlySelected = onlySelected

    def run(self):
        try:
            self.emit(SIGNAL('status'),u'Loading Features...')
            progress = 0

            if self.onlySelected:
                pLength = self.sourceLayer.selectedFeatureCount()
                sourceFeatures = self.sourceLayer.selectedFeaturesIterator()
            else:
                pLength = int(self.sourceLayer.featureCount())
                sourceFeatures = self.sourceLayer.getFeatures()

            pLength = pLength or 100000 #sometimes qgis can not calculate feature count and returns 0. so if this situation happens/
            #i change value to a number like 100000 to provide the progressbar visuality.
            self.emit(SIGNAL("progressLenght"), pLength)#sends progress length to progressbar
            commonFields = self.attributeAdaptor(self.targetLayer,self.sourceLayer)

            for feature in sourceFeatures:
                if not self.isCancel:
                    modifiedFeature = self.attributeFill(feature,self.targetLayer,commonFields)
                    # self.emit(SIGNAL('insertFeature'), modifiedFeature)
                    self.featureList.append(modifiedFeature)
                    progress = progress + 1
                    self.emit(SIGNAL("progress"), progress)

        except Exception, err:
            self.hasError = True
            self.emit(SIGNAL('error'), err)

    def attributeAdaptor(self,targetLayer, sourceLayer):
        #this function is used for matching target and source layers field names
        targetLayerFields = [] #holds target layer's field names
        sourceLayerFields = [] #holds source layer's field names
        primaryKeyList = [] #holds targetLayer primarykey fields' names

        for index in targetLayer.dataProvider().pkAttributeIndexes():
            primaryKeyList.append(targetLayer.dataProvider().fields().at(index).name())

        for field in sourceLayer.dataProvider().fields().toList():
            sourceLayerFields.append(field.name())

        for field in targetLayer.dataProvider().fields().toList():
            targetLayerFields.append(field.name())

        commonFields = list(set(sourceLayerFields) & set(targetLayerFields))#determining common fields between target and source layer
        commonFields = list(set(commonFields)-set(primaryKeyList)) #removing primarykey fields to prevent uniqueID error.

        return commonFields

    def attributeFill(self, qgsFeature, targetLayer, commonFields):
        #this function is used for adapting a feature's attribute columns to target layer's columns)
        featureFields = {} #holds feature's fields

        try:
            for field in qgsFeature.fields().toList():
                featureFields[field.name()] = qgsFeature[field.name()]
        except:
            pass

        #firstly setting the features fields
        qgsFeature.setFields(targetLayer.dataProvider().fields())

        if commonFields:
            # if they the feature has common fields with target layer than load original values back.
            for fieldName in commonFields:
                try:
                    qgsFeature[fieldName]=featureFields[fieldName]
                except:
                    pass

        return qgsFeature

    def stop(self):
        self.isCancel = True
        self.wait()
        self.terminate()

class Committer(QThread):
    #this thread is used for handling long process of saving changes to datasource
    def __init__(self, qgsVectorLayer):
        QThread.__init__(self)
        self.qgsVectorLayer = qgsVectorLayer

    def run(self):
        self.emit(SIGNAL("commitStarted"))
        self.qgsVectorLayer.commitChanges()



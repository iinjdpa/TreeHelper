# coding: utf-8

__Name__ = 'Tree helper'
__Comment__ = '''
Permite gestionar el arbol de FreeCAD abriendo sub-ventanas para los elementos seleccionados
'''
__Author__ = "Daniel Pose. iinjdpa at gmail"
__Version__ = '0.2'
__Date__ = '2021-12-05'
__License__ = 'MIT'
__Web__ = ""
__Wiki__ = ""
__Icon__ = ''
__Help__ = ''
__Status__ = 'alpha'
__Requires__ = 'Freecad >= 0.19'
__Communication__ = ''
__Files__ = ''


import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui
from PySide.QtCore import Qt, QByteArray, QDataStream, QIODevice
from PySide.QtGui import QDialog, QApplication, QTreeWidgetItem, QDockWidget, QGraphicsDropShadowEffect, QColor
from PySide.QtGui import QMessageBox, QAbstractItemView, QDrag
import PySide2
import os
import sys
from TreeHelper import ui_treewindow
from collections import OrderedDict
import time


class Objdoc(object):
    def __init__(self,doc):
        self.ViewObject = mViewObject()
        self.Name = doc.Name
        self.Label = doc.Name

class mViewObject(object):
    def __init__(self):
        pass
    def claimChildren(self):
        # Nombre del documento
        doc = App.activeDocument()
        if doc == None:
            doc = FreeCAD.newDocument()
        docName = doc.Name
        # Buscamos el árbol de FreeCAD. Es la forma de poder importar todos los objetos por orden
        mw = Gui.getMainWindow()
        self.tw = mw.findChildren(QtGui.QTreeWidget)
        self.tw0 = self.tw[0]
        self.tw0.repaint()
        self.FCtreeitems = self.tw0.findItems('*', Qt.MatchWrap | Qt.MatchWildcard  | Qt.MatchRecursive)
        root_labels = []
        for it in self.FCtreeitems:
            if not it.parent(): continue
            if isinstance(it.parent(), list):
                for itp in it.parent():
                    if itp == docName:
                        root_labels.append(it.text(0))
            else:
                if it.parent().text(0) == docName:
                    root_labels.append(it.text(0))
        root_objects = App.ActiveDocument.RootObjects
        root_objects_from_labels = []
        if len(root_labels) == len(root_objects):
            for obj in root_labels:
                obj_by_label = App.ActiveDocument.getObjectsByLabel(obj)
                if len(obj_by_label) > 1:
                    QMessageBox.critical(self, "Error","There are objects with same label!")
                    return []
                else:
                    root_objects_from_labels.append(App.ActiveDocument.getObjectsByLabel(obj)[0])
            return root_objects_from_labels
        else:
            return root_objects

    def update(self):
        pass

class TreeDrops(QtGui.QTreeWidget):
    itemDropped = QtCore.Signal()
    customMimeType = "application/x-qabstractitemmodeldatalist"
    def __init__(self, parent=None):
        super(TreeDrops, self).__init__(parent=None)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.dragEnabled()
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

    def startDrag(self, supportedActions):
        drag = QDrag(self)
        mimedata = self.model().mimeData(self.selectedIndexes())

        encoded = QByteArray()
        stream = QDataStream(encoded, QIODevice.WriteOnly)
        self.encodeData(self.selectedItems(), stream)
        mimedata.setData(self.customMimeType, encoded)

        drag.setMimeData(mimedata)
        drag.exec_(supportedActions)

    def encodeData(self, items, stream):
        stream.writeInt32(len(items))
        for item in items:
            p = item
            rows = []
            while p is not None:
                rows.append(self.indexFromItem(p).row())
                p = p.parent()
            stream.writeInt32(len(rows))
            for row in reversed(rows):
                stream.writeInt32(row)
        return stream

    def dropEvent(self, event):
        global miglobal
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            # El texto del elemento seleccionado:
            # textoSeleccionado = event.source().selectedItems()[0].text(0)
            # El índice del elemento seleccionado
            # indiceElemento = event.source().indexFromItem(event.source().selectedItems()[0])
            # El qtreewidgetitem
            # indiceElemento = event.source().currentItem()

            # parent = self.indexAt(event.pos())
            destiny = self.itemAt(event.pos()).text(1)

            origin_label = event.source().selectedItems()[0].text(0)
            obj_by_label = App.ActiveDocument.getObjectsByLabel(origin_label)
            if len(obj_by_label) > 1:
                QMessageBox.critical(self, "Error","There are objects with same label!")
                return
            else:
                origin_obj = App.ActiveDocument.getObjectsByLabel(origin_label)[0]
            
            # Buscamos el objeto padre del origen
            if event.source().selectedItems()[0].parent():
                origin_father_label = event.source().selectedItems()[0].parent().text(0)
            else:
                return

            obj_by_label = App.ActiveDocument.getObjectsByLabel(origin_father_label)
            if len(obj_by_label) > 1:
                QMessageBox.critical(self, "Error","There are objects with same label!")
                return
            else:
                if App.ActiveDocument.getObjectsByLabel(origin_father_label):
                    origin_father = App.ActiveDocument.getObjectsByLabel(origin_father_label)[0]
            
            App.ActiveDocument.openTransaction('moveobject')
            # Object moved between sub-elements
            if App.ActiveDocument.getObject(destiny):
                origin_obj.adjustRelativeLinks(App.ActiveDocument.getObject(destiny))
                App.ActiveDocument.getObject(destiny).addObject(origin_obj)
            else:
                # Object moved to main
                origin_father.removeObject(origin_obj)
            
            # Repaint FreeCAD QtreeWidget for update changes
            tw = mw.findChildren(QtGui.QTreeWidget)
            tw0 = [t.repaint() for t in tw]
            
            App.ActiveDocument.commitTransaction()
            App.ActiveDocument.recompute()
            
            self.itemDropped.emit()
            # Esta línea hace que se mueva la información de un árbol al otro
            # self.model().dropMimeData(event.mimeData(), event.dropAction(), 0, 0, parent)

class Treehelper(QDialog,ui_treewindow.Ui_Dialog):
    window_closed = QtCore.Signal()
    def __init__(self,parent=None):
        super(Treehelper,self).__init__(parent,QtCore.Qt.WindowStaysOnTopHint)
        self.setupUi(self)
        param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Macro")     
        self.path = param.GetString("MacroPath","") + "/"
        self.path = self.path.replace("\\","/")
        self.treeWidget2 = TreeDrops(self)
        self.gridLayout.replaceWidget(self.treeWidget, self.treeWidget2)
        self.treeWidget.close()
        qtreewidgetitem0 = self.treeWidget2.headerItem()
        qtreewidgetitem0.setText(0, u"Element")
        qtreewidgetitem1 = self.treeWidget2.headerItem()
        qtreewidgetitem1.setText(1, u"Name")
        self.gridLayout.update()
        self.treeWidget2.setColumnCount(2)
        self.treeWidget2.setLineWidth(6)
        self.treeWidget2.setAlternatingRowColors(True)
        self.treeWidget2.setIconSize(QtCore.QSize(18, 18))
        self.treeWidget2.setAnimated(True)
        self.treeWidget2.header().sectionSize(1200)
        self.treeWidget2.header().setDefaultSectionSize(1200)
        self.treeWidget2.header().setMinimumSectionSize(1200)
        self.treeWidget2.header().setCascadingSectionResizes(True)
        self.treeWidget2.header().setHighlightSections(True)
        self.treeWidget2.header().setStretchLastSection(True)
        # Creamos una variable para guardar el elemento raiz del árbol
        self.mainelement = ''
        # Hacemos la ventana modal
        # self.setModal(False)
        # Cargamos el árbol
        self.loadtree()

        # Actualizamos el arbol despues de mover un objeto
        self.treeWidget2.itemDropped.connect(self.updatetree)

    def updatetree(self):
        # Actualizamos todos los sub-arboles creados
        mw = Gui.getMainWindow()
        qd = mw.findChildren(QtGui.QDialog,name='Tree helper')
        for q in qd:
            try:
                q.loadtree()
            except:
                pass

    def loadtree(self):
        """Lee el árbol de FreeCAD a partir del elemento seleccionado y lo carga en el árbol de ayuda
        """
        self.treeWidget2.clear()

        doc = App.activeDocument()
        if doc == None:
            doc = FreeCAD.newDocument()

        # El objeto seleccionado será el primero del árbol
        if self.mainelement:
            if self.mainelement.Name == doc.Name:
                # El objeto principal es el documento
                mainTreeItem  = QTreeWidgetItem(self.treeWidget2)
                mainTreeItem.setText(0,doc.Name)
                mainTreeItem.setText(1,doc.Name)
                mainTreeItem.setExpanded(True)
                objSel = self.mainelement
            else:
                # El objeto principal es otro cualquiera
                objSel = self.mainelement
                mainTreeItem  = QTreeWidgetItem(self.treeWidget2)
                mainTreeItem.setText(0,objSel.Label)
                mainTreeItem.setText(1,objSel.Name)
                try:
                    mainTreeItem.setIcon(0,objSel.ViewObject.Icon)
                except:
                    pass
                mainTreeItem.setExpanded(True)
        else:
            if Gui.Selection.getCompleteSelection():
                objSel = Gui.Selection.getCompleteSelection()[0]
                self.mainelement = objSel
                mainTreeItem  = QTreeWidgetItem(self.treeWidget2)
                mainTreeItem.setText(0,objSel.Label)
                mainTreeItem.setText(1,objSel.Name)
                try:
                    mainTreeItem.setIcon(0,objSel.ViewObject.Icon)
                except:
                    pass
                mainTreeItem.setExpanded(True)
            else:
                objSel = Objdoc(doc)
                self.mainelement = objSel
                mainTreeItem  = QTreeWidgetItem(self.treeWidget2)
                mainTreeItem.setText(0,doc.Name)
                mainTreeItem.setText(1,doc.Name)
                mainTreeItem.setExpanded(True)
            
        # Iteramos sobre los objetos bajo el objeto seleccionado
        dictObjs = OrderedDict()
        lstObjs = [[0,objSel,'main']]
        while lstObjs:
            crrObj = lstObjs.pop()
            # crrObj[1].ViewObject.update()
            for obj in crrObj[1].ViewObject.claimChildren():
                level = crrObj[0]
                # Guardamos su nivel dentro del árbol, el propio objeto y el nombre del objeto padre
                dcName = obj.Name
                ct = 0
                # Un mismo objeto puede estar en distintas partes del árbol. No repetimos clave
                while dcName in dictObjs:
                    dcName = f'{dcName}{ct:04d}'
                    ct+=1
                dictObjs[dcName] = [level+1,obj,crrObj[1].Name]
                lstObjs.append(dictObjs[obj.Name])
        
        # Iteramos ahora sobre los objetos recogidos para insertarlos en el árbol
        dictItems = {}
        dictItems[objSel.Name] = mainTreeItem
        for k,elem in dictObjs.items():
            itemElem = QTreeWidgetItem(dictItems[dictObjs[k][2]])
            itemElem.setText(0,dictObjs[k][1].Label)
            itemElem.setText(1,dictObjs[k][1].Name)
            try:
                itemElem.setIcon(0,dictObjs[k][1].ViewObject.Icon)
            except:
                pass
            itemElem.setExpanded(True)
            dictItems[k] = itemElem

if __name__ == '__main__': 
    mw = Gui.getMainWindow()
    mform=Treehelper(mw)
    mform.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
    mform.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
    mform.show()
    mform.exec_()
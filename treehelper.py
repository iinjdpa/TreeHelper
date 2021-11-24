# coding: utf-8

__Name__ = 'Tree helper'
__Comment__ = '''
Permite gestionar el arbol de FreeCAD abriendo sub-ventanas para los elementos seleccionados
'''
__Author__ = "Daniel Pose. iinjdpa at gmail"
__Version__ = '0.1'
__Date__ = '2021-11-15'
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
from PySide.QtCore import Qt
from PySide.QtGui import QLineEdit, QRadioButton, QDialog, QApplication, QStyleFactory, QTreeWidgetItem, QMainWindow
from PySide.QtGui import QComboBox, QMessageBox, QFileDialog
import os
import sys
from TreeHelper import ui_treewindow
from collections import OrderedDict

# import ptvsd
# print("Waiting for debugger attach")
# # 5678 is the default attach port in the VS Code debug configurations
# ptvsd.enable_attach(address=('localhost', 5678), redirect_output=True)
# #ptvsd.wait_for_attach()
# ptvsd.break_into_debugger()


class Objdoc(object):
    def __init__(self,doc):
        self.OutList = App.ActiveDocument.RootObjects
        self.Name = doc.Name

class TreeDrops(QtGui.QTreeWidget):
    itemDropped = QtCore.Signal()
    def __init__(self, parent=None):
        super(TreeDrops, self).__init__(parent=None)
        # self.setColumnCount(1)
        # self.setDefaultDropAction(QtCore.Qt.CopyAction)
        # self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.setAcceptDrops(True)

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
            origin = Gui.Selection.getCompleteSelection()[0].Name
            # origin = App.ActiveDocument.ActiveObject.Name

            App.ActiveDocument.getObject(origin).adjustRelativeLinks(App.ActiveDocument.getObject(destiny))
            App.ActiveDocument.getObject(destiny).addObject(App.ActiveDocument.getObject(origin))

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
        self.treeWidget2.setIconSize(QtCore.QSize(12, 12))
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
        # Buscamos el árbol de FreeCAD. Es la forma de poder importar todos los objetos por orden
        mw = Gui.getMainWindow()
        self.tw = mw.findChildren(QtGui.QTreeWidget)
        self.tw0 = self.tw[0]
        self.FCtreeitems = self.tw0.findItems('*', Qt.MatchWrap | Qt.MatchWildcard  | Qt.MatchRecursive)[0]

        # Cargamos el árbol
        self.loadtree()

        # Actualizamos el arbol despues de mover un objeto
        self.treeWidget2.itemDropped.connect(self.updatetree)

    def updatetree(self):
        self.loadtree()

    def old_loadtree(self):
        """Lee el árbol de FreeCAD a partir del elemento seleccionado y lo carga en el árbol de ayuda
        """
        self.treeWidget2.clear()

        # El objeto seleccionado será el primero del árbol
        if Gui.Selection.getCompleteSelection():
            if not self.mainelement:
                objSel = Gui.Selection.getCompleteSelection()[0]
                self.mainelement = objSel
            else:
                objSel = self.mainelement
            mainTreeItem  = QTreeWidgetItem(self.treeWidget2)
            mainTreeItem.setText(0,objSel.Label)
            mainTreeItem.setText(1,objSel.Name)
            mainTreeItem.setIcon(0,objSel.ViewObject.Icon)
            mainTreeItem.setExpanded(True)
        else:
            doc = App.activeDocument()
            if doc == None:
                doc = FreeCAD.newDocument()
            mainTreeItem  = QTreeWidgetItem(self.treeWidget2)
            mainTreeItem.setText(0,doc.Name)
            mainTreeItem.setText(1,doc.Name)
            mainTreeItem.setExpanded(True)
            objSel = Objdoc(doc)

        # Iteramos sobre los objetos bajo el objeto seleccionado
        dictObjs = OrderedDict()
        lstObjs = [[0,objSel,'main']]
        while lstObjs:
            crrObj = lstObjs.pop()
            for obj in crrObj[1].OutList:
                level = crrObj[0]
                # Guardamos su nivel dentro del árbol, el propio objeto y el nombre del objeto padre
                dictObjs[obj.Name] = [level+1,obj,crrObj[1].Name]
                lstObjs.append(dictObjs[obj.Name])
        
        # Iteramos ahora sobre los objetos recogidos para insertarlos en el árbol
        dictItems = {}
        dictItems[objSel.Name] = mainTreeItem
        # print('El contenido de dictObjs: ',dictObjs)
        # print('El contenido de dictItems: ',dictItems)
        for k,elem in dictObjs.items():
            itemElem = QTreeWidgetItem(dictItems[dictObjs[k][2]])
            itemElem.setText(0,dictObjs[k][1].Label)
            itemElem.setText(1,dictObjs[k][1].Name)
            itemElem.setIcon(0,dictObjs[k][1].ViewObject.Icon)
            itemElem.setExpanded(True)
            dictItems[k] = itemElem

    def loadtree(self):
        """Lee el árbol de FreeCAD a partir del elemento seleccionado y lo carga en el árbol de ayuda
        """
        self.treeWidget2.clear()

        # El objeto seleccionado será el primero del árbol
        if Gui.Selection.getCompleteSelection():
            if not self.mainelement:
                objSel = Gui.Selection.getCompleteSelection()[0]
                self.mainelement = objSel
            else:
                objSel = self.mainelement
            mainTreeItem  = QTreeWidgetItem(self.treeWidget2)
            mainTreeItem.setText(0,objSel.Label)
            mainTreeItem.setText(1,objSel.Name)
            mainTreeItem.setIcon(0,objSel.ViewObject.Icon)
            mainTreeItem.setExpanded(True)
        else:
            doc = App.activeDocument()
            if doc == None:
                doc = FreeCAD.newDocument()
            mainTreeItem  = QTreeWidgetItem(self.treeWidget2)
            mainTreeItem.setText(0,doc.Name)
            mainTreeItem.setText(1,doc.Name)
            mainTreeItem.setExpanded(True)
            objSel = Objdoc(doc)

        # Iteramos sobre los objetos bajo el objeto seleccionado
        dictObjs = OrderedDict()
        lstObjs = [[0,objSel,'main']]
        while lstObjs:
            crrObj = lstObjs.pop()
            for obj in crrObj[1].OutList:
                level = crrObj[0]
                # Guardamos su nivel dentro del árbol, el propio objeto y el nombre del objeto padre
                dictObjs[obj.Name] = [level+1,obj,crrObj[1].Name]
                lstObjs.append(dictObjs[obj.Name])
        
        # Iteramos ahora sobre los objetos recogidos para insertarlos en el árbol
        dictItems = {}
        dictItems[objSel.Name] = mainTreeItem
        print('El contenido de dictObjs: ',dictObjs)
        print('El contenido de dictItems: ',dictItems)
        for k,elem in dictObjs.items():
            itemElem = QTreeWidgetItem(dictItems[dictObjs[k][2]])
            itemElem.setText(0,dictObjs[k][1].Label)
            itemElem.setText(1,dictObjs[k][1].Name)
            itemElem.setIcon(0,dictObjs[k][1].ViewObject.Icon)
            itemElem.setExpanded(True)
            dictItems[k] = itemElem


if __name__ == '__main__': 
    mform=Treehelper()
    mform.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
    mform.setWindowFlag(Qt.WindowMaximizeButtonHint, True)
    mform.show()
    mform.exec_()
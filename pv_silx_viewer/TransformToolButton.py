#!/usr/bin/env python3

from os import path
from copy import deepcopy

from silx.gui.plot.PlotToolButtons import PlotToolButton
from silx.gui import qt

from sscPimega import pi450D

TRANSFORM_BUTTON_PATH = path.dirname(path.realpath(__file__))

def pimega450DTrans(data):
    data_out = deepcopy(data)
    data_out = pi450D.view(data, -1)

    return data_out

def noTrans(data):
    
    return data

class TransformToolButton(PlotToolButton):
    """Tool button to transform image according to selected
    transformation. Usually PiMega stuff."""

    STATE = None
    """Lazy loaded states used to feed TransformToolButton"""

    def __init__(self, parent=None, plot=None):
        if self.STATE is None:
            self.STATE = {}
            
            self.STATE["None", "icon"] = qt.QIcon(path.join(path.dirname(path.realpath(__file__)),
                                                          "./icons/matrix.png"))
            self.STATE["None", "state"] = "None"
            self.STATE["None", "action"] = "No transformation"
            # 450D model
            self.STATE["450D", "icon"] = qt.QIcon(path.join(path.dirname(path.realpath(__file__)),
                                                           "./icons/pimega-450D.png"))
            self.STATE["450D", "state"] = "450D"
            self.STATE["450D", "action"] = "450D model transformation"
            # 540D model
            self.STATE["540D", "icon"] = qt.QIcon(path.join(path.dirname(path.realpath(__file__)),
                                                          "./icons/pimega-540.png"))
            self.STATE["540D", "state"] = "540D"
            self.STATE["540D", "action"] = "540D model transformation"

        super(TransformToolButton, self).__init__(parent=parent, plot=plot)

        self.createAllActions()
        self.setTransformation("None")
        
    def createAllActions(self):
        """
        Create actions for all model restorations.
        """

        pimegaNoneAction = self._createAction("None")
        pimegaNoneAction.triggered.connect(lambda: self.setTransformation("None"))
        pimegaNoneAction.setIconVisibleInMenu(True)

        pimega450DAction = self._createAction("450D")
        pimega450DAction.triggered.connect(lambda: self.setTransformation("450D"))
        pimega450DAction.setIconVisibleInMenu(True)

        pimega540DAction = self._createAction("540D")
        pimega540DAction.triggered.connect(lambda: self.setTransformation("540D"))
        pimega540DAction.setIconVisibleInMenu(True)
        
        menu = qt.QMenu(self)
        menu.addAction(pimegaNoneAction)
        menu.addAction(pimega450DAction)
        menu.addAction(pimega540DAction)
        self.setMenu(menu)
        self.setPopupMode(qt.QToolButton.InstantPopup)

    def _createAction(self, model):
        icon = self.STATE[model, "icon"]
        text = self.STATE[model, "action"]
        return qt.QAction(icon, text, self)

    def setTransformation(self, model):
        """Configure the transformation according to model"""
        plot = self.plot()
        if plot is not None:

            if model == "450D":
                plot.transform = True
                plot.transformation = pimega450DTrans
                plot.do_transform()
                
            elif model == "None":
                plot.transform = False
                plot.transformation = noTrans
                plot.recover()

            icon, tooltip = self.STATE[model, "icon"], self.STATE[model, "state"]
            self.setIcon(icon)
            self.setToolTip(tooltip)

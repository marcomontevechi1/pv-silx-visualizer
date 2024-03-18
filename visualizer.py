#!/usr/bin/env python3

import sys
import numpy
from os import getenv, path
from copy import deepcopy
from sscPimega import pi450D

from silx.gui.plot import Plot2D
from silx.gui.plot.actions import PlotAction
from silx.gui import qt
from dotenv import load_dotenv
import epics


def global_transform(data):
    data_out = deepcopy(data)
    data_out = pi450D.view(data, -1)

    return data_out


class RestoreActionFile(PlotAction):
    '''
    WIP: Action to use SSCPimega to restore 
    image according with PiMega model.

    Its still missing the actual usage of SSCPimega.
    For now it just sums a value to each pixel of the image.
    '''

    def __init__(self, plot, parent=None):

        restore = qt.QIcon(path.join(path.dirname(path.realpath(__file__)),
                                     "./matrix.png"))

        super(RestoreActionFile, self).__init__(
            plot, icon=restore, text='Restore',
            tooltip='Geometrically restore PiMega image',
            triggered=self.__store_variable,
            checkable=True, parent=parent)

        self.restore = False
        self.plot.prev_data = None
        self.original_shape = None  # To check if image is already restored
        self.plot.sigActiveImageChanged.connect(self.keep_coherence)

    def keep_coherence(self):
        '''
        Make sure previous data keeps coherent
        when different image is selected in file
        '''

        self.plot.sigActiveImageChanged.disconnect(self.keep_coherence)

        activeImage = self.plot.getActiveImage()
        if activeImage is not None and activeImage.getData().shape == self.original_shape:
            self.plot.prev_data = activeImage.getData()

            if self.restore:
                new_data = global_transform(self.plot.prev_data)
                if new_data is not None:
                    activeImage.setData(new_data)

        self.plot.sigActiveImageChanged.connect(self.keep_coherence)

    def __store_variable(self, checked):
        '''
        Is the button clicked? If yes, restore each new image.

        Variable to tell if its supposed to restore each new
        image.
        '''

        self.plot.sigActiveImageChanged.disconnect(self.keep_coherence)

        self.restore = checked
        activeImage = self.plot.getActiveImage()

        if self.original_shape is None:
            self.original_shape = activeImage.getData().shape

        if not checked:
            if self.plot.prev_data is not None:
                activeImage.setData(self.plot.prev_data)
        else:
            if activeImage is not None:
                nowData = activeImage.getData()

                if nowData.shape == self.original_shape:
                    self.plot.prev_data = activeImage.getData()
                    new_data = global_transform(self.plot.prev_data)
                    activeImage.setData(new_data)

        self.plot.sigActiveImageChanged.connect(self.keep_coherence)


class RestoreActionPV(PlotAction):
    '''
    WIP: Action to use SSCPimega to restore 
    image according with PiMega model.

    Its still missing the actual usage of SSCPimega.
    For now it just sums a value to each pixel of the image.
    '''

    def __init__(self, plot, parent=None):

        restore = qt.QIcon(path.join(path.dirname(path.realpath(__file__)),
                                     "./matrix.png"))

        super(RestoreActionPV, self).__init__(
            plot, icon=restore, text='Restore',
            tooltip='Geometrically restore PiMega image',
            triggered=self.__store_variable,
            checkable=True, parent=parent)

        self.restore = False
        self.prev_data = None

    def __store_variable(self, checked):
        '''
        Is the button clicked? If yes, restore each new image.

        Variable to tell if its supposed to restore each new
        image.
        '''
        self.restore = checked
        activeImage = self.plot.getActiveImage()

        if not checked:
            if self.plot.prev_data is not None:
                self.plot.addImage(self.plot.prev_data)
        else:
            if activeImage is not None:
                self.plot.prev_data = activeImage.getData()
                new_data = global_transform(self.plot.prev_data)
                self.plot.addImage(new_data)


class PVPlotter(Plot2D):
    '''
    Class to get PV info and plot ArrayData image.
    It uses RestoreAction to apply SSCPimega restoration to image
    if desired.
    '''

    def __init__(self):
        super(PVPlotter, self).__init__()

        self.create_pvs()

        self.setWindowTitle(self.array_pv.pvname)
        self.action = RestoreActionPV(self, self)
        self.profile.addAction(self.action)

        self.array_pv.add_callback(self.pv_replot)
        self.pv_replot(value=self.array_pv.value)

    def create_pvs(self):
        '''
        Instantiate PV objects as class parameters.
        '''

        self.array_pv = epics.PV(getenv("EPICS_ARRAY_PV"), auto_monitor=True)
        self.width_pv = epics.PV(
            getenv("EPICS_ARRAY_WIDTH"), auto_monitor=True)
        self.height_pv = epics.PV(
            getenv("EPICS_ARRAY_HEIGHT"), auto_monitor=True)
        self.width_val = self.width_pv.value
        self.height_val = self.height_pv.value

    def update_dimensions(self, *args, **kwargs):
        '''
        Unfortunately needed.

        For some reason, if pv_replot tries to pv.get any
        pv object it times out, so for now this is what updates
        array dimensions in any eventual change.

        If array dimensions start changing often enough that this 
        generates sync problems, this obiously should be changed.
        '''
        pvname = kwargs["pvname"]
        value = kwargs["value"]
        if pvname == self.height_pv.pvname:
            self.height_val = value
        elif pvname == self.width_pv.pvname:
            self.width_val = value

    def pv_replot(self, *args, **kwargs):
        '''
        Upon new PV value, redo plot.
        '''
        if kwargs["value"] is not None:

            data = numpy.reshape(
                kwargs["value"], (self.height_val, self.width_val))
            self.prev_data = data

            if self.action.restore:
                data = global_transform(data)

            self.addImage(data)


def createWindow(parent, settings):
    # Local import to avoid early import (like h5py)
    # SOme libraries have to be configured first properly
    from silx.app.view.Viewer import Viewer
    from silx.app.view.ApplicationContext import ApplicationContext

    class MyApplicationContext(ApplicationContext):
        """This class is shared to all the silx view application."""

        def __init__(self, parent, settings=None):
            super(MyApplicationContext, self).__init__(parent, settings)

        def findPrintToolBar(self, plot):
            # FIXME: It would be better to use the Qt API
            return plot._outputToolBar

        def viewWidgetCreated(self, view, widget):
            """Called when the widget of the view was created.

            So we can custom it.
            """
            from silx.gui.plot import Plot2D
            if isinstance(widget, Plot2D):
                toolBar = self.findPrintToolBar(widget)
                restore_action = RestoreActionFile(widget, widget)
                toolBar.addAction(restore_action)

    class MyViewer(Viewer):

        def __init__(self, parent=None, settings=None):
            super(MyViewer, self).__init__(parent=None, settings=None)

        def plotPv(self):

            load_dotenv()

            if None in [getenv("EPICS_ARRAY_PV"),
                        getenv("EPICS_ARRAY_WIDTH"),
                        getenv("EPICS_ARRAY_HEIGHT")]:
                msg = qt.QMessageBox()
                msg_ = "Array PVs are misconfigured. Correct .env file or set the"
                msg_ += " environment variables before running this application."
                msg_ += " Desired variables are EPICS_ARRAY_PV, EPICS_ARRAY_WIDTH"
                msg_ += " and EPICS_ARRAY_HEGHT."
                msg.setText(msg_)
                msg.setIcon(qt.QMessageBox.Critical)
                msg.setWindowTitle("PVs not defined.")
                msg.exec()
                return

            self.PvPlot = PVPlotter()
            self.PvPlot.show()

        def createActions(self):
            super(MyViewer, self).createActions()
            action = qt.QAction("&Plot", self)
            action.setStatusTip("Plot PV")
            action.triggered.connect(self.plotPv)
            self._plotPvAction = action

        def createMenus(self):
            fileMenu = self.menuBar().addMenu("&File")
            fileMenu.addAction(self._openAction)
            fileMenu.addMenu(self._openRecentMenu)
            fileMenu.addAction(self._closeAllAction)
            fileMenu.addSeparator()
            fileMenu.addAction(self._exitAction)
            fileMenu.aboutToShow.connect(self._Viewer__updateFileMenu)

            pvMenu = self.menuBar().addMenu("&Plot PV")
            pvMenu.addAction(self._plotPvAction)

            optionMenu = self.menuBar().addMenu("&Options")
            optionMenu.addMenu(self._plotImageOrientationMenu)
            optionMenu.addMenu(self._plotBackendMenu)
            optionMenu.aboutToShow.connect(self._Viewer__updateOptionMenu)

            viewMenu = self.menuBar().addMenu("&Views")
            viewMenu.addAction(self._displayCustomNxdataWindow)

            helpMenu = self.menuBar().addMenu("&Help")
            helpMenu.addAction(self._aboutAction)
            helpMenu.addAction(self._documentationAction)

        def createApplicationContext(self, settings):
            return MyApplicationContext(self, settings)

    window = MyViewer(parent=parent, settings=settings)
    window.setWindowTitle(window.windowTitle() + " [custom]")
    return window


def main(args):
    from silx.app.view import main as silx_view_main
    # Monkey patch the main window creation
    silx_view_main.createWindow = createWindow
    # Use the default launcher
    silx_view_main.main(args)


if __name__ == '__main__':
    main(sys.argv)

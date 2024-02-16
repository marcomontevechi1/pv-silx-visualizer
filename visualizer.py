#!/usr/bin/env python3

import sys
import numpy
from os import getenv

from silx.gui.plot import Plot2D
from silx.gui.plot.actions import PlotAction
from silx.gui import qt
from dotenv import load_dotenv
import epics


class RestoreAction(PlotAction):
    def __init__(self, plot, parent=None):

        restore = qt.QIcon("./matrix.png")

        super(RestoreAction, self).__init__(
            plot, icon=restore, text='Restore',
            tooltip='Geometrically restore PiMega image',
            triggered=self.__store_variable,
            checkable=True, parent=parent)

        plot.sigActiveImageChanged.connect(self.__restore)
        self.restore = False
        self.prev_data = None

    def __store_variable(self, checked):
        '''
        Variable to tell if its supposed to restore each new
        image.
        '''
        self.restore = checked
        self.__restore()

        if not checked:
            self.plot.replot()

    def __restore(self):
        '''
        Restore current image.
        '''

        activeImage = self.plot.getActiveImage()

        if activeImage is not None:

            data = activeImage.getData()
            self.plot.sigActiveImageChanged.disconnect(self.__restore)

            if self.restore:

                self.prev_data = activeImage.getData()
                self.originalData = activeImage.getData()
                data += 500
                activeImage.setData(data)

            elif self.prev_data is not None:
                activeImage.setData(self.prev_data)
                self.prev_data = None

            self.plot.sigActiveImageChanged.connect(self.__restore)


class PVPlotter(Plot2D):

    def __init__(self):
        super(PVPlotter, self).__init__()

        self.create_pvs()

    def create_pvs(self):

        self.array_pv = epics.PV(getenv("EPICS_ARRAY_PV"), auto_monitor=True)
        self.width_pv = epics.PV(
            getenv("EPICS_ARRAY_WIDTH"), auto_monitor=True)
        self.height_pv = epics.PV(
            getenv("EPICS_ARRAY_HEIGHT"), auto_monitor=True)
        self.width_val = self.width_pv.value
        self.height_val = self.height_pv.value

        self.setWindowTitle(self.array_pv.pvname)
        action = RestoreAction(self, self)
        self.profile.addAction(action)

        self.array_pv.add_callback(self.pv_replot)
        self.pv_replot(value=self.array_pv.value)

    def update_dimensions(self, *args, **kwargs):
        pvname = kwargs["pvname"]
        value = kwargs["value"]
        if pvname == self.height_pv.pvname:
            self.height_val = value
        elif pvname == self.width_pv.pvname:
            self.width_val = value

    def pv_replot(self, *args, **kwargs):
        if kwargs["value"] is not None:

            data = numpy.reshape(
                kwargs["value"], (self.height_val, self.width_val))
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
                action = RestoreAction(widget, widget)
                toolBar.addAction(action)

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

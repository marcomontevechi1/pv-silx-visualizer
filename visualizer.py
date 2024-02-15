#!/usr/bin/env python

import sys
import numpy

from silx.gui import qt
from dotenv import load_dotenv
from os import getenv

def createWindow(parent, settings):
    # Local import to avoid early import (like h5py)
    #SOme libraries have to be configured first properly
    from silx.gui.plot.actions import PlotAction
    from silx.gui import qt
    from silx.app.view.Viewer import Viewer
    from silx.app.view.ApplicationContext import ApplicationContext
        
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
                    data+=500
                    activeImage.setData(data)
                    
                elif self.prev_data is not None:
                    activeImage.setData(self.prev_data)
                    self.prev_data = None
                    
                self.plot.sigActiveImageChanged.connect(self.__restore)
           
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
            print("Keep working here")

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
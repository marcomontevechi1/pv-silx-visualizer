#!/usr/bin/env python

import sys
import numpy

from silx.gui import qt

def createWindow(parent, settings):
    # Local import to avoid early import (like h5py)
    #SOme libraries have to be configured first properly
    from silx.gui.plot.actions import PlotAction
    from silx.app.view.Viewer import Viewer
    from silx.gui.utils import glutils
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
            print(checked)
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
        # def __init__(self, parent=None, settings=None):
        #     super(MyViewer, self).__init__()
            
        #     self.myMenus()
            
        # def myMenus(self):
        #     pv_plotter = self.menuBar().addMenu("&Get from PV")
        
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
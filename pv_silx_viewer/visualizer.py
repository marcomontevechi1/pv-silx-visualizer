#!/usr/bin/env python3

import sys
from os import path, environ
from copy import deepcopy
import functools

# Sometimes the following imports need to be local
# to avoid early imports. In this application this wasnt needed
# until now.
from silx.gui.plot import Plot2D
from silx.gui.plot.actions import PlotAction
from silx.gui import qt
from silx.app.view.Viewer import Viewer
from silx.app.view.ApplicationContext import ApplicationContext
from silx.app.view import main as silx_view_main
import numpy
import yaml
import epics

from TransformToolButton import TransformToolButton
from sscPimega import pi450D


VISUALIZER_PATH = path.dirname(path.realpath(__file__))


def recover(widget):
    """
    Sets image to the raw value.
    """

    activeImage = widget.getActiveImage()
    if widget.raw_data is not None:
        activeImage.setData(widget.raw_data)


def do_transform(widget):
    """
    Transform image according to transformation defined by
    TransformToolButton.

    Disconnects from signal to avoid recursive self-calling.
    """

    if widget.transform:
        activeImage = widget.getActiveImage()
        if activeImage is not None:
            widget.raw_data = activeImage.getData()
            new_data = widget.transformation(widget.raw_data)
            widget.sigActiveImageChanged.disconnect(widget.do_transform)
            activeImage.setData(new_data)
            widget.sigActiveImageChanged.connect(widget.do_transform)


class PVPlotter(Plot2D):
    '''
    Class to get PV info and plot ArrayData image.
    It uses RestoreAction to apply SSCPimega restoration to image
    if desired.
    '''

    def __init__(self, array_prefix, width_suffix="ArraySize0_RBV",
                 height_suffix="ArraySize1_RBV", *args, **kwargs):
        super(PVPlotter, self).__init__()

        self.array_prefix = array_prefix
        self.height_suffix = height_suffix
        self.width_suffix = width_suffix
        self.raw_data = None
        self.create_pvs()

        self.setWindowTitle(self.array_pv.pvname)

        self.recover = functools.partial(recover, self)
        transform = TransformToolButton(self, self)
        self.profile.addWidget(transform)

        self.array_pv.add_callback(self.pv_replot)
        self.pv_replot(value=self.array_pv.value)

        self.getKeepDataAspectRatioButton().keepDataAspectRatio()
        self.show()

    def create_pvs(self):
        '''
        Instantiate PV objects as class parameters.
        '''

        self.array_pv = epics.PV(
            self.array_prefix+"ArrayData", auto_monitor=True)
        self.width_pv = epics.PV(self.array_prefix+self.width_suffix)
        self.height_pv = epics.PV(self.array_prefix+self.height_suffix)

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

    def do_transform(self):
        """
        Transform image according to transformation defined
        by TransformToolButton.

        Is supposed to be called only when TransformToolButton
        is pressed. Other than that, pv_replot is responsible for
        transforming image before plotting.
        """

        if self.transform:
            activeImage = self.getActiveImage()
            if activeImage is not None:
                self.raw_data = activeImage.getData()
                new_data = self.transformation(self.raw_data)
                self.addImage(new_data)

    def pv_replot(self, *args, **kwargs):
        '''
        Upon new PV value, redo plot.

        Also responsible for transforming array before
        plotting because if plot before transforming,
        visualization effect is terrible.
        '''
        if kwargs["value"] is not None:

            data = numpy.reshape(
                kwargs["value"], (self.height_val, self.width_val))
            self.raw_data = data

            data = self.transformation(data)

            self.addImage(data)


class MyApplicationContext(ApplicationContext):
    """This class is shared to all the silx view application."""

    def __init__(self, parent, settings=None):
        super(MyApplicationContext, self).__init__(parent, settings)
        self.parent = parent

    def findPrintToolBar(self, plot):
        # FIXME: It would be better to use the Qt API
        return plot._outputToolBar

    def viewWidgetCreated(self, view, widget):
        """Called when the widget of the view was created.

        So we can custom it.

        For some bad reason this seems to be the standard 
        way offered by the framework to custom the widget.
        """
        from silx.gui.plot import Plot2D
        if isinstance(widget, Plot2D):
            toolBar = self.findPrintToolBar(widget)
            widget.raw_data = None  # Needed to keep transformation coherence
            # Needed to keep transformation coherence
            widget.recover = functools.partial(recover, widget)
            # Needed to keep transformation coherence
            widget.do_transform = functools.partial(do_transform, widget)
            transform = TransformToolButton(widget, widget)
            toolBar.addWidget(transform)
            self.parent.plot = widget
            self.parent.connect_plot_signal()


class FileViewer(Viewer):
    """
    A simple silx viewer with the option to apply a transformation
    to the plot or plot a defined PV.
    """

    def __init__(self, array_prefix, width_suffix="ArraySize0_RBV",
                 height_suffix="ArraySize1_RBV", parent=None, settings=None):
        super(FileViewer, self).__init__(parent=None, settings=None)

        self.array_pv = array_prefix
        self.width_pv = width_suffix
        self.height_pv = height_suffix

    def connect_plot_signal(self):
        """
        Must be defined here but only called by viewWidgetCreated()
        because silx customization framework is this weird...
        """
        self.plot.sigActiveImageChanged.connect(self.plot.do_transform)

    def plotPv(self):
        """
        Spawn PVPlotter
        """

        self.PvPlot = PVPlotter(array_prefix=self.array_pv,
                                width_suffix=self.width_pv,
                                height_suffix=self.height_pv)

    def createActions(self):
        """
        Add button to call plotPV method
        """
        super(FileViewer, self).createActions()
        action = qt.QAction("&Plot", self)
        action.setStatusTip("Plot PV")
        action.triggered.connect(self.plotPv)
        self._plotPvAction = action

    def createMenus(self):
        """
        Create basic menus.

        Maybe can just be a super(FileViewer, self).createMenus() ?
        """
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


def defCreateWindow(prefix, width, height):
    """Define and return a createWindow function with defined prefix,
    height and width values for FileViewer.

    It will be called by mainQt.
    """

    def create_window(parent, settings):

        window = FileViewer(array_prefix=prefix, width_suffix=width,
                            height_suffix=height, parent=parent,
                            settings=settings)
        window.setWindowTitle(window.windowTitle() + " [custom]")
        return window

    return create_window


def get_args(parser):

    parser.add_argument("-p", "--prefix",
                        type=str,
                        help="ArrayData PV prefix to plot instead of file")
    parser.add_argument("-w", "--width-suffix",
                        type=str,
                        default="ArraySize0_RBV",
                        help="PV to get width from. (default ArraySize0_RBV)")
    parser.add_argument("-a", "--height-suffix",
                        type=str,
                        default="ArraySize1_RBV",
                        help="PV to get height from. (ArraySize1_RBV)")
    parser.add_argument("-i", "--pv",
                        action='store_true',
                        default=False,
                        help="Only plot pv, ignore file viewer")

    return parser.parse_args()


def silx_main(argv):
    """
    Override of silx_view_main.main to add arguments
    Main function to launch the viewer as an application

    :param argv: Command line arguments
    :returns: exit status
    """
    parser = silx_view_main.createParser()
    options = parser.parse_args(argv[1:])
    silx_view_main.mainQt(options)


def find_in_dict(prefix, width, height, dic, fail=False):
    """tries to find prefix, width and height PV names
    in dictionary. If not found and fail=True, fail"""

    try:
        if prefix is None:
            prefix = dic["ARRAY_PREFIX"]
        if width is None:
            width = dic["WIDTH_SUFFIX"]
        if height is None:
            height = dic["HEIGHT_SUFFIX"]
    except KeyError:
        msg = "ARRAY_PREFIX, WIDTH_SUFFIX or HEIGHT_SUFFIX are not defined."
        msg += " Please define it as an environment variable, in defaults.yml"
        msg += " file or with --prefix, --width-suffix and --height-suffix"
        msg += " options."
        if fail:
            raise Exception(msg)

    return prefix, width, height


def getPVS(args):
    """
    Get PVs to plot in PVPlotter.
    If --prefix, --width-suffix or --height-suffix options are
        used, use values defined in them.
    If no options are used, try to load from file.
    If no file is defined, try to get from env vars.
    If no env vars are defined, exit and shout angrily at user. 
    """

    defaults_path = path.join(VISUALIZER_PATH, "defaults.yml")
    prefix, width, height = args.prefix, args.width_suffix, args.height_suffix

    if path.isfile(defaults_path):
        with open(path.join(VISUALIZER_PATH, "defaults.yml"), "r") as file:
            defaults = yaml.safe_load(file)

        prefix, width, height = find_in_dict(prefix, width,
                                             height, defaults)

    prefix, width, height = find_in_dict(prefix, width,
                                         height, environ,
                                         fail=True)

    return prefix, width, height


def main(args):
    '''
    Gets custom args to decide if its supposed to plot file or PV.
    Passes rest of arguments to silx_view_main
    '''

    parser = silx_view_main.createParser()
    args = get_args(parser)
    prefix, width, height = getPVS(args)

    if args.pv:

        app = qt.QApplication([])
        window = PVPlotter(prefix, width, height)
        window.show()

        result = app.exec()
        # remove ending warnings relative to QTimer
        app.deleteLater()

    else:
        # Monkey patch the main window creation
        silx_view_main.createWindow = defCreateWindow(prefix, width, height)
        # Use the default launcher
        silx_main(sys.argv)


if __name__ == '__main__':

    main(sys.argv)

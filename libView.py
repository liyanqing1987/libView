#!/bin/env python3
# -*- coding: utf-8 -*-
##################################
# FileName : libView.py
# Author   : yanqing.li
# Email    : liyanqing1987@163.com
# Created  : 2019-03-15 11:11:11
# Description :
# libView.py is used to show the
# contents of library files and 
# compare the data of different
# cells.
##################################
import os
import re
import sys
import copy
import numpy
import argparse
import collections

# For PyQt5 gui.
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, qApp, QFrame, QGridLayout, QFileDialog, QSplitter, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QLabel, QLineEdit, QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QComboBox, QDesktopWidget, QPushButton
from PyQt5.QtGui import QBrush
from PyQt5.QtCore import Qt

# For matplotlib related functions (need matplotlib 2.2.2 or higher version).
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib import pyplot
from mpl_toolkits.mplot3d import axes3d

# For library file parsing.
import libertyParser

os.environ["PYTHONUNBUFFERED"]="1"

def readArgs():
    """
    Read in arguments.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input',
                        nargs='+',
                        default=[],
                        help='Generate init configure file.')

    args = parser.parse_args()

    for inputFile in args.input:
        if not os.path.exists(inputFile):
            print('*Error*: ' + str(inputFile) + ': No such file.')
            sys.exit(1)

    return(args.input)

class pyplotFigure(FigureCanvasQTAgg):
    """
    Draw curve on GUI.
    """
    def __init__(self):
        self.fig = Figure()
        super(pyplotFigure, self).__init__(self.fig)

    def drawEmptyPlot(self, text='', xPoint=0.3, yPoint=0.5):
        """
        Draw empty figure.
        """
        self.fig.clf()
        ax = self.fig.add_subplot(111)
        ax.axis('off')
        ax.text(xPoint, yPoint, text)
        self.draw()

    def drawPlot(self, xList, yList, xLabel, yLabel, yUnit='', title=''):
        """
        Draw a curve with pyplot.
        """
        # Draw the figure.
        self.fig.clf()
        ax = self.fig.add_subplot(111)
        ax.plot(xList, yList, 'ro-')

        # If x axis items is string.
        self.fig.subplots_adjust(bottom=0.2)
        xticksLabels = ax.get_xticklabels()
        for xticksLabel in xticksLabels:
            xticksLabel.set_rotation(30)
            xticksLabel.set_fontsize(12)

        # Set x/y labels. 
        ax.set_xlabel(xLabel)
        ax.set_ylabel(yLabel)

        # Show grid. 
        ax.grid(True)

        # Set title.
        if title != '':
            self.fig.suptitle(title)

        # Get value info.
        xMin = min(xList)
        xMax = max(xList)
        yMin = min(yList)
        yMax = max(yList)

        # Define the curve range.
        if len(xList) == 1:
            xLim = [xMin-1, xMax+1]
            yLim = [yMin-1, yMax+1]
        else:
            xLim = [xMin, xMax]
            if yMin == yMax:
                yLim = [yMin-1, yMax+1]
            else:
                yLim = [1.1*yMin-0.1*yMax, 1.1*yMax-0.1*yMin]

        ax.set_xlim(xLim)
        ax.set_ylim(yLim)

        # Show all point values, or peak value. 
        for i in range(len(xList)):
            ax.text(xList[i], yList[i], str(yList[i]) + ' ' + str(yUnit))

        # Show figure.
        self.draw()

    def draw3DPlot(self, xArray, yArray, zArray, xLabel, yLabel, zLabel, title=''):
        """
        Draw a 3D curve with pyplot.
        """
        # Draw the figure.
        self.fig.clf()
        ax = self.fig.add_subplot(111, projection='3d')
        ax.plot_wireframe(xArray, yArray, zArray)

        # Set x/y/z labels. 
        ax.set_xlabel(xLabel)
        ax.set_ylabel(yLabel)
        ax.set_zlabel(zLabel)

        # Show grid. 
        ax.grid(True)

        # Set title.
        if title != '':
            self.fig.suptitle(title)

        # Show figure.
        self.draw()

class mainWindow(QMainWindow):
    """
    GUI.
    """
    def __init__(self, inputFileList):
        super().__init__()
        self.initVars()
        self.initUI()

        for inputFile in inputFileList:
            self.loadLibFile(inputFile)

    def initVars(self):
        self.libDic = collections.OrderedDict()
        self.specifiedLibDic = collections.OrderedDict()
        self.specifiedCellCount = 0

        self.leakagePowerTabMultiEnable = False
        self.timingTabMultiEnable = False
        self.internalPowerTabMultiEnable = False

        self.leakagePowerUnit = ''
        self.timingUnit = ''
        self.internalPowerUnit = ''

        self.areaTabFigure = pyplotFigure()
        self.leakagePowerTabFigure = pyplotFigure()
        self.timingTabFigure = pyplotFigure()
        self.internalPowerTabFigure = pyplotFigure()

    def centerWindow(self):
        """
        Move the input GUI window into the center of the computer windows.
        """
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def initUI(self):
        """
        Main process, draw the main graphic.
        """
        # main window. 
        self.cellListFrame = QFrame(self)
        self.mainFrame = QFrame(self)

        self.mainSplitter = QSplitter(Qt.Horizontal)
        self.mainSplitter.addWidget(self.cellListFrame)
        self.mainSplitter.addWidget(self.mainFrame)
        self.setCentralWidget(self.mainSplitter)

        self.mainSplitter.setStretchFactor(0, 1)
        self.mainSplitter.setStretchFactor(1, 8)
        self.mainSplitter.setSizes([300, 1500])
        self.mainSplitter.setHandleWidth(10)

        # Init Gui.
        self.genMenubar()
        self.initGui()

        # Size and position. 
        self.resize(1600, 600)
        self.centerWindow()
        self.setWindowTitle('libView')


#### For Menu Bar (begin) ####
    def genMenubar(self):
        """
        Generate menubar.
        """
        menubar = self.menuBar()

        # File
        loadAction = QAction('Load', self)
        loadAction.triggered.connect(lambda:self.loadLibFile())

        exitAction = QAction('Quit', self)
        exitAction.triggered.connect(qApp.quit)

        fileMenu = menubar.addMenu('File')
        fileMenu.addAction(loadAction)
        fileMenu.addAction(exitAction)

    def loadLibFile(self, libraryFile=''):
        """
        Load library file.
        """
        if libraryFile == '':
            (libraryFile, fileType) = QFileDialog.getOpenFileName(self, 'Load library file', '.', "Library Files (*.lib)")

        if libraryFile:
            print('Loading library file "' + str(libraryFile) + '" ...')
            libraryFileName = os.path.basename(libraryFile)

            if libraryFileName in self.libDic:
                print('*Warning*: library file "' + str(libraryFileName) + '" has ever been loaded!')
                return
            else:
                self.libDic[libraryFileName] = collections.OrderedDict()
                myParser = libertyParser.libertyParser(libraryFile)
                self.libDic[libraryFileName]['parser'] = myParser
                cellList = myParser.getCellList()
                self.libDic[libraryFileName]['cellList'] = cellList

                # Get leakagePower/timing/internalPower unit.
                unitDic = myParser.getUnit()

                if 'leakage_power_unit' in unitDic:
                    leakagePowerUnit = re.sub('"', '', unitDic['leakage_power_unit'])
                    leakagePowerUnit = re.sub('\d', '', leakagePowerUnit)
                    if self.leakagePowerUnit == '':
                        self.leakagePowerUnit = leakagePowerUnit
                        self.internalPowerUnit = leakagePowerUnit
                    elif self.leakagePowerUnit != leakagePowerUnit:
                        print('*Warning*: leakage_power_unit is "' + str(leakagePowerUnit) + '" on library file "' + str(libraryFile) + '", it is different with original library file, will ignore it.')

                if 'time_unit' in unitDic:
                    timingUnit = re.sub('"', '', unitDic['time_unit'])
                    timingUnit = re.sub('\d', '', timingUnit)
                    if self.timingUnit == '':
                        self.timingUnit = timingUnit
                    elif self.timingUnit != timingUnit:
                        print('*Warning*: time_unit is "' + str(timingUnit) + '" on library file "' + str(libraryFile) + '", it is different with original library file, will ignore it.')

            self.updateCellListTree()
#### For Menu Bar (end) ####


#### Init Gui (begin) ####
    def initGui(self):
        """
        Init Gui, init self.cellListFrame and self.mainFrame.
        """
        self.initCellListFrame()
        self.initMainFrame()

    def initCellListFrame(self):
        """
        Init liberty-cell information on left sideBar.
        """
        # self.cellListFrame
        self.cellListFrame.setFrameShadow(QFrame.Raised)
        self.cellListFrame.setFrameShape(QFrame.Box)

        self.cellSelectLine = QLineEdit()
        cellSelectButton = QPushButton('Select', self.cellListFrame)
        cellSelectButton.clicked.connect(self.selectCell)

        self.cellListTree = QTreeWidget(self.cellListFrame)
        self.cellListTree.setColumnCount(1)
        self.cellListTree.setHeaderLabel('Lib->Cell')
        self.cellListTree.clicked.connect(self.cellListBeClicked)

        # self.cellListFrame - Grid
        cellListFrameGrid = QGridLayout()

        cellListFrameGrid.addWidget(self.cellSelectLine, 0, 0)
        cellListFrameGrid.addWidget(cellSelectButton, 0, 1)
        cellListFrameGrid.addWidget(self.cellListTree, 1, 0, 1, 2)

        cellListFrameGrid.setRowStretch(0, 1)
        cellListFrameGrid.setRowStretch(1, 20)
        cellListFrameGrid.setColumnStretch(0, 10)
        cellListFrameGrid.setColumnStretch(1, 1)

        self.cellListFrame.setLayout(cellListFrameGrid)

    def initMainFrame(self):
        """
        Init self.mainFrame.
        """
        # self.mainFram
        self.mainFrame.setFrameShadow(QFrame.Raised)
        self.mainFrame.setFrameShape(QFrame.Box)

        self.libLabel = QLabel('Lib', self.mainFrame)
        self.libLabel.setStyleSheet("font-weight: bold;")
        self.libLine = QLineEdit()

        self.cellLabel = QLabel('Cell', self.mainFrame)
        self.cellLabel.setStyleSheet("font-weight: bold;")
        self.cellLine = QLineEdit()

        self.tabWidget = QTabWidget(self.mainFrame)

        # self.mainFram - Grid
        mainFrameGrid = QGridLayout()

        mainFrameGrid.addWidget(self.libLabel, 0, 0)
        mainFrameGrid.addWidget(self.libLine, 0, 1)
        mainFrameGrid.addWidget(self.cellLabel, 1, 0)
        mainFrameGrid.addWidget(self.cellLine, 1, 1)
        mainFrameGrid.addWidget(self.tabWidget, 2, 0, 1, 2)

        mainFrameGrid.setRowStretch(0, 1)
        mainFrameGrid.setRowStretch(1, 1)
        mainFrameGrid.setRowStretch(2, 10)

        self.mainFrame.setLayout(mainFrameGrid)

        # Init self.tabWidget
        self.initTabWidget()

    def initTabWidget(self):
        """
        Init self.tabWidget.
        """
        self.areaTab = QWidget()
        self.leakagePowerTab = QWidget()
        self.timingTab = QWidget()
        self.internalPowerTab = QWidget()

        self.tabWidget.addTab(self.areaTab, 'Area')
        self.tabWidget.addTab(self.leakagePowerTab, 'Leakage Power')
        self.tabWidget.addTab(self.timingTab, 'Timing')
        self.tabWidget.addTab(self.internalPowerTab, 'Internal Power')

        self.tabWidget.currentChanged.connect(self.tabWidgetCurrentChanged)

        # Init sub-tabs.
        self.initAreaTab()
        self.initLeakagePowerTab()
        self.initTimingTab()
        self.initInternalPowerTab()

    def tabWidgetCurrentChanged(self):
        """
        Update the related QLabel if the current tab is changed. 
        """
        if self.tabWidget.currentIndex() == 0:
            self.updateAreaTabFigure()
        elif self.tabWidget.currentIndex() == 1:
            self.updateLeakagePowerTabFigure()
        elif self.tabWidget.currentIndex() == 2:
            self.updateTimingTabFigure()
        elif self.tabWidget.currentIndex() == 3:
            self.updateInternalPowerTabFigure()

    def initAreaTab(self):
        """
        Init self.areaTab.
        """
        # self.areaTab
        self.areaTabTable = QTableWidget(self.areaTab)
        self.areaTabTable.setShowGrid(True)
        self.areaTabTable.setColumnCount(3)
        self.areaTabTable.setHorizontalHeaderLabels(['LIB', 'CELL', 'area'])

        # self.areaTab - Grid
        areaTabGrid = QGridLayout()

        areaTabGrid.addWidget(self.areaTabTable, 0, 0)
        areaTabGrid.addWidget(self.areaTabFigure, 0, 1)

        areaTabGrid.setColumnStretch(0, 1)
        areaTabGrid.setColumnStretch(1, 1)

        self.areaTab.setLayout(areaTabGrid)

        # Show text "Cell Area Curve"
        self.updateAreaTabFigure()

    def initLeakagePowerTab(self):
        """
        Init self.leakagePowerTab.
        """
        # self.leakagePowerTab
        self.leakagePowerTabFrame = QFrame(self.leakagePowerTab)
        self.leakagePowerTabFrame.setFrameShadow(QFrame.Raised)
        self.leakagePowerTabFrame.setFrameShape(QFrame.Box)

        self.leakagePowerTabTable = QTableWidget(self.leakagePowerTab)
        self.leakagePowerTabTable.setShowGrid(True)
        self.leakagePowerTabTable.setColumnCount(5)
        self.leakagePowerTabTable.setHorizontalHeaderLabels(['LIB', 'CELL', 'when', 'related_pg_pin', 'value'])

        # self.leakagePowerTab - Grid
        leakagePowerTabGrid = QGridLayout()

        leakagePowerTabGrid.addWidget(self.leakagePowerTabFrame, 0, 0, 1, 2)
        leakagePowerTabGrid.addWidget(self.leakagePowerTabTable, 1, 0)
        leakagePowerTabGrid.addWidget(self.leakagePowerTabFigure, 1, 1)

        leakagePowerTabGrid.setRowStretch(0, 1)
        leakagePowerTabGrid.setRowStretch(1, 20)
        leakagePowerTabGrid.setColumnStretch(0, 1)
        leakagePowerTabGrid.setColumnStretch(1, 1)

        self.leakagePowerTab.setLayout(leakagePowerTabGrid)

        # Init self.leakagePowerTabFrame
        self.initLeakagePowerTabFrame()

    def initLeakagePowerTabFrame(self):
        # self.leakagePowerTabFrame
        self.leakagePowerTabWhenLabel = QLabel('when:', self.leakagePowerTabFrame)
        self.leakagePowerTabWhenLabel.setAlignment(Qt.AlignRight)
        self.leakagePowerTabWhenCombo = QComboBox(self.leakagePowerTabFrame)
        self.leakagePowerTabWhenCombo.activated.connect(self.updateLeakagePowerTabRelatedPgPinCombo)

        self.leakagePowerTabRelatedPgPinLabel = QLabel('related_pg_pin:', self.leakagePowerTabFrame)
        self.leakagePowerTabRelatedPgPinLabel.setAlignment(Qt.AlignRight)
        self.leakagePowerTabRelatedPgPinCombo = QComboBox(self.leakagePowerTabFrame)
        self.leakagePowerTabRelatedPgPinCombo.activated.connect(self.updateLeakagePowerTabTable)

        self.leakagePowerTabEmptyLabel = QLabel('')

        # self.leakagePowerTabFrame - Grid
        leakagePowerTabFrameGrid = QGridLayout()

        leakagePowerTabFrameGrid.addWidget(self.leakagePowerTabWhenLabel, 0, 0)
        leakagePowerTabFrameGrid.addWidget(self.leakagePowerTabWhenCombo, 0, 1)
        leakagePowerTabFrameGrid.addWidget(self.leakagePowerTabRelatedPgPinLabel, 0, 2)
        leakagePowerTabFrameGrid.addWidget(self.leakagePowerTabRelatedPgPinCombo, 0, 3)
        leakagePowerTabFrameGrid.addWidget(self.leakagePowerTabEmptyLabel, 0, 4, 1, 6)

        self.leakagePowerTabFrame.setLayout(leakagePowerTabFrameGrid)

    def initTimingTab(self):
        """
        Init self.timingTab.
        """
        # self.timingTab
        self.timingTabBundleBusFrame = QFrame(self.timingTab)
        self.timingTabBundleBusFrame.setFrameShadow(QFrame.Raised)
        self.timingTabBundleBusFrame.setFrameShape(QFrame.Box)

        self.timingTabPinFrame = QFrame(self.timingTab)
        self.timingTabPinFrame.setFrameShadow(QFrame.Raised)
        self.timingTabPinFrame.setFrameShape(QFrame.Box)

        self.timingTabTable = QTableWidget(self.timingTab)
        self.timingTabTable.setShowGrid(True)

        # self.timingTab - Grid
        timingTabGrid = QGridLayout()

        timingTabGrid.addWidget(self.timingTabBundleBusFrame, 0, 0, 1, 1)
        timingTabGrid.addWidget(self.timingTabPinFrame, 0, 1, 1, 5)
        timingTabGrid.addWidget(self.timingTabTable, 1, 0, 1, 3)
        timingTabGrid.addWidget(self.timingTabFigure, 1, 3, 1, 3)

        timingTabGrid.setRowStretch(0, 1)
        timingTabGrid.setRowStretch(1, 20)
        #timingTabGrid.setColumnStretch(0, 1)
        #timingTabGrid.setColumnStretch(1, 3)

        self.timingTab.setLayout(timingTabGrid)

        # Init self.timingTabPinFrame
        self.initTimingTabBundleBusFrame()
        self.initTimingTabPinFrame()

    def initTimingTabBundleBusFrame(self):
        # self.timingTabBundleBusFrame
        self.timingTabBundleLabel = QLabel('bundle:', self.timingTabBundleBusFrame)
        self.timingTabBundleLabel.setAlignment(Qt.AlignRight)
        self.timingTabBundleCombo = QComboBox(self.timingTabBundleBusFrame)
        self.timingTabBundleCombo.activated.connect(self.updateTimingTabPinCombo)

        self.timingTabBusLabel = QLabel('bus:', self.timingTabBundleBusFrame)
        self.timingTabBusLabel.setAlignment(Qt.AlignRight)
        self.timingTabBusCombo = QComboBox(self.timingTabBundleBusFrame)
        self.timingTabBusCombo.activated.connect(self.updateTimingTabPinCombo)

        # self.timingTabBundleBusFrame - Grid
        timingTabBundleBusFrameGrid = QGridLayout()

        timingTabBundleBusFrameGrid.addWidget(self.timingTabBundleLabel, 0, 0)
        timingTabBundleBusFrameGrid.addWidget(self.timingTabBundleCombo, 0, 1)
        timingTabBundleBusFrameGrid.addWidget(self.timingTabBusLabel, 1, 0)
        timingTabBundleBusFrameGrid.addWidget(self.timingTabBusCombo, 1, 1)

        self.timingTabBundleBusFrame.setLayout(timingTabBundleBusFrameGrid)

    def initTimingTabPinFrame(self):
        # self.timingTabPinFrame
        self.timingTabPinLabel = QLabel('pin:', self.timingTabPinFrame)
        self.timingTabPinLabel.setAlignment(Qt.AlignRight)
        self.timingTabPinCombo = QComboBox(self.timingTabPinFrame)
        self.timingTabPinCombo.activated.connect(self.updateTimingTabRelatedPinCombo)

        self.timingTabRelatedPinLabel = QLabel('related_pin:', self.timingTabPinFrame)
        self.timingTabRelatedPinLabel.setAlignment(Qt.AlignRight)
        self.timingTabRelatedPinCombo = QComboBox(self.timingTabPinFrame)
        self.timingTabRelatedPinCombo.activated.connect(self.updateTimingTabRelatedPgPinCombo)

        self.timingTabRelatedPgPinLabel = QLabel('related_pg_pin:', self.timingTabPinFrame)
        self.timingTabRelatedPgPinLabel.setAlignment(Qt.AlignRight)
        self.timingTabRelatedPgPinCombo = QComboBox(self.timingTabPinFrame)
        self.timingTabRelatedPgPinCombo.activated.connect(self.updateTimingTabTimingSenseCombo)

        self.timingTabTimingSenseLabel = QLabel('timing_sense:', self.timingTabPinFrame)
        self.timingTabTimingSenseLabel.setAlignment(Qt.AlignRight)
        self.timingTabTimingSenseCombo = QComboBox(self.timingTabPinFrame)
        self.timingTabTimingSenseCombo.activated.connect(self.updateTimingTabTimingTypeCombo)

        self.timingTabTimingTypeLabel = QLabel('timing_type:', self.timingTabPinFrame)
        self.timingTabTimingTypeLabel.setAlignment(Qt.AlignRight)
        self.timingTabTimingTypeCombo = QComboBox(self.timingTabPinFrame)
        self.timingTabTimingTypeCombo.activated.connect(self.updateTimingTabWhenCombo)

        self.timingTabWhenLabel = QLabel('when:', self.timingTabPinFrame)
        self.timingTabWhenLabel.setAlignment(Qt.AlignRight)
        self.timingTabWhenCombo = QComboBox(self.timingTabPinFrame)
        self.timingTabWhenCombo.activated.connect(self.updateTimingTabTableTypeCombo)

        self.timingTabTableTypeLabel = QLabel('Table Type:', self.timingTabPinFrame)
        self.timingTabTableTypeLabel.setAlignment(Qt.AlignRight)
        self.timingTabTableTypeCombo = QComboBox(self.timingTabPinFrame)
        self.timingTabTableTypeCombo.activated.connect(self.updateTimingTabIndexCombo)

        self.timingTabIndex1Label = QLabel('index_1:', self.timingTabPinFrame)
        self.timingTabIndex1Label.setAlignment(Qt.AlignRight)
        self.timingTabIndex1Combo = QComboBox(self.timingTabPinFrame)
        self.timingTabIndex1Combo.activated.connect(self.updateTimingTabTable)

        self.timingTabIndex2Label = QLabel('index_2:', self.timingTabPinFrame)
        self.timingTabIndex2Label.setAlignment(Qt.AlignRight)
        self.timingTabIndex2Combo = QComboBox(self.timingTabPinFrame)
        self.timingTabIndex2Combo.activated.connect(self.updateTimingTabTable)

        # self.timingTabPinFrame - Grid
        timingTabPinFrameGrid = QGridLayout()

        timingTabPinFrameGrid.addWidget(self.timingTabPinLabel, 0, 0)
        timingTabPinFrameGrid.addWidget(self.timingTabPinCombo, 0, 1)
        timingTabPinFrameGrid.addWidget(self.timingTabRelatedPinLabel, 0, 2)
        timingTabPinFrameGrid.addWidget(self.timingTabRelatedPinCombo, 0, 3)
        timingTabPinFrameGrid.addWidget(self.timingTabRelatedPgPinLabel, 0, 4)
        timingTabPinFrameGrid.addWidget(self.timingTabRelatedPgPinCombo, 0, 5)
        timingTabPinFrameGrid.addWidget(self.timingTabTimingSenseLabel, 0, 6)
        timingTabPinFrameGrid.addWidget(self.timingTabTimingSenseCombo, 0, 7)
        timingTabPinFrameGrid.addWidget(self.timingTabTimingTypeLabel, 0, 8)
        timingTabPinFrameGrid.addWidget(self.timingTabTimingTypeCombo, 0, 9)
        timingTabPinFrameGrid.addWidget(self.timingTabWhenLabel, 1, 0)
        timingTabPinFrameGrid.addWidget(self.timingTabWhenCombo, 1, 1)
        timingTabPinFrameGrid.addWidget(self.timingTabTableTypeLabel, 1, 2)
        timingTabPinFrameGrid.addWidget(self.timingTabTableTypeCombo, 1, 3)
        timingTabPinFrameGrid.addWidget(self.timingTabIndex1Label, 1, 4)
        timingTabPinFrameGrid.addWidget(self.timingTabIndex1Combo, 1, 5)
        timingTabPinFrameGrid.addWidget(self.timingTabIndex2Label, 1, 6)
        timingTabPinFrameGrid.addWidget(self.timingTabIndex2Combo, 1, 7)

        self.timingTabPinFrame.setLayout(timingTabPinFrameGrid)

    def initInternalPowerTab(self):
        """
        Init self.internalPowerTab.
        """
        # self.internalPowerTab
        self.internalPowerTabBundleBusFrame = QFrame(self.internalPowerTab)
        self.internalPowerTabBundleBusFrame.setFrameShadow(QFrame.Raised)
        self.internalPowerTabBundleBusFrame.setFrameShape(QFrame.Box)

        self.internalPowerTabPinFrame = QFrame(self.internalPowerTab)
        self.internalPowerTabPinFrame.setFrameShadow(QFrame.Raised)
        self.internalPowerTabPinFrame.setFrameShape(QFrame.Box)

        self.internalPowerTabTable = QTableWidget(self.internalPowerTab)

        # self.internalPowerTab - Grid
        internalPowerTabGrid = QGridLayout()

        internalPowerTabGrid.addWidget(self.internalPowerTabBundleBusFrame, 0, 0, 1, 1)
        internalPowerTabGrid.addWidget(self.internalPowerTabPinFrame, 0, 1, 1, 5)
        internalPowerTabGrid.addWidget(self.internalPowerTabTable, 1, 0, 1, 3)
        internalPowerTabGrid.addWidget(self.internalPowerTabFigure, 1, 3, 1, 3)

        internalPowerTabGrid.setRowStretch(0, 1)
        internalPowerTabGrid.setRowStretch(1, 20)
        #internalPowerTabGrid.setColumnStretch(0, 1)
        #internalPowerTabGrid.setColumnStretch(1, 1)

        self.internalPowerTab.setLayout(internalPowerTabGrid)

        # Init self.internalPowerTabPinFrame
        self.initInternalPowerTabBundleBusFrame()
        self.initInternalPowerTabPinFrame()

    def initInternalPowerTabBundleBusFrame(self):
        # self.internalPowerTabBundleBusFrame
        self.internalPowerTabBundleLabel = QLabel('bundle:', self.internalPowerTabBundleBusFrame)
        self.internalPowerTabBundleLabel.setAlignment(Qt.AlignRight)
        self.internalPowerTabBundleCombo = QComboBox(self.internalPowerTabBundleBusFrame)
        self.internalPowerTabBundleCombo.activated.connect(self.updateInternalPowerTabPinCombo)

        self.internalPowerTabBusLabel = QLabel('bus:', self.internalPowerTabBundleBusFrame)
        self.internalPowerTabBusLabel.setAlignment(Qt.AlignRight)
        self.internalPowerTabBusCombo = QComboBox(self.internalPowerTabBundleBusFrame)
        self.internalPowerTabBusCombo.activated.connect(self.updateInternalPowerTabPinCombo)

        # self.internalPowerTabBundleBusFrame - Grid
        internalPowerTabBundleBusFrameGrid = QGridLayout()

        internalPowerTabBundleBusFrameGrid.addWidget(self.internalPowerTabBundleLabel, 0, 0)
        internalPowerTabBundleBusFrameGrid.addWidget(self.internalPowerTabBundleCombo, 0, 1)
        internalPowerTabBundleBusFrameGrid.addWidget(self.internalPowerTabBusLabel, 1, 0)
        internalPowerTabBundleBusFrameGrid.addWidget(self.internalPowerTabBusCombo, 1, 1)

        self.internalPowerTabBundleBusFrame.setLayout(internalPowerTabBundleBusFrameGrid)

    def initInternalPowerTabPinFrame(self):
        # self.internalPowerTabPinFrame
        self.internalPowerTabPinLabel = QLabel('pin:', self.internalPowerTabPinFrame)
        self.internalPowerTabPinLabel.setAlignment(Qt.AlignRight)
        self.internalPowerTabPinCombo = QComboBox(self.internalPowerTabPinFrame)
        self.internalPowerTabPinCombo.activated.connect(self.updateInternalPowerTabRelatedPinCombo)

        self.internalPowerTabRelatedPinLabel = QLabel('related_pin:', self.internalPowerTabPinFrame)
        self.internalPowerTabRelatedPinLabel.setAlignment(Qt.AlignRight)
        self.internalPowerTabRelatedPinCombo = QComboBox(self.internalPowerTabPinFrame)
        self.internalPowerTabRelatedPinCombo.activated.connect(self.updateInternalPowerTabRelatedPgPinCombo)

        self.internalPowerTabRelatedPgPinLabel = QLabel('related_pg_pin:', self.internalPowerTabPinFrame)
        self.internalPowerTabRelatedPgPinLabel.setAlignment(Qt.AlignRight)
        self.internalPowerTabRelatedPgPinCombo = QComboBox(self.internalPowerTabPinFrame)
        self.internalPowerTabRelatedPgPinCombo.activated.connect(self.updateInternalPowerTabWhenCombo)

        self.internalPowerTabEmptyLabel = QLabel('', self.internalPowerTabPinFrame)

        self.internalPowerTabWhenLabel = QLabel('when:', self.internalPowerTabPinFrame)
        self.internalPowerTabWhenLabel.setAlignment(Qt.AlignRight)
        self.internalPowerTabWhenCombo = QComboBox(self.internalPowerTabPinFrame)
        self.internalPowerTabWhenCombo.activated.connect(self.updateInternalPowerTabTableTypeCombo)

        self.internalPowerTabTableTypeLabel = QLabel('Table Type:', self.internalPowerTabPinFrame)
        self.internalPowerTabTableTypeLabel.setAlignment(Qt.AlignRight)
        self.internalPowerTabTableTypeCombo = QComboBox(self.internalPowerTabPinFrame)
        self.internalPowerTabTableTypeCombo.activated.connect(self.updateInternalPowerTabIndexCombo)

        self.internalPowerTabIndex1Label = QLabel('index_1:', self.internalPowerTabPinFrame)
        self.internalPowerTabIndex1Label.setAlignment(Qt.AlignRight)
        self.internalPowerTabIndex1Combo = QComboBox(self.internalPowerTabPinFrame)
        self.internalPowerTabIndex1Combo.activated.connect(self.updateInternalPowerTabTable)

        self.internalPowerTabIndex2Label = QLabel('index_2:', self.internalPowerTabPinFrame)
        self.internalPowerTabIndex2Label.setAlignment(Qt.AlignRight)
        self.internalPowerTabIndex2Combo = QComboBox(self.internalPowerTabPinFrame)
        self.internalPowerTabIndex2Combo.activated.connect(self.updateInternalPowerTabTable)

        # self.internalPowerTabPinFrame - Grid
        internalPowerTabPinFrameGrid = QGridLayout()

        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabPinLabel, 0, 0)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabPinCombo, 0, 1)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabRelatedPinLabel, 0, 2)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabRelatedPinCombo, 0, 3)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabRelatedPgPinLabel, 0, 4)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabRelatedPgPinCombo, 0, 5)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabEmptyLabel, 0, 6, 1, 4)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabWhenLabel, 1, 0)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabWhenCombo, 1, 1)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabTableTypeLabel, 1, 2)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabTableTypeCombo, 1, 3)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabIndex1Label, 1, 4)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabIndex1Combo, 1, 5)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabIndex2Label, 1, 6)
        internalPowerTabPinFrameGrid.addWidget(self.internalPowerTabIndex2Combo, 1, 7)

        self.internalPowerTabPinFrame.setLayout(internalPowerTabPinFrameGrid)
#### Init Gui (end) ####


#### Update Cell List Tree (begin) ####
    def sortCellWithSize(self, origCellList):
        """
        If cell format match "(.+?)D(\d+)\D.*" (\d+ is the cell size), sort the cell list with cell size.
        """
        seriesCellCompile = re.compile('^(.+?)D(\d+)(BWP.*)$')
        seriesCellDic = collections.OrderedDict()
        seriesCellDic['zzz'] = []

        # Get <cell_head><cell_size>_<cell_tail> cells.
        for cellName in origCellList:
            if seriesCellCompile.match(cellName):
                myMatch = seriesCellCompile.match(cellName)
                cellHead = myMatch.group(1)
                cellTail = myMatch.group(3)
                seriesCell = str(cellHead) + str(cellTail)
                seriesCellDic.setdefault(seriesCell, [])
                seriesCellDic[seriesCell].append(cellName)
            else:
                seriesCellDic['zzz'].append(cellName)

        # Move sign cell sub-dict to 'zzz'.
        seriesCellList = list(seriesCellDic.keys())
        for seriesCell in seriesCellList:
            if seriesCell != 'zzz':
                cellList = seriesCellDic[seriesCell]
                if len(cellList) == 1:
                    seriesCellListValue = cellList[0]
                    seriesCellDic.pop(seriesCell)
                    seriesCellDic['zzz'].append(seriesCellListValue)

        # Sort sub-dict with cell size.
        sortedCellList = []
        seriesCellList = list(seriesCellDic.keys())
        seriesCellList.sort()

        for seriesCell in seriesCellList:
            seriesCellList = seriesCellDic[seriesCell]
            if seriesCell == 'zzz':
                seriesCellList.sort()
            else:
                seriesCellList.sort(key=lambda x:int(seriesCellCompile.match(x).group(2)))
            for cellName in seriesCellList:
                sortedCellList.append(cellName)

        return(sortedCellList)

    def updateCellListTree(self):
        """
        Update liberty-cell information on left sideBar.
        """
        self.cellListTree.clear()

        for libraryFileName in self.libDic.keys():
            libItem = QTreeWidgetItem(self.cellListTree)
            libItem.setText(0, libraryFileName)
            libItem.setForeground(0, QBrush(Qt.blue))
            cellList = list(self.libDic[libraryFileName]['cellList'])

            # Sort cell name with cell size (***D\d+***). 
            sortedCellList = self.sortCellWithSize(cellList)

            # Show cells on left sideBar. 
            for cellName in sortedCellList:
                cellItem = QTreeWidgetItem(libItem)
                cellItem.setText(0, cellName)
                cellItem.setForeground(0, QBrush(Qt.green))
                if (libraryFileName in self.specifiedLibDic) and (cellName in self.specifiedLibDic[libraryFileName]):
                    cellItem.setCheckState(0, Qt.Checked)
                else:
                    cellItem.setCheckState(0, Qt.Unchecked)

        self.cellListTree.expandAll()

    def getCellAreaInfo(self, libraryFileName, cellName, libCellAreaDic):
        self.specifiedLibDic[libraryFileName][cellName]['area'] = libCellAreaDic[cellName]

    def getCellLeakagePowerInfo(self, libraryFileName, cellName, libCellLeakagePowerDic):
        self.specifiedLibDic[libraryFileName][cellName]['leakage_power'] = []
        self.leakagePowerTabDic[libraryFileName][cellName]['leakage_power'] = collections.OrderedDict()

        for cellLeakagePowerDic in libCellLeakagePowerDic[cellName]:
            cellLeakagePowerValue = cellLeakagePowerDic.get('value', 'N/A')
            cellLeakagePowerValue = re.sub('"', '', cellLeakagePowerValue)
            cellLeakagePowerWhen = cellLeakagePowerDic.get('when', 'N/A')
            cellLeakagePowerWhen = re.sub('"', '', cellLeakagePowerWhen)
            cellLeakagePowerRelatedPgPin = cellLeakagePowerDic.get('related_pg_pin', 'N/A')
            cellLeakagePowerRelatedPgPin = re.sub('"', '', cellLeakagePowerRelatedPgPin)
            tmpLeakagePowerDic = {
                                  'value' : cellLeakagePowerValue,
                                  'when' : cellLeakagePowerWhen,
                                  'related_pg_pin' : cellLeakagePowerRelatedPgPin,
                                 }
            self.specifiedLibDic[libraryFileName][cellName]['leakage_power'].append(tmpLeakagePowerDic)

            if self.specifiedCellCount >= 2:
                self.leakagePowerTabDic[libraryFileName][cellName]['leakage_power'].setdefault('when', collections.OrderedDict())
                self.leakagePowerTabDic[libraryFileName][cellName]['leakage_power']['when'].setdefault(cellLeakagePowerWhen, collections.OrderedDict())
                self.leakagePowerTabDic[libraryFileName][cellName]['leakage_power']['when'][cellLeakagePowerWhen].setdefault('related_pg_pin', [])
                self.leakagePowerTabDic[libraryFileName][cellName]['leakage_power']['when'][cellLeakagePowerWhen]['related_pg_pin'].append(cellLeakagePowerRelatedPgPin)

    def getPinTimingInfo(self, pinTimingDicList):
        tmpTimingDicList = []
        tmpPinTimingDic = collections.OrderedDict()

        for pinTimingDic in pinTimingDicList:
            pinTimingRelatedPin = pinTimingDic.get('related_pin', 'N/A')
            pinTimingRelatedPin = re.sub('"', '', pinTimingRelatedPin)
            pinTimingRelatedPgPin = pinTimingDic.get('related_pg_pin', 'N/A')
            pinTimingRelatedPgPin = re.sub('"', '', pinTimingRelatedPgPin)
            pinTimingTimingSense = pinTimingDic.get('timing_sense', 'N/A')
            pinTimingTimingSense = re.sub('"', '', pinTimingTimingSense)
            pinTimingTimingType = pinTimingDic.get('timing_type', 'N/A')
            pinTimingTimingType = re.sub('"', '', pinTimingTimingType)
            pinTimingWhen = pinTimingDic.get('when', 'N/A')
            pinTimingWhen = re.sub('"', '', pinTimingWhen)

            tmpTimingDic = collections.OrderedDict()
            tmpTimingDic = {
                            'related_pin' : pinTimingRelatedPin,
                            'related_pg_pin' : pinTimingRelatedPgPin,
                            'timing_sense' : pinTimingTimingSense,
                            'timing_type' : pinTimingTimingType,
                            'when' : pinTimingWhen,
                           }
            tmpTimingDic['table_type'] = collections.OrderedDict()

            tmpPinTimingDic.setdefault('related_pin', collections.OrderedDict())
            tmpPinTimingDic['related_pin'].setdefault(pinTimingRelatedPin, collections.OrderedDict())
            tmpPinTimingDic['related_pin'][pinTimingRelatedPin].setdefault('related_pg_pin', collections.OrderedDict())
            tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'].setdefault(pinTimingRelatedPgPin, collections.OrderedDict())
            tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin].setdefault('timing_sense', collections.OrderedDict())
            tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'].setdefault(pinTimingTimingSense, collections.OrderedDict())
            tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense].setdefault('timing_type', collections.OrderedDict())
            tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'].setdefault(pinTimingTimingType, collections.OrderedDict())
            tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType].setdefault('when', collections.OrderedDict())
            tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'].setdefault(pinTimingWhen, collections.OrderedDict())
            tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen].setdefault('table_type', collections.OrderedDict())

            for tableType in pinTimingDic['table_type'].keys():
                if (tableType == 'cell_rise') or (tableType == 'rise_transition') or (tableType == 'cell_fall') or (tableType == 'fall_transition') or (tableType == 'rise_constraint') or (tableType == 'fall_constraint') or (tableType == 'ocv_sigma_rise_contraint') or (tableType == 'ocv_sigma_fall_contraint') or (tableType == 'ocv_sigma_rise_transition') or (tableType == 'ocv_sigma_fall_transition') or (tableType == 'ocv_sigma_cell_rise') or (tableType == 'ocv_sigma_cell_fall'):
                    pinTimingTableTypeDic = pinTimingDic['table_type'][tableType]
                    if 'index_1' in pinTimingTableTypeDic:
                        pinTimingGroupIndex1 = pinTimingTableTypeDic['index_1']
                        pinTimingGroupIndex1 = re.sub('\(', '', pinTimingGroupIndex1)
                        pinTimingGroupIndex1 = re.sub('\)', '', pinTimingGroupIndex1)
                        pinTimingGroupIndex1 = re.sub('"', '', pinTimingGroupIndex1)
                        pinTimingGroupIndex1 = re.sub(',', '', pinTimingGroupIndex1)
                        pinTimingGroupIndex1 = pinTimingGroupIndex1.split()
                    else:
                        pinTimingGroupIndex1 = []

                    if 'index_2' in pinTimingTableTypeDic:
                        pinTimingGroupIndex2 = pinTimingTableTypeDic['index_2']
                        pinTimingGroupIndex2 = re.sub('\(', '', pinTimingGroupIndex2)
                        pinTimingGroupIndex2 = re.sub('\)', '', pinTimingGroupIndex2)
                        pinTimingGroupIndex2 = re.sub('"', '', pinTimingGroupIndex2)
                        pinTimingGroupIndex2 = re.sub(',', '', pinTimingGroupIndex2)
                        pinTimingGroupIndex2 = pinTimingGroupIndex2.split()
                    else:
                        pinTimingGroupIndex2 = []

                    if 'values' in pinTimingTableTypeDic:
                        pinTimingGroupValues = []
                        tmpCellPinTimingGroupValues = pinTimingTableTypeDic['values']
                        tmpCellPinTimingGroupValues = re.sub('\(', '', tmpCellPinTimingGroupValues)
                        tmpCellPinTimingGroupValues = re.sub('\)', '', tmpCellPinTimingGroupValues)
                        tmpCellPinTimingGroupValues = re.split('"\s*,', tmpCellPinTimingGroupValues)
                        for pinTimingGroupValue in tmpCellPinTimingGroupValues:
                            pinTimingGroupValue = re.sub('"', '', pinTimingGroupValue)
                            pinTimingGroupValue = re.sub(',', '', pinTimingGroupValue)
                            pinTimingGroupValue = pinTimingGroupValue.split()
                            pinTimingGroupValues.append(pinTimingGroupValue)
                    else:
                        pinTimingGroupValues = []

                    tmpTimingDic['table_type'][tableType] = {
                                                             'index_1' : pinTimingGroupIndex1,
                                                             'index_2' : pinTimingGroupIndex2,
                                                             'values' : pinTimingGroupValues,
                                                            }

                    tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'].setdefault(tableType, collections.OrderedDict())
                    tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'][tableType].setdefault('index_1', range(len(pinTimingGroupIndex1)))
                    tmpPinTimingDic['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'][tableType].setdefault('index_2', range(len(pinTimingGroupIndex2)))

            tmpTimingDicList.append(tmpTimingDic)

        return(tmpTimingDicList, tmpPinTimingDic)

    def getTimingInfo(self, libraryFileName, cellName, libPinDic):
        if libPinDic['cell'][cellName]:
            for key in libPinDic['cell'][cellName]:
                if key == 'bundle':
                    for bundleName in libPinDic['cell'][cellName]['bundle']:
                        bundleTimingDicList = []
                        if 'timing' in libPinDic['cell'][cellName]['bundle'][bundleName]:
                            bundleTimingDicList = libPinDic['cell'][cellName]['bundle'][bundleName]['timing']
                        if 'pin' in libPinDic['cell'][cellName]['bundle'][bundleName]:
                            for pinName in libPinDic['cell'][cellName]['bundle'][bundleName]['pin']:
                                if ('timing' in libPinDic['cell'][cellName]['bundle'][bundleName]['pin'][pinName]) or (len(bundleTimingDicList) > 0):
                                    libPinTimingDicList = []
                                    if 'timing' in libPinDic['cell'][cellName]['bundle'][bundleName]['pin'][pinName]:
                                        libPinTimingDicList = libPinDic['cell'][cellName]['bundle'][bundleName]['pin'][pinName]['timing']
                                    if len(bundleTimingDicList) > 0:
                                        libPinTimingDicList.extend(bundleTimingDicList)
                                    (tmpTimingDicList, tmpPinTimingDic) = self.getPinTimingInfo(libPinTimingDicList)
                                    self.specifiedLibDic[libraryFileName][cellName].setdefault('bundle', collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bundle'].setdefault(bundleName, collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bundle'][bundleName].setdefault('pin', collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bundle'][bundleName]['pin'].setdefault(pinName, collections.OrderedDict())
                                    if tmpTimingDicList:
                                        self.specifiedLibDic[libraryFileName][cellName]['bundle'][bundleName]['pin'][pinName].setdefault('timing', tmpTimingDicList)
                                    self.timingTabDic[libraryFileName][cellName].setdefault('bundle', collections.OrderedDict())
                                    self.timingTabDic[libraryFileName][cellName]['bundle'].setdefault(bundleName, collections.OrderedDict())
                                    self.timingTabDic[libraryFileName][cellName]['bundle'][bundleName].setdefault('pin', collections.OrderedDict())
                                    self.timingTabDic[libraryFileName][cellName]['bundle'][bundleName]['pin'].setdefault(pinName, collections.OrderedDict())
                                    if tmpPinTimingDic:
                                        self.timingTabDic[libraryFileName][cellName]['bundle'][bundleName]['pin'][pinName].setdefault('timing', tmpPinTimingDic)
                elif key == 'bus':
                    for busName in libPinDic['cell'][cellName]['bus']:
                        busTimingDicList = []
                        if 'timing' in libPinDic['cell'][cellName]['bus'][busName]:
                            busTimingDicList = libPinDic['cell'][cellName]['bus'][busName]['timing']
                        if 'pin' in libPinDic['cell'][cellName]['bus'][busName]:
                            for pinName in libPinDic['cell'][cellName]['bus'][busName]['pin']:
                                if ('timing' in libPinDic['cell'][cellName]['bus'][busName]['pin'][pinName]) or (len(busTimingDicList) > 0):
                                    libPinTimingDicList = []
                                    if 'timing' in libPinDic['cell'][cellName]['bus'][busName]['pin'][pinName]:
                                        libPinTimingDicList = libPinDic['cell'][cellName]['bus'][busName]['pin'][pinName]['timing']
                                    if len(busTimingDicList) > 0:
                                        libPinTimingDicList.extend(busTimingDicList)
                                    (tmpTimingDicList, tmpPinTimingDic) = self.getPinTimingInfo(libPinTimingDicList)
                                    self.specifiedLibDic[libraryFileName][cellName].setdefault('bus', collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bus'].setdefault(busName, collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bus'][busName].setdefault('pin', collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bus'][busName]['pin'].setdefault(pinName, collections.OrderedDict())
                                    if tmpTimingDicList:
                                        self.specifiedLibDic[libraryFileName][cellName]['bus'][busName]['pin'][pinName].setdefault('timing', tmpTimingDicList)
                                    self.timingTabDic[libraryFileName][cellName].setdefault('bus', collections.OrderedDict())
                                    self.timingTabDic[libraryFileName][cellName]['bus'].setdefault(busName, collections.OrderedDict())
                                    self.timingTabDic[libraryFileName][cellName]['bus'][busName].setdefault('pin', collections.OrderedDict())
                                    self.timingTabDic[libraryFileName][cellName]['bus'][busName]['pin'].setdefault(pinName, collections.OrderedDict())
                                    if tmpPinTimingDic:
                                        self.timingTabDic[libraryFileName][cellName]['bus'][busName]['pin'][pinName].setdefault('timing', tmpPinTimingDic)
                elif key == 'pin':
                    for pinName in libPinDic['cell'][cellName]['pin']:
                        if 'timing' in libPinDic['cell'][cellName]['pin'][pinName]:
                            (tmpTimingDicList, tmpPinTimingDic) = self.getPinTimingInfo(libPinDic['cell'][cellName]['pin'][pinName]['timing'])
                            self.specifiedLibDic[libraryFileName][cellName].setdefault('pin', collections.OrderedDict())
                            self.specifiedLibDic[libraryFileName][cellName]['pin'].setdefault(pinName, collections.OrderedDict())
                            if tmpTimingDicList:
                                self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName].setdefault('timing', tmpTimingDicList)
                            self.timingTabDic[libraryFileName][cellName].setdefault('pin', collections.OrderedDict())
                            self.timingTabDic[libraryFileName][cellName]['pin'].setdefault(pinName, collections.OrderedDict())
                            if tmpPinTimingDic:
                                self.timingTabDic[libraryFileName][cellName]['pin'][pinName].setdefault('timing', tmpPinTimingDic)

    def getPinInternalPowerInfo(self, pinInternalPowerDicList):
        tmpInternalPowerDicList = []
        tmpPinInternalPowerDic = collections.OrderedDict()

        for pinInternalPowerDic in pinInternalPowerDicList:
            pinInternalPowerRelatedPin = pinInternalPowerDic.get('related_pin', 'N/A')
            pinInternalPowerRelatedPin = re.sub('"', '', pinInternalPowerRelatedPin)
            pinInternalPowerRelatedPgPin = pinInternalPowerDic.get('related_pg_pin', 'N/A')
            pinInternalPowerRelatedPgPin = re.sub('"', '', pinInternalPowerRelatedPgPin)
            pinInternalPowerWhen = pinInternalPowerDic.get('when', 'N/A')
            pinInternalPowerWhen = re.sub('"', '', pinInternalPowerWhen)

            tmpInternalPowerDic = collections.OrderedDict()
            tmpInternalPowerDic = {
                            'related_pin' : pinInternalPowerRelatedPin,
                            'related_pg_pin' : pinInternalPowerRelatedPgPin,
                            'when' : pinInternalPowerWhen,
                           }
            tmpInternalPowerDic['table_type'] = collections.OrderedDict()

            tmpPinInternalPowerDic.setdefault('related_pin', collections.OrderedDict())
            tmpPinInternalPowerDic['related_pin'].setdefault(pinInternalPowerRelatedPin, collections.OrderedDict())
            tmpPinInternalPowerDic['related_pin'][pinInternalPowerRelatedPin].setdefault('related_pg_pin', collections.OrderedDict())
            tmpPinInternalPowerDic['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'].setdefault(pinInternalPowerRelatedPgPin, collections.OrderedDict())
            tmpPinInternalPowerDic['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin].setdefault('when', collections.OrderedDict())
            tmpPinInternalPowerDic['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'].setdefault(pinInternalPowerWhen, collections.OrderedDict())
            tmpPinInternalPowerDic['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen].setdefault('table_type', collections.OrderedDict())

            for tableType in pinInternalPowerDic['table_type'].keys():
                if (tableType == 'fall_power') or (tableType == 'rise_power'):
                    pinInternalPowerTableTypeDic = pinInternalPowerDic['table_type'][tableType]
                    if 'index_1' in pinInternalPowerTableTypeDic:
                        pinInternalPowerGroupIndex1 = pinInternalPowerTableTypeDic['index_1']
                        pinInternalPowerGroupIndex1 = re.sub('\(', '', pinInternalPowerGroupIndex1)
                        pinInternalPowerGroupIndex1 = re.sub('\)', '', pinInternalPowerGroupIndex1)
                        pinInternalPowerGroupIndex1 = re.sub('"', '', pinInternalPowerGroupIndex1)
                        pinInternalPowerGroupIndex1 = re.sub(',', '', pinInternalPowerGroupIndex1)
                        pinInternalPowerGroupIndex1 = pinInternalPowerGroupIndex1.split()
                    else:
                        pinInternalPowerGroupIndex1 = []

                    if 'index_2' in pinInternalPowerTableTypeDic:
                        pinInternalPowerGroupIndex2 = pinInternalPowerTableTypeDic['index_2']
                        pinInternalPowerGroupIndex2 = re.sub('\(', '', pinInternalPowerGroupIndex2)
                        pinInternalPowerGroupIndex2 = re.sub('\)', '', pinInternalPowerGroupIndex2)
                        pinInternalPowerGroupIndex2 = re.sub('"', '', pinInternalPowerGroupIndex2)
                        pinInternalPowerGroupIndex2 = re.sub(',', '', pinInternalPowerGroupIndex2)
                        pinInternalPowerGroupIndex2 = pinInternalPowerGroupIndex2.split()
                    else:
                        pinInternalPowerGroupIndex2 = []

                    if 'values' in pinInternalPowerTableTypeDic:
                        pinInternalPowerGroupValues = []
                        tmpCellPinInternalPowerGroupValues = pinInternalPowerTableTypeDic['values']
                        tmpCellPinInternalPowerGroupValues = re.sub('\(', '', tmpCellPinInternalPowerGroupValues)
                        tmpCellPinInternalPowerGroupValues = re.sub('\)', '', tmpCellPinInternalPowerGroupValues)
                        tmpCellPinInternalPowerGroupValues = re.split('"\s*,', tmpCellPinInternalPowerGroupValues)
                        for pinInternalPowerGroupValue in tmpCellPinInternalPowerGroupValues:
                            pinInternalPowerGroupValue = re.sub('"', '', pinInternalPowerGroupValue)
                            pinInternalPowerGroupValue = re.sub(',', '', pinInternalPowerGroupValue)
                            pinInternalPowerGroupValue = pinInternalPowerGroupValue.split()
                            pinInternalPowerGroupValues.append(pinInternalPowerGroupValue)
                    else:
                        pinInternalPowerGroupValues = []

                    tmpInternalPowerDic['table_type'][tableType] = {
                                                             'index_1' : pinInternalPowerGroupIndex1,
                                                             'index_2' : pinInternalPowerGroupIndex2,
                                                             'values' : pinInternalPowerGroupValues,
                                                            }

                    tmpPinInternalPowerDic['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'].setdefault(tableType, collections.OrderedDict())
                    tmpPinInternalPowerDic['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'][tableType].setdefault('index_1', range(len(pinInternalPowerGroupIndex1)))
                    tmpPinInternalPowerDic['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'][tableType].setdefault('index_2', range(len(pinInternalPowerGroupIndex2)))

            tmpInternalPowerDicList.append(tmpInternalPowerDic)

        return(tmpInternalPowerDicList, tmpPinInternalPowerDic)

    def getInternalPowerInfo(self, libraryFileName, cellName, libPinDic):
        if libPinDic['cell'][cellName]:
            for key in libPinDic['cell'][cellName]:
                if key == 'bundle':
                    for bundleName in libPinDic['cell'][cellName]['bundle']:
                        bundleInternalPowerDicList = []
                        if 'internal_power' in libPinDic['cell'][cellName]['bundle'][bundleName]:
                            bundleInternalPowerDicList = libPinDic['cell'][cellName]['bundle'][bundleName]['internal_power']
                        if 'pin' in libPinDic['cell'][cellName]['bundle'][bundleName]:
                            for pinName in libPinDic['cell'][cellName]['bundle'][bundleName]['pin']:
                                if ('internal_power' in libPinDic['cell'][cellName]['bundle'][bundleName]['pin'][pinName]) or (len(bundleInternalPowerDicList) > 0):
                                    libPinInternalPowerDicList = []
                                    if 'internal_power' in libPinDic['cell'][cellName]['bundle'][bundleName]['pin'][pinName]:
                                        libPinInternalPowerDicList = libPinDic['cell'][cellName]['bundle'][bundleName]['pin'][pinName]['internal_power']
                                    if len(bundleInternalPowerDicList) > 0:
                                        libPinInternalPowerDicList.extend(bundleInternalPowerDicList)
                                    (tmpInternalPowerDicList, tmpPinInternalPowerDic) = self.getPinInternalPowerInfo(libPinInternalPowerDicList)
                                    self.specifiedLibDic[libraryFileName][cellName].setdefault('bundle', collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bundle'].setdefault(bundleName, collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bundle'][bundleName].setdefault('pin', collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bundle'][bundleName]['pin'].setdefault(pinName, collections.OrderedDict())
                                    if tmpInternalPowerDicList:
                                        self.specifiedLibDic[libraryFileName][cellName]['bundle'][bundleName]['pin'][pinName].setdefault('internal_power', tmpInternalPowerDicList)
                                    self.internalPowerTabDic[libraryFileName][cellName].setdefault('bundle', collections.OrderedDict())
                                    self.internalPowerTabDic[libraryFileName][cellName]['bundle'].setdefault(bundleName, collections.OrderedDict())
                                    self.internalPowerTabDic[libraryFileName][cellName]['bundle'][bundleName].setdefault('pin', collections.OrderedDict())
                                    self.internalPowerTabDic[libraryFileName][cellName]['bundle'][bundleName]['pin'].setdefault(pinName, collections.OrderedDict())
                                    if tmpPinInternalPowerDic:
                                        self.internalPowerTabDic[libraryFileName][cellName]['bundle'][bundleName]['pin'][pinName].setdefault('internal_power', tmpPinInternalPowerDic)
                elif key == 'bus':
                    for busName in libPinDic['cell'][cellName]['bus']:
                        busInternalPowerDicList = []
                        if 'internal_power' in libPinDic['cell'][cellName]['bus'][busName]:
                            busInternalPowerDicList = libPinDic['cell'][cellName]['bus'][busName]['internal_power']
                        if 'pin' in libPinDic['cell'][cellName]['bus'][busName]:
                            for pinName in libPinDic['cell'][cellName]['bus'][busName]['pin']:
                                if ('internal_power' in libPinDic['cell'][cellName]['bus'][busName]['pin'][pinName]) or (len(busInternalPowerDicList) > 0):
                                    libPinInternalPowerDicList = []
                                    if 'internal_power' in libPinDic['cell'][cellName]['bus'][busName]['pin'][pinName]:
                                        libPinInternalPowerDicList = libPinDic['cell'][cellName]['bus'][busName]['pin'][pinName]['internal_power']
                                    if len(busInternalPowerDicList) > 0:
                                        libPinInternalPowerDicList.extend(busInternalPowerDicList)
                                    (tmpInternalPowerDicList, tmpPinInternalPowerDic) = self.getPinInternalPowerInfo(libPinInternalPowerDicList)
                                    self.specifiedLibDic[libraryFileName][cellName].setdefault('bus', collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bus'].setdefault(busName, collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bus'][busName].setdefault('pin', collections.OrderedDict())
                                    self.specifiedLibDic[libraryFileName][cellName]['bus'][busName]['pin'].setdefault(pinName, collections.OrderedDict())
                                    if tmpInternalPowerDicList:
                                        self.specifiedLibDic[libraryFileName][cellName]['bus'][busName]['pin'][pinName].setdefault('internal_power', tmpInternalPowerDicList)
                                    self.internalPowerTabDic[libraryFileName][cellName].setdefault('bus', collections.OrderedDict())
                                    self.internalPowerTabDic[libraryFileName][cellName]['bus'].setdefault(busName, collections.OrderedDict())
                                    self.internalPowerTabDic[libraryFileName][cellName]['bus'][busName].setdefault('pin', collections.OrderedDict())
                                    self.internalPowerTabDic[libraryFileName][cellName]['bus'][busName]['pin'].setdefault(pinName, collections.OrderedDict())
                                    if tmpPinInternalPowerDic:
                                        self.internalPowerTabDic[libraryFileName][cellName]['bus'][busName]['pin'][pinName].setdefault('internal_power', tmpPinInternalPowerDic)
                elif key == 'pin':
                    for pinName in libPinDic['cell'][cellName]['pin']:
                        if 'internal_power' in libPinDic['cell'][cellName]['pin'][pinName]:
                            (tmpInternalPowerDicList, tmpPinInternalPowerDic) = self.getPinInternalPowerInfo(libPinDic['cell'][cellName]['pin'][pinName]['internal_power'])
                            self.specifiedLibDic[libraryFileName][cellName].setdefault('pin', collections.OrderedDict())
                            self.specifiedLibDic[libraryFileName][cellName]['pin'].setdefault(pinName, collections.OrderedDict())
                            if tmpInternalPowerDicList:
                                self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName].setdefault('internal_power', tmpInternalPowerDicList)
                            self.internalPowerTabDic[libraryFileName][cellName].setdefault('pin', collections.OrderedDict())
                            self.internalPowerTabDic[libraryFileName][cellName]['pin'].setdefault(pinName, collections.OrderedDict())
                            if tmpPinInternalPowerDic:
                                self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName].setdefault('internal_power', tmpPinInternalPowerDic)

    def selectCell(self):
        """
        Select specified cells.
        """
        cellSelectString = self.cellSelectLine.text().strip()
        selectedCellList = cellSelectString.split()

        for i in range(len(selectedCellList)):
            if re.search('\*', selectedCellList[i]):
                selectedCellList[i] = re.sub('\*', '.*', selectedCellList[i])

        item = QTreeWidgetItemIterator(self.cellListTree)

        while item.value():
            if item.value().parent():
                if item.value().checkState(0) == Qt.Checked:
                    item.value().setCheckState(0, Qt.Unchecked)
                cellName = item.value().text(0)
                for selectedCell in selectedCellList:
                    if re.match('^' + str(selectedCell) + '$', cellName):
                        item.value().setCheckState(0, Qt.Checked)
                        break

            item += 1

        self.cellListBeClicked()

    def cellListBeClicked(self):
        """
        Update clicked lib/cell information.
        """
        self.specifiedLibDic = collections.OrderedDict()
        self.specifiedCellCount = 0

        # Save clicked lib-cells into self.specifiedLibDic.
        item = QTreeWidgetItemIterator(self.cellListTree)

        while item.value():
            if item.value().parent():
                libraryFileName = item.value().parent().text(0)
                cellName = item.value().text(0)

                if item.value().checkState(0) == Qt.Checked:
                    if libraryFileName not in self.specifiedLibDic:
                        self.specifiedLibDic[libraryFileName] = collections.OrderedDict()
                    if cellName not in self.specifiedLibDic[libraryFileName]:
                        self.specifiedLibDic[libraryFileName][cellName] = collections.OrderedDict()
                        self.specifiedCellCount += 1
                elif item.value().checkState(0) == Qt.Unchecked:
                    if (libraryFileName in self.specifiedLibDic) and (cellName in self.specifiedLibDic[libraryFileName]):
                        del self.specifiedLibDic[libraryFileName][cellName]
                        self.specifiedCellCount -= 1
                        if len(self.specifiedLibDic[libraryFileName]) == 0:
                            del self.specifiedLibDic[libraryFileName]

            item += 1

        # Get lib-cell area/leakge_power/timing/internal_power infos.
        self.leakagePowerTabDic = collections.OrderedDict()
        self.timingTabDic = collections.OrderedDict()
        self.internalPowerTabDic = collections.OrderedDict()

        for libraryFileName in self.specifiedLibDic:
            self.leakagePowerTabDic[libraryFileName] = collections.OrderedDict()
            self.timingTabDic[libraryFileName] = collections.OrderedDict()
            self.internalPowerTabDic[libraryFileName] = collections.OrderedDict()

            libCellAreaDic = self.libDic[libraryFileName]['parser'].getCellArea()
            libCellLeakagePowerDic = self.libDic[libraryFileName]['parser'].getCellLeakagePower()
            libPinDic = self.libDic[libraryFileName]['parser'].getLibPinInfo()

            for cellName in self.specifiedLibDic[libraryFileName]:
                self.leakagePowerTabDic[libraryFileName][cellName] = collections.OrderedDict()
                self.timingTabDic[libraryFileName][cellName] = collections.OrderedDict()
                self.internalPowerTabDic[libraryFileName][cellName] = collections.OrderedDict()

                # area
                self.getCellAreaInfo(libraryFileName, cellName, libCellAreaDic)

                # leakge power
                self.getCellLeakagePowerInfo(libraryFileName, cellName, libCellLeakagePowerDic)

                # timing
                self.getTimingInfo(libraryFileName, cellName, libPinDic)

                # internal power    
                self.getInternalPowerInfo(libraryFileName, cellName, libPinDic)

        # Check tab multi-enable.
        if self.specifiedCellCount >= 2:
            self.leakagePowerTabMultiEnable = self.checkTabMultiEnable(self.leakagePowerTabDic)
            self.timingTabMultiEnable = self.checkTabMultiEnable(self.timingTabDic)
            self.internalPowerTabMultiEnable = self.checkTabMultiEnable(self.internalPowerTabDic)
        else:
            self.leakagePowerTabMultiEnable = False
            self.timingTabMultiEnable = False
            self.internalPowerTabMultiEnable = False

        # Cell list item click behavior - self.updateMainFrame() (Update the GUI)
        self.updateMainFrame()

    def checkTabMultiEnable(self, tabDic):
        tabMultiEnable = True

        if self.specifiedCellCount < 2:
            tabMultiEnable = False
        else:
            lastTabCellDic = collections.OrderedDict()

            for libraryFileName in tabDic.keys():
                for cellName in tabDic[libraryFileName]:
                    tabCellDic = tabDic[libraryFileName][cellName]
                    if not lastTabCellDic:
                        lastTabCellDic = copy.deepcopy(tabCellDic)
                    else:
                        if lastTabCellDic != tabCellDic:
                            tabMultiEnable = False
                            print('*Warning*: specified cells have different structure!')
                            break

                if not tabMultiEnable:
                    break

        return(tabMultiEnable)
#### Update Cell List Tree (end) ####


#### Update Main Frame (begin) ####
    def updateMainFrame(self):
        """
        Update self.mainFrame.
        """
        self.updateMainFrameLibCell()
        self.updateMainFrameTabs()

    def updateMainFrameLibCell(self):
        """
        Update self.mainFrame lib/cell part.
        """
        self.libLine.setText('')
        self.cellLine.setText('')

        # Get specified lib/cell.
        specifiedLibList = []
        specifiedCellList = []

        for libraryFileName in self.specifiedLibDic.keys():
            for cellName in self.specifiedLibDic[libraryFileName].keys():
                if libraryFileName not in specifiedLibList:
                    specifiedLibList.append(libraryFileName)
                if cellName not in specifiedCellList:
                    specifiedCellList.append(cellName)

        self.libLine.setText(' '.join(specifiedLibList))
        self.cellLine.setText(' '.join(specifiedCellList))

    def updateMainFrameTabs(self):
        """
        Update area/leakage_power/timing/inter_power tables.
        """
        self.updateAreaTab()
        self.updateLeakagePowerTab()
        self.updateTimingTab()
        self.updateInternalPowerTab()
#### Update Main Frame (end) ####


#### Update Area Tab (begin) ####
    def updateAreaTab(self):
        """
        Update area tab.
        """
        self.updateAreaTabTable()

    def updateAreaTabTable(self):
        """
        Update area tab table.
        """
        self.areaTabTable.setRowCount(self.specifiedCellCount)

        self.areaTabFigureXList = []
        self.areaTabFigureYList = []
        row = 0

        # Update self.areaTabTable.
        for libraryFileName in self.specifiedLibDic.keys():
            for cellName in self.specifiedLibDic[libraryFileName].keys():
                self.areaTabTable.setItem(row, 0, QTableWidgetItem(libraryFileName))
                self.areaTabTable.setItem(row, 1, QTableWidgetItem(cellName))
                cellArea = self.specifiedLibDic[libraryFileName][cellName]['area']
                self.areaTabTable.setItem(row, 2, QTableWidgetItem(cellArea))
                self.areaTabFigureXList.append('cell_' + str(row+1))
                self.areaTabFigureYList.append(float(cellArea))
                row += 1

        self.areaTabTable.resizeColumnsToContents()
        self.updateAreaTabFigure()

    def updateAreaTabFigure(self):
        """
        Update area tab figure.
        """
        self.areaTabFigure.drawEmptyPlot('Cell Area Curve')

        if self.specifiedCellCount > 1:
            if len(self.areaTabFigureXList) > 0:
                self.areaTabFigure.drawPlot(self.areaTabFigureXList, self.areaTabFigureYList, xLabel='Cell-Num', yLabel='Area', yUnit='', title='Cell Area Curve')
#### Update Area Tab (end) ####


#### Update Leakage Power Tab (begin) ####
    def updateLeakagePowerTab(self):
        """
        Update leakagePower tab.
        """
        self.updateLeakagePowerTabFrame()

    def updateLeakagePowerTabFrame(self):
        """
        Update leakagePower tab frame.
        """
        self.updateLeakagePowerTabWhenCombo()

    def updateLeakagePowerTabWhenCombo(self):
        """
        Update leakagePower tab frame 'when' QComboBox.
        """
        self.leakagePowerTabWhenCombo.clear()
        finish = False

        if self.leakagePowerTabMultiEnable:
            for libraryFileName in self.leakagePowerTabDic.keys():
                for cellName in self.leakagePowerTabDic[libraryFileName]:
                    cellWhenList = list(set(list(self.leakagePowerTabDic[libraryFileName][cellName]['leakage_power']['when'].keys())))
                    self.leakagePowerTabWhenCombo.addItems(cellWhenList)
                    finish = True
                    break
                if finish:
                    break

        self.updateLeakagePowerTabRelatedPgPinCombo()

    def updateLeakagePowerTabRelatedPgPinCombo(self):
        """
        Update leakagePower tab frame 'related_pg_pin' QComboBox.
        """
        self.leakagePowerTabRelatedPgPinCombo.clear()
        finish = False

        if self.leakagePowerTabMultiEnable:
            for libraryFileName in self.leakagePowerTabDic.keys():
                for cellName in self.leakagePowerTabDic[libraryFileName]:
                    cellLeakagePowerWhen = self.leakagePowerTabWhenCombo.currentText().strip()
                    cellRelatedPgPinList = list(set(self.leakagePowerTabDic[libraryFileName][cellName]['leakage_power']['when'][cellLeakagePowerWhen]['related_pg_pin']))
                    self.leakagePowerTabRelatedPgPinCombo.addItems(cellRelatedPgPinList)
                    finish = True
                    break
                if finish:
                    break

        self.updateLeakagePowerTabTable()

    def updateLeakagePowerTabTable(self):
        """
        Update leakagePower tab table.
        """
        self.leakagePowerTabFigureXList = []
        self.leakagePowerTabFigureYList = []

        # Update self.leakagePowerTabTable.
        if self.leakagePowerTabMultiEnable:
            self.leakagePowerTabTable.setRowCount(self.specifiedCellCount)
            specifiedWhen = self.leakagePowerTabWhenCombo.currentText().strip()
            specifiedRelatedPgPin = self.leakagePowerTabRelatedPgPinCombo.currentText().strip()
            row = 0
            for libraryFileName in self.specifiedLibDic.keys():
                for cellName in self.specifiedLibDic[libraryFileName]:
                    self.leakagePowerTabTable.setItem(row, 0, QTableWidgetItem(libraryFileName))
                    self.leakagePowerTabTable.setItem(row, 1, QTableWidgetItem(cellName))
                    self.leakagePowerTabTable.setItem(row, 2, QTableWidgetItem(specifiedWhen))
                    self.leakagePowerTabTable.setItem(row, 3, QTableWidgetItem(specifiedRelatedPgPin))
                    specifiedValue = 0
                    for tmpDic in self.specifiedLibDic[libraryFileName][cellName]['leakage_power']:
                        if (tmpDic['when'] == specifiedWhen) and (tmpDic['related_pg_pin'] == specifiedRelatedPgPin):
                            specifiedValue = tmpDic['value']
                            break
                    self.leakagePowerTabTable.setItem(row, 4, QTableWidgetItem(specifiedValue))
                    self.leakagePowerTabFigureXList.append('cell_' + str(row+1))
                    self.leakagePowerTabFigureYList.append(float(specifiedValue))
                    row += 1
        else:
            leakagePowerTabTableRowCount = 0
            for libraryFileName in self.specifiedLibDic.keys():
                for cellName in self.specifiedLibDic[libraryFileName]:
                    leakagePowerTabTableRowCount += len(self.specifiedLibDic[libraryFileName][cellName]['leakage_power'])
            self.leakagePowerTabTable.setRowCount(leakagePowerTabTableRowCount)
            row = 0
            for libraryFileName in self.specifiedLibDic.keys():
                for cellName in self.specifiedLibDic[libraryFileName]:
                    for cellLeakagePowerDic in self.specifiedLibDic[libraryFileName][cellName]['leakage_power']:
                        self.leakagePowerTabTable.setItem(row, 0, QTableWidgetItem(libraryFileName))
                        self.leakagePowerTabTable.setItem(row, 1, QTableWidgetItem(cellName))
                        self.leakagePowerTabTable.setItem(row, 2, QTableWidgetItem(cellLeakagePowerDic['when']))
                        self.leakagePowerTabTable.setItem(row, 3, QTableWidgetItem(cellLeakagePowerDic['related_pg_pin']))
                        self.leakagePowerTabTable.setItem(row, 4, QTableWidgetItem(cellLeakagePowerDic['value']))
                        self.leakagePowerTabFigureXList.append('cell_' + str(row+1))
                        self.leakagePowerTabFigureYList.append(float(cellLeakagePowerDic['value']))
                        row += 1

        self.leakagePowerTabTable.resizeColumnsToContents()
        self.updateLeakagePowerTabFigure()

    def updateLeakagePowerTabFigure(self):
        """
        Update leakagePower tab figure.
        """
        self.leakagePowerTabFigure.drawEmptyPlot('Cell Leakage Power Curve')

        if self.leakagePowerTabMultiEnable:
            if len(self.leakagePowerTabFigureXList) > 0:
                self.leakagePowerTabFigure.drawPlot(self.leakagePowerTabFigureXList, self.leakagePowerTabFigureYList, xLabel='Cell-Num', yLabel='Leakge-Power (' + str(self.leakagePowerUnit) + ')', yUnit=self.leakagePowerUnit, title='Cell Leakage Power Curve')
#### Update Leakage Power Tab (end) ####


#### Update Timing Tab (begin) ####
    def updateTimingTab(self):
        """
        Update timing tab.
        """
        self.updateTimingTabBundleBusFrame()
        self.updateTimingTabPinFrame()

    def updateTimingTabBundleBusFrame(self):
        """
        Update timing tab bundle/bus frame.
        """
        self.updateTimingTabBundleCombo()
        self.updateTimingTabBusCombo()

    def updateTimingTabBundleCombo(self):
        """
        Update timing tab frame 'bundle' QComboBox.
        """
        self.timingTabBundleCombo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    if 'bundle' in self.timingTabDic[libraryFileName][cellName]:
                        cellBundleList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'].keys())))
                        cellBundleList.insert(0, '')
                        self.timingTabBundleCombo.addItems(cellBundleList)
                        finish = True
                        break
                if finish:
                    break

    def updateTimingTabBusCombo(self):
        """
        Update timing tab frame 'bus' QComboBox.
        """
        self.timingTabBusCombo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    if 'bus' in self.timingTabDic[libraryFileName][cellName]:
                        cellBusList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'].keys())))
                        cellBusList.insert(0, '')
                        self.timingTabBusCombo.addItems(cellBusList)
                        finish = True
                        break
                if finish:
                    break

    def updateTimingTabPinFrame(self):
        """
        Update timing tab pin frame.
        """
        self.updateTimingTabPinCombo()

    def updateTimingTabPinCombo(self):
        """
        Update timing tab frame 'pin' QComboBox.
        """
        self.timingTabPinCombo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    specifiedBundle = self.timingTabBundleCombo.currentText().strip()
                    specifiedBus = self.timingTabBusCombo.currentText().strip()
                    if specifiedBundle != '':
                        pinList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'].keys())))
                    elif specifiedBus != '':
                        pinList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'].keys())))
                    else:
                        if 'pin' in self.timingTabDic[libraryFileName][cellName]:
                            pinList = list(set(list(self.timingTabDic[libraryFileName][cellName]['pin'].keys())))
                        else:
                            pinList = []
                    self.timingTabPinCombo.addItems(pinList)
                    finish = True
                    break
                if finish:
                    break

        self.updateTimingTabRelatedPinCombo()

    def updateTimingTabRelatedPinCombo(self):
        """
        Update timing tab frame 'related_pin' QComboBox.
        """
        self.timingTabRelatedPinCombo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    pinName = self.timingTabPinCombo.currentText().strip()
                    specifiedBundle = self.timingTabBundleCombo.currentText().strip()
                    specifiedBus = self.timingTabBusCombo.currentText().strip()
                    pinTimingRelatedPinList = []
                    if specifiedBundle != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinTimingRelatedPinList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']['related_pin'].keys())))
                    elif specifiedBus != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinTimingRelatedPinList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']['related_pin'].keys())))
                    else:
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinTimingRelatedPinList = list(set(list(self.timingTabDic[libraryFileName][cellName]['pin'][pinName]['timing']['related_pin'].keys())))
                    self.timingTabRelatedPinCombo.addItems(pinTimingRelatedPinList)
                    finish = True
                    break
                if finish:
                    break

        self.updateTimingTabRelatedPgPinCombo()

    def updateTimingTabRelatedPgPinCombo(self):
        """
        Update timing tab frame 'related_pg_pin' QComboBox.
        """
        self.timingTabRelatedPgPinCombo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    pinName = self.timingTabPinCombo.currentText().strip()
                    pinTimingRelatedPin = self.timingTabRelatedPinCombo.currentText().strip()
                    specifiedBundle = self.timingTabBundleCombo.currentText().strip()
                    specifiedBus = self.timingTabBusCombo.currentText().strip()
                    pinTimingRelatedPgPinList = []
                    if specifiedBundle != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinTimingRelatedPgPinList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'].keys())))
                    elif specifiedBus != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinTimingRelatedPgPinList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'].keys())))
                    else:
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinTimingRelatedPgPinList = list(set(list(self.timingTabDic[libraryFileName][cellName]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'].keys())))
                    self.timingTabRelatedPgPinCombo.addItems(pinTimingRelatedPgPinList)
                    finish = True
                    break
                if finish:
                    break

        self.updateTimingTabTimingSenseCombo()

    def updateTimingTabTimingSenseCombo(self):
        """
        Update timing tab frame 'timing_sense' QComboBox.
        """
        self.timingTabTimingSenseCombo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    pinName = self.timingTabPinCombo.currentText().strip()
                    pinTimingRelatedPin = self.timingTabRelatedPinCombo.currentText().strip()
                    pinTimingRelatedPgPin = self.timingTabRelatedPgPinCombo.currentText().strip()
                    specifiedBundle = self.timingTabBundleCombo.currentText().strip()
                    specifiedBus = self.timingTabBusCombo.currentText().strip()
                    pinTimingTimingSenseList = []
                    if specifiedBundle != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinTimingTimingSenseList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'].keys())))
                    elif specifiedBus != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinTimingTimingSenseList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'].keys())))
                    else:
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinTimingTimingSenseList = list(set(list(self.timingTabDic[libraryFileName][cellName]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'].keys())))
                    self.timingTabTimingSenseCombo.addItems(pinTimingTimingSenseList)
                    finish = True
                    break
                if finish:
                    break

        self.updateTimingTabTimingTypeCombo()

    def updateTimingTabTimingTypeCombo(self):
        """
        Update timing tab frame 'timing_type' QComboBox.
        """
        self.timingTabTimingTypeCombo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    pinName = self.timingTabPinCombo.currentText().strip()
                    pinTimingRelatedPin = self.timingTabRelatedPinCombo.currentText().strip()
                    pinTimingRelatedPgPin = self.timingTabRelatedPgPinCombo.currentText().strip()
                    pinTimingTimingSense = self.timingTabTimingSenseCombo.currentText().strip()
                    specifiedBundle = self.timingTabBundleCombo.currentText().strip()
                    specifiedBus = self.timingTabBusCombo.currentText().strip()
                    pinTimingTimingTypeList = []
                    if specifiedBundle != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinTimingTimingTypeList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'].keys())))
                    elif specifiedBus != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinTimingTimingTypeList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'].keys())))
                    else:
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinTimingTimingTypeList = list(set(list(self.timingTabDic[libraryFileName][cellName]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'].keys())))
                    self.timingTabTimingTypeCombo.addItems(pinTimingTimingTypeList)
                    finish = True
                    break
                if finish:
                    break

        self.updateTimingTabWhenCombo()

    def updateTimingTabWhenCombo(self):
        """
        Update timing tab frame 'when' QComboBox.
        """
        self.timingTabWhenCombo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    pinName = self.timingTabPinCombo.currentText().strip()
                    pinTimingRelatedPin = self.timingTabRelatedPinCombo.currentText().strip()
                    pinTimingRelatedPgPin = self.timingTabRelatedPgPinCombo.currentText().strip()
                    pinTimingTimingSense = self.timingTabTimingSenseCombo.currentText().strip()
                    pinTimingTimingType = self.timingTabTimingTypeCombo.currentText().strip()
                    specifiedBundle = self.timingTabBundleCombo.currentText().strip()
                    specifiedBus = self.timingTabBusCombo.currentText().strip()
                    pinTimingWhenList = []
                    if specifiedBundle != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinTimingWhenList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'].keys())))
                    elif specifiedBus != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinTimingWhenList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'].keys())))
                    else:
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinTimingWhenList = list(set(list(self.timingTabDic[libraryFileName][cellName]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'].keys())))
                    self.timingTabWhenCombo.addItems(pinTimingWhenList)
                    finish = True
                    break
                if finish:
                    break

        self.updateTimingTabTableTypeCombo()

    def updateTimingTabTableTypeCombo(self):
        """
        Update timing tab frame 'Table Type' QComboBox.
        """
        self.timingTabTableTypeCombo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            pinName = self.timingTabPinCombo.currentText().strip()
            pinTimingRelatedPin = self.timingTabRelatedPinCombo.currentText().strip()
            pinTimingRelatedPgPin = self.timingTabRelatedPgPinCombo.currentText().strip()
            pinTimingTimingSense = self.timingTabTimingSenseCombo.currentText().strip()
            pinTimingTimingType = self.timingTabTimingTypeCombo.currentText().strip()
            pinTimingWhen = self.timingTabWhenCombo.currentText().strip()
            specifiedBundle = self.timingTabBundleCombo.currentText().strip()
            specifiedBus = self.timingTabBusCombo.currentText().strip()

            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    pinTimingTableTypeList = []
                    if specifiedBundle != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinTimingTableTypeList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'].keys())))
                    elif specifiedBus != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinTimingTableTypeList = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'].keys())))
                    else:
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinTimingTableTypeList = list(set(list(self.timingTabDic[libraryFileName][cellName]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'].keys())))
                    self.timingTabTableTypeCombo.addItems(pinTimingTableTypeList)
                    finish = True
                    break
                if finish:
                    break

        self.updateTimingTabIndexCombo()

    def updateTimingTabIndexCombo(self):
        """
        Update timing tab frame 'index_1/index_2' QComboBox.
        """
        self.timingTabIndex1Combo.clear()
        self.timingTabIndex2Combo.clear()
        finish = False

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            pinName = self.timingTabPinCombo.currentText().strip()
            pinTimingRelatedPin = self.timingTabRelatedPinCombo.currentText().strip()
            pinTimingRelatedPgPin = self.timingTabRelatedPgPinCombo.currentText().strip()
            pinTimingTimingSense = self.timingTabTimingSenseCombo.currentText().strip()
            pinTimingTimingType = self.timingTabTimingTypeCombo.currentText().strip()
            pinTimingWhen = self.timingTabWhenCombo.currentText().strip()
            pinTimingTableType = self.timingTabTableTypeCombo.currentText().strip()
            specifiedBundle = self.timingTabBundleCombo.currentText().strip()
            specifiedBus = self.timingTabBusCombo.currentText().strip()

            for libraryFileName in self.timingTabDic.keys():
                for cellName in self.timingTabDic[libraryFileName]:
                    pinTimingIndex1List = []
                    pinTimingIndex2List = []
                    if specifiedBundle != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinTimingIndex1List = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'][pinTimingTableType]['index_1'])))
                            pinTimingIndex2List = list(set(list(self.timingTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'][pinTimingTableType]['index_2'])))
                    elif specifiedBus != '':
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinTimingIndex1List = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'][pinTimingTableType]['index_1'])))
                            pinTimingIndex2List = list(set(list(self.timingTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'][pinTimingTableType]['index_2'])))
                    else:
                        if 'timing' in self.timingTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinTimingIndex1List = list(set(list(self.timingTabDic[libraryFileName][cellName]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'][pinTimingTableType]['index_1'])))
                            pinTimingIndex2List = list(set(list(self.timingTabDic[libraryFileName][cellName]['pin'][pinName]['timing']['related_pin'][pinTimingRelatedPin]['related_pg_pin'][pinTimingRelatedPgPin]['timing_sense'][pinTimingTimingSense]['timing_type'][pinTimingTimingType]['when'][pinTimingWhen]['table_type'][pinTimingTableType]['index_2'])))

                    self.timingTabIndex1Combo.addItem('')
                    for index1 in pinTimingIndex1List:
                        self.timingTabIndex1Combo.addItem(str(index1))

                    self.timingTabIndex2Combo.addItem('')
                    for index2 in pinTimingIndex2List:
                        self.timingTabIndex2Combo.addItem(str(index2))

                    finish = True
                    break
                if finish:
                    break

        self.updateTimingTabTable()

    def updateTimingTabTable(self):
        """
        Update timing tab table self.timingTabTable.
        """
        self.timingTabTable.setRowCount(0)
        self.timingTabTable.setColumnCount(0)

        if self.timingTabMultiEnable or self.specifiedCellCount == 1:
            self.timingTabFigureXList = []
            self.timingTabFigureYList = []
            self.timingTabFigureXArray = numpy.array([])
            self.timingTabFigureYArray = numpy.array([])
            self.timingTabFigureZArray = numpy.array([])

            pinName = self.timingTabPinCombo.currentText().strip()
            pinTimingRelatedPin = self.timingTabRelatedPinCombo.currentText().strip()
            pinTimingRelatedPgPin = self.timingTabRelatedPgPinCombo.currentText().strip()
            pinTimingTimingSense = self.timingTabTimingSenseCombo.currentText().strip()
            pinTimingTimingType = self.timingTabTimingTypeCombo.currentText().strip()
            pinTimingWhen = self.timingTabWhenCombo.currentText().strip()
            pinTimingTableType = self.timingTabTableTypeCombo.currentText().strip()
            pinTimingIndex1 = self.timingTabIndex1Combo.currentText().strip()
            pinTimingIndex2 = self.timingTabIndex2Combo.currentText().strip()
            specifiedBundle = self.timingTabBundleCombo.currentText().strip()
            specifiedBus = self.timingTabBusCombo.currentText().strip()

            if self.specifiedCellCount == 1:
                libraryFileName = sorted(self.specifiedLibDic.keys())[0]
                cellName = sorted(self.specifiedLibDic[libraryFileName].keys())[0]
                index1List = []
                index2List = []
                valuesList = []
                pinTimingDicList = []

                if specifiedBundle != '':
                    if 'timing' in self.specifiedLibDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                        pinTimingDicList = self.specifiedLibDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']
                elif specifiedBus != '':
                    if 'timing' in self.specifiedLibDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                        pinTimingDicList = self.specifiedLibDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']
                else:
                    if 'timing' in self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName]:
                        pinTimingDicList = self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName]['timing']

                for pinTimingDic in pinTimingDicList:
                    if (pinTimingRelatedPin == pinTimingDic['related_pin']) and (pinTimingRelatedPgPin == pinTimingDic['related_pg_pin']) and (pinTimingTimingSense == pinTimingDic['timing_sense']) and (pinTimingTimingType == pinTimingDic['timing_type']) and (pinTimingWhen == pinTimingDic['when']):
                        index1List = pinTimingDic['table_type'][pinTimingTableType]['index_1']
                        index2List = pinTimingDic['table_type'][pinTimingTableType]['index_2']
                        valuesList = pinTimingDic['table_type'][pinTimingTableType]['values']

                        if (pinTimingIndex1 != '') and (pinTimingIndex2 == ''):
                            self.timingTabFigureXList = [float(i) for i in index2List]
                            self.timingTabFigureYList = [float(i) for i in valuesList[int(pinTimingIndex1)]]
                        elif (pinTimingIndex1 == '') and (pinTimingIndex2 != ''):
                            self.timingTabFigureXList = [float(i) for i in index1List]
                            for valueList in valuesList:
                                self.timingTabFigureYList.append(float(valueList[int(pinTimingIndex2)]))
                        elif (pinTimingIndex1 == '') and (pinTimingIndex2 == ''):
                            xList = []
                            for i in range(len(index1List)):
                                tmpList = []
                                for j in range(len(index2List)):
                                    tmpList.append(index1List[i])
                                xList.append(tmpList)
                            yList = []
                            for i in range(len(index2List)):
                                yList.append(index2List)
                            self.timingTabFigureXArray = numpy.array(xList, dtype='float64')
                            self.timingTabFigureYArray = numpy.array(yList, dtype='float64')
                            self.timingTabFigureZArray = numpy.array(valuesList, dtype='float64')

                if len(index1List) > 0:
                    if len(index2List) > 0:
                        self.timingTabTable.setRowCount(len(index1List))
                        self.timingTabTable.setVerticalHeaderLabels(index1List)
                        self.timingTabTable.setColumnCount(len(index2List))
                        self.timingTabTable.setHorizontalHeaderLabels(index2List)
                    else:
                        self.timingTabTable.setRowCount(1)
                        self.timingTabTable.setColumnCount(len(index1List))
                        self.timingTabTable.setHorizontalHeaderLabels(index1List)
  
                    for i in range(len(valuesList)):
                        for j in range(len(valuesList[i])):
                            self.timingTabTable.setItem(i, j, QTableWidgetItem(valuesList[i][j]))
            elif self.timingTabMultiEnable:
                self.timingTabTable.setColumnCount(5)
                self.timingTabTable.setHorizontalHeaderLabels(['LIB', 'CELL', 'index_1', 'index_2', 'value'])
                self.timingTabTable.setRowCount(self.specifiedCellCount)
                row = 0

                for libraryFileName in self.timingTabDic.keys():
                    for cellName in self.timingTabDic[libraryFileName]:
                        pinTimingDicList = []
                        if specifiedBundle != '':
                            if 'timing' in self.specifiedLibDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                                pinTimingDicList = self.specifiedLibDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['timing']
                        elif specifiedBus != '':
                            if 'timing' in self.specifiedLibDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                                pinTimingDicList = self.specifiedLibDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['timing']
                        else:
                            if 'timing' in self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName]:
                                pinTimingDicList = self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName]['timing']

                        for pinTimingDic in pinTimingDicList:
                            if (pinTimingRelatedPin == pinTimingDic['related_pin']) and (pinTimingRelatedPgPin == pinTimingDic['related_pg_pin']) and (pinTimingTimingSense == pinTimingDic['timing_sense']) and (pinTimingTimingType == pinTimingDic['timing_type']) and (pinTimingWhen == pinTimingDic['when']):
                                if pinTimingIndex1 == '':
                                    self.timingTabIndex1Combo.setCurrentText('0')
                                    pinTimingIndex1 = 0
                                if pinTimingIndex2 == '':
                                    self.timingTabIndex2Combo.setCurrentText('0')
                                    pinTimingIndex2 = 0

                                if pinTimingIndex1 != '':
                                    if pinTimingIndex2 != '':
                                        timingIndex1 = pinTimingDic['table_type'][pinTimingTableType]['index_1'][int(pinTimingIndex1)]
                                        if len(pinTimingDic['table_type'][pinTimingTableType]['index_2']) > 0:
                                            timingIndex2 = pinTimingDic['table_type'][pinTimingTableType]['index_2'][int(pinTimingIndex2)]
                                        else:
                                            timingIndex2 = ''
                                        timingValue = pinTimingDic['table_type'][pinTimingTableType]['values'][int(pinTimingIndex1)][int(pinTimingIndex2)]
                                    else:
                                        timingIndex1 = pinTimingDic['table_type'][pinTimingTableType]['index_1'][int(pinTimingIndex1)]
                                        timingIndex2 = ''
                                        timingValue = pinTimingDic['table_type'][pinTimingTableType]['values'][0][int(pinTimingIndex1)]

                                    self.timingTabTable.setItem(row, 0, QTableWidgetItem(libraryFileName))
                                    self.timingTabTable.setItem(row, 1, QTableWidgetItem(cellName))
                                    self.timingTabTable.setItem(row, 2, QTableWidgetItem(timingIndex1))
                                    self.timingTabTable.setItem(row, 3, QTableWidgetItem(timingIndex2))
                                    self.timingTabTable.setItem(row, 4, QTableWidgetItem(timingValue))
                                    self.timingTabFigureXList.append('cell_' + str(row+1))
                                    self.timingTabFigureYList.append(float(timingValue))
                                    row += 1

            self.timingTabTable.resizeColumnsToContents()

        self.updateTimingTabFigure()

    def updateTimingTabFigure(self):
        """
        Update timing tab figure.
        """
        self.timingTabFigure.drawEmptyPlot('Cell Timing Curve')

        if self.specifiedCellCount == 1:
            pinTimingIndex1 = self.timingTabIndex1Combo.currentText().strip()
            pinTimingIndex2 = self.timingTabIndex2Combo.currentText().strip()
            if (pinTimingIndex1 == '') and (pinTimingIndex2 == ''):
                if (len(self.timingTabFigureXArray) > 0) and (len(self.timingTabFigureYArray) > 0) and (len(self.timingTabFigureZArray) > 0):
                    self.timingTabFigure.draw3DPlot(self.timingTabFigureXArray, self.timingTabFigureYArray, self.timingTabFigureZArray, xLabel='index_1', yLabel='index_2', zLabel='values', title='Cell Timing Curve')
            elif (pinTimingIndex1 != '') and (pinTimingIndex2 == ''):
                if (len(self.timingTabFigureXList) > 0) and (len(self.timingTabFigureYList) > 0):
                    self.timingTabFigure.drawPlot(self.timingTabFigureXList, self.timingTabFigureYList, xLabel='index_2', yLabel='Timing (' + str(self.timingUnit) + ')', yUnit=self.timingUnit, title='Cell Timing Curve')
            elif (pinTimingIndex1 == '') and (pinTimingIndex2 != ''):
                if (len(self.timingTabFigureXList) > 0) and (len(self.timingTabFigureYList) > 0):
                    self.timingTabFigure.drawPlot(self.timingTabFigureXList, self.timingTabFigureYList, xLabel='index_1', yLabel='Timing (' + str(self.timingUnit) + ')', yUnit=self.timingUnit, title='Cell Timing Curve')
        elif self.timingTabMultiEnable:
            if (len(self.timingTabFigureXList) > 0) and (len(self.timingTabFigureYList) > 0):
                self.timingTabFigure.drawPlot(self.timingTabFigureXList, self.timingTabFigureYList, xLabel='Cell-Num', yLabel='Timing (' + str(self.timingUnit) + ')', yUnit=self.timingUnit, title='Cell Timing Curve')
#### Update Timing Tab (end) ####


#### Update Internal Power Tab (begin) ####
    def updateInternalPowerTab(self):
        """
        Update internalPower tab.
        """
        self.updateInternalPowerTabBundleBusFrame()
        self.updateInternalPowerTabPinFrame()

    def updateInternalPowerTabBundleBusFrame(self):
        """
        Update internalPower tab bundle/bus frame.
        """
        self.updateInternalPowerTabBundleCombo()
        self.updateInternalPowerTabBusCombo()

    def updateInternalPowerTabBundleCombo(self):
        """
        Update internalPower tab frame 'bundle' QComboBox.
        """
        self.internalPowerTabBundleCombo.clear()
        finish = False

        if self.internalPowerTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.internalPowerTabDic.keys():
                for cellName in self.internalPowerTabDic[libraryFileName]:
                    if 'bundle' in self.internalPowerTabDic[libraryFileName][cellName]:
                        cellBundleList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bundle'].keys())))
                        self.internalPowerTabBundleCombo.addItems(cellBundleList)
                        finish = True
                        break
                if finish:
                    break

    def updateInternalPowerTabBusCombo(self):
        """
        Update internalPower tab frame 'bus' QComboBox.
        """
        self.internalPowerTabBusCombo.clear()
        finish = False

        if self.internalPowerTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.internalPowerTabDic.keys():
                for cellName in self.internalPowerTabDic[libraryFileName]:
                    if 'bus' in self.internalPowerTabDic[libraryFileName][cellName]:
                        cellBusList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bus'].keys())))
                        self.internalPowerTabBusCombo.addItems(cellBusList)
                        finish = True
                        break
                if finish:
                    break

    def updateInternalPowerTabPinFrame(self):
        """
        Update internalPower tab pin frame.
        """
        self.updateInternalPowerTabPinCombo()

    def updateInternalPowerTabPinCombo(self):
        """
        Update internalPower tab frame 'pin' QComboBox.
        """
        self.internalPowerTabPinCombo.clear()
        finish = False

        if self.internalPowerTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.internalPowerTabDic.keys():
                for cellName in self.internalPowerTabDic[libraryFileName]:
                    specifiedBundle = self.internalPowerTabBundleCombo.currentText().strip()
                    specifiedBus = self.internalPowerTabBusCombo.currentText().strip()
                    if specifiedBundle != '':
                        pinList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'].keys())))
                    elif specifiedBus != '':
                        pinList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'].keys())))
                    else:
                        if 'pin' in self.internalPowerTabDic[libraryFileName][cellName]:
                            pinList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['pin'].keys())))
                        else:
                            pinList = []
                    self.internalPowerTabPinCombo.addItems(pinList)
                    finish = True
                    break
                if finish:
                    break

        self.updateInternalPowerTabRelatedPinCombo()

    def updateInternalPowerTabRelatedPinCombo(self):
        """
        Update internalPower tab frame 'related_pin' QComboBox.
        """
        self.internalPowerTabRelatedPinCombo.clear()
        finish = False

        if self.internalPowerTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.internalPowerTabDic.keys():
                for cellName in self.internalPowerTabDic[libraryFileName]:
                    pinName = self.internalPowerTabPinCombo.currentText().strip()
                    specifiedBundle = self.internalPowerTabBundleCombo.currentText().strip()
                    specifiedBus = self.internalPowerTabBusCombo.currentText().strip()
                    pinInternalPowerRelatedPinList = []
                    if specifiedBundle != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinInternalPowerRelatedPinList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['internal_power']['related_pin'].keys())))
                    elif specifiedBus != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinInternalPowerRelatedPinList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['internal_power']['related_pin'].keys())))
                    else:
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinInternalPowerRelatedPinList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]['internal_power']['related_pin'].keys())))
                    self.internalPowerTabRelatedPinCombo.addItems(pinInternalPowerRelatedPinList)
                    finish = True
                    break
                if finish:
                    break

        self.updateInternalPowerTabRelatedPgPinCombo()

    def updateInternalPowerTabRelatedPgPinCombo(self):
        """
        Update internalPower tab frame 'related_pg_pin' QComboBox.
        """
        self.internalPowerTabRelatedPgPinCombo.clear()
        finish = False

        if self.internalPowerTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.internalPowerTabDic.keys():
                for cellName in self.internalPowerTabDic[libraryFileName]:
                    pinName = self.internalPowerTabPinCombo.currentText().strip()
                    pinInternalPowerRelatedPin = self.internalPowerTabRelatedPinCombo.currentText().strip()
                    specifiedBundle = self.internalPowerTabBundleCombo.currentText().strip()
                    specifiedBus = self.internalPowerTabBusCombo.currentText().strip()
                    pinInternalPowerRelatedPgPinList = []
                    if specifiedBundle != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinInternalPowerRelatedPgPinList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'].keys())))
                    elif specifiedBus != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinInternalPowerRelatedPgPinList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'].keys())))
                    else:
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinInternalPowerRelatedPgPinList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'].keys())))
                    self.internalPowerTabRelatedPgPinCombo.addItems(pinInternalPowerRelatedPgPinList)
                    finish = True
                    break
                if finish:
                    break

        self.updateInternalPowerTabWhenCombo()

    def updateInternalPowerTabWhenCombo(self):
        """
        Update internalPower tab frame 'when' QComboBox.
        """
        self.internalPowerTabWhenCombo.clear()
        finish = False

        if self.internalPowerTabMultiEnable or self.specifiedCellCount == 1:
            for libraryFileName in self.internalPowerTabDic.keys():
                for cellName in self.internalPowerTabDic[libraryFileName]:
                    pinName = self.internalPowerTabPinCombo.currentText().strip()
                    pinInternalPowerRelatedPin = self.internalPowerTabRelatedPinCombo.currentText().strip()
                    pinInternalPowerRelatedPgPin = self.internalPowerTabRelatedPgPinCombo.currentText().strip()
                    specifiedBundle = self.internalPowerTabBundleCombo.currentText().strip()
                    specifiedBus = self.internalPowerTabBusCombo.currentText().strip()
                    pinInternalPowerWhenList = []
                    if specifiedBundle != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinInternalPowerWhenList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'].keys())))
                    elif specifiedBus != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinInternalPowerWhenList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'].keys())))
                    else:
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinInternalPowerWhenList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'].keys())))
                    self.internalPowerTabWhenCombo.addItems(pinInternalPowerWhenList)
                    finish = True
                    break
                if finish:
                    break

        self.updateInternalPowerTabTableTypeCombo()

    def updateInternalPowerTabTableTypeCombo(self):
        """
        Update internalPower tab frame 'Table Type' QComboBox.
        """
        self.internalPowerTabTableTypeCombo.clear()
        finish = False

        if self.internalPowerTabMultiEnable or self.specifiedCellCount == 1:
            pinName = self.internalPowerTabPinCombo.currentText().strip()
            pinInternalPowerRelatedPin = self.internalPowerTabRelatedPinCombo.currentText().strip()
            pinInternalPowerRelatedPgPin = self.internalPowerTabRelatedPgPinCombo.currentText().strip()
            pinInternalPowerWhen = self.internalPowerTabWhenCombo.currentText().strip()
            specifiedBundle = self.internalPowerTabBundleCombo.currentText().strip()
            specifiedBus = self.internalPowerTabBusCombo.currentText().strip()

            for libraryFileName in self.internalPowerTabDic.keys():
                for cellName in self.internalPowerTabDic[libraryFileName]:
                    pinInternalPowerTableTypeList = []
                    if specifiedBundle != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinInternalPowerTableTypeList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'].keys())))
                    elif specifiedBus != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinInternalPowerTableTypeList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'].keys())))
                    else:
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinInternalPowerTableTypeList = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'].keys())))
                    self.internalPowerTabTableTypeCombo.addItems(pinInternalPowerTableTypeList)
                    finish = True
                    break
                if finish:
                    break

        self.updateInternalPowerTabIndexCombo()

    def updateInternalPowerTabIndexCombo(self):
        """
        Update internalPower tab frame 'index_1/index_2' QComboBox.
        """
        self.internalPowerTabIndex1Combo.clear()
        self.internalPowerTabIndex2Combo.clear()
        finish = False

        if self.internalPowerTabMultiEnable or self.specifiedCellCount == 1:
            pinName = self.internalPowerTabPinCombo.currentText().strip()
            pinInternalPowerRelatedPin = self.internalPowerTabRelatedPinCombo.currentText().strip()
            pinInternalPowerRelatedPgPin = self.internalPowerTabRelatedPgPinCombo.currentText().strip()
            pinInternalPowerWhen = self.internalPowerTabWhenCombo.currentText().strip()
            pinInternalPowerTableType = self.internalPowerTabTableTypeCombo.currentText().strip()
            specifiedBundle = self.internalPowerTabBundleCombo.currentText().strip()
            specifiedBus = self.internalPowerTabBusCombo.currentText().strip()

            for libraryFileName in self.internalPowerTabDic.keys():
                for cellName in self.internalPowerTabDic[libraryFileName]:
                    pinInternalPowerIndex1List = []
                    pinInternalPowerIndex2List = []
                    if specifiedBundle != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                            pinInternalPowerIndex1List = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'][pinInternalPowerTableType]['index_1'])))
                            pinInternalPowerIndex2List = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'][pinInternalPowerTableType]['index_2'])))
                    elif specifiedBus != '':
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                            pinInternalPowerIndex1List = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'][pinInternalPowerTableType]['index_1'])))
                            pinInternalPowerIndex2List = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'][pinInternalPowerTableType]['index_2'])))
                    else:
                        if 'internal_power' in self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]:
                            pinInternalPowerIndex1List = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'][pinInternalPowerTableType]['index_1'])))
                            pinInternalPowerIndex2List = list(set(list(self.internalPowerTabDic[libraryFileName][cellName]['pin'][pinName]['internal_power']['related_pin'][pinInternalPowerRelatedPin]['related_pg_pin'][pinInternalPowerRelatedPgPin]['when'][pinInternalPowerWhen]['table_type'][pinInternalPowerTableType]['index_2'])))

                    self.internalPowerTabIndex1Combo.addItem('')
                    for index1 in pinInternalPowerIndex1List:
                        self.internalPowerTabIndex1Combo.addItem(str(index1))

                    self.internalPowerTabIndex2Combo.addItem('')
                    for index2 in pinInternalPowerIndex2List:
                        self.internalPowerTabIndex2Combo.addItem(str(index2))

                    finish = True
                    break
                if finish:
                    break

        self.updateInternalPowerTabTable()

    def updateInternalPowerTabTable(self):
        """
        Update internalPower tab table self.internalPowerTabTable.
        """
        self.internalPowerTabTable.setRowCount(0)
        self.internalPowerTabTable.setColumnCount(0)

        if self.internalPowerTabMultiEnable or self.specifiedCellCount == 1:
            self.internalPowerTabFigureXList = []
            self.internalPowerTabFigureYList = []
            self.internalPowerTabFigureXArray = numpy.array([])
            self.internalPowerTabFigureYArray = numpy.array([])
            self.internalPowerTabFigureZArray = numpy.array([])

            pinName = self.internalPowerTabPinCombo.currentText().strip()
            pinInternalPowerRelatedPin = self.internalPowerTabRelatedPinCombo.currentText().strip()
            pinInternalPowerRelatedPgPin = self.internalPowerTabRelatedPgPinCombo.currentText().strip()
            pinInternalPowerWhen = self.internalPowerTabWhenCombo.currentText().strip()
            pinInternalPowerTableType = self.internalPowerTabTableTypeCombo.currentText().strip()
            pinInternalPowerIndex1 = self.internalPowerTabIndex1Combo.currentText().strip()
            pinInternalPowerIndex2 = self.internalPowerTabIndex2Combo.currentText().strip()
            specifiedBundle = self.internalPowerTabBundleCombo.currentText().strip()
            specifiedBus = self.internalPowerTabBusCombo.currentText().strip()

            if self.specifiedCellCount == 1:
                libraryFileName = sorted(self.specifiedLibDic.keys())[0]
                cellName = sorted(self.specifiedLibDic[libraryFileName].keys())[0]
                index1List = []
                index2List = []
                valuesList = []
                pinInternalPowerDicList = []

                if specifiedBundle != '':
                    if 'internal_power' in self.specifiedLibDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                        pinInternalPowerDicList = self.specifiedLibDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['internal_power']
                elif specifiedBus != '':
                    if 'internal_power' in self.specifiedLibDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                        pinInternalPowerDicList = self.specifiedLibDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['internal_power']
                else:
                    if 'internal_power' in self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName]:
                        pinInternalPowerDicList = self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName]['internal_power']

                for pinInternalPowerDic in pinInternalPowerDicList:
                    if (pinInternalPowerRelatedPin == pinInternalPowerDic['related_pin']) and (pinInternalPowerRelatedPgPin == pinInternalPowerDic['related_pg_pin']) and (pinInternalPowerWhen == pinInternalPowerDic['when']):
                        index1List = pinInternalPowerDic['table_type'][pinInternalPowerTableType]['index_1']
                        index2List = pinInternalPowerDic['table_type'][pinInternalPowerTableType]['index_2']
                        valuesList = pinInternalPowerDic['table_type'][pinInternalPowerTableType]['values']

                        if (pinInternalPowerIndex1 != '') and (pinInternalPowerIndex2 == ''):
                            self.internalPowerTabFigureXList = [float(i) for i in index2List]
                            self.internalPowerTabFigureYList = [float(i) for i in valuesList[int(pinInternalPowerIndex1)]]
                        elif (pinInternalPowerIndex1 == '') and (pinInternalPowerIndex2 != ''):
                            self.internalPowerTabFigureXList = [float(i) for i in index1List]
                            for valueList in valuesList:
                                self.internalPowerTabFigureYList.append(float(valueList[int(pinInternalPowerIndex2)]))
                        elif (pinInternalPowerIndex1 == '') and (pinInternalPowerIndex2 == ''):
                            xList = []
                            for i in range(len(index1List)):
                                tmpList = []
                                for j in range(len(index2List)):
                                    tmpList.append(index1List[i])
                                xList.append(tmpList)
                            yList = []
                            for i in range(len(index2List)):
                                yList.append(index2List)
                            self.internalPowerTabFigureXArray = numpy.array(xList, dtype='float64')
                            self.internalPowerTabFigureYArray = numpy.array(yList, dtype='float64')
                            self.internalPowerTabFigureZArray = numpy.array(valuesList, dtype='float64')

                if len(index1List) > 0:
                    if len(index2List) > 0:
                        self.internalPowerTabTable.setRowCount(len(index1List))
                        self.internalPowerTabTable.setVerticalHeaderLabels(index1List)
                        self.internalPowerTabTable.setColumnCount(len(index2List))
                        self.internalPowerTabTable.setHorizontalHeaderLabels(index2List)
                    else:
                        self.internalPowerTabTable.setRowCount(1)
                        self.internalPowerTabTable.setColumnCount(len(index1List))
                        self.internalPowerTabTable.setHorizontalHeaderLabels(index1List)

                    for i in range(len(valuesList)):
                        for j in range(len(valuesList[i])):
                            self.internalPowerTabTable.setItem(i, j, QTableWidgetItem(valuesList[i][j]))
            elif self.internalPowerTabMultiEnable:
                self.internalPowerTabTable.setColumnCount(5)
                self.internalPowerTabTable.setHorizontalHeaderLabels(['LIB', 'CELL', 'index_1', 'index_2', 'value'])
                self.internalPowerTabTable.setRowCount(self.specifiedCellCount)
                row = 0

                for libraryFileName in self.internalPowerTabDic.keys():
                    for cellName in self.internalPowerTabDic[libraryFileName]:
                        pinInternalPowerDicList = []
                        if specifiedBundle != '':
                            if 'internal_power' in self.specifiedLibDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]:
                                pinInternalPowerDicList = self.specifiedLibDic[libraryFileName][cellName]['bundle'][specifiedBundle]['pin'][pinName]['internal_power']
                        elif specifiedBus != '':
                            if 'internal_power' in self.specifiedLibDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]:
                                pinInternalPowerDicList = self.specifiedLibDic[libraryFileName][cellName]['bus'][specifiedBus]['pin'][pinName]['internal_power']
                        else:
                            if 'internal_power' in self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName]:
                                pinInternalPowerDicList = self.specifiedLibDic[libraryFileName][cellName]['pin'][pinName]['internal_power']

                        for pinInternalPowerDic in pinInternalPowerDicList:
                            if (pinInternalPowerRelatedPin == pinInternalPowerDic['related_pin']) and (pinInternalPowerRelatedPgPin == pinInternalPowerDic['related_pg_pin']) and (pinInternalPowerWhen == pinInternalPowerDic['when']):
                                if pinInternalPowerIndex1 == '':
                                    self.internalPowerTabIndex1Combo.setCurrentText('0')
                                    pinInternalPowerIndex1 = 0
                                if pinInternalPowerIndex2 == '':
                                    self.internalPowerTabIndex2Combo.setCurrentText('0')
                                    pinInternalPowerIndex2 = 0

                                if pinInternalPowerIndex1 != '':
                                    if pinInternalPowerIndex2 != '':
                                        internalPowerIndex1 = pinInternalPowerDic['table_type'][pinInternalPowerTableType]['index_1'][int(pinInternalPowerIndex1)]
                                        if len(pinInternalPowerDic['table_type'][pinInternalPowerTableType]['index_2']) > 0:
                                            internalPowerIndex2 = pinInternalPowerDic['table_type'][pinInternalPowerTableType]['index_2'][int(pinInternalPowerIndex2)]
                                        else:
                                            internalPowerIndex2 = ''
                                        internalPowerValue = pinInternalPowerDic['table_type'][pinInternalPowerTableType]['values'][int(pinInternalPowerIndex1)][int(pinInternalPowerIndex2)]
                                    else:
                                        internalPowerIndex1 = pinInternalPowerDic['table_type'][pinInternalPowerTableType]['index_1'][int(pinInternalPowerIndex1)]
                                        internalPowerIndex2 = ''
                                        internalPowerValue = pinInternalPowerDic['table_type'][pinInternalPowerTableType]['values'][0][int(pinInternalPowerIndex1)]

                                    self.internalPowerTabTable.setItem(row, 0, QTableWidgetItem(libraryFileName))
                                    self.internalPowerTabTable.setItem(row, 1, QTableWidgetItem(cellName))
                                    self.internalPowerTabTable.setItem(row, 2, QTableWidgetItem(internalPowerIndex1))
                                    self.internalPowerTabTable.setItem(row, 3, QTableWidgetItem(internalPowerIndex2))
                                    self.internalPowerTabTable.setItem(row, 4, QTableWidgetItem(internalPowerValue))
                                    self.internalPowerTabFigureXList.append('cell_' + str(row+1))
                                    self.internalPowerTabFigureYList.append(float(internalPowerValue))
                                    row += 1

            self.internalPowerTabTable.resizeColumnsToContents()

        self.updateInternalPowerTabFigure()

    def updateInternalPowerTabFigure(self):
        """
        Update internalPower tab figure.
        """
        self.internalPowerTabFigure.drawEmptyPlot('Cell Internal Power Curve')

        if self.specifiedCellCount == 1:
            pinInternalPowerIndex1 = self.internalPowerTabIndex1Combo.currentText().strip()
            pinInternalPowerIndex2 = self.internalPowerTabIndex2Combo.currentText().strip()
            if (pinInternalPowerIndex1 == '') and (pinInternalPowerIndex2 == ''):
                if (len(self.internalPowerTabFigureXArray) > 0) and (len(self.internalPowerTabFigureYArray) > 0) and (len(self.internalPowerTabFigureZArray) > 0):
                    self.internalPowerTabFigure.draw3DPlot(self.internalPowerTabFigureXArray, self.internalPowerTabFigureYArray, self.internalPowerTabFigureZArray, xLabel='index_1', yLabel='index_2', zLabel='values', title='Cell Internal Power Curve')
            elif (pinInternalPowerIndex1 != '') and (pinInternalPowerIndex2 == ''):
                if (len(self.internalPowerTabFigureXList) > 0) and (len(self.internalPowerTabFigureYList) > 0):
                    self.internalPowerTabFigure.drawPlot(self.internalPowerTabFigureXList, self.internalPowerTabFigureYList, xLabel='index_2', yLabel='Internal-Power (' + str(self.internalPowerUnit) + ')', yUnit=self.internalPowerUnit, title='Cell Internal Power Curve')
            elif (pinInternalPowerIndex1 == '') and (pinInternalPowerIndex2 != ''):
                if (len(self.internalPowerTabFigureXList) > 0) and (len(self.internalPowerTabFigureYList) > 0):
                    self.internalPowerTabFigure.drawPlot(self.internalPowerTabFigureXList, self.internalPowerTabFigureYList, xLabel='index_1', yLabel='Internal-Power (' + str(self.internalPowerUnit) + ')', yUnit=self.internalPowerUnit, title='Cell Internal Power Curve')
        elif self.internalPowerTabMultiEnable:
            if (len(self.internalPowerTabFigureXList) > 0) and (len(self.internalPowerTabFigureYList) > 0):
                self.internalPowerTabFigure.drawPlot(self.internalPowerTabFigureXList, self.internalPowerTabFigureYList, xLabel='Cell-Num', yLabel='Internal-Power (' + str(self.internalPowerUnit) + ')', yUnit=self.internalPowerUnit, title='Cell Internal Power Curve')
#### Update Internal Power Tab (end) ####


################
# Main Process #
################
def main():
    inputFileList = readArgs()
    app = QApplication(sys.argv)
    mw = mainWindow(inputFileList)
    mw.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

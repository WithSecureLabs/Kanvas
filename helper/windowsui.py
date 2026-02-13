# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'windows_v2.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QMainWindow,
    QPushButton, QSizePolicy, QSpacerItem, QTreeView,
    QVBoxLayout, QWidget, QMenu)
from PySide6.QtGui import QAction

class Ui_KanvasMainWindow(object):
    def setupUi(self, KanvasMainWindow):
        if not KanvasMainWindow.objectName():
            KanvasMainWindow.setObjectName(u"KanvasMainWindow")
        KanvasMainWindow.resize(1000, 600)
        self.centralwidget = QWidget(KanvasMainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.sidePanel = QFrame(self.centralwidget)
        self.sidePanel.setObjectName(u"sidePanel")
        self.sidePanel.setFrameShape(QFrame.StyledPanel)
        self.verticalLayout = QVBoxLayout(self.sidePanel)
        self.verticalLayout.setSpacing(10)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(10, 10, 10, 10)
        self.verticalLayout.setAlignment(Qt.AlignTop)
        self.grpCase = QGroupBox(self.sidePanel)
        self.grpCase.setObjectName(u"grpCase")
        self.caseLayout = QVBoxLayout(self.grpCase)
        self.caseLayout.setSpacing(5)
        self.caseLayout.setContentsMargins(5, 5, 5, 5)
        self.caseLayout.setObjectName(u"caseLayout")
        self.left_button_7 = QPushButton(self.grpCase)
        self.left_button_7.setObjectName(u"left_button_7")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.left_button_7.sizePolicy().hasHeightForWidth())
        self.left_button_7.setSizePolicy(sizePolicy)
        self.caseLayout.addWidget(self.left_button_7)
        self.left_button_8 = QPushButton(self.grpCase)
        self.left_button_8.setObjectName(u"left_button_8")
        sizePolicy.setHeightForWidth(self.left_button_8.sizePolicy().hasHeightForWidth())
        self.left_button_8.setSizePolicy(sizePolicy)
        self.caseLayout.addWidget(self.left_button_8)
        self.left_button_6 = QPushButton(self.grpCase)
        self.left_button_6.setObjectName(u"left_button_6")
        sizePolicy.setHeightForWidth(self.left_button_6.sizePolicy().hasHeightForWidth())
        self.left_button_6.setSizePolicy(sizePolicy)
        self.caseLayout.addWidget(self.left_button_6)
        self.left_button_5 = QPushButton(self.grpCase)
        self.left_button_5.setObjectName(u"left_button_5")
        sizePolicy.setHeightForWidth(self.left_button_5.sizePolicy().hasHeightForWidth())
        self.left_button_5.setSizePolicy(sizePolicy)
        self.caseLayout.addWidget(self.left_button_5)
        self.left_button_4 = QPushButton(self.grpCase)
        self.left_button_4.setObjectName(u"left_button_4")
        sizePolicy.setHeightForWidth(self.left_button_4.sizePolicy().hasHeightForWidth())
        self.left_button_4.setSizePolicy(sizePolicy)
        self.caseLayout.addWidget(self.left_button_4)
        self.left_button_3 = QPushButton(self.grpCase)
        self.left_button_3.setObjectName(u"left_button_3")
        sizePolicy.setHeightForWidth(self.left_button_3.sizePolicy().hasHeightForWidth())
        self.left_button_3.setSizePolicy(sizePolicy)
        self.caseLayout.addWidget(self.left_button_3)
        self.left_button_2 = QPushButton(self.grpCase)
        self.left_button_2.setObjectName(u"left_button_2")
        sizePolicy.setHeightForWidth(self.left_button_2.sizePolicy().hasHeightForWidth())
        self.left_button_2.setSizePolicy(sizePolicy)
        self.caseLayout.addWidget(self.left_button_2)
        self.left_button_21 = QPushButton(self.grpCase)
        self.left_button_21.setObjectName(u"left_button_21")
        sizePolicy.setHeightForWidth(self.left_button_21.sizePolicy().hasHeightForWidth())
        self.left_button_21.setSizePolicy(sizePolicy)
        self.caseLayout.addWidget(self.left_button_21)
        self.left_button_23 = QPushButton(self.grpCase)
        self.left_button_23.setObjectName(u"left_button_23")
        sizePolicy.setHeightForWidth(self.left_button_23.sizePolicy().hasHeightForWidth())
        self.left_button_23.setSizePolicy(sizePolicy)
        self.caseLayout.addWidget(self.left_button_23)
        self.verticalLayout.addWidget(self.grpCase)
        self.labelSheet = QLabel(self.sidePanel)
        self.labelSheet.setObjectName(u"labelSheet")
        sizePolicy.setHeightForWidth(self.labelSheet.sizePolicy().hasHeightForWidth())
        self.labelSheet.setSizePolicy(sizePolicy)
        self.verticalLayout.addWidget(self.labelSheet)
        self.comboBoxSheet = QComboBox(self.sidePanel)
        self.comboBoxSheet.setObjectName(u"comboBoxSheet")
        sizePolicy.setHeightForWidth(self.comboBoxSheet.sizePolicy().hasHeightForWidth())
        self.comboBoxSheet.setSizePolicy(sizePolicy)
        self.verticalLayout.addWidget(self.comboBoxSheet)
        self.grpLookups = QGroupBox(self.sidePanel)
        self.grpLookups.setObjectName(u"grpLookups")
        self.lookupsLayout = QVBoxLayout(self.grpLookups)
        self.lookupsLayout.setSpacing(5)
        self.lookupsLayout.setContentsMargins(5, 5, 5, 5)
        self.lookupsLayout.setObjectName(u"lookupsLayout")
        self.left_button_9 = QPushButton(self.grpLookups)
        self.left_button_9.setObjectName(u"left_button_9")
        self.lookupsLayout.addWidget(self.left_button_9)
        self.left_button_11 = QPushButton(self.grpLookups)
        self.left_button_11.setObjectName(u"left_button_11")
        self.lookupsLayout.addWidget(self.left_button_11)
        self.left_button_22 = QPushButton(self.grpLookups)
        self.left_button_22.setObjectName(u"left_button_22")
        self.lookupsLayout.addWidget(self.left_button_22)
        self.left_button_12 = QPushButton(self.grpLookups)
        self.left_button_12.setObjectName(u"left_button_12")
        self.lookupsLayout.addWidget(self.left_button_12)
        self.left_button_13 = QPushButton(self.grpLookups)
        self.left_button_13.setObjectName(u"left_button_13")
        self.lookupsLayout.addWidget(self.left_button_13)
        self.left_button_14 = QPushButton(self.grpLookups)
        self.left_button_14.setObjectName(u"left_button_14")
        self.lookupsLayout.addWidget(self.left_button_14)
        self.left_button_10 = QPushButton(self.grpLookups)
        self.left_button_10.setObjectName(u"left_button_10")
        self.lookupsLayout.addWidget(self.left_button_10)
        self.verticalLayout.addWidget(self.grpLookups)
        self.grpKBase = QGroupBox(self.sidePanel)
        self.grpKBase.setObjectName(u"grpKBase")
        self.kbaseLayout = QVBoxLayout(self.grpKBase)
        self.kbaseLayout.setSpacing(5)
        self.kbaseLayout.setContentsMargins(5, 5, 5, 5)
        self.kbaseLayout.setObjectName(u"kbaseLayout")
        self.left_button_15 = QPushButton(self.grpKBase)
        self.left_button_15.setObjectName(u"left_button_15")
        self.kbaseLayout.addWidget(self.left_button_15)
        self.left_button_16 = QPushButton(self.grpKBase)
        self.left_button_16.setObjectName(u"left_button_16")
        self.kbaseLayout.addWidget(self.left_button_16)
        self.left_button_17 = QPushButton(self.grpKBase)
        self.left_button_17.setObjectName(u"left_button_17")
        self.left_button_17.setVisible(False)
        self.kbaseLayout.addWidget(self.left_button_17)
        self.left_button_20 = QPushButton(self.grpKBase)
        self.left_button_20.setObjectName(u"left_button_20")
        sizePolicy.setHeightForWidth(self.left_button_20.sizePolicy().hasHeightForWidth())
        self.left_button_20.setSizePolicy(sizePolicy)
        self.left_button_20.setVisible(False)
        self.kbaseLayout.addWidget(self.left_button_20)
        self.verticalLayout.addWidget(self.grpKBase)
        self.grpSettings = QGroupBox(self.sidePanel)
        self.grpSettings.setObjectName(u"grpSettings")
        self.settingsLayout = QVBoxLayout(self.grpSettings)
        self.settingsLayout.setSpacing(5)
        self.settingsLayout.setContentsMargins(5, 5, 5, 5)
        self.settingsLayout.setObjectName(u"settingsLayout")
        self.left_button_18 = QPushButton(self.grpSettings)
        self.left_button_18.setObjectName(u"left_button_18")
        self.settingsLayout.addWidget(self.left_button_18)
        self.left_button_19 = QPushButton(self.grpSettings)
        self.left_button_19.setObjectName(u"left_button_19")
        self.settingsLayout.addWidget(self.left_button_19)
        self.verticalLayout.addWidget(self.grpSettings)
        self.verticalSpacerBottom = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(self.verticalSpacerBottom)
        self.labelVersion = QLabel(self.sidePanel)
        self.labelVersion.setObjectName(u"labelVersion")
        self.labelVersion.setAlignment(Qt.AlignCenter)
        sizePolicy.setHeightForWidth(self.labelVersion.sizePolicy().hasHeightForWidth())
        self.labelVersion.setSizePolicy(sizePolicy)
        self.labelVersion.setMaximumWidth(128)
        self.labelVersion.setMinimumHeight(31)
        self.labelVersion.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.addWidget(self.labelVersion)
        self.labelVersionNumber = QLabel(self.sidePanel)
        self.labelVersionNumber.setObjectName(u"labelVersionNumber")
        self.labelVersionNumber.setAlignment(Qt.AlignCenter)
        sizePolicy.setHeightForWidth(self.labelVersionNumber.sizePolicy().hasHeightForWidth())
        self.labelVersionNumber.setSizePolicy(sizePolicy)
        self.labelVersionNumber.setMaximumWidth(128)
        self.labelVersionNumber.setMinimumHeight(16)
        self.labelVersionNumber.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.addWidget(self.labelVersionNumber)
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(self.verticalSpacer)
        self.horizontalLayout.addWidget(self.sidePanel)
        self.mainPanelLayout = QVBoxLayout()
        self.mainPanelLayout.setObjectName(u"mainPanelLayout")
        self.treeViewMain = QTreeView(self.centralwidget)
        self.treeViewMain.setObjectName(u"treeViewMain")
        self.mainPanelLayout.addWidget(self.treeViewMain)
        self.footerLayout = QHBoxLayout()
        self.footerLayout.setObjectName(u"footerLayout")
        self.down_button_1 = QPushButton(self.centralwidget)
        self.down_button_1.setObjectName(u"down_button_1")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.down_button_1.sizePolicy().hasHeightForWidth())
        self.down_button_1.setSizePolicy(sizePolicy1)
        self.down_button_1.setMinimumSize(QSize(100, 30))
        self.footerLayout.addWidget(self.down_button_1)
        self.down_button_2 = QPushButton(self.centralwidget)
        self.down_button_2.setObjectName(u"down_button_2")
        sizePolicy1.setHeightForWidth(self.down_button_2.sizePolicy().hasHeightForWidth())
        self.down_button_2.setSizePolicy(sizePolicy1)
        self.down_button_2.setMinimumSize(QSize(100, 30))
        self.footerLayout.addWidget(self.down_button_2)
        self.down_button_3 = QPushButton(self.centralwidget)
        self.down_button_3.setObjectName(u"down_button_3")
        sizePolicy1.setHeightForWidth(self.down_button_3.sizePolicy().hasHeightForWidth())
        self.down_button_3.setSizePolicy(sizePolicy1)
        self.down_button_3.setMinimumSize(QSize(100, 30))
        self.footerLayout.addWidget(self.down_button_3)
        self.down_button_8 = QPushButton(self.centralwidget)
        self.down_button_8.setObjectName(u"down_button_8")
        sizePolicy1.setHeightForWidth(self.down_button_8.sizePolicy().hasHeightForWidth())
        self.down_button_8.setSizePolicy(sizePolicy1)
        self.down_button_8.setMinimumSize(QSize(100, 30))
        self.footerLayout.addWidget(self.down_button_8)
        self.down_button_9 = QPushButton(self.centralwidget)
        self.down_button_9.setObjectName(u"down_button_9")
        sizePolicy1.setHeightForWidth(self.down_button_9.sizePolicy().hasHeightForWidth())
        self.down_button_9.setSizePolicy(sizePolicy1)
        self.down_button_9.setMinimumSize(QSize(100, 30))
        self.footerLayout.addWidget(self.down_button_9)
        # self.down_button_4 = QPushButton(self.centralwidget)  # Hidden: List Systems
        # self.down_button_4.setObjectName(u"down_button_4")
        # sizePolicy1.setHeightForWidth(self.down_button_4.sizePolicy().hasHeightForWidth())
        # self.down_button_4.setSizePolicy(sizePolicy1)
        # self.down_button_4.setMinimumSize(QSize(100, 30))
        # self.footerLayout.addWidget(self.down_button_4)  # Hidden: List Systems
        # self.down_button_5 = QPushButton(self.centralwidget)  # Hidden: List Users
        # self.down_button_5.setObjectName(u"down_button_5")
        # sizePolicy1.setHeightForWidth(self.down_button_5.sizePolicy().hasHeightForWidth())
        # self.down_button_5.setSizePolicy(sizePolicy1)
        # self.down_button_5.setMinimumSize(QSize(100, 30))
        # self.footerLayout.addWidget(self.down_button_5)  # Hidden: List Users
        self.down_button_6 = QPushButton(self.centralwidget)
        self.down_button_6.setObjectName(u"down_button_6")
        sizePolicy1.setHeightForWidth(self.down_button_6.sizePolicy().hasHeightForWidth())
        self.down_button_6.setSizePolicy(sizePolicy1)
        self.down_button_6.setMinimumSize(QSize(100, 30))
        self.footerLayout.addWidget(self.down_button_6)
        self.down_button_7 = QPushButton(self.centralwidget)
        self.down_button_7.setObjectName(u"down_button_7")
        sizePolicy1.setHeightForWidth(self.down_button_7.sizePolicy().hasHeightForWidth())
        self.down_button_7.setSizePolicy(sizePolicy1)
        self.down_button_7.setMinimumSize(QSize(100, 30))
        self.footerLayout.addWidget(self.down_button_7)
        self.more_button = QPushButton(self.centralwidget)
        self.more_button.setObjectName(u"more_button")
        sizePolicy1.setHeightForWidth(self.more_button.sizePolicy().hasHeightForWidth())
        self.more_button.setSizePolicy(sizePolicy1)
        self.more_button.setMinimumSize(QSize(100, 30))
        self.more_button.setText("Quick Reference")
        # Menu will be created and configured in kanvas.py to avoid C++ object deletion issues
        self.footerLayout.addWidget(self.more_button)
        self.labelFileStatus = QLabel(self.centralwidget)
        self.labelFileStatus.setObjectName(u"labelFileStatus")
        self.footerLayout.addWidget(self.labelFileStatus)
        self.mainPanelLayout.addLayout(self.footerLayout)
        self.horizontalLayout.addLayout(self.mainPanelLayout)
        KanvasMainWindow.setCentralWidget(self.centralwidget)
        self.retranslateUi(KanvasMainWindow)
        QMetaObject.connectSlotsByName(KanvasMainWindow)
    # setupUi

    def retranslateUi(self, KanvasMainWindow):
        KanvasMainWindow.setWindowTitle(QCoreApplication.translate("KanvasMainWindow", u"kanvas - IR Case Management", None))
        self.sidePanel.setStyleSheet(QCoreApplication.translate("KanvasMainWindow", u"\n"
"        QFrame {\n"
"            background-color: #2B2B2B;\n"
"            color: white;\n"
"            font-family: Arial;\n"
"        }\n"
"        QPushButton {\n"
"            background-color: #4A4A4A;\n"
"            color: white;\n"
"            border: 1px solid #5A5A5A;\n"
"            border-radius: 5px;\n"
"            padding: 5px;\n"
"            font-size: 12px;\n"
"            font-family: Arial;\n"
"        }\n"
"        QPushButton:hover {\n"
"            background-color: #5A5A5A;\n"
"            border: 1px solid #6A6A6A;\n"
"        }\n"
"        QLabel {\n"
"            color: white;\n"
"            font-weight: bold;\n"
"            margin-bottom: 10px;\n"
"            text-align: center;\n"
"            font-family: Arial;\n"
"        }\n"
"        QGroupBox {\n"
"            border: 1px solid #5A5A5A;\n"
"            border-radius: 5px;\n"
"            margin-top: 1ex;\n"
"            padding-top: 15px;  /* Add top padding to prevent overlap */\n"
"            color: white;\n"
" "
                        "           font-family: Arial;\n"
"        }\n"
"        QGroupBox::title {\n"
"            subcontrol-origin: margin;\n"
"            subcontrol-position: top center; /* Center the title for better appearance */\n"
"            padding: 0 5px;\n"
"            color: white;\n"
"            margin-top: 5px; /* Add more margin to the title */\n"
"        }\n"
"       ", None))
        self.grpCase.setTitle(QCoreApplication.translate("KanvasMainWindow", u"Case", None))
        self.left_button_7.setText(QCoreApplication.translate("KanvasMainWindow", u"New Case", None))
        self.left_button_8.setText(QCoreApplication.translate("KanvasMainWindow", u"Open Case", None))
        self.left_button_6.setText(QCoreApplication.translate("KanvasMainWindow", u"Timeline", None))
        self.left_button_5.setText(QCoreApplication.translate("KanvasMainWindow", u"Lateral Movement", None))
        self.left_button_4.setText(QCoreApplication.translate("KanvasMainWindow", u"ATTACK Summary", None))
        self.left_button_3.setText(QCoreApplication.translate("KanvasMainWindow", u"D3FEND Mapping", None))
        self.left_button_2.setText(QCoreApplication.translate("KanvasMainWindow", u"VERIS Reporting", None))
        self.left_button_21.setText(QCoreApplication.translate("KanvasMainWindow", u"Flow Builder", None))
        self.left_button_23.setText(QCoreApplication.translate("KanvasMainWindow", u"Generate Report", None))
        self.labelSheet.setText(QCoreApplication.translate("KanvasMainWindow", u"Select Sheet", None))
        self.grpLookups.setTitle(QCoreApplication.translate("KanvasMainWindow", u"Lookups", None))
        self.left_button_9.setText(QCoreApplication.translate("KanvasMainWindow", u"IP Insights", None))
        self.left_button_11.setText(QCoreApplication.translate("KanvasMainWindow", u"Domain Insights", None))
        self.left_button_22.setText(QCoreApplication.translate("KanvasMainWindow", u"Email Insights", None))
        self.left_button_12.setText(QCoreApplication.translate("KanvasMainWindow", u"File Insights", None))
        self.left_button_13.setText(QCoreApplication.translate("KanvasMainWindow", u"App-ID Insights", None))
        self.left_button_14.setText(QCoreApplication.translate("KanvasMainWindow", u"CVE Insights", None))
        self.left_button_10.setText(QCoreApplication.translate("KanvasMainWindow", u"Ransomware Victims", None))
        self.grpKBase.setTitle(QCoreApplication.translate("KanvasMainWindow", u"KBase", None))
        self.left_button_15.setText(QCoreApplication.translate("KanvasMainWindow", u"Markdowns", None))
        self.left_button_16.setText(QCoreApplication.translate("KanvasMainWindow", u"Bookmarks", None))
        self.left_button_17.setText(QCoreApplication.translate("KanvasMainWindow", u"Win Event ID", None))
        self.grpSettings.setTitle(QCoreApplication.translate("KanvasMainWindow", u"Settings", None))
        self.left_button_18.setText(QCoreApplication.translate("KanvasMainWindow", u"API Settings", None))
        self.left_button_19.setText(QCoreApplication.translate("KanvasMainWindow", u"Download Updates", None))
        self.labelVersion.setText(QCoreApplication.translate("KanvasMainWindow", u"K.a.n.v.a.s", None))
        self.labelVersion.setStyleSheet(QCoreApplication.translate("KanvasMainWindow", u"background-color: #E51448; color: white; text-align: center; font-family: Arial; font-size: 10pt; font-weight: normal;", None))
        self.labelVersionNumber.setText(QCoreApplication.translate("KanvasMainWindow", u" Version 0.4.6", None))
        self.labelVersionNumber.setStyleSheet(QCoreApplication.translate("KanvasMainWindow", u"color: white; text-align: center; font-family: Arial; font-size: 8pt; font-weight: normal;", None))
        self.down_button_1.setText(QCoreApplication.translate("KanvasMainWindow", u"Add New Entry", None))
        self.down_button_2.setText(QCoreApplication.translate("KanvasMainWindow", u"Delete Entry", None))
        self.down_button_3.setText(QCoreApplication.translate("KanvasMainWindow", u"Refresh Table", None))
        # self.down_button_4.setText(QCoreApplication.translate("KanvasMainWindow", u"List Systems", None))  # Hidden: List Systems
        # self.down_button_5.setText(QCoreApplication.translate("KanvasMainWindow", u"List Users", None))    # Hidden: List Users
        self.down_button_6.setText(QCoreApplication.translate("KanvasMainWindow", u"Defang", None))
        self.down_button_7.setText(QCoreApplication.translate("KanvasMainWindow", u"STIX Export", None))
        self.down_button_8.setText(QCoreApplication.translate("KanvasMainWindow", u"Add EvidenceType", None))
        self.down_button_9.setText(QCoreApplication.translate("KanvasMainWindow", u"Add System Type", None))
        self.more_button.setText(QCoreApplication.translate("KanvasMainWindow", u"Quick Reference", None))
        self.labelFileStatus.setText(QCoreApplication.translate("KanvasMainWindow", u"File Path", None))
    # retranslateUi


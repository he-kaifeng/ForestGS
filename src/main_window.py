import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFileSystemModel, QIcon, QAction, QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QSplitter,
    QTreeView, QTabWidget, QToolBar,
    QFileDialog, QStatusBar, QLabel, QHeaderView, QMessageBox
)

from data_management_tab import DataManagementTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("林木基因组育种分析平台")
        self.resize(1280, 720)

        # 初始化核心组件
        self.init_models()
        self.init_ui()
        self.init_connections()

    # --------------------------
    # 初始化方法
    # --------------------------
    def init_models(self):
        """ 初始化数据模型 """
        # 文件系统模型，用于目录树显示
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")  # 设置根目录为空

    def init_ui(self):
        """ 初始化界面布局 """
        # 主布局：水平分割器
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 设置文件夹显示和工作区
        self.setup_file_tree()
        self.setup_workspace_tabs()

        # 将文件夹显示区域和工作区添加到分割器
        self.main_splitter.addWidget(self.file_tree_widget)
        self.main_splitter.addWidget(self.workspace_tabs)
        self.main_splitter.setSizes([300, 980])

        # 设置中心部件
        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.addWidget(self.main_splitter)
        self.setCentralWidget(central_widget)

        # 设置菜单栏、工具栏和状态栏
        self.setup_menubar()
        self.setup_toolbar()
        self.setup_statusbar()

    def init_connections(self):
        """ 初始化信号连接 """
        self.file_tree.doubleClicked.connect(self.on_file_double_click)  # 双击文件

    # --------------------------
    # UI 组件设置方法
    # --------------------------
    def setup_file_tree(self):
        """ 设置文件夹显示区域 """
        self.file_tree_widget = QWidget()
        layout = QVBoxLayout(self.file_tree_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIsDecorated(False)  # 不显示子节点线条
        self.file_tree.setAlternatingRowColors(True)  # 显示交替行背景色
        self.file_tree.header().setStretchLastSection(False)  # 不拉伸最后一列
        self.file_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 文件名列拉伸
        self.file_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 大小列自适应内容

        # 仅显示文件名和文件大小
        self.file_model.setHeaderData(1, Qt.Orientation.Horizontal, "大小")
        for i in range(2, 4):  # 隐藏日期和类型列
            self.file_tree.setColumnHidden(i, True)

        layout.addWidget(self.file_tree)

    def setup_workspace_tabs(self):
        """ 设置右侧工作区标签页 """
        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.addTab(DataManagementTab(plink_path='../bin/plink.exe'), "基因型数据处理")
        self.workspace_tabs.addTab(QLabel("表型数据管理"), "表型数据处理")
        self.workspace_tabs.addTab(QLabel("基因组选择模型"), "GWAS")
        self.workspace_tabs.addTab(QLabel("育种值预测"), "GS")

    def setup_menubar(self):
        """ 设置菜单栏 """
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("打开项目", self.open_project)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

    def setup_toolbar(self):
        """ 设置工具栏 """
        toolbar = QToolBar("快速操作")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        # 添加工具栏按钮：打开项目
        open_project_action = QAction(QIcon("icons/open_folder.png"), "打开文件夹", self)
        open_project_action.triggered.connect(self.open_project)
        toolbar.addAction(open_project_action)

        # 添加工具栏按钮：显示/隐藏文件夹区域
        toggle_file_tree_action = QAction(QIcon("icons/folder.png"), "显示/隐藏文件夹", self)
        toggle_file_tree_action.triggered.connect(self.toggle_file_tree)
        toolbar.addAction(toggle_file_tree_action)

    def setup_statusbar(self):
        """ 设置状态栏 """
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    # --------------------------
    # 核心功能方法
    # --------------------------
    def open_project(self):
        """ 打开项目目录 """
        dir_path = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if dir_path:
            self.file_model.setRootPath(dir_path)
            self.file_tree.setRootIndex(self.file_model.index(dir_path))
            self.status_bar.showMessage(f"已打开项目: {dir_path}")

    def toggle_file_tree(self):
        """ 显示或隐藏文件夹显示区域 """
        if self.file_tree_widget.isVisible():
            self.file_tree_widget.hide()
            self.main_splitter.setSizes([0, 1280])  # 文件夹区域宽度为 0
        else:
            self.file_tree_widget.show()
            self.main_splitter.setSizes([300, 980])  # 文件夹区域宽度为 300

    def on_file_double_click(self, index):
        """ 双击文件打开到工作区 """
        file_path = self.file_model.filePath(index)

        if os.path.isfile(file_path):
            self.status_bar.showMessage(f"已选中文件: {file_path}")

            # 获取当前激活的标签页
            current_tab = self.workspace_tabs.currentWidget()

            # 检查标签页是否具有处理文件路径的方法
            if hasattr(current_tab, "handle_file_path"):
                current_tab.handle_file_path(file_path)
            else:
                self.status_bar.showMessage(f"当前标签页不支持文件处理: {type(current_tab).__name__}")

    def closeEvent(self, event: QCloseEvent):
        reply = QMessageBox.question(self, '退出', '是否确认退出?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()

import os

from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QTextEdit, QMessageBox, QFileDialog, QLineEdit

from file_preview_dialog import FilePreviewDialog


class CommonTab(QWidget):
    def __init__(self):
        super().__init__()
        # 设置窗口样式
        self.setStyleSheet("""
            QWidget {
                font-family: "Segoe UI";
                font-size: 12px;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            DraggableLineEdit, QComboBox {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QTextEdit {
                border: 1px solid #ccc;
                border-radius: 3px;
                padding: 5px;
            }
            QRadioButton {
                font-size: 12px;
            }
            QCheckBox {
                font-size: 12px;
            }
        """)

    def create_log_group(self):
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        log_group.setLayout(log_layout)
        return log_group

    def select_path(self, line_edit, mode="file"):
        try:
            if mode == "file":
                path, _ = QFileDialog.getOpenFileName(self, "选择文件")
            elif mode == "directory":
                path = QFileDialog.getExistingDirectory(self, "选择目录")
            else:
                raise ValueError("Invalid mode. Use 'file' or 'directory'.")
            if path:
                line_edit.setText(path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"选择路径时发生错误: {str(e)}")

    def preview_file(self, file_path):
        try:
            self.log_view.append(f'预览文件 {file_path}')
            if not file_path or not os.path.isfile(file_path):
                raise FileNotFoundError("文件路径无效，请先选择或传递文件！")
            dialog = FilePreviewDialog(file_path, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))


class DraggableLineEdit(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)  # 允许拖入

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖入事件：检查是否有文件路径"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """拖放事件：处理文件路径"""
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()  # 获取第一个文件的本地路径
            self.setText(file_path)  # 设置文本内容
            event.acceptProposedAction()
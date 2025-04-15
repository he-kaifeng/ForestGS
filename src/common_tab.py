import os

from PyQt6.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QTextEdit, QMessageBox, QFileDialog

from file_preview_dialog import FilePreviewDialog


class CommonTab(QWidget):
    def __init__(self):
        super().__init__()

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

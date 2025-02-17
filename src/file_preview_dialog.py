from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import Qt


class FilePreviewDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件预览")
        self.resize(800, 600)

        # 主布局
        layout = QVBoxLayout()

        # 文本显示区域
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        # 加载文件内容
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            self.text_edit.setPlainText(content)
        except Exception as e:
            self.text_edit.setPlainText(f"无法加载文件内容:\n{str(e)}")

        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont, QImage
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QScrollArea, QWidget, QTextEdit


class FilePreviewDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文件预览")
        self.resize(800, 600)

        # 主布局
        layout = QVBoxLayout()

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        # 内容显示区域
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        scroll_area.setWidget(content_widget)

        # 加载文件内容
        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
                image_label = QLabel()
                pixmap = QPixmap(file_path)

                # 获取窗口的大小
                max_width = self.width() - 40  # 留一些边距
                max_height = self.height() - 100  # 为关闭按钮留些空间

                # 缩放图片
                scaled_pixmap = self.scale_image(pixmap, max_width, max_height)

                image_label.setPixmap(scaled_pixmap)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                content_layout.addWidget(image_label)
            else:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                text_edit = QTextEdit()
                text_edit.setPlainText(content)
                text_edit.setReadOnly(True)
                font = QFont("Courier", 10)
                text_edit.setFont(font)
                content_layout.addWidget(text_edit)
        except Exception as e:
            error_label = QLabel(f"无法加载文件内容:\n{str(e)}")
            error_label.setWordWrap(True)
            content_layout.addWidget(error_label)

        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # 关闭按钮
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)

    def scale_image(self, pixmap, max_width, max_height):
        # 获取原始图片的尺寸
        original_width = pixmap.width()
        original_height = pixmap.height()

        # 计算缩放比例
        width_ratio = max_width / original_width
        height_ratio = max_height / original_height
        scale_ratio = min(width_ratio, height_ratio)

        # 如果图片小于最大尺寸，则不进行缩放
        if scale_ratio >= 1:
            return pixmap

        # 计算新的尺寸
        new_width = int(original_width * scale_ratio)
        new_height = int(original_height * scale_ratio)

        # 缩放图片
        return pixmap.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
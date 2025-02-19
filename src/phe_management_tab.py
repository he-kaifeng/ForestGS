import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QDoubleSpinBox, QGroupBox, QFormLayout, QFileDialog,
    QLabel, QGridLayout, QMessageBox, QComboBox, QSizePolicy
)

from file_preview_dialog import FilePreviewDialog

# 设置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PhenoManagementTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # 主垂直布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # 初始化文件选择组
        file_group = self.create_file_group()

        # 初始化参数设置组
        param_group = self.create_param_group()
        normalization_group = self.create_normalization_group()
        recoding_group = self.create_recoding_group()

        # 初始化运行日志组
        log_group = self.create_log_group()

        # --- 布局排列 ---
        grid_layout = QGridLayout()
        grid_layout.addWidget(file_group, 0, 0, 1, 2)  # 跨两列
        grid_layout.addWidget(param_group, 1, 0, 1, 2)  # 跨两列
        grid_layout.addWidget(normalization_group, 2, 0)
        grid_layout.addWidget(recoding_group, 2, 1)

        # 设置列宽自适应
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        # 主布局组合
        main_layout.addLayout(grid_layout)
        main_layout.addWidget(log_group, stretch=1)

        self.setLayout(main_layout)

    def create_file_group(self):
        # --- 文件选择组 ---
        file_group = QGroupBox("表型文件选择")
        file_layout = QVBoxLayout()

        # 输入文件路径
        input_file_label = QLabel("表型数据文件")
        input_file_label.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(input_file_label)

        file_path_layout = QHBoxLayout()
        self.input_file_path = QLineEdit()
        btn_select_file = QPushButton("选择目标文件")
        btn_select_file.clicked.connect(lambda: self.select_path(self.input_file_path, mode="file"))
        btn_preview = QPushButton("预览")
        btn_preview.clicked.connect(self.preview_file)
        file_path_layout.addWidget(self.input_file_path, stretch=3)
        file_path_layout.addWidget(btn_select_file, stretch=1)
        file_path_layout.addWidget(btn_preview, stretch=1)
        file_layout.addLayout(file_path_layout)

        # 输出目录选择
        output_label = QLabel("结果输出目录")
        output_label.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(output_label)

        output_path_layout = QHBoxLayout()
        self.output_dir = QLineEdit()
        btn_output = QPushButton("选择结果路径")
        btn_output.clicked.connect(lambda: self.select_path(self.output_dir, "directory"))
        output_path_layout.addWidget(self.output_dir, stretch=3)
        output_path_layout.addWidget(btn_output, stretch=2)
        file_layout.addLayout(output_path_layout)

        file_group.setLayout(file_layout)
        return file_group

    def create_param_group(self):
        param_group = QGroupBox("异常值过滤")
        param_layout = QFormLayout()

        # 性状列选择
        self.trait_combobox = QComboBox()
        self.trait_combobox.setEditable(False)
        self.trait_combobox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        param_layout.addRow("选择过滤性状:", self.trait_combobox)

        # 标准差倍数选择
        self.sd_spin = QDoubleSpinBox()
        self.sd_spin.setRange(1.0, 5.0)
        self.sd_spin.setValue(3.0)
        self.sd_spin.setSingleStep(0.5)
        self.sd_spin.setSuffix(" 倍标准差")
        param_layout.addRow("异常值阈值:", self.sd_spin)

        # 执行按钮
        self.btn_param = QPushButton("执行异常值过滤")
        self.btn_param.setStyleSheet("background-color: #2196F3; color: white;")
        param_layout.addWidget(self.btn_param)

        param_group.setLayout(param_layout)
        return param_group

    def create_recoding_group(self):
        recoding_group = QGroupBox("数据归一化")
        recoding_layout = QFormLayout()

        self.recoding_combobox = QComboBox()
        self.recoding_combobox.setEditable(False)
        self.recoding_combobox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        recoding_layout.addRow("选择分析性状:", self.recoding_combobox)

        self.normalization_method = QComboBox()
        self.normalization_method.addItems(["Z-score标准化", "Min-Max归一化"])
        recoding_layout.addRow("归一化方法:", self.normalization_method)
        recoding_group.setLayout(recoding_layout)

        self.btn_recoding = QPushButton("执行数据归一化")
        self.btn_recoding.setStyleSheet("background-color: #2196F3; color: white;")
        recoding_layout.addWidget(self.btn_recoding)

        return recoding_group

    def create_normalization_group(self):
        normalization_group = QGroupBox("数据重编码")
        main_layout = QVBoxLayout()

        # ==== 性状选择 ====
        form_layout = QFormLayout()
        self.normalization_combobox = QComboBox()
        form_layout.addRow(QLabel("选择重编码性状:"), self.normalization_combobox)

        # ==== 转换方向 ====
        self.recoding_direction = QComboBox()
        self.recoding_direction.addItems([
            "word2num（表型→数字）",
            "num2word（数字→表型）"
        ])
        form_layout.addRow(QLabel("转换方向:"), self.recoding_direction)

        main_layout.addLayout(form_layout)

        # ==== 文件选择（保持原有结构）====
        self.mapping_file_widget = QWidget()
        file_layout = QHBoxLayout()
        self.mapping_file_edit = QLineEdit()
        self.mapping_file_btn = QPushButton("选择转化表")
        self.mapping_file_btn.clicked.connect(lambda: self.select_path(self.output_dir, "file"))
        file_layout.addWidget(self.mapping_file_edit)
        file_layout.addWidget(self.mapping_file_btn)
        self.mapping_file_widget.setLayout(file_layout)
        main_layout.addWidget(QLabel("转化表文件:"))
        main_layout.addWidget(self.mapping_file_widget)
        self.mapping_file_widget.hide()

        # ==== 事件绑定 ====
        self.recoding_direction.currentIndexChanged.connect(self._toggle_mapping_file)

        # ==== 执行按钮 ====
        self.execute_recoding_btn = QPushButton("执行转换")
        main_layout.addWidget(self.execute_recoding_btn, alignment=Qt.AlignmentFlag.AlignRight)

        normalization_group.setLayout(main_layout)
        return normalization_group

    def _toggle_mapping_file(self):
        """切换转化表文件控件的可见性"""
        is_num2word = "num2word" in self.recoding_direction.currentText()
        self.mapping_file_widget.setVisible(is_num2word)

    def create_log_group(self):
        # --- 运行日志 ---
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        log_group.setLayout(log_layout)
        return log_group

    def select_path(self, line_edit, mode="file"):
        """通用路径选择方法"""
        try:
            if mode == "file":
                path, _ = QFileDialog.getOpenFileName(self, "选择文件")
            elif mode == "directory":
                path = QFileDialog.getExistingDirectory(self, "选择输出目录")
            else:
                raise ValueError("Invalid mode. Use 'file' or 'directory'.")

            if path:
                line_edit.setText(path)
        except Exception as e:
            logger.error(f"Error selecting path: {e}")
            QMessageBox.critical(self, "错误", f"选择路径时发生错误: {e}")

    def preview_file(self):
        """文件预览功能"""
        file_path = self.input_file_path.text()
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "错误", "无效的文件路径！")
            return

        try:
            if not os.access(file_path, os.R_OK):
                QMessageBox.warning(self, "错误", "无法读取文件，请检查文件权限！")
                return

            dialog = FilePreviewDialog(file_path, self)
            dialog.exec()
        except Exception as e:
            logger.error(f"Error previewing file: {e}")
            QMessageBox.critical(self, "错误", f"预览文件时发生错误: {e}")

    def validate_input(self):
        """验证输入合法性"""
        if not self.input_file_path.text() or not os.path.isfile(self.input_file_path.text()):
            QMessageBox.warning(self, "错误", "请先选择有效的表型数据文件！")
            return False

        if not self.output_dir.text() or not os.path.isdir(self.output_dir.text()):
            QMessageBox.warning(self, "错误", "请先选择有效的输出目录！")
            return False

        if self.trait_combobox.currentText() == "":
            QMessageBox.warning(self, "错误", "请选择要分析的性状！")
            return False

        if not 1.0 <= self.sd_spin.value() <= 5.0:
            QMessageBox.warning(self, "错误", "标准差倍数应在1.0到5.0之间！")
            return False

        return True

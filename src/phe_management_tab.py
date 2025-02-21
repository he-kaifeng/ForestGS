import os

import pandas as pd
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QDoubleSpinBox, QGroupBox, QFormLayout, QFileDialog,
    QLabel, QGridLayout, QMessageBox, QComboBox, QSizePolicy
)

from file_preview_dialog import FilePreviewDialog
from pheno_operations import PhenoOperations


# todo 相关性分析
class PhenoManagementTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.worker = PhenoOperations()  # 业务逻辑对象
        self.thread = QThread()  # 新线程
        self.worker.moveToThread(self.thread)  # 将业务逻辑移动到新线程
        self.connect_signals()  # 连接信号和槽
        self.thread.start()

    def connect_signals(self):
        # 连接业务逻辑的信号到UI的槽
        self.worker.progress_signal.connect(self.log_view.append)
        self.worker.error_signal.connect(lambda msg: QMessageBox.critical(self, "错误", msg))
        self.worker.result_signal.connect(self.handle_result)

        # 连接按钮点击事件到业务逻辑
        self.btn_param.clicked.connect(self.run_outlier_filter)
        self.btn_recoding.clicked.connect(self.run_normalization)
        self.btn_missing_value.clicked.connect(self.run_missing_value_fill)
        self.btn_execute_recoding.clicked.connect(self.run_recoding)

    def run_missing_value_fill(self):
        """执行缺失值填充"""
        if not self.validate_input():
            return
        trait = self.missing_value_combobox.currentText()
        method = self.missing_value_method.currentText()
        out_dir = self.output_dir.text()
        self.worker.start_missing_value_fill.emit(self.phenotype_data, trait, method, out_dir)

    def run_outlier_filter(self):
        """执行异常值过滤"""
        if not self.validate_input():
            return
        trait = self.trait_combobox.currentText()
        sd_multiplier = self.sd_spin.value()
        out_dir = self.output_dir.text()
        self.worker.start_outlier_filter.emit(self.phenotype_data, trait, sd_multiplier, out_dir)

    def run_normalization(self):
        """执行数据归一化"""
        if not self.validate_input():
            return
        trait = self.recoding_combobox.currentText()
        method = self.normalization_method.currentText()
        out_dir = self.output_dir.text()
        self.worker.start_normalization.emit(self.phenotype_data, trait, method, out_dir)

    def run_recoding(self):
        """执行数据重编码"""
        if not self.validate_input():
            return
        trait = self.normalization_combobox.currentText()
        direction = self.recoding_direction.currentText()
        out_dir = self.output_dir.text()
        mapping_file = None
        if direction == "num2word（数字→表型）":
            mapping_file = self.mapping_file_edit.text()
            if not mapping_file or not os.path.isfile(mapping_file):
                QMessageBox.warning(self, "错误", "请选择有效的转化表文件！")
                return
        self.worker.start_recoding.emit(self.phenotype_data, trait, direction, out_dir, mapping_file)

    def handle_result(self, result):
        """处理业务逻辑返回的结果"""
        self.phenotype_data = result
        self.log_view.append("数据处理完成，结果已更新")

    def closeEvent(self, event):
        """关闭窗口时停止线程"""
        self.thread.quit()
        self.thread.wait()
        super().closeEvent(event)

    def init_ui(self):
        # 主垂直布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # 初始化文件选择组
        file_group = self.create_file_group()

        # 初始化功能组
        param_group = self.create_param_group()
        normalization_group = self.create_normalization_group()
        recoding_group = self.create_recoding_group()
        missing_value_group = self.create_missing_value_group()

        # 初始化运行日志组
        log_group = self.create_log_group()

        # 布局排列
        grid_layout = QGridLayout()
        grid_layout.addWidget(file_group, 0, 0, 1, 2)  # 跨两列
        grid_layout.addWidget(param_group, 1, 1)
        grid_layout.addWidget(normalization_group, 2, 0)
        grid_layout.addWidget(recoding_group, 2, 1)
        grid_layout.addWidget(missing_value_group, 1, 0)

        # 设置列宽自适应
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        # 主布局组合
        main_layout.addLayout(grid_layout)
        main_layout.addWidget(log_group, stretch=1)

        self.setLayout(main_layout)

    def create_file_group(self):
        file_group = QGroupBox("表型文件选择")
        file_layout = QVBoxLayout()

        # 输入文件路径
        input_file_label = QLabel("表型数据文件")
        input_file_label.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(input_file_label)

        file_path_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        btn_select_file = QPushButton("选择目标文件")
        btn_select_file.clicked.connect(self.open_file)
        btn_preview = QPushButton("预览")
        btn_preview.clicked.connect(self.preview_file)
        file_path_layout.addWidget(self.file_path, stretch=3)
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

    def open_file(self):
        # 获取文件路径
        self.select_path(self.file_path, mode="file")
        file_path = self.file_path.text()
        # 检查文件路径是否为空或无效
        if not file_path or not os.path.isfile(file_path):
            return
        # 加载表型数据
        self.load_phenotype_data(file_path)

    def load_phenotype_data(self, file_path):
        try:
            # 文件格式自动识别
            if file_path.endswith('.csv'):
                self.phenotype_data = pd.read_csv(file_path, encoding='utf-8')
            elif file_path.endswith(('.xlsx', '.xls')):
                self.phenotype_data = pd.read_excel(file_path, engine='openpyxl')
            elif file_path.endswith('.txt'):
                self.phenotype_data = pd.read_csv(file_path, sep='\t')
            else:
                raise ValueError("不支持的文件格式")
            self.columns = self.phenotype_data.columns.tolist()
            self.columns[0] = 'all'
            self.add_items()
            self.log_view.setText(f"成功加载表型数据\t{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "数据加载错误",
                                 f"无法加载表型数据：\n{str(e)}\n"
                                 f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")
            self.log_view.setText("数据加载错误"
                                  f"无法加载表型数据：\n{str(e)}\n"
                                  f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")

    def add_items(self):
        self.trait_combobox.clear()
        self.recoding_combobox.clear()
        self.normalization_combobox.clear()
        self.missing_value_combobox.clear()

        self.trait_combobox.addItems(self.columns[1:])
        self.recoding_combobox.addItems(self.columns)
        self.normalization_combobox.addItems(self.columns[1:])
        self.missing_value_combobox.addItems(self.columns)

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
        self.sd_spin.setSingleStep(1)
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
        recoding_layout.addRow("选择归一化性状:", self.recoding_combobox)

        self.normalization_method = QComboBox()
        self.normalization_method.addItems(["Z-score", "Min-Max"])
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

        # ==== 文件选择====
        self.mapping_file_widget = QWidget()
        file_layout = QHBoxLayout()
        self.mapping_file_edit = QLineEdit()
        self.mapping_file_btn = QPushButton("选择转化表")
        self.mapping_file_btn.clicked.connect(lambda: self.select_path(self.mapping_file_edit, "file"))
        file_layout.addWidget(self.mapping_file_edit)
        file_layout.addWidget(self.mapping_file_btn)
        self.mapping_file_widget.setLayout(file_layout)
        main_layout.addWidget(QLabel("转化表文件:"))
        main_layout.addWidget(self.mapping_file_widget)
        self.mapping_file_widget.hide()

        # ==== 事件绑定 ====
        self.recoding_direction.currentIndexChanged.connect(self._toggle_mapping_file)

        self.btn_execute_recoding = QPushButton("执行转换")
        main_layout.addWidget(self.btn_execute_recoding, alignment=Qt.AlignmentFlag.AlignRight)

        normalization_group.setLayout(main_layout)
        return normalization_group

    def create_missing_value_group(self):
        # --- 缺失值填充组 ---
        missing_value_group = QGroupBox("缺失值填充")
        missing_value_layout = QFormLayout()
        # 性状列选择
        self.missing_value_combobox = QComboBox()
        self.missing_value_combobox.setEditable(False)
        self.missing_value_combobox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        missing_value_layout.addRow("选择填充性状:", self.missing_value_combobox)
        # 填充方法选择
        self.missing_value_method = QComboBox()
        self.missing_value_method.addItems(["均值填充", "中位数填充", "众数填充", "前向填充", "后向填充"])
        missing_value_layout.addRow("填充方法:", self.missing_value_method)
        # 执行按钮
        self.btn_missing_value = QPushButton("执行缺失值填充")
        self.btn_missing_value.setStyleSheet("background-color: #2196F3; color: white;")
        missing_value_layout.addWidget(self.btn_missing_value)
        missing_value_group.setLayout(missing_value_layout)
        return missing_value_group

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
            QMessageBox.critical(self, "错误", f"选择路径时发生错误: {e}")

    def preview_file(self):
        """文件预览功能"""
        file_path = self.file_path.text()
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
            QMessageBox.critical(self, "错误", f"预览文件时发生错误: {e}")

    def validate_input(self):
        """验证输入合法性"""
        if not self.file_path.text() or not os.path.isfile(self.file_path.text()):
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

    def handle_file_path(self, file_path):
        try:
            if not os.path.isfile(file_path):
                raise FileNotFoundError("文件路径无效，请先选择或传递文件！")
            self.file_path.setText(file_path)
            self.load_phenotype_data(file_path)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

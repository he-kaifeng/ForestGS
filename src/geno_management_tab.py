import os
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QDoubleSpinBox, QMessageBox, QGroupBox, QFormLayout, QComboBox, QFileDialog,
    QLabel, QGridLayout
)
from file_preview_dialog import FilePreviewDialog
from geno_operations import GenoOperations


class GenoManagementTab(QWidget):
    def __init__(self, plink_path):
        super().__init__()
        self.supported_formats = {
            "PLINK文本格式 (.ped)": "ped",
            "PLINK二进制格式 (.bed)": "bed",
            "VCF格式 (.vcf)": "vcf"
        }
        self.plink_path = plink_path
        self.init_ui()
        self.worker = GenoOperations(self.plink_path)  # 业务逻辑对象
        self.thread = QThread()  # 新线程
        self.worker.moveToThread(self.thread)  # 将业务逻辑移动到新线程
        self.connect_signals()  # 连接信号和槽
        self.thread.start()

    def init_ui(self):
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
            QLineEdit, QComboBox {
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
            QLabel {
                font-size: 12px;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # 文件选择组
        file_group = self.create_file_group()
        main_layout.addWidget(file_group)

        # 格式转换与质控组
        convert_qc_group = self.create_convert_qc_group()
        main_layout.addWidget(convert_qc_group)

        # 日志输出组
        log_group = self.create_log_group()
        main_layout.addWidget(log_group, stretch=1)

        self.setLayout(main_layout)

    def connect_signals(self):
        # 连接业务逻辑的信号到UI的槽
        self.worker.progress_signal.connect(self.log_view.append)
        self.worker.error_signal.connect(lambda msg: QMessageBox.critical(self, "错误", msg))
        self.worker.result_signal.connect(self.handle_result)
        # 连接按钮点击事件到业务逻辑
        self.btn_convert.clicked.connect(self.run_convert_format)
        self.btn_run_qc.clicked.connect(self.run_quality_control)
        self.btn_filter.clicked.connect(self.run_filter_data)
        self.btn_genetic_analysis.clicked.connect(self.run_genetic_analysis)

    def run_convert_format(self):
        """执行文件格式转换"""
        if not self.validate_input():
            return
        input_file = self.file_path.text()
        output_dir = self.output_path.text()
        target_format = self.supported_formats[self.target_format.currentText()]
        self.worker.start_convert_format.emit(input_file, output_dir, target_format)

    def run_quality_control(self):
        """执行质量控制"""
        if not self.validate_input():
            return
        input_file = self.file_path.text()
        output_dir = self.output_path.text()
        maf = self.maf_spin.value()
        missing_geno = self.missing_geno_spin.value()
        missing_sample = self.missing_sample_spin.value()
        r2 = self.r2_spin.value()
        self.worker.start_quality_control.emit(input_file, output_dir, maf, missing_geno, missing_sample, r2)

    def run_filter_data(self):
        """执行数据过滤"""
        if not self.validate_input():
            return
        input_file = self.file_path.text()
        output_dir = self.output_path.text()
        filter_sample = self.filter_sample_input.text()
        exclude_sample = self.exclude_sample_input.text()
        filter_snp = self.filter_snp_input.text()
        exclude_snp = self.exclude_snp_input.text()
        self.worker.start_filter_data.emit(input_file, output_dir, filter_sample, exclude_sample, filter_snp,
                                           exclude_snp)

    def run_genetic_analysis(self):
        """执行遗传结构分析"""
        if not self.validate_input():
            return
        input_file = self.file_path.text()
        output_dir = self.output_path.text()
        pca_components = self.pca_components_spin.value()
        relationship_method = self.relationship_method.currentText()
        extract_file = self.extract_file_edit.text()
        self.worker.start_genetic_analysis.emit(input_file, output_dir, pca_components, relationship_method,
                                                extract_file)

    def handle_result(self, result):
        """处理业务逻辑返回的结果"""
        self.log_view.append("数据处理完成，结果已更新")

    def validate_input(self):
        """验证输入是否有效"""
        if not self.file_path.text() or not os.path.isfile(self.file_path.text()):
            QMessageBox.warning(self, "错误", "请选择有效的输入文件！")
            return False
        if not self.output_path.text() or not os.path.isdir(self.output_path.text()):
            QMessageBox.warning(self, "错误", "请选择有效的输出目录！")
            return False
        return True

    def create_file_group(self):
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout()

        target_file_label = QLabel("基因型数据")
        target_file_label.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(target_file_label)

        file_path_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        btn_select_file = QPushButton("选择目标文件")
        btn_select_file.clicked.connect(lambda: self.select_path(self.file_path, mode="file"))
        btn_preview = QPushButton("预览")
        btn_preview.clicked.connect(self.preview_file)
        file_path_layout.addWidget(self.file_path, stretch=3)
        file_path_layout.addWidget(btn_select_file, stretch=1)
        file_path_layout.addWidget(btn_preview, stretch=1)
        file_layout.addLayout(file_path_layout)

        output_file_label = QLabel("结果输出目录")
        output_file_label.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(output_file_label)

        output_path_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        btn_output = QPushButton("选择输出路径")
        btn_output.clicked.connect(lambda: self.select_path(self.output_path, mode="directory"))
        output_path_layout.addWidget(self.output_path, stretch=3)
        output_path_layout.addWidget(btn_output, stretch=2)
        file_layout.addLayout(output_path_layout)

        file_group.setLayout(file_layout)
        return file_group

    def create_convert_qc_group(self):
        convert_qc_group = QGroupBox("基因型数据处理")
        convert_qc_layout = QGridLayout()

        # 格式转换
        convert_group = self.create_convert_group()
        convert_qc_layout.addWidget(convert_group, 1, 0)

        # 质量控制
        qc_group = self.create_qc_group()
        convert_qc_layout.addWidget(qc_group, 0, 0)

        # 数据过滤
        filter_group = self.create_filter_group()
        convert_qc_layout.addWidget(filter_group, 0, 1)

        # 遗传结构分析
        genetics_group = self.create_genetics_group()
        convert_qc_layout.addWidget(genetics_group, 1, 1)

        convert_qc_layout.setColumnStretch(0, 1)
        convert_qc_layout.setColumnStretch(1, 1)
        convert_qc_layout.setColumnMinimumWidth(0, 300)
        convert_qc_layout.setColumnMinimumWidth(1, 300)

        convert_qc_group.setLayout(convert_qc_layout)
        return convert_qc_group

    def create_convert_group(self):
        convert_group = QGroupBox("文件格式转换")
        convert_layout = QFormLayout()
        self.target_format = QComboBox()
        self.target_format.addItems(["PLINK文本格式 (.ped)", "PLINK二进制格式 (.bed)", "VCF格式 (.vcf)"])
        convert_layout.addRow("转换为格式:", self.target_format)
        self.btn_convert = QPushButton("执行转换")
        self.btn_convert.setStyleSheet("background-color: #FF9800; color: white;")
        convert_layout.addWidget(self.btn_convert)
        convert_group.setLayout(convert_layout)
        return convert_group

    def create_qc_group(self):
        qc_group = QGroupBox("质量控制")
        qc_layout = QFormLayout()
        self.maf_spin = QDoubleSpinBox()
        self.maf_spin.setRange(0.0, 0.5)
        self.maf_spin.setValue(0.05)
        self.maf_spin.setSingleStep(0.01)
        qc_layout.addRow("最小等位基因频率:", self.maf_spin)

        self.missing_geno_spin = QDoubleSpinBox()
        self.missing_geno_spin.setRange(0.0, 1.0)
        self.missing_geno_spin.setValue(0.1)
        self.missing_geno_spin.setSingleStep(0.05)
        qc_layout.addRow("SNP最大缺失率:", self.missing_geno_spin)

        self.missing_sample_spin = QDoubleSpinBox()
        self.missing_sample_spin.setRange(0.0, 1.0)
        self.missing_sample_spin.setValue(0.1)
        self.missing_sample_spin.setSingleStep(0.05)
        qc_layout.addRow("样本最大缺失率:", self.missing_sample_spin)

        self.r2_spin = QDoubleSpinBox()
        self.r2_spin.setRange(0.0, 1.0)
        self.r2_spin.setValue(0.8)
        self.r2_spin.setSingleStep(0.1)
        qc_layout.addRow("R² 阈值:", self.r2_spin)

        self.btn_run_qc = QPushButton("开始质控")
        self.btn_run_qc.setStyleSheet("background-color: #4CAF50; color: white;")
        qc_layout.addWidget(self.btn_run_qc)

        qc_group.setLayout(qc_layout)
        return qc_group

    def create_filter_group(self):
        filter_group = QGroupBox("数据过滤")
        filter_layout = QFormLayout()

        self.filter_sample_input, btn_filter_sample = self.create_file_selector("保留样本列表文件路径:")
        filter_layout.addRow("保留样本列表文件路径:", btn_filter_sample)

        self.exclude_sample_input, btn_exclude_sample = self.create_file_selector("排除样本列表文件路径:")
        filter_layout.addRow("排除样本列表文件路径:", btn_exclude_sample)

        self.filter_snp_input, btn_filter_snp = self.create_file_selector("保留SNP列表文件路径:")
        filter_layout.addRow("保留SNP列表文件路径:", btn_filter_snp)

        self.exclude_snp_input, btn_exclude_sample = self.create_file_selector("排除SNP列表文件路径:")
        filter_layout.addRow("排除SNP列表文件路径:", btn_exclude_sample)

        self.btn_filter = QPushButton("执行数据过滤")
        self.btn_filter.setStyleSheet("background-color: #FFC107; color: white;")
        filter_layout.addWidget(self.btn_filter)
        filter_group.setLayout(filter_layout)
        return filter_group

    def create_genetics_group(self):
        genetics_group = QGroupBox("遗传结构分析")
        genetics_layout = QFormLayout()
        # 主成分数量 (PCA)
        self.pca_components_spin = QDoubleSpinBox()
        self.pca_components_spin.setRange(2, 10)
        self.pca_components_spin.setValue(3)
        self.pca_components_spin.setSingleStep(1)
        genetics_layout.addRow("主成分数量 (PCA):", self.pca_components_spin)
        # 亲缘关系矩阵方法
        self.relationship_method = QComboBox()
        self.relationship_method.addItems(["IBS", "GRM"])
        genetics_layout.addRow("亲缘关系矩阵方法:", self.relationship_method)
        # SNP 过滤文件选择
        self.extract_file_edit = QLineEdit()
        self.extract_file_edit.setPlaceholderText("选择 SNP 过滤文件（可选）")
        self.extract_file_edit.setReadOnly(True)  # 禁止手动输入
        self.btn_extract_file = QPushButton("浏览...")
        self.btn_extract_file.clicked.connect(lambda: self.select_path(self.output_path, mode="file"))
        extract_file_layout = QHBoxLayout()
        extract_file_layout.addWidget(self.extract_file_edit)
        extract_file_layout.addWidget(self.btn_extract_file)
        genetics_layout.addRow("SNP 过滤文件:", extract_file_layout)
        # 执行遗传分析按钮
        self.btn_genetic_analysis = QPushButton("执行遗传分析")
        self.btn_genetic_analysis.setStyleSheet("background-color: #8BC34A; color: white;")
        genetics_layout.addWidget(self.btn_genetic_analysis)
        genetics_group.setLayout(genetics_layout)
        return genetics_group

    def create_file_selector(self, label_text):
        layout = QHBoxLayout()
        line_edit = QLineEdit()
        btn = QPushButton("选择文件")
        btn.clicked.connect(lambda: self.select_path(line_edit, mode="file"))
        layout.addWidget(line_edit)
        layout.addWidget(btn)
        return line_edit, layout

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

    def handle_file_path(self, file_path):
        try:
            if not os.path.isfile(file_path):
                raise FileNotFoundError("文件路径无效，请先选择或传递文件！")
            self.file_path.setText(file_path)
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    # 文件预览
    def preview_file(self):
        try:
            file_path = self.file_path.text()
            self.log_view.append(f'预览文件 {file_path}')
            if not file_path or not os.path.isfile(file_path):
                raise FileNotFoundError("文件路径无效，请先选择或传递文件！")
            dialog = FilePreviewDialog(file_path, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

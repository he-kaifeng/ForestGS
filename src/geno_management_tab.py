import os

from PyQt6.QtCore import QThread
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QDoubleSpinBox, QMessageBox, QGroupBox, QFormLayout, QComboBox, QGridLayout, QSizePolicy, QLabel
)

from common_tab import CommonTab, DraggableLineEdit
from geno_operations import GenoOperations


class GenoManagementTab(CommonTab):
    def __init__(self, plink_path):
        super().__init__()
        self.supported_formats = {
            "PLINK文本格式 (.ped)": "ped",
            "PLINK二进制格式 (.bed)": "bed",
            "VCF格式 (.vcf)": "vcf"
        }
        self.plink_path = plink_path
        self.init_ui()
        self.worker = GenoOperations()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        # 在线程启动后触发初始化
        self.thread.started.connect(lambda: self.worker.initialize(plink_path))
        self.connect_signals()
        self.thread.start()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        file_group = self.create_file_group()
        convert_qc_group = self.create_convert_qc_group()
        log_group = self.create_log_group()

        main_layout.addWidget(file_group)
        main_layout.addWidget(convert_qc_group)
        main_layout.addWidget(log_group, stretch=1)

        self.setLayout(main_layout)

    def connect_signals(self):
        # 连接业务逻辑的信号到UI的槽
        self.worker.progress_signal.connect(self.log_view.append)
        self.worker.error_signal.connect(lambda msg: QMessageBox.critical(self, "错误", msg))
        # 连接按钮点击事件到业务逻辑
        self.btn_convert.clicked.connect(self.run_convert_format)
        self.btn_run_qc.clicked.connect(self.run_quality_control)
        self.btn_filter.clicked.connect(self.run_filter_data)
        self.btn_genetic_analysis.clicked.connect(self.run_genetic_analysis)
        self.worker.operation_complete.connect(self.show_operation_dialog)

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
        # extract_file = self.extract_file_edit.text()
        self.worker.start_genetic_analysis.emit(input_file, output_dir, pca_components, relationship_method, None)
        # extract_file)

    def validate_input(self):
        if not self.file_path.text() or not os.path.isfile(self.file_path.text()):
            QMessageBox.warning(self, "错误", "请选择有效的输入文件！")
            return False
        if not self.output_path.text() or not os.path.isdir(self.output_path.text()):
            QMessageBox.warning(self, "错误", "请选择有效的输出目录！")
            return False
        return True

    def create_file_group(self):
        file_group = QGroupBox("文件选择")
        file_layout = QFormLayout()

        file_layout.setHorizontalSpacing(15)
        file_layout.setVerticalSpacing(10)

        # 基因型数据行
        file_path_layout = QHBoxLayout()
        self.file_path = DraggableLineEdit()
        self.file_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        btn_select_file = QPushButton("选择目标文件")
        btn_select_file.setIcon(QIcon("../icons/select.svg"))
        btn_select_file.clicked.connect(lambda: self.select_path(self.file_path, mode="file"))

        btn_preview = QPushButton("预览")
        btn_preview.setIcon(QIcon("../icons/see.svg"))
        btn_preview.clicked.connect(lambda: self.preview_file(self.file_path.text()))

        file_path_layout.addWidget(self.file_path, 3)
        file_path_layout.addSpacing(10)
        file_path_layout.addWidget(btn_select_file, 1)
        file_path_layout.addSpacing(10)
        file_path_layout.addWidget(btn_preview, 1)

        file_layout.addRow("基因型数据:", file_path_layout)

        # 输出路径行
        output_path_layout = QHBoxLayout()
        self.output_path = DraggableLineEdit()
        self.output_path.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        btn_output = QPushButton("选择输出路径")
        btn_output.setIcon(QIcon("../icons/result_dir.svg"))
        btn_output.clicked.connect(lambda: self.select_path(self.output_path, mode="directory"))

        output_path_layout.addWidget(self.output_path, 3)
        output_path_layout.addSpacing(10)
        output_path_layout.addWidget(btn_output, 2)
        output_path_layout.addSpacing(10)

        file_layout.addRow("结果输出目录:", output_path_layout)

        # 设置布局
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
        self.btn_convert.setIcon(QIcon("../icons/run.svg"))
        convert_layout.addWidget(self.btn_convert)
        convert_group.setLayout(convert_layout)
        return convert_group

    def create_qc_group(self):
        qc_group = QGroupBox("质量控制")
        qc_layout = QFormLayout()

        qc_layout.setHorizontalSpacing(20)
        qc_layout.setVerticalSpacing(10)

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

        self.btn_run_qc = QPushButton("执行质控")
        self.btn_run_qc.setIcon(QIcon("../icons/run.svg"))
        qc_layout.addWidget(self.btn_run_qc)

        qc_group.setLayout(qc_layout)
        return qc_group

    def create_filter_group(self):
        filter_group = QGroupBox("数据过滤")
        filter_layout = QFormLayout()

        filter_layout.setHorizontalSpacing(20)
        filter_layout.setVerticalSpacing(10)

        self.filter_sample_input, btn_filter_sample = self.create_file_selector()
        filter_layout.addRow("保留样本列表文件路径:", btn_filter_sample)

        self.exclude_sample_input, btn_exclude_sample = self.create_file_selector()
        filter_layout.addRow("排除样本列表文件路径:", btn_exclude_sample)

        self.filter_snp_input, btn_filter_snp = self.create_file_selector()
        filter_layout.addRow("保留SNP列表文件路径:", btn_filter_snp)

        self.exclude_snp_input, btn_exclude_sample = self.create_file_selector()
        filter_layout.addRow("排除SNP列表文件路径:", btn_exclude_sample)

        self.btn_filter = QPushButton("执行数据过滤")
        self.btn_filter.setIcon(QIcon("../icons/run.svg"))
        filter_layout.addWidget(self.btn_filter)
        filter_group.setLayout(filter_layout)
        return filter_group

    def create_genetics_group(self):
        genetics_group = QGroupBox("遗传结构分析")
        genetics_layout = QFormLayout()

        genetics_layout.setHorizontalSpacing(20)
        genetics_layout.setVerticalSpacing(10)

        # 主成分数量 (PCA)
        self.pca_components_spin = QDoubleSpinBox()
        self.pca_components_spin.setRange(2, 10)
        self.pca_components_spin.setValue(3)
        self.pca_components_spin.setSingleStep(1)
        genetics_layout.addRow("群体分层分析 (PCA):", self.pca_components_spin)
        # 亲缘关系矩阵方法
        self.relationship_method = QComboBox()
        self.relationship_method.addItems(["IBS", "GRM"])
        genetics_layout.addRow("亲缘关系检查:", self.relationship_method)
        # SNP 过滤文件选择
        # self.extract_file_edit = QLineEdit()
        # self.extract_file_edit.setPlaceholderText("选择 SNP 过滤文件（可选）")
        # self.extract_file_edit.setReadOnly(True)  # 禁止手动输入
        # self.btn_extract_file = QPushButton("浏览...")
        # self.btn_extract_file.clicked.connect(lambda: self.select_path(self.output_path, mode="file"))
        # extract_file_layout = QHBoxLayout()
        # extract_file_layout.addWidget(self.extract_file_edit)
        # extract_file_layout.addWidget(self.btn_extract_file)
        # genetics_layout.addRow("SNP 过滤文件:", extract_file_layout)
        # 执行遗传分析按钮
        self.btn_genetic_analysis = QPushButton("执行遗传分析")
        self.btn_genetic_analysis.setIcon(QIcon("../icons/run.svg"))
        genetics_layout.addWidget(self.btn_genetic_analysis)
        genetics_group.setLayout(genetics_layout)
        return genetics_group

    def create_file_selector(self):
        layout = QHBoxLayout()
        line_edit = DraggableLineEdit()
        btn = QPushButton("选择文件")
        btn.setIcon(QIcon("../icons/select.svg"))
        btn.clicked.connect(lambda: self.select_path(line_edit, mode="file"))
        layout.addWidget(line_edit)
        layout.addSpacing(5)
        layout.addWidget(btn)
        return line_edit, layout

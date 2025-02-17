import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QDoubleSpinBox, QCheckBox, QMessageBox, QGroupBox, QFormLayout, QComboBox, QFileDialog,
    QLabel, QGridLayout
)

from file_preview_dialog import FilePreviewDialog


class DataManagementTab(QWidget):
    def __init__(self, plink_path):
        super().__init__()
        # 初始化转换参数
        self.supported_formats = {
            "PLINK文本格式 (.ped)": "ped",
            "PLINK二进制格式 (.bed)": "bed",
            "VCF格式 (.vcf)": "vcf"
        }

        self.plink_path = plink_path
        self.temp_files = []  # 临时文件清理
        self.init_ui()

    def init_ui(self):
        # 主垂直布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)  # 设置边距
        main_layout.setSpacing(15)

        # --- 文件选择组 ---
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout()

        target_file_label = QLabel("目标文件")
        target_file_label.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(target_file_label)

        file_path_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        btn_preview = QPushButton("预览")
        btn_preview.clicked.connect(self.preview_file)
        file_path_layout.addWidget(self.file_path, stretch=4)
        file_path_layout.addWidget(btn_preview, stretch=1)
        file_layout.addLayout(file_path_layout)

        output_file_label = QLabel("输出文件目录")
        output_file_label.setStyleSheet("font-weight: bold;")
        file_layout.addWidget(output_file_label)

        output_path_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        btn_output = QPushButton("选择输出路径")
        btn_output.clicked.connect(lambda: self.select_path(self.output_path, mode="directory"))
        output_path_layout.addWidget(self.output_path, stretch=4)
        output_path_layout.addWidget(btn_output, stretch=1)
        file_layout.addLayout(output_path_layout)

        file_group.setLayout(file_layout)

        # --- 格式转换与质控 ---
        convert_qc_group = QGroupBox("格式转换与质量控制")
        convert_qc_layout = QGridLayout()

        # 格式转换
        convert_group = QGroupBox("文件格式转换")
        convert_layout = QFormLayout()
        self.target_format = QComboBox()
        self.target_format.addItems(["PLINK文本格式 (.ped)", "PLINK二进制格式 (.bed)", "VCF格式 (.vcf)"])
        convert_layout.addRow("转换为格式:", self.target_format)
        self.btn_convert = QPushButton("执行转换")
        self.btn_convert.setStyleSheet("background-color: #FF9800; color: white;")
        convert_layout.addRow(self.btn_convert)
        convert_group.setLayout(convert_layout)

        # 质量控制
        qc_group = QGroupBox("质量控制")
        qc_layout = QFormLayout()
        self.maf_spin = QDoubleSpinBox()
        self.maf_spin.setRange(0.0, 0.5)
        self.maf_spin.setValue(0.05)
        self.maf_spin.setSingleStep(0.01)
        self.maf_spin.setSuffix(" (范围: 0.0 - 0.5)")
        qc_layout.addRow("最小等位基因频率 (MAF):", self.maf_spin)

        self.missing_geno_spin = QDoubleSpinBox()
        self.missing_geno_spin.setRange(0.0, 1.0)
        self.missing_geno_spin.setValue(0.1)
        self.missing_geno_spin.setSingleStep(0.05)
        self.missing_geno_spin.setSuffix(" (范围: 0.0 - 1.0)")
        qc_layout.addRow("SNP最大缺失率:", self.missing_geno_spin)

        self.missing_sample_spin = QDoubleSpinBox()
        self.missing_sample_spin.setRange(0.0, 1.0)
        self.missing_sample_spin.setValue(0.1)
        self.missing_sample_spin.setSingleStep(0.05)
        self.missing_sample_spin.setSuffix(" (范围: 0.0 - 1.0)")
        qc_layout.addRow("样本最大缺失率:", self.missing_sample_spin)

        self.hwe_check = QCheckBox("启用哈迪-温伯格平衡检验 (p < 1e-6)")
        self.hwe_check.setChecked(True)
        qc_layout.addRow(self.hwe_check)

        self.btn_run_qc = QPushButton("开始质控")
        self.btn_run_qc.setStyleSheet("background-color: #4CAF50; color: white;")
        qc_layout.addWidget(self.btn_run_qc)

        qc_group.setLayout(qc_layout)

        # --- 数据过滤模块 ---
        filter_group = QGroupBox("数据过滤")
        filter_layout = QFormLayout()

        # 保留样本文件选择
        retain_sample_layout = QHBoxLayout()
        self.filter_sample_input = QLineEdit()
        btn_filter_sample = QPushButton("选择文件")
        btn_filter_sample.clicked.connect(lambda: self.select_path(self.filter_sample_input, mode="file"))
        retain_sample_layout.addWidget(self.filter_sample_input)
        retain_sample_layout.addWidget(btn_filter_sample)
        filter_layout.addRow("保留样本列表文件路径:", retain_sample_layout)

        # 排除样本文件选择
        exclude_sample_layout = QHBoxLayout()
        self.exclude_sample_input = QLineEdit()
        btn_exclude_sample = QPushButton("选择文件")
        btn_exclude_sample.clicked.connect(lambda: self.select_path(self.exclude_sample_input, mode="file"))
        exclude_sample_layout.addWidget(self.exclude_sample_input)
        exclude_sample_layout.addWidget(btn_exclude_sample)
        filter_layout.addRow("排除样本列表文件路径:", exclude_sample_layout)

        # 保留SNP文件选择
        retain_snp_layout = QHBoxLayout()
        self.filter_snp_input = QLineEdit()
        btn_filter_snp = QPushButton("选择文件")
        btn_filter_snp.clicked.connect(lambda: self.select_path(self.filter_snp_input, mode="file"))
        retain_snp_layout.addWidget(self.filter_snp_input)
        retain_snp_layout.addWidget(btn_filter_snp)
        filter_layout.addRow("保留SNP列表文件路径:", retain_snp_layout)

        # 排除SNP文件选择
        exclude_snp_layout = QHBoxLayout()
        self.exclude_snp_input = QLineEdit()
        btn_exclude_snp = QPushButton("选择文件")
        btn_exclude_snp.clicked.connect(lambda: self.select_path(self.exclude_snp_input, mode="file"))
        exclude_snp_layout.addWidget(self.exclude_snp_input)
        exclude_snp_layout.addWidget(btn_exclude_snp)
        filter_layout.addRow("排除SNP列表文件路径:", exclude_snp_layout)

        # 数据过滤执行按钮
        self.btn_filter = QPushButton("执行数据过滤")
        self.btn_filter.setStyleSheet("background-color: #FFC107; color: white;")
        filter_layout.addWidget(self.btn_filter)
        filter_group.setLayout(filter_layout)

        # 遗传结构分析
        genetics_group = QGroupBox("遗传结构分析")
        genetics_layout = QFormLayout()
        self.pca_components_spin = QDoubleSpinBox()
        self.pca_components_spin.setRange(1, 10)
        self.pca_components_spin.setValue(3)
        self.pca_components_spin.setSingleStep(1)
        genetics_layout.addRow("主成分数量 (PCA):", self.pca_components_spin)

        self.relationship_method = QComboBox()
        self.relationship_method.addItems(["IBS (身份状态)", "GRM (遗传关系矩阵)"])
        genetics_layout.addRow("亲缘关系矩阵方法:", self.relationship_method)

        self.btn_genetic_analysis = QPushButton("执行遗传分析")
        self.btn_genetic_analysis.setStyleSheet("background-color: #8BC34A; color: white;")
        genetics_layout.addWidget(self.btn_genetic_analysis)

        genetics_group.setLayout(genetics_layout)

        # 网格布局排列
        convert_qc_layout.addWidget(convert_group, 1, 0)  # 第一行第一列
        convert_qc_layout.addWidget(qc_group, 0, 0)  # 第一行第二列
        convert_qc_layout.addWidget(filter_group, 0, 1)  # 第二行第一列
        convert_qc_layout.addWidget(genetics_group, 1, 1)  # 第二行第二列

        # 设置所有列的拉伸因子为 1
        convert_qc_layout.setColumnStretch(0, 1)
        convert_qc_layout.setColumnStretch(1, 1)

        # 设置所有列的最小宽度（可选）
        convert_qc_layout.setColumnMinimumWidth(0, 300)
        convert_qc_layout.setColumnMinimumWidth(1, 300)

        convert_qc_group.setLayout(convert_qc_layout)

        # --- 日志输出 ---
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        log_group.setLayout(log_layout)

        # 主布局组合
        main_layout.addWidget(file_group)
        main_layout.addWidget(convert_qc_group)
        main_layout.addWidget(log_group, stretch=1)

        self.setLayout(main_layout)

    def select_path(self, line_edit, mode="file"):
        """
        通用路径选择方法
        :param line_edit: 需要填充路径的 QLineEdit 对象
        :param mode: 可选 "file" 或 "directory"，分别表示文件选择和目录选择
        """
        if mode == "file":
            path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        elif mode == "directory":
            path = QFileDialog.getExistingDirectory(self, "选择目录")
        else:
            raise ValueError("Invalid mode. Use 'file' or 'directory'.")

        if path:
            line_edit.setText(path)

    def handle_file_path(self, file_path):
        """处理传递过来的文件路径"""
        print(f"[DataManagementTab] 接收文件路径: {file_path}")
        self.file_path.setText(file_path)  # 更新文件路径到输入框

    def preview_file(self):
        """弹出文件预览窗口"""
        file_path = self.file_path.text()
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "错误", "文件路径无效，请先选择或传递文件！")
            return

        # 弹出文件预览对话框
        dialog = FilePreviewDialog(file_path, self)
        dialog.exec()

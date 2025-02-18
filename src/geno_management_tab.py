import os
import logging
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QDoubleSpinBox, QCheckBox, QMessageBox, QGroupBox, QFormLayout, QComboBox, QFileDialog,
    QLabel, QGridLayout
)
from file_preview_dialog import FilePreviewDialog

# 设置日志记录
logging.basicConfig(filename='app.log', level=logging.INFO)


class GenoManagementTab(QWidget):
    def __init__(self, plink_path):
        super().__init__()
        self.supported_formats = {
            "PLINK文本格式 (.ped)": "ped",
            "PLINK二进制格式 (.bed)": "bed",
            "VCF格式 (.vcf)": "vcf"
        }
        self.plink_path = plink_path
        self.temp_files = []
        self.init_ui()

    def init_ui(self):
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

    def create_file_group(self):
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout()

        target_file_label = QLabel("目标文件")
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

        output_file_label = QLabel("输出文件目录")
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
        self.btn_convert.clicked.connect(self.convert_format)
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
        self.maf_spin.setSuffix(" (范围: 0.0 - 0.5)")
        qc_layout.addRow("最小等位基因频率:", self.maf_spin)

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
            else:
                logging.warning("User canceled the file selection dialog.")
        except Exception as e:
            logging.error(f"Error in select_path: {e}")
            QMessageBox.critical(self, "错误", f"选择路径时发生错误: {str(e)}")

    def handle_file_path(self, file_path):
        try:
            logging.info(f"[DataManagementTab] 接收文件路径: {file_path}")
            if not os.path.isfile(file_path):
                raise FileNotFoundError("文件路径无效，请先选择或传递文件！")
            self.file_path.setText(file_path)
        except Exception as e:
            logging.error(f"Error in handle_file_path: {e}")
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
            logging.error(f"Error in preview_file: {e}")
            QMessageBox.critical(self, "错误", str(e))

    # 文件格式转换
    def convert_format(self):
        input_file = self.file_path.text()
        input_file = os.path.splitext(input_file)[0]
        output_file = self.output_path.text()
        output_file = os.path.join(output_file, f'{os.path.basename(input_file)}_result')

        # 获取目标格式
        selected_format = self.target_format.currentText()

        # 根据选择的格式生成plink命令
        command = [self.plink_path, "--file", input_file]

        if selected_format == "PLINK文本格式 (.ped)":
            command.extend(["--recode", "--out", output_file])
        elif selected_format == "PLINK二进制格式 (.bed)":
            command.extend(["--make-bed", "--out", output_file])
        elif selected_format == "VCF格式 (.vcf)":
            command.extend(["--recode", "vcf", "--out", output_file])
        else:
            self.log_view.append("未知的格式选择！")
            return

        # 在日志中输出开始信息
        self.log_view.append(f"开始转换文件：{input_file} 到 {selected_format} 格式...")
        self.log_view.append(f"执行命令：{' '.join(command)}")

        try:
            # 使用subprocess运行plink命令
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in iter(process.stdout.readline, ''):
                self.log_view.append(line.strip())  # 将plink的输出添加到日志中
            process.stdout.close()
            process.wait()

            if process.returncode == 0:
                self.log_view.append(f"文件转换成功！输出文件：{output_file}")
            else:
                self.log_view.append(f"文件转换失败！请检查输入文件和参数配置。")
                for line in iter(process.stderr.readline, ''):
                    self.log_view.append(line.strip())

        except Exception as e:
            self.log_view.append(f"发生错误：{str(e)}")

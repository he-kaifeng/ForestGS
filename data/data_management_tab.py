import os
import subprocess

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QDoubleSpinBox, QCheckBox, QMessageBox, QGroupBox, QFormLayout, QComboBox, QFileDialog
)

from file_preview_dialog import FilePreviewDialog
from plink_thread import PlinkThread
from file_conversion_thread import FileConversionThread


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
        main_layout.setSpacing(15)  # 组件间距

        # --- 文件选择组 ---
        file_group = QGroupBox("文件选择")
        file_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        # self.file_path.setReadOnly(True)  # 设置为只读，避免用户直接编辑
        btn_preview = QPushButton("预览")
        btn_preview.clicked.connect(self.preview_file)  # 点击按钮弹出预览窗口
        file_layout.addWidget(self.file_path, stretch=4)  # 输入框占80%宽度
        file_layout.addWidget(btn_preview, stretch=1)  # 按钮占20%
        file_group.setLayout(file_layout)

        # --- 格式转换组 ---
        convert_group = QGroupBox("文件格式转换")
        convert_layout = QFormLayout()

        # 目标格式选择
        self.target_format = QComboBox()
        self.target_format.addItems(self.supported_formats.keys())
        convert_layout.addRow("转换为格式:", self.target_format)

        # 输出路径选择
        self.output_path = QLineEdit()
        btn_output = QPushButton("选择输出路径")
        btn_output.clicked.connect(self.select_output_path)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.output_path, 4)
        path_layout.addWidget(btn_output, 1)
        convert_layout.addRow("输出路径:", path_layout)

        # 转换按钮
        self.btn_convert = QPushButton("执行转换")
        self.btn_convert.setStyleSheet("background-color: #FF9800; color: white;")
        self.btn_convert.clicked.connect(self.convert_file)
        convert_layout.addRow(self.btn_convert)

        convert_group.setLayout(convert_layout)

        # --- 质控参数组 ---
        params_group = QGroupBox("质量控制")
        params_layout = QFormLayout()  # 表单布局对齐标签和输入
        # MAF参数
        self.maf_spin = QDoubleSpinBox()
        self.maf_spin.setRange(0.0, 0.5)
        self.maf_spin.setValue(0.05)
        self.maf_spin.setSingleStep(0.01)
        self.maf_spin.setSuffix(" (范围: 0.0 - 0.5)")
        params_layout.addRow("最小等位基因频率 (MAF):", self.maf_spin)
        # SNP 缺失率参数
        self.missing_geno = QDoubleSpinBox()
        self.missing_geno.setRange(0.0, 1.0)
        self.missing_geno.setValue(0.1)
        self.missing_geno.setSingleStep(0.05)
        self.missing_geno.setSuffix(" (范围: 0.0 - 1.0)")
        params_layout.addRow("SNP最大缺失率:", self.missing_geno)
        # SNP 缺失率参数
        self.missing = QDoubleSpinBox()
        self.missing.setRange(0.0, 1.0)
        self.missing.setValue(0.1)
        self.missing.setSingleStep(0.05)
        self.missing.setSuffix(" (范围: 0.0 - 1.0)")
        params_layout.addRow("样本最大缺失率:", self.missing)
        # HWE检验
        self.hwe_check = QCheckBox("启用哈迪-温伯格平衡检验 (p < 1e-6)")
        self.hwe_check.setChecked(True)
        params_layout.addRow(self.hwe_check)
        params_group.setLayout(params_layout)

        # --- 执行控制组 ---
        control_group = QWidget()
        control_layout = QHBoxLayout()
        self.btn_run = QPushButton("开始质控")
        self.btn_run.setStyleSheet("background-color: #4CAF50; color: white;")  # 绿色按钮
        self.btn_run.clicked.connect(self.run_plink)
        self.btn_help = QPushButton("帮助")
        self.btn_help.setStyleSheet("background-color: #2196F3; color: white;")  # 蓝色按钮
        control_layout.addWidget(self.btn_help)
        control_layout.addStretch(1)  # 添加弹性空间
        control_layout.addWidget(self.btn_run)
        control_group.setLayout(control_layout)

        # --- 日志输出组 ---
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("font-family: Consolas; font-size: 10pt;")  # 等宽字体
        log_layout.addWidget(self.log_view)
        log_group.setLayout(log_layout)

        # 将所有组添加到主布局
        main_layout.addWidget(file_group)
        main_layout.addWidget(convert_group)
        main_layout.addWidget(params_group)
        main_layout.addWidget(control_group)
        main_layout.addWidget(log_group, stretch=1)  # 日志区域可拉伸

        self.setLayout(main_layout)

    def select_output_path(self):
        """选择输出目录"""
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_path.setText(path)

    def convert_file(self):
        """执行文件格式转换"""
        input_path = self.file_path.text()
        output_dir = self.output_path.text()
        target_format = self.supported_formats[self.target_format.currentText()]

        if not input_path or not os.path.exists(input_path):
            QMessageBox.critical(self, "错误", "请输入有效的输入文件路径！")
            return
        if not output_dir:
            QMessageBox.critical(self, "错误", "请选择输出目录！")
            return

        # 生成输出文件名
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_prefix = os.path.join(output_dir, base_name)

        # 根据输入格式和输出格式构建转换命令
        conversion_commands = self.build_conversion_commands(input_path, output_prefix, target_format)

        if not conversion_commands:
            QMessageBox.critical(self, "错误", "不支持此格式的转换！")
            return

        # 启动转换线程
        self.thread = FileConversionThread(
            self.plink_path,
            conversion_commands,
            output_prefix,
            target_format
        )
        self.thread.log_signal.connect(self.log_view.append)
        self.thread.finished_signal.connect(self.on_conversion_finished)
        self.thread.start()
        self.btn_convert.setEnabled(False)

    def build_conversion_commands(self, input_path, output_prefix, target_format):
        """构建不同格式的转换命令链"""
        commands = []
        input_ext = os.path.splitext(input_path)[1].lower()

        # 定义支持转换的格式矩阵
        conversion_matrix = {
            ("vcf", "ped"): [
                ["--vcf", input_path, "--recode", "--out", output_prefix]
            ],
            ("vcf", "bed"): [
                ["--vcf", input_path, "--make-bed", "--out", output_prefix]
            ],
            ("ped", "vcf"): [
                ["--file", output_prefix, "--recode", "vcf", "--out", output_prefix]
            ],
            ("ped", "bed"): [
                ["--file", output_prefix, "--make-bed", "--out", output_prefix]
            ],
            ("bed", "vcf"): [
                ["--bfile", output_prefix, "--recode", "vcf", "--out", output_prefix]
            ],
            ("bed", "ped"): [
                ["--bfile", output_prefix, "--recode", "--out", output_prefix]
            ]
        }

        # 获取输入格式类型
        input_type = None
        if input_ext == ".vcf":
            input_type = "vcf"
        elif input_ext == ".ped":
            input_type = "ped"
        elif input_ext == ".bed":
            input_type = "bed"

        if input_type and (input_type, target_format) in conversion_matrix:
            return conversion_matrix[(input_type, target_format)]

        # 处理hapmap的特殊转换
        if input_ext == ".hmp.txt" and target_format in ["ped", "bed"]:
            return self.handle_hapmap_conversion(input_path, output_prefix, target_format)

        return None

    def handle_hapmap_conversion(self, input_path, output_prefix, target_format):
        """处理hapmap到plink格式的转换"""
        # 生成中间ped/map文件
        ped_path = output_prefix + ".ped"
        map_path = output_prefix + ".map"

        try:
            # 读取hapmap文件并转换
            df = pd.read_csv(input_path, sep="\t")
            # ...（添加具体的hapmap转换逻辑）...
            # 返回转换命令链
            return [
                ["--file", output_prefix, "--make-bed", "--out", output_prefix]
                if target_format == "bed"
                else []
            ]
        except Exception as e:
            self.log_view.append(f"Hapmap转换错误: {str(e)}")
            return None

    def on_conversion_finished(self, success):
        """转换完成处理"""
        self.btn_convert.setEnabled(True)
        if success:
            self.log_view.append("文件转换完成！")
            # 自动更新文件路径到新生成的格式
            new_path = self.thread.output_files[0]
            self.file_path.setText(new_path)
        else:
            self.log_view.append("文件转换失败！")

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

    def run_plink(self):
        input_path = self.file_path.text()
        if not input_path:
            QMessageBox.warning(self, "错误", "请先选择文件！")
            return

        # 创建输出目录
        output_dir = os.path.join(os.path.dirname(input_path), "result")
        os.makedirs(output_dir, exist_ok=True)
        output_prefix = os.path.join(output_dir, "data_qc")

        # 根据文件类型预处理
        if input_path.endswith(".vcf"):
            self.process_vcf(input_path, output_prefix)
        elif input_path.endswith(".hmp.txt.csv"):
            self.process_hapmap(input_path, output_prefix)
        elif input_path.endswith(".ped"):
            self.process_plink_text(input_path, output_prefix)
        elif input_path.endswith(".bed"):
            self.process_plink_binary(input_path, output_prefix)
        else:
            QMessageBox.critical(self, "错误", "不支持的格式！请输入正确的格式")

    def process_vcf(self, vcf_path, output_prefix):
        """ 转换VCF为Plink二进制并质控 """
        plink_cmd = [
            self.plink_path,
            "--vcf", vcf_path,
            "--allow-extra-chr",
            "--make-bed",
            "--out", output_prefix + "_temp"
        ]
        self.run_command(plink_cmd, output_prefix)

    def process_hapmap(self, hmp_path, output_prefix):
        """ 转换Hapmap为Plink二进制并质控 """
        try:
            # 读取Hapmap文件
            df = pd.read_csv(hmp_path, sep="\t", header=0)
            samples = df.columns[11:]  # 假设前11列为元数据
            ped_data = []

            # 转换为Plink .ped格式
            for _, row in df.iterrows():
                snp_id = row["rs#"]
                chrom = row["chrom"]
                pos = row["pos"]
                alleles = row["alleles"].split("/")
                genotypes = row[samples].replace(alleles[0], "A").replace(alleles[1], "B")
                ped_line = ["0", "0", "0", "0", "0", "0"] + genotypes.tolist()
                ped_data.append(ped_line)

            # 保存临时文件
            ped_path = output_prefix + "_temp.ped"
            pd.DataFrame(ped_data).to_csv(ped_path, sep=" ", index=False, header=False)
            self.temp_files.append(ped_path)

            # 生成.map文件
            map_data = df[["chrom", "rs#", "pos"]].rename(columns={"rs#": "snp_id"})
            map_path = output_prefix + "_temp.map"
            map_data.to_csv(map_path, sep="\t", index=False, header=False)
            self.temp_files.append(map_path)

            # 转换为二进制格式
            plink_cmd = [
                self.plink_path,
                "--file", output_prefix + "_temp",
                "--make-bed",
                "--out", output_prefix + "_temp_binary"
            ]
            self.run_command(plink_cmd, output_prefix)

        except Exception as e:
            self.log_view.append(f"Hapmap转换错误: {str(e)}")

    def process_plink_text(self, ped_path, output_prefix):
        """ 处理Plink文本格式（.ped/.map） """
        map_path = ped_path.replace(".ped", ".map")
        if not os.path.exists(map_path):
            QMessageBox.critical(self, "错误", "缺少.map文件！")
            return
        plink_cmd = [
            self.plink_path,
            "--file", os.path.splitext(ped_path)[0],
            "--make-bed",
            "--out", output_prefix + "_temp"
        ]
        self.run_command(plink_cmd, output_prefix)

    def process_plink_binary(self, bed_path, output_prefix):
        """ 直接处理Plink二进制格式 """
        bim_path = bed_path.replace(".bed", ".bim")
        fam_path = bed_path.replace(".bed", ".fam")
        if not os.path.exists(bim_path) or not os.path.exists(fam_path):
            QMessageBox.critical(self, "错误", "缺少.bim或.fam文件！")
            return
        # 直接质控
        self.start_plink_qc(os.path.splitext(bed_path)[0], output_prefix)

    def run_command(self, cmd, output_prefix):
        """ 通用PLINK命令执行 """
        try:
            self.log_view.append("转换文件格式中...")
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            self.log_view.append(process.stdout)
            if process.returncode == 0:
                self.start_plink_qc(cmd[-1], output_prefix)
            else:
                self.log_view.append("格式转换失败！")
        except Exception as e:
            self.log_view.append(f"命令执行错误: {str(e)}")

    def start_plink_qc(self, input_prefix, output_prefix):
        """ 启动质控线程 """
        maf = self.maf_spin.value()
        geno = self.missing_geno.value()
        missing = self.missing.value()
        self.thread = PlinkThread(
            self.plink_path,
            input_prefix,
            output_prefix,
            maf,
            geno,
            missing,
            self.hwe_check.isChecked()
        )
        self.thread.log_signal.connect(self.log_view.append)
        self.thread.finished_signal.connect(lambda success: self.on_plink_finished(success, output_prefix))
        self.thread.start()
        self.btn_run.setEnabled(False)

    def on_plink_finished(self, success, output_prefix):
        self.btn_run.setEnabled(True)
        if success:
            self.log_view.append("质控完成！输出文件：")
            self.log_view.append(f"- {output_prefix}.bed")
            self.log_view.append(f"- {output_prefix}.bim")
            self.log_view.append(f"- {output_prefix}.fam")
            # 清理临时文件
            for f in self.temp_files:
                if os.path.exists(f):
                    os.remove(f)
        else:
            self.log_view.append("质控失败，请检查日志！")

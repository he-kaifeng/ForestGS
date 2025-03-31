import os
import pandas as pd
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QGroupBox, QFormLayout, QFileDialog,
    QLabel, QCheckBox, QSpinBox, QMessageBox, QComboBox
)
from file_preview_dialog import FilePreviewDialog
from gwas_operations import GWASOperations


class GWASTab(QWidget):
    def __init__(self, plink_path):
        super().__init__()
        self.plink_path = plink_path
        self.init_ui()
        self.init_worker()

    def init_ui(self):
        """初始化用户界面"""
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

        # 结果文件路径选择组
        result_file_path_group = self.create_result_file_path_group()
        main_layout.addWidget(result_file_path_group)

        # GWAS参数设置组
        gwas_param_group = self.create_gwas_param_group()
        main_layout.addWidget(gwas_param_group)

        # 日志输出组
        log_group = self.create_log_group()
        main_layout.addWidget(log_group, stretch=1)

        self.setLayout(main_layout)

    def init_worker(self):
        """初始化业务逻辑对象和线程"""
        self.worker = GWASOperations(self.plink_path)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.connect_signals()
        self.thread.start()

    def connect_signals(self):
        """连接信号与槽"""
        self.worker.progress_signal.connect(self.log_view.append)
        self.worker.error_signal.connect(lambda msg: QMessageBox.critical(self, "错误", msg))
        self.worker.result_signal.connect(self.handle_result)
        self.btn_run_gwas.clicked.connect(self.run_gwas)

    def run_gwas(self):
        """执行 GWAS 分析"""
        if not self.validate_input():
            return

        gwas_args = {
            "pheno_file": self.pheno_file_edit.text().strip(),
            "geno_file": self.geno_file_edit.text().strip(),
            "kinship_file": self.kinship_file_edit.text().strip() if self.kinship_file_edit.text().strip() else None,
            "covar_file": self.covar_file_edit.text().strip() if self.covar_file_edit.text().strip() else None,
            "core_sample_file": self.core_sample_edit.text().strip() if self.core_sample_edit.text().strip() else None,
            "result_dir": self.result_file_path_edit.text().strip(),
            "pheno_trait": self.trait_combo.currentText(),
            "random_marker": self.random_marker_check.isChecked(),
            "marker_num": self.marker_num_spin.value(),
            "logp_marker": self.logp_marker_check.isChecked(),
        }

        self.log_view.clear()
        self.log_view.append("开始 GWAS 分析...")
        self.worker.start_gwas.emit(gwas_args)

    def handle_result(self, result):
        """处理业务逻辑返回的结果"""
        self.log_view.append("数据处理完成，结果已更新")

    def validate_input(self):
        """验证输入是否有效"""
        if not self.pheno_file_edit.text().strip() or not self.geno_file_edit.text().strip():
            QMessageBox.critical(self, "错误", "表型数据和基因型数据文件必须选择！")
            return False
        if not self.result_file_path_edit.text().strip():
            QMessageBox.critical(self, "错误", "请选择结果文件保存路径！")
            return False
        return True

    def create_file_group(self):
        """创建文件选择组"""
        file_group = QGroupBox("输入文件选择")
        file_layout = QFormLayout()

        # 实例变量初始化
        self.pheno_file_edit = QLineEdit()
        self.geno_file_edit = QLineEdit()
        self.kinship_file_edit = QLineEdit()
        self.covar_file_edit = QLineEdit()
        self.core_sample_edit = QLineEdit()

        # 为每个文件选择创建布局
        def add_file_selector(label_text, line_edit):
            file_path_layout = QHBoxLayout()

            btn_select_file = QPushButton("选择文件")
            btn_select_file.clicked.connect(lambda: self.load_traits(label_text, line_edit))

            btn_preview = QPushButton("预览")
            btn_preview.clicked.connect(lambda: self.preview_file(line_edit.text()))

            file_path_layout.addWidget(line_edit, stretch=3)
            file_path_layout.addWidget(btn_select_file, stretch=1)
            file_path_layout.addWidget(btn_preview, stretch=1)

            file_layout.addRow(QLabel(label_text), file_path_layout)

        # 添加不同的文件选择器
        add_file_selector("表型数据文件:", self.pheno_file_edit)
        add_file_selector("基因型数据文件:", self.geno_file_edit)
        add_file_selector("亲缘关系矩阵文件 (可选):", self.kinship_file_edit)
        add_file_selector("协方差矩阵文件 (可选):", self.covar_file_edit)
        add_file_selector("核心样本ID文件 (可选):", self.core_sample_edit)

        file_group.setLayout(file_layout)
        return file_group

    def load_traits(self, label_text, line_edit):
        self.select_path(line_edit, mode="file")
        file_path = line_edit.text()
        if label_text == '表型数据文件:':
            try:
                # 文件格式自动识别
                if file_path.endswith('.txt'):
                    self.phenotype_data = pd.read_csv(file_path, sep='\t')
                else:
                    raise ValueError("仅支持制表符分隔的txt文件")
                self.columns = self.phenotype_data.columns.tolist()
                if self.columns[0] == 'FID' and self.columns[1] == 'IID':
                    self.trait_combo.clear()
                    self.trait_combo.addItems(self.columns[2:])
                else:
                    line_edit.clear()
                    QMessageBox.critical(self, "数据加载错误",
                                         f"无法加载表型数据：\n"
                                         f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")
            except Exception as e:
                line_edit.clear()
                QMessageBox.critical(self, "数据加载错误",
                                     f"无法加载表型数据：\n{str(e)}\n"
                                     f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")
                self.log_view.setText("数据加载错误"
                                      f"无法加载表型数据：\n{str(e)}\n"
                                      f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")

    def create_gwas_param_group(self):
        """创建 GWAS 参数设置组"""
        gwas_param_group = QGroupBox("GWAS参数设置")
        gwas_param_layout = QFormLayout()

        # 性状选择组件
        self.trait_combo = QComboBox()
        self.trait_combo.setPlaceholderText("请选择性状")
        gwas_param_layout.addRow("选择性状:", self.trait_combo)

        # 随机标记
        self.random_marker_check = QCheckBox("使用随机标记")
        self.random_marker_check.setChecked(True)
        gwas_param_layout.addWidget(self.random_marker_check)

        # 标记数量
        self.marker_num_spin = QSpinBox()
        self.marker_num_spin.setRange(1000, 1000000)
        self.marker_num_spin.setValue(10000)
        self.marker_num_spin.setSingleStep(1000)
        gwas_param_layout.addRow("标记数量:", self.marker_num_spin)

        # 使用-logp排序后的显著性标记
        self.logp_marker_check = QCheckBox("使用-logp排序后的显著性标记")
        gwas_param_layout.addWidget(self.logp_marker_check)

        # 开始分析按钮
        self.btn_run_gwas = QPushButton("开始全基因组关联分析")
        self.btn_run_gwas.setStyleSheet("background-color: #2196F3; color: white;")
        gwas_param_layout.addWidget(self.btn_run_gwas)

        gwas_param_group.setLayout(gwas_param_layout)
        return gwas_param_group

    def create_log_group(self):
        """创建日志输出组"""
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        log_group.setLayout(log_layout)
        return log_group

    def create_result_file_path_group(self):
        """创建结果文件路径选择组"""
        result_file_path_group = QGroupBox("结果文件路径选择")
        result_file_path_layout = QHBoxLayout()

        self.result_file_path_edit = QLineEdit()
        self.result_file_path_edit.setPlaceholderText("选择结果文件保存路径")

        btn_select_result_path = QPushButton("选择输出路径")
        btn_select_result_path.clicked.connect(lambda: self.select_path(self.result_file_path_edit, mode="directory"))

        result_file_path_layout.addWidget(self.result_file_path_edit)
        result_file_path_layout.addWidget(btn_select_result_path)

        result_file_path_group.setLayout(result_file_path_layout)
        return result_file_path_group

    def select_path(self, line_edit, mode="file"):
        """选择文件或目录路径"""
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
        """预览文件"""
        try:
            self.log_view.append(f'预览文件 {file_path}')
            if not file_path or not os.path.isfile(file_path):
                raise FileNotFoundError("文件路径无效，请先选择或传递文件！")
            dialog = FilePreviewDialog(file_path, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def load_traits(self, label_text, line_edit):
        self.select_path(line_edit, mode="file")
        file_path = line_edit.text()
        if file_path is None or file_path == '':
            return
        if label_text == '表型数据文件:':
            try:
                # 文件格式自动识别
                if file_path.endswith('.txt'):
                    self.phenotype_data = pd.read_csv(file_path, sep='\t')
                elif file_path.endswith('.csv'):
                    self.phenotype_data = pd.read_csv(file_path)
                else:
                    raise ValueError("仅支持制表符分隔的txt文件或csv文件")
                self.columns = self.phenotype_data.columns.tolist()
                if self.columns[0] == 'FID' and self.columns[1] == 'IID':
                    self.trait_combo.clear()
                    self.trait_combo.addItems(self.columns[2:])
                else:
                    line_edit.clear()
                    QMessageBox.critical(self, "数据加载错误",
                                         f"无法加载表型数据：\n"
                                         f"请确保：\n1. 文件格式正确\n仅支持制表符分隔的txt文件或csv文件\n2. 包含表头行\n")
            except Exception as e:
                line_edit.clear()
                QMessageBox.critical(self, "数据加载错误",
                                     f"无法加载表型数据：\n{str(e)}\n"
                                     f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")
                self.log_view.setText("数据加载错误"
                                      f"无法加载表型数据：\n{str(e)}\n"
                                      f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")

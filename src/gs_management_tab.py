import os
import pandas as pd
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLineEdit, QGroupBox, QFormLayout, QFileDialog,
    QLabel, QCheckBox, QSpinBox, QMessageBox, QComboBox, QRadioButton, QGridLayout
)
from file_preview_dialog import FilePreviewDialog
from gs_operations import GSOperations


class GSTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.worker = GSOperations()  # 业务逻辑对象
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
        self.btn_run_gs.clicked.connect(self.run_gs)

    def run_gs(self):
        # 检查必要文件是否已选择
        if not self.pheno_file_edit.text().strip() or not self.geno_file_edit.text().strip():
            QMessageBox.critical(self, "错误", "表型数据和基因型数据文件必须选择！")
            return
        # 检查结果文件路径是否已选择
        if not self.result_file_path_edit.text().strip():
            QMessageBox.critical(self, "错误", "请选择结果文件保存路径！")
            return
        # 检查性状是否已选择
        if not self.trait_combo.currentText():
            QMessageBox.critical(self, "错误", "请选择性状！")
            return
        # 获取用户输入的文件路径和参数
        gs_args = {
            "pheno_file": self.pheno_file_edit.text().strip(),
            "geno_file": self.geno_file_edit.text().strip(),
            "train_file": self.train_model_file_edit.text().strip(),
            "core_sample_file": self.core_sample_edit.text().strip() if self.core_sample_edit.text().strip() else None,
            "result_dir": self.result_file_path_edit.text().strip(),
            "trait": self.trait_combo.currentText(),
            "models": next(
                (model for model, radio_button in self.model_radio_buttons.items() if radio_button.isChecked()), None),
            "threads": self.threads_spin.value(),
            "use_gpu": self.gpu_check.isChecked(),
            "optimization": self.optimization_combo.currentText(),
        }
        # 清空日志
        self.log_view.clear()
        # 调用业务逻辑执行 GS 分析
        self.log_view.append("开始 GS 分析...")
        self.worker.start_gs.emit(gs_args)  # 触发信号

    def handle_result(self, result):
        """处理业务逻辑返回的结果"""
        self.log_view.append("数据处理完成，结果已更新")

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
            QRadioButton {
                font-size: 12px;
            }
            QCheckBox {
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
        # GS参数设置组
        gs_param_group = self.create_gs_param_group()
        main_layout.addWidget(gs_param_group)
        # 日志输出组
        log_group = self.create_log_group()
        main_layout.addWidget(log_group, stretch=1)
        self.setLayout(main_layout)

    def create_file_group(self):
        file_group = QGroupBox("输入文件选择")
        file_layout = QFormLayout()
        # 实例变量初始化
        self.pheno_file_edit = QLineEdit()
        self.geno_file_edit = QLineEdit()
        self.core_sample_edit = QLineEdit()
        self.train_model_file_edit = QLineEdit()

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
        add_file_selector("训练表型数据文件:", self.pheno_file_edit)
        add_file_selector("训练基因型数据文件:", self.geno_file_edit)
        add_file_selector("核心样本ID文件 (可选):", self.core_sample_edit)
        add_file_selector("预测基因型文件:", self.train_model_file_edit)
        file_group.setLayout(file_layout)
        return file_group

    def create_gs_param_group(self):

        gs_param_group = QGroupBox("GS 参数设置")

        gs_param_layout = QVBoxLayout()

        trait_layout = QHBoxLayout()
        trait_label = QLabel("选择性状:")
        self.trait_combo = QComboBox()
        self.trait_combo.setPlaceholderText("请选择性状")
        trait_layout.addWidget(trait_label)
        trait_layout.addWidget(self.trait_combo)
        gs_param_layout.addLayout(trait_layout)

        model_group = QGroupBox("选择模型")
        model_layout = QGridLayout()
        self.model_radio_buttons = {
            "GBLUP": QRadioButton("GBLUP"),
            "rrBLUP": QRadioButton("rrBLUP(Ridge)"),
            "BayesA": QRadioButton("BayesA"),
            "SVR": QRadioButton("SVR"),
            "RF": QRadioButton("RF"),
            "LASSO": QRadioButton("LASSO"),
            "CatBoost": QRadioButton("CatBoost"),
            "XGBoost": QRadioButton("XGBoost"),
            "LightGBM": QRadioButton("LightGBM"),
        }

        row, col = 0, 0
        for radio_button in self.model_radio_buttons.values():
            model_layout.addWidget(radio_button, row, col)
            col += 1
            if col > 1:  # 每行两列
                col = 0
                row += 1
        model_group.setLayout(model_layout)
        gs_param_layout.addWidget(model_group)
        # 线程数
        threads_layout = QHBoxLayout()
        threads_label = QLabel("线程数:")
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 16)
        self.threads_spin.setValue(4)
        threads_layout.addWidget(threads_label)
        threads_layout.addWidget(self.threads_spin)
        gs_param_layout.addLayout(threads_layout)

        self.gpu_check = QCheckBox("使用 GPU 加速")
        gs_param_layout.addWidget(self.gpu_check)

        optimization_layout = QHBoxLayout()
        optimization_label = QLabel("优化算法:")
        self.optimization_combo = QComboBox()
        self.optimization_combo.addItems(["网格搜索", "随机搜索", "贝叶斯优化"])
        optimization_layout.addWidget(optimization_label)
        optimization_layout.addWidget(self.optimization_combo)
        gs_param_layout.addLayout(optimization_layout)

        self.btn_run_gs = QPushButton("执行基因型选择")
        self.btn_run_gs.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-size: 14px; border-radius: 5px; }"
            "QPushButton:hover { background-color: #45a049; }"
        )
        gs_param_layout.addWidget(self.btn_run_gs)
        # 设置主布局
        gs_param_group.setLayout(gs_param_layout)
        return gs_param_group

    def create_log_group(self):
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view)
        log_group.setLayout(log_layout)
        return log_group

    def create_result_file_path_group(self):
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

    # 文件预览
    def preview_file(self, file_path):
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
                                         f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")
            except Exception as e:
                line_edit.clear()
                QMessageBox.critical(self, "数据加载错误",
                                     f"无法加载表型数据：\n{str(e)}\n"
                                     f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")
                self.log_view.setText("数据加载错误"
                                      f"无法加载表型数据：\n{str(e)}\n"
                                      f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")

import pandas as pd
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QGroupBox, QFormLayout, QLabel, QCheckBox, QSpinBox, QMessageBox, QComboBox, QRadioButton, QGridLayout
)

from common_tab import CommonTab, DraggableLineEdit
from gs_operations import GSOperations


class GSTab(CommonTab):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.btn_run_gs.clicked.connect(self.run_gs)

    def run_gs(self):
        if not self.pheno_file_edit.text().strip() or not self.geno_file_edit.text().strip():
            QMessageBox.critical(self, "错误", "表型数据和基因型数据文件必须选择！")
            return
        if not self.result_file_path_edit.text().strip():
            QMessageBox.critical(self, "错误", "请选择结果文件保存路径！")
            return
        if not self.trait_combo.currentText():
            QMessageBox.critical(self, "错误", "请选择性状！")
            return
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
        self.log_view.append("开始 GS 分析...")
        self.worker = GSOperations(gs_args)
        self.worker.progress_signal.connect(self.upload_message)
        self.worker.error_signal.connect(lambda msg: QMessageBox.critical(self, "错误", msg))
        self.worker.start()

    def upload_message(self, message):
        self.log_view.append(message)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        file_group = self.create_file_group()
        main_layout.addWidget(file_group)

        result_file_path_group = self.create_result_file_path_group()
        main_layout.addWidget(result_file_path_group)

        gs_param_group = self.create_gs_param_group()
        main_layout.addWidget(gs_param_group)

        log_group = self.create_log_group()
        main_layout.addWidget(log_group, stretch=1)
        self.setLayout(main_layout)

    def create_file_group(self):
        file_group = QGroupBox("输入文件选择")
        file_layout = QFormLayout()

        self.pheno_file_edit = DraggableLineEdit()
        self.geno_file_edit = DraggableLineEdit()
        self.core_sample_edit = DraggableLineEdit()
        self.train_model_file_edit = DraggableLineEdit()

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

        add_file_selector("训练表型数据文件:", self.pheno_file_edit)
        add_file_selector("训练基因型数据文件:", self.geno_file_edit)
        # add_file_selector("核心样本ID文件 (可选):", self.core_sample_edit)
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
            "GBDT": QRadioButton("GBDT"),
            "ElasticNet": QRadioButton("ElasticNet")
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
        gs_param_layout.addWidget(self.btn_run_gs)

        gs_param_group.setLayout(gs_param_layout)
        return gs_param_group

    def create_result_file_path_group(self):
        result_file_path_group = QGroupBox("结果文件路径选择")
        result_file_path_layout = QHBoxLayout()
        self.result_file_path_edit = DraggableLineEdit()
        self.result_file_path_edit.setPlaceholderText("选择结果文件保存路径")
        btn_select_result_path = QPushButton("选择输出路径")
        btn_select_result_path.clicked.connect(lambda: self.select_path(self.result_file_path_edit, mode="directory"))
        result_file_path_layout.addWidget(self.result_file_path_edit)
        result_file_path_layout.addWidget(btn_select_result_path)
        result_file_path_group.setLayout(result_file_path_layout)
        return result_file_path_group

    def load_traits(self, label_text, line_edit):
        self.select_path(line_edit, mode="file")
        file_path = line_edit.text()
        if file_path is None or file_path == '':
            return
        if label_text == '训练表型数据文件:':
            try:
                if file_path.endswith('.txt'):
                    self.phenotype_data = pd.read_csv(file_path, sep='\t')
                elif file_path.endswith('.csv'):
                    self.phenotype_data = pd.read_csv(file_path)
                else:
                    raise ValueError("仅支持制表符分隔的txt文件或csv文件")
                self.columns = self.phenotype_data.columns.tolist()
                self.trait_combo.clear()
                self.trait_combo.addItems(self.columns[1:])
            except Exception as e:
                line_edit.clear()
                QMessageBox.critical(self, "数据加载错误",
                                     f"无法加载表型数据：\n{str(e)}\n"
                                     f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")
                self.log_view.setText("数据加载错误"
                                      f"无法加载表型数据：\n{str(e)}\n"
                                      f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")

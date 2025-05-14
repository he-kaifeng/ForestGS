import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit, QPushButton, QGridLayout, QRadioButton, QLabel, QComboBox, QSpinBox, QCheckBox, \
    QMessageBox
from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QHBoxLayout

from common_tab import CommonTab
from gs import parse_json_from_file
from gs_operations import GSOperations


class GSWithDataTab(CommonTab):
    def __init__(self, config_file):
        super().__init__()
        self.config = parse_json_from_file(config_file)
        self.trait_combo = QComboBox()
        self.init_ui()
        self.btn_run_gs.clicked.connect(self.run_gs)

    def run_gs(self):
        if not self.result_file_path_edit.text().strip():
            QMessageBox.critical(self, "错误", "请选择结果文件保存路径！")
            return
        if not self.trait_combo.currentText():
            QMessageBox.critical(self, "错误", "请选择性状！")
            return
        gs_args = {
            "pheno_file": self.pheno_file,
            "geno_file": self.geno_file,
            "train_file": self.training_file_path_edit.text().strip(),
            "core_sample_file": None,
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

        species_group = self.create_species_population_group()
        main_layout.addWidget(species_group)

        result_file_path_group = self.create_result_file_path_group()
        main_layout.addWidget(result_file_path_group)

        gs_param_group = self.create_gs_param_group()
        main_layout.addWidget(gs_param_group)

        log_group = self.create_log_group()
        main_layout.addWidget(log_group)
        self.setLayout(main_layout)

    def create_species_population_group(self):
        group = QGroupBox("选择物种和群体")
        layout = QVBoxLayout()

        species_layout = QHBoxLayout()
        species_label = QLabel("物种:")
        self.species_combo = QComboBox()
        self.species_combo.addItems([m["specie"] for m in self.config["curated_models"]])
        species_layout.addWidget(species_label)
        species_layout.addWidget(self.species_combo)

        population_layout = QHBoxLayout()
        population_label = QLabel("群体:")
        self.population_combo = QComboBox()
        population_layout.addWidget(population_label)
        population_layout.addWidget(self.population_combo)

        self.paper_info_label = QLabel("文献信息：")
        self.paper_info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.paper_info_label.setStyleSheet("color: blue; text-decoration: underline;")

        # 信号连接
        self.species_combo.currentIndexChanged.connect(self._update_populations)
        self.population_combo.currentIndexChanged.connect(self._update_paper_info)

        layout.addLayout(species_layout)
        layout.addLayout(population_layout)
        layout.addWidget(self.paper_info_label)
        group.setLayout(layout)

        if self.species_combo.count() > 0:
            self.species_combo.setCurrentIndex(0)
            self._update_populations()
            if self.population_combo.count() > 0:
                self.population_combo.setCurrentIndex(0)
                self._update_paper_info()

        return group

    def _update_populations(self):
        self.population_combo.clear()
        selected_specie = self.species_combo.currentText()
        for model in self.config["curated_models"]:
            if model["specie"] == selected_specie:
                self.population_combo.addItems([p["population"] for p in model["populations"]])
                break

    def _update_paper_info(self):
        selected_specie = self.species_combo.currentText()
        selected_population = self.population_combo.currentText()

        for model in self.config["curated_models"]:
            if model["specie"] == selected_specie:
                for population in model["populations"]:
                    if population["population"] == selected_population:
                        paper_link = f"<a href='{population['url']}'>{population['paper']}</a>"
                        self.paper_info_label.setText(f"文献信息：{paper_link}")
                        self.paper_info_label.setOpenExternalLinks(True)
                        self.pheno_file = population["phe"]
                        self.geno_file = population["geno"]
                        self.load_traits(self.pheno_file)
                        break
                break

    def load_traits(self, file_path):
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
            QMessageBox.critical(self, "数据加载错误",
                                 f"无法加载表型数据：\n{str(e)}\n"
                                 f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")
            self.log_view.setText("数据加载错误"
                                  f"无法加载表型数据：\n{str(e)}\n"
                                  f"请确保：\n1. 文件格式正确\n2. 包含表头行\n")

    def create_gs_param_group(self):
        gs_param_group = QGroupBox("GS 参数设置")

        gs_param_layout = QVBoxLayout()

        trait_layout = QHBoxLayout()
        trait_label = QLabel("选择性状:")

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
        result_file_path_group = QGroupBox("文件路径选择")
        main_layout = QVBoxLayout()

        training_layout = QHBoxLayout()
        lbl_training = QLabel("预测文件：")  # 新增标签
        self.training_file_path_edit = QLineEdit()
        self.training_file_path_edit.setPlaceholderText("选择预测文件路径")
        btn_training = QPushButton("选择训练基因型文件")
        btn_training.clicked.connect(lambda: self.select_path(self.training_file_path_edit, mode="file"))

        training_layout.addWidget(lbl_training)
        training_layout.addWidget(self.training_file_path_edit)
        training_layout.addWidget(btn_training)

        result_layout = QHBoxLayout()
        lbl_result = QLabel("结果路径：")
        self.result_file_path_edit = QLineEdit()
        self.result_file_path_edit.setPlaceholderText("选择结果文件保存路径")
        btn_result = QPushButton("选择输出路径")
        btn_result.clicked.connect(lambda: self.select_path(self.result_file_path_edit, mode="directory"))

        result_layout.addWidget(lbl_result)
        result_layout.addWidget(self.result_file_path_edit)
        result_layout.addWidget(btn_result)

        main_layout.addLayout(training_layout)
        main_layout.addLayout(result_layout)

        result_file_path_group.setLayout(main_layout)
        return result_file_path_group

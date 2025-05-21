import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QLabel, QComboBox, QSpinBox, QMessageBox, QFormLayout
from PyQt6.QtWidgets import QVBoxLayout, QGroupBox, QHBoxLayout

from common_tab import CommonTab, DraggableLineEdit
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
            "models": self.model_combo.currentText(),
            "threads": self.threads_spin.value(),
            "use_gpu": self.gpu_combo.currentText() == "启用",
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
        layout = QFormLayout()

        layout.setHorizontalSpacing(20)
        # 物种行
        self.species_combo = QComboBox()
        self.species_combo.addItems([m["specie"] for m in self.config["curated_models"]])
        layout.addRow("物种:", self.species_combo)

        # 群体行
        self.population_combo = QComboBox()
        layout.addRow("群体:", self.population_combo)

        # 文献信息
        self.paper_info_label = QLabel("文献信息：")
        self.paper_info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addRow("文献信息:", self.paper_info_label)  # 单独添加，不带标签

        # 信号连接
        self.species_combo.currentIndexChanged.connect(self._update_populations)
        self.population_combo.currentIndexChanged.connect(self._update_paper_info)

        # 初始化逻辑
        if self.species_combo.count() > 0:
            self.species_combo.setCurrentIndex(0)
            self._update_populations()
            if self.population_combo.count() > 0:
                self.population_combo.setCurrentIndex(0)
                self._update_paper_info()

        group.setLayout(layout)
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
                        paper_link = f"<a href='{population['url']}' style='text-decoration: none;'>{population['paper']}</a>"
                        self.paper_info_label.setText(f"{paper_link}")
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
        gs_param_layout = QFormLayout()

        # 设置表单布局样式
        gs_param_layout.setHorizontalSpacing(20)  # 标签与控件间距
        gs_param_layout.setVerticalSpacing(15)  # 控件垂直间距

        # 选择性状行
        self.trait_combo.setPlaceholderText("请选择性状")
        gs_param_layout.addRow(QLabel("选择性状:"), self.trait_combo)

        # 模型分类
        self.model_categories = {
            "BLUP": ["GBLUP", "rrBLUP(Ridge)"],
            "机器学习": ["SVR", "RF", "CatBoost", "XGBoost", "LightGBM", "GBDT"],
            "贝叶斯方法": ["BayesA"],
            "正则化方法": ["LASSO", "ElasticNet"]
        }

        # 模型类别选择
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.model_categories.keys())
        self.category_combo.currentTextChanged.connect(self.update_model_combo)
        gs_param_layout.addRow(QLabel("模型类别:"), self.category_combo)

        # 具体模型选择
        self.model_combo = QComboBox()
        gs_param_layout.addRow(QLabel("具体模型:"), self.model_combo)
        self.update_model_combo(self.category_combo.currentText())

        # 线程数
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 16)
        self.threads_spin.setValue(4)
        gs_param_layout.addRow(QLabel("线程数:"), self.threads_spin)

        # GPU加速
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItems(["启用", "禁用"])
        gs_param_layout.addRow(QLabel("使用 GPU 加速:"), self.gpu_combo)

        # 优化算法
        self.optimization_combo = QComboBox()
        self.optimization_combo.addItems(["网格搜索", "随机搜索", "贝叶斯优化"])
        gs_param_layout.addRow(QLabel("优化算法:"), self.optimization_combo)

        # 执行按钮
        self.btn_run_gs = QPushButton("执行基因型选择")
        gs_param_layout.addRow(None, self.btn_run_gs)  # 无标签行

        # 设置布局
        gs_param_group.setLayout(gs_param_layout)
        return gs_param_group

    def update_model_combo(self, category):
        current_models = self.model_categories.get(category, [])
        self.model_combo.clear()
        self.model_combo.addItems(current_models)

    def create_result_file_path_group(self):
        result_file_path_group = QGroupBox("文件路径选择")
        form_layout = QFormLayout()

        # 设置表单布局样式
        form_layout.setHorizontalSpacing(20)  # 标签与控件间距
        form_layout.setVerticalSpacing(15)  # 控件垂直间距

        # 预测文件行
        lbl_training = QLabel("预测文件：")
        self.training_file_path_edit = DraggableLineEdit()
        self.training_file_path_edit.setPlaceholderText("选择预测文件路径")

        # 按钮容器
        training_btn_layout = QHBoxLayout()
        btn_training = QPushButton("选择训练基因型文件")
        btn_training.clicked.connect(lambda: self.select_path(self.training_file_path_edit, mode="file"))
        training_btn_layout.addWidget(self.training_file_path_edit, stretch=5)
        training_btn_layout.addSpacing(10)
        training_btn_layout.addWidget(btn_training, stretch=1)

        # 添加预测文件行
        form_layout.addRow(lbl_training, training_btn_layout)

        # 结果路径行
        lbl_result = QLabel("结果路径：")
        self.result_file_path_edit = DraggableLineEdit()
        self.result_file_path_edit.setPlaceholderText("选择结果文件保存路径")

        # 结果按钮容器
        result_btn_layout = QHBoxLayout()
        btn_result = QPushButton("选择输出路径")
        btn_result.clicked.connect(lambda: self.select_path(self.result_file_path_edit, mode="directory"))
        result_btn_layout.addWidget(self.result_file_path_edit, stretch=5)
        result_btn_layout.addSpacing(10)
        result_btn_layout.addWidget(btn_result, stretch=1)

        # 添加结果路径行
        form_layout.addRow(lbl_result, result_btn_layout)

        # 设置布局
        result_file_path_group.setLayout(form_layout)
        return result_file_path_group

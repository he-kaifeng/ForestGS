from PyQt6.QtCore import QThread, pyqtSignal

from gs import get_sample_id, read_vcf, get_pheno, genomic_selections, visualize_results, save_GEBV


class GSOperations(QThread):
    progress_signal = pyqtSignal(str)  # 进度信号
    error_signal = pyqtSignal(str)  # 错误信号

    def __init__(self, gs_args):
        super().__init__()
        self.gs_args = gs_args

    def run(self):
        try:
            sample_ids = get_sample_id(self.gs_args["core_sample_file"])
            ids, geno_data = read_vcf(self.gs_args["geno_file"], sample_ids)
            self.progress_signal.emit("训练基因型数据读取完成")

            train_ids, train_genotypes = read_vcf(self.gs_args["train_file"], None)
            self.progress_signal.emit("预测基因型数据读取完成")

            pheno_data = get_pheno(self.gs_args["pheno_file"], self.gs_args["trait"], sample_ids)
            self.progress_signal.emit("训练表型数据读取完成")

            self.progress_signal.emit(f"开始进行模型训练及预测，选择的模型：{self.gs_args['models']}")
            metrics = genomic_selections(geno_data, pheno_data, self.gs_args["models"],
                                         self.gs_args["threads"], self.gs_args["use_gpu"],
                                         self.gs_args["optimization"], train_genotypes, train_ids)
            self.progress_signal.emit("基因组选择完成")

            result_str = f"基因组选择结果:\n性能指标:\n{metrics}"
            self.progress_signal.emit(result_str)
            visualize_results(metrics, self.gs_args["result_dir"])
            save_GEBV(metrics["gebv"], f"{self.gs_args['result_dir']}/GEBV.csv")
        except Exception as e:
            self.error_signal.emit(f"发生错误: {str(e)}")

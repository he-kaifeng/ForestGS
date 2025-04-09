import os
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from PyQt6.QtCore import QObject, pyqtSignal

from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, Lasso, BayesianRidge
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.svm import SVR
from xgboost import XGBRegressor


def genomic_selections(genotypes, phenotypic_data, model, threads, use_gpu, optimization,
                       train_genotypes, train_ids):
    try:
        # 数据分割
        X_train, X_test, y_train, y_test = train_test_split(genotypes, phenotypic_data, test_size=0.2,
                                                            random_state=42)
        # 模型选择
        models = {
            "BayesA": BayesianRidge(),
            "rrBLUP": Ridge(alpha=1.0),
            "LASSO": Lasso(alpha=0.01),
            "SVR": SVR(kernel="linear"),
            "RF": RandomForestRegressor(n_estimators=100, n_jobs=threads),
            "CatBoost": CatBoostRegressor(thread_count=threads, task_type="GPU" if use_gpu else "CPU", verbose=0),
            "XGBoost": XGBRegressor(n_jobs=threads, tree_method="gpu_hist" if use_gpu else "auto"),
            "LightGBM": LGBMRegressor(n_jobs=threads, device="gpu" if use_gpu else "cpu"),
        }

        model_instance = models.get(model)
        if model_instance is None:
            raise ValueError(f"不支持的模型: {model}")

        # 模型训练
        start_time = time.time()
        model_instance.fit(X_train, y_train)
        training_time = time.time() - start_time

        test = model_instance.predict(X_test)

        start_time = time.time()
        gebv = model_instance.predict(train_genotypes)
        prediction_time = time.time() - start_time

        metrics = {
            "PCC": np.corrcoef(y_test, test)[0, 1],
            "R²": r2_score(y_test, test),
            "MSE": mean_squared_error(y_test, test),
            "RMSE": np.sqrt(mean_squared_error(y_test, test)),
            "Training Time": training_time,
            "Prediction Time": prediction_time,
            "y_test": y_test,
            "y_pred": test,
        }
        # 将 GEBV 与样本 ID 结合
        gebv_df = pd.DataFrame({"IID": train_ids, "GEBV": gebv})
        return gebv_df, metrics
    except Exception as e:
        raise ValueError(f"基因组选择时发生错误: {str(e)}")


def get_sample_id(sample_file):
    """读取核心样本文件并返回样本 ID"""
    if sample_file is None:
        return None
    try:
        core_samples = pd.read_csv(sample_file, sep="\s+", header=None)

        if core_samples.shape[1] == 1:
            core_samples.columns = ["FID_IID"]

        elif core_samples.shape[1] == 2:
            core_samples.columns = ["FID", "IID"]
            core_samples["FID_IID"] = core_samples["FID"].astype(str) + "_" + core_samples["IID"].astype(str)

        else:
            raise ValueError("core_sample_file 文件格式不正确，应为 1 列（FID_IID）或 2 列（FID 和 IID）")

        return core_samples["FID_IID"]
    except Exception as e:
        raise ValueError(f"读取核心样本文件时发生错误: {str(e)}")


def generate_phenotypic_data(phenotype_file, sample_ids, trait):
    try:
        phenotype_df = pd.read_csv(phenotype_file, sep="\t")
        phenotype_df["FID_IID"] = phenotype_df["FID"].astype(str) + "_" + phenotype_df["IID"].astype(str)
        phenotype_df = phenotype_df[phenotype_df["FID_IID"].isin(sample_ids)]
        if phenotype_df.empty:
            raise ValueError("未找到与 sample_ids 匹配的表型数据")
        return phenotype_df[trait].values
    except Exception as e:
        raise ValueError(f"读取表型数据时发生错误: {str(e)}")


def read_plink_bed(geno_file, sample_ids=None):
    try:
        base_path = os.path.splitext(geno_file)[0]  # 去掉 .bed 后缀
        fam_file = base_path + ".fam"
        bim_file = base_path + ".bim"
        # 读取 .fam 文件（样本信息）
        fam = pd.read_csv(fam_file, sep="\s+", header=None,
                          names=["FID", "IID", "FatherID", "MotherID", "Sex", "Phenotype"])
        fam["FID_IID"] = fam["FID"].astype(str) + "_" + fam["IID"].astype(str)
        samples = fam["FID_IID"].values
        n_samples = len(samples)
        # 读取 .bim 文件（位点信息）
        bim = pd.read_csv(bim_file, sep="\s+", header=None,
                          names=["Chromosome", "MarkerID", "GeneticDistance", "Position", "Allele1", "Allele2"])
        n_markers = len(bim)
        # 读取 .bed 文件（基因型数据）
        with open(geno_file, "rb") as bed:
            header = bed.read(3)
            if header != b'\x6C\x1B\x01':
                raise ValueError("Invalid .bed file header")
            genotypes = np.fromfile(bed, dtype=np.uint8).reshape(n_samples, -1)
        # 将基因型数据转换为 0, 1, 2 格式
        genotypes = np.unpackbits(genotypes, axis=1)[:, :n_markers * 2].reshape(n_samples, n_markers, 2)
        genotypes = genotypes.sum(axis=2)
        # 如果提供了样本 ID，则筛选样本
        if sample_ids is not None:
            sample_indices = np.isin(samples, sample_ids)
            if np.sum(sample_indices) == 0:
                raise ValueError("未找到与 sample_ids 匹配的样本")
            samples = samples[sample_indices]
            genotypes = genotypes[sample_indices, :]
        return genotypes, samples, bim
    except Exception as e:
        raise ValueError(f"读取 PLINK 文件时发生错误: {str(e)}")


class GSOperations(QObject):
    start_gs = pyqtSignal(dict)  # 触发 GS 操作的信号
    progress_signal = pyqtSignal(str)  # 进度信号
    error_signal = pyqtSignal(str)  # 错误信号
    result_signal = pyqtSignal(str)  # 结果信号

    def __init__(self):
        super().__init__()
        self.start_gs.connect(self.run_gs)

    def run_gs(self, gs_args):
        try:
            sample_ids = get_sample_id(gs_args["core_sample_file"])

            genotypes, ids, bim = read_plink_bed(gs_args["geno_file"], sample_ids)

            self.progress_signal.emit("训练基因型数据读取完成")

            train_genotypes, train_ids, train_bim = read_plink_bed(gs_args["train_file"], None)
            self.progress_signal.emit("预测基因型数据读取完成")

            phenotypic_data = generate_phenotypic_data(gs_args["pheno_file"], ids, gs_args["trait"])
            self.progress_signal.emit("训练表型数据读取完成")

            gebv_df, metrics = genomic_selections(genotypes, phenotypic_data, gs_args["models"],
                                                  gs_args["threads"], gs_args["use_gpu"],
                                                  gs_args["optimization"], train_genotypes, train_ids)
            self.progress_signal.emit("基因组选择完成")
            # 保存结果
            result_file = os.path.join(gs_args["result_dir"], "gs_results.csv")
            gebv_df.to_csv(result_file, index=False)
            self.progress_signal.emit(f"结果已保存到: {result_file}")
            # 输出结果
            result_str = f"基因组选择结果:\n{gebv_df.head()}\n\n性能指标:\n{metrics}"
            self.result_signal.emit(result_str)
            # 可视化结果
            self.visualize_results(metrics["y_test"], metrics["y_pred"], metrics, gs_args["result_dir"])
        except Exception as e:
            self.error_signal.emit(f"发生错误: {str(e)}")

    def visualize_results(self, y_test, y_pred, metrics, save_dir="results"):
        try:
            # 确保保存目录存在
            os.makedirs(save_dir, exist_ok=True)

            # 提取关键性能指标
            r2 = metrics["R²"]
            pcc = metrics["PCC"]
            rmse = metrics["RMSE"]

            # 1. 箱线图
            plt.figure(figsize=(6, 6))
            sns.boxplot(data=[y_test, y_pred], palette="Set2")
            plt.xticks([0, 1], ['Actual Values', 'Predicted Values'])
            plt.title(f'Boxplot of Actual vs Predicted Values\nR²={r2:.3f}, PCC={pcc:.3f}, RMSE={rmse:.3f}')
            plt.savefig(os.path.join(save_dir, "boxplot.pdf"), dpi=300, bbox_inches="tight")
            plt.close()

            # 2. 散点图
            plt.figure(figsize=(6, 6))
            plt.scatter(y_test, y_pred, alpha=0.5)
            plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], color='red', linestyle='--')
            plt.title(f'Scatter Plot of Actual vs Predicted Values\nR²={r2:.3f}, PCC={pcc:.3f}, RMSE={rmse:.3f}')
            plt.xlabel('Actual Values')
            plt.ylabel('Predicted Values')
            plt.savefig(os.path.join(save_dir, "scatter_plot.pdf"), dpi=300, bbox_inches="tight")
            plt.close()

            # 3. 频率分布图
            plt.figure(figsize=(6, 6))
            sns.histplot(y_test, color='blue', label='Actual Values', kde=True)
            sns.histplot(y_pred, color='orange', label='Predicted Values', kde=True)
            plt.title(f'Distribution of Actual vs Predicted Values\nR²={r2:.3f}, PCC={pcc:.3f}, RMSE={rmse:.3f}')
            plt.legend()
            plt.savefig(os.path.join(save_dir, "distribution_plot.pdf"), dpi=300, bbox_inches="tight")
            plt.close()

            # 发送进度信号
            self.progress_signal.emit(f"Visualization results saved to: {save_dir}")
        except Exception as e:
            raise ValueError(f"Error during visualization: {str(e)}")

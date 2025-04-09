import gzip
import io
import os
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, Lasso, BayesianRidge
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.svm import SVR
from xgboost import XGBRegressor


def read_vcf(vcf_file, sample_ids=None):
    if vcf_file.endswith('.gz'):
        f = gzip.open(vcf_file, 'rt')
    else:
        f = open(vcf_file)

    lines = [line for line in f if not line.startswith('##')]
    f.close()

    vcf_data = pd.read_csv(io.StringIO(''.join(lines)), sep='\t')
    vcf_samples = vcf_data.columns[9:].tolist()

    # 提取用户选择的样本
    if sample_ids is not None:
        vcf_samples = sample_ids

    vcf_arr = []

    for sample in vcf_samples:
        sample_data = vcf_data[sample].tolist()
        processed_data = []
        for genotype in sample_data:
            if ':' in genotype:
                genotype = genotype.split(':')[0]
            if '|' in genotype:
                alleles = genotype.split('|')
            else:
                alleles = genotype.split('/')
            try:
                sum_alleles = sum(int(allele) for allele in alleles)
            except ValueError:
                # todo 填充vcf文件
                sum_alleles = -1
            processed_data.append(sum_alleles)
        vcf_arr.append(processed_data)
    return vcf_samples, vcf_arr


def get_pheno(phenotype_file, column, sample_ids=None):
    if phenotype_file.endswith('.csv'):
        pheno_data = pd.read_csv(phenotype_file)
    else:
        pheno_data = pd.read_csv(phenotype_file, sep="\t")

    sample_id_col = pheno_data.columns[0]

    if sample_ids is not None:
        filtered_data = pheno_data[pheno_data[sample_id_col].isin(sample_ids)][[sample_id_col, column]]
        filtered_data = filtered_data.set_index(sample_id_col).loc[sample_ids].reset_index()
        return filtered_data[column].tolist()
    else:
        return pheno_data[column].tolist()


def genomic_selections(genotypes, phenotypic_data, model, threads, use_gpu):
    try:
        # 数据分割
        x_train, x_test, y_train, y_test = train_test_split(genotypes, phenotypic_data, test_size=0.2)
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
        model_instance.fit(x_train, y_train)
        training_time = time.time() - start_time

        test = model_instance.predict(x_test)

        metrics = {
            "PCC": np.corrcoef(y_test, test)[0, 1],
            "R²": r2_score(y_test, test),
            "MSE": mean_squared_error(y_test, test),
            "RMSE": np.sqrt(mean_squared_error(y_test, test)),
            "Training Time": training_time,
            "y_test": y_test,
            "y_pred": test,
        }
        return metrics
    except Exception as e:
        raise ValueError(f"基因组选择时发生错误: {str(e)}")


def visualize_results(metrics, save_dir="results"):
    try:
        os.makedirs(save_dir, exist_ok=True)

        r2 = metrics["R²"]
        pcc = metrics["PCC"]
        rmse = metrics["RMSE"]
        y_test = metrics["y_test"]
        y_pred = metrics["y_pred"]

        plt.figure(figsize=(6, 6))
        sns.boxplot(data=[y_test, y_pred], palette="Set2")
        plt.xticks([0, 1], ['Actual Values', 'Predicted Values'])
        plt.title(f'Boxplot of Actual vs Predicted Values\nR²={r2:.3f}, PCC={pcc:.3f}, RMSE={rmse:.3f}')
        plt.savefig(os.path.join(save_dir, "boxplot.pdf"), dpi=300, bbox_inches="tight")
        plt.close()

        plt.figure(figsize=(6, 6))
        plt.scatter(y_test, y_pred, alpha=0.5)
        plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], color='red', linestyle='--')
        plt.title(f'Scatter Plot of Actual vs Predicted Values\nR²={r2:.3f}, PCC={pcc:.3f}, RMSE={rmse:.3f}')
        plt.xlabel('Actual Values')
        plt.ylabel('Predicted Values')
        plt.savefig(os.path.join(save_dir, "scatter_plot.pdf"), dpi=300, bbox_inches="tight")
        plt.close()

        plt.figure(figsize=(6, 6))
        sns.histplot(y_test, color='blue', label='Actual Values', kde=True)
        sns.histplot(y_pred, color='orange', label='Predicted Values', kde=True)
        plt.title(f'Distribution of Actual vs Predicted Values\nR²={r2:.3f}, PCC={pcc:.3f}, RMSE={rmse:.3f}')
        plt.legend()
        plt.savefig(os.path.join(save_dir, "distribution_plot.pdf"), dpi=300, bbox_inches="tight")
        plt.close()

    except Exception as e:
        raise ValueError(f"Error during visualization: {str(e)}")


if __name__ == '__main__':
    samples, arr = read_vcf("geno.vcf")
    phe = get_pheno("phe.txt", "TSLL")

    result = genomic_selections(arr, phe, "CatBoost", 8, True)
    visualize_results(result)

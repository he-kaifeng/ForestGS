import gzip
import io
import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from scipy import linalg
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.kernel_ridge import KernelRidge
from sklearn.linear_model import Ridge, Lasso, BayesianRidge, ElasticNet
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
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
                # 填充vcf文件
                sum_alleles = -1
            processed_data.append(sum_alleles)
        vcf_arr.append(processed_data)
    return vcf_samples, vcf_arr


def get_sample_id(sample_file):
    if sample_file is None:
        return None
    try:
        core_samples = pd.read_csv(sample_file, sep="\s+", header=None)
        return core_samples.squeeze().tolist()
    except Exception as e:
        raise ValueError(f"读取核心样本文件时发生错误: {str(e)}")


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


def save_list_with_pandas(data, file_path):
    try:
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False, header=False)  # 或者 to_excel()
        print(f"数据已成功保存至：{file_path}")
    except Exception as e:
        print(f"保存失败：{str(e)}")


def genomic_selections(genotypes, phenotypic_data, model, threads, use_gpu, optimization,
                       train_genotypes, train_ids):
    try:

        x_train, x_test, y_train, y_test = train_test_split(genotypes, phenotypic_data, test_size=0.4, random_state=0)

        k = 40000
        selector = SelectKBest(score_func=f_regression, k=k)
        x_train = selector.fit_transform(x_train, y_train)
        x_test = selector.transform(genotypes)
        train_genotypes = selector.transform(train_genotypes)
        y_test = phenotypic_data

        models = {
            "GBLUP": gblup,
            "KRR": KernelRidge(alpha=0.1, kernel='rbf'),
            "BayesA": BayesianRidge(),
            "rrBLUP": Ridge(alpha=1.0),
            "LASSO": Lasso(alpha=0.01),
            "SVR": SVR(kernel="linear", C=100, gamma="auto"),
            "RF": RandomForestRegressor(n_estimators=500, n_jobs=threads, random_state=42),
            "CatBoost": CatBoostRegressor(thread_count=threads, task_type="GPU" if use_gpu else "CPU", verbose=0),
            "XGBoost": XGBRegressor(n_jobs=threads, tree_method="gpu_hist" if use_gpu else "auto"),
            "LightGBM": LGBMRegressor(n_jobs=threads, device="gpu" if use_gpu else "cpu"),
            "GBDT": GradientBoostingRegressor(),
            "ElasticNet": ElasticNet(alpha=0.1, l1_ratio=0.5)
        }

        model_instance = models.get(model)
        if model_instance is None:
            raise ValueError(f"不支持的模型: {model}")

        if model == "GBLUP":
            _, test = model_instance(x_train, y_train, x_test)
            train_matrix = np.empty((0, 2))
            if train_genotypes is not None:
                _, train_pred = model_instance(x_train, y_train, train_genotypes)
                train_matrix = np.column_stack((train_ids, train_pred))
        else:
            # 其他模型保持原有的处理方式
            model_instance.fit(x_train, y_train)
            test = model_instance.predict(x_test)
            train_matrix = np.empty((0, 2))
            if train_genotypes is not None:
                train_pred = model_instance.predict(train_genotypes)
                train_matrix = np.column_stack((train_ids, train_pred))

        metrics = {
            "PCC": np.corrcoef(y_test, test)[0, 1],
            "R²": r2_score(y_test, test),
            "MSE": mean_squared_error(y_test, test),
            "RMSE": np.sqrt(mean_squared_error(y_test, test)),
            "y_test": y_test,
            "y_pred": test,
            "gebv": train_matrix.tolist(),
            "actual_vs_predicted": np.column_stack((y_test, test)).tolist()
        }

        return metrics
    except Exception as e:
        raise ValueError(f"基因组选择时发生错误: {str(e)}")


def save_GEBV(GEBV, save_path="GEBV.csv"):
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df = pd.DataFrame(
            GEBV,
            columns=["SampleID", "GEBV"]
        )
        df.to_csv(save_path, index=False)
        print(f"成功保存预测结果至：{os.path.abspath(save_path)}")
        return True
    except Exception as e:
        print(f"保存预测结果失败：{str(e)}")
        return False


def save_actual_vs_predicted(result, save_path="actual_vs_predicted.csv"):
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        df = pd.DataFrame(
            result,
            columns=["Actual", "Predicted"]
        )
        df.to_csv(save_path, index=False)
        print(f"成功保存预测结果至：{os.path.abspath(save_path)}")
        return True
    except Exception as e:
        print(f"保存预测结果失败：{str(e)}")
        return False


def gblup(X_train, y_train, X_test=None, h2=0.5, lambda_param=1e-6):
    # 保存原始数据的均值
    y_mean = np.mean(y_train)

    # 标准化基因型数据
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    n_train = X_train_scaled.shape[0]

    # 计算加性遗传关系矩阵(G)
    G_train = np.dot(X_train_scaled, X_train_scaled.T) / X_train_scaled.shape[1]

    # 添加一个小的对角线项以确保矩阵是正定的
    G_train += np.eye(n_train) * lambda_param

    # 计算方差组分
    Vg = h2 * np.var(y_train)  # 基因型方差
    Ve = (1 - h2) * np.var(y_train)  # 环境方差

    # 构建混合模型方程
    V = G_train * Vg + np.eye(n_train) * Ve

    # 求解混合模型方程
    gebv_train = Vg * np.dot(G_train, linalg.solve(V, (y_train - y_mean)))

    # 将育种值转换回原始尺度
    gebv_train = gebv_train + y_mean

    if X_test is not None:
        # 使用相同的scaler转换测试数据
        X_test_scaled = scaler.transform(X_test)

        # 计算测试集的G矩阵
        G_test = np.dot(X_test_scaled, X_train_scaled.T) / X_train_scaled.shape[1]

        # 预测测试集的GEBV
        gebv_test = Vg * np.dot(G_test, linalg.solve(V, (y_train - y_mean)))

        # 将育种值转换回原始尺度
        gebv_test = gebv_test + y_mean

        return gebv_train, gebv_test

    return gebv_train


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
        plt.savefig(os.path.join(save_dir, "boxplot.png"), dpi=300, bbox_inches="tight")
        plt.close()

        plt.figure(figsize=(6, 6))
        plt.scatter(y_test, y_pred, alpha=0.5)
        plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], color='red', linestyle='--')
        plt.title(f'Scatter Plot of Actual vs Predicted Values\nR²={r2:.3f}, PCC={pcc:.3f}, RMSE={rmse:.3f}')
        plt.xlabel('Actual Values')
        plt.ylabel('Predicted Values')
        plt.savefig(os.path.join(save_dir, "scatter_plot.png"), dpi=300, bbox_inches="tight")
        plt.close()

        plt.figure(figsize=(6, 6))
        sns.histplot(y_test, color='blue', label='Actual Values', kde=True)
        sns.histplot(y_pred, color='orange', label='Predicted Values', kde=True)
        plt.title(f'Distribution of Actual vs Predicted Values\nR²={r2:.3f}, PCC={pcc:.3f}, RMSE={rmse:.3f}')
        plt.legend()
        plt.savefig(os.path.join(save_dir, "distribution_plot.png"), dpi=300, bbox_inches="tight")
        plt.close()

    except Exception as e:
        raise ValueError(f"Error during visualization: {str(e)}")


def read_plink_bed(geno_file, sample_ids=None):
    try:
        base_path = os.path.splitext(geno_file)[0]
        fam_file = base_path + ".fam"
        bim_file = base_path + ".bim"

        fam = pd.read_csv(fam_file, sep="\s+", header=None,
                          names=["FID", "IID", "FatherID", "MotherID", "Sex", "Phenotype"])
        fam["FID_IID"] = fam["FID"].astype(str) + "_" + fam["IID"].astype(str)
        samples = fam["FID_IID"].values
        n_samples = len(samples)

        bim = pd.read_csv(bim_file, sep="\s+", header=None,
                          names=["Chromosome", "MarkerID", "GeneticDistance", "Position", "Allele1", "Allele2"])
        n_markers = len(bim)

        with open(geno_file, "rb") as bed:
            header = bed.read(3)
            if header != b'\x6C\x1B\x01':
                raise ValueError("Invalid .bed file header")
            genotypes = np.fromfile(bed, dtype=np.uint8).reshape(n_samples, -1)

        genotypes = np.unpackbits(genotypes, axis=1)[:, :n_markers * 2].reshape(n_samples, n_markers, 2)
        genotypes = genotypes.sum(axis=2)

        if sample_ids is not None:
            sample_indices = np.isin(samples, sample_ids)
            if np.sum(sample_indices) == 0:
                raise ValueError("未找到与 sample_ids 匹配的样本")
            samples = samples[sample_indices]
            genotypes = genotypes[sample_indices, :]
        return genotypes, samples, bim
    except Exception as e:
        raise ValueError(f"读取 PLINK 文件时发生错误: {str(e)}")


def parse_json_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


if __name__ == '__main__':
    geno, geno_data = read_vcf("D:\\Projects\\R_project\\ForestGS\\data\\geno.vcf", None)
    phe_data = get_pheno("D:\\Projects\\R_project\\ForestGS\\data\\phe\\filled_data_均值填充.txt", "Dbh")

    metrics = genomic_selections(geno_data, phe_data, "KRR", 4, True, None, None, None)
    visualize_results(metrics, "results")
    save_actual_vs_predicted(metrics["actual_vs_predicted"], "results/actual_vs_predicted.csv")

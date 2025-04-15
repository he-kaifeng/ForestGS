import os
import subprocess

import numpy as np
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal
from matplotlib import pyplot as plt


class GWASOperations(QObject):
    # 定义信号
    start_gwas = pyqtSignal(dict)  # 触发 GWAS 操作的信号
    progress_signal = pyqtSignal(str)  # 进度信号
    error_signal = pyqtSignal(str)  # 错误信号
    result_signal = pyqtSignal(str)  # 结果信号

    def __init__(self, plink_path):
        super().__init__()
        self.plink_path = plink_path
        # 连接信号和槽
        self.start_gwas.connect(self.run_gwas)

    def run_gwas(self, gwas_args):
        """执行 GWAS 分析的具体逻辑"""
        print(gwas_args)
        try:
            # 检查表型文件是否存在
            if not os.path.isfile(gwas_args["pheno_file"]):
                raise FileNotFoundError(f"表型文件不存在: {gwas_args['pheno_file']}")
            # 检查基因型文件是否存在
            geno_file = gwas_args["geno_file"]
            geno_prefix = os.path.splitext(geno_file)[0]
            # 构建 PLINK 命令
            plink_cmd = ([
                self.plink_path, '--bfile', geno_prefix,
                "--assoc",
                "--pheno", gwas_args["pheno_file"],
                "--pheno-name", gwas_args["pheno_trait"],
                "--out", os.path.join(gwas_args["result_dir"], "gwas_results"),
                "--allow-no-sex"
            ])
            # 添加可选参数
            if gwas_args["kinship_file"]:
                plink_cmd.extend(["--genome", gwas_args["kinship_file"]])
            if gwas_args["covar_file"]:
                plink_cmd.extend(["--covar", gwas_args["covar_file"]])
            if gwas_args["core_sample_file"]:
                plink_cmd.extend(["--keep", gwas_args["core_sample_file"]])
            if gwas_args["random_marker"]:
                plink_cmd.extend(["--mperm", str(gwas_args["marker_num"])])
            if gwas_args["logp_marker"]:
                plink_cmd.extend(["--logistic", "hide-covar"])
            # 执行命令
            self.progress_signal.emit(f"执行命令: {' '.join(plink_cmd)}")
            subprocess.run(plink_cmd, check=True)
            # 处理结果
            self.progress_signal.emit("GWAS 分析完成！")
            self.result_signal.emit(f"结果已保存到: {gwas_args['result_dir']}")
            # 调用绘图函数
            self.plot_manhattan_and_qq(gwas_args["result_dir"])

        except subprocess.CalledProcessError as e:
            self.error_signal.emit(f"PLINK 命令执行失败: {str(e)}")
        except Exception as e:
            self.error_signal.emit(f"GWAS 分析失败: {str(e)}")

    def plot_manhattan_and_qq(self, result_dir):
        """绘制曼哈顿图和 QQ 图"""
        try:
            # 读取结果文件
            result_file = os.path.join(result_dir, "gwas_results.qassoc")
            if not os.path.isfile(result_file):
                raise FileNotFoundError(f"结果文件不存在: {result_file}")
            df = pd.read_csv(result_file, sep='\s+')  # 使用正则表达式匹配任意空白分隔符
            # 过滤无效的P值并计算-log10(p)
            df = df.dropna(subset=['P'])
            df['minus_log10p'] = -np.log10(df['P'])
            # 为每个染色体分配颜色（交替颜色）
            colors = ['skyblue', 'navy']
            df['color'] = df['CHR'].apply(lambda x: colors[x % 2])
            # 计算x轴位置（按染色体分组排列）
            chromosomes = df['CHR'].unique()
            chromosomes.sort()
            x_offset = 0
            x = []
            chr_pos = {}  # 记录染色体起始和结束位置
            chr_width = 100  # 每个染色体的固定宽度
            for chr in chromosomes:
                chr_data = df[df['CHR'] == chr]
                num_snps = len(chr_data)
                x_pos = np.linspace(x_offset, x_offset + chr_width, num_snps, endpoint=False)
                x.extend(x_pos)
                chr_pos[chr] = (x_offset, x_offset + chr_width)
                x_offset += chr_width + 10  # 染色体间留空10个单位
            # 绘制曼哈顿图
            plt.figure(figsize=(14, 6))
            plt.scatter(x, df['minus_log10p'], c=df['color'], s=5, alpha=0.7)
            # 设置x轴标签（染色体编号）
            xticks = [np.mean(chr_pos[chr]) for chr in chromosomes]
            plt.xticks(xticks, chromosomes)
            plt.xlabel('Chromosome')
            plt.ylabel('-log10(p-value)')
            # 添加显著性线（Bonferroni校正）
            n_snps = len(df)
            bonferroni_threshold = 0.05 / n_snps
            plt.axhline(-np.log10(bonferroni_threshold), color='red', linestyle='--', linewidth=1)
            plt.title('Manhattan Plot')
            plt.tight_layout()
            plt.savefig(os.path.join(result_dir, "manhattan_plot.pdf"))  # 保存曼哈顿图
            # 计算理论分位数和观测分位数
            observed = -np.log10(np.sort(df['P']))
            expected = -np.log10(np.linspace(1 / len(df), 1, len(df)))
            # 绘制QQ图
            plt.figure(figsize=(6, 6))
            plt.scatter(expected, observed, s=5, alpha=0.5)
            plt.plot([0, max(expected)], [0, max(expected)], '--', color='red', linewidth=1)
            plt.xlabel('Expected -log10(p)')
            plt.ylabel('Observed -log10(p)')
            plt.title('QQ Plot')
            plt.tight_layout()
            plt.savefig(os.path.join(result_dir, "qq_plot.pdf"))  # 保存QQ图
            self.progress_signal.emit("曼哈顿图和 QQ 图已生成并保存！")
        except Exception as e:
            self.error_signal.emit(f"绘图失败: {str(e)}")

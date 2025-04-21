import gzip
import os
import shutil
import subprocess

import numpy as np
import seaborn as sns
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal
from matplotlib import pyplot as plt


class GenoOperations(QObject):
    # 定义信号，用于与UI线程通信
    progress_signal = pyqtSignal(str)  # 进度信息
    error_signal = pyqtSignal(str)  # 错误信息
    result_signal = pyqtSignal(str)  # 处理结果（输出文件路径）
    # 定义信号，用于触发具体操作
    start_convert_format = pyqtSignal(str, str, str)  # 文件格式转换
    start_quality_control = pyqtSignal(str, str, float, float, float, float)  # 质量控制
    start_filter_data = pyqtSignal(str, str, str, str, str, str)  # 数据过滤
    start_genetic_analysis = pyqtSignal(str, str, float, str, str)  # 遗传结构分析

    def __init__(self, plink_path):
        super().__init__()
        self.plink_path = plink_path
        # 将信号连接到具体实现函数
        self.start_convert_format.connect(self.handle_convert_format)
        self.start_quality_control.connect(self.handle_quality_control)
        self.start_filter_data.connect(self.handle_filter_data)
        self.start_genetic_analysis.connect(self.handle_genetic_analysis)

    def handle_convert_format(self, input_file, output_dir, target_format):
        """文件格式转换"""
        try:
            self.progress_signal.emit(f"正在执行文件格式转换\n\t输入文件: {input_file}\n\t目标格式: {target_format}")
            # 获取输入文件的基本名（不带扩展名）
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_file = os.path.join(output_dir, base_name)
            # 获取输入文件的扩展名
            input_extension = os.path.splitext(input_file)[1].lower()
            # 检查输入文件格式是否有效
            if input_extension not in [".ped", ".bed", ".vcf"]:
                raise ValueError(f"不支持的输入文件格式: {input_extension}")
            # 根据输入格式和目标格式执行转换
            if input_extension == ".ped" and target_format == "bed":
                # 从ped转换到bed
                input_prefix = os.path.splitext(input_file)[0]
                process = subprocess.run(
                    [self.plink_path, "--file", input_prefix, "--make-bed", "--out", output_file],
                    capture_output=True, text=True
                )
            elif input_extension == ".ped" and target_format == "vcf":
                # 从ped转换到vcf
                input_prefix = os.path.splitext(input_file)[0]
                process = subprocess.run(
                    [self.plink_path, "--file", input_prefix, "--recode", "vcf", "--out", output_file],
                    capture_output=True, text=True
                )
            elif input_extension == ".bed" and target_format == "ped":
                # 从bed转换到ped
                input_prefix = os.path.splitext(input_file)[0]
                process = subprocess.run(
                    [self.plink_path, "--bfile", input_prefix, "--recode", "--out", output_file],
                    capture_output=True, text=True
                )
            elif input_extension == ".bed" and target_format == "vcf":
                # 从bed转换到vcf
                input_prefix = os.path.splitext(input_file)[0]
                process = subprocess.run(
                    [self.plink_path, "--bfile", input_prefix, "--recode", "vcf", "--out", output_file],
                    capture_output=True, text=True
                )
            elif input_extension == ".vcf" and target_format == "ped":
                # 从vcf转换到ped
                process = subprocess.run(
                    [self.plink_path, "--vcf", input_file, "--recode", "--const-fid", "--out", output_file],
                    capture_output=True, text=True
                )
            elif input_extension == ".vcf" and target_format == "bed":
                # 从vcf转换到bed
                process = subprocess.run(
                    [self.plink_path, "--vcf", input_file, "--make-bed", "--const-fid", "--out", output_file],
                    capture_output=True, text=True
                )
            else:
                raise ValueError(f"不支持从 {input_extension} 转换到 {target_format}")
            # 显示PLINK的输出
            self.progress_signal.emit(f"PLINK输出:\n{process.stdout}")
            if process.stderr:
                self.progress_signal.emit(f"PLINK错误信息:\n{process.stderr}")
            self._cleanup_files(output_file)
            self.progress_signal.emit("文件格式转换完成！")
            self.result_signal.emit(output_file)
        except subprocess.CalledProcessError as e:
            self.error_signal.emit(f"PLINK工具执行失败: {str(e)}")
        except Exception as e:
            self.error_signal.emit(f"文件格式转换失败: {str(e)}")

    def handle_quality_control(self, input_file, output_dir, maf=None, missing_geno=None, missing_sample=None, r2=None):
        """执行质量控制并生成所需文件和图表"""
        try:
            self.progress_signal.emit(f"正在执行质量控制\n\t输入文件: {input_file}")
            # 获取输入文件的基本名（不带扩展名）
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_prefix = os.path.join(output_dir, base_name)
            log_file = f"{output_prefix}_preprocessed.log"
            # 根据输入文件类型动态调整 PLINK 命令
            input_extension = os.path.splitext(input_file)[1].lower()
            if input_extension == ".bed":
                input_prefix = os.path.splitext(input_file)[0]
                plink_input_args = ["--bfile", input_prefix]
            elif input_extension == ".ped":
                input_prefix = os.path.splitext(input_file)[0]
                plink_input_args = ["--file", input_prefix]
            elif input_extension == ".vcf":
                plink_input_args = ["--vcf", input_file, "--const-fid"]
            else:
                raise ValueError(f"不支持的输入文件格式: {input_extension}")
            # 基本过滤
            self._run_plink(
                plink_input_args + [
                    "--out", output_prefix,
                    "--make-bed",
                    "--freqx",
                    "--missing",
                    "--het",
                    "--geno", str(missing_geno) if missing_geno else "0.05",
                    "--mind", str(missing_sample) if missing_sample else "0.05",
                    "--maf", str(maf) if maf else "0.01"
                ],
                log_file
            )
            # 填充缺失值
            self._run_plink([
                "--bfile", output_prefix,
                "--out", f"{output_prefix}_f",
                "--make-bed",
                "--fill-missing-a2"
            ], log_file)
            # LD 过滤
            self._run_plink([
                "--bfile", f"{output_prefix}_f",
                "--out", output_prefix,
                "--indep-pairwise", "50", "10", str(r2) if r2 else "0.8"
            ], log_file)
            # 提取 LD 过滤后的 SNP
            self._run_plink([
                "--bfile", f"{output_prefix}_f",
                "--out", f"{output_prefix}_r",
                "--extract", f"{output_prefix}.prune.in",
                "--make-bed"
            ], log_file)
            # 数据转换：生成 .ped/.map 文件
            self._run_plink([
                "--bfile", f"{output_prefix}_r",
                "--out", f"{output_prefix}_filter",
                "--recode", "compound-genotypes", "01",
                "--output-missing-genotype", "3"
            ], log_file)
            # 数据转换：生成 .bed/.bim/.fam 文件
            self._run_plink([
                "--bfile", f"{output_prefix}_r",
                "--out", f"{output_prefix}_filter",
                "--output-missing-genotype", "3",
                "--make-bed"
            ], log_file)
            # 生成图表
            self._generate_het_histogram(output_prefix)
            self._generate_maf_histogram(output_prefix)  # 使用 .frqx 文件生成 MAF 分布直方图
            self._generate_imiss_histogram(output_prefix)
            self._generate_lmiss_histogram(output_prefix)
            # 删除不需要的中间文件和日志文件
            self._cleanup_intermediate_files(output_prefix)
            self.progress_signal.emit("质量控制完成！")
            self.result_signal.emit(output_prefix)
        except Exception as e:
            self.error_signal.emit(f"质量控制失败: {str(e)}")

    def _run_plink(self, args, log_file):
        """运行 PLINK 命令，并将输出实时显示到 UI 界面"""
        cmd = [self.plink_path] + args
        self.progress_signal.emit(f"正在执行命令: {' '.join(cmd)}")
        with open(log_file, "a") as log:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            for line in process.stdout:
                log.write(line)
                self.progress_signal.emit(line.strip())  # 将输出实时显示到 UI 界面
            for line in process.stderr:
                log.write(line)
                self.progress_signal.emit(line.strip())  # 将错误信息实时显示到 UI 界面
            process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"PLINK 命令执行失败: {' '.join(cmd)}")

    def _generate_het_histogram(self, output_prefix):
        """生成杂合率分布直方图"""
        het_file = f"{output_prefix}.het"
        if not os.path.exists(het_file):
            raise FileNotFoundError(f"杂合率文件未找到: {het_file}")
        df = pd.read_csv(het_file, sep='\s+')
        plt.figure(figsize=(10, 6))
        plt.hist(df["F"], bins=50, color="blue", alpha=0.7)
        plt.xlim(0, 1)
        plt.xlabel("Heterozygosity Rate", fontsize=12)
        plt.ylabel("Number of SNPs", fontsize=12)
        plt.title("Histogram of SNP Heterozygosity Rates", fontsize=14)
        plt.xticks(fontsize=10)
        plt.yticks(fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.savefig(f"{output_prefix}_het.pdf")
        plt.close()

    def _generate_maf_histogram(self, output_prefix):
        freqx_data = pd.read_csv(output_prefix + '.frqx', sep='\t')
        sample_num = pd.read_csv(output_prefix + '.fam', sep=' ').shape[0]

        maf_data = pd.DataFrame({'maf': (freqx_data['C(HOM A1)'] * 2 + freqx_data['C(HET)']) / (sample_num * 2)})
        # 生成直方图
        plt.figure(figsize=(10, 6))
        plt.hist(maf_data['maf'], bins=50, color="blue", alpha=0.7)
        plt.xlim(0, 1)
        plt.xlabel("Minor Allele Frequency (MAF)", fontsize=12)
        plt.ylabel("Number of SNPs", fontsize=12)
        plt.title("Histogram of SNP Minor Allele Frequencies", fontsize=14)
        plt.xticks(fontsize=10)
        plt.yticks(fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.savefig(f"{output_prefix}_maf.pdf")
        plt.close()

    def _generate_imiss_histogram(self, output_prefix):
        """生成样本缺失率分布直方图"""
        imiss_file = f"{output_prefix}.imiss"
        if not os.path.exists(imiss_file):
            raise FileNotFoundError(f"样本缺失率文件未找到: {imiss_file}")
        df = pd.read_csv(imiss_file, sep='\s+')
        plt.figure(figsize=(10, 6))
        plt.hist(df["F_MISS"], bins=50, color="blue", alpha=0.7)
        plt.xlim(0, 1)
        plt.xlabel("Sample Missing Rate", fontsize=12)
        plt.ylabel("Number of Samples", fontsize=12)
        plt.title("Histogram of Sample Missing Rates", fontsize=14)
        plt.xticks(fontsize=10)
        plt.yticks(fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.savefig(f"{output_prefix}_imiss.pdf")
        plt.close()

    def _generate_lmiss_histogram(self, output_prefix):
        """生成SNP缺失率分布直方图"""
        lmiss_file = f"{output_prefix}.lmiss"
        if not os.path.exists(lmiss_file):
            raise FileNotFoundError(f"SNP缺失率文件未找到: {lmiss_file}")
        df = pd.read_csv(lmiss_file, sep='\s+')
        plt.figure(figsize=(10, 6))
        plt.hist(df["F_MISS"], bins=50, color="blue", alpha=0.7)
        plt.xlim(0, 1)
        plt.xlabel("SNP Missing Rate", fontsize=12)
        plt.ylabel("Number of SNPs", fontsize=12)
        plt.title("Histogram of SNP Missing Rates", fontsize=14)
        plt.xticks(fontsize=10)
        plt.yticks(fontsize=10)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.savefig(f"{output_prefix}_lmiss.pdf")
        plt.close()

    def _cleanup_intermediate_files(self, output_prefix):
        """删除不需要的中间文件和日志文件"""
        files_to_delete = [
            f"{output_prefix}.bed", f"{output_prefix}.bim", f"{output_prefix}.fam", f"{output_prefix}.log",
            f"{output_prefix}.nosex",
            f"{output_prefix}_f.bed", f"{output_prefix}_f.bim", f"{output_prefix}_f.fam", f"{output_prefix}_f.log",
            f"{output_prefix}_f.nosex",
            f"{output_prefix}_r.bed", f"{output_prefix}_r.bim", f"{output_prefix}_r.fam", f"{output_prefix}_r.log",
            f"{output_prefix}_r.nosex",
            f"{output_prefix}_filter.log", f"{output_prefix}_filter.nosex"
        ]
        for file in files_to_delete:
            if os.path.exists(file):
                os.remove(file)
                self.progress_signal.emit(f"已删除文件: {file}")

    def handle_filter_data(self, input_file, output_dir, filter_sample=None, exclude_sample=None, filter_snp=None,
                           exclude_snp=None):
        """根据输入参数对VCF、BED、PED文件进行样本和SNP的筛选"""
        try:
            self.progress_signal.emit(f"正在执行数据筛选\n\t输入文件: {input_file}")
            # 获取输入文件的基本名（不带扩展名）
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            result_name = base_name + "_handle"
            output_file = os.path.join(output_dir, result_name)
            # 获取输入文件的扩展名
            input_extension = os.path.splitext(input_file)[1].lower()
            # 检查输入文件格式是否有效
            if input_extension not in [".vcf", ".bed", ".ped"]:
                raise ValueError(f"不支持的输入文件格式: {input_extension}")
            # 根据输入文件格式进行筛选
            if input_extension == ".vcf":
                # VCF文件筛选
                self._filter_vcf(input_file, output_file, filter_sample, exclude_sample, filter_snp, exclude_snp)
            elif input_extension == ".bed":
                # BED文件筛选
                self._filter_bed(input_file, output_file, filter_sample, exclude_sample, filter_snp, exclude_snp)
            elif input_extension == ".ped":
                # PED文件筛选
                self._filter_ped(input_file, output_file, filter_sample, exclude_sample, filter_snp, exclude_snp)
            self.progress_signal.emit("数据筛选完成！")
            self.result_signal.emit(output_file)
        except Exception as e:
            self.error_signal.emit(f"数据筛选失败: {str(e)}")

    def _filter_vcf(self, input_file, output_file, filter_sample, exclude_sample, filter_snp, exclude_snp):
        """筛选VCF文件"""
        try:
            # 构建PLINK命令
            cmd = [self.plink_path, "--vcf", input_file, "--make-bed", "--const-fid", "--out", output_file]
            # 添加样本筛选参数
            self._run_plink_with_filters(cmd, output_file, filter_sample, exclude_sample, filter_snp, exclude_snp)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"PLINK工具执行失败: {str(e)}")

    def _filter_bed(self, input_file, output_file, filter_sample, exclude_sample, filter_snp, exclude_snp):
        """筛选BED文件"""
        try:
            # 获取BED文件前缀
            input_prefix = os.path.splitext(input_file)[0]
            # 构建PLINK命令
            cmd = [self.plink_path, "--bfile", input_prefix, "--make-bed", "--out", output_file]
            # 添加样本筛选参数
            self._run_plink_with_filters(cmd, output_file, filter_sample, exclude_sample, filter_snp, exclude_snp)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"PLINK工具执行失败: {str(e)}")

    def _filter_ped(self, input_file, output_file, filter_sample, exclude_sample, filter_snp, exclude_snp):
        """筛选PED文件"""
        try:
            # 获取PED文件前缀
            input_prefix = os.path.splitext(input_file)[0]
            # 构建PLINK命令
            cmd = [self.plink_path, "--file", input_prefix, "--make-bed", "--out", output_file]
            # 添加样本筛选参数
            self._run_plink_with_filters(cmd, output_file, filter_sample, exclude_sample, filter_snp, exclude_snp)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"PLINK工具执行失败: {str(e)}")

    def _run_plink_with_filters(self, cmd, output_file, filter_sample=None, exclude_sample=None, filter_snp=None,
                                exclude_snp=None):
        try:
            # 添加样本筛选参数
            if filter_sample:
                cmd.extend(["--keep", filter_sample])
            if exclude_sample:
                cmd.extend(["--remove", exclude_sample])
            # 添加SNP筛选参数
            if filter_snp:
                cmd.extend(["--extract", filter_snp])
            if exclude_snp:
                cmd.extend(["--exclude", exclude_snp])
            # 执行PLINK命令
            process = subprocess.run(cmd, capture_output=True, text=True)
            # 显示PLINK输出
            self.progress_signal.emit(f"PLINK输出:\n{process.stdout}")
            if process.stderr:
                self.progress_signal.emit(f"PLINK错误信息:\n{process.stderr}")
            # 删除不必要的文件
            self._cleanup_files(output_file)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"PLINK工具执行失败: {str(e)}")

    def _cleanup_files(self, output_file):
        """删除PLINK生成的log和nosex文件"""
        log_file = f"{output_file}.log"
        nosex_file = f"{output_file}.nosex"
        if os.path.exists(log_file):
            os.remove(log_file)
        if os.path.exists(nosex_file):
            os.remove(nosex_file)

    def handle_genetic_analysis(self, input_file, output_dir, pca_components, relationship_method, extract_file=None):
        """执行遗传分析，包括 PCA 和亲缘关系分析"""
        try:
            self.progress_signal.emit(f"正在执行遗传分析\n\t输入文件: {input_file}")
            # 获取输入文件的基本名（不带扩展名）
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_prefix = os.path.join(output_dir, base_name)
            log_file = f"{output_prefix}_genetic_analysis.log"
            # 根据输入文件类型动态调整 PLINK 命令
            input_extension = os.path.splitext(input_file)[1].lower()
            if input_extension == ".bed":
                input_prefix = os.path.splitext(input_file)[0]
                plink_input_args = ["--bfile", input_prefix]
            elif input_extension == ".ped":
                input_prefix = os.path.splitext(input_file)[0]
                plink_input_args = ["--file", input_prefix]
            elif input_extension == ".vcf":
                plink_input_args = ["--vcf", input_file]
            else:
                raise ValueError(f"不支持的输入文件格式: {input_extension}")
            # PCA 分析
            self._run_plink(
                plink_input_args + [
                    "--out", output_prefix,
                    "--pca", str(pca_components)
                ],
                log_file
            )
            # 生成 PCA 坐标图
            self._generate_pca_plot(output_prefix)
            # 亲缘关系分析
            if relationship_method == "IBS":
                # 如果提供了 extract_file，添加 --extract 参数
                ibs_args = plink_input_args + [
                    "--out", output_prefix,
                    "--distance", "ibs", "square"
                ]
                if extract_file:
                    ibs_args.extend(["--extract", extract_file])
                self._run_plink(ibs_args, log_file)
                relationship_matrix_file = f"{output_prefix}.mibs"
            elif relationship_method == "GRM":
                grm_args = plink_input_args + [
                    "--out", output_prefix,
                    "--make-grm-gz"
                ]
                if extract_file:
                    grm_args.extend(["--extract", extract_file])
                self._run_plink(grm_args, log_file)
                relationship_matrix_file = f"{output_prefix}.grm.gz"
            else:
                raise ValueError(f"不支持的亲缘关系分析方法: {relationship_method}")
            # 生成亲缘相关性热图
            self._generate_relationship_heatmap(relationship_matrix_file, output_prefix, relationship_method)
            self.progress_signal.emit("遗传分析完成！")
            self.result_signal.emit(output_prefix)
        except Exception as e:
            print(e)
            self.error_signal.emit(f"遗传分析失败: {str(e)}")

    def _generate_pca_plot(self, output_prefix):
        """生成 PCA 坐标图"""
        eigenvec_file = f"{output_prefix}.eigenvec"
        if not os.path.exists(eigenvec_file):
            raise FileNotFoundError(f"PCA 结果文件未找到: {eigenvec_file}")
        # 读取 PCA 结果
        df = pd.read_csv(eigenvec_file, sep="\s+", header=None)
        # 提取前两个主成分
        pc1 = df.iloc[:, 2]
        pc2 = df.iloc[:, 3]
        # 生成 PCA 坐标图
        plt.figure(figsize=(10, 8))
        plt.scatter(pc1, pc2, alpha=0.6, c='blue', edgecolor='black', s=50)
        plt.xlabel("PC1", fontsize=14)
        plt.ylabel("PC2", fontsize=14)
        plt.title("PCA Scatter Plot (Top 2 Principal Components)", fontsize=16, pad=20)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.savefig(f"{output_prefix}_pca.pdf", dpi=300, bbox_inches='tight')
        plt.close()

    def _generate_relationship_heatmap(self, relationship_matrix_file, output_prefix, relationship_method):
        """生成亲缘相关性热图"""
        if not os.path.exists(relationship_matrix_file):
            raise FileNotFoundError(f"亲缘关系矩阵文件未找到: {relationship_matrix_file}")
        # 读取亲缘关系矩阵
        if relationship_method == "IBS":
            matrix = pd.read_csv(relationship_matrix_file, sep="\s+", header=None)
            # 读取样本 ID
            ids_file = f"{output_prefix}.mibs.id"
            if not os.path.exists(ids_file):
                raise FileNotFoundError(f"IBS 样本 ID 文件未找到: {ids_file}")
            ids = pd.read_csv(ids_file, sep="\s+", header=None)
            # 将样本 ID 设置为矩阵的行列索引
            matrix.columns = ids[0]
            matrix.index = ids[0]
        elif relationship_method == "GRM":
            # 定义 .grm.gz 和 .grm.id 文件路径
            grm_gz_file = f"{output_prefix}.grm.gz"
            grm_ids_file = f"{output_prefix}.grm.id"
            if not os.path.exists(grm_gz_file) or not os.path.exists(grm_ids_file):
                raise FileNotFoundError(f"GRM 文件未找到: {grm_gz_file} 或 {grm_ids_file}")
            # 解压 .grm.gz 文件
            grm_file = f"{output_prefix}.grm"
            with gzip.open(grm_gz_file, "rb") as gz_in:
                with open(grm_file, "wb") as f_out:
                    shutil.copyfileobj(gz_in, f_out)
            # 读取 GRM 矩阵
            matrix = read_grm_matrix(grm_file, grm_ids_file)
        # 生成热图
        plt.figure(figsize=(10, 8))
        sns.heatmap(matrix, cmap="viridis", annot=False, fmt=".2f")
        plt.title(f"Kinship Correlation Heatmap ({relationship_method})")
        plt.savefig(f"{output_prefix}_relationship_heatmap.pdf")
        plt.close()


def read_grm_matrix(grm_file, grm_ids_file):
    # 读取样本 ID
    ids = pd.read_csv(grm_ids_file, sep="\s+", header=None)
    n_samples = len(ids)
    # 初始化对称矩阵
    matrix = np.zeros((n_samples, n_samples))
    # 读取 .grm 文件并填充矩阵
    with open(grm_file, "r") as f:
        for line in f:
            parts = line.strip().split()
            i = int(parts[0]) - 1  # 转换为 0 索引
            j = int(parts[1]) - 1  # 转换为 0 索引
            grm_value = float(parts[3])
            matrix[i, j] = grm_value
            if i != j:  # 如果不是对角元素，填充对称位置
                matrix[j, i] = grm_value
    # 将矩阵转换为 DataFrame，并设置样本 ID 为行列索引
    matrix = pd.DataFrame(matrix, index=ids[0], columns=ids[0])
    return matrix

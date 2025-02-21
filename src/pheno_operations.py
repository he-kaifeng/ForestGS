import os
import matplotlib.pyplot as plt
import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal
import seaborn as sns


class PhenoOperations(QObject):
    # 定义信号，用于与UI线程通信
    progress_signal = pyqtSignal(str)  # 进度信息
    error_signal = pyqtSignal(str)  # 错误信息
    result_signal = pyqtSignal(pd.DataFrame)  # 处理结果
    start_outlier_filter = pyqtSignal(pd.DataFrame, str, float, str)
    start_missing_value_fill = pyqtSignal(pd.DataFrame, str, str, str)
    start_normalization = pyqtSignal(pd.DataFrame, str, str, str)
    start_recoding = pyqtSignal(pd.DataFrame, str, str, str, str)

    def __init__(self):
        super().__init__()

        # 将信号连接到具体实现函数
        self.start_outlier_filter.connect(self.handle_outlier_filter)
        self.start_missing_value_fill.connect(self.handle_missing_value_fill)
        self.start_normalization.connect(self.handle_normalization)
        self.start_recoding.connect(self.handle_recoding)

    def handle_missing_value_fill(self, data, trait, method, out_dir):
        """缺失值填充"""
        self.progress_signal.emit(f'正在执行缺失值填充\n\t填充性状: {trait}\n\t填充方法: {method}')
        try:
            # 确保输出目录存在
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            # 判断是否为所有性状
            traits_to_process = [trait] if trait != "all" else data.columns[1:]
            for trait in traits_to_process:
                # 检查性状是否为数值型
                is_numeric = pd.api.types.is_numeric_dtype(data[trait])
                # 找出缺失值并保存到单独的文件中
                missing_data = data[data[trait].isna()]
                if not missing_data.empty:
                    missing_file_path = os.path.join(out_dir, f'missing_values_{trait}.csv')
                    missing_data.to_csv(missing_file_path, index=False,
                                        encoding='utf-8')
                    self.progress_signal.emit(f"缺失值结果已保存到: {missing_file_path}")
                # 填充缺失值
                if method in ["前向填充", "后向填充"] or is_numeric:
                    if method == "均值填充" and is_numeric:
                        data[trait] = data[trait].fillna(data[trait].mean())
                    elif method == "中位数填充" and is_numeric:
                        data[trait] = data[trait].fillna(data[trait].median())
                    elif method == "众数填充" and is_numeric:
                        data[trait] = data[trait].fillna(data[trait].mode()[0])
                    elif method == "前向填充":
                        data[trait] = data[trait].fillna.ffill()
                    elif method == "后向填充":
                        data[trait] = data[trait].fillna.bfill()
                else:
                    self.progress_signal.emit(f"性状 {trait} 不是数值型，仅支持前向或后向填充。")
                    continue
            # 保存填充后的数据
            filled_file_path = os.path.join(out_dir, f'filled_data_{method}.csv')
            data.to_csv(filled_file_path, index=False, encoding='utf-8')
            self.result_signal.emit(data)
            self.progress_signal.emit(f"缺失值填充完成，结果已保存到: {filled_file_path}")
        except Exception as e:
            self.error_signal.emit(f"缺失值填充失败: {str(e)}")

    def handle_outlier_filter(self, data, trait, sd_multiplier, out_dir):
        """异常值过滤"""
        try:
            # 确保输出目录存在
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            # 检查性状是否为数值型
            if not pd.api.types.is_numeric_dtype(data[trait]):
                self.progress_signal.emit(f"性状 {trait} 不是数值型，跳过异常值过滤。")
                return
            # 计算过滤范围
            mean = data[trait].mean()
            std = data[trait].std()
            lower_bound = mean - sd_multiplier * std
            upper_bound = mean + sd_multiplier * std
            # 过滤数据
            filtered_data = data[(data[trait] >= lower_bound) & (data[trait] <= upper_bound)]
            outlier_data = data[(data[trait] < lower_bound) | (data[trait] > upper_bound)]
            # 保存过滤后的数据和异常数据
            filtered_file_path = os.path.join(out_dir, f'filtered_data_{trait}.csv')
            outlier_file_path = os.path.join(out_dir, f'outlier_data_{trait}.csv')
            filtered_data.to_csv(filtered_file_path, index=False, encoding='utf-8')
            outlier_data.to_csv(outlier_file_path, index=False, encoding='utf-8')
            # 绘制过滤前后的频率分布图
            plt.figure(figsize=(12, 6))
            # 过滤前的分布
            plt.subplot(1, 2, 1)
            data[trait].plot(kind='hist', bins=30, color='blue', alpha=0.7, edgecolor='black')
            plt.title(f'Before Filtering\nTrait: {trait}')
            plt.xlabel(trait)
            plt.ylabel('Frequency')
            # 过滤后的分布
            plt.subplot(1, 2, 2)
            filtered_data[trait].plot(kind='hist', bins=30, color='green', alpha=0.7, edgecolor='black')
            plt.title(f'After Filtering\nTrait: {trait}')
            plt.xlabel(trait)
            plt.ylabel('Frequency')
            # 保存分布图
            plot_file_path = os.path.join(out_dir, f'frequency_distribution_{trait}.png')
            plt.tight_layout()
            plt.savefig(plot_file_path, dpi=300)
            plt.close()
            # 发送结果信号
            self.result_signal.emit(filtered_data)
            self.progress_signal.emit(f"异常值过滤完成，结果已保存到: {filtered_file_path}")
        except Exception as e:
            self.error_signal.emit(f"异常值过滤失败: {str(e)}")

    def handle_normalization(self, data, trait, method, out_dir):
        """数据归一化"""
        try:
            # 确保输出目录存在
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            # 判断是否为所有性状
            traits_to_process = [trait] if trait != "all" else data.columns
            # 归一化数据
            for trait in traits_to_process:
                # 检查性状是否为数值型
                if not pd.api.types.is_numeric_dtype(data[trait]):
                    self.progress_signal.emit(f"性状 {trait} 不是数值型，跳过归一化。")
                    continue
                # 保存归一化前的数据
                original_data = data[trait].copy()
                # 根据方法进行归一化
                if method == "Z-score":
                    data[trait] = (data[trait] - data[trait].mean()) / data[trait].std()
                elif method == "Min-Max":
                    data[trait] = (data[trait] - data[trait].min()) / (data[trait].max() - data[trait].min())
                else:
                    self.error_signal.emit(f"未知的归一化方法: {method}")
                    return
                # 绘制归一化前后的分布图（箱线图 + 样本点）
                plt.figure(figsize=(12, 6))
                # 归一化前的分布图
                plt.subplot(1, 2, 1)
                sns.boxplot(y=original_data, color='lightblue', width=0.5, showfliers=False)  # 箱线图
                sns.stripplot(y=original_data, color='blue', alpha=0.7, jitter=True, edgecolor='black',
                              linewidth=0.5)  # 样本点
                plt.title(f'Before Normalization\nTrait: {trait}')
                plt.ylabel('Phenotype Value')
                plt.xlabel('Group')
                # 归一化后的分布图
                plt.subplot(1, 2, 2)
                sns.boxplot(y=data[trait], color='lightgreen', width=0.5, showfliers=False)  # 箱线图
                sns.stripplot(y=data[trait], color='green', alpha=0.7, jitter=True, edgecolor='black',
                              linewidth=0.5)  # 样本点
                plt.title(f'After Normalization\nTrait: {trait}')
                plt.ylabel('Phenotype Value')
                plt.xlabel('Group')
                # 保存分布图
                plot_file_path = os.path.join(out_dir, f'distribution_{trait}_{method}.png')
                plt.tight_layout()
                plt.savefig(plot_file_path, dpi=300)
                plt.close()
                self.progress_signal.emit(f"性状 {trait} 的归一化完成，分布图已保存到: {plot_file_path}")
            # 保存归一化后的数据
            if trait == "all":
                normalized_file_path = os.path.join(out_dir, 'normalized_data_all.csv')
            else:
                normalized_file_path = os.path.join(out_dir, f'normalized_data_{trait}_{method}.csv')
            data.to_csv(normalized_file_path, index=False, encoding='utf-8')
            self.progress_signal.emit(f"归一化后的数据已保存到: {normalized_file_path}")
            # 发送最终结果信号
            self.result_signal.emit(data)
            self.progress_signal.emit("数据归一化完成")
        except Exception as e:
            self.error_signal.emit(f"数据归一化失败: {str(e)}")

    def handle_recoding(self, data, trait, direction, out_dir, mapping_file=None):
        """数据重编码"""
        try:
            # 确保输出目录存在
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            # 检查性状是否存在
            if trait not in data.columns:
                raise ValueError(f"性状 {trait} 不存在于数据中！")
            # 根据方向进行重编码
            if direction == "word2num（表型→数字）":
                # 将表型数据重编码为连续非负整数
                self.progress_signal.emit(f"开始将性状 {trait} 的表型数据重编码为连续非负整数...")
                unique_values = data[trait].unique()
                mapping = {value: idx for idx, value in enumerate(unique_values)}  # 从 0 开始编号
                data[trait] = data[trait].map(mapping)
                # 保存映射表
                mapping_df = pd.DataFrame(list(mapping.items()), columns=['word', 'num'])
                mapping_file_path = os.path.join(out_dir, f'mapping_{trait}_word2num.csv')
                mapping_df.to_csv(mapping_file_path, index=False, encoding='utf-8')
                self.progress_signal.emit(f"性状 {trait} 的重编码映射表已保存到: {mapping_file_path}")
            elif direction == "num2word（数字→表型）":
                # 将连续非负整数重编码为表型数据
                self.progress_signal.emit(f"开始将性状 {trait} 的数字数据重编码为表型数据...")
                if mapping_file is None:
                    raise ValueError("转换方向为数字→表型时，必须提供转化表文件！")
                # 读取映射表
                mapping_df = pd.read_csv(mapping_file)
                if 'num' not in mapping_df.columns or 'word' not in mapping_df.columns:
                    raise ValueError("转化表文件必须包含 'num' 和 'word' 两列！")
                mapping = dict(zip(mapping_df['num'], mapping_df['word']))
                data[trait] = data[trait].map(mapping)
            else:
                raise ValueError(f"未知的转换方向: {direction}")
            # 保存重编码后的数据
            recoded_file_path = os.path.join(out_dir, f'recoded_data_{trait}.csv')
            data.to_csv(recoded_file_path, index=False, encoding='utf-8')
            self.progress_signal.emit(f"重编码后的数据已保存到: {recoded_file_path}")
            # 发送结果信号
            self.result_signal.emit(data)
            self.progress_signal.emit(f"性状 {trait} 的重编码完成")
        except Exception as e:
            self.error_signal.emit(f"数据重编码失败: {str(e)}")

import pandas as pd
from PyQt6.QtCore import QObject, pyqtSignal


class PhenoOperations(QObject):
    # 定义信号，用于与UI线程通信
    progress_signal = pyqtSignal(str)  # 进度信息
    error_signal = pyqtSignal(str)  # 错误信息
    result_signal = pyqtSignal(pd.DataFrame)  # 处理结果
    start_outlier_filter = pyqtSignal(pd.DataFrame, str, float)
    start_missing_value_fill = pyqtSignal(pd.DataFrame, str, str)
    start_normalization = pyqtSignal(pd.DataFrame, str, str)
    start_recoding = pyqtSignal(pd.DataFrame, str, str, str)

    def __init__(self):
        super().__init__()
        self.start_outlier_filter.connect(self.handle_outlier_filter)
        self.start_missing_value_fill.connect(self.handle_missing_value_fill)
        self.start_normalization.connect(self.handle_normalization)
        self.start_recoding.connect(self.handle_recoding)

    def handle_missing_value_fill(self, data, trait, method):
        """缺失值填充"""
        try:
            if method == "均值填充":
                data[trait].fillna(data[trait].mean(), inplace=True)
            elif method == "中位数填充":
                data[trait].fillna(data[trait].median(), inplace=True)
            elif method == "众数填充":
                data[trait].fillna(data[trait].mode()[0], inplace=True)
            elif method == "前向填充":
                data[trait].fillna(method='ffill', inplace=True)
            elif method == "后向填充":
                data[trait].fillna(method='bfill', inplace=True)
            self.result_signal.emit(data)
            self.progress_signal.emit("缺失值填充完成")
        except Exception as e:
            self.error_signal.emit(f"缺失值填充失败: {str(e)}")

    def handle_outlier_filter(self, data, trait, sd_multiplier):
        """异常值过滤"""
        try:
            mean = data[trait].mean()
            std = data[trait].std()
            lower_bound = mean - sd_multiplier * std
            upper_bound = mean + sd_multiplier * std
            filtered_data = data[(data[trait] >= lower_bound) & (data[trait] <= upper_bound)]
            self.result_signal.emit(filtered_data)
            self.progress_signal.emit("异常值过滤完成")
        except Exception as e:
            self.error_signal.emit(f"异常值过滤失败: {str(e)}")

    def handle_normalization(self, data, trait, method):
        """数据归一化"""
        try:
            if method == "Z-score标准化":
                data[trait] = (data[trait] - data[trait].mean()) / data[trait].std()
            elif method == "Min-Max归一化":
                data[trait] = (data[trait] - data[trait].min()) / (data[trait].max() - data[trait].min())
            self.result_signal.emit(data)
            self.progress_signal.emit("数据归一化完成")
        except Exception as e:
            self.error_signal.emit(f"数据归一化失败: {str(e)}")

    def handle_recoding(self, data, trait, direction, mapping_file=None):
        """数据重编码"""
        try:
            if direction == "word2num（表型→数字）":
                # 将文本转换为数字
                unique_values = data[trait].unique()
                mapping = {value: idx + 1 for idx, value in enumerate(unique_values)}
                data[trait] = data[trait].map(mapping)
            elif direction == "num2word（数字→表型）":
                # 将数字转换为文本
                if mapping_file is None:
                    raise ValueError("转换方向为数字→表型时，必须提供转化表文件！")
                mapping_df = pd.read_csv(mapping_file)
                mapping = dict(zip(mapping_df['num'], mapping_df['word']))
                data[trait] = data[trait].map(mapping)
            self.result_signal.emit(data)
            self.progress_signal.emit("数据重编码完成")
        except Exception as e:
            self.error_signal.emit(f"数据重编码失败: {str(e)}")

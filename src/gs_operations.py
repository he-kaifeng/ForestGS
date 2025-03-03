from PyQt6.QtCore import QObject, pyqtSignal


class GSOperations(QObject):
    start_gs = pyqtSignal(dict)  # 触发 GS 操作的信号
    progress_signal = pyqtSignal(str)  # 进度信号
    error_signal = pyqtSignal(str)  # 错误信号
    result_signal = pyqtSignal(str)  # 结果信号

    def __init__(self):
        super().__init__()


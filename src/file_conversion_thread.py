import os
import subprocess

from PyQt6.QtCore import pyqtSignal, QThread


class FileConversionThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, plink_path, commands, output_prefix, target_format):
        super().__init__()
        self.plink_path = plink_path
        self.commands = commands
        self.output_prefix = output_prefix
        self.target_format = target_format
        self.output_files = []

    def run(self):
        try:
            for cmd in self.commands:
                full_cmd = [self.plink_path] + cmd
                self.log_signal.emit("执行命令: " + " ".join(full_cmd))

                process = subprocess.run(
                    full_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )

                self.log_signal.emit(process.stdout)
                if process.returncode != 0:
                    self.log_signal.emit("转换失败，错误码：" + str(process.returncode))
                    self.finished_signal.emit(False)
                    return

            # 收集生成的文件列表
            self.collect_output_files()
            self.finished_signal.emit(True)

        except Exception as e:
            self.log_signal.emit(f"转换过程异常: {str(e)}")
            self.finished_signal.emit(False)

    def collect_output_files(self):
        """根据目标格式收集生成的文件"""
        base_path = self.output_prefix
        format_extensions = {
            "ped": [".ped", ".map"],
            "bed": [".bed", ".bim", ".fam"],
            "vcf": [".vcf"]
        }

        for ext in format_extensions.get(self.target_format, []):
            file_path = base_path + ext
            if os.path.exists(file_path):
                self.output_files.append(file_path)

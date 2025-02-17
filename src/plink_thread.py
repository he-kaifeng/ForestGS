import subprocess

from PyQt6.QtCore import pyqtSignal, QThread


class PlinkThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self, plink_path, input_prefix, output_prefix, maf, geno, missing, hwe_check):
        super().__init__()
        self.hwe_check = hwe_check
        self.plink_path = plink_path
        self.input_prefix = input_prefix
        self.output_prefix = output_prefix
        self.geno = geno
        self.maf = maf
        self.missing = missing

    def run(self):
        try:
            # 通用PLINK质控命令
            cmd = [
                self.plink_path,
                "--bfile", self.input_prefix,
                "--freqx","--missing",
                "--mind", str(self.missing),
                "--maf", str(self.maf),
                "--geno", str(self.geno)
            ]

            # 如果启用 HWE 检查，添加相应参数
            if self.hwe_check:
                cmd.append("--hwe")
                cmd.append("1e-6")

            cmd.extend([
                "--make-bed",
                "--out", self.output_prefix
            ])

            self.log_signal.emit("执行PLINK命令:\n" + " ".join(cmd))

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            for line in process.stdout:
                self.log_signal.emit(line.strip())

            process.wait()
            self.finished_signal.emit(process.returncode == 0)

        except Exception as e:
            self.log_signal.emit(f"错误: {str(e)}")
            self.finished_signal.emit(False)

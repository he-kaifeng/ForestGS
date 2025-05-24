import ctypes
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from main_window import MainWindow


def main():
    # 设置任务栏图标
    myappid = 'mycompany.myproduct.subproduct.version'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    # 创建应用实例
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('../icons/app.ico'))

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 启动事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

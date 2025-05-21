import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow
from qt_material import apply_stylesheet


def main():
    # 创建应用实例
    app = QApplication(sys.argv)

    # 创建主窗口
    window = MainWindow()
    # apply_stylesheet(app, theme='light_blue.xml')
    window.show()

    # 启动事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

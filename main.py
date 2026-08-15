import sys
import argparse
from PySide6.QtWidgets import QApplication
from gui import create_main_window


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Post Seal Vision System.")
    parser.add_argument("--camera", type=int, default=1, help="Camera index to open (default: 1)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = create_main_window(args.camera)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
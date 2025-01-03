import sys
from PyQt6.QtWidgets import QApplication
from video_player import VideoPlayerWindow

def main():
    app = QApplication(sys.argv)
    window = VideoPlayerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

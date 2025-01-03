from video_player import VideoPlayerWindow
from PyQt6.QtWidgets import QApplication
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = VideoPlayerWindow()
    player.show()
    sys.exit(app.exec())

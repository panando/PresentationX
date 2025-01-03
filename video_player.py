import cv2
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QFileDialog, QLabel, QListWidget,
                            QInputDialog, QSlider, QMenu)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap

class VideoPlayerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频标记播放器")
        self.setGeometry(100, 100, 1200, 800)
        
        # 初始化变量
        self.video_path = None
        self.cap = None
        self.marks = []
        self.current_mark_index = -1
        self.is_playing = False
        self.is_seeking = False
        self.seek_timer = QTimer()  # 添加防抖动定时器
        self.seek_timer.setSingleShot(True)
        self.seek_timer.timeout.connect(self.delayed_seek)
        self.current_frame_cache = None
        
        self.setup_ui()
        self.setup_timer()
        self.setup_mark_list_context_menu()
        
    def setup_ui(self):
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # 左侧视频区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 视频显示区
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.video_label)
        
        # 时间轴
        timeline_container = QWidget()
        timeline_layout = QVBoxLayout(timeline_container)
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.sliderPressed.connect(self.on_timeline_pressed)
        self.timeline.sliderReleased.connect(self.on_timeline_released)
        self.timeline.sliderMoved.connect(self.on_timeline_change)
        self.timeline.setStyleSheet("""
            QSlider::handle:horizontal {
                background: #2196F3;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::groove:horizontal {
                height: 10px;
                background: #E0E0E0;
                margin: 0px;
                border-radius: 5px;
            }
        """)
        timeline_layout.addWidget(self.timeline)
        left_layout.addWidget(timeline_container)
        
        # 控制按钮
        controls = QHBoxLayout()
        self.load_btn = QPushButton("加载视频")
        self.play_btn = QPushButton("播放")
        self.mark_btn = QPushButton("添加标记")
        
        self.load_btn.clicked.connect(self.load_video)
        self.play_btn.clicked.connect(self.toggle_play)
        self.mark_btn.clicked.connect(self.add_mark)
        
        controls.addWidget(self.load_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.mark_btn)
        left_layout.addLayout(controls)
        
        # 右侧标记列表
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.mark_list = QListWidget()
        self.mark_list.itemDoubleClicked.connect(self.edit_mark)
        right_layout.addWidget(QLabel("标记列表"))
        right_layout.addWidget(self.mark_list)
        
        # 添加到主布局
        layout.addWidget(left_widget, stretch=7)
        layout.addWidget(right_widget, stretch=3)
        
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.setInterval(33)  # 约30fps
        self.seek_delay = 100  # 100ms的防抖动延迟
        
    def load_video(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "选择视频文件")
            if file_name:
                self.video_path = file_name
                self.cap = cv2.VideoCapture(file_name)
                total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.timeline.setMaximum(total_frames)
                self.marks = []
                self.mark_list.clear()
                self.update_frame()
                self.draw_timeline_marks()
        except Exception as e:
            print(f"加载视频出错: {str(e)}")
            
    def toggle_play(self):
        if self.cap is None:
            return
        
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.setText("暂停")
            self.timer.start()
        else:
            self.play_btn.setText("播放")
            self.timer.stop()
            
    def update_frame(self):
        if self.cap is None or self.seek_timer.isActive():
            return
            
        try:
            ret, frame = self.cap.read()
            if ret:
                self.current_frame_cache = frame
                self.display_frame(frame)
                current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                self.timeline.blockSignals(True)  # 阻止时间轴值改变时触发事件
                self.timeline.setValue(int(current_frame))
                self.timeline.blockSignals(False)
                
                # 检查是否到达标记
                for mark in self.marks:
                    if abs(mark['frame'] - current_frame) < 1:  # 允许一帧的误差
                        self.is_playing = False
                        self.play_btn.setText("播放")
                        self.timer.stop()
                        break
        except Exception as e:
            print(f"更新帧出错: {str(e)}")
            
    def add_mark(self):
        if self.cap is None:
            return
            
        current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        mark = {
            'frame': current_frame,
            'note': ''  # 初始为空注释
        }
        self.marks.append(mark)
        self.marks.sort(key=lambda x: x['frame'])
        self.update_mark_list()
        self.draw_timeline_marks()
            
    def update_mark_list(self):
        self.mark_list.clear()
        for mark in self.marks:
            display_text = f"帧:{int(mark['frame'])}"
            if mark['note']:  # 如果有注释则显示
                display_text += f" - {mark['note']}"
            self.mark_list.addItem(display_text)
            
    def edit_mark(self, item):
        # 双击跳转到标记处
        index = self.mark_list.row(item)
        if 0 <= index < len(self.marks):
            frame = self.marks[index]['frame']
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame)
            self.is_playing = False
            self.play_btn.setText("播放")
            self.timer.stop()
            self.delayed_seek()

    def on_timeline_pressed(self):
        self.timer.stop()
        self.seek_timer.stop()

    def on_timeline_released(self):
        self.delayed_seek()
        if self.is_playing:
            self.timer.start()

    def on_timeline_change(self, value):
        self.seek_timer.stop()
        self.seek_timer.start(self.seek_delay)

    def delayed_seek(self):
        """延迟执行seek操作"""
        try:
            if self.cap is None:
                return
            value = self.timeline.value()
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, value)
            ret, frame = self.cap.read()
            if ret:
                self.current_frame_cache = frame
                self.display_frame(frame)
        except Exception as e:
            print(f"时间轴操作出错: {str(e)}")

    def display_frame(self, frame):
        try:
            if frame is None:
                return
                
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            
            img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            scaled_pixmap = QPixmap.fromImage(img).scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation  # 使用快速转换提高性能
            )
            self.video_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"显示帧出错: {str(e)}")

    def draw_timeline_marks(self):
        base_style = """
            QSlider::handle:horizontal {
                background: #2196F3;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::groove:horizontal {
                height: 10px;
                background: #E0E0E0;
                margin: 0px;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #2196F3;
            }
            QSlider::add-page:horizontal {
                background: #E0E0E0;
            }
        """
        
        # 添加标记指示器样式
        mark_indicators = ""
        if self.timeline.maximum() > 0:
            for mark in self.marks:
                position = (mark['frame'] / self.timeline.maximum()) * 100
                mark_indicators += f"""
                    QSlider::handle:horizontal {{
                        background: #E0E0E0;
                    }}
                    QSlider::handle:horizontal::after {{
                        content: "";
                        position: absolute;
                        left: {position}%;
                        top: -8px;
                        width: 2px;
                        height: 26px;
                        background: #FF4081;
                        margin-left: -1px;
                    }}
                """
        
        complete_style = base_style + mark_indicators
        self.timeline.setStyleSheet(complete_style)

    def setup_mark_list_context_menu(self):
        self.mark_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mark_list.customContextMenuRequested.connect(self.show_mark_context_menu)
        
    def show_mark_context_menu(self, position):
        menu = QMenu()
        edit_action = menu.addAction("注释标记")
        action = menu.exec(self.mark_list.mapToGlobal(position))
        
        if action == edit_action:
            current_item = self.mark_list.itemAt(position)
            if current_item:
                self.add_mark_note(self.mark_list.row(current_item))

    def add_mark_note(self, index):
        if 0 <= index < len(self.marks):
            text, ok = QInputDialog.getText(
                self, "添加注释",
                "请输入标记注释：",
                text=self.marks[index]['note']
            )
            if ok:
                self.marks[index]['note'] = text
                self.update_mark_list()

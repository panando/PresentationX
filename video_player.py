import cv2
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QFileDialog, QLabel, QListWidget,
                            QInputDialog, QSlider, QMenu, QSplitter, QMessageBox, QFrame)
from styles import (TIMELINE_STYLE, VOLUME_SLIDER_STYLE, 
                   TIME_LABEL_STYLE, MARK_LABEL_STYLE)
from PyQt6.QtGui import QShortcut
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QEvent, QDateTime, QUrl
from PyQt6.QtGui import QImage, QPixmap, QKeySequence
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

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
        
        # 初始化音频播放器
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)  # 默认音量50%
        
        # 添加快捷键计时器
        self.last_prev_key_time = 0
        self.prev_key_interval = 500  # 500ms间隔
        
        self.setup_ui()
        self.setup_timer()
        self.setup_mark_list_context_menu()
        
    def setup_ui(self):
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # 使用系统默认窗口控制
        self.old_pos = None
        
        # 添加窗口拖动功能
        def mousePressEvent(event):
            self.old_pos = event.globalPosition().toPoint()
            
        def mouseMoveEvent(event):
            if self.old_pos:
                delta = event.globalPosition().toPoint() - self.old_pos
                self.move(self.pos() + delta)
                self.old_pos = event.globalPosition().toPoint()
                
        def mouseReleaseEvent(event):
            self.old_pos = None
            
        central_widget.mousePressEvent = mousePressEvent
        central_widget.mouseMoveEvent = mouseMoveEvent
        central_widget.mouseReleaseEvent = mouseReleaseEvent
        
        # 左侧视频区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 视频显示区
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.video_label)
        
        # 视频显示区
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.video_label, stretch=8)  # 视频区域占主要空间
        
        # 时间轴和标记区域容器
        timeline_container = QWidget()
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(10, 2, 10, 2)
        timeline_layout.setSpacing(2)

        # 创建时间显示面板
        time_display = QHBoxLayout()
        # 设置统一的边距和间距
        time_display.setContentsMargins(0, 0, 0, 0)
        time_display.setSpacing(5)

        # 左侧时间标签固定宽度
        LEFT_TIME_WIDTH = 80
        self.current_time_label = QLabel("00:00:00")
        self.current_time_label.setStyleSheet(TIME_LABEL_STYLE)
        self.current_time_label.setFixedWidth(LEFT_TIME_WIDTH)

        # 时间轴
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.sliderPressed.connect(self.on_timeline_pressed)
        self.timeline.sliderReleased.connect(self.on_timeline_released)
        self.timeline.sliderMoved.connect(self.on_timeline_change)
        self.timeline.setStyleSheet(TIMELINE_STYLE)

        # 右侧时间标签固定宽度
        RIGHT_TIME_WIDTH = 80
        self.total_time_label = QLabel("00:00:00")
        self.total_time_label.setStyleSheet(TIME_LABEL_STYLE)
        self.total_time_label.setFixedWidth(RIGHT_TIME_WIDTH)

        # 音量滑块固定宽度
        VOLUME_WIDTH = 80
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(VOLUME_WIDTH)
        self.volume_slider.setStyleSheet(VOLUME_SLIDER_STYLE)
        self.volume_slider.valueChanged.connect(self.set_volume)

        # 添加到时间轴布局
        time_display.addWidget(self.current_time_label)
        time_display.addWidget(self.timeline, stretch=1)
        time_display.addWidget(self.total_time_label)
        time_display.addWidget(self.volume_slider)

        # 创建标记区域布局
        marks_display = QHBoxLayout()
        marks_display.setContentsMargins(0, 0, 8, 0)  # 将右边距设为8px，左边距为0
        marks_display.setSpacing(5)

        # 标记时间标签
        self.current_mark_time = QLabel("--:--:--")
        self.current_mark_time.setStyleSheet(TIME_LABEL_STYLE)
        self.current_mark_time.setFixedWidth(LEFT_TIME_WIDTH)  # 恢复原始宽度

        # 标记容器
        marks_frame_container = QWidget()
        marks_frame_layout = QHBoxLayout(marks_frame_container)
        marks_frame_layout.setContentsMargins(0, 0, 0, 0)
        marks_frame_layout.setSpacing(0)

        self.marks_frame = QFrame()
        self.marks_frame.setStyleSheet("""
            QFrame { 
                border: 1px solid #AAAAAA; 
                background: transparent;
                border-radius: 5px;
                margin: 2px 0px;
            }
        """)
        self.marks_frame.setFixedHeight(20)
        marks_frame_layout.addWidget(self.marks_frame)

        # 下一个标记时间和持续时间
        self.next_mark_time = QLabel("--:--:--")
        self.next_mark_time.setStyleSheet(TIME_LABEL_STYLE)
        self.next_mark_time.setFixedWidth(RIGHT_TIME_WIDTH)

        self.duration_label = QLabel("00:00.000")
        self.duration_label.setStyleSheet(TIME_LABEL_STYLE)
        self.duration_label.setFixedWidth(VOLUME_WIDTH)

        # 添加到标记区域布局
        marks_display.addWidget(self.current_mark_time)
        marks_display.addWidget(marks_frame_container, stretch=1)
        marks_display.addWidget(self.next_mark_time)
        marks_display.addWidget(self.duration_label)

        # 添加到主容器
        timeline_layout.addLayout(time_display)
        timeline_layout.addLayout(marks_display)

        # 添加到左侧布局
        left_layout.addWidget(timeline_container, stretch=1)

        # 控制按钮
        controls = QHBoxLayout()
        self.load_btn = QPushButton("加载视频")
        self.play_btn = QPushButton("播放")
        self.mark_btn = QPushButton("添加标记")
        self.stop_btn = QPushButton("停止")
        
        self.load_btn.clicked.connect(self.load_video)
        self.play_btn.clicked.connect(self.toggle_play)
        self.mark_btn.clicked.connect(self.add_mark)
        self.stop_btn.clicked.connect(self.stop_video)
        
        # 添加全屏按钮
        self.fullscreen_btn = QPushButton("全屏")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        
        controls.addWidget(self.load_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.mark_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.fullscreen_btn)
        left_layout.addLayout(controls)
        
        # 设置最小窗口大小
        self.setMinimumSize(800, 600)
        
        # 右侧标记列表
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 添加可调整大小的分割器
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 导入导出按钮
        import_export_layout = QHBoxLayout()
        self.export_btn = QPushButton("导出标记")
        self.import_btn = QPushButton("导入标记")
        self.export_btn.clicked.connect(self.export_marks)
        self.import_btn.clicked.connect(self.import_marks)
        import_export_layout.addWidget(self.export_btn)
        import_export_layout.addWidget(self.import_btn)

        # 标记列表
        self.mark_list = QListWidget()
        self.mark_list.itemDoubleClicked.connect(self.edit_mark)
        
        # 创建容器并添加控件
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.addWidget(QLabel("标记列表"))
        list_layout.addLayout(import_export_layout)
        list_layout.addWidget(self.mark_list)
        
        # 添加可调整大小的分割器
        self.splitter.addWidget(list_container)
        self.splitter.setStretchFactor(0, 1)
        
        right_layout.addWidget(self.splitter)
        
        # 添加到主布局
        layout.addWidget(left_widget, stretch=7)
        layout.addWidget(right_widget, stretch=3)
        
        # 添加快捷键
        self.shortcut_fullscreen = QShortcut(QKeySequence("F11"), self)
        self.shortcut_fullscreen.activated.connect(self.toggle_fullscreen)
        
        # 修改F键和`键为全屏快捷键
        self.shortcut_f = QShortcut(Qt.Key.Key_F, self)
        self.shortcut_f.activated.connect(self.toggle_fullscreen)
        self.shortcut_backtick = QShortcut(Qt.Key.Key_QuoteLeft, self)  # 对应`键
        self.shortcut_backtick.activated.connect(self.toggle_fullscreen)
        
        # 将回车键改为跳转到上个标记
        self.shortcut_enter = QShortcut(Qt.Key.Key_Return, self)
        self.shortcut_enter.activated.connect(self.jump_to_prev_one_mark)
        
        # 空格键播放/暂停
        self.shortcut_space = QShortcut(Qt.Key.Key_Space, self)
        self.shortcut_space.activated.connect(self.toggle_play)
        
        # m键添加标记
        self.shortcut_mark = QShortcut(Qt.Key.Key_M, self)
        self.shortcut_mark.activated.connect(self.add_mark)
        
        # delete和backspace键删除标记
        self.shortcut_delete = QShortcut(Qt.Key.Key_Delete, self)
        self.shortcut_delete.activated.connect(self.delete_selected_mark)
        self.shortcut_backspace = QShortcut(Qt.Key.Key_Backspace, self)
        self.shortcut_backspace.activated.connect(self.delete_selected_mark)
        
        # 修改上下左右键快捷键
        self.shortcut_next = QShortcut(Qt.Key.Key_Right, self)
        self.shortcut_next.activated.connect(self.jump_to_next_mark)
        self.shortcut_next = QShortcut(Qt.Key.Key_Down, self)
        self.shortcut_next.activated.connect(self.jump_to_next_mark)
        
        # 修改上键和左键直接跳转到上上个标记
        self.shortcut_prev = QShortcut(Qt.Key.Key_Left, self)
        self.shortcut_prev.activated.connect(self.jump_to_prev_mark)
        self.shortcut_prev = QShortcut(Qt.Key.Key_Up, self)
        self.shortcut_prev.activated.connect(self.jump_to_prev_mark)
        
        # 添加R键和Shift键跳转到上个标记
        self.shortcut_prev_one = QShortcut(Qt.Key.Key_R, self)
        self.shortcut_prev_one.activated.connect(self.jump_to_prev_one_mark)
        self.shortcut_prev_one = QShortcut(Qt.Key.Key_Shift, self)
        self.shortcut_prev_one.activated.connect(self.jump_to_prev_one_mark)
        
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.setInterval(33)  # 约30fps
        self.seek_delay = 100  # 100ms的防抖动延迟
        
    def delayed_seek(self):
        """防抖动的延迟跳转"""
        if self.cap is None:
            return
        
        try:
            target_frame = self.timeline.value()
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            # 确保音频同步
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                position = int((target_frame / fps) * 1000)
                # 添加缓冲时间
                self.media_player.setPosition(max(0, position - 50))
                
        except Exception as e:
            print(f"跳转操作出错: {str(e)}")
        
    def set_volume(self, value):
        """设置音量"""
        self.audio_output.setVolume(value / 100.0)

    def load_video(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "选择视频文件")
            if file_name:
                self.video_path = file_name
                self.cap = cv2.VideoCapture(file_name)
                
                # 设置媒体播放器并预加载
                self.media_player.setSource(QUrl.fromLocalFile(file_name))
                # 等待媒体加载完成
                while self.media_player.mediaStatus() != QMediaPlayer.MediaStatus.LoadedMedia:
                    QApplication.processEvents()
                self.media_player.pause()
                
                total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.timeline.setMaximum(total_frames)
                # 添加默认的开始和结束标记
                self.marks = [
                    {'frame': 0, 'note': '开始'},
                    {'frame': total_frames - 1, 'note': '结束'}
                ]
                self.mark_list.clear()
                self.update_mark_list()
                self.update_frame()
                self.draw_timeline_marks()
        except Exception as e:
            print(f"加载视频出错: {str(e)}")
            
    def jump_to_next_mark(self):
        if self.cap is None or not self.marks:
            return
            
        current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        
        # 检查当前是否处于标记位置
        is_at_mark = any(abs(mark['frame'] - current_frame) < 1 for mark in self.marks)
        
        if is_at_mark:
            # 如果处于标记位置，直接播放
            self.is_playing = True
            self.play_btn.setText("暂停")
            self.timer.start()
            # 同步音频位置
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                self.media_player.setPosition(int(current_frame / fps * 1000))
            self.media_player.play()  # 播放音频
        else:
            # 否则跳转到下一个标记
            next_mark = None
            for mark in self.marks:
                if mark['frame'] > current_frame:
                    next_mark = mark
                    break
                    
            if next_mark:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, next_mark['frame'])
                self.is_playing = True
                self.play_btn.setText("暂停")
                self.timer.start()
                # 同步音频位置
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                if fps > 0:
                    self.media_player.setPosition(int(next_mark['frame'] / fps * 1000))
                self.media_player.play()  # 播放音频
                self.update_frame()
            
    def jump_to_prev_mark(self):
        """直接跳转到上上个标记并播放"""
        if self.cap is None or not self.marks:
            return
            
        current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        prev_marks = [mark for mark in reversed(self.marks) if mark['frame'] < current_frame]
        
        if len(prev_marks) > 1:
            # 跳转到上上个标记
            prev_mark = prev_marks[1]
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, prev_mark['frame'])
            self.is_playing = True
            self.play_btn.setText("暂停")
            self.timer.start()
            # 同步音频位置
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                self.media_player.setPosition(int(prev_mark['frame'] / fps * 1000))
            self.media_player.play()
            self.update_frame()
    
    def jump_to_prev_one_mark(self):
        """跳转到上一个标记并播放"""
        if self.cap is None or not self.marks:
            return
            
        current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        prev_marks = [mark for mark in reversed(self.marks) if mark['frame'] < current_frame]
        
        if prev_marks:
            # 跳转到上一个标记
            prev_mark = prev_marks[0]
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, prev_mark['frame'])
            self.is_playing = True
            self.play_btn.setText("暂停")
            self.timer.start()
            # 同步音频位置
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                self.media_player.setPosition(int(prev_mark['frame'] / fps * 1000))
            self.media_player.play()  # 播放音频
            self.update_frame()

    def toggle_play(self):
        if self.cap is None:
            return
        
        if not self.is_playing:
            # 如果没有标记，从头播放
            if not self.marks:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self.is_playing = True
                self.play_btn.setText("暂停")
                self.timer.start()
                self.media_player.play()  # 播放音频
            else:
                # 查找下一个标记
                current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                next_mark = None
                for mark in self.marks:
                    if mark['frame'] > current_frame:
                        next_mark = mark
                        break
                
                if next_mark:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                    self.is_playing = True
                    self.play_btn.setText("暂停")
                    self.timer.start()
                    self.media_player.play()  # 播放音频
                else:
                    # 没有下一个标记，回到第一个标记
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.marks[0]['frame'])
                    self.is_playing = True
                    self.play_btn.setText("暂停")
                    self.timer.start()
                    self.media_player.play()  # 播放音频
        else:
            self.is_playing = False
            self.play_btn.setText("播放")
            self.timer.stop()
            self.media_player.pause()  # 暂停音频
            # 暂停时显示当前帧
            if self.current_frame_cache is not None:
                self.display_frame(self.current_frame_cache)
            
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
                
                # 更新时间显示
                self.update_time_display()
                
                # 检查是否到达标记
                for mark in self.marks:
                    if abs(mark['frame'] - current_frame) < 1:  # 允许一帧的误差
                        self.is_playing = False
                        self.play_btn.setText("播放")
                        self.timer.stop()
                        self.media_player.pause()  # 暂停音频
                        break
                self.update_mark_times()  # 添加这一行
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
            
    def frame_to_time(self, frame):
        if self.cap is None:
            return "00:00:00"
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            return "00:00:00"
            
        # 计算当前时间
        total_seconds = int(frame / fps)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def update_time_display(self):
        """更新当前时间和总时间显示"""
        if self.cap is None:
            return
            
        current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        if fps > 0:
            # 更新当前时间
            self.current_time_label.setText(self.frame_to_time(current_frame))
            # 更新总时间
            self.total_time_label.setText(self.frame_to_time(total_frames))

    def update_mark_list(self):
        self.mark_list.clear()
        for mark in self.marks:
            time_str = self.frame_to_time(mark['frame'])
            display_text = f"{time_str}"
            if mark['note']:  # 如果有注释则显示
                display_text += f" - {mark['note']}"
            self.mark_list.addItem(display_text)
            
    def edit_mark(self, item):
        # 双击跳转到标记处并暂停
        index = self.mark_list.row(item)
        if 0 <= index < len(self.marks):
            frame_num = int(self.marks[index]['frame'])
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            self.is_playing = False
            self.play_btn.setText("播放")
            self.timer.stop()
            # 同步音频位置
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            if fps > 0:
                self.media_player.setPosition(int(frame_num / fps * 1000))
            self.media_player.pause()  # 暂停音频
            # 立即显示目标帧
            ret, frame = self.cap.read()
            if ret:
                self.current_frame_cache = frame
                self.display_frame(frame)
            # 更新时间轴位置
            self.timeline.blockSignals(True)
            self.timeline.setValue(frame_num)
            self.timeline.blockSignals(False)

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
            self.media_player.setPosition(int(value / self.cap.get(cv2.CAP_PROP_FPS) * 1000))  # 同步音频位置
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
            
            # 更新主窗口视频
            main_pixmap = QPixmap.fromImage(img).scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_label.setPixmap(main_pixmap)
            
            # 如果全屏窗口存在，更新全屏窗口视频
            if hasattr(self, 'fullscreen_window'):
                self.update_fullscreen_frame()
                
        except Exception as e:
            print(f"显示帧出错: {str(e)}")
            
    def resizeEvent(self, event):
        """窗口大小改变时重新调整视频显示和标记容器位置"""
        super().resizeEvent(event)
        
        # 更新marks_frame_container的宽度以匹配timeline
        for widget in self.findChildren(QWidget):
            if isinstance(widget, QWidget) and widget.layout() and widget.layout().count() > 0:
                if self.marks_frame in [widget.layout().itemAt(i).widget() for i in range(widget.layout().count())]:
                    widget.setFixedWidth(self.timeline.width())
                    break
        
        if self.current_frame_cache is not None:
            self.display_frame(self.current_frame_cache)
        # 窗口大小改变时重新绘制标记
        self.draw_timeline_marks()

    def draw_timeline_marks(self):
        """重绘时间轴标记"""
        # 清除旧标记
        if hasattr(self, 'mark_labels'):
            for label in self.mark_labels:
                label.deleteLater()
        self.mark_labels = []
        
        # 获取时间轴的实际可用宽度
        timeline_width = self.timeline.width()
        marks_frame_width = self.marks_frame.width()
        
        # 在标记容器中添加标记
        for mark in self.marks:
            # 计算标记位置，使用与时间轴相同的比例
            position = (mark['frame'] / self.timeline.maximum()) * marks_frame_width
            
            # 创建标记标签（三角形）
            label = QLabel("▲", self.marks_frame)
            label.setStyleSheet(MARK_LABEL_STYLE)
            label.setFixedSize(10, 10)
            
            # 设置标记位置，确保在容器内部
            x_pos = int(position - label.width()/2)
            y_pos = int((self.marks_frame.height() - label.height())/2)
            
            # 限制x坐标范围
            x_pos = max(0, min(x_pos, marks_frame_width - label.width()))
            
            label.move(x_pos, y_pos)
            label.show()
            self.mark_labels.append(label)
            
        self.update_mark_times()

    def setup_mark_list_context_menu(self):
        self.mark_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.mark_list.customContextMenuRequested.connect(self.show_mark_context_menu)
        
    def show_mark_context_menu(self, position):
        menu = QMenu()
        edit_action = menu.addAction("编辑注释")
        delete_action = menu.addAction("删除标记")
        action = menu.exec(self.mark_list.mapToGlobal(position))
        
        current_item = self.mark_list.itemAt(position)
        if current_item:
            index = self.mark_list.row(current_item)
            if action == edit_action:
                self.add_mark_note(index)
            elif action == delete_action:
                self.delete_mark(index)

    def delete_mark(self, index):
        if 0 <= index < len(self.marks):
            # 获取要删除的标记信息
            mark = self.marks[index]
            time_str = self.frame_to_time(mark['frame'])
            note = mark['note'] if mark['note'] else "无注释"
            
            # 弹出确认对话框
            confirm = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除标记吗？\n时间: {time_str}\n注释: {note}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                self.marks.pop(index)
                self.update_mark_list()
                self.draw_timeline_marks()

    def delete_selected_mark(self):
        """删除当前选中的标记"""
        current_item = self.mark_list.currentItem()
        if current_item:
            index = self.mark_list.row(current_item)
            self.delete_mark(index)

    def toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

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

    def export_marks(self):
        """导出标记到txt文件"""
        if not self.marks:
            QMessageBox.warning(self, "警告", "没有可导出的标记")
            return
            
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "导出标记",
            "",
            "Text Files (*.txt)"
        )
        
        if file_name:
            try:
                with open(file_name, 'w', encoding='utf-8') as f:
                    for mark in self.marks:
                        time_str = self.frame_to_time(mark['frame'])
                        f.write(f"{time_str} {mark['note']}\n")
                QMessageBox.information(self, "成功", "标记已成功导出")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def import_marks(self):
        """从txt文件导入标记"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "导入标记",
            "",
            "Text Files (*.txt)"
        )
        
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    new_marks = []
                    for line in lines:
                        # 分割时间和注释
                        parts = line.strip().split(' ', 1)
                        if len(parts) >= 1:
                            time_str = parts[0]
                            note = parts[1] if len(parts) > 1 else ''
                            # 将时间字符串转换为帧数
                            h, m, s = map(int, time_str.split(':'))
                            fps = self.cap.get(cv2.CAP_PROP_FPS)
                            frame = int((h * 3600 + m * 60 + s) * fps)
                            new_marks.append({
                                'frame': frame,
                                'note': note
                            })
                    self.marks = new_marks
                    self.update_mark_list()
                    self.draw_timeline_marks()
                QMessageBox.information(self, "成功", "标记已成功导入")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {str(e)}")

    def stop_video(self):
        if self.cap is not None:
            self.is_playing = False
            self.play_btn.setText("播放")
            self.timer.stop()
            self.media_player.stop()  # 停止音频
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.update_frame()

    def toggle_fullscreen(self):
        if hasattr(self, 'fullscreen_window'):
            # 如果已经全屏，则退出全屏
            self.fullscreen_window.close()
            del self.fullscreen_window
            self.fullscreen_btn.setText("全屏")
            return
            
        # 创建全屏窗口
        self.fullscreen_window = QWidget()
        self.fullscreen_window.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.fullscreen_window.setStyleSheet("background-color: black;")
        
        # 创建布局并添加视频标签
        layout = QVBoxLayout(self.fullscreen_window)
        layout.setContentsMargins(0, 0, 0, 0)
        self.fullscreen_label = QLabel()
        self.fullscreen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 设置初始视频帧
        if self.video_label.pixmap():
            self.update_fullscreen_frame()
        
        layout.addWidget(self.fullscreen_label)
        
        # 设置全屏
        self.fullscreen_window.showFullScreen()
        self.fullscreen_btn.setText("退出全屏")
        
        # 重新设置全屏窗口的快捷键
        self.setup_fullscreen_shortcuts()
        
        # 连接事件
        self.fullscreen_window.keyPressEvent = lambda event: self.exit_fullscreen(event)
        self.fullscreen_window.mouseDoubleClickEvent = lambda event: self.exit_fullscreen(event)
        self.fullscreen_window.resizeEvent = lambda event: self.update_fullscreen_frame()

    def setup_fullscreen_shortcuts(self):
        """设置全屏窗口的快捷键"""
        # 空格键播放/暂停
        QShortcut(Qt.Key.Key_Space, self.fullscreen_window).activated.connect(self.toggle_play)
        
        # m键添加标记
        QShortcut(Qt.Key.Key_M, self.fullscreen_window).activated.connect(self.add_mark)
        
        # delete键删除标记
        QShortcut(Qt.Key.Key_Delete, self.fullscreen_window).activated.connect(self.delete_selected_mark)
        
        # 添加上下左右键快捷键
        QShortcut(Qt.Key.Key_Right, self.fullscreen_window).activated.connect(self.jump_to_next_mark)
        QShortcut(Qt.Key.Key_Down, self.fullscreen_window).activated.connect(self.jump_to_next_mark)
        QShortcut(Qt.Key.Key_Left, self.fullscreen_window).activated.connect(self.jump_to_prev_mark)
        QShortcut(Qt.Key.Key_Up, self.fullscreen_window).activated.connect(self.jump_to_prev_mark)
        
        # 添加F键和`键全屏快捷键
        QShortcut(Qt.Key.Key_F, self.fullscreen_window).activated.connect(self.toggle_fullscreen)
        QShortcut(Qt.Key.Key_QuoteLeft, self.fullscreen_window).activated.connect(self.toggle_fullscreen)
        
        # 添加回车键跳转到上个标记
        QShortcut(Qt.Key.Key_Return, self.fullscreen_window).activated.connect(self.jump_to_prev_one_mark)
        
        # 添加R键和Shift键跳转到上个标记的快捷键
        QShortcut(Qt.Key.Key_R, self.fullscreen_window).activated.connect(self.jump_to_prev_one_mark)
        QShortcut(Qt.Key.Key_Shift, self.fullscreen_window).activated.connect(self.jump_to_prev_one_mark)

    def update_fullscreen_frame(self):
        """更新全屏窗口的视频帧"""
        if hasattr(self, 'fullscreen_label') and self.video_label.pixmap():
            self.fullscreen_label.setPixmap(self.video_label.pixmap().scaled(
                self.fullscreen_window.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        
    def exit_fullscreen(self, event):
        # 处理键盘事件
        if hasattr(event, 'key') and event.key() == Qt.Key.Key_Escape:
            self.toggle_fullscreen()
        # 处理鼠标双击事件
        elif isinstance(event, type(event)) and event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggle_fullscreen()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
            self.fullscreen_btn.setText("全屏")
        super().keyPressEvent(event)

    def update_mark_times(self):
        """更新标记时间显示"""
        if self.cap is None or not self.marks:
            return
            
        current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
        current_mark = None
        next_mark = None
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        # 查找当前标记和下一个标记
        for i, mark in enumerate(self.marks):
            if mark['frame'] <= current_frame:
                current_mark = mark
                if i < len(self.marks) - 1:
                    next_mark = self.marks[i + 1]
            else:
                if next_mark is None:
                    next_mark = mark
                break
        
        # 更新显示
        if current_mark:
            self.current_mark_time.setText(self.frame_to_time(current_mark['frame']))
        else:
            self.current_mark_time.setText("--:--:--")
            
        if next_mark:
            self.next_mark_time.setText(self.frame_to_time(next_mark['frame']))
            if current_mark and fps > 0:
                # 计算两个标记之间的时长（精确到毫秒）
                duration_frames = next_mark['frame'] - current_mark['frame']
                duration_seconds = duration_frames / fps
                minutes = int(duration_seconds // 60)
                seconds = int(duration_seconds % 60)
                milliseconds = int((duration_seconds % 1) * 1000)
                self.duration_label.setText(f"{minutes:02}:{seconds:02}.{milliseconds:03}")
            else:
                self.duration_label.setText("00:00.000")
        else:
            self.next_mark_time.setText("--:--:--")
            self.duration_label.setText("00:00.000")

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    player = VideoPlayerWindow()
    player.show()
    sys.exit(app.exec())





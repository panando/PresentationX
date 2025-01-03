import cv2
import json
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QFileDialog, QLabel, QListWidget,
                            QInputDialog, QSlider, QMenu, QSplitter, QMessageBox)
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
        
        # 时间轴
        timeline_container = QWidget()
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(10, 2, 10, 2)  # 进一步减少内边距
        timeline_layout.setSpacing(2)  # 进一步减少间距
        
        # 时间轴和进度显示
        time_display = QHBoxLayout()
        time_display.setSpacing(5)
        
        # 当前时间
        self.current_time_label = QLabel("00:00:00")
        self.current_time_label.setStyleSheet("font-size: 11px; color: #666;")
        time_display.addWidget(self.current_time_label)
        
        # 时间轴
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.sliderPressed.connect(self.on_timeline_pressed)
        self.timeline.sliderReleased.connect(self.on_timeline_released)
        self.timeline.sliderMoved.connect(self.on_timeline_change)
        # 基础样式
        self.timeline.setStyleSheet("""
            QSlider {
                min-height: 12px;
                margin: 2px 8px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #E0E0E0;
                margin: 0px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #9E9E9E;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
        """)
        time_display.addWidget(self.timeline, stretch=1)
        
        # 总时间
        self.total_time_label = QLabel("00:00:00")
        self.total_time_label.setStyleSheet("font-size: 11px; color: #666;")
        time_display.addWidget(self.total_time_label)
        
        # 添加音量控制
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setStyleSheet("""
            QSlider::handle:horizontal {
                background: #4CAF50;
                width: 12px;
                margin: -3px 0;
                border-radius: 6px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #E0E0E0;
                margin: 0px;
                border-radius: 3px;
            }
        """)
        self.volume_slider.valueChanged.connect(self.set_volume)
        time_display.addWidget(self.volume_slider)
        
        timeline_layout.addLayout(time_display)
        
        # 标记容器
        self.marks_container = QWidget()
        self.marks_container.setStyleSheet("background: transparent;")
        timeline_layout.addWidget(self.marks_container)
        
        left_layout.addWidget(timeline_container, stretch=1)  # 时间轴区域占较小空间
        
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
        
        # 标记列表
        self.mark_list = QListWidget()
        self.mark_list.itemDoubleClicked.connect(self.edit_mark)
        
        # 创建容器并添加控件
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.addWidget(QLabel("标记列表"))
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
        
        # 回车键全屏
        self.shortcut_enter = QShortcut(Qt.Key.Key_Return, self)
        self.shortcut_enter.activated.connect(self.toggle_fullscreen)
        
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
        
        # 添加上下左右键快捷键
        self.shortcut_next = QShortcut(Qt.Key.Key_Right, self)
        self.shortcut_next.activated.connect(self.jump_to_next_mark)
        self.shortcut_next = QShortcut(Qt.Key.Key_Down, self)
        self.shortcut_next.activated.connect(self.jump_to_next_mark)
        
        self.shortcut_prev = QShortcut(Qt.Key.Key_Left, self)
        self.shortcut_prev.activated.connect(self.jump_to_prev_mark_with_interval)
        self.shortcut_prev = QShortcut(Qt.Key.Key_Up, self)
        self.shortcut_prev.activated.connect(self.jump_to_prev_mark_with_interval)
        
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.setInterval(33)  # 约30fps
        self.seek_delay = 100  # 100ms的防抖动延迟
        
    def delayed_seek(self):
        """防抖动的延迟跳转"""
        if self.cap is None:
            return
        target_frame = self.timeline.value()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        # 同步音频位置
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            self.media_player.setPosition(int(target_frame / fps * 1000))
        
    def set_volume(self, value):
        """设置音量"""
        self.audio_output.setVolume(value / 100.0)

    def load_video(self):
        try:
            file_name, _ = QFileDialog.getOpenFileName(self, "选择视频文件")
            if file_name:
                self.video_path = file_name
                self.cap = cv2.VideoCapture(file_name)
                # 设置媒体播放器
                self.media_player.setSource(QUrl.fromLocalFile(file_name))
                self.media_player.play()
                self.media_player.pause()  # 先暂停，等待用户点击播放
                
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
                self.media_player.setPosition(int(next_mark['frame'] / self.cap.get(cv2.CAP_PROP_FPS) * 1000))  # 同步音频位置
                self.media_player.play()  # 播放音频
                self.update_frame()
            
    def jump_to_prev_mark(self):
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
            self.media_player.setPosition(int(prev_mark['frame'] / self.cap.get(cv2.CAP_PROP_FPS) * 1000))  # 同步音频位置
            self.media_player.play()  # 播放音频
            self.update_frame()
        elif len(prev_marks) == 1:
            # 只有一个标记时跳转到它
            prev_mark = prev_marks[0]
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, prev_mark['frame'])
            self.is_playing = True
            self.play_btn.setText("暂停")
            self.timer.start()
            self.media_player.setPosition(int(prev_mark['frame'] / self.cap.get(cv2.CAP_PROP_FPS) * 1000))  # 同步音频位置
            self.media_player.play()  # 播放音频
            self.update_frame()

    def jump_to_prev_mark_with_interval(self):
        """500ms内连续按下快捷键跳转到上上个标记"""
        current_time = QDateTime.currentMSecsSinceEpoch()
        if current_time - self.last_prev_key_time < self.prev_key_interval:
            # 如果两次按键间隔小于500ms，跳转到上上个标记
            self.jump_to_prev_mark()
        else:
            # 否则跳转到上一个标记
            current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            prev_marks = [mark for mark in reversed(self.marks) if mark['frame'] < current_frame]
            if prev_marks:
                prev_mark = prev_marks[0]
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, prev_mark['frame'])
                self.is_playing = True
                self.play_btn.setText("暂停")
                self.timer.start()
                self.update_frame()
        
        # 更新最后按键时间
        self.last_prev_key_time = current_time
            
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
        if self.current_frame_cache is not None:
            self.display_frame(self.current_frame_cache)
        # 窗口大小改变时重新绘制标记
        self.draw_timeline_marks()

    def draw_timeline_marks(self):
        # 仅添加标记样式
        mark_style = """
            QSlider::groove:horizontal {
                border-left: 0% solid transparent;
                border-right: 100% solid transparent;
            }
        """
        if self.timeline.maximum() > 0:
            for mark in self.marks:
                position = mark['frame'] / self.timeline.maximum()
                mark_style += f"""
                    QSlider::groove:horizontal {{
                        border-left: {position * 100}% solid transparent;
                        border-right: {(1 - position) * 100}% solid transparent;
                    }}
                    QSlider::add-page:horizontal {{
                        border-left: 2px solid #FF4081;
                        margin-left: -2px;
                    }}
                """
        
        # 保留现有样式并添加标记样式
        self.timeline.setStyleSheet(self.timeline.styleSheet() + mark_style)
        
        # 清除旧标记
        if hasattr(self, 'mark_labels'):
            for label in self.mark_labels:
                label.deleteLater()
        self.mark_labels = []
        
        # 在时间轴下方添加标记
        for mark in self.marks:
            # 获取时间轴相对位置和宽度
            timeline_pos = self.timeline.pos()
            timeline_width = self.timeline.width()
            
            # 设置标记容器位置和大小
            self.marks_container.setGeometry(
                timeline_pos.x(),  # 与时间轴对齐
                timeline_pos.y(),  # 与时间轴对齐
                timeline_width,  # 与时间轴同宽
                self.timeline.height()  # 与时间轴同高
            )
            self.marks_container.setStyleSheet("background: transparent;")
            
            # 计算标记位置（基于时间轴宽度）
            position = (mark['frame'] / self.timeline.maximum()) * timeline_width
            
            # 创建标记
            label = QLabel("▼", self.marks_container)
            label.setStyleSheet("color: #FF4081; font-size: 10px;")
            label.move(
                int(position - 6),  # 调整标记位置使其与滑块对齐
                5  # 紧贴时间轴下方
            )
            label.show()
            self.mark_labels.append(label)

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
        QShortcut(Qt.Key.Key_Left, self.fullscreen_window).activated.connect(self.jump_to_prev_mark_with_interval)
        QShortcut(Qt.Key.Key_Up, self.fullscreen_window).activated.connect(self.jump_to_prev_mark_with_interval)
        
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

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    player = VideoPlayerWindow()
    player.show()
    sys.exit(app.exec())

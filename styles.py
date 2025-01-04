# 时间轴基础样式
TIMELINE_STYLE = """
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
"""

# 音量控制样式
VOLUME_SLIDER_STYLE = """
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
"""

# 时间显示样式
TIME_LABEL_STYLE = "font-size: 11px; color: #666;"

# 标记容器样式
MARKS_CONTAINER_STYLE = "background: transparent;"

# 标记样式
MARK_LABEL_STYLE = "color: #FF4081; font-size: 10px;"

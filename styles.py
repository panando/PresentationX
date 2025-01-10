# 时间轴基础样式 - 修复CSS注释语法
TIMELINE_STYLE = """
    QSlider {
        min-height: 12px;
        margin: 2px 0px;        /* 移除左右边距 */
        padding: 4px 8px;       /* 改用内边距控制间距 */
        border: 1px solid #AAAAAA;
        border-radius: 5px;
        background: transparent;
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
TIME_LABEL_STYLE = """
    font-size: 11px;
    color: #666;
    padding: 0 4px;
    min-width: 60px;
    text-align: center;
"""

# 修改标记样式，调整大小和边距
MARK_LABEL_STYLE = """
    QLabel {
        color: #FF4081;
        font-size: 8px;
        background: transparent;
        padding: 0;
        margin: 0;
        border: none;
    }
"""

# 视频显示区域样式
VIDEO_DISPLAY_STYLE = """
    QLabel {
        background-color: #000000;
        border: 2px solid #E0E0E0;
        border-radius: 8px;
        padding: 10px;
        margin: 10px;
        box-shadow: 0px 0px 10px rgba(76, 175, 80, 0.5);
    }
"""

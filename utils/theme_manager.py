import ctypes
import os
import re
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon, QPen
from PyQt6.QtCore import Qt, QPoint

BASE_THEME_TEMPLATE = """
QMainWindow, QDialog {{
    background-color: {main_bg};
    color: {main_fg};
}}
QWidget {{
    background-color: {main_bg};
    color: {main_fg};
}}
QMenuBar {{
    background-color: {menubar_bg};
    color: {menubar_fg};
    padding: 2px 4px;
}}
QMenuBar::item {{
    background-color: transparent;
    padding: 4px 8px;
    margin: 1px;
    border-radius: 3px;
}}
QMenuBar::item:selected {{
    background-color: {menubar_item_selected_bg};
}}
QMenu {{
    background-color: {menu_bg};
    color: {menu_fg};
    border: 1px solid {menu_border};
    padding: 4px;
}}
QMenu::item {{
    background-color: transparent;
    padding: 6px 36px 6px 24px;
    border-radius: 3px;
    margin: 1px 2px;
}}
QMenu::item:selected {{
    background-color: {menu_item_selected_bg};
}}
QMenu::item:disabled {{
    color: #777777;
    background-color: transparent;
}}
QMenu::separator {{
    height: 1px;
    background-color: {menu_border};
    margin: 4px 6px;
}}
QTreeWidget {{
    background-color: {tree_bg};
    color: {tree_fg};
    border: 1px solid {tree_border};
    outline: none;
}}
QTreeWidget::item {{
    outline: none;
}}
QTreeWidget::item:selected {{
    background-color: {tree_item_selected_bg};
    color: #ffffff;
    border: none;
    outline: none;
}}
QTreeWidget::item:hover {{
    background-color: {tree_item_hover_bg};
}}
QTextEdit, QPlainTextEdit {{
    background-color: {editor_bg};
    color: {editor_fg};
    border: 1px solid {editor_border};
    selection-background-color: {editor_selection_bg};
}}
QTabWidget::pane {{
    border: 1px solid {tab_pane_border};
    background-color: {tab_pane_bg};
    border-radius: 4px;
}}
QTabBar::tab {{
    background-color: {tab_bg};
    color: {tab_fg};
    padding: 6px 12px;
    border: 1px solid {tab_border};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 3px;
}}
QTabBar::tab:hover {{
    background-color: {tab_hover_bg};
    color: {tab_hover_fg};
}}
QTabBar::tab:selected {{
    background-color: {tab_selected_bg};
    color: {tab_selected_fg};
    border-top: 2px solid {tab_selected_indicator};
    border-bottom: 1px solid {tab_selected_bg};
    font-weight: bold;
}}
QPushButton#btn_add_core_card {{
    background-color: {card_add_btn_bg};
    color: {card_add_btn_fg};
    border: 1px dashed {card_add_btn_border};
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: bold;
}}
QPushButton#btn_add_core_card:hover {{
    background-color: {card_add_btn_hover_bg};
    border: 1px solid {card_add_btn_hover_border};
    color: {card_add_btn_hover_fg};
}}
QPushButton#btn_add_core_card:pressed {{
    background-color: {card_add_btn_pressed_bg};
}}
QToolBar {{
    background-color: {toolbar_bg};
    border: none;
}}
QPushButton {{
    background-color: {btn_bg};
    color: {btn_fg};
    border: 1px solid {btn_border};
    padding: 4px 8px;
    border-radius: 4px;
}}
QPushButton:hover {{
    background-color: {btn_hover_bg};
}}
QPushButton:checked {{
    background-color: {btn_checked_bg};
}}
QLabel {{
    color: {label_fg};
}}
QLineEdit, QComboBox {{
    background-color: {input_bg};
    color: {input_fg};
    border: 1px solid {input_border};
    padding: 2px 4px;
}}
QRadioButton {{
    color: {main_fg};
    spacing: 8px;
    background-color: transparent;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 9px;
    border: 2px solid {radio_border};
    background-color: {input_bg};
}}
QRadioButton::indicator:hover {{
    border-color: {accent};
}}
QRadioButton::indicator:checked {{
    border: 2px solid {accent};
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 {accent}, stop:0.48 {accent}, stop:0.52 {input_bg}, stop:1 {input_bg});
}}
QRadioButton::indicator:disabled {{
    border-color: #555555;
    background-color: #2a2a2a;
}}
QCheckBox {{
    color: {main_fg};
    spacing: 8px;
    background-color: transparent;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 2px solid {checkbox_border};
    background-color: {input_bg};
}}
QCheckBox::indicator:hover {{
    border-color: {accent};
}}
QCheckBox::indicator:checked {{
    border: 2px solid {accent};
    background-color: {accent};
    image: url('{checkbox_check_icon}');
}}
QCheckBox::indicator:disabled {{
    border-color: #555555;
    background-color: #2a2a2a;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: {input_bg};
    color: {input_fg};
    border: 1px solid {input_border};
    border-radius: 4px;
    padding: 3px 6px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {accent};
}}
QGroupBox {{
    color: {main_fg};
    border: 1px solid {tab_pane_border};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {accent};
}}
QScrollBar:vertical {{
    background: {main_bg};
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {btn_bg};
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: {btn_hover_bg};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {main_bg};
    height: 10px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: {btn_bg};
    min-width: 20px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {btn_hover_bg};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QTableWidget {{
    background-color: {table_bg};
    color: {table_fg};
    gridline-color: {table_grid};
    border: 1px solid {table_border};
}}
QHeaderView::section {{
    background-color: {header_bg};
    color: {header_fg};
    padding: 4px;
    border: 1px solid {header_border};
}}
QTableCornerButton::section {{
    background-color: {table_corner_bg};
}}
QStatusBar, QWidget#statusBar {{
    background-color: {status_bar_bg};
    border-top: 1px solid {status_bar_border};
}}
QStatusBar QPushButton, QWidget#statusBar QPushButton {{
    background-color: {status_btn_bg};
    color: {status_btn_fg};
    border: 1px solid {status_btn_border};
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 11px;
}}
QStatusBar QPushButton:hover, QWidget#statusBar QPushButton:hover {{
    background-color: {status_btn_hover_bg};
}}
QStatusBar QLabel, QWidget#statusBar QLabel {{
    color: {status_label_fg};
    background-color: transparent;
}}
QListWidget#trash_list_widget {{
    background-color: {trash_list_bg};
    color: {trash_list_fg};
    border: 1px solid {trash_list_border};
    outline: none;
}}
QListWidget#trash_list_widget::item:selected {{
    background-color: {trash_item_selected_bg};
    color: #ffffff;
}}
QListWidget#trash_list_widget::item:hover {{
    background-color: {trash_item_hover_bg};
}}
QLabel#lbl_current_file {{
    padding: 5px;
    border: 1px solid {current_file_lbl_border};
    background-color: {current_file_lbl_bg};
    color: {current_file_lbl_fg};
}}
QLabel#lbl_focus_banner {{
    background-color: {focus_banner_bg};
    color: {focus_banner_fg};
    font-size: 11px;
    padding: 4px 10px;
    border-radius: 4px;
    border: 1px solid {focus_banner_border};
}}
QPushButton#btn_save_scene_info {{
    background-color: {scene_btn_bg};
    color: {scene_btn_fg};
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    font-weight: bold;
}}
QPushButton#btn_save_scene_info:hover {{
    background-color: {scene_btn_hover_bg};
}}
QPushButton#btn_toggle_left, QPushButton#btn_toggle_right, QPushButton#btn_trash {{
    background-color: transparent;
    border: none;
    border-radius: 3px;
}}
QPushButton#btn_toggle_left:hover, QPushButton#btn_toggle_right:hover, QPushButton#btn_trash:hover {{
    background-color: {icon_btn_hover_bg};
}}
"""

THEME_COLORS = {
    "default": {
        "main_bg": "#1e1e1e", "main_fg": "#e3e3e3",
        "menubar_bg": "#2d2d2d", "menubar_fg": "#e3e3e3", "menubar_item_selected_bg": "#3d3d3d",
        "menu_bg": "#2d2d2d", "menu_fg": "#e3e3e3", "menu_border": "#3d3d3d", "menu_item_selected_bg": "#3d3d3d",
        "tree_bg": "#252526", "tree_fg": "#e3e3e3", "tree_border": "#3d3d3d", "tree_item_selected_bg": "#094771", "tree_item_hover_bg": "#2a2d2e",
        "editor_bg": "#1e1e1e", "editor_fg": "#e3e3e3", "editor_border": "#3d3d3d", "editor_selection_bg": "#264f78",
        "tab_pane_bg": "#1e1e1e", "tab_pane_border": "#383a3f",
        "tab_bg": "#282a2e", "tab_fg": "#b8c0cc", "tab_border": "#383a3f",
        "tab_hover_bg": "#34383f", "tab_hover_fg": "#ffffff",
        "tab_selected_bg": "#1e1e1e", "tab_selected_fg": "#58a6ff", "tab_selected_indicator": "#58a6ff",
        "card_add_btn_bg": "rgba(88, 166, 255, 0.10)", "card_add_btn_fg": "#79c0ff", "card_add_btn_border": "rgba(88, 166, 255, 0.40)",
        "card_add_btn_hover_bg": "rgba(88, 166, 255, 0.20)", "card_add_btn_hover_border": "#58a6ff", "card_add_btn_hover_fg": "#ffffff",
        "card_add_btn_pressed_bg": "rgba(88, 166, 255, 0.30)",
        "toolbar_bg": "#2d2d2d",
        "btn_bg": "#3d3d3d", "btn_fg": "#e3e3e3", "btn_border": "#555555", "btn_hover_bg": "#4d4d4d", "btn_checked_bg": "#094771",
        "label_fg": "#e3e3e3",
        "input_bg": "#3c3c3c", "input_fg": "#e3e3e3", "input_border": "#555555",
        "table_bg": "#252526", "table_fg": "#e3e3e3", "table_grid": "#3d3d3d", "table_border": "#3d3d3d",
        "header_bg": "#2d2d2d", "header_fg": "#e3e3e3", "header_border": "#3d3d3d", "table_corner_bg": "#2d2d2d",
        "status_bar_bg": "#2d2d2d", "status_bar_border": "#3d3d3d",
        "status_btn_bg": "#3d3d3d", "status_btn_fg": "#e3e3e3", "status_btn_border": "#555555", "status_btn_hover_bg": "#4d4d4d",
        "status_label_fg": "#e3e3e3",
        "trash_list_bg": "#252526", "trash_list_fg": "#e3e3e3", "trash_list_border": "#3d3d3d",
        "trash_item_selected_bg": "#094771", "trash_item_hover_bg": "#2a2d2e",
        "scene_btn_bg": "#0e639c", "scene_btn_fg": "#ffffff", "scene_btn_hover_bg": "#1177bb",
        "focus_banner_bg": "rgba(30, 30, 30, 180)", "focus_banner_fg": "#888888", "focus_banner_border": "#444444",
        "current_file_lbl_bg": "#2d2d2d", "current_file_lbl_fg": "#e3e3e3", "current_file_lbl_border": "#555555",
        "icon_btn_hover_bg": "#3d3d3d"
    },
    "green": {
        "main_bg": "#121b15", "main_fg": "#e0ede5",
        "menubar_bg": "#1a261e", "menubar_fg": "#e0ede5", "menubar_item_selected_bg": "#26392d",
        "menu_bg": "#1a261e", "menu_fg": "#e0ede5", "menu_border": "#26392d", "menu_item_selected_bg": "#26392d",
        "tree_bg": "#16211a", "tree_fg": "#e0ede5", "tree_border": "#26392d", "tree_item_selected_bg": "#1f4c32", "tree_item_hover_bg": "#1e2e24",
        "editor_bg": "#121b15", "editor_fg": "#e0ede5", "editor_border": "#26392d", "editor_selection_bg": "#2c5e43",
        "tab_pane_bg": "#121b15", "tab_pane_border": "#26392d",
        "tab_bg": "#1c2b21", "tab_fg": "#b2d8be", "tab_border": "#26392d",
        "tab_hover_bg": "#253a2d", "tab_hover_fg": "#ffffff",
        "tab_selected_bg": "#121b15", "tab_selected_fg": "#5cdb95", "tab_selected_indicator": "#5cdb95",
        "card_add_btn_bg": "rgba(92, 219, 149, 0.10)", "card_add_btn_fg": "#7ee787", "card_add_btn_border": "rgba(92, 219, 149, 0.40)",
        "card_add_btn_hover_bg": "rgba(92, 219, 149, 0.20)", "card_add_btn_hover_border": "#5cdb95", "card_add_btn_hover_fg": "#ffffff",
        "card_add_btn_pressed_bg": "rgba(92, 219, 149, 0.30)",
        "toolbar_bg": "#1a261e",
        "btn_bg": "#26392d", "btn_fg": "#e0ede5", "btn_border": "#35523d", "btn_hover_bg": "#35523d", "btn_checked_bg": "#1f4c32",
        "label_fg": "#e0ede5",
        "input_bg": "#2a3f32", "input_fg": "#e0ede5", "input_border": "#35523d",
        "table_bg": "#16211a", "table_fg": "#e0ede5", "table_grid": "#26392d", "table_border": "#26392d",
        "header_bg": "#1a261e", "header_fg": "#e0ede5", "header_border": "#26392d", "table_corner_bg": "#1a261e",
        "status_bar_bg": "#1a261e", "status_bar_border": "#26392d",
        "status_btn_bg": "#26392d", "status_btn_fg": "#e0ede5", "status_btn_border": "#35523d", "status_btn_hover_bg": "#35523d",
        "status_label_fg": "#e0ede5",
        "trash_list_bg": "#16211a", "trash_list_fg": "#e0ede5", "trash_list_border": "#26392d",
        "trash_item_selected_bg": "#1f4c32", "trash_item_hover_bg": "#1e2e24",
        "scene_btn_bg": "#1f4c32", "scene_btn_fg": "#ffffff", "scene_btn_hover_bg": "#2d6a47",
        "focus_banner_bg": "rgba(22, 33, 26, 180)", "focus_banner_fg": "#7a9e86", "focus_banner_border": "#26392d",
        "current_file_lbl_bg": "#1a261e", "current_file_lbl_fg": "#e0ede5", "current_file_lbl_border": "#26392d",
        "icon_btn_hover_bg": "#26392d"
    },
    "celadon": {
        "main_bg": "#111b21", "main_fg": "#cbe0e8",
        "menubar_bg": "#1a2932", "menubar_fg": "#cbe0e8", "menubar_item_selected_bg": "#273d4a",
        "menu_bg": "#1a2932", "menu_fg": "#cbe0e8", "menu_border": "#273d4a", "menu_item_selected_bg": "#273d4a",
        "tree_bg": "#15222a", "tree_fg": "#cbe0e8", "tree_border": "#273d4a", "tree_item_selected_bg": "#1d4e6e", "tree_item_hover_bg": "#1d2f3a",
        "editor_bg": "#111b21", "editor_fg": "#cbe0e8", "editor_border": "#273d4a", "editor_selection_bg": "#2a5f80",
        "tab_pane_bg": "#111b21", "tab_pane_border": "#273d4a",
        "tab_bg": "#1c2d38", "tab_fg": "#b2d4e3", "tab_border": "#273d4a",
        "tab_hover_bg": "#263e4d", "tab_hover_fg": "#ffffff",
        "tab_selected_bg": "#111b21", "tab_selected_fg": "#4fc3f7", "tab_selected_indicator": "#4fc3f7",
        "card_add_btn_bg": "rgba(79, 195, 247, 0.10)", "card_add_btn_fg": "#64b5f6", "card_add_btn_border": "rgba(79, 195, 247, 0.40)",
        "card_add_btn_hover_bg": "rgba(79, 195, 247, 0.20)", "card_add_btn_hover_border": "#4fc3f7", "card_add_btn_hover_fg": "#ffffff",
        "card_add_btn_pressed_bg": "rgba(79, 195, 247, 0.30)",
        "toolbar_bg": "#1a2932",
        "btn_bg": "#273d4a", "btn_fg": "#cbe0e8", "btn_border": "#2e4d61", "btn_hover_bg": "#2e4d61", "btn_checked_bg": "#1d4e6e",
        "label_fg": "#cbe0e8",
        "input_bg": "#2d4655", "input_fg": "#cbe0e8", "input_border": "#2e4d61",
        "table_bg": "#15222a", "table_fg": "#cbe0e8", "table_grid": "#273d4a", "table_border": "#273d4a",
        "header_bg": "#1a2932", "header_fg": "#cbe0e8", "header_border": "#273d4a", "table_corner_bg": "#1a2932",
        "status_bar_bg": "#1a2932", "status_bar_border": "#273d4a",
        "status_btn_bg": "#273d4a", "status_btn_fg": "#cbe0e8", "status_btn_border": "#2e4d61", "status_btn_hover_bg": "#2e4d61",
        "status_label_fg": "#cbe0e8",
        "trash_list_bg": "#15222a", "trash_list_fg": "#cbe0e8", "trash_list_border": "#273d4a",
        "trash_item_selected_bg": "#1d4e6e", "trash_item_hover_bg": "#1d2f3a",
        "scene_btn_bg": "#1d4e6e", "scene_btn_fg": "#ffffff", "scene_btn_hover_bg": "#246691",
        "focus_banner_bg": "rgba(21, 34, 42, 180)", "focus_banner_fg": "#789cae", "focus_banner_border": "#273d4a",
        "current_file_lbl_bg": "#1a2932", "current_file_lbl_fg": "#cbe0e8", "current_file_lbl_border": "#273d4a",
        "icon_btn_hover_bg": "#273d4a"
    },
    "sepia": {
        "main_bg": "#2e2620", "main_fg": "#dfd5cc",
        "menubar_bg": "#382e27", "menubar_fg": "#dfd5cc", "menubar_item_selected_bg": "#4a3d34",
        "menu_bg": "#382e27", "menu_fg": "#dfd5cc", "menu_border": "#4a3d34", "menu_item_selected_bg": "#4a3d34",
        "tree_bg": "#251e19", "tree_fg": "#dfd5cc", "tree_border": "#4a3d34", "tree_item_selected_bg": "#6d4c3d", "tree_item_hover_bg": "#3d322a",
        "editor_bg": "#2e2620", "editor_fg": "#dfd5cc", "editor_border": "#4a3d34", "editor_selection_bg": "#5c4333",
        "tab_pane_bg": "#2e2620", "tab_pane_border": "#4a3d34",
        "tab_bg": "#3d332a", "tab_fg": "#d9cbbe", "tab_border": "#4a3d34",
        "tab_hover_bg": "#504237", "tab_hover_fg": "#ffffff",
        "tab_selected_bg": "#2e2620", "tab_selected_fg": "#f4b97f", "tab_selected_indicator": "#f4b97f",
        "card_add_btn_bg": "rgba(244, 185, 127, 0.12)", "card_add_btn_fg": "#f4b97f", "card_add_btn_border": "rgba(244, 185, 127, 0.40)",
        "card_add_btn_hover_bg": "rgba(244, 185, 127, 0.22)", "card_add_btn_hover_border": "#f4b97f", "card_add_btn_hover_fg": "#ffffff",
        "card_add_btn_pressed_bg": "rgba(244, 185, 127, 0.32)",
        "toolbar_bg": "#382e27",
        "btn_bg": "#4a3d34", "btn_fg": "#dfd5cc", "btn_border": "#5c4c40", "btn_hover_bg": "#5c4c40", "btn_checked_bg": "#6d4c3d",
        "label_fg": "#dfd5cc",
        "input_bg": "#382e27", "input_fg": "#dfd5cc", "input_border": "#5c4c40",
        "table_bg": "#251e19", "table_fg": "#dfd5cc", "table_grid": "#4a3d34", "table_border": "#4a3d34",
        "header_bg": "#382e27", "header_fg": "#dfd5cc", "header_border": "#4a3d34", "table_corner_bg": "#382e27",
        "status_bar_bg": "#382e27", "status_bar_border": "#4a3d34",
        "status_btn_bg": "#4a3d34", "status_btn_fg": "#dfd5cc", "status_btn_border": "#5c4c40", "status_btn_hover_bg": "#5c4c40",
        "status_label_fg": "#dfd5cc",
        "trash_list_bg": "#251e19", "trash_list_fg": "#dfd5cc", "trash_list_border": "#4a3d34",
        "trash_item_selected_bg": "#6d4c3d", "trash_item_hover_bg": "#3d322a",
        "scene_btn_bg": "#6d4c3d", "scene_btn_fg": "#ffffff", "scene_btn_hover_bg": "#8a614e",
        "focus_banner_bg": "rgba(37, 30, 25, 180)", "focus_banner_fg": "#a89587", "focus_banner_border": "#4a3d34",
        "current_file_lbl_bg": "#382e27", "current_file_lbl_fg": "#dfd5cc", "current_file_lbl_border": "#4a3d34",
        "icon_btn_hover_bg": "#4a3d34"
    },
    "polar": {
        "main_bg": "#1d212a", "main_fg": "#d8dee9",
        "menubar_bg": "#242933", "menubar_fg": "#d8dee9", "menubar_item_selected_bg": "#3b4252",
        "menu_bg": "#242933", "menu_fg": "#d8dee9", "menu_border": "#3b4252", "menu_item_selected_bg": "#3b4252",
        "tree_bg": "#181b22", "tree_fg": "#d8dee9", "tree_border": "#3b4252", "tree_item_selected_bg": "#434c5e", "tree_item_hover_bg": "#2e3440",
        "editor_bg": "#1d212a", "editor_fg": "#d8dee9", "editor_border": "#3b4252", "editor_selection_bg": "#434c5e",
        "tab_pane_bg": "#1d212a", "tab_pane_border": "#3b4252",
        "tab_bg": "#2b313e", "tab_fg": "#c5d0e0", "tab_border": "#3b4252",
        "tab_hover_bg": "#394254", "tab_hover_fg": "#ffffff",
        "tab_selected_bg": "#1d212a", "tab_selected_fg": "#88c0d0", "tab_selected_indicator": "#88c0d0",
        "card_add_btn_bg": "rgba(136, 192, 208, 0.12)", "card_add_btn_fg": "#88c0d0", "card_add_btn_border": "rgba(136, 192, 208, 0.40)",
        "card_add_btn_hover_bg": "rgba(136, 192, 208, 0.22)", "card_add_btn_hover_border": "#88c0d0", "card_add_btn_hover_fg": "#ffffff",
        "card_add_btn_pressed_bg": "rgba(136, 192, 208, 0.32)",
        "toolbar_bg": "#242933",
        "btn_bg": "#3b4252", "btn_fg": "#d8dee9", "btn_border": "#4c566a", "btn_hover_bg": "#4c566a", "btn_checked_bg": "#81a1c1",
        "label_fg": "#d8dee9",
        "input_bg": "#2e3440", "input_fg": "#d8dee9", "input_border": "#4c566a",
        "table_bg": "#181b22", "table_fg": "#d8dee9", "table_grid": "#3b4252", "table_border": "#3b4252",
        "header_bg": "#242933", "header_fg": "#d8dee9", "header_border": "#3b4252", "table_corner_bg": "#242933",
        "status_bar_bg": "#242933", "status_bar_border": "#3b4252",
        "status_btn_bg": "#3b4252", "status_btn_fg": "#d8dee9", "status_btn_border": "#4c566a", "status_btn_hover_bg": "#4c566a",
        "status_label_fg": "#d8dee9",
        "trash_list_bg": "#181b22", "trash_list_fg": "#d8dee9", "trash_list_border": "#3b4252",
        "trash_item_selected_bg": "#434c5e", "trash_item_hover_bg": "#2e3440",
        "scene_btn_bg": "#434c5e", "scene_btn_fg": "#ffffff", "scene_btn_hover_bg": "#556077",
        "focus_banner_bg": "rgba(24, 27, 34, 180)", "focus_banner_fg": "#7e889b", "focus_banner_border": "#3b4252",
        "current_file_lbl_bg": "#242933", "current_file_lbl_fg": "#d8dee9", "current_file_lbl_border": "#3b4252",
        "icon_btn_hover_bg": "#3b4252"
    },
    "forest": {
        "main_bg": "#151c1a", "main_fg": "#d1dedb",
        "menubar_bg": "#1d2624", "menubar_fg": "#d1dedb", "menubar_item_selected_bg": "#2b3834",
        "menu_bg": "#1d2624", "menu_fg": "#d1dedb", "menu_border": "#2b3834", "menu_item_selected_bg": "#2b3834",
        "tree_bg": "#101514", "tree_fg": "#d1dedb", "tree_border": "#2b3834", "tree_item_selected_bg": "#324d45", "tree_item_hover_bg": "#202c29",
        "editor_bg": "#151c1a", "editor_fg": "#d1dedb", "editor_border": "#2b3834", "editor_selection_bg": "#2f4f46",
        "tab_pane_bg": "#151c1a", "tab_pane_border": "#2b3834",
        "tab_bg": "#202c29", "tab_fg": "#bad0cb", "tab_border": "#2b3834",
        "tab_hover_bg": "#2b3b37", "tab_hover_fg": "#ffffff",
        "tab_selected_bg": "#151c1a", "tab_selected_fg": "#69f0ae", "tab_selected_indicator": "#69f0ae",
        "card_add_btn_bg": "rgba(105, 240, 174, 0.10)", "card_add_btn_fg": "#69f0ae", "card_add_btn_border": "rgba(105, 240, 174, 0.40)",
        "card_add_btn_hover_bg": "rgba(105, 240, 174, 0.20)", "card_add_btn_hover_border": "#69f0ae", "card_add_btn_hover_fg": "#ffffff",
        "card_add_btn_pressed_bg": "rgba(105, 240, 174, 0.30)",
        "toolbar_bg": "#1d2624",
        "btn_bg": "#2b3834", "btn_fg": "#d1dedb", "btn_border": "#3a4d47", "btn_hover_bg": "#3a4d47", "btn_checked_bg": "#406b60",
        "label_fg": "#d1dedb",
        "input_bg": "#1d2624", "input_fg": "#d1dedb", "input_border": "#3a4d47",
        "table_bg": "#101514", "table_fg": "#d1dedb", "table_grid": "#2b3834", "table_border": "#2b3834",
        "header_bg": "#1d2624", "header_fg": "#d1dedb", "header_border": "#2b3834", "table_corner_bg": "#1d2624",
        "status_bar_bg": "#1d2624", "status_bar_border": "#2b3834",
        "status_btn_bg": "#2b3834", "status_btn_fg": "#d1dedb", "status_btn_border": "#3a4d47", "status_btn_hover_bg": "#3a4d47",
        "status_label_fg": "#d1dedb",
        "trash_list_bg": "#101514", "trash_list_fg": "#d1dedb", "trash_list_border": "#2b3834",
        "trash_item_selected_bg": "#324d45", "trash_item_hover_bg": "#202c29",
        "scene_btn_bg": "#324d45", "scene_btn_fg": "#ffffff", "scene_btn_hover_bg": "#3f6258",
        "focus_banner_bg": "rgba(16, 21, 20, 180)", "focus_banner_fg": "#758d86", "focus_banner_border": "#2b3834",
        "current_file_lbl_bg": "#1d2624", "current_file_lbl_fg": "#d1dedb", "current_file_lbl_border": "#2b3834",
        "icon_btn_hover_bg": "#2b3834"
    }
}

class ThemeManager:
    THEME_NAME_MAP = {
        "預設深色模式（Dark mode）": "default",
        "預設深色": "default",
        "綠影風格": "green",
        "青瓷風格": "celadon",
        "暮茶風格": "sepia",
        "極地夜空": "polar",
        "暗影森林": "forest",
        "default": "default",
        "green": "green",
        "celadon": "celadon",
        "sepia": "sepia",
        "polar": "polar",
        "forest": "forest",
    }

    @staticmethod
    def _get_checkmark_icon_path():
        icon_path = os.path.abspath("resources/icons/check_white.png").replace("\\", "/")
        if not os.path.exists(icon_path):
            os.makedirs(os.path.dirname(icon_path), exist_ok=True)
            p = QPixmap(16, 16)
            p.fill(Qt.GlobalColor.transparent)
            pt = QPainter(p)
            pt.setRenderHint(QPainter.RenderHint.Antialiasing)
            pt.setPen(QPen(QColor("#ffffff"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            pt.drawLine(3, 8, 6, 12)
            pt.drawLine(6, 12, 13, 4)
            pt.end()
            p.save(icon_path)
        return icon_path

    @staticmethod
    def get_theme_colors(theme_name):
        base_colors = THEME_COLORS.get(theme_name, THEME_COLORS["default"])
        colors = dict(base_colors)
        if "accent" not in colors:
            colors["accent"] = colors.get("tab_selected_indicator", "#58a6ff")
        if "radio_border" not in colors:
            colors["radio_border"] = "#858d98"
        if "checkbox_border" not in colors:
            colors["checkbox_border"] = "#858d98"
        if "subtext_color" not in colors:
            colors["subtext_color"] = "#a0aec0"
        colors["checkbox_check_icon"] = ThemeManager._get_checkmark_icon_path()
        return colors

    @staticmethod
    def get_theme_qss(theme_name):
        colors = ThemeManager.get_theme_colors(theme_name)
        return BASE_THEME_TEMPLATE.format(**colors)

    @staticmethod
    def apply_theme_to_dialog(dialog, parent=None):
        """為對話框自動套用對應主題與縮放樣式。"""
        theme_name = "default"
        if parent and hasattr(parent, "current_theme"):
            theme_name = parent.current_theme
        elif hasattr(dialog, "parent") and dialog.parent() and hasattr(dialog.parent(), "current_theme"):
            theme_name = dialog.parent().current_theme
        
        scale = getattr(parent, "scale_factor", 1.0) if parent else getattr(dialog, "scale_factor", 1.0)
        dialog.scale_factor = scale
        from utils.font_manager import FontManager
        dialog.setFont(FontManager.get_font(size=int(9 * scale)))
        qss = ThemeManager.get_theme_qss(theme_name)
        scaled_qss = ThemeManager.scale_qss(qss, scale)
        dialog.setStyleSheet(scaled_qss)

    @staticmethod
    def scale_qss(qss_string, scale):
        if scale == 1.0:
            return qss_string

        def replace_px(match):
            val = int(match.group(1))
            return f"{max(1, int(round(val * scale)))}px"

        return re.sub(r'(?<![\w-])(\d+)px', replace_px, qss_string)

def set_window_dark_mode(hwnd, caption_color=0x1e1e1e, text_color=0xe3e3e3):
    try:
        dwm = ctypes.windll.dwmapi
        rendering = ctypes.c_int(1)
        dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(rendering), ctypes.sizeof(rendering))
        dwm.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(rendering), ctypes.sizeof(rendering))
        
        c_color = ctypes.c_int(caption_color)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(c_color), ctypes.sizeof(c_color))
        
        t_color = ctypes.c_int(text_color)
        dwm.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(t_color), ctypes.sizeof(t_color))
    except Exception:
        pass

def create_custom_icon(icon_type, color_hex="#e3e3e3", scale_factor=1.0, direction=None):
    size = int(16 * scale_factor)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = painter.pen()
    pen.setColor(QColor(color_hex))
    pen.setWidthF((2.0 if icon_type == "arrow" else 1.5) * scale_factor)
    painter.setPen(pen)
    
    s = scale_factor
    if icon_type == "folder":
        painter.drawPolyline([
            QPoint(int(2 * s), int(5 * s)), 
            QPoint(int(2 * s), int(2 * s)), 
            QPoint(int(6 * s), int(2 * s)), 
            QPoint(int(8 * s), int(5 * s))
        ])
        painter.drawRect(int(2 * s), int(5 * s), int(12 * s), int(8 * s))
    elif icon_type == "file":
        painter.drawPolygon([
            QPoint(int(3 * s), int(1 * s)), 
            QPoint(int(10 * s), int(1 * s)), 
            QPoint(int(13 * s), int(4 * s)), 
            QPoint(int(13 * s), int(14 * s)), 
            QPoint(int(3 * s), int(14 * s))
        ])
        painter.drawLine(int(10 * s), int(1 * s), int(10 * s), int(4 * s))
        painter.drawLine(int(10 * s), int(4 * s), int(13 * s), int(4 * s))
    elif icon_type == "arrow":
        if direction == "left":
            painter.drawPolyline([
                QPoint(int(10 * s), int(4 * s)), 
                QPoint(int(5 * s), int(8 * s)), 
                QPoint(int(10 * s), int(12 * s))
            ])
        else:
            painter.drawPolyline([
                QPoint(int(6 * s), int(4 * s)), 
                QPoint(int(11 * s), int(8 * s)), 
                QPoint(int(6 * s), int(12 * s))
            ])
    elif icon_type == "trash":
        painter.drawLine(int(2 * s), int(3 * s), int(14 * s), int(3 * s))
        painter.drawPolyline([
            QPoint(int(6 * s), int(3 * s)), 
            QPoint(int(6 * s), int(1 * s)), 
            QPoint(int(10 * s), int(1 * s)), 
            QPoint(int(10 * s), int(3 * s))
        ])
        painter.drawPolygon([
            QPoint(int(4 * s), int(3 * s)), 
            QPoint(int(5 * s), int(14 * s)), 
            QPoint(int(11 * s), int(14 * s)), 
            QPoint(int(12 * s), int(3 * s))
        ])
        painter.drawLine(int(6 * s), int(5 * s), int(6 * s), int(12 * s))
        painter.drawLine(int(10 * s), int(5 * s), int(10 * s), int(12 * s))
        
    painter.end()
    return QIcon(pixmap)

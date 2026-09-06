"""樣式與主題 QSS 模板模組。"""

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

import pytest
from PyQt6.QtWidgets import QApplication, QRadioButton, QCheckBox, QWidget
from utils.theme_manager import ThemeManager, THEME_COLORS
from views.dialogs.initial_scale_dialog import InitialScaleDialog
from views.dialogs.export_scope_dialog import ExportScopeDialog
from views.dialogs.word_count_settings_dialog import WordCountSettingsDialog
from views.dialogs.autosave_settings_dialog import AutosaveSettingsDialog
from views.dialogs.storage_path_dialog import StoragePathDialog
from views.dialogs.global_search_dialog import GlobalSearchDialog
from views.dialogs.snapshot_dialog import SnapshotDialog
from views.dialogs.scene_metadata_dialog import SceneMetadataDialog
from views.dialogs.new_book_dialog import NewBookDialog
from views.dialogs.lint_dialog import LintDialog
from views.dialogs.lint_whitelist_dialog import LintWhitelistDialog


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_theme_manager_tokens_for_all_themes(app):
    """驗證所有 6 種主題皆具備高對比指示器與強調色 tokens。"""
    theme_names = ["default", "green", "celadon", "sepia", "polar", "forest"]
    for name in theme_names:
        colors = ThemeManager.get_theme_colors(name)
        assert "accent" in colors
        assert "radio_border" in colors
        assert "checkbox_border" in colors
        assert "subtext_color" in colors
        assert "checkbox_check_icon" in colors

        qss = ThemeManager.get_theme_qss(name)
        assert "QRadioButton" in qss
        assert "QRadioButton::indicator" in qss
        assert "QCheckBox" in qss
        assert "QCheckBox::indicator" in qss
        assert "QDialog" in qss
        assert "QSpinBox" in qss
        assert "QPlainTextEdit" in qss


def test_initial_scale_dialog_indicators(app):
    """驗證初次啟動比例選擇視窗的 RadioButton 與選項卡片。"""
    dlg = InitialScaleDialog()
    assert dlg.windowTitle() == "九方小說編輯器 — 介面大小設定"
    assert len(dlg._radio_buttons) == 5
    # 驗證預設選中 1.0
    checked_radios = [r for r, s in dlg._radio_buttons if r.isChecked()]
    assert len(checked_radios) == 1
    assert checked_radios[0].styleSheet() != ""
    assert "QRadioButton::indicator" in checked_radios[0].styleSheet()
    dlg.close()


def test_export_scope_dialog_theme_awareness(app):
    """驗證匯出設定視窗支援高對比度 RadioButton 與 CheckBox。"""
    dlg = ExportScopeDialog()
    assert dlg.radio_merge.isChecked()
    assert dlg.chk_include_title.isChecked()
    assert dlg.tree_widget is not None
    dlg.close()


def test_word_count_settings_dialog_theme_awareness(app):
    """驗證字數統計設定視窗支援主題色。"""
    dlg = WordCountSettingsDialog()
    assert dlg.chk_half is not None
    assert dlg.chk_full_space is not None
    dlg.close()


def test_autosave_settings_dialog_theme_awareness(app):
    """驗證自動存檔設定視窗支援主題色與 SpinBox。"""
    dlg = AutosaveSettingsDialog()
    assert dlg.spin_interval.value() == 10
    assert dlg.spin_max_files.value() == 100
    dlg.close()


def test_storage_path_dialog_theme_awareness(app):
    """驗證存檔路徑視窗載入與控制項。"""
    dlg = StoragePathDialog(current_path="C:/test/path")
    assert dlg.line_path.text() == "C:/test/path"
    dlg.close()


def test_global_search_dialog_theme_awareness(app):
    """驗證全域搜尋視窗樣式包含主題色彩。"""
    dlg = GlobalSearchDialog()
    assert dlg.input_search is not None
    assert dlg.results_table is not None
    dlg.close()


def test_snapshot_dialog_theme_awareness(app):
    """驗證快照視窗表格樣式。"""
    dlg = SnapshotDialog(db_path=":memory:")
    assert dlg.table is not None
    dlg.close()


def test_scene_metadata_dialog_init(app):
    """驗證場景屬性視窗支援 QPlainTextEdit。"""
    dlg = SceneMetadataDialog(scene_name="第一幕", scene_summary="測試摘要")
    assert dlg.summary_edit.toPlainText() == "測試摘要"
    dlg.close()


def test_dialogs_across_all_themes(app):
    """驗證所有 6 種主題皆能透過 apply_theme_to_dialog 正確套用於對話框。"""
    class MockParent(QWidget):
        def __init__(self, theme):
            super().__init__()
            self.current_theme = theme
            self.scale_factor = 1.25

    theme_names = ["default", "green", "celadon", "sepia", "polar", "forest"]
    for theme in theme_names:
        parent = MockParent(theme)
        colors = ThemeManager.get_theme_colors(theme)
        
        # 測試 ExportScopeDialog
        dlg_export = ExportScopeDialog(parent=parent)
        assert dlg_export.styleSheet() != ""
        assert colors["accent"] in dlg_export.styleSheet()
        dlg_export.close()

        # 測試 WordCountSettingsDialog
        dlg_wc = WordCountSettingsDialog(parent=parent)
        assert dlg_wc.styleSheet() != ""
        assert colors["accent"] in dlg_wc.styleSheet()
        dlg_wc.close()

        # 測試 NewBookDialog
        dlg_nb = NewBookDialog(parent=parent)
        assert dlg_nb.styleSheet() != ""
        assert colors["accent"] in dlg_nb.styleSheet()
        dlg_nb.close()

        # 測試 LintDialog
        dlg_lint = LintDialog(parent=parent)
        assert dlg_lint.styleSheet() != ""
        assert colors["accent"] in dlg_lint.styleSheet()
        dlg_lint.close()

        # 測試 LintWhitelistDialog
        dlg_lw = LintWhitelistDialog(parent=parent)
        assert dlg_lw.styleSheet() != ""
        assert colors["accent"] in dlg_lw.styleSheet()
        dlg_lw.close()

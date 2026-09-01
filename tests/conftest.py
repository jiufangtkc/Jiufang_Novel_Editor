import os
import tempfile
import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QMessageBox

@pytest.fixture(autouse=True)
def isolate_app_environment():
    """
    確保所有測試都在獨立的臨時目錄下進行，
    避免讀寫真實使用者的 LOCALAPPDATA 與 Temp_doc / Story 檔案。
    """
    temp_dir = tempfile.TemporaryDirectory()
    original_appdata = os.environ.get('LOCALAPPDATA')
    os.environ['LOCALAPPDATA'] = temp_dir.name
    yield temp_dir
    
    if original_appdata is not None:
        os.environ['LOCALAPPDATA'] = original_appdata
    else:
        del os.environ['LOCALAPPDATA']
    try:
        temp_dir.cleanup()
    except Exception:
        pass

@pytest.fixture(autouse=True)
def block_qmessagebox():
    """
    全域阻擋 QMessageBox 的顯示。
    當遇到錯誤或提示時，避免視窗彈出並發出 Windows 警告音（導致 pytest 卡死）。
    """
    with patch('PyQt6.QtWidgets.QMessageBox.information'), \
         patch('PyQt6.QtWidgets.QMessageBox.warning'), \
         patch('PyQt6.QtWidgets.QMessageBox.critical'), \
         patch('PyQt6.QtWidgets.QMessageBox.about'), \
         patch('PyQt6.QtWidgets.QMessageBox.question', return_value=QMessageBox.StandardButton.Yes):
        yield

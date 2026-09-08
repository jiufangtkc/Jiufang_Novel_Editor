import os
import sys
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.token_estimator import TokenEstimator

def test_estimate_request_green_status():
    with patch("services.ai_service.AIService.count_tokens") as mock_count:
        # 模擬 input 與 system tokens
        mock_count.side_effect = [1000, 500]
        
        result = TokenEstimator.estimate_request(
            provider="TestProvider",
            api_url="http://test",
            task_type="character",
            novel_text="小說內文...",
            system_prompt="系統設定",
            user_prompt_overhead="額外指示",
            context_limit=10000
        )
        
        # input(1000) + system(500) + reserved(character 4000) + overhead(1000) = 6500
        assert result.total_estimated_tokens == 6500
        assert result.status == "GREEN"

def test_estimate_request_yellow_status():
    with patch("services.ai_service.AIService.count_tokens") as mock_count:
        mock_count.side_effect = [3500, 500]
        
        result = TokenEstimator.estimate_request(
            provider="TestProvider",
            api_url="http://test",
            task_type="character",
            novel_text="小說內文...",
            system_prompt="系統設定",
            user_prompt_overhead="額外指示",
            context_limit=10000
        )
        
        # input(3500) + system(500) + reserved(4000) + overhead(1000) = 9000
        # 9000 >= 10000 * 0.8
        assert result.total_estimated_tokens == 9000
        assert result.status == "YELLOW"

def test_estimate_request_red_status():
    with patch("services.ai_service.AIService.count_tokens") as mock_count:
        mock_count.side_effect = [6000, 500]
        
        result = TokenEstimator.estimate_request(
            provider="TestProvider",
            api_url="http://test",
            task_type="character",
            novel_text="小說內文...",
            system_prompt="系統設定",
            user_prompt_overhead="額外指示",
            context_limit=10000
        )
        
        # input(6000) + system(500) + reserved(4000) + overhead(1000) = 11500
        # 11500 > 10000
        assert result.total_estimated_tokens == 11500
        assert result.status == "RED"

def test_estimate_request_no_context_limit():
    with patch("services.ai_service.AIService.count_tokens") as mock_count:
        mock_count.side_effect = [1000, 500]
        
        result = TokenEstimator.estimate_request(
            provider="TestProvider",
            api_url="http://test",
            task_type="character",
            novel_text="小說內文...",
            system_prompt="系統設定",
            user_prompt_overhead="額外指示",
            context_limit=0
        )
        
        # 如果 limit <= 0，預設回傳黃色
        assert result.status == "YELLOW"

def test_fast_estimate_tokens():
    """驗證本地快速估算對空字串、中文、中英混合之準確性。"""
    assert TokenEstimator.fast_estimate_tokens("") == 0
    # 純中文 10 字，約 12 Token
    chinese_text = "莫庸持劍凝視星空深處無語"
    tokens = TokenEstimator.fast_estimate_tokens(chinese_text)
    assert 10 <= tokens <= 15

    # 中英混合文本
    mixed_text = "莫庸使用 Python 與 AI 模型進行分析"
    tokens_mixed = TokenEstimator.fast_estimate_tokens(mixed_text)
    assert tokens_mixed > 0

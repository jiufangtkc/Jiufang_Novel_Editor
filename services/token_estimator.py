from dataclasses import dataclass
from typing import Optional
from services.ai_service import AIService

@dataclass
class TokenEstimateResult:
    input_tokens: int
    system_tokens: int
    reserved_output_tokens: int
    overhead_tokens: int
    total_estimated_tokens: int
    context_limit: int
    status: str  # "GREEN", "YELLOW", "RED"
    status_message: str

class TokenEstimator:
    """負責估算 AI 請求所需的 Tokens，並驗證是否符合 Model Context Limit。"""
    
    # 針對不同任務的建議預留輸出字數（Tokens）
    DEFAULT_RESERVED_OUTPUT = {
        "character": 4000,
        "impression": 2000,
        "world": 3000,
        "timeline": 3000,
        "proofread": 2000,
        "chat": 2000,
        "continuation": 1500,
        "default": 3000
    }
    
    # 固定的安全緩衝 Tokens
    SAFETY_OVERHEAD = 1000

    @classmethod
    def fast_estimate_tokens(cls, text: str) -> int:
        """純本機零延遲 Token 快速估算代理方法。"""
        return AIService.fast_estimate_tokens(text)

    @classmethod
    def estimate_request(cls, provider: str, api_url: str, task_type: str, 
                         novel_text: str, system_prompt: str, user_prompt_overhead: str, 
                         context_limit: int) -> TokenEstimateResult:
        """
        估算總需求 Tokens 並回傳驗證狀態。
        """
        # 1. 計算輸入部分的 Tokens
        input_tokens = AIService.count_tokens(provider, api_url, novel_text, timeout=2)
        system_tokens = AIService.count_tokens(provider, api_url, system_prompt + user_prompt_overhead, timeout=2)
        
        # 2. 決定預留輸出 Tokens
        reserved_output = cls.DEFAULT_RESERVED_OUTPUT.get(task_type, cls.DEFAULT_RESERVED_OUTPUT["default"])
        
        # 3. 計算總估算
        total_estimated = input_tokens + system_tokens + reserved_output + cls.SAFETY_OVERHEAD
        
        # 4. 判斷狀態
        status = "GREEN"
        status_message = "可以嘗試送出"
        
        if context_limit > 0:
            if total_estimated > context_limit:
                status = "RED"
                status_message = "超過目前 Context 限制，請縮小分析範圍或調高限制"
            elif total_estimated >= context_limit * 0.8:
                status = "YELLOW"
                status_message = "接近 Context 上限，可能導致分析較慢或失敗"
        else:
            # 如果沒有正確設定 Context Limit，預設為黃色警告
            status = "YELLOW"
            status_message = "無法取得 Context 限制，請留意可能超過上限"
            
        return TokenEstimateResult(
            input_tokens=input_tokens,
            system_tokens=system_tokens,
            reserved_output_tokens=reserved_output,
            overhead_tokens=cls.SAFETY_OVERHEAD,
            total_estimated_tokens=total_estimated,
            context_limit=context_limit,
            status=status,
            status_message=status_message
        )

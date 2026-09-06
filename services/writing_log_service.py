class WritingLogService:
    """處理創作日誌數據分析、指標運算與圖表資料整合作業。"""

    @staticmethod
    def calculate_dashboard_metrics(logs: list) -> dict:
        """計算寫作儀表板各項綜合指標卡片數據。"""
        if not logs:
            logs = []

        total_duration = sum(l.get("duration", 0) for l in logs)
        total_words = sum(l.get("word_count", 0) for l in logs)
        total_ai_chars = sum(l.get("ai_continuation_chars", 0) for l in logs)
        total_ai_chats = sum(l.get("ai_chat_count", 0) for l in logs)
        total_manual_words = max(0, total_words - total_ai_chars)

        total_structuring = 0
        total_editorial = 0
        total_brainstorming = 0
        for l in logs:
            details = l.get("ai_details", {})
            if isinstance(details, dict):
                total_structuring += details.get("character", 0) + details.get("world", 0) + details.get("timeline", 0)
                total_editorial += details.get("proofread", 0) + details.get("impression", 0)
                total_brainstorming += details.get("chat", 0)

        all_interactions = total_ai_chats if total_ai_chats > 0 else (total_structuring + total_editorial + total_brainstorming)
        if total_structuring == 0 and total_editorial == 0 and total_brainstorming == 0 and total_ai_chats > 0:
            total_brainstorming = total_ai_chats

        active_days = len([l for l in logs if l.get("word_count", 0) > 0 or l.get("duration", 0) > 0])
        avg_words = int(total_words / max(1, active_days))

        total_hours = total_duration // 3600
        total_mins = (total_duration % 3600) // 60

        handcrafted_pct = 100 if total_words == 0 else int((total_manual_words / max(1, total_words)) * 100)
        if total_ai_chars == 0:
            card_main_val = f"{handcrafted_pct}% 純手創"
        else:
            card_main_val = f"{handcrafted_pct}% 手創 (代筆 {total_ai_chars:,}字)"

        if all_interactions == 0 and total_ai_chars == 0:
            card_sub_val = "100% 獨立原創 | 零 AI 介入"
        else:
            if total_ai_chars > 0:
                card_sub_val = f"含正文擴寫 | 輔助 {all_interactions} 次"
            elif total_editorial >= total_structuring and total_editorial > 0:
                card_sub_val = f"定位：文字校審評語 ({all_interactions} 次)"
            elif total_structuring > 0:
                card_sub_val = f"定位：設定架構整理 ({all_interactions} 次)"
            elif total_brainstorming > 0:
                card_sub_val = f"定位：靈感對話助手 ({all_interactions} 次)"
            else:
                card_sub_val = f"輔助互動 {all_interactions} 次 | 0 字代筆"

        return {
            "total_duration": total_duration,
            "total_words": total_words,
            "total_ai_chars": total_ai_chars,
            "total_ai_chats": total_ai_chats,
            "total_manual_words": total_manual_words,
            "total_structuring": total_structuring,
            "total_editorial": total_editorial,
            "total_brainstorming": total_brainstorming,
            "all_interactions": all_interactions,
            "active_days": active_days,
            "avg_words": avg_words,
            "total_hours": total_hours,
            "total_mins": total_mins,
            "duration_main": f"{total_hours} 小時 {total_mins} 分",
            "duration_sub": f"活躍寫作 {active_days} 天",
            "words_main": f"{total_words:,} 字",
            "words_sub": f"含手寫 {total_manual_words:,} 字",
            "avg_main": f"{avg_words:,} 字 / 天",
            "avg_sub": "連續紀錄中",
            "ai_main": card_main_val,
            "ai_sub": card_sub_val
        }

    @staticmethod
    def prepare_chart_data(logs: list) -> tuple:
        """整理傳遞給 WritingChartView 之近期趨勢與全量打卡歷史資料。"""
        if not logs:
            return [], [], [], [], [], {}

        sorted_logs_asc = sorted(logs, key=lambda x: x.get("date", ""))
        recent_logs = sorted_logs_asc[-14:] if len(sorted_logs_asc) > 14 else sorted_logs_asc
        recent_dates = [x.get("date", "") for x in recent_logs]
        recent_values = [max(0, x.get("word_count", 0)) for x in recent_logs]
        recent_ai_chars = [max(0, x.get("ai_continuation_chars", 0)) for x in recent_logs]
        recent_ai_chats = [max(0, x.get("ai_chat_count", 0)) for x in recent_logs]
        recent_ai_details = [x.get("ai_details", {}) for x in recent_logs]

        full_date_map = {x.get("date", ""): max(0, x.get("word_count", 0)) for x in logs if x.get("date")}

        return (
            recent_dates, recent_values, recent_ai_chars, recent_ai_chats, recent_ai_details,
            full_date_map
        )

    @staticmethod
    def format_table_rows(logs: list) -> list:
        """格式化單日寫作記錄供表格檢視呈現。"""
        if not logs:
            return []

        rows = []
        sorted_logs_desc = sorted(logs, key=lambda x: x.get("date", ""), reverse=True)
        for log in sorted_logs_desc:
            date_str = log.get("date", "")
            duration = log.get("duration", 0)
            word_count = log.get("word_count", 0)
            ai_chars = log.get("ai_continuation_chars", 0)
            ai_chats = log.get("ai_chat_count", 0)

            hours = duration // 3600
            minutes = (duration % 3600) // 60
            seconds = duration % 60

            if hours > 0:
                duration_str = f"{hours} 小時 {minutes} 分"
            elif minutes > 0:
                duration_str = f"{minutes} 分 {seconds} 秒"
            else:
                duration_str = f"{seconds} 秒"

            manual_words = max(0, word_count - ai_chars)

            details = log.get("ai_details", {})
            structuring = 0
            editorial = 0
            chat = 0
            continuation = 0
            if isinstance(details, dict):
                structuring = details.get("character", 0) + details.get("world", 0) + details.get("timeline", 0)
                editorial = details.get("proofread", 0) + details.get("impression", 0)
                chat = details.get("chat", 0)
                continuation = details.get("continuation", 0)

            day_interactions = ai_chats if ai_chats > 0 else (structuring + editorial + chat + continuation)
            if structuring == 0 and editorial == 0 and chat == 0 and ai_chats > 0:
                chat = ai_chats

            tags = []
            if editorial > 0:
                tags.append(f"[🔍校審 {editorial}]")
            if structuring > 0:
                tags.append(f"[🧩整理 {structuring}]")
            if chat > 0:
                tags.append(f"[💬靈感 {chat}]")
            if continuation > 0:
                tags.append(f"[✍️擴寫 {continuation}]")

            tag_str = " ".join(tags)
            if day_interactions == 0 and continuation == 0:
                chat_display = "0 次"
            elif tag_str:
                chat_display = f"{day_interactions} 次  {tag_str}"
            else:
                chat_display = f"{day_interactions} 次"

            tooltip_lines = [
                f"【{date_str} AI 輔助誠信明細】",
                f"• 親筆手寫字數：{manual_words:,} 字",
                f"• AI 續寫字數：{ai_chars:,} 字" + (f" ({continuation} 次)" if continuation else ""),
                f"• 責任編輯審校：{editorial} 次 (校稿、文學評語)",
                f"• 設定架構整理：{structuring} 次 (角色、世界觀、時間線)",
                f"• 靈感對話助手：{chat} 次",
                "────────────────────────",
                "誠信備註：除擴寫外，其餘功能皆為結構/校對輔助，不代筆正文。"
            ]

            rows.append({
                "date_str": date_str,
                "duration_str": duration_str,
                "manual_words": manual_words,
                "ai_chars": ai_chars,
                "chat_display": chat_display,
                "tooltip": "\n".join(tooltip_lines)
            })

        return rows

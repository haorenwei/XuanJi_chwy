export interface UserSetting {
  id: number
  user_id: number
  llm_provider: string | null
  llm_api_key: string | null
  llm_api_base_url: string | null
  llm_model_name: string | null
  ollama_base_url: string | null
  ollama_model: string | null
  tool_llm_provider: string | null
  tool_llm_api_key: string | null
  tool_llm_api_base_url: string | null
  tool_llm_model_name: string | null
  tool_ollama_base_url: string | null
  tool_ollama_model: string | null
  intent_llm_provider: string | null
  intent_llm_api_key: string | null
  intent_llm_api_base_url: string | null
  intent_llm_model_name: string | null
  emotion_llm_provider: string | null
  emotion_llm_api_key: string | null
  emotion_llm_api_base_url: string | null
  emotion_llm_model_name: string | null
  format_llm_provider: string | null
  format_llm_api_key: string | null
  format_llm_api_base_url: string | null
  format_llm_model_name: string | null
  show_tool_result: boolean | null
  show_collaboration: boolean | null
  token_monthly_budget: number | null
  created_at: string
  updated_at: string
}

export interface SettingUpdate {
  llm_provider?: string
  llm_api_key?: string
  llm_api_base_url?: string
  llm_model_name?: string
  ollama_base_url?: string
  ollama_model?: string
  tool_llm_provider?: string
  tool_llm_api_key?: string | null
  tool_llm_api_base_url?: string | null
  tool_llm_model_name?: string | null
  tool_ollama_base_url?: string | null
  tool_ollama_model?: string | null
  intent_llm_provider?: string | null
  intent_llm_api_key?: string | null
  intent_llm_api_base_url?: string | null
  intent_llm_model_name?: string | null
  emotion_llm_provider?: string | null
  emotion_llm_api_key?: string | null
  emotion_llm_api_base_url?: string | null
  emotion_llm_model_name?: string | null
  format_llm_provider?: string | null
  format_llm_api_key?: string | null
  format_llm_api_base_url?: string | null
  format_llm_model_name?: string | null
  show_tool_result?: boolean | null
  show_collaboration?: boolean | null
  token_monthly_budget?: number | null
}

export interface TokenUsageSummary {
  today_tokens: number
  month_tokens: number
  total_tokens: number
  monthly_budget: number | null
}

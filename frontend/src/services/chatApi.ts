// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// AI Chat API çağrıları - TonbilAi dogal dil asistani

import api from './api';

// --- Tip Tanimlari ---

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  action_type: string | null;
  action_result: Record<string, unknown> | null;
  timestamp: string;
}

export interface ChatSendRequest {
  message: string;
}

export interface ChatSendResponse {
  reply: string;
  action_type: string | null;
  action_result: Record<string, unknown> | null;
}

// --- API Fonksiyonlari ---

/** Kullanıcınin mesajini AI asistana gönderir */
export async function sendChatMessage(message: string): Promise<ChatSendResponse> {
  const { data } = await api.post<ChatSendResponse>('/chat/send', { message });
  return data;
}

/** Sohbet gecmisini getirir (varsayilan limit: 50) */
export async function fetchChatHistory(limit: number = 50): Promise<ChatMessage[]> {
  const { data } = await api.get<ChatMessage[]>('/chat/history', { params: { limit } });
  return data;
}

/** Tum sohbet gecmisini siler */
export async function clearChatHistory(): Promise<void> {
  await api.delete('/chat/history');
}

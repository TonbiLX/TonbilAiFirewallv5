// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Telegram Bot API çağrıları

import api from './api';

export const fetchTelegramConfig = () => api.get('/telegram/config');
export const updateTelegramConfig = (data: any) => api.put('/telegram/config', data);
export const testTelegram = (message?: string) =>
  api.post('/telegram/test', message ? { message } : {});

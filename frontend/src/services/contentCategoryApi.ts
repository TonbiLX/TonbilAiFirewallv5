// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Icerik Filtre Kategorileri API cagrilari ve tip tanimlari
// Profillerde kullanilan engelleme kategorileri yonetimi

import api from './api';

// --- Tipler ---

export interface BlocklistSummary {
  id: number;
  name: string;
  domain_count: number;
  enabled: boolean;
}

export interface ContentCategory {
  id: number;
  key: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  example_domains: string[];
  custom_domains: string | null;
  domain_count: number;
  enabled: boolean;
  blocklist_ids: number[];
  blocklists: BlocklistSummary[];
  created_at: string | null;
  updated_at: string | null;
}

export interface ContentCategoryCreate {
  key: string;
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  example_domains?: string[];
  custom_domains?: string;
  blocklist_ids?: number[];
}

export interface ContentCategoryUpdate {
  name?: string;
  description?: string;
  icon?: string;
  color?: string;
  example_domains?: string[];
  custom_domains?: string;
  blocklist_ids?: number[];
  enabled?: boolean;
}

// --- API Fonksiyonlari ---

export async function fetchContentCategories(): Promise<ContentCategory[]> {
  const { data } = await api.get('/content-categories/');
  return data;
}

export async function createContentCategory(payload: ContentCategoryCreate): Promise<ContentCategory> {
  const { data } = await api.post('/content-categories/', payload);
  return data;
}

export async function updateContentCategory(id: number, payload: ContentCategoryUpdate): Promise<ContentCategory> {
  const { data } = await api.patch(`/content-categories/${id}`, payload);
  return data;
}

export async function deleteContentCategory(id: number): Promise<void> {
  await api.delete(`/content-categories/${id}`);
}

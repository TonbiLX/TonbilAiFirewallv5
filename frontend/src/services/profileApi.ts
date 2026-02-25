// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// Profil API çağrıları

import api from './api';

export const fetchProfiles = () => api.get('/profiles/');
export const fetchProfile = (id: number) => api.get(`/profiles/${id}`);
export const createProfile = (data: any) => api.post('/profiles/', data);
export const updateProfile = (id: number, data: any) => api.patch(`/profiles/${id}`, data);
export const deleteProfile = (id: number) => api.delete(`/profiles/${id}`);

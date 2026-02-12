/**
 * API Service for Levi App
 * Connects to the backend server for reminder management
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://worker-production-a4be.up.railway.app/api';

// ===== DEV MOCK MODE =====
// Set to true to bypass login and use mock data for testing
export const DEV_MOCK_AUTH = false;

const MOCK_USER: User = {
  id: 1,
  phone: '+998901234567',
  name: 'Test User',
  timezone: 'Asia/Tashkent',
  language: 'uz',
  created_at: '2026-01-01T00:00:00Z',
};

const MOCK_REMINDERS: Reminder[] = [
  {
    id: 101,
    user_id: 1,
    task_text: 'Dorilarni ichish',
    scheduled_time_utc: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    user_timezone: 'Asia/Tashkent',
    status: 'pending',
    created_at: new Date().toISOString(),
  },
  {
    id: 102,
    user_id: 1,
    task_text: 'Xarid qilish - non, sut, tuxum',
    scheduled_time_utc: new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString(),
    user_timezone: 'Asia/Tashkent',
    status: 'pending',
    created_at: new Date().toISOString(),
  },
  {
    id: 103,
    user_id: 1,
    task_text: 'Ingliz tili darsiga borish',
    scheduled_time_utc: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    user_timezone: 'Asia/Tashkent',
    status: 'done',
    created_at: new Date().toISOString(),
  },
];
// ===== END DEV MOCK =====

// Types
export interface User {
  id: number;
  phone: string;
  name: string;
  timezone: string;
  language: string;
  created_at: string;
}

export interface Reminder {
  id: number;
  user_id: number;
  task_text: string;
  notes?: string;
  location?: string;
  scheduled_time_utc: string;
  user_timezone: string;
  status: 'pending' | 'done' | 'snoozed';
  recurrence_type?: string;
  recurrence_time?: string;
  created_at: string;
}

export interface LoginRequest {
  phone: string;
  password: string;
}

export interface RegisterRequest {
  name: string;
  phone: string;
  password: string;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  token?: string;
  message?: string;
}

export interface OtpRequest {
  phone: string;
}

export interface OtpVerifyRequest {
  phone: string;
  otp: string;
  name?: string;
  password?: string;
  isLogin?: boolean;
}

export interface OtpResponse {
  success: boolean;
  message?: string;
}

export interface ReminderResponse {
  success: boolean;
  reminders?: Reminder[];
  reminder?: Reminder;
  message?: string;
}

// Helper function for API calls
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('auth_token');
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Network error' }));
    throw new Error(error.message || 'API request failed');
  }

  return response.json();
}

// Auth API
export const authAPI = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await apiCall<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    
    if (response.token) {
      localStorage.setItem('auth_token', response.token);
    }
    
    return response;
  },

  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await apiCall<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    
    if (response.token) {
      localStorage.setItem('auth_token', response.token);
    }
    
    return response;
  },

  logout: () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user');
  },

  getCurrentUser: async (): Promise<User | null> => {
    if (DEV_MOCK_AUTH) return MOCK_USER;
    try {
      const response = await apiCall<{ user: User }>('/auth/me');
      return response.user;
    } catch {
      return null;
    }
  },

  isAuthenticated: (): boolean => {
    if (DEV_MOCK_AUTH) return true;
    return !!localStorage.getItem('auth_token');
  },

  sendOtp: async (data: OtpRequest): Promise<OtpResponse> => {
    return apiCall<OtpResponse>('/auth/send-otp', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  verifyOtp: async (data: OtpVerifyRequest): Promise<AuthResponse> => {
    const response = await apiCall<AuthResponse>('/auth/verify-otp', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    
    if (response.token) {
      localStorage.setItem('auth_token', response.token);
    }
    
    return response;
  },
};

// Reminders API
export const remindersAPI = {
  getAll: async (status?: string): Promise<Reminder[]> => {
    if (DEV_MOCK_AUTH) {
      let reminders = [...MOCK_REMINDERS];
      if (status) reminders = reminders.filter(r => r.status === status);
      return reminders;
    }
    const query = status ? `?status=${status}` : '';
    const response = await apiCall<ReminderResponse>(`/reminders${query}`);
    return response.reminders || [];
  },

  getById: async (id: number): Promise<Reminder | null> => {
    try {
      const response = await apiCall<ReminderResponse>(`/reminders/${id}`);
      return response.reminder || null;
    } catch {
      return null;
    }
  },

  create: async (data: { task_text: string; scheduled_time: string }): Promise<Reminder | null> => {
    try {
      const response = await apiCall<ReminderResponse>('/reminders', {
        method: 'POST',
        body: JSON.stringify(data),
      });
      return response.reminder || null;
    } catch {
      return null;
    }
  },

  updateStatus: async (id: number, status: 'pending' | 'done' | 'snoozed'): Promise<boolean> => {
    try {
      await apiCall(`/reminders/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      return true;
    } catch {
      return false;
    }
  },

  reschedule: async (id: number, newTime: string): Promise<boolean> => {
    try {
      await apiCall(`/reminders/${id}/reschedule`, {
        method: 'PATCH',
        body: JSON.stringify({ scheduled_time: newTime }),
      });
      return true;
    } catch {
      return false;
    }
  },

  delete: async (id: number): Promise<boolean> => {
    try {
      await apiCall(`/reminders/${id}`, {
        method: 'DELETE',
      });
      return true;
    } catch {
      return false;
    }
  },
};

// User API
export const userAPI = {
  updateProfile: async (data: { name?: string; timezone?: string }): Promise<boolean> => {
    try {
      await apiCall('/user/profile', {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
      return true;
    } catch {
      return false;
    }
  },

  updatePassword: async (data: { current_password: string; new_password: string }): Promise<boolean> => {
    try {
      await apiCall('/user/password', {
        method: 'PATCH',
        body: JSON.stringify(data),
      });
      return true;
    } catch {
      return false;
    }
  },
};

// Voice API
export interface VoiceParseResponse {
  success: boolean;
  transcription?: string;
  reminders?: Array<{
    task: string;
    time_utc: string;
    notes?: string;
    location?: string;
    recurrence_type?: string;
    recurrence_time?: string;
  }>;
  message?: string;
}

export interface VoiceReminderResponse {
  success: boolean;
  transcription?: string;
  reminders?: Reminder[];
  message?: string;
}

export const voiceAPI = {
  /**
   * Upload audio and get transcription + parsed reminders (preview)
   */
  parse: async (audioBlob: Blob, language: string = 'uz'): Promise<VoiceParseResponse> => {
    const token = localStorage.getItem('auth_token');
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    formData.append('language', language);

    const response = await fetch(`${API_BASE_URL}/voice/parse?language=${language}`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Voice parsing failed' }));
      throw new Error(error.message || 'Voice parsing failed');
    }

    return response.json();
  },

  /**
   * Upload audio and create reminders directly
   */
  createFromVoice: async (audioBlob: Blob, language: string = 'uz'): Promise<VoiceReminderResponse> => {
    const token = localStorage.getItem('auth_token');
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    formData.append('language', language);

    const response = await fetch(`${API_BASE_URL}/reminders/voice?language=${language}`, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Voice reminder creation failed' }));
      throw new Error(error.message || 'Voice reminder creation failed');
    }

    return response.json();
  },
};

export default {
  auth: authAPI,
  reminders: remindersAPI,
  user: userAPI,
  voice: voiceAPI,
};

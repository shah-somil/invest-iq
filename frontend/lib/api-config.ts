/**
 * API Configuration
 * Handles API URLs for both local development and production
 */

// Get API URL from environment variable or default to localhost
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Debug logging (remove in production if needed)
if (typeof window !== 'undefined') {
  console.log('🔧 API Configuration:');
  console.log('  - NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL);
  console.log('  - API_URL (resolved):', API_URL);
  console.log('  - NODE_ENV:', process.env.NODE_ENV);
}

// API Client with error handling
export class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_URL) {
    this.baseURL = baseURL;
  }

  private async handleResponse(response: Response) {
    if (!response.ok) {
      console.error(`❌ API Error: ${response.status} ${response.statusText}`);
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
    }
    console.log(`✅ API Success: ${response.status}`);
    return response.json();
  }

  async get(endpoint: string) {
    const url = `${this.baseURL}${endpoint}`;
    console.log(`🌐 API GET: ${url}`);
    const response = await fetch(url);
    return this.handleResponse(response);
  }

  async post(endpoint: string, data: any) {
    const url = `${this.baseURL}${endpoint}`;
    console.log(`🌐 API POST: ${url}`, data);
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return this.handleResponse(response);
  }
}

// Singleton instance
export const apiClient = new APIClient();

// Helper functions for common API calls
export const api = {
  // Health check
  health: () => apiClient.get('/health'),

  // Companies
  getCompanies: () => apiClient.get('/companies'),

  // Stats
  getStats: () => apiClient.get('/stats'),

  // RAG Search
  search: (params: {
    company_name: string;
    query: string;
    top_k?: number;
    filter_source?: string;
  }) => apiClient.post('/rag/search', params),

  // Dashboard Generation
  generateDashboard: (params: {
    company_name: string;
    top_k?: number;
    max_tokens?: number;
    temperature?: number;
    model?: string;
  }) => apiClient.post('/dashboard/rag', params),

  // Chat
  chat: (params: {
    message: string;
    conversation_history?: Array<{ role: string; content: string }>;
    company_name?: string;
    model?: string;
    temperature?: number;
    enable_web_search?: boolean;
  }) => apiClient.post('/chat', params),
};

// Environment info
export const getEnvironment = () => ({
  apiUrl: API_URL,
  isProduction: process.env.NODE_ENV === 'production',
  isDevelopment: process.env.NODE_ENV === 'development',
});




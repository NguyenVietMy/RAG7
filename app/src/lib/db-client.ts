/**
 * Database client for client-side components
 * This uses API routes to interact with the database since we can't connect directly from the browser
 */

export class DBClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.NEXT_PUBLIC_API_URL || '/api';
  }

  async query(endpoint: string, method: string = 'GET', body?: any) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.message || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Chats
  async getChats() {
    return this.query('/db/chats');
  }

  async createChat(data: { title: string; collection_name?: string | null }) {
    return this.query('/db/chats', 'POST', data);
  }

  async updateChat(id: string, data: { title?: string; title_refined?: boolean }) {
    return this.query(`/db/chats/${id}`, 'PATCH', data);
  }

  async deleteChat(id: string) {
    return this.query(`/db/chats/${id}`, 'DELETE');
  }

  // Messages
  async getMessages(chatId: string) {
    return this.query(`/db/chats/${chatId}/messages`);
  }

  async createMessage(data: { chat_id: string; role: string; content: string }) {
    return this.query('/db/messages', 'POST', data);
  }

  // RAG Settings
  async getRAGSettings() {
    return this.query('/db/rag-settings');
  }

  async upsertRAGSettings(data: {
    rag_n_results: number;
    rag_similarity_threshold: number;
    rag_max_context_tokens: number;
    chat_model?: string;
  }) {
    return this.query('/db/rag-settings', 'PUT', data);
  }
}

export const dbClient = new DBClient();


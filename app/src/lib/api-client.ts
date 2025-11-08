const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = BACKEND_URL) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText, message: response.statusText }));
      // FastAPI returns errors in 'detail' field, but we also check 'message'
      const errorMessage = error.detail || error.message || `Request failed: ${response.statusText}`;
      throw new Error(errorMessage);
    }

    return response.json();
  }

  // Health checks
  async healthChroma() {
    return this.request<{ status: string; collections_count: number }>("/health/chroma");
  }

  // Collections
  async createCollection(name: string, metadata?: Record<string, any>) {
    return this.request<{ name: string; metadata?: Record<string, any> }>("/collections", {
      method: "POST",
      body: JSON.stringify({ name, metadata }),
    });
  }

  async listCollections() {
    return this.request<{ collections: Array<{ name: string; metadata?: Record<string, any>; count?: number }>; total: number }>("/collections");
  }

  async getCollection(name: string) {
    return this.request<{ name: string; metadata?: Record<string, any>; count?: number }>(`/collections/${name}`);
  }

  // Upsert documents
  async upsert(
    collectionName: string,
    data: {
      ids: string[];
      documents?: string[];
      embeddings?: number[][];
      metadatas?: Record<string, any>[];
      model?: string;
    }
  ) {
    return this.request<{ status: string; upserted: number }>(
      `/collections/${collectionName}/upsert`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  // Query
  async query(
    collectionName: string,
    data: {
      query_texts?: string[];
      query_embeddings?: number[][];
      n_results?: number;
      model?: string;
      where?: Record<string, any>;
      include?: string[];
    }
  ) {
    return this.request(`/collections/${collectionName}/query`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
}

export const apiClient = new ApiClient();
export default apiClient;


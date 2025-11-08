"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function ChromaHealthCheck() {
  const [status, setStatus] = useState<{ loading: boolean; data: any; error: string | null }>({
    loading: false,
    data: null,
    error: null,
  });

  const checkHealth = async () => {
    setStatus({ loading: true, data: null, error: null });
    try {
      const data = await apiClient.healthChroma();
      setStatus({ loading: false, data, error: null });
    } catch (error: any) {
      setStatus({ loading: false, data: null, error: error.message });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>ChromaDB Connection Test</CardTitle>
        <CardDescription>Test the connection to your ChromaDB backend</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button onClick={checkHealth} disabled={status.loading}>
          {status.loading ? "Checking..." : "Test Connection"}
        </Button>

        {status.data && (
          <div className="p-4 bg-green-900/20 border border-green-700/50 rounded-lg">
            <pre className="text-sm text-green-200">
              {JSON.stringify(status.data, null, 2)}
            </pre>
          </div>
        )}

        {status.error && (
          <div className="p-4 bg-red-900/20 border border-red-700/50 rounded-lg">
            <p className="text-sm text-red-200">Error: {status.error}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}


"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import DashboardNavbar from "@/components/dashboard-navbar";
import { apiClient } from "@/lib/api-client";
import { createClient } from "../../../supabase/client";
import { toast } from "@/components/ui/use-toast";

interface RAGConfig {
  rag_n_results: number;
  rag_similarity_threshold: number;
  rag_max_context_tokens: number;
}

export default function SettingsPage() {
  const [config, setConfig] = useState<RAGConfig>({
    rag_n_results: 3,
    rag_similarity_threshold: 0.0,
    rag_max_context_tokens: 2000,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (user) {
        setUserId(user.id);

        // Load from Supabase directly (same way we load chats/messages)
        const { data, error } = await supabase
          .from("user_rag_settings")
          .select("*")
          .eq("user_id", user.id)
          .single();

        if (error && error.code !== "PGRST116") {
          // PGRST116 = no rows returned
          throw error;
        }

        if (data) {
          setConfig({
            rag_n_results: data.rag_n_results,
            rag_similarity_threshold: data.rag_similarity_threshold,
            rag_max_context_tokens: data.rag_max_context_tokens,
          });
        } else {
          // No config found, use defaults
          const defaultConfig = await apiClient.getRAGConfig(user.id);
          setConfig(defaultConfig);
        }
      } else {
        // Load defaults if not logged in
        const defaultConfig = await apiClient.getRAGConfig();
        setConfig(defaultConfig);
      }
    } catch (error) {
      console.error("Error loading config:", error);
      toast({
        title: "Error",
        description: "Failed to load RAG configuration",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);

      if (!userId) {
        toast({
          title: "Error",
          description: "Please sign in to save configuration",
          variant: "destructive",
        });
        return;
      }

      // Validate config via backend (optional, but good for validation)
      const validatedConfig = await apiClient.updateRAGConfig(config, userId);

      // Save directly to Supabase (same way we save chats/messages)
      // Use upsert with onConflict to handle both insert and update
      const supabase = createClient();
      const { error } = await supabase.from("user_rag_settings").upsert(
        {
          user_id: userId,
          rag_n_results: validatedConfig.rag_n_results,
          rag_similarity_threshold: validatedConfig.rag_similarity_threshold,
          rag_max_context_tokens: validatedConfig.rag_max_context_tokens,
        },
        {
          onConflict: "user_id", // Use the unique constraint
        }
      );

      if (error) throw error;

      toast({
        title: "Success",
        description: "RAG configuration saved successfully",
      });
    } catch (error: any) {
      console.error("Error saving config:", error);
      toast({
        title: "Error",
        description: error.message || "Failed to save RAG configuration",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white">
        <DashboardNavbar />
        <div className="container mx-auto px-4 py-8">
          <div className="text-center">Loading configuration...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white">
      <DashboardNavbar />
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold mb-6">RAG Configuration</h1>
        <p className="text-gray-600 mb-8">
          Configure how the RAG (Retrieval Augmented Generation) system
          retrieves and uses context from your knowledge base.
        </p>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle>RAG Settings</CardTitle>
            <CardDescription>
              Adjust these settings to control how many results are retrieved,
              similarity filtering, and context size limits.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* RAG N Results */}
            <div className="space-y-2">
              <Label htmlFor="rag_n_results">
                Number of Results (RAG_N_RESULTS)
              </Label>
              <div className="flex items-center gap-4">
                <Input
                  id="rag_n_results"
                  type="number"
                  min="1"
                  max="100"
                  value={config.rag_n_results}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      rag_n_results: parseInt(e.target.value) || 3,
                    })
                  }
                  className="w-24"
                />
                <span className="text-sm text-gray-500">
                  Number of document chunks to retrieve from ChromaDB (1-100)
                </span>
              </div>
              <p className="text-xs text-gray-500">
                More results provide more context but may include less relevant
                information.
              </p>
            </div>

            {/* Similarity Threshold */}
            <div className="space-y-2">
              <Label htmlFor="rag_similarity_threshold">
                Similarity Threshold
              </Label>
              <div className="space-y-2">
                <div className="flex items-center gap-4">
                  <Input
                    id="rag_similarity_threshold"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={config.rag_similarity_threshold}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        rag_similarity_threshold:
                          parseFloat(e.target.value) || 0.0,
                      })
                    }
                    className="w-24"
                  />
                  <span className="text-sm text-gray-500">
                    Minimum similarity score (0.0-1.0) to include results
                  </span>
                </div>
                <Slider
                  value={[config.rag_similarity_threshold]}
                  onValueChange={([value]) =>
                    setConfig({ ...config, rag_similarity_threshold: value })
                  }
                  min={0}
                  max={1}
                  step={0.01}
                  className="w-full"
                />
              </div>
              <p className="text-xs text-gray-500">
                Higher values filter out less similar results. 0.0 includes all
                results, 1.0 only includes perfect matches.
              </p>
            </div>

            {/* Max Context Tokens */}
            <div className="space-y-2">
              <Label htmlFor="rag_max_context_tokens">
                Max Context Tokens (RAG_MAX_CONTEXT_TOKENS)
              </Label>
              <div className="flex items-center gap-4">
                <Input
                  id="rag_max_context_tokens"
                  type="number"
                  min="1"
                  max="10000"
                  step="100"
                  value={config.rag_max_context_tokens}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      rag_max_context_tokens: parseInt(e.target.value) || 2000,
                    })
                  }
                  className="w-32"
                />
                <span className="text-sm text-gray-500">
                  Maximum tokens to include in context (1-10000)
                </span>
              </div>
              <p className="text-xs text-gray-500">
                Limits the total size of context sent to the AI. Larger values
                allow more context but increase token usage.
              </p>
            </div>

            <div className="pt-4">
              <Button onClick={handleSave} disabled={saving}>
                {saving ? "Saving..." : "Save Configuration"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>How It Works</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-gray-600">
            <div>
              <h3 className="font-semibold mb-2">Number of Results</h3>
              <p>
                This determines how many document chunks are retrieved from your
                knowledge base for each query. More results provide more context
                but may include less relevant information.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">Similarity Threshold</h3>
              <p>
                Results with similarity scores below this threshold are filtered
                out. This helps ensure only relevant context is included in the
                AI response.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-2">Max Context Tokens</h3>
              <p>
                This limits the total size of context sent to the AI model. If
                the retrieved results exceed this limit, only the most relevant
                results (up to the limit) are included.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

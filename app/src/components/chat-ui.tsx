"use client";

import { useState, useEffect, useCallback } from "react";
import { Pencil, Search, Send, Plus, Loader2, Trash2 } from "lucide-react";
import { Button } from "./ui/button";
import { apiClient } from "@/lib/api-client";
import { createClient } from "../../supabase/client";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at?: string;
};

type Chat = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
  collection_name?: string | null;
  message_count?: number;
};

export default function ChatUI() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingChats, setIsLoadingChats] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(
    null
  );
  const [collections, setCollections] = useState<
    Array<{ name: string; count?: number }>
  >([]);

  const activeChat = chats.find((chat) => chat.id === activeChatId);
  const filteredChats = chats.filter((chat) =>
    chat.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Load chats from database on mount
  useEffect(() => {
    loadChats();
    loadCollections();
  }, []);

  // Load messages when active chat changes
  useEffect(() => {
    if (activeChatId) {
      loadMessages(activeChatId);
    }
  }, [activeChatId]);

  const loadCollections = async () => {
    try {
      const response = await apiClient.listCollections();
      setCollections(response.collections || []);
      // Auto-select first collection if available
      if (response.collections && response.collections.length > 0) {
        setSelectedCollection(response.collections[0].name);
      }
    } catch (err: any) {
      console.error("Failed to load collections:", err);
    }
  };

  const loadChats = async () => {
    setIsLoadingChats(true);
    try {
      const supabase = createClient();

      const { data, error: dbError } = await supabase
        .from("chats")
        .select("*")
        .eq("is_archived", false)
        .order("last_message_at", { ascending: false })
        .limit(50); // Limit to recent chats

      if (dbError) throw dbError;

      const loadedChats: Chat[] = (data || []).map((chat) => ({
        id: chat.id,
        title: chat.title,
        messages: [], // Load messages separately
        createdAt: new Date(chat.created_at),
        collection_name: chat.collection_name,
        message_count: chat.message_count || 0,
      }));

      setChats(loadedChats);
    } catch (err: any) {
      console.error("Failed to load chats:", err);
      setError(err?.message || "Failed to load chats");
    } finally {
      setIsLoadingChats(false);
    }
  };

  const loadMessages = async (chatId: string) => {
    try {
      const supabase = createClient();

      const { data, error: dbError } = await supabase
        .from("messages")
        .select("*")
        .eq("chat_id", chatId)
        .order("created_at", { ascending: true })
        .limit(100); // Load last 100 messages

      if (dbError) throw dbError;

      const messages: ChatMessage[] = (data || []).map((msg) => ({
        id: msg.id,
        role: msg.role as "user" | "assistant",
        content: msg.content,
        created_at: msg.created_at,
      }));

      // Update chat with loaded messages
      setChats((prevChats) =>
        prevChats.map((chat) =>
          chat.id === chatId ? { ...chat, messages } : chat
        )
      );
    } catch (err: any) {
      console.error("Failed to load messages:", err);
      setError(err?.message || "Failed to load messages");
    }
  };

  const saveMessage = async (
    chatId: string,
    role: "user" | "assistant",
    content: string
  ): Promise<string | null> => {
    try {
      const supabase = createClient();

      const { data, error: dbError } = await supabase
        .from("messages")
        .insert({
          chat_id: chatId,
          role,
          content,
        })
        .select()
        .single();

      if (dbError) throw dbError;
      return data?.id || null;
    } catch (err: any) {
      console.error("Failed to save message:", err);
      return null;
    }
  };

  const generateTitleAsync = async (chatId: string, userMessage: string) => {
    try {
      const response = await apiClient.generateTitle({
        user_message: userMessage,
      });

      const supabase = createClient();

      await supabase
        .from("chats")
        .update({
          title: response.title,
          title_refined: true,
        })
        .eq("id", chatId);

      // Update local state
      setChats((prevChats) =>
        prevChats.map((chat) =>
          chat.id === chatId ? { ...chat, title: response.title } : chat
        )
      );
    } catch (err: any) {
      console.error("Failed to generate title:", err);
      // Don't show error to user, title generation is optional
    }
  };

  const handleNewChat = () => {
    setActiveChatId(null);
    setInputValue("");
    setError(null);
  };

  const handleDeleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent chat selection when clicking delete

    if (
      !confirm(
        "Are you sure you want to delete this chat? All messages will be permanently deleted."
      )
    ) {
      return;
    }

    try {
      const supabase = createClient();

      // Delete chat (CASCADE DELETE will automatically delete all messages)
      const { error: deleteError } = await supabase
        .from("chats")
        .delete()
        .eq("id", chatId);

      if (deleteError) throw deleteError;

      // Remove from local state
      setChats((prevChats) => prevChats.filter((chat) => chat.id !== chatId));

      // If deleted chat was active, clear active chat
      if (activeChatId === chatId) {
        setActiveChatId(null);
        setInputValue("");
      }
    } catch (err: any) {
      console.error("Failed to delete chat:", err);
      setError(err?.message || "Failed to delete chat");
    }
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setIsLoading(true);
    setError(null);

    try {
      const supabaseClient = createClient();

      // Create new chat if none is active
      let chatIdToUse = activeChatId;
      let isNewChat = false;

      if (!chatIdToUse) {
        const initialTitle = userMessage.substring(0, 50) || "New chat";
        const { data: newChat, error: chatError } = await supabaseClient
          .from("chats")
          .insert({
            title: initialTitle,
            collection_name: selectedCollection,
          })
          .select()
          .single();

        if (chatError) throw chatError;
        chatIdToUse = newChat.id;
        isNewChat = true;

        // Add to local state
        const newChatLocal: Chat = {
          id: newChat.id,
          title: initialTitle,
          messages: [],
          createdAt: new Date(newChat.created_at),
          collection_name: selectedCollection,
        };
        setChats([newChatLocal, ...chats]);
        setActiveChatId(newChat.id);
      }

      // Save user message
      const userMessageId = await saveMessage(
        chatIdToUse!,
        "user",
        userMessage
      );
      if (!userMessageId) {
        throw new Error("Failed to save user message");
      }

      // Add user message to UI optimistically
      const userMessageObj: ChatMessage = {
        id: userMessageId,
        role: "user",
        content: userMessage,
      };

      setChats((prevChats) =>
        prevChats.map((chat) =>
          chat.id === chatIdToUse
            ? {
                ...chat,
                messages: [...chat.messages, userMessageObj],
              }
            : chat
        )
      );

      // Get all messages for context (including the one we just added)
      const currentChat = chats.find((c) => c.id === chatIdToUse);
      const allMessages = [...(currentChat?.messages || []), userMessageObj];

      // Prepare messages for API
      const apiMessages = allMessages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

      // Get active chat's collection name
      const activeChatCollection =
        activeChat?.collection_name || selectedCollection;

      // Load RAG config from Supabase (single config for local app)
      let ragConfig = null;
      try {
        const { data: ragSettings, error: ragError } = await supabaseClient
          .from("rag_settings")
          .select("*")
          .limit(1)
          .single();

        if (!ragError && ragSettings) {
          ragConfig = {
            rag_n_results: ragSettings.rag_n_results,
            rag_similarity_threshold: ragSettings.rag_similarity_threshold,
            rag_max_context_tokens: ragSettings.rag_max_context_tokens,
          };
        }
      } catch (err) {
        console.warn("Failed to load RAG config, using defaults:", err);
      }

      // Call backend API (no user ID needed for local app)
      // Pass RAG config explicitly to ensure it's used
      const response = await apiClient.chat(
        {
          messages: apiMessages,
          collection_name: activeChatCollection || undefined,
          ...(ragConfig && {
            rag_n_results: ragConfig.rag_n_results,
            rag_similarity_threshold: ragConfig.rag_similarity_threshold,
            rag_max_context_tokens: ragConfig.rag_max_context_tokens,
          }),
        }
      );

      // Save assistant message
      const assistantMessageId = await saveMessage(
        chatIdToUse!,
        "assistant",
        response.content
      );

      const assistantMessageObj: ChatMessage = {
        id: assistantMessageId || Date.now().toString(),
        role: "assistant",
        content: response.content,
      };

      // Update UI with assistant response
      setChats((prevChats) =>
        prevChats.map((chat) =>
          chat.id === chatIdToUse
            ? {
                ...chat,
                messages: [...chat.messages, assistantMessageObj],
              }
            : chat
        )
      );

      // Generate title asynchronously if this is a new chat
      if (isNewChat && allMessages.length === 1) {
        // Generate title based on user's prompt only
        generateTitleAsync(chatIdToUse!, userMessage).catch(console.error);
      }
    } catch (err: any) {
      console.error("Error sending message:", err);
      setError(err?.message || "Failed to send message. Please try again.");
      // Remove optimistic user message on error
      if (activeChatId) {
        setChats((prevChats) =>
          prevChats.map((chat) =>
            chat.id === activeChatId
              ? {
                  ...chat,
                  messages: chat.messages.slice(0, -1),
                }
              : chat
          )
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !isLoading) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex h-[calc(100vh-73px)] bg-white">
      {/* Left Sidebar */}
      <aside className="w-64 border-r border-gray-200 bg-white flex flex-col">
        {/* New Chat Button */}
        <div className="p-3 border-b border-gray-200">
          <Button
            onClick={handleNewChat}
            className="w-full justify-start gap-2 bg-white hover:bg-gray-50 text-black border border-gray-200"
            variant="outline"
          >
            <Pencil className="h-4 w-4" />
            New chat
          </Button>
        </div>

        {/* Collection Selector */}
        {collections.length > 0 && (
          <div className="p-3 border-b border-gray-200">
            <label className="block text-xs font-medium text-gray-700 mb-1">
              Knowledge Base
            </label>
            <select
              value={selectedCollection || ""}
              onChange={(e) => setSelectedCollection(e.target.value || null)}
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black bg-white"
            >
              <option value="">None</option>
              {collections.map((col) => (
                <option key={col.name} value={col.name}>
                  {col.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Search Chats */}
        <div className="p-3 border-b border-gray-200">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search chats"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Chats Section */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-3">
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2 px-2">
              Chats
            </h2>
            {isLoadingChats ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
              </div>
            ) : (
              <div className="space-y-1">
                {filteredChats.map((chat) => (
                  <div
                    key={chat.id}
                    className={`group relative flex items-center gap-2 rounded-lg text-sm transition-colors ${
                      activeChatId === chat.id
                        ? "bg-gray-100"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    <button
                      onClick={() => setActiveChatId(chat.id)}
                      className={`flex-1 text-left px-3 py-2 ${
                        activeChatId === chat.id
                          ? "text-black font-medium"
                          : "text-gray-700"
                      }`}
                    >
                      <div className="truncate">{chat.title}</div>
                      {chat.message_count && chat.message_count > 0 && (
                        <div className="text-xs text-gray-400 mt-0.5">
                          {chat.message_count} messages
                        </div>
                      )}
                    </button>
                    <button
                      onClick={(e) => handleDeleteChat(chat.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-2 text-gray-400 hover:text-red-600 transition-all"
                      title="Delete chat"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
                {filteredChats.length === 0 && !isLoadingChats && (
                  <div className="px-3 py-2 text-sm text-gray-400">
                    No chats found
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col bg-white">
        {error && (
          <div className="px-4 py-2 bg-red-50 border-b border-red-200 text-red-700 text-sm">
            {error}
            <button onClick={() => setError(null)} className="ml-2 underline">
              Dismiss
            </button>
          </div>
        )}

        {!activeChat ? (
          // Empty State - Initial Prompt
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-2xl px-4">
              <h1 className="text-4xl font-semibold text-gray-800 mb-4">
                What's on the agenda today?
              </h1>
              <div className="mt-8 max-w-3xl mx-auto">
                <div className="relative">
                  <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Ask anything"
                    disabled={isLoading}
                    className="w-full px-4 py-3 pr-12 rounded-3xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:opacity-50"
                    rows={1}
                    style={{
                      minHeight: "52px",
                      maxHeight: "200px",
                    }}
                    onInput={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      target.style.height = "auto";
                      target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
                    }}
                  />
                  <div className="absolute right-3 top-[calc(50%-1px)] transform -translate-y-1/2 flex items-center gap-2">
                    <Button
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim() || isLoading}
                      className="h-8 w-8 p-0 rounded-full bg-transparent hover:bg-gray-100 text-gray-600 hover:text-gray-800 disabled:opacity-50"
                      variant="ghost"
                    >
                      {isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          // Active Chat View
          <>
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto px-4 py-6">
              <div className="max-w-3xl mx-auto space-y-6">
                {activeChat.messages.length === 0 ? (
                  <div className="text-center text-gray-400 py-12">
                    Start a conversation...
                  </div>
                ) : (
                  activeChat.messages.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${
                        message.role === "user"
                          ? "justify-end"
                          : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                          message.role === "user"
                            ? "bg-blue-600 text-white"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        <div className="whitespace-pre-wrap text-sm">
                          {message.content}
                        </div>
                      </div>
                    </div>
                  ))
                )}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 text-gray-800 rounded-2xl px-4 py-3">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-200 bg-white p-4">
              <div className="max-w-3xl mx-auto">
                <div className="relative">
                  <Plus className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyPress}
                    placeholder="Ask anything"
                    disabled={isLoading}
                    className="w-full pl-12 pr-12 py-3 rounded-3xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:opacity-50"
                    rows={1}
                    style={{
                      minHeight: "52px",
                      maxHeight: "200px",
                    }}
                    onInput={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      target.style.height = "auto";
                      target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
                    }}
                  />
                  <div className="absolute right-3 top-[calc(50%-1px)] transform -translate-y-1/2 flex items-center gap-2">
                    <Button
                      onClick={handleSendMessage}
                      disabled={!inputValue.trim() || isLoading}
                      className="h-8 w-8 p-0 rounded-full bg-transparent hover:bg-gray-100 text-gray-600 hover:text-gray-800 disabled:opacity-50"
                      variant="ghost"
                    >
                      {isLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

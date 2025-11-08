"use client";

import { useState } from "react";
import { Pencil, Search, Send, Plus } from "lucide-react";
import { Button } from "./ui/button";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type Chat = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
};

export default function ChatUI() {
  const [chats, setChats] = useState<Chat[]>([
    {
      id: "1",
      title: "Giải thích chi tiết quà tặng",
      messages: [],
      createdAt: new Date(),
    },
    {
      id: "2",
      title: "Str vs repr in Python",
      messages: [],
      createdAt: new Date(),
    },
    {
      id: "3",
      title: "Code refinement suggestions",
      messages: [],
      createdAt: new Date(),
    },
    {
      id: "4",
      title: "Connect ELRS to Arduino",
      messages: [],
      createdAt: new Date(),
    },
    {
      id: "5",
      title: "Using Chroma DB",
      messages: [],
      createdAt: new Date(),
    },
  ]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const activeChat = chats.find((chat) => chat.id === activeChatId);
  const filteredChats = chats.filter((chat) =>
    chat.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleNewChat = () => {
    const newChat: Chat = {
      id: Date.now().toString(),
      title: "New chat",
      messages: [],
      createdAt: new Date(),
    };
    setChats([newChat, ...chats]);
    setActiveChatId(newChat.id);
    setInputValue("");
  };

  const handleSendMessage = () => {
    if (!inputValue.trim()) return;

    // Create new chat if none is active
    let chatIdToUse = activeChatId;
    if (!activeChatId) {
      const newChat: Chat = {
        id: Date.now().toString(),
        title: inputValue.substring(0, 50) || "New chat",
        messages: [],
        createdAt: new Date(),
      };
      setChats([newChat, ...chats]);
      setActiveChatId(newChat.id);
      chatIdToUse = newChat.id;
    }

    const message: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue,
    };

    setChats((prevChats) =>
      prevChats.map((chat) =>
        chat.id === chatIdToUse
          ? {
              ...chat,
              messages: [...chat.messages, message],
              title:
                chat.messages.length === 0 && chat.title === "New chat"
                  ? inputValue.substring(0, 50)
                  : chat.title,
            }
          : chat
      )
    );

    setInputValue("");

    // Simulate assistant response
    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "This is a placeholder response. The AI assistant functionality will be implemented separately.",
      };

      setChats((prevChats) =>
        prevChats.map((chat) =>
          chat.id === chatIdToUse
            ? { ...chat, messages: [...chat.messages, assistantMessage] }
            : chat
        )
      );
    }, 500);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
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
            <div className="space-y-1">
              {filteredChats.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => setActiveChatId(chat.id)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                    activeChatId === chat.id
                      ? "bg-gray-100 text-black font-medium"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <div className="truncate">{chat.title}</div>
                </button>
              ))}
              {filteredChats.length === 0 && (
                <div className="px-3 py-2 text-sm text-gray-400">
                  No chats found
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col bg-white">
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
                    className="w-full px-4 py-3 pr-12 rounded-3xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
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
                      disabled={!inputValue.trim()}
                      className="h-8 w-8 p-0 rounded-full bg-transparent hover:bg-gray-100 text-gray-600 hover:text-gray-800 disabled:opacity-50"
                      variant="ghost"
                    >
                      <Send className="h-4 w-4" />
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
                {activeChat.messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.role === "user" ? "justify-end" : "justify-start"
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
                ))}
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
                    className="w-full pl-12 pr-12 py-3 rounded-3xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
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
                      disabled={!inputValue.trim()}
                      className="h-8 w-8 p-0 rounded-full bg-transparent hover:bg-gray-100 text-gray-600 hover:text-gray-800 disabled:opacity-50"
                      variant="ghost"
                    >
                      <Send className="h-4 w-4" />
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


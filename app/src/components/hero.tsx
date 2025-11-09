"use client";

import Link from "next/link";
import { ArrowRight, Play } from "lucide-react";
import { Button } from "./ui/button";
import { motion } from "framer-motion";

export default function Hero() {
  return (
    <section
      id="home"
      className="relative min-h-screen bg-[#0F172A] overflow-hidden pt-20"
    >
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#3B82F6]/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#3B82F6]/10 rounded-full blur-3xl animate-pulse delay-1000" />
      </div>

      <div className="relative container mx-auto px-4 py-20 md:py-32">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left Content */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-left"
          >
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight"
            >
              Forge your own{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#3B82F6] to-[#60A5FA]">
                AI Decision Support System
              </span>
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
              className="text-lg md:text-xl text-gray-300 mb-8 leading-relaxed max-w-2xl"
            >
              Transform your documents into an intelligent AI professional that
              provides cited, accurate answers. No code required.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.6 }}
              className="flex flex-col sm:flex-row gap-4"
            >
              <Link href="/sign-up">
                <Button
                  size="lg"
                  className="bg-[#3B82F6] hover:bg-[#2563EB] text-white text-lg px-8 py-6 rounded-md shadow-lg shadow-[#3B82F6]/50 hover:shadow-[#3B82F6]/70 transition-all"
                >
                  Create Your AI Professional
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
            </motion.div>
          </motion.div>

          {/* Right Content - Chat Mockup */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="relative"
          >
            <div className="relative bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-xl rounded-2xl border border-gray-700/50 p-6 shadow-2xl">
              {/* Chat Header */}
              <div className="flex items-center gap-3 mb-6 pb-4 border-b border-gray-700">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#3B82F6] to-[#60A5FA] flex items-center justify-center">
                  <span className="text-white font-bold">AI</span>
                </div>
                <div>
                  <div className="text-white font-semibold">RAG7</div>
                  <div className="text-gray-400 text-sm">Online</div>
                </div>
              </div>

              {/* Chat Messages */}
              <div className="space-y-4">
                <div className="flex justify-end">
                  <div className="bg-[#3B82F6] text-white rounded-2xl rounded-tr-sm px-4 py-3 max-w-xs">
                    What are the key findings from the Q4 report?
                  </div>
                </div>
                <div className="flex justify-start">
                  <div className="bg-gray-700/50 text-gray-100 rounded-2xl rounded-tl-sm px-4 py-3 max-w-md">
                    Based on the Q4 Financial Report (page 12), revenue
                    increased by 23% YoY to $4.2M, with customer acquisition
                    costs decreasing by 15%.
                    <div className="mt-2 text-xs text-gray-400 border-t border-gray-600 pt-2">
                      📄 Source: Q4_Financial_Report.pdf
                    </div>
                  </div>
                </div>
              </div>

              {/* Typing Indicator */}
              <div className="mt-4 flex items-center gap-2 text-gray-400 text-sm">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200" />
                </div>
                <span>RAG7 is analyzing your documents...</span>
              </div>
            </div>

            {/* Floating Elements */}
            <motion.div
              animate={{ y: [0, -10, 0] }}
              transition={{ duration: 3, repeat: Infinity }}
              className="absolute -top-4 -right-4 bg-[#3B82F6] text-white px-4 py-2 rounded-lg shadow-lg text-sm font-semibold"
            >
              ✓ Cited Answers
            </motion.div>
            <motion.div
              animate={{ y: [0, 10, 0] }}
              transition={{ duration: 3, repeat: Infinity, delay: 1 }}
              className="absolute -bottom-4 -left-4 bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg text-sm font-semibold border border-gray-700"
            >
              🔒 Private & Secure
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

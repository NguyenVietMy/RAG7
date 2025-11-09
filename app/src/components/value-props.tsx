"use client";

import { motion } from "framer-motion";
import { Zap, Database, Shield, FileCheck } from "lucide-react";

const features = [
  {
    icon: Zap,
    title: "No-Code Setup",
    description:
      "Upload your documents and start chatting in minutes. No technical expertise required.",
  },
  {
    icon: Database,
    title: "Multi-Source Intelligence",
    description:
      "Combine insights from PDFs, docs, spreadsheets, and more into one intelligent system.",
  },
  {
    icon: Shield,
    title: "Private & Secure",
    description:
      "Your data stays yours. Enterprise-grade encryption and privacy controls built-in.",
  },
  {
    icon: FileCheck,
    title: "Cited Answers",
    description:
      "Every response includes source citations so you can verify and trust the information.",
  },
];

export default function ValueProps() {
  return (
    <section
      id="features"
      className="py-24 bg-[#0F172A] relative overflow-hidden"
    >
      {/* Background decoration */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-[#3B82F6]/5 to-transparent" />

      <div className="container mx-auto px-4 relative">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Why Choose RAG7
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Everything you need to build your AI decision support system
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              whileHover={{ y: -8, transition: { duration: 0.2 } }}
              className="group relative"
            >
              <div className="h-full bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm rounded-xl border border-gray-700/50 p-8 hover:border-[#3B82F6]/50 transition-all duration-300">
                {/* Icon */}
                <div className="w-14 h-14 rounded-lg bg-[#3B82F6]/10 flex items-center justify-center mb-6 group-hover:bg-[#3B82F6]/20 transition-colors">
                  <feature.icon className="w-7 h-7 text-[#3B82F6]" />
                </div>

                {/* Content */}
                <h3 className="text-xl font-semibold text-white mb-3">
                  {feature.title}
                </h3>
                <p className="text-gray-400 leading-relaxed">
                  {feature.description}
                </p>

                {/* Hover effect */}
                <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-[#3B82F6]/0 to-[#3B82F6]/0 group-hover:from-[#3B82F6]/5 group-hover:to-transparent transition-all duration-300 pointer-events-none" />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

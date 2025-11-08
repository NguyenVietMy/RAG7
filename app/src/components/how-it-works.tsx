"use client";

import { motion } from "framer-motion";
import { Upload, Cpu, MessageSquare } from "lucide-react";

const steps = [
  {
    number: "01",
    icon: Upload,
    title: "Upload",
    description:
      "Drop your documents, PDFs, or data files into Lola. We support all major formats.",
  },
  {
    number: "02",
    icon: Cpu,
    title: "Index",
    description:
      "Our AI processes and indexes your content, creating a knowledge base tailored to your needs.",
  },
  {
    number: "03",
    icon: MessageSquare,
    title: "Chat",
    description:
      "Ask questions and get intelligent, cited answers from your AI professional instantly.",
  },
];

export default function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="py-24 bg-gradient-to-b from-[#0F172A] to-[#1E293B] relative overflow-hidden"
    >
      <div className="container mx-auto px-4 relative">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-20"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            How Lola Works
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Get started in three simple steps
          </p>
        </motion.div>

        <div className="relative max-w-5xl mx-auto">
          {/* Connection Line */}
          <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-[#3B82F6]/20 via-[#3B82F6]/50 to-[#3B82F6]/20 -translate-y-1/2" />

          <div className="grid md:grid-cols-3 gap-8 lg:gap-12">
            {steps.map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.2 }}
                className="relative"
              >
                <div className="relative bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-700/50 p-8 hover:border-[#3B82F6]/50 transition-all duration-300 group">
                  {/* Step Number */}
                  <div className="absolute -top-6 left-8 text-6xl font-bold text-[#3B82F6]/20 group-hover:text-[#3B82F6]/30 transition-colors">
                    {step.number}
                  </div>

                  {/* Icon */}
                  <div className="relative w-16 h-16 rounded-xl bg-[#3B82F6]/10 flex items-center justify-center mb-6 group-hover:bg-[#3B82F6]/20 transition-colors">
                    <step.icon className="w-8 h-8 text-[#3B82F6]" />
                  </div>

                  {/* Content */}
                  <h3 className="text-2xl font-bold text-white mb-4">
                    {step.title}
                  </h3>
                  <p className="text-gray-400 leading-relaxed">
                    {step.description}
                  </p>

                  {/* Arrow for desktop */}
                  {index < steps.length - 1 && (
                    <div className="hidden lg:block absolute top-1/2 -right-6 w-12 h-0.5 bg-[#3B82F6]/50 -translate-y-1/2">
                      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-t-transparent border-b-4 border-b-transparent border-l-8 border-l-[#3B82F6]/50" />
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

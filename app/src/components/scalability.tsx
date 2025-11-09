"use client";

import { motion } from "framer-motion";
import { TrendingUp, Database, Brain } from "lucide-react";

const features = [
  {
    icon: Database,
    title: "Unlimited Documents",
    description:
      "Add as many documents as you need. There's no limit to how much knowledge RAG7 can learn and retain.",
  },
  {
    icon: TrendingUp,
    title: "Growing Intelligence",
    description:
      "With each document, RAG7 becomes smarter, more accurate, and more valuable as your AI professional.",
  },
  {
    icon: Brain,
    title: "Continuous Learning",
    description:
      "Your knowledge base grows with your needs. The more you feed it, the better it serves you.",
  },
];

export default function Scalability() {
  return (
    <section
      id="scalability"
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
            IT SCALES INFINITELY
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            The more documents you add to train, the more intelligent
          </p>
        </motion.div>

        <div className="relative max-w-5xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 lg:gap-12 items-stretch">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.2 }}
                className="relative flex flex-col"
              >
                <div className="relative bg-gradient-to-br from-gray-800/80 to-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-700/50 p-8 hover:border-[#3B82F6]/50 transition-all duration-300 group flex-1 flex flex-col">
                  {/* Icon */}
                  <div className="relative w-16 h-16 rounded-xl bg-[#3B82F6]/10 flex items-center justify-center mb-6 group-hover:bg-[#3B82F6]/20 transition-colors">
                    <feature.icon className="w-8 h-8 text-[#3B82F6]" />
                  </div>

                  {/* Content */}
                  <h3 className="text-2xl font-bold text-white mb-4">
                    {feature.title}
                  </h3>
                  <p className="text-gray-400 leading-relaxed flex-grow">
                    {feature.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

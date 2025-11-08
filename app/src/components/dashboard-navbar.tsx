"use client";

import Link from "next/link";
import Image from "next/image";
import { Home } from "lucide-react";

export default function DashboardNavbar() {
  return (
    <nav className="w-full border-b border-gray-200 bg-white py-4">
      <div className="container mx-auto px-4 flex justify-between items-center">
        <div className="flex items-center gap-6">
          <Link href="/" prefetch className="flex items-center">
            <Image
              src="/Lola_logo.png"
              alt="Lola"
              width={180}
              height={60}
              className="h-16 w-auto"
            />
          </Link>
          <Link
            href="/dashboard"
            className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
          >
            <Home className="h-4 w-4" />
            Dashboard
          </Link>
          <Link
            href="/import"
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Import
          </Link>
          <Link
            href="/settings"
            className="text-sm text-gray-600 hover:text-gray-900"
          >
            Settings
          </Link>
        </div>
      </div>
    </nav>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fire Detection Dashboard",
  description: "Real-time UAV forest fire detection — Edge-Cloud System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-900 text-slate-100">{children}</body>
    </html>
  );
}

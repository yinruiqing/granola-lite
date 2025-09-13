import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Layout } from "@/components/layout/Layout";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Granola Lite - AI 会议纪要工具",
  description: "基于 AI 的智能会议记录和转录工具",
  manifest: "/manifest.json",
  themeColor: "#3b82f6",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Granola Lite",
  },
  formatDetection: {
    telephone: false,
  },
  openGraph: {
    type: "website",
    siteName: "Granola Lite",
    title: "Granola Lite - AI 会议纪要工具",
    description: "基于 AI 的智能会议记录和转录工具",
  },
  twitter: {
    card: "summary",
    title: "Granola Lite - AI 会议纪要工具",
    description: "基于 AI 的智能会议记录和转录工具",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <Layout>{children}</Layout>
      </body>
    </html>
  );
}

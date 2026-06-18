import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/sonner";
import { AuthContextProvider } from "@/contexts/AuthContext";
import { getSession } from "@/lib/session";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Revature EvaluAI",
  description: "Revature EvaluAI — AI-powered evaluation platform for technical assessments",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const session = await getSession();
  const user = session
    ? { id: session.userId, email: session.email, role: session.role }
    : null;

  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <AuthContextProvider user={user}>
          {children}
          <Toaster />
        </AuthContextProvider>
      </body>
    </html>
  );
}

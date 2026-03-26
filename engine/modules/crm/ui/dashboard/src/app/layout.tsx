import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Sidebar from "@/components/Sidebar";
import { SidebarProvider } from "@/context/SidebarContext";

export const metadata: Metadata = {
  title: "Revenue Terminal | Autonomous OS",
  description: "Enterprise-grade autonomous revenue agent command center.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body style={{ display: 'flex', minHeight: '100vh', overflow: 'hidden' }} suppressHydrationWarning>
        <SidebarProvider>
          <Sidebar />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <Header />
            <main style={{ flex: 1, overflowY: 'auto' }}>
              {children}
            </main>
            <Footer />
          </div>
        </SidebarProvider>
      </body>
    </html>
  );
}

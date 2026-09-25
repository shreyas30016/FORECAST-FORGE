import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "leaflet/dist/leaflet.css";
import "./globals.css";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { LocationProvider } from "@/context/LocationContext";
import { SettingsProvider } from "@/context/SettingsContext";
import { CopilotProvider } from "@/context/CopilotContext";
import { GlobalCopilot } from "@/components/agent/GlobalCopilot";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Forecast Forge AI | Atmospheric Weather Intelligence",
  description: "Next-generation meteorological command center and multi-model ensemble intelligence workstation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <body className="antialiased flex h-screen overflow-hidden bg-background text-text-primary" suppressHydrationWarning>
        <SettingsProvider>
          <LocationProvider>
            <CopilotProvider>
              {/* Workstation Sidebar */}
              <Sidebar />
              
              {/* Main Workstation Area */}
              <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                <Topbar />
                <main className="flex-1 overflow-auto p-3 sm:p-4 lg:p-5">
                  {children}
                </main>
                <GlobalCopilot />
              </div>
            </CopilotProvider>
          </LocationProvider>
        </SettingsProvider>
      </body>
    </html>
  );
}

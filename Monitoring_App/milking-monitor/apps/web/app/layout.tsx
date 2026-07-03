import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "../components/providers/session-provider";

export const metadata: Metadata = {
  title: "Milking Monitor",
  description: "Supervisor dashboard for milking process compliance monitoring.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

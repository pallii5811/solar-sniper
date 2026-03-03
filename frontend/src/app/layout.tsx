import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SOLAR SNIPER - Energy Edition",
  description: "SOLAR SNIPER - Energy Edition",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}

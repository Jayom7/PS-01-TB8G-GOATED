import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PS-01 · Secure Knowledge Workspace",
  description: "A multimodal retrieval workspace concept for Code Carnival 3.0.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

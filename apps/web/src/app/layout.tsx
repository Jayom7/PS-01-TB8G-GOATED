import type { Metadata } from "next";
import "./globals.css";
import "./atelier.css";

export const metadata: Metadata = {
  title: "Clearframe · Secure Knowledge Workspace",
  description: "A secure workspace for evidence-grounded enterprise knowledge.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

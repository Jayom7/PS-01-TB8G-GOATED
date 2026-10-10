import type { Metadata } from "next";
import "./globals.css";
import "./atelier.css";

export const metadata: Metadata = {
  title: "Clearframe · Secure Knowledge Workspace",
  description: "A secure workspace for evidence-grounded enterprise knowledge.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: `try{document.documentElement.dataset.theme=localStorage.getItem("clearframe-theme")==="dark"?"dark":"light"}catch{document.documentElement.dataset.theme="light"}` }} /></head>
      <body>{children}</body>
    </html>
  );
}

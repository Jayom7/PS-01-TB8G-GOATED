"use client";

import { useEffect, type ReactNode } from "react";
import { Icon } from "./icons";

export function AuthFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    try { document.documentElement.dataset.theme = localStorage.getItem("clearframe-theme") === "dark" ? "dark" : "light"; } catch { /* Keep the default when storage is unavailable. */ }
  }, []);
  return <main className="login-shell"><aside className="auth-story" aria-label="About Clearframe"><span className="auth-story-mark"><Icon name="lock" size={27} /></span><h2>Knowledge with<br />a clear provenance.</h2><p>Documents, scans, and business records.<br />One workspace to connect the evidence.</p><ol className="auth-principles"><li><Icon name="user" size={18} /><span>Start with your organization identity.</span></li><li><Icon name="search" size={18} /><span>Search within your authorized context.</span></li><li><Icon name="files" size={18} /><span>Follow citations to the original source.</span></li></ol><small>Clearframe · Protected knowledge workspace</small></aside>{children}</main>;
}

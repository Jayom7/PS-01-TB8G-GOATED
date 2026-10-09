"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { Icon } from "./icons";

// Native modal dialog owns focus trapping and background inertness.
export function Drawer({ title, description, onClose, children, variant = "dialog", busy = false }: {
  title: string; description: string; onClose: () => void; children: ReactNode; variant?: "dialog" | "evidence"; busy?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const closeRef = useRef(onClose);
  useEffect(() => { closeRef.current = onClose; }, [onClose]);
  useEffect(() => {
    const dialog = ref.current;
    const trigger = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    if (variant === "dialog") { document.body.style.overflow = "hidden"; dialog?.showModal(); }
    else { dialog?.show(); dialog?.querySelector<HTMLButtonElement>("button")?.focus(); }
    const dismiss = (event: KeyboardEvent) => {
      if (variant === "evidence" && event.key === "Escape" && !document.querySelector("dialog:modal")) closeRef.current();
    };
    document.addEventListener("keydown", dismiss);
    return () => {
      document.removeEventListener("keydown", dismiss);
      dialog?.close();
      document.body.style.overflow = previousOverflow;
      if (trigger instanceof HTMLElement && trigger.isConnected) trigger.focus();
    };
  }, [variant]);
  return <dialog ref={ref} className={`source-drawer ${variant === "dialog" ? "centered-dialog" : "evidence-panel"}`} aria-labelledby={titleId}
    onKeyDown={(event) => {
      if (variant !== "dialog" || event.key !== "Tab") return;
      const items = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), iframe, [tabindex="0"]')).filter((element) => element.getClientRects().length > 0);
      const first = items[0]; const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }}
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget) {
      const box = event.currentTarget.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) onClose();
    } }}>
    <header className="drawer-heading"><div><h2 id={titleId}>{title}</h2><p>{description}</p></div>
      <button className="icon-button" type="button" disabled={busy} aria-label={`Close ${title.toLowerCase()}`} onClick={onClose} autoFocus><Icon name="close" /></button>
    </header>
    {children}
  </dialog>;
}

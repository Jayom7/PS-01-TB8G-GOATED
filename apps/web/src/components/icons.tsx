import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "chat" | "files" | "table" | "upload" | "chart" | "send" | "paperclip"
  | "chevron" | "menu" | "close" | "user" | "arrow" | "lock" | "home";

const paths: Record<IconName, ReactNode> = {
  chat: <path d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H6l-3 2v-5.5A7.5 7.5 0 1 1 20 11.5Z" />,
  files: <><path d="M7 3.75h7l4.25 4.5v12A1.75 1.75 0 0 1 16.5 22h-9A1.75 1.75 0 0 1 5.75 20.25v-14A2.5 2.5 0 0 1 8.25 3.75Z" /><path d="M14 4v5h4M9 13h6M9 17h6" /></>,
  table: <><rect x="3.5" y="4.5" width="17" height="15" rx="1.5" /><path d="M3.5 10h17M9 4.5v15m6-15v15" /></>,
  upload: <><path d="M12 15V3m0 0L7.5 7.5M12 3l4.5 4.5" /><path d="M5 14v5.25A1.75 1.75 0 0 0 6.75 21h10.5A1.75 1.75 0 0 0 19 19.25V14" /></>,
  chart: <><path d="M4 20V11M10 20V5m6 15v-8m6 8V8" /></>,
  send: <><path d="m21 3-7.4 18-3.4-7.2L3 10.4 21 3Z" /><path d="M10.2 13.8 21 3" /></>,
  paperclip: <path d="m8.5 12.5 6.8-6.8a3.2 3.2 0 0 1 4.5 4.5l-9.5 9.5a5 5 0 0 1-7.1-7.1l9.2-9.2" />,
  chevron: <path d="m7 10 5 5 5-5" />,
  menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
  close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  user: <><circle cx="12" cy="8" r="3.25" /><path d="M5 20a7 7 0 0 1 14 0" /></>,
  arrow: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 1 1 8 0v3" /></>,
  home: <><path d="m3 10 9-7 9 7" /><path d="M5 9v11h14V9M9 20v-6h6v6" /></>,
};

export function Icon({
  name,
  size = 20,
  ...props
}: SVGProps<SVGSVGElement> & { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {paths[name]}
    </svg>
  );
}

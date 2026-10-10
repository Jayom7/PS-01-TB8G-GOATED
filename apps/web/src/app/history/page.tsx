import AuthenticatedWorkspace from "@/components/authenticated-workspace";

export const metadata = {title: "Conversation history · Clearframe"};

export default function HistoryPage() {
  return <AuthenticatedWorkspace view="History" />;
}

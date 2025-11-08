import DashboardNavbar from "@/components/dashboard-navbar";
import ChatUI from "@/components/chat-ui";

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-white">
      <DashboardNavbar />
      <ChatUI />
    </div>
  );
}

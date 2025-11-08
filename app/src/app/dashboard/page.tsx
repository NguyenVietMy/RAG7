import DashboardNavbar from "@/components/dashboard-navbar";
import ChatUI from "@/components/chat-ui";
import { redirect } from "next/navigation";
import { createClient } from "../../../supabase/server";

export default async function Dashboard() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return redirect("/sign-in");
  }

  return (
    <div className="min-h-screen bg-white">
      <DashboardNavbar />
      <ChatUI />
    </div>
  );
}

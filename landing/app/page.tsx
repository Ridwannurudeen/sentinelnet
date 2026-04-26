import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import ThreePillars from "@/components/ThreePillars";
import RecentActivity from "@/components/RecentActivity";
import CodeTabs from "@/components/CodeTabs";
import ContractsTable from "@/components/ContractsTable";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="min-h-screen bg-bg">
      <Navbar />
      <Hero />
      <ThreePillars />
      <RecentActivity />
      <CodeTabs />
      <ContractsTable />
      <Footer />
    </main>
  );
}

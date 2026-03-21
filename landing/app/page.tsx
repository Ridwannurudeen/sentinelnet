import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import LiveStats from "@/components/LiveStats";
import FeatureGrid from "@/components/FeatureGrid";
import CodeTabs from "@/components/CodeTabs";
import ContractsTable from "@/components/ContractsTable";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main className="min-h-screen bg-bg">
      <Navbar />
      <Hero />
      <LiveStats />
      <FeatureGrid />
      <CodeTabs />
      <ContractsTable />
      <Footer />
    </main>
  );
}

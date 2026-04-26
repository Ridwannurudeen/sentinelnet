import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import GetStartedFlow from "@/components/GetStartedFlow";

export const metadata = {
  title: "Get started — SentinelNet",
  description: "Integrate SentinelNet trust scores in 60 seconds.",
};

export default function Page() {
  return (
    <main className="min-h-screen bg-bg">
      <Navbar />
      <section className="pt-28 sm:pt-36 pb-12 px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <p className="text-sm text-muted mb-6 inline-flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-trust" />
            5-minute integration
          </p>
          <h1
            className="font-display font-light text-text"
            style={{
              fontSize: "clamp(2.5rem, 7vw, 5.5rem)",
              lineHeight: "1.0",
              letterSpacing: "-0.04em",
            }}
          >
            Integrate
            <br />
            <span className="italic">in five minutes.</span>
          </h1>
          <p className="mt-8 max-w-2xl text-lg sm:text-xl text-muted leading-relaxed font-light">
            Three steps. Pick your stack, drop in one call, deploy. Every score
            you receive is on-chain, slashable, and challengeable for 72 hours.
          </p>
        </div>
      </section>
      <GetStartedFlow />
      <Footer />
    </main>
  );
}

import Footer from "@/components/footer"
import Hero from "@/components/hero"
import Navbar from "@/components/navbar"
import ValueProps from "@/components/value-props"
import HowItWorks from "@/components/how-it-works"

export default function Home() {
  return (
    <div className="min-h-screen bg-[#0F172A]">
      <Navbar />
      <Hero />
      <ValueProps />
      <HowItWorks />
      <Footer />
    </div>
  )
}
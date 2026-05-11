import { Link } from "react-router-dom";
import Navbar from "../components/Navbar";

export default function Home() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-4xl px-6 py-20 text-center">
        <span className="text-6xl">🌿</span>
        <h1 className="mt-6 text-5xl font-bold tracking-tight text-gray-900">
          NigerFlora BioSciences
        </h1>
        <p className="mt-4 text-xl text-gray-500">
          From soil to science to pharmacy.
        </p>
        <p className="mt-6 text-lg text-gray-600 max-w-2xl mx-auto">
          An AI-powered platform connecting centuries of Nigerian herbal
          knowledge to modern pharmaceutical production — validated, digitized,
          and ready for the global market.
        </p>
        <div className="mt-10 flex justify-center gap-4">
          <Link
            to="/login"
            className="rounded-lg bg-brand-600 px-6 py-3 text-base font-semibold text-white hover:bg-brand-700"
          >
            Get Started
          </Link>
          <a
            href="https://github.com"
            className="rounded-lg border border-gray-300 px-6 py-3 text-base font-semibold text-gray-700 hover:bg-gray-50"
          >
            Learn More
          </a>
        </div>
      </main>
    </div>
  );
}

import type { Metadata } from "next";
import { Fraunces, Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const fraunces = Fraunces({ subsets: ["latin"], variable: "--font-fraunces", display: "swap" });

export const metadata: Metadata = {
  title: "MediNaija — Your chronic care companion",
  description: "Drugs, delivery and check-ins in one chronic-care plan for Nigerians."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={inter.variable + " " + fraunces.variable + " font-sans"}>
        {children}
      </body>
    </html>
  );
}

import "./globals.css";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "Consolidation in the Poultry Packing Industry",
  description: "",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="light">
      <head>
        <script defer src="https://core-facility-umami.vercel.app/script.js" data-website-id="247afa6c-d983-442f-a866-595409c05917"></script>
      </head>
      <body className={inter.className}>{children}</body>
    </html>
  );
}

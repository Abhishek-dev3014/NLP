import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import { AppShell } from "@/components/shell";
import { GeistSans } from "geist/font/sans";
import "./globals.css";
export const metadata: Metadata = {
  title: {
    default: "VeriFact AI — Think critically. Verify intelligently.",
    template: "%s · VeriFact AI",
  },
  description:
    "Transparent NLP analysis for a more informed perspective. Explore language patterns, genuine model predictions, and claims worth verifying.",
};
const themeScript = `try{document.documentElement.dataset.theme=localStorage.getItem('verifact-theme')||'dark'}catch(e){}`;
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      data-theme="dark"
      data-scroll-behavior="smooth"
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={GeistSans.variable}>
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}

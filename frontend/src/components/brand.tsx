import Link from "next/link";
import { ScanLine } from "lucide-react";
export function Brand() {
  return (
    <Link href="/" className="brand" aria-label="VeriFact AI home">
      <span className="brand-mark">
        <ScanLine size={23} strokeWidth={2.2} />
      </span>
      <span>
        VeriFact<span className="brand-ai"> AI</span>
      </span>
    </Link>
  );
}

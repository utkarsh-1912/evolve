import Image from "next/image";
import { Link } from "@/i18n/navigation";

// évolvé logo, re-cut assets (docs/09 §10): transparent lockup or mark, always on a navy surface.
export function BrandLogo({ variant = "lockup", height = 32, descriptor }: { variant?: "lockup" | "mark"; height?: number; descriptor?: string }) {
  const src = variant === "mark" ? "/brand/evolve-mark-transparent.png" : "/brand/evolve-logo-transparent.png";
  const width = variant === "mark" ? Math.round((height * 133) / 132) : Math.round((height * 411) / 132);
  return (
    <Link href="/" className="flex items-center gap-3 rounded-md">
      <Image src={src} alt="évolvé" width={width} height={height} priority style={{ width, height }} />
      {descriptor ? <span className="hidden text-sm text-mist lg:inline">{descriptor}</span> : null}
    </Link>
  );
}

import Image from "next/image";
import { Link } from "@/i18n/navigation";

// évolvé logo, re-cut assets (docs/09 §10): transparent lockup or mark, always on a navy/dark surface.
export function BrandLogo({ variant = "lockup", height = 32, href = "/queue" }: { variant?: "lockup" | "mark"; height?: number; href?: string }) {
  const src = variant === "mark" ? "/brand/evolve-mark-transparent.png" : "/brand/evolve-logo-transparent.png";
  const width = variant === "mark" ? Math.round((height * 133) / 132) : Math.round((height * 411) / 132);
  return (
    <Link href={href} className="flex items-center gap-3 rounded-md">
      <Image src={src} alt="évolvé" width={width} height={height} priority style={{ width, height }} />
    </Link>
  );
}

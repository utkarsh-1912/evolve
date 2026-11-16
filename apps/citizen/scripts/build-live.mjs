// Builds the citizen app against the live backend into .next-live (cross-platform env; Windows cmd has no VAR=x).
import { spawnSync } from "node:child_process";
const env = { ...process.env, NEXT_PUBLIC_API: process.env.NEXT_PUBLIC_API ?? "http://localhost:8010", NEXT_DIST_DIR: ".next-live" };
const r = spawnSync("npx", ["next", "build"], { stdio: "inherit", env, shell: true });
process.exit(r.status ?? 1);

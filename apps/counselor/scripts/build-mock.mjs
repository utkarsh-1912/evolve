// Production build wired to the SIMULATED mock adapter (for the mock e2e suite). Cross-platform env setting.
import { spawnSync } from "node:child_process";
const r = spawnSync("npx", ["next", "build"], { stdio: "inherit", shell: true, env: { ...process.env, NEXT_PUBLIC_API: "mock" } });
process.exit(r.status ?? 1);

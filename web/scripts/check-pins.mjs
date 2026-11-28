// Fails when a dependency in package.json is not pinned to an exact version (F-15.01).
import { readFileSync } from "node:fs";

const pkg = JSON.parse(
  readFileSync(new URL("../package.json", import.meta.url), "utf8"),
);
const exact = /^\d+\.\d+\.\d+$/;
const loose = Object.entries({
  ...pkg.dependencies,
  ...pkg.devDependencies,
}).filter(([, version]) => !exact.test(version));
if (loose.length > 0) {
  for (const [name, version] of loose)
    console.error(`not pinned: ${name}@${version}`);
  process.exit(1);
}
console.log("all dependencies pinned to exact versions");

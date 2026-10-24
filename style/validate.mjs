// style/validate.mjs — validate a style with @maplibre/maplibre-gl-style-spec (installed with viewer/).
import { readFileSync } from 'node:fs';
const spec = await import(new URL('../viewer/node_modules/@maplibre/maplibre-gl-style-spec/dist/index.mjs', import.meta.url));
for (const f of process.argv.slice(2)) {
  const style = JSON.parse(readFileSync(f, 'utf8'));
  const errs = spec.validateStyleMin(style);
  console.log(f, errs.length ? errs.slice(0, 10).map(e => e.message) : 'OK', `(${errs.length} errors)`);
  process.exitCode ||= errs.length ? 1 : 0;
}

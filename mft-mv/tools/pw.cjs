// Resolve Playwright: a local / global install (else stop with an install hint).
const path = require('path');
try {
  module.exports = require('playwright');
} catch (_) {
  module.exports = (() => { throw new Error('Playwright not found: run "npm i playwright" and "npx playwright install chromium" in the project root (or set NODE_PATH to `npm root -g`)'); })();
}
// file:// URL of index.html with query (forward slashes on Windows)
module.exports.pageUrl = (query) => 'file:///' + path.resolve(__dirname, '../index.html').replace(/\\/g, '/').replace(/^\//, '') + query;
module.exports.SWIFT = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--allow-file-access-from-files'];
// the real GPU (D3D11 through ANGLE): the sky's volumetric clouds are slow on SwiftShader
module.exports.GPU = ['--use-angle=d3d11', '--ignore-gpu-blocklist', '--enable-gpu-rasterization', '--allow-file-access-from-files'];
module.exports.argsFor = (gpu) => (gpu ? module.exports.GPU : module.exports.SWIFT);

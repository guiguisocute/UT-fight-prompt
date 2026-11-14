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

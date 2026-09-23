const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'web/index.html'), 'utf8');
const js = fs.readFileSync(path.join(root, 'web/subscription_gate_v32.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'web/subscription_gate_v32.css'), 'utf8');
function ok(cond, msg){ if(!cond) throw new Error(msg); }
ok(html.includes('body class="subscription-checking32"'), 'initial body must be checking, not pending');
ok(html.includes('id="subscriptionGate32" aria-live="polite" hidden'), 'gate must start hidden');
ok(html.includes('subscription_gate_v32.js?v=321'), 'JS cache-bust must be v321');
ok(html.includes('subscription_gate_v32.css?v=321'), 'CSS cache-bust must be v321');
ok(js.includes('installGameBootBarrier'), 'game boot barrier missing');
ok(js.includes('installBusinessIconBootstrap'), 'business icon bootstrap missing');
ok(js.includes("!url.startsWith('/api/subscription/check')"), 'subscription endpoint must bypass game barrier');
ok(js.includes("showGate('Подписка пока не найдена"), 'gate must only reveal after negative result');
ok(css.includes('body.subscription-checking32 .subscription-gate32'), 'checking state must hide gate');
console.log('v32.1 tests passed');

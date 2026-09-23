const fs=require('fs');
const path=require('path');
const root=path.resolve(__dirname,'..');
function read(p){return fs.readFileSync(path.join(root,p),'utf8')}
const gate=read('web/subscription_gate_v32.js');
const index=read('web/index.html');
const ref=read('web/referrals_v33_1.js');
const css=read('web/referrals_v33.css');
const bot=read('bot.py');
const app=read('app.py');
const allWeb=fs.readdirSync(path.join(root,'web')).filter(f=>/\.(js|html)$/.test(f)).map(f=>read('web/'+f)).join('\n');

if(!gate.includes('/static/referrals_v33_1.js?v=331'))throw new Error('v33.1 referral script is not loaded');
if(!index.includes('/static/referrals_v33.css?v=331'))throw new Error('v33.1 referral CSS cache version missing');
if(!ref.includes('refTopButton331'))throw new Error('header gift button missing');
if(!ref.includes('ref-entry-main331'))throw new Error('Main referral entry missing');
if(!ref.includes('ref-entry-rating331'))throw new Error('Rating referral entry missing');
if(!ref.includes("page='referrals'"))throw new Error('dedicated referral page state missing');
if(!ref.includes('tg.initDataUnsafe.start_param'))throw new Error('Telegram start_param referral fallback missing');
if(!css.includes('ref-entry-main331'))throw new Error('v33.1 visibility CSS missing');
if(!bot.includes('WEBAPP_VERSION = "331"'))throw new Error('bot cache version is not 331');
if(!app.includes('CORPORATION_REFERRALS_V33_BEGIN'))throw new Error('referral backend missing');
if(/\b(?:alert|confirm|prompt)\s*\(/.test(allWeb))throw new Error('native alert/confirm/prompt remains in web files');
console.log('V33.1 visibility tests: OK');

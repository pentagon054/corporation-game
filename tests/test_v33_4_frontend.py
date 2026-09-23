from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

def test_no_native_dialog_calls():
    bad = []
    pattern = re.compile(r"(?<![\w.])(alert|confirm|prompt)\s*\(|\.show(?:Alert|Confirm|Popup)\s*\(")
    for path in WEB.rglob("*"):
        if path.suffix not in {".js", ".html"}:
            continue
        text = path.read_text(encoding="utf-8")
        for i,line in enumerate(text.splitlines(),1):
            if pattern.search(line):
                bad.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    assert not bad, "Native dialogs remain:\n" + "\n".join(bad)

def test_referral_entry_is_static_and_desktop_ready():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "referrals_v33.css").read_text(encoding="utf-8")
    gate = (WEB / "subscription_gate_v32.js").read_text(encoding="utf-8")
    assert 'id="refGlobalEntry33"' in index
    assert 'id="refDesktopEntry33"' in index
    assert '@media(min-width:900px)' in css
    assert '.ref-desktop-entry33' in css
    assert '/static/referrals_v33.js?v=334' in gate
    assert '/static/v29.js?v=334' in gate
    assert '/static/corporation_dialogs_v33.js?v=334' in gate
    assert '/static/subscription_gate_v32.js?v=334' in index

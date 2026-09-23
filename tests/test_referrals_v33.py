import importlib.util
import os
import sys
import tempfile
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
TMP = tempfile.TemporaryDirectory()
os.environ['DB_PATH'] = str(Path(TMP.name) / 'test_referrals.db')
os.environ['APP_ENV'] = 'test'
os.environ['ALLOW_DEV_AUTH'] = '1'
os.environ['ALLOW_SUBSCRIPTION_DEV_BYPASS'] = '1'
os.environ['BOT_TOKEN'] = 'test-token'
os.environ.pop('RAILWAY_DEPLOYMENT_ID', None)
os.environ.pop('RAILWAY_PROJECT_ID', None)
os.environ.pop('RAILWAY_ENVIRONMENT_NAME', None)
os.environ.pop('RAILWAY_SERVICE_ID', None)
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location('corp_v33_app', ROOT / 'app.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def seed(uid, money=20000):
    app.ensure_player(uid, f'u{uid}')
    with app.closing(app.db()) as conn:
        conn.execute(
            'UPDATE players SET corp_name=?,money=? WHERE user_id=?',
            (f'Corp{uid}', float(money), int(uid)),
        )
        conn.commit()


def set_days(uid, count):
    with app.closing(app.db()) as conn:
        season = app._v33_current_season(conn)
        for i in range(count):
            conn.execute(
                'INSERT OR IGNORE INTO referral_active_days(season_id,user_id,day,first_seen_at) VALUES(?,?,?,?)',
                (season, int(uid), f'2026-09-{10 + i:02d}', 1_790_000_000 + i),
            )
        conn.commit()


def money(uid):
    with app.closing(app.db()) as conn:
        return float(conn.execute('SELECT money FROM players WHERE user_id=?', (int(uid),)).fetchone()['money'])


def expect_http(status, fn):
    try:
        fn()
    except HTTPException as exc:
        assert exc.status_code == status, (exc.status_code, exc.detail)
        return
    raise AssertionError(f'Expected HTTP {status}')


def main():
    inviter = 1001
    invitee = 2002
    other = 3003
    seed(inviter, 50_000)
    seed(invitee, 200_000)
    seed(other, 20_000)

    # Binding is unique and immutable within the season.
    bound = app._v33_bind_referral(invitee, inviter)
    assert bound['ok'] and not bound['already_bound']
    again = app._v33_bind_referral(invitee, inviter)
    assert again['already_bound']
    expect_http(409, lambda: app._v33_bind_referral(invitee, other))
    expect_http(400, lambda: app._v33_bind_referral(inviter, inviter))

    # Capital alone is not enough: five active days are also required.
    set_days(invitee, 4)
    assert app._v33_check_referral_reward(invitee) is False
    assert money(invitee) == 200_000
    assert money(inviter) == 50_000

    set_days(invitee, 5)
    assert app._v33_check_referral_reward(invitee) is True
    assert money(invitee) == 210_000
    assert money(inviter) == 70_000

    # Re-checking cannot pay the bonus a second time.
    assert app._v33_check_referral_reward(invitee) is False
    assert money(invitee) == 210_000
    assert money(inviter) == 70_000

    with app.closing(app.db()) as conn:
        season = app._v33_current_season(conn)
        ref = conn.execute(
            'SELECT * FROM referrals WHERE season_id=? AND invitee_id=?',
            (season, invitee),
        ).fetchone()
        event = conn.execute(
            'SELECT * FROM referral_reward_events WHERE season_id=? AND invitee_id=?',
            (season, invitee),
        ).fetchone()
        assert int(ref['rewarded_at']) > 0
        assert float(ref['invitee_reward']) == 10_000
        assert float(ref['inviter_reward']) == 20_000
        assert event is not None
        assert int(event['active_days']) == 5
        assert float(event['capitalization']) >= 200_000

    payload = app._v33_referral_payload(inviter)
    assert payload['friends_count'] == 1
    assert payload['rewarded_count'] == 1
    assert payload['friends'][0]['rewarded'] is True
    assert payload['friends'][0]['active_days'] == 5
    assert payload['friends'][0]['capital'] >= 200_000
    assert payload['referral_link'].endswith(f'?start=ref_{inviter}')

    print('V33 referral tests: OK')


if __name__ == '__main__':
    main()

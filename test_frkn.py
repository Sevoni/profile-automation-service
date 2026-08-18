import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import frkn_bot

TEST_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_out")
frkn_bot.CONFIG_PATH = os.path.join(TEST_OUT, "sub.txt")
frkn_bot.AWG_PATH = os.path.join(TEST_OUT, "awg.txt")
frkn_bot.AWG_ZIP_PATH = os.path.join(TEST_OUT, "awg_configs.zip")
frkn_bot.STATE_PATH = os.path.join(TEST_OUT, "sub_state.json")

calls = []


def fake_http_request(url, method="GET", body=None, headers=None, retries=None):
    calls.append(url)
    if "sub.frkn.org" in url:
        return 200, "#profile-title:_TEST\nhysteria2://x#Node1\nvless://y#Node2\n"
    if "amneziawg" in url:
        return 200, {"nodes": [
            {"config": "\n  [Interface]\n  PrivateKey = AAA\n\n  Jc = 7\n  I1 = <r 128>\n  I2 = \n  I3 = \n  I4 = \n  I5 = \n\n  [Peer]\n  Endpoint = 1.2.3.4:51820\n  # Suomi — conn_id: c1\n", "label": "Suomi2 🏴‍☠️ "},
            {"config": "[Interface]\nPrivateKey = BBB\nJc = 7\nI1 = <r 128>\nI2 = \nI3 = \nI4 = \nI5 = \n[Peer]\nEndpoint = 5.6.7.8:51820\n# NL — conn_id: c2\n", "label": "Suomi2 🏴‍☠️ "},
        ]}
    if "wireguard" in url:
        return 200, {"nodes": [
            {"config": "\n    [Interface]\n    PrivateKey = CCC\n    [Peer]\n    Endpoint = 94.198.54.132:51820\n    # Moscow — conn_id: c3\n    ", "label": "Moscow"},
        ]}
    return 404, {}


frkn_bot.http_request = fake_http_request
frkn_bot.fetch_and_publish("sub-test")

with open(frkn_bot.CONFIG_PATH, encoding="utf-8") as fh:
    sub = fh.read()
with open(frkn_bot.AWG_PATH, encoding="utf-8") as fh:
    awg = fh.read()
print("=== sub.txt ===")
print(sub)
print("=== awg.txt ===")
print(awg)
print("=== CALLS ===")
for c in calls:
    print(c)

# sub.txt: only URIs, no AWG
assert "hysteria2://x#Node1" in sub and "vless://y#Node2" in sub
assert "[Interface]" not in sub
assert "AmneziaWG" not in sub

# awg.txt: AWG (dev) + Moscow (ru), with overrides
assert "AmneziaWG (dev)" in awg
assert "WireGuard (ru)" in awg
assert "Moscow" in awg
assert f"I1 = {frkn_bot.AWG_I1}" in awg, "I1 not overridden"
for v in ["I2", "I3", "I4", "I5"]:
    assert awg.count(f"{v} = 0") == 2, f"{v} override count: {awg.count(f'{v} = 0')}"
assert "<r 128>" not in awg

# archive: 3 .conf files with unique names, overrides applied
with zipfile.ZipFile(frkn_bot.AWG_ZIP_PATH) as zf:
    names = zf.namelist()
    print("=== ARCHIVE ===", names)
    assert len(names) == 3, f"expected 3 configs, got {names}"
    assert len(set(names)) == 3, "duplicate filenames"
    assert any(n.startswith("Suomi2") for n in names)
    assert any(n.startswith("Suomi2_2") for n in names)
    assert "Moscow.conf" in names
    for name in names:
        content = zf.read(name).decode("utf-8")
        assert "[Interface]" in content
        if "Moscow" in name:
            assert "94.198.54.132:51820" in content
        else:
            assert f"I1 = {frkn_bot.AWG_I1}" in content
            assert "I2 = 0" in content
            assert "<r 128>" not in content

# exactly 2 API connection calls (no duplicate fetches)
awg_calls = sum("amneziawg" in c for c in calls)
ru_calls = sum("wireguard?id=" in c and "env=ru" in c for c in calls)
assert awg_calls == 1, f"amneziawg calls: {awg_calls}"
assert ru_calls == 1, f"ru wg calls: {ru_calls}"
print("PASS")
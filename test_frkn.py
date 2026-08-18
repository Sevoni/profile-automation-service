import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import frkn_bot

TEST_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_out")
frkn_bot.CONFIG_PATH = os.path.join(TEST_OUT, "sub.txt")
frkn_bot.STATE_PATH = os.path.join(TEST_OUT, "sub_state.json")

calls = []


def fake_http_request(url, method="GET", body=None, headers=None, retries=None):
    calls.append(url)
    if "sub.frkn.org" in url:
        return 200, "#profile-title:_TEST\nhysteria2://x#Node1\nvless://y#Node2\n"
    if "amneziawg" in url:
        return 200, {"nodes": [
            {"config": "\n  [Interface]\n  PrivateKey = AAA\n\n  Jc = 7\n  I1 = <r 128>\n  I2 = \n  I3 = \n  I4 = \n  I5 = \n\n  [Peer]\n  Endpoint = 1.2.3.4:51820\n  # Suomi — conn_id: c1\n", "label": "Suomi"},
            {"config": "[Interface]\nPrivateKey = BBB\nJc = 7\nI1 = <r 128>\nI2 = \nI3 = \nI4 = \nI5 = \n[Peer]\nEndpoint = 5.6.7.8:51820\n# NL — conn_id: c2\n", "label": "NL"},
        ]}
    if "wireguard" in url:
        return 200, {"nodes": [
            {"config": "\n    [Interface]\n    PrivateKey = CCC\n    [Peer]\n    Endpoint = 94.198.54.132:51820\n    # Moscow — conn_id: c3\n    ", "label": "Moscow"},
        ]}
    return 404, {}


frkn_bot.http_request = fake_http_request
frkn_bot.fetch_and_publish("sub-test")

with open(frkn_bot.CONFIG_PATH, encoding="utf-8") as fh:
    out = fh.read()
print(out)
print("=== CALLS ===")
for c in calls:
    print(c)
assert any("amneziawg?id=sub-test&env=dev" in c for c in calls), "missing awg call"
assert any("wireguard?id=sub-test&env=ru" in c for c in calls), "missing ru wg call"
assert "AmneziaWG (dev)" in out
assert "WireGuard (ru)" in out
assert "Moscow" in out
assert "1.2.3.4:51820" in out and "5.6.7.8:51820" in out
assert "94.198.54.132:51820" in out
assert f"I1 = {frkn_bot.AWG_I1}" in out, "I1 not overridden"
for v in ["I2", "I3", "I4", "I5"]:
    assert out.count(f"{v} = 0") == 2, f"{v} override count: {out.count(f'{v} = 0')}"
assert "<r 128>" not in out, "old I1 value still present"
assert not out.endswith("Moscow — conn_id: c3\n    ")
print("PASS")
#!/usr/bin/env python3
"""FRKN subscription bot: register on frkn.org with a plausible fake gmail ->
take subscription_id from the API response -> download config from
sub.frkn.org -> save to docs/sub.txt so GitHub Pages serves it."""

import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request

FRKN_API = "https://api.frkn.org"
SUB_BASE = "https://sub.frkn.org"
CONFIG_PATH = os.path.join("docs", "sub.txt")
STATE_PATH = "sub_state.json"

TRIAL_HOURS = 72
RENEW_BEFORE_HOURS = 1.5

REQUEST_RETRIES = 4
REQUEST_BACKOFF_SEC = 5
REGISTER_ATTEMPTS = 1   

AWG_ENV = "dev"
RU_WG_ENV = "ru"

AWG_I1 = (
    "<b 0xce000000010897a297ecc34cd6dd000044d0ec2e2e1ea2991f467ace4222129b5a098823784694b4897b9986ae0b7280135fa85e196d9ad980b150122129ce2a9379531b0fd3e871ca5fdb883c369832f730e272d7b8b74f393f9f0fa43f11e510ecb2219a52984410c204cf875585340c62238e14ad04dff382f2c200e0ee22fe743b9c6b8b043121c5710ec289f471c91ee414fca8b8be8419ae8ce7ffc53837f6ade262891895f3f4cecd31bc93ac5599e18e4f01b472362b8056c3172b513051f8322d1062997ef4a383b01706598d08d48c221d30e74c7ce000cdad36b706b1bf9b0607c32ec4b3203a4ee21ab64df336212b9758280803fcab14933b0e7ee1e04a7becce3e2633f4852585c567894a5f9efe9706a151b615856647e8b7dba69ab357b3982f554549bef9256111b2d67afde0b496f16962d4957ff654232aa9e845b61463908309cfd9de0a6abf5f425f577d7e5f6440652aa8da5f73588e82e9470f3b21b27b28c649506ae1a7f5f15b876f56abc4615f49911549b9bb39dd804fde182bd2dcec0c33bad9b138ca07d4a4a1650a2c2686acea05727e2a78962a840ae428f55627516e73c83dd8893b02358e81b524b4d99fda6df52b3a8d7a5291326e7ac9d773c5b43b8444554ef5aea104a738ed650aa979674bbed38da58ac29d87c29d387d80b526065baeb073ce65f075ccb56e47533aef357dceaa8293a523c5f6f790be90e4731123d3c6152a70576e90b4ab5bc5ead01576c68ab633ff7d36dcde2a0b2c68897e1acfc4d6483aaaeb635dd63c96b2b6a7a2bfe042f6aed82e5363aa850aace12ee3b1a93f30d8ab9537df483152a5527faca21efc9981b304f11fc95336f5b9637b174c5a0659e2b22e159a9fed4b8e93047371175b1d6d9cc8ab745f3b2281537d1c75fb9451871864efa5d184c38c185fd203de206751b92620f7c369e031d2041e152040920ac2c5ab5340bfc9d0561176abf10a147287ea90758575ac6a9f5ac9f390d0d5b23ee12af583383d994e22c0cf42383834bcd3ada1b3825a0664d8f3fb678261d57601ddf94a8a68a7c273a18c08aa99c7ad8c6c42eab67718843597ec9930457359dfdfbce024afc2dcf9348579a57d8d3490b2fa99f278f1c37d87dad9b221acd575192ffae1784f8e60ec7cee4068b6b988f0433d96d6a1b1865f4e155e9fe020279f434f3bf1bd117b717b92f6cd1cc9bea7d45978bcc3f24bda631a36910110a6ec06da35f8966c9279d130347594f13e9e07514fa370754d1424c0a1545c5070ef9fb2acd14233e8a50bfc5978b5bdf8bc1714731f798d21e2004117c61f2989dd44f0cf027b27d4019e81ed4b5c31db347c4a3a4d85048d7093cf16753d7b0d15e078f5c7a5205dc2f87e330a1f716738dce1c6180e9d02869b5546f1c4d2748f8c90d9693cba4e0079297d22fd61402dea32ff0eb69ebd65a5d0b687d87e3a8b2c42b648aa723c7c7daf37abcc4bb85caea2ee8f55bec20e913b3324ab8f5c3304f820d42ad1b9f2ffc1a3af9927136b4419e1e579ab4c2ae3c776d293d397d575df181e6cae0a4ada5d67ecea171cca3288d57c7bbdaee3befe745fb7d634f70386d873b90c4d6c6596bb65af68f9e5121e67ebf0d89d3c909ceedfb32ce9575a7758ff080724e1ab5d5f43074ecb53a479af21ed03d7b6899c36631c0166f9d47e5e1d4528a5d3d3f744029c4b1c190cbfbad06f5f83f7ad0429fa9a2719c56ffe3783460e166de2d8>"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

FIRST_NAMES_MALE = [
    "ivan", "alexey", "alexandr", "dmitry", "sergey", "andrey", "mikhail",
    "nikolay", "vladimir", "pavel", "evgeny", "artem", "anton", "oleg",
    "igor", "roman", "maxim", "denis", "viktor", "yuriy", "vasily",
    "konstantin", "timofey", "grigory", "bogdan", "daniil", "egor", "ilya",
    "kirill", "leonid", "mark", "matvey", "ruslan", "semyon", "stanislav",
    "timur", "vadim", "valeriy", "yaroslav", "georgy", "gleb", "boris",
    "anatoly", "gennady", "vladislav", "fedor", "pyotr", "stepan", "arkady",
    "german", "edvard", "albert", "david", "emil", "filipp",
]

LAST_NAMES_MALE = [
    "smirnov", "ivanov", "kuznetsov", "popov", "sokolov", "lebedev",
    "kozlov", "novikov", "morozov", "petrov", "volkov", "solovyev",
    "vasilyev", "zaitsev", "pavlov", "semenov", "golubev", "vinogradov",
    "bogdanov", "vorobyev", "fedorov", "mikhailov", "belyaev", "tarasov",
    "belov", "komarov", "orlov", "kiselev", "makarov", "andreev",
    "kovalev", "ilyin", "gusev", "titov", "tikhomirov", "kozhevnikov",
    "nikitin", "stepanov", "mironov", "karpov", "efimov", "lazarev",
    "medvedev", "eremin", "danilov", "yakovlev", "gromov", "kirillov",
    "sorokin", "terentyev", "doronin", "glazkov", "konovalov", "maslov",
    "sergeev", "romanov",
]

FIRST_NAMES_FEMALE = [
    "anna", "elena", "olga", "irina", "svetlana", "tatiana", "ekaterina",
    "maria", "daria", "anastasia", "julia", "oksana", "lydia", "vera",
    "nadezhda", "lyudmila", "galina", "valentina", "tamara", "raisa",
    "nina", "zinaida", "polina", "alina", "kristina", "victoria", "sofia",
    "evgenia", "elizaveta", "ksenia", "veronika", "milana", "alisa",
    "diana", "margarita", "valeriya", "yana", "eva", "alexandra",
    "uliana", "angelina", "karina", "regina", "rosa", "sabina", "aliona",
    "emma", "larisa", "elvira", "zoya", "inessa", "vladislava", "ruslana",
]

LAST_NAMES_FEMALE = [
    "smirnova", "ivanova", "kuznetsova", "popova", "sokolova", "lebedeva",
    "kozlova", "novikova", "morozova", "petrova", "volkova", "solovyeva",
    "vasilyeva", "zaitseva", "pavlova", "semenova", "golubeva",
    "vinogradova", "bogdanova", "vorobyeva", "fedorova", "mikhailova",
    "belyaeva", "tarasova", "belova", "komarova", "orlova", "kiseleva",
    "makarova", "andreeva", "kovaleva", "ilyina", "guseva", "titova",
    "tikhomirova", "kozhevnikova", "nikitina", "stepanova", "mironova",
    "karpova", "efimova", "lazareva", "medvedeva", "eremina", "danilova",
    "yakovleva", "gromova", "kirillova", "sorokina", "terentyeva",
    "doronina", "glazkova", "konovalova", "maslova", "sergeeva", "romanova",
]


def generate_email():
    if random.random() < 0.5:
        first = random.choice(FIRST_NAMES_MALE)
        last = random.choice(LAST_NAMES_MALE)
    else:
        first = random.choice(FIRST_NAMES_FEMALE)
        last = random.choice(LAST_NAMES_FEMALE)
    number = random.choice(
        [str(random.randint(1, 999)), str(random.randint(1970, 2005))]
    )
    return f"{first}{last}{number}@gmail.com"


def http_request(
    url,
    method="GET",
    body=None,
    headers=None,
    retries=REQUEST_RETRIES,
):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if data is not None:
        req_headers["Content-Type"] = "application/json"
    if headers:
        req_headers.update(headers)

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(
                url, data=data, headers=req_headers, method=method
            )
            with urllib.request.urlopen(request, timeout=30) as resp:
                raw = resp.read()
                try:
                    return resp.status, json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    return resp.status, raw.decode("utf-8")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(REQUEST_BACKOFF_SEC * attempt)
    raise RuntimeError(f"Request failed for {url}: {last_err}")


def frkn_register(email):
    status, data = http_request(
        f"{FRKN_API}/account",
        method="POST",
        body={"email": email, "language": "ru", "trial": True},
    )
    if status not in (200, 201):
        raise RuntimeError(f"frkn: registration failed (HTTP {status}): {data}")
    return data


def download_subscription_config(sub_id):
    url = f"{SUB_BASE}/{sub_id}"
    status, data = http_request(
        url, headers={"Accept": "text/plain, */*;q=0.5"}
    )
    if status != 200:
        raise RuntimeError(
            f"sub.frkn.org: failed to fetch config (HTTP {status}): {data}"
        )
    if isinstance(data, dict):
        data = json.dumps(data, ensure_ascii=False)
    return str(data)


def download_connection_configs(sub_id, protocol, env):
    url = f"{FRKN_API}/info/connections/{protocol}?id={sub_id}&env={env}"
    status, data = http_request(url)
    if status != 200:
        raise RuntimeError(
            f"frkn: failed to fetch {protocol} configs (HTTP {status}): {data}"
        )
    nodes = (data or {}).get("nodes") if isinstance(data, dict) else None
    if not isinstance(nodes, list) or not nodes:
        raise RuntimeError(f"frkn: {protocol} ({env}) returned no configs")
    return [str(node["config"]).strip() for node in nodes]


def apply_awg_overrides(config_text):
    lines = []
    for line in config_text.split("\n"):
        if re.match(r"^\s*I1\s*=", line):
            lines.append(f"{line.split('=', 1)[0].rstrip()} = {AWG_I1}")
        elif re.match(r"^\s*I[2-5]\s*=", line):
            lines.append(f"{line.split('=', 1)[0].rstrip()} = 0")
        else:
            lines.append(line)
    return "\n".join(lines)


def build_extra_configs(sub_id):
    sections = []
    try:
        awg = [
            apply_awg_overrides(config)
            for config in download_connection_configs(sub_id, "amneziawg", AWG_ENV)
        ]
        sections.append(f"\n# ===== AmneziaWG ({AWG_ENV}) =====\n\n" + "\n\n".join(awg))
    except RuntimeError as exc:
        print(f"Warning: no AmneziaWG configs ({exc})", file=sys.stderr)
    try:
        ru_wg = download_connection_configs(sub_id, "wireguard", RU_WG_ENV)
        sections.append(f"\n# ===== WireGuard ({RU_WG_ENV}) =====\n\n" + "\n\n".join(ru_wg))
    except RuntimeError as exc:
        print(f"Warning: no WireGuard {RU_WG_ENV} configs ({exc})", file=sys.stderr)
    if not sections:
        return None
    return "\n".join(sections)


def fetch_and_publish(sub_id):
    config_text = download_subscription_config(sub_id)
    extra = build_extra_configs(sub_id)
    if extra:
        config_text = config_text.rstrip("\n") + "\n" + extra + "\n"
    publish_config(config_text)


def publish_config(config_text):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        fh.write(config_text)
    print(f"Config written to {CONFIG_PATH} ({len(config_text)} bytes)")


def read_state():
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(sub_id, created_at):
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump({"subscription_id": sub_id, "created_at": created_at}, fh)
    print(f"State saved to {STATE_PATH}")


def should_renew(state):
    sub_id = state.get("subscription_id")
    created_at = state.get("created_at")
    if not sub_id or not created_at:
        return True
    age_hours = (time.time() - created_at) / 3600
    return age_hours >= TRIAL_HOURS - RENEW_BEFORE_HOURS


def register_subscription():
    for attempt in range(1, REGISTER_ATTEMPTS + 1):
        email = generate_email()
        print(f"Registering with {email} (attempt {attempt}) ...")
        try:
            api_resp = frkn_register(email)
        except RuntimeError as exc:
            print(f"Registration failed: {exc}", file=sys.stderr)
            continue
        api_id = (api_resp or {}).get("subscription_id")
        if api_id:
            return api_id
        print(
            f"API returned no subscription_id (attempt {attempt})",
            file=sys.stderr,
        )
    return None


def main():
    state = read_state()
    if not should_renew(state):
        sub_id = state["subscription_id"]
        print(f"Subscription ID: {sub_id} (refreshing config)")
        try:
            fetch_and_publish(sub_id)
            return
        except RuntimeError as exc:
            print(
                f"Subscription {sub_id} unavailable ({exc}); registering a new one",
                file=sys.stderr,
            )

    sub_id = register_subscription()
    if not sub_id:
        print("ERROR: could not obtain subscription ID", file=sys.stderr)
        sys.exit(1)

    print(f"Subscription ID: {sub_id}")
    write_state(sub_id, int(time.time()))
    fetch_and_publish(sub_id)


if __name__ == "__main__":
    main()
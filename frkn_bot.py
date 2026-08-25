#!/usr/bin/env python3
"""FRKN subscription bot: register on frkn.org with a plausible fake gmail ->
take subscription_id from the API response -> download config from
sub.frkn.org -> save to docs/sub.txt so GitHub Pages serves it."""

import base64
import hashlib
import hmac
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

FRKN_API = "https://api.frkn.org"
SUB_BASE = "https://sub.frkn.org"
CONFIG_PATH = os.path.join("docs", "sub.txt")
AWG_PATH = os.path.join("docs", "awg.txt")
AWG_ZIP_PATH = os.path.join("docs", "awg_configs.zip")
CLASH_YAML_PATH = os.path.join("docs", "clash.yaml")
CLASH_AGE_PATH = os.path.join("docs", "clash.yaml.age")
STATE_PATH = "sub_state.json"

DEFAULT_AGE_PUBLIC_KEY = (
    "age15j00qgx4zqqqgtfnzlj2e2740t856jypnufmzkra7kzv3lapqs4q4qypej"
)
AGE_PUBLIC_KEY = os.environ.get("AGE_PUBLIC_KEY", DEFAULT_AGE_PUBLIC_KEY)

AUTO_GROUP_NAME = "⚡️ Авто"
VPN_GROUP_NAME = "🛡️ VPN"

TRIAL_HOURS = 72
RENEW_BEFORE_HOURS = 1.5

REQUEST_RETRIES = 4
REQUEST_BACKOFF_SEC = 5
REGISTER_ATTEMPTS = 1   

AWG_ENV = "dev"

AWG_I1 = (
    "<b 0xce000000010897a297ecc34cd6dd000044d0ec2e2e1ea2991f467ace4222129b5a098823784694b4897b9986ae0b7280135fa85e196d9ad980b150122129ce2a9379531b0fd3e871ca5fdb883c369832f730e272d7b8b74f393f9f0fa43f11e510ecb2219a52984410c204cf875585340c62238e14ad04dff382f2c200e0ee22fe743b9c6b8b043121c5710ec289f471c91ee414fca8b8be8419ae8ce7ffc53837f6ade262891895f3f4cecd31bc93ac5599e18e4f01b472362b8056c3172b513051f8322d1062997ef4a383b01706598d08d48c221d30e74c7ce000cdad36b706b1bf9b0607c32ec4b3203a4ee21ab64df336212b9758280803fcab14933b0e7ee1e04a7becce3e2633f4852585c567894a5f9efe9706a151b615856647e8b7dba69ab357b3982f554549bef9256111b2d67afde0b496f16962d4957ff654232aa9e845b61463908309cfd9de0a6abf5f425f577d7e5f6440652aa8da5f73588e82e9470f3b21b27b28c649506ae1a7f5f15b876f56abc4615f49911549b9bb39dd804fde182bd2dcec0c33bad9b138ca07d4a4a1650a2c2686acea05727e2a78962a840ae428f55627516e73c83dd8893b02358e81b524b4d99fda6df52b3a8d7a5291326e7ac9d773c5b43b8444554ef5aea104a738ed650aa979674bbed38da58ac29d87c29d387d80b526065baeb073ce65f075ccb56e47533aef357dceaa8293a523c5f6f790be90e4731123d3c6152a70576e90b4ab5bc5ead01576c68ab633ff7d36dcde2a0b2c68897e1acfc4d6483aaaeb635dd63c96b2b6a7a2bfe042f6aed82e5363aa850aace12ee3b1a93f30d8ab9537df483152a5527faca21efc9981b304f11fc95336f5b9637b174c5a0659e2b22e159a9fed4b8e93047371175b1d6d9cc8ab745f3b2281537d1c75fb9451871864efa5d184c38c185fd203de206751b92620f7c369e031d2041e152040920ac2c5ab5340bfc9d0561176abf10a147287ea90758575ac6a9f5ac9f390d0d5b23ee12af583383d994e22c0cf42383834bcd3ada1b3825a0664d8f3fb678261d57601ddf94a8a68a7c273a18c08aa99c7ad8c6c42eab67718843597ec9930457359dfdfbce024afc2dcf9348579a57d8d3490b2fa99f278f1c37d87dad9b221acd575192ffae1784f8e60ec7cee4068b6b988f0433d96d6a1b1865f4e155e9fe020279f434f3bf1bd117b717b92f6cd1cc9bea7d45978bcc3f24bda631a36910110a6ec06da35f8966c9279d130347594f13e9e07514fa370754d1424c0a1545c5070ef9fb2acd14233e8a50bfc5978b5bdf8bc1714731f798d21e2004117c61f2989dd44f0cf027b27d4019e81ed4b5c31db347c4a3a4d85048d7093cf16753d7b0d15e078f5c7a5205dc2f87e330a1f716738dce1c6180e9d02869b5546f1c4d2748f8c90d9693cba4e0079297d22fd61402dea32ff0eb69ebd65a5d0b687d87e3a8b2c42b648aa723c7c7daf37abcc4bb85caea2ee8f55bec20e913b3324ab8f5c3304f820d42ad1b9f2ffc1a3af9927136b4419e1e579ab4c2ae3c776d293d397d575df181e6cae0a4ada5d67ecea171cca3288d57c7bbdaee3befe745fb7d634f70386d873b90c4d6c6596bb65af68f9e5121e67ebf0d89d3c909ceedfb32ce9575a7758ff080724e1ab5d5f43074ecb53a479af21ed03d7b6899c36631c0166f9d47e5e1d4528a5d3d3f744029c4b1c190cbfbad06f5f83f7ad0429fa9a2719c56ffe3783460e166de2d8>"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

CLASH_BASE = {
    "mode": "rule",
    "ipv6": False,
    "log-level": "warning",
    "allow-lan": True,
    "bind-address": "*",
    "unified-delay": True,
    "tcp-concurrent": True,
    "mixed-port": 7890,
    "external-controller": "127.0.0.1:9090",
    "dns": {
        "enable": True,
        "listen": "127.0.0.1:1053",
        "ipv6": False,
        "enhanced-mode": "fake-ip",
        "fake-ip-range": "198.18.0.1/16",
        "default-nameserver": [
            "system",
            "9.9.9.9",
            "77.88.8.8",
            "83.220.169.155",
        ],
        "nameserver": [
            "https://dns.comss.one/dns-query",
            "83.220.169.155",
            "212.109.195.93",
            "195.133.25.16",
        ],
        "nameserver-policy": {
            "+.ru": ["system", "9.9.9.9", "149.112.112.112", "77.88.8.8"],
            "+.su": ["system", "9.9.9.9", "149.112.112.112", "77.88.8.8"],
            "+.\u0440\u0444": [
                "system",
                "9.9.9.9",
                "149.112.112.112",
                "77.88.8.8",
            ],
        },
    },
    "tun": {
        "enable": True,
        "stack": "mixed",
        "auto-route": True,
        "auto-detect-interface": True,
        "strict-route": True,
        "mtu": 1280,
        "dns-hijack": ["any:53"],
    },
    "rules": [
        "IP-CIDR,8.39.125.7/32,DIRECT,no-resolve",
        "GEOIP,private,DIRECT,no-resolve",
        "IP-CIDR,127.0.0.0/8,DIRECT,no-resolve",
        "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
        "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
        "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
        "DOMAIN-SUFFIX,ru,DIRECT",
        "DOMAIN-SUFFIX,su,DIRECT",
        "DOMAIN-SUFFIX,xn--p1ai,DIRECT",
        "GEOIP,RU,DIRECT",
        "MATCH,\U0001f6e1\ufe0f VPN",
    ],
}

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
    return [
        {
            "label": str(node.get("label", "")).strip(),
            "config": str(node["config"]).strip(),
        }
        for node in nodes
    ]


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


def fetch_awg(sub_id):
    awg_nodes = []
    try:
        awg_nodes = download_connection_configs(sub_id, "amneziawg", AWG_ENV)
    except RuntimeError as exc:
        print(f"Warning: no AmneziaWG configs ({exc})", file=sys.stderr)
    return awg_nodes


def build_extra_text(awg_nodes):
    if not awg_nodes:
        return None
    awg = [apply_awg_overrides(node["config"]) for node in awg_nodes]
    return f"\n# ===== AmneziaWG ({AWG_ENV}) =====\n\n" + "\n\n".join(awg)


def sanitize_label(label):
    name = re.sub(r"[^\w\-]+", "_", label).strip("_")
    return name or "node"


def build_awg_zip(awg_nodes):
    entries = []
    used = set()
    for node in awg_nodes:
        base = sanitize_label(node["label"])
        name = base
        i = 2
        while name in used:
            name = f"{base}_{i}"
            i += 1
        used.add(name)
        entries.append((f"{name}.conf", apply_awg_overrides(node["config"])))
    if not entries:
        return False
    os.makedirs(os.path.dirname(AWG_ZIP_PATH), exist_ok=True)
    with zipfile.ZipFile(AWG_ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, config in entries:
            zf.writestr(name, config)
    print(f"Archive written to {AWG_ZIP_PATH} ({len(entries)} configs)")
    return True


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Config written to {path} ({len(text)} bytes)")


def write_bytes(path, blob):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(blob)
    print(f"Config written to {path} ({len(blob)} bytes)")


def unique_name(name, used):
    base = name.strip() or "proxy"
    candidate = base
    i = 2
    while candidate in used:
        candidate = f"{base} #{i}"
        i += 1
    used.add(candidate)
    return candidate


def parse_awg_config(config_text, label):
    sections = {}
    section = None
    for line in config_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("["):
            name = stripped.strip("[]").strip().lower()
            if name == "interface" and sections.get("interface"):
                break
            section = name
            sections.setdefault(section, {})
            continue
        if section is None or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        sections[section][key.strip().upper()] = value.strip()

    iface = sections.get("interface", {})
    peer = sections.get("peer", {})

    endpoint = peer.get("ENDPOINT", "")
    host, sep, port_str = endpoint.rpartition(":")
    if not sep or not host:
        raise ValueError(f"AWG config {label!r}: bad endpoint {endpoint!r}")

    address = iface.get("ADDRESS", "").split(",")[0].strip()
    local_ip = address.split("/")[0].strip()
    if not local_ip:
        raise ValueError(f"AWG config {label!r}: no Address")

    awg_option = {}
    for key in (
        "JC", "JMIN", "JMAX",
        "S1", "S2", "S3", "S4",
        "H1", "H2", "H3", "H4",
        "I1", "I2", "I3", "I4", "I5",
    ):
        raw = iface.get(key)
        if raw is None or raw == "":
            continue
        awg_option[key.lower()] = int(raw) if raw.isdigit() else raw

    allowed_ips = [
        cidr.strip()
        for cidr in peer.get("ALLOWEDIPS", "").split(",")
        if cidr.strip()
    ]

    proxy = {
        "name": label,
        "type": "wireguard",
        "server": host.strip(),
        "port": int(port_str),
        "ip": local_ip,
        "private-key": iface.get("PRIVATEKEY", ""),
        "public-key": peer.get("PUBLICKEY", ""),
        "udp": True,
    }
    mtu = iface.get("MTU")
    if mtu and mtu.isdigit():
        proxy["mtu"] = int(mtu)
    if allowed_ips:
        proxy["allowed-ips"] = allowed_ips
    if awg_option:
        proxy["amnezia-wg-option"] = awg_option
    return proxy


def parse_share_link(link):
    scheme, _, rest = link.partition("://")
    if not _:
        return None
    scheme = scheme.lower()

    fragment_sep = rest.find("#")
    if fragment_sep >= 0:
        name = urllib.parse.unquote(rest[fragment_sep + 1:]).strip()
        rest = rest[:fragment_sep]
    else:
        name = ""

    userinfo_sep = rest.rfind("@")
    if userinfo_sep >= 0:
        credential = urllib.parse.unquote(rest[:userinfo_sep])
        hostport = rest[userinfo_sep + 1:]
    else:
        credential = ""
        hostport = rest

    query_sep = hostport.find("?")
    if query_sep >= 0:
        query = dict(
            urllib.parse.parse_qsl(hostport[query_sep + 1:], keep_blank_values=True)
        )
        hostport = hostport[:query_sep]
    else:
        query = {}

    host, sep, port_str = hostport.rpartition(":")
    if not sep or not host:
        return None

    if scheme == "hysteria2":
        proxy = {
            "name": name,
            "type": "hysteria2",
            "server": host,
            "port": int(port_str),
            "password": credential,
            "skip-cert-verify": query.get("insecure", "").lower() == "true",
        }
        sni = query.get("sni")
        if sni:
            proxy["sni"] = sni
        for src, dst in (("up-mbps", "up"), ("down-mbps", "down")):
            value = query.get(src)
            if value and value.isdigit() and int(value) > 0:
                proxy[dst] = int(value)
        obfs_password = query.get("obfs-password")
        if obfs_password:
            proxy["obfs"] = query.get("obfs", "salamander")
            proxy["obfs-password"] = obfs_password
        return proxy

    if scheme == "vless":
        transport = query.get("type", "tcp").lower()
        if transport == "xhttp":
            return None
        security = query.get("security", "none").lower()
        proxy = {
            "name": name,
            "type": "vless",
            "server": host,
            "port": int(port_str),
            "uuid": credential,
            "udp": True,
        }
        if security in ("tls", "reality"):
            proxy["tls"] = True
            sni = query.get("sni") or query.get("host")
            if sni:
                proxy["servername"] = sni
            fp = query.get("fp")
            if fp:
                proxy["client-fingerprint"] = fp
        if security == "reality":
            reality_opts = {}
            if query.get("pbk"):
                reality_opts["public-key"] = query["pbk"]
            if query.get("sid"):
                reality_opts["short-id"] = query["sid"]
            if reality_opts:
                proxy["reality-opts"] = reality_opts
        flow = query.get("flow")
        if flow:
            proxy["flow"] = flow
        if transport == "grpc":
            proxy["network"] = "grpc"
            service_name = query.get("serviceName")
            if service_name:
                proxy["grpc-opts"] = {"grpc-service-name": service_name}
        elif transport == "ws":
            proxy["network"] = "ws"
            ws_opts = {"path": urllib.parse.unquote(query.get("path", "/"))}
            if query.get("host"):
                ws_opts["headers"] = {"Host": query["host"]}
            proxy["ws-opts"] = ws_opts
        return proxy

    return None


def collect_sub_proxies(sub_text, used_names):
    proxies = []
    for line in sub_text.splitlines():
        link = line.strip()
        if not link or link.startswith("#"):
            continue
        try:
            proxy = parse_share_link(link)
        except (ValueError, KeyError) as exc:
            print(f"Warning: skip bad link ({exc})", file=sys.stderr)
            continue
        if proxy is None:
            print(
                f"Warning: unsupported share link skipped: "
                f"{link.split('://', 1)[0]}://...",
                file=sys.stderr,
            )
            continue
        proxy["name"] = unique_name(proxy["name"], used_names)
        proxies.append(proxy)
    return proxies


def build_clash_config(awg_nodes, sub_text):
    import yaml

    used_names = set()
    proxies = []
    for node in awg_nodes:
        try:
            proxy = parse_awg_config(
                apply_awg_overrides(node["config"]), node["label"]
            )
        except (ValueError, KeyError) as exc:
            print(f"Warning: skip AWG node ({exc})", file=sys.stderr)
            continue
        proxy["name"] = unique_name(proxy["name"], used_names)
        proxies.append(proxy)

    proxies.extend(collect_sub_proxies(sub_text, used_names))

    auto_group = {
        "name": AUTO_GROUP_NAME,
        "type": "url-test",
        "tolerance": 100,
        "url": "https://www.gstatic.com/generate_204",
        "interval": 15,
        "include-all": True,
        "hidden": True,
    }
    vpn_group = {
        "name": VPN_GROUP_NAME,
        "type": "select",
        "proxies": [AUTO_GROUP_NAME, "DIRECT"]
        + [proxy["name"] for proxy in proxies],
    }

    config = dict(CLASH_BASE)
    config["proxies"] = proxies
    config["proxy-groups"] = [auto_group, vpn_group]
    return yaml.dump(
        config, allow_unicode=True, sort_keys=False, width=1000000
    )


BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32_GENERATOR = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)


def _bech32_polymod(values):
    chk = 1
    for value in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ value
        for i in range(5):
            if (top >> i) & 1:
                chk ^= BECH32_GENERATOR[i]
    return chk


def _bech32_hrp_expand(hrp):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _bech32_convert_bits(data, from_bits, to_bits, pad=True):
    acc = 0
    bits = 0
    ret = []
    maxv = (1 << to_bits) - 1
    max_acc = (1 << (from_bits + to_bits - 1)) - 1
    for value in data:
        acc = ((acc << from_bits) | value) & max_acc
        bits += from_bits
        while bits >= to_bits:
            bits -= to_bits
            ret.append((acc >> bits) & maxv)
    if pad and bits:
        ret.append((acc << (to_bits - bits)) & maxv)
    elif pad is False and bits >= from_bits:
        raise ValueError("Invalid padding")
    return ret


def bech32_decode(address):
    address = address.strip().lower()
    pos = address.rfind("1")
    if pos < 1:
        raise ValueError("bad bech32 address")
    hrp = address[:pos]
    data = []
    for char in address[pos + 1:]:
        idx = BECH32_CHARSET.find(char)
        if idx < 0:
            raise ValueError(f"bad bech32 character {char!r}")
        data.append(idx)
    if _bech32_polymod(_bech32_hrp_expand(hrp) + data) != 1:
        raise ValueError("bad bech32 checksum")
    return bytes(_bech32_convert_bits(data[:-6], 5, 8, pad=False))


AGE_HEADER_FIRST_LINE = "age-encryption.org/v1"
AGE_X25519_INFO = b"age-encryption.org/v1/X25519"
AGE_HKDF_INFO_HEADER = b"header"
AGE_HKDF_INFO_PAYLOAD = b"payload"
AGE_CHUNK_SIZE = 64 * 1024


def encrypt_age(data, recipient):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric.x25519 import (
        X25519PrivateKey,
        X25519PublicKey,
    )
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        PublicFormat,
    )

    recipient_pub = bech32_decode(recipient)
    if len(recipient_pub) != 32:
        raise ValueError("age recipient key must be 32 bytes")

    file_key = os.urandom(16)

    ephemeral = X25519PrivateKey.generate()
    ephemeral_pub = ephemeral.public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw
    )
    shared_secret = ephemeral.exchange(
        X25519PublicKey.from_public_bytes(recipient_pub)
    )

    wrap_salt = ephemeral_pub + recipient_pub
    wrap_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=wrap_salt,
        info=AGE_X25519_INFO,
    ).derive(shared_secret)
    wrapped = ChaCha20Poly1305(wrap_key).encrypt(
        b"\x00" * 12, file_key, None
    )

    def b64raw(raw):
        return base64.b64encode(raw).decode("ascii").rstrip("=")

    header = (
        f"{AGE_HEADER_FIRST_LINE}\n"
        f"-> X25519 {b64raw(ephemeral_pub)}\n"
        f"{b64raw(wrapped)}\n"
        "---"
    )

    mac_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=AGE_HKDF_INFO_HEADER,
    ).derive(file_key)
    mac = hmac.new(mac_key, header.encode("ascii"), hashlib.sha256).digest()

    stream_nonce = os.urandom(16)
    payload_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=stream_nonce,
        info=AGE_HKDF_INFO_PAYLOAD,
    ).derive(file_key)
    aead = ChaCha20Poly1305(payload_key)

    body = bytearray()
    total_chunks = max(1, -(-len(data) // AGE_CHUNK_SIZE))
    for index in range(total_chunks):
        chunk = data[index * AGE_CHUNK_SIZE:(index + 1) * AGE_CHUNK_SIZE]
        is_final = index == total_chunks - 1
        nonce = index.to_bytes(11, "big") + (b"\x01" if is_final else b"\x00")
        body += aead.encrypt(nonce, chunk, None)

    return (
        header.encode("ascii")
        + b" "
        + b64raw(mac).encode("ascii")
        + b"\n"
        + stream_nonce
        + bytes(body)
    )


def fetch_and_publish(sub_id):
    awg_nodes = fetch_awg(sub_id)

    config_text = download_subscription_config(sub_id)
    publish_config(config_text)

    extra = build_extra_text(awg_nodes)
    if extra:
        write_text(AWG_PATH, extra + "\n")
    else:
        write_text(AWG_PATH, "# no AmneziaWG configs\n")

    if not build_awg_zip(awg_nodes):
        print("Warning: no configs for archive", file=sys.stderr)
        if os.path.exists(AWG_ZIP_PATH):
            os.remove(AWG_ZIP_PATH)

    clash_text = build_clash_config(awg_nodes, config_text)
    write_text(CLASH_YAML_PATH, clash_text)

    # Шифрование age временно отключено (проверка yaml-конфига).
    # if AGE_PUBLIC_KEY:
    #     try:
    #         blob = encrypt_age(clash_text.encode("utf-8"), AGE_PUBLIC_KEY)
    #     except Exception as exc:
    #         print(f"Warning: age encryption failed ({exc})", file=sys.stderr)
    #     else:
    #         write_bytes(CLASH_AGE_PATH, blob)
    # else:
    #     print(
    #         "Warning: AGE_PUBLIC_KEY not set, skip clash.yaml.age",
    #         file=sys.stderr,
    #     )


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
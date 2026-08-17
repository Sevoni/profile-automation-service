#!/usr/bin/env python3
"""FRKN subscription bot: register on frkn.org with a plausible fake gmail ->
take subscription_id from the API response -> download config from
sub.frkn.org -> save to docs/sub.txt so GitHub Pages serves it."""

import json
import os
import random
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
REGISTER_ATTEMPTS = 3

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
            config_text = download_subscription_config(sub_id)
            publish_config(config_text)
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
    config_text = download_subscription_config(sub_id)
    publish_config(config_text)


if __name__ == "__main__":
    main()
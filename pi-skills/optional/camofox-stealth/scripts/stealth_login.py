#!/usr/bin/env python3
"""stealth_login — establish a logged-in session in the local Camoufox server.

Two paths, both usable on native Windows (where the noVNC login flow does NOT
work — the server forces headless off-Linux):

  cookies <domain>            Reuse the login you already have in your normal
                              browser: read that domain's cookies and inject
                              them into Camoufox. No password touched. Best.

  store <domain> <user>       Save credentials to the OS keychain (Windows
                              Credential Manager / macOS Keychain / Secret
                              Service). Password read from stdin or getpass —
                              never from argv, never through the model.

  fill <domain> <login_url>   Pull stored credentials and drive the login form
                              (type user/pass, submit). Best-effort: fails on
                              captcha/2FA (unavoidable, headless has no UI).

The model never sees a password: `store` reads it out-of-band; `fill` reads it
from the keychain. Only the resulting session cookies live in Camoufox.

Optional deps (installed only when a path needs them):
  pip install browser_cookie3   # cookies path
  pip install keyring           # store/fill paths
"""
import argparse
import getpass
import json
import sys
import urllib.request

SERVER = "http://127.0.0.1:9377"
USER_ID = "recon"
SESSION_KEY = "r1"
KEYRING_SERVICE_PREFIX = "camofox-stealth"


def _post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SERVER + path, data=data,
        headers={"Content-Type": "application/json; charset=utf-8"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8") or "{}")


def _server_up():
    try:
        with urllib.request.urlopen(SERVER + "/health", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def cmd_cookies(args):
    try:
        import browser_cookie3
    except ImportError:
        print("ERROR: browser_cookie3 not installed. Run: pip install browser_cookie3", file=sys.stderr)
        return 3
    loaders = {
        "firefox": getattr(browser_cookie3, "firefox", None),
        "chrome": getattr(browser_cookie3, "chrome", None),
        "edge": getattr(browser_cookie3, "edge", None),
    }
    order = [args.browser] if args.browser != "auto" else ["firefox", "chrome", "edge"]
    jar = None
    used = None
    for name in order:
        fn = loaders.get(name)
        if not fn:
            continue
        try:
            jar = fn(domain_name=args.domain)
            used = name
            if list(jar):
                break
        except Exception as e:
            print(f"[{name}] could not read cookies: {e}", file=sys.stderr)
    cookies = []
    for c in (jar or []):
        cookies.append({
            "name": c.name, "value": c.value,
            "domain": c.domain, "path": c.path or "/",
            "secure": bool(c.secure),
            "expires": int(c.expires) if c.expires else -1,
        })
    if not cookies:
        print(f"No cookies found for '{args.domain}' in {order}. "
              f"Log into the site in your browser first (Firefox most reliable).", file=sys.stderr)
        return 4
    if not _server_up():
        print("ERROR: stealth server not running. Run recon.sh ensure first.", file=sys.stderr)
        return 2
    _post(f"/sessions/{USER_ID}/cookies", {"cookies": cookies})
    print(f"Injected {len(cookies)} cookies for '{args.domain}' from {used}. "
          f"web_open on that site now carries the login.")
    return 0


def _keyring():
    try:
        import keyring
        return keyring
    except ImportError:
        print("ERROR: keyring not installed. Run: pip install keyring", file=sys.stderr)
        return None


def cmd_store(args):
    kr = _keyring()
    if not kr:
        return 3
    # Password from stdin (piped, one line) or interactive getpass — never argv.
    if not sys.stdin.isatty():
        password = sys.stdin.readline().rstrip("\n")
    else:
        password = getpass.getpass(f"Password for {args.username}@{args.domain} (not echoed): ")
    if not password:
        print("ERROR: empty password.", file=sys.stderr)
        return 5
    service = f"{KEYRING_SERVICE_PREFIX}:{args.domain}"
    kr.set_password(service, "__username__", args.username)
    kr.set_password(service, args.username, password)
    print(f"Stored credentials for {args.username}@{args.domain} in the OS keychain.")
    return 0


def _get_tab(url):
    r = _post("/tabs", {"userId": USER_ID, "sessionKey": SESSION_KEY, "url": url})
    return r.get("tabId")


def cmd_fill(args):
    kr = _keyring()
    if not kr:
        return 3
    service = f"{KEYRING_SERVICE_PREFIX}:{args.domain}"
    username = kr.get_password(service, "__username__")
    password = kr.get_password(service, username) if username else None
    if not username or not password:
        print(f"No stored credentials for '{args.domain}'. Run: stealth_login.py store {args.domain} <user>",
              file=sys.stderr)
        return 4
    if not _server_up():
        print("ERROR: stealth server not running. Run recon.sh ensure first.", file=sys.stderr)
        return 2
    tab = _get_tab(args.login_url)
    if not tab:
        print("ERROR: could not open login page.", file=sys.stderr)
        return 6
    # Best-effort selectors: common username/email + password fields.
    _post(f"/tabs/{tab}/type", {"userId": USER_ID, "selector": args.user_selector, "text": username})
    _post(f"/tabs/{tab}/type", {"userId": USER_ID, "selector": args.pass_selector, "text": password, "submit": True})
    print(f"Submitted login for {username}@{args.domain}. Verify with web_open. "
          f"If it did not work, the page likely has captcha/2FA (cannot be automated headless).")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="stealth_login", description="Establish a Camoufox login session.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("cookies", help="reuse an existing browser login via cookies")
    pc.add_argument("domain")
    pc.add_argument("--browser", default="auto", choices=["auto", "firefox", "chrome", "edge"])
    pc.set_defaults(func=cmd_cookies)

    ps = sub.add_parser("store", help="save credentials to the OS keychain")
    ps.add_argument("domain")
    ps.add_argument("username")
    ps.set_defaults(func=cmd_store)

    pf = sub.add_parser("fill", help="drive the login form with stored credentials")
    pf.add_argument("domain")
    pf.add_argument("login_url")
    pf.add_argument("--user-selector", default="input[type=email], input[name=username], input[type=text]")
    pf.add_argument("--pass-selector", default="input[type=password]")
    pf.set_defaults(func=cmd_fill)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

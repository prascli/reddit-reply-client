#!/usr/bin/env python3
"""Minimal Reddit client: authenticate as one account, then reply to one thread.

This is the whole client. It is deliberately small so the behaviour is auditable:

  - it authenticates with the password grant of a *script* app, so it can only
    ever act as the single account that owns the credentials;
  - it reads nothing except the thread being replied to;
  - it can post one comment, and delete that comment again;
  - it never votes, never sends messages, never touches moderation endpoints.

Usage
    export REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=...
    export REDDIT_USERNAME=... REDDIT_PASSWORD=...
    python3 reddit_client.py whoami
    python3 reddit_client.py reply --url https://www.reddit.com/r/.../comments/abc123/... --file reply.md --dry-run
    python3 reddit_client.py reply --url ... --file reply.md
    python3 reddit_client.py delete --id t1_xyz
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = "script:reddit-reply-client:v1.0 (by /u/%s)" % os.environ.get("REDDIT_USERNAME", "unknown")


def env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit("missing environment variable %s" % name)
    return value


def http(url, data=None, headers=None, method=None):
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8", "ignore")
            return r.status, (json.loads(body) if body.strip().startswith("{") else body)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:300]


def token():
    basic = base64.b64encode(("%s:%s" % (env("REDDIT_CLIENT_ID"),
                                          env("REDDIT_CLIENT_SECRET"))).encode()).decode()
    status, body = http("https://www.reddit.com/api/v1/access_token",
                        data=urllib.parse.urlencode({
                            "grant_type": "password",
                            "username": env("REDDIT_USERNAME"),
                            "password": env("REDDIT_PASSWORD"),
                        }).encode(),
                        headers={"Authorization": "Basic " + basic,
                                 "Content-Type": "application/x-www-form-urlencoded"},
                        method="POST")
    if status != 200 or not isinstance(body, dict) or "access_token" not in body:
        raise SystemExit("auth failed %s: %s" % (status, body))
    return body["access_token"]


def whoami():
    status, me = http("https://oauth.reddit.com/api/v1/me",
                      headers={"Authorization": "Bearer " + token()})
    if status != 200:
        raise SystemExit("whoami failed %s" % status)
    print("account:", me.get("name"), "| link karma:", me.get("link_karma"),
          "| comment karma:", me.get("comment_karma"))
    return me


def reply(url, path, dry_run=False):
    m = re.search(r"/comments/([a-z0-9]+)", url)
    if not m:
        raise SystemExit("not a thread URL: %s" % url)
    thing = "t3_" + m.group(1)
    text = open(path, encoding="utf-8").read().strip()
    if not text:
        raise SystemExit("refusing to post an empty comment")
    if dry_run:
        print("dry-run | target:", thing, "| chars:", len(text))
        return None
    status, out = http("https://oauth.reddit.com/api/comment",
                       data=urllib.parse.urlencode({"thing_id": thing, "text": text,
                                                    "api_type": "json"}).encode(),
                       headers={"Authorization": "Bearer " + token(),
                                "Content-Type": "application/x-www-form-urlencoded"},
                       method="POST")
    if status != 200:
        raise SystemExit("reply failed %s: %s" % (status, out))
    errors = ((out.get("json") or {}).get("errors") or [])
    if errors:
        raise SystemExit("reddit rejected the comment: %s" % errors)
    fullname = (((out.get("json") or {}).get("data") or {}).get("things") or [{}])[0].get("data", {}).get("name")
    print("posted:", fullname)
    return fullname


def delete(fullname):
    status, out = http("https://oauth.reddit.com/api/del",
                       data=urllib.parse.urlencode({"id": fullname}).encode(),
                       headers={"Authorization": "Bearer " + token(),
                                "Content-Type": "application/x-www-form-urlencoded"},
                       method="POST")
    print("delete:", status)
    return status == 200


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    r = sub.add_parser("reply")
    r.add_argument("--url", required=True)
    r.add_argument("--file", required=True)
    r.add_argument("--dry-run", action="store_true")
    d = sub.add_parser("delete")
    d.add_argument("--id", required=True)
    args = parser.parse_args()

    if args.cmd == "whoami":
        whoami()
    elif args.cmd == "reply":
        reply(args.url, args.file, dry_run=args.dry_run)
    else:
        sys.exit(0 if delete(args.id) else 1)


if __name__ == "__main__":
    main()

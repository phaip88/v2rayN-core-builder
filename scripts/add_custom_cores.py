#!/usr/bin/env python3
"""
add_custom_cores.py - Inject user-declared extra cores (cores.user.json) into v2rayN ServiceLib sources.

Design goals (lessons from the failed regex approach):
  * Anchor-based insertion: every edit targets an exact anchor, located AFTER
    a known section start; whitespace-tolerant where v2rayN formatting varies.
  * Pre-flight, atomic: ALL anchors are resolved and ALL cores validated BEFORE
    any file is written. A failure anywhere leaves the tree untouched.
  * Idempotent: a core id already present in a file is reported and skipped.
  * Fail-fast errors name the file, the missing anchor, and the likely cause.

MUST run AFTER patches/v2rayN-extended-cores.patch has been applied when any
core uses "txtArg": true (the CoreManager inline-argument condition only
exists in the patched file).

Usage:
    python3 add_custom_cores.py <cores.user.json> <v2rayN-source-root>

cores.user.json schema (JSON array):
[
  {
    "id": "mytunnel",        # required  C# identifier; also used as bin/<id>/ folder
    "enumValue": 37,         # required  unique int, 37..98
    "repo": "owner/repo",    # required  GitHub repo, used for the download-page URL
    "exes": ["a_windows_amd64", "a"],     # optional, default [id]
    "arguments": " {0}",                  # optional, default " {0}"
    "absolutePath": true,                 # optional, default true
    "txtArg": true,          # optional, default true: config text passed INLINE as argument
                             #           false = core expects a config FILE path instead
    "environment": {"K": "{0}"}           # optional extra env vars ({0} = config path)
  }
]
"""

import json
import os
import re
import sys

CUSTOM_ENUM_MIN = 37
V2RAYN_RESERVED_ENUM = 99
ALLOWED_KEYS = {"id", "enumValue", "repo", "exes", "arguments",
                "absolutePath", "txtArg", "environment"}
ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def die(msg):
    raise SystemExit(f"[ERROR] {msg}")


def read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def csharp_str(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def find_unique(content, anchor, where, what):
    n = content.count(anchor)
    if n == 0:
        die(f"{where}: {what} not found:\n        {anchor!r}\n"
            f"        Cause: source layout differs too much, or the base patch "
            f"(patches/v2rayN-extended-cores.patch) was not applied first.")
    if n > 1:
        die(f"{where}: {what} matches {n} times, must be exactly once")
    return content.index(anchor)


def load_and_validate(config_path):
    if not os.path.exists(config_path):
        print(f"[*] {config_path} not found -> nothing to inject.")
        return []
    try:
        with open(config_path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        die(f"{config_path}: invalid JSON: {e}")
    if not isinstance(data, list):
        die(f"{config_path}: top level must be a JSON array of core objects")
    print(f"[*] Loaded {len(data)} custom core declaration(s)")
    seen_enum, seen_id = set(), set()
    cores = []
    for entry in data:
        if isinstance(entry, dict) and entry and all(k.startswith("_") for k in entry):
            print(f"[*] skipping comment-only entry (keys {sorted(entry)})")
            continue
        c = validate(entry, seen_enum, seen_id)
        cores.append(c)
    return cores


def validate(core, seen_enum, seen_id):
    if not isinstance(core, dict):
        die(f"each entry must be a JSON object, got {type(core).__name__}")
    unknown = [k for k in core if k not in ALLOWED_KEYS]
    if unknown:
        print(f"[!] warning: ignoring unknown key(s) {unknown} "
              f"(typo? allowed: {sorted(ALLOWED_KEYS)})")
    cid = core.get("id")
    if not isinstance(cid, str) or not ID_RE.match(cid):
        die(f"id {cid!r} is not a valid C# identifier")
    if cid != cid.lower():
        print(f"[!] warning: id '{cid}' not lowercase; also used as bin/{cid}/ folder name")
    val = core.get("enumValue")
    if isinstance(val, bool) or not isinstance(val, int):
        die(f"[{cid}] 'enumValue' must be an integer, got {val!r}")
    if not CUSTOM_ENUM_MIN <= val < V2RAYN_RESERVED_ENUM:
        die(f"[{cid}] enumValue must be in [{CUSTOM_ENUM_MIN},{V2RAYN_RESERVED_ENUM}) "
            f"(1-30 official, 31-36 project defaults, 99=v2rayN)")
    if val in seen_enum:
        die(f"[{cid}] duplicate enumValue {val} in config")
    repo = core.get("repo")
    if not isinstance(repo, str) or not repo.strip():
        die(f"[{cid}] 'repo' is required, e.g. \"owner/repo\"")
    exes = core.get("exes", [cid])
    if not isinstance(exes, list) or not exes or not all(isinstance(e, str) and e for e in exes):
        die(f"[{cid}] 'exes' must be a non-empty array of strings")
    args = core.get("arguments", " {0}")
    if not isinstance(args, str):
        die(f"[{cid}] 'arguments' must be a string containing '{{0}}'")
    if "{0}" not in args:
        print(f"[!] warning: [{cid}] 'arguments' has no {{0}} placeholder - config won't reach this core")
    env = core.get("environment", {})
    if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
        die(f"[{cid}] 'environment' must map string->string")
    seen_enum.add(val)
    seen_id.add(cid)
    return {"id": cid, "enum": val, "repo": repo.strip(), "exes": exes,
            "args": args, "abs": bool(core.get("absolutePath", True)),
            "txtArg": bool(core.get("txtArg", True)), "env": env}


# ---------------------------------------------------------------- planners --
# Each planner returns (path, new_content_or_None, added_count); None = unchanged.

def plan_ecore_type(root, cores):
    path = os.path.join(root, "v2rayN", "ServiceLib", "Enums", "ECoreType.cs")
    require(path)
    content = read(path)
    existing_ids = set(re.findall(r"^\s*([A-Za-z_]\w*)\s*=\s*\d+", content, re.M))
    existing_ints = {}
    for k, v in re.findall(r"([A-Za-z_]\w*)\s*=\s*(\d+)", content):
        existing_ints.setdefault(int(v), k)
    added, ins = 0, []
    for c in cores:
        if c["id"] in existing_ids or f"ECoreType.{c['id']}" in content:
            print(f"[-] ECoreType.cs: '{c['id']}' already present, skipped")
            continue
        clash = existing_ints.get(c["enum"])
        if clash:
            die(f"[{c['id']}] enumValue {c['enum']} already used by '{clash}' in ECoreType.cs")
        anchor = "    v2rayN = 99\n}"
        pos = find_unique(content, anchor, "ECoreType.cs", "'v2rayN = 99' tail anchor")
        ins.append((pos, f"    {c['id']} = {c['enum']},\n"))
        existing_ints[c["enum"]] = c["id"]
        added += 1
        print(f"[+] ECoreType.cs: {c['id']} = {c['enum']}")
    return path, apply_insertions(content, ins), added


def plan_global(root, cores):
    path = os.path.join(root, "v2rayN", "ServiceLib", "Global.cs")
    require(path)
    content = read(path)
    anchor = '        { ECoreType.v2rayN, "2dust/v2rayN" },'
    added, ins = 0, []
    for c in cores:
        if f"ECoreType.{c['id']}" in content:
            print(f"[-] Global.cs: '{c['id']}' already present, skipped")
            continue
        pos = find_unique(content, anchor, "Global.cs", "CoreUrls[v2rayN] anchor")
        ins.append((pos, f'            {{ ECoreType.{c["id"]}, "{c["repo"]}" }},\n'))
        added += 1
        print(f"[+] Global.cs: CoreUrls[{c['id']}] -> {c['repo']}")
    return path, apply_insertions(content, ins), added


def plan_core_info(root, cores):
    path = os.path.join(root, "v2rayN", "ServiceLib", "Manager", "CoreInfoManager.cs")
    require(path)
    content = read(path)
    start_m = re.search(r"_coreInfo\s*=\s*\[", content)
    if not start_m:
        die("CoreInfoManager.cs: '_coreInfo = [' assignment not found")
    start = start_m.start()
    mo = re.compile(r"\n[ \t]*\];").search(content, start)
    if not mo:
        die("CoreInfoManager.cs: closing '];' of the _coreInfo collection not found")
    pos = mo.start()
    added, blocks = 0, []
    for c in cores:
        if f"ECoreType.{c['id']}" in content:
            print(f"[-] CoreInfoManager.cs: '{c['id']}' already present, skipped")
            continue
        exes = ", ".join(f'"{e}"' for e in c["exes"])
        b = (
            "\n"
            "                new CoreInfo\n"
            "                {\n"
            f"                    CoreType = ECoreType.{c['id']},\n"
            f"                    CoreExes = [{exes}],\n"
            f"                    Arguments = \"{csharp_str(c['args'])}\",\n"
            f"                    Url = GetCoreUrl(ECoreType.{c['id']}),\n"
            f"                    AbsolutePath = {str(c['abs']).lower()},\n"
        )
        if c["env"]:
            b += (
                "                    Environment = new Dictionary<string, string?>()\n"
                "                    {\n"
                + "".join(f"                        {{ \"{k}\", \"{csharp_str(v)}\" }},\n"
                          for k, v in c["env"].items())
                + "                    },\n"
            )
        b += "                },"
        blocks.append(b)
        added += 1
        print(f"[+] CoreInfoManager.cs: CoreInfo[{c['id']}]")
    return path, (content[:pos] + "".join(blocks) + content[pos:] if blocks else None), added


def plan_core_manager(root, cores):
    txt_arg = [c for c in cores if c["txtArg"]]
    if not txt_arg:
        return None, None, 0
    path = os.path.join(root, "v2rayN", "ServiceLib", "Manager", "CoreManager.cs")
    require(path)
    content = read(path)
    tail = ") ? System.IO.File.ReadAllText(Utils.GetBinConfigPath(configPath))"
    head = "(coreInfo.CoreType is ECoreType.brook or "
    tpos = content.find(tail)
    if tpos == -1:
        die("CoreManager.cs: ReadAllText ternary tail not found.\n"
            "        Cause: base patch not applied, or v2rayN changed RunProcessNormal().")
    if content.count(tail) != 1:
        die("CoreManager.cs: ReadAllText ternary tail is ambiguous")
    hpos = content.rfind(head, 0, tpos)
    if hpos == -1:
        die("CoreManager.cs: '(coreInfo.CoreType is ECoreType.brook or ...' head not found.\n"
            "        Apply patches/v2rayN-extended-cores.patch BEFORE running this script.")
    added, ins = 0, []
    for c in txt_arg:
        if f"ECoreType.{c['id']}" in content[hpos:tpos]:
            print(f"[-] CoreManager.cs: '{c['id']}' already in inline-arg list, skipped")
            continue
        ins.append((tpos, f" or ECoreType.{c['id']}"))
        added += 1
        print(f"[+] CoreManager.cs: {c['id']} gets config text as inline argument")
    return path, apply_insertions(content, ins), added


# ---------------------------------------------------------------- helpers --

def require(path):
    if not os.path.exists(path):
        die(f"missing file: {path}")


def apply_insertions(content, ins):
    """Apply (pos,text) insertions ascending; positions are original-content based."""
    if not ins:
        return None
    result, prev = [], 0
    for pos, text in sorted(ins):
        result.append(content[prev:pos])
        result.append(text)
        prev = pos
    result.append(content[prev:])
    return "".join(result)


def main():
    if len(sys.argv) != 3:
        die("usage: add_custom_cores.py <cores.user.json> <v2rayN-source-root>")
    config_path, root = sys.argv[1], sys.argv[2]
    if not os.path.isdir(root):
        die(f"v2rayN source root not found: {root}")
    cores = load_and_validate(config_path)
    if not cores:
        print("[*] Nothing to inject.")
        return

    # Pre-flight: plan every edit before touching disk.
    plans = [
        plan_ecore_type(root, cores),
        plan_global(root, cores),
        plan_core_info(root, cores),
        plan_core_manager(root, cores),
    ]
    written = 0
    for path, content, _ in plans:
        if content is not None:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            written += 1
    print(f"[DONE] custom cores injected ({written} file(s) modified)")


if __name__ == "__main__":
    main()

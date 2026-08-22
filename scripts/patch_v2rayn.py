#!/usr/bin/env python3
"""
patch_v2rayn.py - Automated patcher for extending v2rayN with custom core support.
"""

import os
import sys
import json
import re
from pathlib import Path

def find_file(root_dir, pattern):
    for path in Path(root_dir).rglob(pattern):
        if path.is_file():
            return path
    return None

def patch_ecore_type(file_path, cores):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    modified = False
    for core in cores:
        cid = core["id"]
        enum_val = core.get("enumValue")
        if re.search(rf"\b{cid}\b", content):
            print(f"[-] ECoreType already contains {cid}")
            continue

        pattern = r"(\s*)([a-zA-Z0-9_]+\s*=\s*\d+)(,?)(\s*\n\s*\})"
        def repl(m):
            indent = m.group(1)
            last_entry = m.group(2)
            closing = m.group(4)
            return f"{indent}{last_entry},\n{indent}{cid} = {enum_val}{closing}"

        new_content, count = re.subn(pattern, repl, content, count=1)
        if count > 0:
            content = new_content
            modified = True
            print(f"[+] Added {cid} = {enum_val} to ECoreType.cs")
        else:
            last_brace_idx = content.rfind("}")
            if last_brace_idx != -1:
                entry = f"    {cid} = {enum_val},\n"
                content = content[:last_brace_idx] + entry + content[last_brace_idx:]
                modified = True
                print(f"[+] Appended {cid} = {enum_val} to ECoreType.cs (fallback)")

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

def patch_global(file_path, cores):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    modified = False
    core_urls_match = re.search(r"(CoreUrls\s*=\s*new[^{]*\{)(.*?)(\n\s*\};)", content, re.DOTALL)
    if not core_urls_match:
        print("[!] Could not locate CoreUrls dictionary in Global.cs")
        return

    urls_block = core_urls_match.group(2)
    new_urls_block = urls_block

    for core in cores:
        cid = core["id"]
        repo = core.get("repo", "")
        if not repo:
            continue
        if f"ECoreType.{cid}" in urls_block:
            print(f"[-] Global.cs CoreUrls already contains {cid}")
            continue

        new_entry = f"        {{ ECoreType.{cid}, \"{repo}\" }},\n"
        new_urls_block = new_urls_block.rstrip() + "\n" + new_entry
        modified = True
        print(f"[+] Added ECoreType.{cid} -> {repo} to Global.cs CoreUrls")

    if modified:
        content = content[:core_urls_match.start(2)] + new_urls_block + content[core_urls_match.end(2):]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

def patch_core_info_manager(file_path, cores):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    modified = False
    for core in cores:
        cid = core["id"]
        if f"ECoreType.{cid}" in content:
            print(f"[-] CoreInfoManager.cs already contains {cid}")
            continue

        exes_json = json.dumps(core.get("exes", [cid]))
        args = core.get("arguments", " {0}").replace('"', '\\"')
        abs_path = "true" if core.get("absolutePath", True) else "false"

        core_info_snippet = f"""
                new CoreInfo
                {{
                    CoreType = ECoreType.{cid},
                    CoreExes = {exes_json},
                    Arguments = "{args}",
                    Url = GetCoreUrl(ECoreType.{cid}),
                    AbsolutePath = {abs_path},
                }},"""

        list_end_match = re.search(r"(\n\s*)(\]|\})\s*;", content)
        if list_end_match:
            insert_pos = list_end_match.start()
            content = content[:insert_pos] + core_info_snippet + content[insert_pos:]
            modified = True
            print(f"[+] Added CoreInfo definition for {cid} to CoreInfoManager.cs")
        else:
            print(f"[!] Could not find list closing in CoreInfoManager.cs for {cid}")

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

def patch_core_manager(file_path, cores):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    txt_cores = [c["id"] for c in cores if c.get("isTxtConfig", False)]
    if not txt_cores:
        return

    core_checks = " or ".join([f"ECoreType.{cid}" for cid in txt_cores])
    full_cond = f"(coreInfo.CoreType is ECoreType.brook or {core_checks} || configPath.EndsWith(\".txt\")) && System.IO.File.Exists(Utils.GetBinConfigPath(configPath)) ? System.IO.File.ReadAllText(Utils.GetBinConfigPath(configPath)).Trim() : (coreInfo.AbsolutePath ? Utils.GetBinConfigPath(configPath).AppendQuotes() : configPath)"

    pattern = r"arguments:\s*string\.Format\(coreInfo\.Arguments,\s*([^)]+)\)"
    
    if "System.IO.File.ReadAllText" in content:
        pattern_existing = r"arguments:\s*string\.Format\(coreInfo\.Arguments,\s*\(coreInfo\.CoreType is [^?]+\?[^:]+:[^)]+\)\)"
        m = re.search(pattern_existing, content)
        if m:
            replacement = f"arguments: string.Format(coreInfo.Arguments, {full_cond})"
            content = content[:m.start()] + replacement + content[m.end():]
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print("[+] Updated CoreManager.cs CLI arguments handler")
            return

    m = re.search(pattern, content)
    if m:
        replacement = f"arguments: string.Format(coreInfo.Arguments, {full_cond})"
        content = content[:m.start()] + replacement + content[m.end():]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("[+] Patched CoreManager.cs CLI arguments handler")
    else:
        print("[-] CoreManager.cs arguments pattern not matched (may already be patched or different structure)")

def main():
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    config_file = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "cores.json")

    if not os.path.exists(config_file):
        print(f"[!] Error: Cores config file not found: {config_file}")
        sys.exit(1)

    with open(config_file, "r", encoding="utf-8-sig") as f:
        cores = json.load(f)

    print(f"[*] Loaded {len(cores)} extended core definitions.")

    ecore_file = find_file(root_dir, "ECoreType.cs")
    global_file = find_file(root_dir, "Global.cs")
    core_info_file = find_file(root_dir, "CoreInfoManager.cs")
    core_mgr_file = find_file(root_dir, "CoreManager.cs")

    print(f"[*] ECoreType.cs: {ecore_file}")
    print(f"[*] Global.cs: {global_file}")
    print(f"[*] CoreInfoManager.cs: {core_info_file}")
    print(f"[*] CoreManager.cs: {core_mgr_file}")

    if not all([ecore_file, global_file, core_info_file, core_mgr_file]):
        print("[!] Error: One or more target source files could not be found.")
        sys.exit(1)

    patch_ecore_type(ecore_file, cores)
    patch_global(global_file, cores)
    patch_core_info_manager(core_info_file, cores)
    patch_core_manager(core_mgr_file, cores)

    print("[SUCCESS] All patches successfully applied!")

if __name__ == "__main__":
    main()

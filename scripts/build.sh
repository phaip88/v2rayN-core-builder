#!/usr/bin/env bash
#
# build.sh - Build an extended v2rayN with extra cores (gost, chisel, ssh, sshpass, easytier, cloudflared).
#
# What it does:
#   1. Clones the requested v2rayN version (default: latest release).
#   2. Applies patches/v2rayN-extended-cores.patch (unified diff based on 7.24.4).
#   3. Builds ServiceLib.dll (works on Linux/macOS/Windows).
#   4. Optionally builds the full self-contained Windows client (requires Windows runner / WinForms).
#
# Usage:
#   ./scripts/build.sh [VERSION] [--no-client]
#
# Examples:
#   ./scripts/build.sh                 # latest release, build dll + client
#   ./scripts/build.sh 7.24.4          # pin a version
#   ./scripts/build.sh latest --no-client   # dll only

set -euo pipefail

VERSION="${1:-latest}"
NO_CLIENT=0
for a in "$@"; do
  case "$a" in
    --no-client) NO_CLIENT=1 ;;
  esac
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH="$ROOT/patches/v2rayN-extended-cores.patch"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==> Working dir: $WORK"

# ---- resolve version -------------------------------------------------------
if [ "$VERSION" = "latest" ]; then
  echo "==> Resolving latest v2rayN release tag ..."
  VERSION="$(git ls-remote --tags https://github.com/2dust/v2rayN.git \
      | awk -F'refs/tags/' '{print $2}' \
      | grep -E '^[0-9]+(\.[0-9]+)*$' \
      | sort -V | tail -1)"
  [ -n "$VERSION" ] || { echo "!! could not resolve latest v2rayN tag"; exit 1; }
  echo "    -> $VERSION"
fi

# ---- clone -----------------------------------------------------------------
echo "==> Cloning 2dust/v2rayN @ $VERSION (shallow) ..."
git clone --depth 1 --branch "$VERSION" --filter=blob:none --sparse "https://github.com/2dust/v2rayN.git" "$WORK/v2rayN-src"
cd "$WORK/v2rayN-src"
git sparse-checkout set v2rayN

# ---- apply patch -----------------------------------------------------------
echo "==> Applying extended-cores patch ..."
if git apply --whitespace=nowarn "$PATCH" 2>/dev/null; then
  echo "    git apply: OK"
else
  echo "    git apply failed, retrying with GNU patch (fuzz) ..."
  patch -p1 --fuzz=3 --batch --forward < "$PATCH"
fi

# ---- inject user-declared custom cores --------------------------------------
USER_CORES="$ROOT/cores.user.json"
if [ -f "$USER_CORES" ]; then
  echo "==> Injecting custom cores from cores.user.json ..."
  python3 "$ROOT/scripts/add_custom_cores.py" "$USER_CORES" "$WORK/v2rayN-src"
fi

# ---- build ServiceLib.dll --------------------------------------------------
echo "==> Building ServiceLib.dll (Release) ..."
dotnet build v2rayN/ServiceLib/ServiceLib.csproj -c Release -o "$WORK/dist/ServiceLib"
echo "    -> $(find "$WORK/dist/ServiceLib" -name 'ServiceLib.dll' | head -1)"

# ---- build full client (Windows only) --------------------------------------
if [ "$NO_CLIENT" -eq 0 ]; then
  if [ "$(uname -s)" = "Windows_NT" ] || [[ "$(uname -s)" == MINGW* ]] || [ "${BUILD_CLIENT:-1}" = "1" ]; then
    echo "==> Building full self-contained Windows client (win-x64) ..."
    dotnet publish v2rayN/v2rayN/v2rayN.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -o "$WORK/dist/v2rayN-Extended" \
      || echo "!! Full client build failed (needs Windows runner / WinForms). ServiceLib.dll above is still valid."
  else
    echo "==> Skipping full client build: not running on Windows. Re-run on windows-latest or pass --no-client."
  fi
fi

# ---- package ---------------------------------------------------------------
OUT="$ROOT/dist"
mkdir -p "$OUT"
if [ -d "$WORK/dist/ServiceLib" ]; then
  ( cd "$WORK/dist" && zip -r "$OUT/ServiceLib-extended-${VERSION}.zip" ServiceLib )
  echo "==> Wrote $OUT/ServiceLib-extended-${VERSION}.zip"
fi
if [ -d "$WORK/dist/v2rayN-Extended" ]; then
  ( cd "$WORK/dist" && zip -r "$OUT/v2rayN-Extended-win64-SelfContained-${VERSION}.zip" v2rayN-Extended )
  echo "==> Wrote $OUT/v2rayN-Extended-win64-SelfContained-${VERSION}.zip"
fi
echo "DONE"

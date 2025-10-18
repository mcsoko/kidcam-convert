#!/bin/zsh
# Install or update the "Convert KidCam (HEVC)" macOS Shortcut from a local file or URL.
# Usage:
#   ./install-shortcut.sh                       # import ./Convert KidCam (HEVC).shortcut
#   ./install-shortcut.sh -f ./My.shortcut      # import specific local file
#   ./install-shortcut.sh -u https://... .shortcut  # download from URL and import
#   ./install-shortcut.sh -r                    # replace if a Shortcut with same name exists
#   ./install-shortcut.sh -n "My Name"          # set/override the expected Shortcut name
#   ./install-shortcut.sh -q                    # quiet mode (less chatter)
#
# Notes:
# - Requires macOS 12+ (Shortcuts app with `shortcuts` CLI).
# - Requires ffmpeg installed for the Shortcut to run: `brew install ffmpeg`

set -euo pipefail

QUIET=0
REPLACE=0
SHORTCUT_NAME="Convert KidCam (HEVC)"
DEFAULT_FILE="Convert KidCam (HEVC).shortcut"
SRC_FILE=""
SRC_URL=""

print_info() { (( QUIET )) || printf "%s\n" "$*"; }
print_warn() { printf "⚠️  %s\n" "$*" >&2; }
print_err()  { printf "❌ %s\n" "$*" >&2; }

usage() {
  cat <<EOF
Usage: $0 [options]
  -f, --file <path>        Local .shortcut file to import (default: "./${DEFAULT_FILE}")
  -u, --url  <url>         Download .shortcut from URL and import
  -n, --name <name>        Expected Shortcut name (default: "${SHORTCUT_NAME}")
  -r, --replace            Replace existing Shortcut with the same name
  -q, --quiet              Less output
  -h, --help               Show this help
Examples:
  $0
  $0 -f "./${DEFAULT_FILE}" -r
  $0 -u "https://github.com/you/repo/releases/download/v1/${DEFAULT_FILE}" -r
EOF
}

has_import_cli() {
  shortcuts --help 2>/dev/null | grep -qE '(^|[[:space:]])import([[:space:]]|$)'
}

import_via_gui() {
  # Use the Finder/GUI import flow from CLI by 'opening' the file.
  # This will prompt once in Shortcuts to add the shortcut.
  open "$1"
  print_info "🖱️  A prompt should appear in Shortcuts to add \"${SHORTCUT_NAME}\". Please click Add."
  # Poll for presence (30s timeout)
  for i in {1..30}; do
    if shortcuts list | grep -Fqx "${SHORTCUT_NAME}"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    -f|--file)    SRC_FILE="${2:-}"; shift 2;;
    -u|--url)     SRC_URL="${2:-}"; shift 2;;
    -n|--name)    SHORTCUT_NAME="${2:-}"; shift 2;;
    -r|--replace) REPLACE=1; shift;;
    -q|--quiet)   QUIET=1; shift;;
    -h|--help)    usage; exit 0;;
    *) print_err "Unknown option: $1"; usage; exit 2;;
  esac
done

# --- Pre-flight checks ---
if ! command -v shortcuts >/dev/null 2>&1; then
  print_err "The 'shortcuts' CLI is not available. You need macOS 12+ Shortcuts app."
  print_info "Try running once: open -a Shortcuts"
  exit 1
fi

# Optional: warn if ffmpeg is missing (Shortcut will still import)
if ! command -v ffmpeg >/dev/null 2>&1; then
  print_warn "ffmpeg not found. Install it for the Shortcut to run: brew install ffmpeg"
fi

# --- Acquire .shortcut file ---
WORKFILE=""
CLEANUP=0

if [[ -n "${SRC_URL}" ]]; then
  # Download to temp file
  if ! command -v curl >/dev/null 2>&1; then
    print_err "curl not found; cannot download from URL."
    exit 1
  fi
  WORKFILE="$(mktemp -t kidcam-shortcut.XXXXXX.shortcut)"
  print_info "⬇️  Downloading Shortcut from URL…"
  curl -L -o "${WORKFILE}" "${SRC_URL}"
  CLEANUP=1
else
  # Use local file if provided, otherwise default filename in CWD
  FILEPATH="${SRC_FILE:-./${DEFAULT_FILE}}"
  if [[ ! -f "${FILEPATH}" ]]; then
    print_err "Shortcut file not found: ${FILEPATH}"
    print_info "Tip: In Shortcuts app: File → Export… to create \"./${DEFAULT_FILE}\""
    exit 1
  fi
  WORKFILE="${FILEPATH}"
fi

# --- Import Shortcut ---
print_info "📦 Importing Shortcut: ${SHORTCUT_NAME}"
if has_import_cli; then
  IMPORT_ARGS=(import "${WORKFILE}")
  if (( REPLACE )); then
    IMPORT_ARGS+=(--replace)
  fi
  if (( QUIET )); then
    shortcuts "${IMPORT_ARGS[@]}" >/dev/null
  else
    shortcuts "${IMPORT_ARGS[@]}"
  fi
else
  print_warn "CLI 'shortcuts import' not available on this macOS. Using GUI import fallback."
  import_via_gui "${WORKFILE}" || {
    print_err "Import failed or was not confirmed in time."
    exit 1
  }
fi

# --- Verify install ---
if ! shortcuts list | grep -Fqx "${SHORTCUT_NAME}"; then
  print_err "Import completed but '${SHORTCUT_NAME}' not found in library (if prompted, ensure you clicked Add)."
  exit 1
fi

print_info "✅ Installed Shortcut: ${SHORTCUT_NAME}"
print_info "Run from Finder (Quick Actions) or via CLI:"
print_info "  shortcuts run \"${SHORTCUT_NAME}\" --input-path \"/path/to/folder\""

# Cleanup temp download
if (( CLEANUP )); then
  rm -f "${WORKFILE}" || true
fi
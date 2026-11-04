#!/bin/sh
# Install the pinned voxl-server crate (binary name: voxl) into HERMES_HOME.
# Native libraries on Linux: libx264, libyuv, libopus, libpulse (and -dev for the build).
# GitHub releases ship the crate, not a prebuilt binary.
set -e
VERSION="0.3.3"
if [ -n "$HERMES_HOME" ]; then
  ROOT="$HERMES_HOME/runtime/voxl"
else
  ROOT="${HOME}/.hermes/runtime/voxl"
fi
mkdir -p "$ROOT"
cargo install voxl-server --version "$VERSION" --locked --root "$ROOT" --force
echo "voxl installed under $ROOT/bin"

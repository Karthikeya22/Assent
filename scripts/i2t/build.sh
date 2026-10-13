#!/bin/sh
# img2threejs review harness: bundles main.ts + a factory (generated, or port.ts for the web objects)
# into bundle.js. Serve this folder (python -m http.server 8765) and open index.html?obj=&az=&el=.
# usage: build.sh <factory.ts>
set -e
cd "$(dirname "$0")"
ROOT=$(git rev-parse --show-toplevel)
cp "$1" factory.ts 2>/dev/null || true
ESB=$(ls -d "$ROOT"/node_modules/.pnpm/esbuild@0.25*/node_modules/esbuild/bin/esbuild | head -1)
NODE_PATH="$ROOT/apps/web/node_modules" "$ESB" main.ts --bundle --format=esm --outfile=bundle.js --log-level=warning

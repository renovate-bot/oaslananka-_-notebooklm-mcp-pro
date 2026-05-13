#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$SRC/notebooklm-mcp-pro"
cd "$PROJECT_DIR"

export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-${WORK:-/work}/nlm-mcp-venv}"
uv sync --frozen --no-dev --no-editable
uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python" atheris==2.3.0 pyinstaller==6.17.0

mkdir -p "$OUT"

find "$PROJECT_DIR/fuzz" -name "*_fuzzer.py" -print0 | while IFS= read -r -d "" fuzzer; do
  fuzzer_basename="$(basename "$fuzzer" .py)"
  fuzzer_package="${fuzzer_basename}.pkg"
  work_dir="${WORK:-/tmp}/pyinstaller-${fuzzer_basename}"

  "$UV_PROJECT_ENVIRONMENT/bin/pyinstaller" \
    --distpath "$OUT" \
    --workpath "$work_dir/build" \
    --specpath "$work_dir/spec" \
    --onefile \
    --name "$fuzzer_package" \
    "$fuzzer"

  cat > "$OUT/$fuzzer_basename" <<EOF
#!/bin/sh
# LLVMFuzzerTestOneInput for fuzzer detection.
this_dir=\$(dirname "\$0")
"\$this_dir/$fuzzer_package" "\$@"
EOF
  chmod +x "$OUT/$fuzzer_basename"
done

#!/usr/bin/env bash
# Deploy the explorer on the VM and check that every path really works.
#
#   deploy/vm/deploy.sh            # pull, rebuild what changed, restart, check
#   deploy/vm/deploy.sh --check    # only run the checks
#
# The checks go through nginx (127.0.0.1:8080) the way the browser does, and
# over HTTPS through Caddy, so a misrouted /api/ or a broken certificate fails
# here instead of on users' maps. Exits 1 if any check fails.
set -uo pipefail

cd "$(dirname "$0")/../.."
COMPOSE="docker compose -f deploy/vm/compose.yaml"
WEB="http://127.0.0.1:8080"
SITE="${SITE:-https://eoforeststac.gfz.de}"
S3="https://s3.gfz.de/dog.atlaseo-glm.eo-gridded-data/collections"

if [[ "${1:-}" != "--check" ]]; then
    git pull --ff-only || exit 1
    $COMPOSE up -d --build || exit 1
    echo "Waiting for the services to report healthy..."
    for _ in $(seq 1 90); do
        unhealthy=$($COMPOSE ps --format '{{.Service}} {{.Status}}' | grep -vc healthy)
        [[ "$unhealthy" == 0 ]] && break
        sleep 2
    done
    # Build leftovers otherwise pile up on the VM's disk with every deploy
    docker builder prune -af >/dev/null 2>&1
fi

failures=0
check() {  # check NAME COMMAND...: run COMMAND, print PASS/FAIL
    local name=$1; shift
    local out
    if out=$("$@" 2>&1); then
        printf '  PASS  %s%s\n' "$name" "${out:+  ($out)}"
    else
        printf '  FAIL  %s  %s\n' "$name" "$out"
        failures=$((failures + 1))
    fi
}
enc() { python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"; }

services() { $COMPOSE ps --format '{{.Service}} {{.Status}}' | grep -v healthy && return 1; echo "all healthy"; }

titiler_routed() {  # /api/ must reach TiTiler, not another container
    curl -fsS -m 20 "$WEB/api/healthz" | grep -q '"titiler"' && echo "TiTiler answers /api/"
}

tile() {  # a GAMI 1-degree tile over southern Africa must be a non-empty PNG
    local q="url=$(enc "$S3/GAMI_AGECLASS/GAMI_AGECLASS_1deg_v3.1.zarr")&variable=forest_age&sel=members%3D0&sel=age_class%3D0-20&sel=time%3Dnearest%3A%3A2010-01-01T00%3A00%3A00.000000000&rescale=0,0.72&colormap_name=viridis"
    local bytes
    bytes=$(curl -fsS -m 60 -o /tmp/eoforeststac-check.png -w '%{size_download}' "$WEB/api/tiles/WebMercatorQuad/3/4/4.png?$q") || return 1
    head -c 8 /tmp/eoforeststac-check.png | grep -q PNG && [[ "$bytes" -gt 2000 ]] && echo "$bytes bytes"
}

point() {  # Hansen tree cover in the central Amazon is 100 %
    local q="url=$(enc "$S3/HANSEN_GFC/HANSEN_GFC_v1.12.zarr")&variable=tree_cover"
    curl -fsS -m 60 "$WEB/api/point/-60,-5?$q" | python3 -c 'import sys, json; v = json.load(sys.stdin)["values"][0]; assert v == 100, v; print("tree cover", v)'
}

analysis() {  # a small region-statistics job must finish
    local body id status
    body=$(python3 - "$S3" <<'EOF'
import json, sys
s3 = sys.argv[1]
print(json.dumps({
    "geometry": {"type": "Polygon", "coordinates": [[[10.9, 51.95], [11.1, 51.95], [11.1, 52.05], [10.9, 52.05], [10.9, 51.95]]]},
    "layers": [{"url": f"{s3}/HANSEN_GFC/HANSEN_GFC_v1.12.zarr", "variable": "tree_cover",
                "kind": "cover", "options": {}, "sel": [], "name": "HANSEN_GFC"}],
}))
EOF
)
    id=$(curl -fsS -m 30 -X POST -H 'Content-Type: application/json' -d "$body" "$WEB/api/analysis" | python3 -c 'import sys, json; print(json.load(sys.stdin)["id"])') || return 1
    for _ in $(seq 1 60); do
        status=$(curl -fsS -m 20 "$WEB/api/analysis/$id" | python3 -c 'import sys, json; d = json.load(sys.stdin); print(d["status"], d.get("message", ""))')
        case "$status" in done*) echo "done"; return 0 ;; error*) echo "$status"; return 1 ;; esac
        sleep 2
    done
    echo "timed out"; return 1
}

footprints() {
    curl -fsS -m 30 "$WEB/api/footprints/sources" | python3 -c 'import sys, json; n = len(json.load(sys.stdin)["sources"]); assert n, "no sources"; print(n, "sources")'
}

downloads() {  # the download route reaches TiTiler (unknown jobs: 404 with its message)
    curl -sS -m 20 "$WEB/api/download/0" | grep -q "Unknown or expired download" && echo "routed"
}

explorer() { curl -fsS -m 20 "$WEB/" | grep -q "EOForestSTAC" && echo "page served"; }

https_site() {  # Caddy: valid certificate, and HTTP redirects to HTTPS
    curl -fsS -m 20 -o /dev/null "$SITE/" || return 1
    curl -sS -m 20 -o /dev/null -w '%{http_code} %{redirect_url}' "${SITE/https:/http:}/" | grep -q "^308 https://" || { echo "no HTTP -> HTTPS redirect"; return 1; }
    echo | openssl s_client -connect "${SITE#https://}:443" -servername "${SITE#https://}" 2>/dev/null \
        | openssl x509 -noout -enddate | sed 's/notAfter=/certificate valid until /'
}

echo "Checks:"
check "services healthy" services
check "/api/ reaches TiTiler" titiler_routed
check "explorer page" explorer
check "map tile" tile
check "point value" point
check "analysis job" analysis
check "footprint service" footprints
check "download route" downloads
check "HTTPS" https_site

if [[ $failures -gt 0 ]]; then
    echo "$failures check(s) FAILED"
    exit 1
fi
echo "All checks passed."

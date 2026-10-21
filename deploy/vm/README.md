# GFZ VM deployment

The EOForestSTAC explorer and its TiTiler tile service run with Docker Compose
on `rz-vm225.gfz.de`, published as **http://eoforeststac.gfz.de**. Access is
limited to the GFZ network: `ufw` only allows ports 80/443 from GFZ address
ranges.

```
browser ──► Caddy :80 (host) ──► web (nginx) 127.0.0.1:8080 ──► titiler (internal)
                                   ├─ explorer (webapp/, deploy/vm/config.js)
                                   └─ /api/ → TiTiler, incl. catalog proxy and area downloads
```

- `compose.yaml`: the `web` and `titiler` services. Only `web` is published,
  on `127.0.0.1:8080`; TiTiler is reachable only through `/api/`.
- `Dockerfile.web`, `nginx.conf`, `config.js`: the explorer image. The explorer
  calls TiTiler at the same-origin `./api`.
- `Caddyfile`: host reverse proxy, installed as `/etc/caddy/Caddyfile`. It
  serves plain HTTP until GFZ IT issues a TLS certificate; the HTTPS block to
  switch to is documented at the top of the file.
- Area downloads are kept in the `downloads` named volume (5 GB limit, 2 h TTL).

## Deploy an update

Commit and push to `main`, then on the VM:

```bash
cd ~/eoforeststac/app
git pull --ff-only
docker compose -f deploy/vm/compose.yaml up -d --build
docker compose -f deploy/vm/compose.yaml ps
curl --fail http://127.0.0.1:8080/healthz
curl --fail http://127.0.0.1:8080/api/healthz
```

## First install

```bash
git clone https://github.com/simonbesnard1/eoforeststac.git ~/eoforeststac/app
cd ~/eoforeststac/app
docker compose -f deploy/vm/compose.yaml up -d --build
sudo cp deploy/vm/Caddyfile /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

Keep `BIND_ADDRESS` at its default `127.0.0.1`; Caddy is the only public entry
point.

## Operations

```bash
docker compose -f deploy/vm/compose.yaml logs --tail=200
docker compose -f deploy/vm/compose.yaml restart titiler
docker compose -f deploy/vm/compose.yaml down
```

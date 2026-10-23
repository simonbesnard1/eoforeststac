# GFZ VM deployment

The EOForestSTAC explorer and its TiTiler tile service run with Docker Compose
on `rz-vm225.gfz.de`, published as **http://eoforeststac.gfz.de**. Access is
limited to the GFZ network: `ufw` only allows ports 80/443 from GFZ address
ranges.

```
browser ──► Caddy :443 (host) ──► web (nginx) 127.0.0.1:8080 ──► titiler (internal)
                                   ├─ explorer (webapp/, deploy/vm/config.js)
                                   └─ /api/ → TiTiler, incl. catalog proxy and area downloads
```

- `compose.yaml`: the `web` and `titiler` services. Only `web` is published,
  on `127.0.0.1:8080`; TiTiler is reachable only through `/api/`.
- `Dockerfile.web`, `nginx.conf`, `config.js`: the explorer image. The explorer
  calls TiTiler at the same-origin `./api`.
- `Caddyfile`: host reverse proxy, installed as `/etc/caddy/Caddyfile`. It
  serves HTTPS with the certificate from GFZ IT in `/etc/caddy/certs/`
  (`eoforeststac.crt` full chain, `eoforeststac.key`, which must stay readable
  by the `caddy` group: mode 640) and redirects HTTP to HTTPS. GFZ IT renews
  the certificate every six months with a script that replaces both files and
  runs `systemctl reload caddy`.
- Area downloads are kept in the `downloads` named volume (5 GB limit, 2 h TTL).

## Deploy an update

Commit and push to `main`, then on the VM:

```bash
cd ~/eoforeststac/app
deploy/vm/deploy.sh
```

It pulls, rebuilds what changed, waits for the services to be healthy, clears
Docker's build cache, and then checks every path the browser uses: that
`/api/` reaches TiTiler, a map tile, a point value, an analysis job, the
footprint service, the download route and HTTPS. It exits with status 1 and
lists what failed. `deploy/vm/deploy.sh --check` runs only the checks.

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

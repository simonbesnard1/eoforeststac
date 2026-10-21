# GFZ test-VM deployment

This deployment serves the EOForestSTAC explorer and TiTiler through one
localhost-only port. Apache should proxy the public path to that port. The API
container is not published on the host.

## Install

On `rz-vm225.gfz.de` (139.17.67.110), as the `sbesnard` user (member of the
`docker` group):

```bash
mkdir -p ~/eoforeststac && cd ~/eoforeststac
git clone https://github.com/simonbesnard1/eoforeststac.git app
cd app
docker compose -f deploy/vm/compose.yaml build --pull
docker compose -f deploy/vm/compose.yaml up -d
docker compose -f deploy/vm/compose.yaml ps
curl --fail http://127.0.0.1:8080/healthz
curl --fail http://127.0.0.1:8080/api/healthz
```

If the repository already exists, use `git pull --ff-only` instead of cloning.
Do not run Compose with `sudo` unless GFZ IT explicitly requires rootful Docker.
Rootless Docker or Podman is preferred when supported by the VM.

## Test before Apache is configured

Keep the service bound to localhost and create an SSH tunnel from the client:

```bash
ssh -L 8080:127.0.0.1:8080 sbesnard@rz-vm225.gfz.de
```

Then open <http://localhost:8080>. Do not change `BIND_ADDRESS` to `0.0.0.0`
without coordinating firewall exposure with GFZ IT.

## Host reverse proxy (Caddy) and firewall

The site is intranet-only. Caddy on the host listens on port 80 and proxies
to `127.0.0.1:8080`; its config is [`Caddyfile`](Caddyfile), installed as
`/etc/caddy/Caddyfile`:

```bash
sudo cp deploy/vm/Caddyfile /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
sudo systemctl reload caddy
```

`ufw` allows SSH from anywhere and 80/443 only from GFZ ranges:

```bash
sudo ufw default deny incoming
sudo ufw allow OpenSSH
sudo ufw allow from 139.17.0.0/16 to any port 80,443 proto tcp
sudo ufw allow from 10.0.0.0/8    to any port 80,443 proto tcp
sudo ufw --force enable
```

Pending with GFZ IT: the DNS alias `eoforeststac.gfz.de` and a TLS
certificate. Once issued, place the certificate and key in
`/etc/caddy/certs/` (readable by the `caddy` user) and switch the Caddyfile
to the TLS block documented at its top.

## Operations

```bash
docker compose -f deploy/vm/compose.yaml logs --tail=200
docker compose -f deploy/vm/compose.yaml pull
docker compose -f deploy/vm/compose.yaml build --pull
docker compose -f deploy/vm/compose.yaml up -d
docker compose -f deploy/vm/compose.yaml down
```

Before internet exposure, GFZ IT should verify host patching, rootless/user-
namespace configuration, firewall behavior, Docker's default seccomp/AppArmor
profile, TLS at Apache, access logging, backups, and vulnerability scanning.

# GFZ test-VM deployment

This deployment serves the EOForestSTAC explorer and TiTiler through one
localhost-only port. Apache should proxy the public path to that port. The API
container is not published on the host.

## Install

On `rz-vm558.gfz.de`, as the `forest` user:

```bash
cd /webdata/user/eoforeststac
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
ssh -L 8080:127.0.0.1:8080 forest@rz-vm558.gfz.de
```

Then open <http://localhost:8080>. Do not change `BIND_ADDRESS` to `0.0.0.0`
without coordinating firewall exposure with GFZ IT.

## Apache reverse proxy

The Apache administrator can proxy a dedicated hostname to:

```apache
ProxyPreserveHost On
ProxyPass        / http://127.0.0.1:8080/
ProxyPassReverse / http://127.0.0.1:8080/
```

A dedicated hostname is preferable. If Apache must publish a subpath such as
`/eoforeststac/`, path rewriting must also preserve `/api/`; test all tile and
catalog requests before publication.

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

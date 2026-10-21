# Database administration access

Adminer is optional. The news pipeline and public website do not need it.
Keep it stopped except during a database administration session.

On October 21, 2026, PHP disclosed CVE-2026-109618 and CVE-2026-109619,
both capable of unauthenticated remote code execution. The previously running
Adminer image used PHP 8.4.21. The replacement image pinned in Compose was
verified to contain PHP 8.4.27, a fixed release.

Official advisory: https://www.php.net/archive/2026.php#2026-10-21-5

## Temporary access on the Mac mini

From the production project directory:

```bash
docker compose --profile admin up -d --no-deps adminer
docker compose exec adminer php -v
# Open http://127.0.0.1:5050 on the Mac, then stop when finished:
docker compose stop adminer
```

For access from another trusted machine, use an SSH tunnel instead of exposing
the port to the LAN or internet:

```bash
ssh -N -L 5050:127.0.0.1:5050 m4
```

Then open http://127.0.0.1:5050 on that machine. Database credentials remain
private; never put them in a URL, terminal history or this repository.

## Keep the fix in place

- Keep the `admin` profile, loopback binding and `restart: "no"` setting.
- Do not add Adminer to boot, synthesis or recovery commands.
- Do not revert to `adminer:latest` or the previous image as a rollback.
- For future image updates, inspect PHP's version in a network-isolated
  one-shot container before updating the digest; verify it against current
  PHP security releases. An Adminer application version alone is insufficient.
- If the admin UI fails, stop it. Do not roll back to a vulnerable PHP runtime.
- This fix does not establish whether the old service was ever exploited.

The Postgres data volume, publishing jobs and subscriber records are unchanged.

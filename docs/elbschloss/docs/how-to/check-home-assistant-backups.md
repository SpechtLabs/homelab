# Check Home Assistant's backups

Use this to confirm last night's Home Assistant backup reached the NAS, or to find one to
restore. Nothing alerts on these backups, so a check by hand is the only check.

**Before you start:** `ssh -J cedi@nyx king@nas.local`. Home Assistant at home backs up at 01:00
through its Synology DSM integration, as DSM user `hass`, over the LAN, into
`/volume1/backup/hass`. Home Assistant in Schiltach doesn't back up to the NAS.

1. List the newest backups:

    ```sh
    ssh -J cedi@nyx king@nas.local 'ls -lt /volume1/backup/hass | head -5'
    ```

    You should see a pair from 01:00 today:
    `Automatic_backup_<HA version>_<YYYY-MM-DD>_01.00_<n>.tar` and its `_meta.json`.

2. Count what's kept:

    ```sh
    ssh -J cedi@nyx king@nas.local 'ls /volume1/backup/hass | wc -l'
    ```

    1208 files on 2026-11-26, two per backup. Retention is Home Assistant's backup setting; the
    repo doesn't record it. Keep an eye on the volume if the count only grows.

## Check it worked

Today's `.tar` exists and isn't tiny compared with the ones before it (`ls -l` shows sizes).

## If it didn't

!!! warning "Unverified"
    Home Assistant's configuration isn't in this repo. Where to look: the Synology DSM
    integration and the backup settings in Home Assistant itself, and DSM's connection log for
    user `hass`. Restoring happens in Home Assistant's backup UI, which the repo doesn't
    document.

- Home Assistant down that night: [Respond to an availability alert](respond-to-an-availability-alert.md).
- The NAS was down or rebooting at 01:00: DSM's log.

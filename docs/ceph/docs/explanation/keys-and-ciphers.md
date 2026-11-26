# Keys and ciphers

Ceph 20 (Tentacle) issues cephx keys of type `aes256k` and, by default, accepts only those. The labk3s nodes map RBD images with the kernel's rbd client, and the Pi kernels' libceph (6.6 and 6.12 were tested) can't parse an `aes256k` key: mapping fails with `libceph: Failed to parse secret: -524`. ceph-csi uses kernel rbd by default, so `client.k3s` needed an AES-128 (`aes`) key.

That took three settings:

- The mons allow both ciphers: `ceph_mon_settings: {auth_allowed_ciphers: aes,aes256k}`. `aes256k` stays preferred and is what every daemon and every other client still uses; `client.admin`'s key is `aes256k`.
- `client.k3s` has `key_type: aes` in `ceph_clients`. You can tell the types apart by the key's first two characters: `AQ` for `aes`, `Ag` for `aes256k`.
- Ceph then raises three warnings, and has no option to turn them off: `AUTH_INSECURE_CLIENT_KEY_TYPE` (a client has an `aes` key), `AUTH_INSECURE_KEYS_ALLOWED` and `AUTH_INSECURE_KEYS_CREATABLE`. They're muted for good (`ceph_health_mutes`, sticky) and left out of the HEALTH_WARN alert by name.

The trade-off is visibility. Because `AUTH_INSECURE_CLIENT_KEY_TYPE` is muted, a second `aes` client wouldn't raise anything; the list in `vars/group-ceph.yaml` is the only record.

## Why Buckle never rotates a key

Buckle creates a client with the `key_type` from the vars, but if the client already exists with a key of the other type, the resources script reports it and fails the step (after every other step has run) instead of rotating. Rotating breaks every holder of the old key at once, and the holder that matters, ceph-csi's secret, lives SOPS-encrypted in another repo. A person with both in hand does it: [Rotate a client key](../how-to/rotate-a-client-key.md).

## Where the keys live

| Key | Where |
|---|---|
| `client.admin` | `/etc/ceph/ceph.client.admin.keyring` on all three hosts (label `_admin`) |
| `client.k3s` | the cluster; the copy for ceph-csi in k8s-deployment `apps/ceph-csi-rbd/cluster/labk3s/csi-rbd.secret.yaml` (SOPS, age) |
| cephadm's SSH key | private half in the cluster's config-key store; public half in `ceph_cephadm_pubkey`, on root's `authorized_keys` with `from="100.64.0.0/10"` |
| S3 users | RGW; `radosgw-admin user info --uid=<uid>` |

None of them belong in this repo.

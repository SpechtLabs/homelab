# Explanation

Why the cluster is built the way it is, and what has gone wrong with it.

- [Design](design.md): cephadm with Buckle around it, everything on the tailnet, why there's no Tailscale Service for Ceph, restarts, monitoring.
- [Keys and ciphers](keys-and-ciphers.md): `aes` vs `aes256k`, the three muted warnings, why Buckle won't rotate keys.
- [Kernel, disk and hardware](kernel-disk-and-hardware.md): the 4K-page kernel, the split NVMe, the LV, memory, PCIe Gen 2.
- [Failure modes seen so far](failure-modes.md): incidents since 2026-11-18 and the gotchas they taught.

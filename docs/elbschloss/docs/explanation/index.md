# Explanation

Why Elbschloss is built the way it is, and the gotchas that need some context.

- [isa, and why so much runs on it](isa.md): what moved there from the NUC, what breaks when it's down, what softens that.
- [How power-loss shutdown is ordered](power-loss-shutdown.md): who goes first on battery, who goes last, and the gaps.
- [The NAS and Tailscale](nas-and-tailscale.md): why DSM sits outside Buckle, the Service pass-through quirk on 1.98.4, NFS through `127.0.0.1`.

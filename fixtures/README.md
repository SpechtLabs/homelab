# Host fixtures

One facts file per host. `mise run validate` (and CI) dry-plans every host against them, so
selectors, templates and task specs are checked without a live host. How to refresh one:
[Update a host fixture](../docs/fleet/docs/how-to/update-a-host-fixture.md) in the fleet docs
([Backstage](https://backstage.k8s.specht-labs.de/docs/default/system/fleet/how-to/update-a-host-fixture/)).

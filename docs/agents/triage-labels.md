# Triage labels

The Matt Pocock skills use these five canonical triage roles. Foreman uses the same strings in GitHub Issues.

| Role | GitHub label | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | Maintainer needs to evaluate this issue |
| `needs-info` | `needs-info` | Waiting on reporter for more information |
| `ready-for-agent` | `ready-for-agent` | Fully specified and ready for an AFK agent |
| `ready-for-human` | `ready-for-human` | Requires human implementation or decision |
| `wontfix` | `wontfix` | Will not be actioned |

All five labels already exist in `alexdancer/foreman-ai-hq`. Verify with `gh-axi label list -R alexdancer/foreman-ai-hq`; do not create duplicate labels.

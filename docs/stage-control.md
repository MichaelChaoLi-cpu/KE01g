# Stage Control

Current stage: `kila`

Only global skills and the current Frame's stage skills are active in Codex.

## Frame Status

| Frame | Installed version | State |
|---|---|---|
| MiliFrame | `3.2.3` | `frozen` |
| MicreFrame | `-` | `not-installed` |
| UnaFrame | `0.0.7` | `frozen` |
| KilaFrame | `0.1.5` | `active` |

## Active Skill Policy

### Global

- `check-repo-health`
- `manage-data-versioning`
- `manage-frame-registry`
- `manage-git-workflow`
- `manage-stage-control`

### KilaFrame stage

- `build-procedure`
- `build-response-draft`
- `build-revision-plan`
- `convert-origin-docx`
- `convert-response-docx`
- `edit-markup-docx`
- `execute-procedure`
- `init-revision-workspace`
- `kila-record-human-decision`
- `make-clean-docx`

## Transition History

| Time | From | To | Reason | Gate |
|---|---|---|---|---|
| 2026-09-18T01:25:00Z | none | una | Register the existing Una workflow from .codex/una-install.json and article/una/docx-export-manifest.md before the user-requested major revision transition. | legacy-state-registration |
| 2026-09-18T01:25:22Z | una | kila | 收到 major revision，用户要求切换到 Kila 修回阶段。 | human-confirmed |

<!-- miliframe-stage-control-data
{
  "current_stage": "kila",
  "frozen_frames": [
    "mili",
    "una"
  ],
  "history": [
    {
      "at": "2026-09-18T01:25:00Z",
      "from": "none",
      "gate": "legacy-state-registration",
      "reason": "Register the existing Una workflow from .codex/una-install.json and article/una/docx-export-manifest.md before the user-requested major revision transition.",
      "to": "una"
    },
    {
      "at": "2026-09-18T01:25:22Z",
      "from": "una",
      "gate": "human-confirmed",
      "reason": "收到 major revision，用户要求切换到 Kila 修回阶段。",
      "to": "kila"
    }
  ],
  "schema_version": 1,
  "updated_at": "2026-09-18T01:25:22Z"
}
miliframe-stage-control-data -->

## Using Skills

In Claude Code, invoke any skill with:

```
/skill-name
```

Common combinations:

```
/autoplan
/pd-resume all
/pd-resume [slug]
/save-state
/save-state [slug]
/save-state all
/swarm
/pipeline-feature [description]
/pipeline-bugfix [bug]
/pipeline-content [topic]
/pipeline-audit [path]
/pipeline-deploy [target]
```

## Creating a Skill

See `core/agents/` for the full developer guide, or use `/skill-creator`.
After adding, renaming or removing a skill folder:

```bash
python3 scripts/skill-registry.py          # regenerate this file
python3 scripts/skill-registry.py --lint   # no new lint violations
```

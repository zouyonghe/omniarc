---
name: search-basics
description: Search flow guidance for desktop agents
version: 1
tags: [search]
stages: [planner, decision]
platforms: [macos, windows]
hosts: [codex, opencode, claude, generic, openclaw]
requires_capabilities: [screen_capture]
priority: 8
---

Keep search queries concise. Re-evaluate after each page transition and do not chain a search query change and a result click in the same step.

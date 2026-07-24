---
name: usd-scene-assets
description: Design, review, or refactor USD scene assets for simulation-ready scene composition. Use when working with USD/USD(A)/USDZ scene files, modular scene asset layout, packageable texture/material references, visual-vs-collision geometry separation, physics layer organization, Isaac Sim/IsaacLab scene assets, or multi-environment cloned scene structures.
---

# USD Scene Assets

Use this skill to organize USD scenes as reusable, packageable, simulation-ready assets rather than one-off flattened stages.

## Core workflow

1. Classify the asset:
   - **Standalone scene**: opens directly in Isaac Sim or usdview.
   - **Cloneable env asset**: referenced repeatedly under `/World/envs/env_*`.
   - **Object asset**: reusable object with its own visual, collision, material, and physics layers.

2. Separate concerns into layers:
   - root scene: world entry point, environment placement, global lights/cameras if needed;
   - object asset entry point: stable default prim and object-local namespace;
   - geometry/material layers: renderable meshes, collision meshes, materials, textures;
   - neutral physics layer: USD Physics bodies, joints, collision flags;
   - backend-specific layers: PhysX, Newton/MuJoCo-Warp, or engine-specific tuning.

3. Keep paths portable:
   - use relative asset paths for sublayers, references, payloads, mesh files, and textures;
   - copy textures/resources into the asset package;
   - keep absolute source paths only as debug metadata, never as required asset dependencies.

4. Keep visual and physics geometry distinct:
   - visual meshes: `purpose = "default"` or inherited/default render purpose;
   - collision meshes: `purpose = "guide"` and hidden from normal rendering;
   - do not generate physics colliders from visual meshes unless intentionally debugging.

5. Check downstream semantics:
   - Isaac Sim GUI inspection can use a full standalone scene.
   - IsaacLab RL should prefer cloneable env assets without per-env global physics scenes or duplicate global grounds.
   - Multi-env layouts should override object transforms per env, not duplicate asset files.

## When details matter

Read [scene-asset-structure.md](references/scene-asset-structure.md) when you need concrete hierarchy, layer, naming, or IsaacLab cloning conventions.

## Validation checklist

- Stage has a meaningful `defaultPrim`.
- Asset paths resolve after moving/copying the asset folder.
- Textures are packaged under the asset tree and referenced relatively.
- Collision meshes do not render in normal viewport mode.
- Physics schema is authored on object/body prims, not only on visual meshes.
- Backend-specific schema does not pollute the neutral asset unless intentional.
- Cloneable assets do not define duplicate global `/World/physicsScene` or duplicate global ground per env.

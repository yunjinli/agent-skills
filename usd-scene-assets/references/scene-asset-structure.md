# USD scene asset structure

Use these conventions when designing or reviewing simulation-ready USD scenes.

## Recommended hierarchy

Standalone scene:

```text
scene.usda
└── /World
    ├── physicsScene              # global, standalone only
    ├── ground                    # global, standalone only
    ├── lights/cameras            # optional inspection aids
    └── scene
        ├── obj_000 -> assets/obj_000/obj_000.usda
        ├── obj_001 -> assets/obj_001/obj_001.usda
        └── ...
```

Cloneable IsaacLab env asset:

```text
env_asset.usda
└── /Scene
    ├── table
    ├── objects
    │   ├── obj_000 -> assets/obj_000/obj_000.usda
    │   └── ...
    └── layout metadata
```

IsaacLab runtime stage:

```text
/World
├── physicsScene
├── defaultGroundPlane
└── envs
    ├── env_0/Scene -> env_asset.usda
    ├── env_1/Scene -> env_asset.usda
    └── ...
```

Avoid placing `/World/physicsScene` or global ground inside an asset that will be cloned per env.

## Object asset package

Use one folder per object:

```text
assets/obj_001/
├── obj_001.usda
├── payloads/
│   ├── base.usda
│   ├── geometries.usda
│   ├── materials.usda
│   ├── instances.usda
│   ├── physics.usda
│   ├── physx.usda
│   └── newton_mujoco.usda
└── resources/
    ├── textures/
    └── meshes/
```

Layer responsibilities:

- `obj_001.usda`: default prim, sublayer/reference composition, no heavy mesh data if payloading.
- `base.usda`: stable prim hierarchy, object metadata, part/body transforms, joints if neutral.
- `geometries.usda`: raw mesh geometry definitions or references to packaged mesh resources.
- `materials.usda`: material prims and texture shader networks.
- `instances.usda`: visual/collision mesh instances under body/part prims and material bindings.
- `physics.usda`: neutral USD Physics API, masses, bodies, joints, collision flags.
- `physx.usda`: PhysX-specific APIs and solver/collider tuning.
- `newton_mujoco.usda`: Newton/MuJoCo-Warp-specific tuning when supported.

## Namespaces

Prefer object-local paths:

```text
/obj_001
├── base
│   └── geometry
│       ├── visual
│       └── collision_000
├── part_001
│   └── geometry
│       ├── visual
│       └── collision_000
└── Joints
    └── part_001_joint
```

Do not bind materials or relationships using absolute `/World/...` paths inside reusable object assets. Use object-local relationships where possible.

## Visual and collision conventions

Visual mesh:

```usda
def Mesh "visual" (
    prepend apiSchemas = ["MaterialBindingAPI"]
)
{
    uniform token purpose = "default"
    rel material:binding = </obj_001/Looks/visual_mat>
}
```

Collision mesh:

```usda
def Mesh "collision_000" (
    prepend apiSchemas = ["PhysicsCollisionAPI", "PhysicsMeshCollisionAPI"]
)
{
    uniform token purpose = "guide"
    token visibility = "inherited"
    bool physics:collisionEnabled = true
    uniform token physics:approximation = "convexHull"
}
```

`purpose = "guide"` means the mesh is non-render geometry intended for guides, collision, and debug overlays. It can still appear when the viewport is set to show guide/debug geometry.

## Texture and resource portability

Correct:

```usda
asset inputs:file = @../resources/textures/base_color.png@
```

Avoid required dependencies like:

```usda
asset inputs:file = @/home/user/project/scenes/foo/visual.png@
```

Absolute source paths are acceptable only as custom debug metadata:

```usda
custom string digitalSister:source = "/home/user/project/raw/visual.obj"
```

The asset must still load without that path.

## Physics layering

Use neutral USD Physics for structure:

- `PhysicsRigidBodyAPI`
- `PhysicsMassAPI`
- `PhysicsCollisionAPI`
- `PhysicsMeshCollisionAPI`
- `PhysicsRevoluteJoint` / `PhysicsPrismaticJoint`
- `PhysicsDriveAPI`
- `PhysicsArticulationRootAPI`

Use backend layers for implementation details:

- PhysX: `PhysxRigidBodyAPI`, `PhysxCollisionAPI`, `PhysxJointAPI`, `PhysxArticulationAPI`.
- Newton/MuJoCo-Warp: keep separate until the schema/config is intentionally authored.

Avoid mixing backend-specific tuning into the same layer that defines neutral geometry and hierarchy unless the asset is explicitly backend-only.

## IsaacLab cloning guidance

For RL:

1. Reference the same object/env asset into each `/World/envs/env_N`.
2. Apply per-env object transforms as overrides.
3. Keep one global physics scene.
4. Keep one global ground unless the env asset intentionally contains local terrain.
5. Remove or disable objects that are semantically not part of the task, such as lower-shelf clutter when generating tabletop layouts.
6. For randomized tabletop layouts, require each object footprint to stay fully inside the support surface footprint and avoid inter-object footprint overlap before physics starts.

## Review checklist

- Can the asset folder be moved and still load?
- Are materials bound under stable object-local paths?
- Are all texture paths relative and packaged?
- Are collision meshes guide-purpose and separated from visual meshes?
- Are physics APIs applied to body/part prims instead of only visual meshes?
- Are global scene objects excluded from cloneable env assets?
- Is backend-specific physics authored in a separate layer?
- Is the readable `.usda` debug representation available for inspection when binary `.usd` is produced?

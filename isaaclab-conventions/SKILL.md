---
name: isaaclab-conventions
description: Catch silent convention mismatches when moving state between IsaacLab and another simulator or data source. Use when writing root/body poses into IsaacLab, converting MuJoCo/MJCF trajectories or USD assets into IsaacLab motions, reading robot state back out, debugging a robot that spawns in the wrong orientation or falls immediately, or validating a motion/trajectory conversion.
---

# IsaacLab Conventions

Use this skill whenever state crosses the boundary between IsaacLab and anything else — MuJoCo, a recorded trajectory, a retargeting pipeline, your own npz. These mismatches do not raise. They produce a robot that is subtly or badly wrong, and the wrongness is easy to misattribute to physics, gains, or the policy.

## Quaternion order is version-specific — check it, do not assume

IsaacLab changed quaternion ordering between major versions. MuJoCo and USD use `(w, x, y, z)`. IsaacLab 6.x uses `(x, y, z, w)` throughout — writers, readers, and `isaaclab.utils.math`. Earlier IsaacLab used `(w, x, y, z)`.

Confirm against the installed source before converting anything:

```bash
grep -rn "quaternion orientation in" $ISAACLAB/source/isaaclab_physx/isaaclab_physx/assets/rigid_object/rigid_object.py
grep -n "def quat_mul" -A 6 $ISAACLAB/source/isaaclab/isaaclab/utils/math.py
```

Both should agree. If they say `(x, y, z, w)` and your source data is MuJoCo, reorder at the boundary and nowhere else:

```python
def wxyz_to_xyzw(q):          # MuJoCo/USD -> IsaacLab 6.x
    return q[..., [1, 2, 3, 0]]
```

Keep all intermediate math in the source convention and convert once, at the write. Mixed conventions midway are far harder to find than a single wrong conversion.

## The failure signature

A wrong quaternion order does not look like a quaternion bug. It looks like:

- robot spawns upright but falls instantly, or stands at an odd angle;
- limb positions that are correct relative to each other but rigidly rotated as a group;
- body offsets whose error grows with distance from the root.

If body-relative geometry is right but world placement is wrong, suspect the root orientation before suspecting physics.

## Do not diagnose with an ambiguous probe

A quaternion bug corrupts the experiment used to find it. Writing `[1, 0, 0, 0]` as "identity" is a 180-degree rotation about X if the convention is `xyzw` — so a zero-configuration comparison will "prove" the asset has a flipped base frame.

Probe with a rotation whose **axis** is unambiguous:

```
write (0.7071, 0, 0, 0.7071)   # Rz(90) read as wxyz; Rx(90) read as xyzw
```

Then check which axis the bodies actually rotate about. The axis identifies the convention; magnitudes and signs do not.

## Writing state does not update kinematics

`write_joint_state_to_sim` / `write_root_state_to_sim` set state but do not re-run forward kinematics or refresh the renderer. Reading `body_pos_w` straight afterwards returns stale poses, and a viewer shows a motionless robot while debug markers move.

```python
robot.write_joint_state_to_sim(q, qd)
sim.forward()                     # update kinematics without stepping physics
scene.update(sim.get_physics_dt())
value = robot.data.body_pos_w     # now current
```

## Never validate a conversion against itself

Comparing a converted motion to the data it was built from returns zero however wrong the conversion is. Replay through the **source** simulator and compare body-by-body:

- drive the source sim from the original trajectory,
- compare its body world positions against the converted motion's,
- expect micrometres, not millimetres.

When the source model has equality constraints (MuJoCo tendon/joint coupling), apply them explicitly in the check — `mj_forward` computes constraint *forces*, not constrained positions, so coupled joints sit at zero and produce spurious error.

## Other silent boundary issues

- **Warp proxies**: several `data.*` properties return a warp `ProxyArray` in IsaacLab 6.x. Torch math rejects it. Reach through `.torch`, as IsaacLab's own MDP terms do.
- **USD import order**: config modules must not import runtime classes (`Articulation`, `ContactSensor`, action term implementations). Hydra imports configs before `SimulationApp` starts; a second USD init aborts in `TfEnum::_AddName`. Use `lazy_export()` with a `.pyi` manifest and keep `class_type` a string.
- **Exp-kernel rewards**: `std` is a per-element tolerance, so reduce with `mean`, not `sum`. Summing over N joints makes the effective tolerance depend on N and can saturate the kernel to zero reward *and zero gradient*.

## When details matter

Read [conversion-checks.md](references/conversion-checks.md) for the concrete probe scripts and the boundary-crossing checklist.

## Validation checklist

- Quaternion order verified against the installed IsaacLab source, not assumed.
- Conversion validated against the source simulator, not against itself.
- `sim.forward()` called before reading derived state after a write.
- Coupled/mimic joints reproduced explicitly on both sides of the comparison.
- Config modules import no runtime classes; `pxr` absent from `sys.modules` after importing the env cfg.
- Exp-kernel reward terms reduce with `mean`; kernel value at realistic error is well away from zero.

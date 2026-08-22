# Conversion checks

Concrete procedures for the checks named in the skill. Each is cheap and each has caught a real, silent bug.

## Determine the quaternion convention empirically

Read the installed source first. If it is ambiguous or you want certainty, probe the running sim.

Spawn the articulation, zero every joint, and write a rotation whose axis is unambiguous under
either ordering. `(0.7071, 0, 0, 0.7071)` is `Rz(90)` read as `wxyz` and `Rx(90)` read as `xyzw`:

```python
q = torch.zeros_like(robot.data.joint_pos)
robot.write_joint_state_to_sim(q, torch.zeros_like(q))
root = torch.zeros((1, 13), device=robot.device)
root[0, 2] = 1.0                                  # 1 m up
root[0, 3:7] = torch.tensor([0.7071, 0.0, 0.0, 0.7071], device=robot.device)
robot.write_root_state_to_sim(root)
sim.forward()
scene.update(sim.get_physics_dt())

pelvis = robot.data.body_pos_w[0, robot.body_names.index("pelvis")]
for b in ("left_shoulder_roll_link", "left_ankle_roll_link"):
    print(b, (robot.data.body_pos_w[0, robot.body_names.index(b)] - pelvis).cpu().numpy())
```

Compare against the same bodies at identity. If the offsets rotate about **X**, the array was read
as `xyzw`. If about **Z**, as `wxyz`.

Do not probe with `[1, 0, 0, 0]`. It is identity under `wxyz` and `Rx(180)` under `xyzw`, so a
"zero configuration" comparison silently attributes the rotation to the asset instead of the
convention. That mistake produces a convincing but wrong conclusion that the USD base frame is
flipped.

## Validate a converted motion against the source simulator

The check that matters: drive the **source** simulator from the original trajectory and compare
body world positions against the converted motion.

```python
mj_data.qpos[0:3]  = traj["root_pos"][k]
mj_data.qpos[3:7]  = traj["root_rot"][k]
mj_data.qpos[act_qposadr] = traj["dof_pos"][k]
for child, parent, ratio in coupling:     # see below
    mj_data.qpos[child] = ratio * mj_data.qpos[parent]
mujoco.mj_forward(mj_model, mj_data)

error = norm(mj_data.body(name).xpos - motion["body_pos_w"][frame, index])
```

Expect micrometres. Millimetres mean a real mismatch; decimetres mean a convention error.

Map body names across the boundary explicitly — MuJoCo's `<attach>` prefixes attached subtrees
(`l_rh_left_hand_base`) while the USD does not (`left_hand_base`).

## Reproduce equality/mimic coupling on both sides

`mj_forward` computes constraint *forces*, not constrained positions. Coupled joints stay at
whatever qpos holds, so a comparison against a simulator that does enforce coupling shows error
concentrated on the most distal coupled links.

Read the coefficients from the model rather than hardcoding them:

```python
coupling = []
for eq in range(mj_model.neq):
    if mj_model.eq_type[eq] != mujoco.mjtEq.mjEQ_JOINT:
        continue
    child  = mj_model.jnt_qposadr[mj_model.eq_obj1id[eq]]
    parent = mj_model.jnt_qposadr[mj_model.eq_obj2id[eq]]
    coupling.append((child, parent, float(mj_model.eq_data[eq][1])))
```

MuJoCo equality coefficients and USD `PhysxMimicJointAPI` multipliers describing the same hardware
should match numerically. If they do, the two models agree and any residual error is elsewhere.

## Confirm a config module does not import USD

```bash
$ISAAC_PYTHON -c "
import sys
import your_pkg.tasks.<task>.<task>_env_cfg
print(len([m for m in sys.modules if m == 'pxr' or m.startswith('pxr.')]))"
```

Must print `0`. Anything above zero means Hydra will initialise USD before `SimulationApp`, which
aborts the process inside `TfEnum::_AddName` with no usable Python traceback.

Runtime classes that pull in USD: `isaaclab.assets.Articulation`, `isaaclab.sensors.ContactSensor`,
`isaaclab.envs.mdp.actions.joint_actions.*`. Their `...Cfg` counterparts are clean. Put the runtime
ones under `TYPE_CHECKING` and reference implementations by string
(`class_type = "{DIR}.module:Class"`).

## Sanity-check an exp-kernel reward before training

`exp(-error / std**2)` is flat once `error` exceeds a few times `std**2`; both value and gradient
vanish. Evaluate the kernel at the error you actually expect:

```python
for per_element_error in (0.05, 0.1, 0.2, 0.3):
    e2 = per_element_error ** 2
    print(per_element_error,
          math.exp(-n_elements * e2 / std**2),   # sum form
          math.exp(-e2 / std**2))                # mean form
```

If the value at realistic error is below ~0.01, the term contributes nothing and cannot teach
anything. Reduce with `mean` so `std` keeps its meaning as a per-element tolerance independent of
how many elements the robot has.

## Reading training curves

Mean reward and mean episode length both rise when a policy merely learns to survive. Divide the
per-term episode reward by episode length to get per-step contribution, and watch the task metrics
(`Metrics/motion/error_*`) directly. A policy whose per-step reward is flat while episodes lengthen
is not improving at the task.

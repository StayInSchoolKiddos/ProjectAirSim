# Tiguar visual demo with Skywalker X8 placeholder physics

This example uses the supplied Tiguar Black FBX and matching texture for visuals,
and the existing, unmodified Skywalker X8 JSBSim model and autopilot for motion.
It is **not a Tiguar aerodynamic, mass, propulsion, or performance model**.

## Files

- Source artwork: `unreal/Blocks/Plugins/Drone/SourceAssets/Tiguar/`.
- Asset importer: `tools/unreal/import_tiguar.py`.
- Generated mesh expected by the robot: `/Drone/Tiguar/SM_Tiguar`.
- Scene/client: `client/python/example_user_scripts/jsbsim/tiguar/`.
- Placeholder flight model: `core_sim/jsbsim/models/aircraft/x8/x8.xml`.

The artwork was copied from the user's `OneDrive_2026-10-20` Downloads folder.
The originals are unchanged. The FBX's historical D: texture paths are not used:
the importer explicitly assigns the supplied `Tiguar_Black.tga`. A second FBX
material references `tiguarSTLv281.tga`, which was not supplied; those hardware
surfaces receive a neutral dark material. No new textures are generated.

## Import once

Use the existing Windows UE 5.8 installation, without downloading plugins or
changing engine files. Close other Blocks editors before starting this fresh
import process. In PowerShell from the repository root:

```powershell
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Win64-DebugGame.exe' `
  "$PWD\unreal\Blocks\Blocks.uproject" `
  '-EnablePlugins=PythonScriptPlugin,EditorScriptingUtilities' `
  "-ExecutePythonScript=$PWD\tools\unreal\import_tiguar.py"
```

This enables installed editor scripting plugins for this invocation. It creates
separate assets under `/Drone/Tiguar`, combines the visible FBX components,
excludes collision/engine/mount guide objects, and applies the supplied texture.
It preserves FBX transforms and converts units/orientation using the importer.
The final mesh bakes a 180-degree yaw to align this FBX's nose with the robot's
+X forward axis. The robot's root visual offset stays zero, matching the X8
approach: runtime root-pose updates would otherwise replace that offset.
It does not overwrite an existing `SM_Tiguar` or save the current map.
An `import_report.json` beside the source artwork records included/excluded parts
and the merged bounds in centimetres when import succeeds.

Check the model's orientation, size, textures, and pivot in Unreal before treating
the visual integration as verified. FBX unit metadata is not a measured Tiguar
dimension. Propellers, wheels and control surfaces are rigid in this first demo.

## Run

Use the previously working **DebugGame Editor / Win64** target, with Debug sim
libraries built and staged. The existing JSBSim staging target must also have
copied the X8 model, electric motor and systems into the plugin's `SimLibs`.
Click Play, then run in a Python environment containing the local client:

```powershell
python client/python/example_user_scripts/jsbsim/tiguar/hello_tiguar_jsbsim.py --max-sim-time 20 --telemetry tiguar-telemetry.csv
```

The client loads `SceneTiguarX8Placeholder` and a robot named `Tiguar`, seeds the
same airborne state as the X8 example, and uses the existing X8 waypoint follower.
It checks finite JSBSim state before and after each step, logs the placeholder
physics warning, and optionally writes altitude/airspeed/attitude telemetry.
The scene remains paused after the configured run. This is an air-launch demo,
not a ground takeoff/landing demonstration. It does not use quadcopter commands.

No Tiguar XML is created: `jsbsim-model` deliberately remains `x8`, avoiding any
implication that renaming the model changes its physical behavior. Existing X8
files, vehicle controls and dynamics are unchanged.

## Validation status

Verified on Windows / UE 5.8.3 on 2026-10-20:

- Blocks DebugGame Editor rebuilt successfully (450.60 seconds).
- Imported and saved the source parts, 4K texture, materials and final mesh.
- Visually checked the model and baked forward-axis correction in Blocks.
- Robot/scene JSON schema checks and Python syntax/import checks passed.
- A five-second smoke run and final 20-second airborne run completed with exit
  code 0. The final CSV contains 20 finite altitude/airspeed/attitude samples;
  JSBSim finite-state guards run before and after every physics-control step.
- Left the final scene paused with Tiguar visible. No complete waypoint circuit,
  takeoff, landing, real-aircraft performance or ground-contact validation is
  claimed by this short run.

The FBX produces nearly-zero/degenerate tangent warnings on some components.
These are artwork/shading limitations; the import and demo still completed.
The missing second texture uses the hardware fallback described above.

The task's initial unattended editor launch did not produce an import log.
Import was completed using Unreal's editor Python command after launching
Blocks from Visual Studio. The temporary project-level scripting plugin entries
were removed afterward; no engine files or dependency versions were changed.

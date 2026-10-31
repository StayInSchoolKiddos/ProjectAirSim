"""Import supplied Tiguar visuals into /Drone/Tiguar (Unreal Editor Python).

Run in a fresh Blocks editor process with PythonScriptPlugin and
EditorScriptingUtilities enabled. Does not save or replace the current map.
Existing final assets are never overwritten. See docs/physics/tiguar.md.
"""

import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "unreal/Blocks/Plugins/Drone/SourceAssets/Tiguar"
DEST = "/Drone/Tiguar"
FINAL = DEST + "/SM_Tiguar"


def orient_forward(mesh):
    """Bake the supplied FBX's -X nose to +X; root pose updates replace offsets."""
    if unreal.EditorAssetLibrary.get_metadata_tag(mesh, "TiguarForwardAligned") == "true":
        return
    subsystem = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    settings = subsystem.get_lod_build_settings(mesh, 0)
    settings.set_editor_property("build_scale3d", unreal.Vector(-1, -1, 1))
    subsystem.set_lod_build_settings(mesh, 0, settings)
    unreal.EditorAssetLibrary.set_metadata_tag(mesh, "TiguarForwardAligned", "true")
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)


def import_file(filename, destination, options=None, factory=None):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(filename))
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)
    if options:
        task.set_editor_property("options", options)
    if factory:
        task.set_editor_property("factory", factory)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError("No assets imported from " + str(filename))
    return [unreal.load_asset(p) for p in task.imported_object_paths]


def material(name, texture=None):
    path = DEST + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return unreal.load_asset(path)
    m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, DEST, unreal.Material, unreal.MaterialFactoryNew()
    )
    lib = unreal.MaterialEditingLibrary
    if texture:
        node = lib.create_material_expression(m, unreal.MaterialExpressionTextureSample)
        node.set_editor_property("texture", texture)
        lib.connect_material_property(node, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    else:
        node = lib.create_material_expression(m, unreal.MaterialExpressionConstant3Vector)
        node.set_editor_property("constant", unreal.LinearColor(0.04, 0.04, 0.04, 1))
        lib.connect_material_property(node, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = lib.create_material_expression(m, unreal.MaterialExpressionConstant)
    rough.set_editor_property("r", 0.6)
    lib.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    # Texture alpha is not opacity: UV atlas backgrounds must not cut the mesh.
    lib.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)
    return m


def main():
    if unreal.EditorAssetLibrary.does_asset_exist(FINAL):
        unreal.log("Tiguar already exists; leaving existing assets untouched: " + FINAL)
        return
    for name in ("Tiguar_Black.fbx", "Tiguar_Black.tga"):
        if not (SOURCE / name).is_file():
            raise FileNotFoundError(SOURCE / name)

    texture = unreal.load_asset(DEST + "/Textures/Tiguar_Black")
    if not texture:
        textures = import_file(SOURCE / "Tiguar_Black.tga", DEST + "/Textures")
        texture = next(a for a in textures if isinstance(a, unreal.Texture2D))
    body_material = material("M_TiguarBlack", texture)
    hardware_material = material("M_TiguarHardware")

    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property("automated_import_should_detect_type", False)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False)
    data = ui.static_mesh_import_data
    for key, value in {
        "combine_meshes": False,
        "transform_vertex_to_absolute": True,
        "auto_generate_collision": False,
        "generate_lightmap_u_vs": False,
        "convert_scene": True,
        "convert_scene_unit": True,
        "force_front_x_axis": True,
    }.items():
        data.set_editor_property(key, value)
    existing = unreal.EditorAssetLibrary.list_assets(DEST + "/Parts", recursive=True)
    parts = ([unreal.load_asset(p) for p in existing] if existing else
             import_file(SOURCE / "Tiguar_Black.fbx", DEST + "/Parts", ui, unreal.FbxFactory()))
    actors = []
    merged_actor = None
    report = {"source": str(SOURCE), "included": [], "excluded": [],
              "physics": "Skywalker X8 placeholder; not Tiguar flight dynamics"}
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    try:
        for mesh in parts:
            if not isinstance(mesh, unreal.StaticMesh):
                continue
            name = mesh.get_name().lower()
            # RealFlight collision/engine/mount guides are not aircraft skin.
            if any(token in name for token in ("coll_", "cube", "_mount", "_engine_")):
                report["excluded"].append(mesh.get_path_name())
                continue
            for index, slot in enumerate(mesh.static_materials):
                mat = body_material if "001" in str(slot.material_slot_name) else hardware_material
                mesh.set_material(index, mat)
            unreal.EditorAssetLibrary.save_loaded_asset(mesh)
            actor = actor_subsystem.spawn_actor_from_object(mesh, unreal.Vector(0, 0, 0))
            actors.append(actor)
            report["included"].append(mesh.get_path_name())
        if not actors:
            raise RuntimeError("No visible Tiguar mesh parts were imported")
        options = unreal.MergeStaticMeshActorsOptions()
        # Mesh merge adds its own SM_ prefix to the base package name.
        options.set_editor_property("base_package_name", DEST + "/Tiguar")
        options.set_editor_property("destroy_source_actors", False)
        options.set_editor_property("spawn_merged_actor", True)
        settings = options.mesh_merging_settings
        if hasattr(unreal, "MeshMergePivotType"):
            settings.set_editor_property("pivot_type", unreal.MeshMergePivotType.WORLD_ORIGIN)
        else:
            settings.set_editor_property("pivot_point_at_zero", True)
        settings.set_editor_property("merge_materials", False)
        settings.set_editor_property("generate_light_map_uv", False)
        options.set_editor_property("mesh_merging_settings", settings)
        merged_actor = unreal.get_editor_subsystem(
            unreal.StaticMeshEditorSubsystem
        ).merge_static_mesh_actors(actors, options)
        if not merged_actor:
            raise RuntimeError("Tiguar mesh merge did not produce " + FINAL)
        mesh = merged_actor.static_mesh_component.static_mesh
        if mesh.get_path_name().split(".")[0] != FINAL:
            if not unreal.EditorAssetLibrary.rename_asset(mesh.get_path_name(), FINAL):
                raise RuntimeError("Could not name merged Tiguar mesh " + FINAL)
            mesh = unreal.load_asset(FINAL)
        orient_forward(mesh)
        bounds = mesh.get_bounds()
        report["bounds_origin_cm"] = [bounds.origin.x, bounds.origin.y, bounds.origin.z]
        report["dimensions_cm"] = [2*bounds.box_extent.x, 2*bounds.box_extent.y, 2*bounds.box_extent.z]
        report["baked_yaw_degrees"] = 180
        unreal.EditorAssetLibrary.save_loaded_asset(mesh)
        (SOURCE / "import_report.json").write_text(json.dumps(report, indent=2) + "\n")
        unreal.log("TIGUAR_IMPORT_COMPLETE " + json.dumps(report))
    finally:
        # Only temporary actors created by this script are removed; no map is saved.
        for actor in actors + ([merged_actor] if merged_actor else []):
            actor_subsystem.destroy_actor(actor)


if __name__ == "__main__":
    main()

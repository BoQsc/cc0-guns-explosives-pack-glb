import bpy
import os

source_dir = r"C:\Users\Windows10_new\Downloads\Guns&Explosives (1)\Guns&Explosives"
target_dir = r"C:\Users\Windows10_new\Downloads\Guns&Explosives (1)_glb"

def get_texture_file(folder, prefix, type_keywords):
    for f in os.listdir(folder):
        f_lower = f.lower()
        if f_lower.endswith(('.png', '.jpg', '.jpeg', '.tga', '.tif')):
            if not prefix or f_lower.startswith(prefix.lower()):
                if any(tk in f_lower for tk in type_keywords):
                    return os.path.join(folder, f)
    return None

for root, dirs, files in os.walk(source_dir):
    for file in files:
        if file.lower().endswith('.fbx'):
            fbx_path = os.path.join(root, file)
            
            rel_path = os.path.relpath(root, source_dir)
            out_folder = os.path.join(target_dir, rel_path)
            os.makedirs(out_folder, exist_ok=True)
            
            glb_filename = os.path.splitext(file)[0] + ".glb"
            glb_path = os.path.join(out_folder, glb_filename)
            
            print(f"\n--- Processing: {file} ---")
            
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.fbx(filepath=fbx_path)
            
            png_files = [f for f in files if f.lower().endswith('.png')]
            prefixes = []
            for f in png_files:
                if '_' in f:
                    prefixes.append(f.split('_')[0])
                else:
                    prefixes.append(os.path.splitext(f)[0])
            prefixes = list(set(prefixes))

            # Helper function to build the PBR nodes cleanly
            def build_material_nodes(mat, current_prefix):
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                nodes.clear()
                
                bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                bsdf.location = (0, 0)
                output = nodes.new(type='ShaderNodeOutputMaterial')
                output.location = (300, 0)
                links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                
                def add_texture(filepath, color_space, loc, link_input):
                    if filepath and os.path.exists(filepath):
                        # Load image once to prevent glTF export warnings
                        filename = os.path.basename(filepath)
                        if filename in bpy.data.images:
                            img = bpy.data.images[filename]
                        else:
                            img = bpy.data.images.load(filepath)
                            
                        img.colorspace_settings.name = color_space
                        node = nodes.new('ShaderNodeTexImage')
                        node.image = img
                        node.location = loc
                        if link_input == 'Emission Color' and 'Emission Color' not in bsdf.inputs:
                            link_input = 'Emission'
                        links.new(node.outputs['Color'], bsdf.inputs[link_input])
                        return node
                    return None

                t_base = get_texture_file(root, current_prefix, ['base_color', 'base_colo', 'albedo'])
                t_metal = get_texture_file(root, current_prefix, ['metallic', 'metal'])
                t_rough = get_texture_file(root, current_prefix, ['roughness', 'rough'])
                t_norm = get_texture_file(root, current_prefix, ['normal', 'norm'])
                t_emiss = get_texture_file(root, current_prefix, ['emissive', 'emission'])
                t_opac = get_texture_file(root, current_prefix, ['opacity', 'alpha'])

                add_texture(t_base, 'sRGB', (-300, 200), 'Base Color')
                add_texture(t_metal, 'Non-Color', (-300, -50), 'Metallic')
                add_texture(t_rough, 'Non-Color', (-300, -300), 'Roughness')
                add_texture(t_emiss, 'sRGB', (-300, -750), 'Emission Color')

                if t_opac and os.path.exists(t_opac):
                    add_texture(t_opac, 'Non-Color', (-300, -450), 'Alpha')
                    mat.blend_method = 'BLEND' 

                if t_norm and os.path.exists(t_norm):
                    filename = os.path.basename(t_norm)
                    if filename in bpy.data.images:
                        img = bpy.data.images[filename]
                    else:
                        img = bpy.data.images.load(t_norm)
                    img.colorspace_settings.name = 'Non-Color'
                    tex_node = nodes.new('ShaderNodeTexImage')
                    tex_node.image = img
                    tex_node.location = (-600, -600)
                    
                    norm_node = nodes.new('ShaderNodeNormalMap')
                    norm_node.location = (-300, -600)
                    
                    links.new(tex_node.outputs['Color'], norm_node.inputs['Color'])
                    links.new(norm_node.outputs['Normal'], bsdf.inputs['Normal'])

            # --- THE FIX: BRUTE FORCE VS SMART MODE ---
            if len(prefixes) == 1:
                # BRUTE FORCE: For simple models (Pipe Bomb, AT Mine, Claymore, etc.)
                master_mat = bpy.data.materials.new(name=f"{prefixes[0]}_MasterMat")
                build_material_nodes(master_mat, prefixes[0])
                
                for obj in bpy.context.scene.objects:
                    if obj.type == 'MESH':
                        obj.data.materials.clear() # Delete buggy FBX materials
                        obj.data.materials.append(master_mat) # Force our clean material onto everything
            else:
                # SMART MODE: For complex models (Molotov)
                processed_mats = []
                for obj in bpy.context.scene.objects:
                    if obj.type == 'MESH':
                        if not obj.material_slots:
                            obj.data.materials.append(bpy.data.materials.new(name="Fallback"))
                        
                        for i, slot in enumerate(obj.material_slots):
                            if not slot.material:
                                slot.material = bpy.data.materials.new(name=f"Fallback_{i}")
                                
                            mat = slot.material
                            if mat.name in processed_mats:
                                continue
                                
                            processed_mats.append(mat.name)
                            
                            current_prefix = ""
                            for p in prefixes:
                                if p.lower() in mat.name.lower() or p.lower() in obj.name.lower():
                                    current_prefix = p
                                    break
                            if not current_prefix:
                                current_prefix = prefixes[0]
                                
                            build_material_nodes(mat, current_prefix)

            bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB')
            print(f"Successfully exported to: {glb_path}")

print("\nBATCH CONVERSION V4 COMPLETE!")
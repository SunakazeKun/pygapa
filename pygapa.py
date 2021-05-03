import argparse
import formats.bcsv as bcsv
import formats.jpac210 as jpac210
import os
from helper import *


class ParticleData:
    def __init__(self):
        self.textures = dict()
        self.particles = dict()
        self.effects = list()

    def unpack_json(self, json_file: str, particles_folder: str, bti_folder: str, effects_json_file: str):
        self.textures.clear()
        self.particles.clear()
        self.effects.clear()

        in_json = read_json_file(json_file)
        in_effects_json = read_json_file(effects_json_file)

        unused_texture_names = list()

        print("Loading texture files...")
        for texture_name in in_json["textures"]:
            texture = jpac210.JPATexture()
            texture.file_name = texture_name
            texture.bti_data = read_file(os.path.join(bti_folder, f"{texture_name}.bti"))

            self.textures[texture_name] = texture
            unused_texture_names.append(texture_name)

        print("Loading particle files...")
        for particle_name in in_json["particles"]:
            particle = jpac210.JPAResource()
            in_particle_json = read_json_file(os.path.join(particles_folder, f"{particle_name}.json"))

            particle.unk4 = in_particle_json["unk4"]
            particle.unk6 = in_particle_json["unk6"]
            particle.texture_names = in_particle_json["textures"]

            if "dynamicsBlock" in in_particle_json:
                particle.dynamics_block = jpac210.JPADynamicsBlock()
                particle.dynamics_block.unpack_json(in_particle_json["dynamicsBlock"])
            if "fieldBlocks" in in_particle_json:
                for field_block_json in in_particle_json["fieldBlocks"]:
                    field_block = jpac210.JPAFieldBlock()
                    field_block.unpack_json(field_block_json)
                    particle.field_blocks.append(field_block)
            if "keyBlocks" in in_particle_json:
                for key_block_json in in_particle_json["keyBlocks"]:
                    key_block = jpac210.JPAKeyBlock()
                    key_block.unpack_json(key_block_json)
                    particle.key_blocks.append(key_block)
            if "baseShape" in in_particle_json:
                particle.base_shape = jpac210.JPABaseShape()
                particle.base_shape.unpack_json(in_particle_json["baseShape"])
            if "extraShape" in in_particle_json:
                particle.extra_shape = jpac210.JPAExtraShape()
                particle.extra_shape.unpack_json(in_particle_json["extraShape"])
            if "childShape" in in_particle_json:
                particle.child_shape = jpac210.JPAChildShape()
                particle.child_shape.unpack_json(in_particle_json["childShape"])
            if "exTexShape" in in_particle_json:
                particle.ex_tex_shape = jpac210.JPAExTexShape()
                particle.ex_tex_shape.unpack_json(in_particle_json["exTexShape"])

            for texture_name in particle.texture_names:
                if texture_name in unused_texture_names:
                    unused_texture_names.remove(texture_name)

            self.particles[particle_name] = particle

        if len(unused_texture_names) > 0:
            print("Unused textures found:", unused_texture_names)

        print("Loading effects data...")

        def add_if_missing(ine: dict, oute: dict, key: str, defval):
            val = ine[key] if key in ine else defval
            oute[key] = val

        def add_if_false(ine: dict, oute: dict, key: str, trueval):
            val = ""
            if key in ine and ine[key] is True:
                val = trueval
            oute[key] = val

        index = 0
        for effect_entry in in_effects_json:
            effect = dict()
            effect["No"] = index
            effect["GroupName"] = effect_entry["GroupName"]
            add_if_missing(effect_entry, effect, "AnimName", "")
            add_if_false(effect_entry, effect, "ContinueAnimEnd", "on")
            effect["UniqueName"] = effect_entry["UniqueName"]
            effect["EffectName"] = " ".join(effect_entry["EffectName"])
            add_if_missing(effect_entry, effect, "ParentName", "")
            add_if_missing(effect_entry, effect, "JointName", "")
            add_if_missing(effect_entry, effect, "OffsetX", 0.0)
            add_if_missing(effect_entry, effect, "OffsetY", 0.0)
            add_if_missing(effect_entry, effect, "OffsetZ", 0.0)
            add_if_missing(effect_entry, effect, "StartFrame", 0)
            add_if_missing(effect_entry, effect, "EndFrame", -1)
            add_if_missing(effect_entry, effect, "Affect", "")
            add_if_missing(effect_entry, effect, "Follow", "")
            add_if_missing(effect_entry, effect, "ScaleValue", 1.0)
            add_if_missing(effect_entry, effect, "RateValue", 1.0)
            add_if_missing(effect_entry, effect, "PrmColor", "")
            add_if_missing(effect_entry, effect, "EnvColor", "")
            add_if_missing(effect_entry, effect, "LightAffectValue", 0.0)
            add_if_missing(effect_entry, effect, "DrawOrder", "")

            self.effects.append(effect)
            index += 1

    def unpack_bin(self, jpc_file: str, names_file: str, effects_file: str):
        # Load JPAResource and JPATexture entries
        print("Load JPC file ...")
        particle_container = jpac210.JParticlesContainer()
        particle_container.unpack(read_file(jpc_file))
        self.textures = particle_container.textures
        self.particles.clear()

        # Load ParticleNames entries
        print("Load names BCSV ...")
        particle_names = bcsv.Bcsv()
        particle_names.unpack(read_file(names_file))
        particle_names = particle_names.entries

        # Load AutoEffectList entries
        print("Load effects BCSV ...")
        auto_effects = bcsv.Bcsv()
        auto_effects.unpack(read_file(effects_file))
        self.effects = auto_effects.entries

        # Populate JPAResource entries using their order from ParticleNames
        print("Populate and sort particles  ...")
        for particle_name_entry in particle_names:
            particle_name = particle_name_entry["name"]
            particle_index = particle_name_entry["id"]

            self.particles[particle_name] = particle_container.particles[particle_index]

    def pack_json(self, json_file: str, particles_folder: str, bti_folder: str, effects_json_file: str):
        # Create JSON data that declares which particles and textures belong to this container
        out_json = {
            "particles": list(),
            "textures": list()
        }

        # Create folders if necessary
        os.makedirs(os.path.dirname(json_file), exist_ok=True)
        os.makedirs(particles_folder, exist_ok=True)
        os.makedirs(bti_folder, exist_ok=True)
        os.makedirs(os.path.dirname(effects_json_file), exist_ok=True)

        # Collect particles and write individual JSONs
        print("Dump particles ...")
        for jpa_name, jpa in self.particles.items():
            out_json["particles"].append(jpa_name)

            out_particle_json = {
                "unk4": jpa.unk4,
                "unk6": jpa.unk6
            }

            # Pack blocks
            if jpa.dynamics_block:
                out_particle_json["dynamicsBlock"] = jpa.dynamics_block.pack_json()
            if len(jpa.field_blocks) > 0:
                out_particle_json["fieldBlocks"] = list()

                for field_block in jpa.field_blocks:
                    out_particle_json["fieldBlocks"].append(field_block.pack_json())
            if len(jpa.key_blocks) > 0:
                out_particle_json["keyBlocks"] = list()

                for key_block in jpa.key_blocks:
                    out_particle_json["keyBlocks"].append(key_block.pack_json())
            if jpa.base_shape:
                out_particle_json["baseShape"] = jpa.base_shape.pack_json()
            if jpa.extra_shape:
                out_particle_json["extraShape"] = jpa.extra_shape.pack_json()
            if jpa.child_shape:
                out_particle_json["childShape"] = jpa.child_shape.pack_json()
            if jpa.ex_tex_shape:
                out_particle_json["exTexShape"] = jpa.ex_tex_shape.pack_json()

            # Pack texture names
            out_particle_json["textures"] = jpa.texture_names

            write_json_file(os.path.join(particles_folder, f"{jpa_name}.json"), out_particle_json)

        # Collect texture names and write texture BTIs
        print("Dump textures ...")
        for jpatex_name, jpatex in self.textures.items():
            out_json["textures"].append(jpatex_name)

            write_file(os.path.join(bti_folder, f"{jpatex_name}.bti"), jpatex.bti_data)

        # Write lists of particles and textures
        write_json_file(json_file, out_json)

        # Pack AutoEffectList entries
        out_effects_json = list()

        # Drop fields that contain default values
        def add_non_default(ine: dict, oute: dict, key: str, defval):
            val = ine[key]
            if val != defval:
                oute[key] = val

        def add_if_true(ine: dict, oute: dict, key: str, trueval: str):
            if ine[key] == trueval:
                oute[key] = True

        print("Dump effects ...")
        for effect in self.effects:
            effect_entry = dict()

            effect_entry["GroupName"] = effect["GroupName"]
            add_non_default(effect, effect_entry, "AnimName", "")
            add_if_true(effect, effect_entry, "ContinueAnimEnd", "on")
            effect_entry["UniqueName"] = effect["UniqueName"]

            # EffectName is a list of effect names
            effect_names = effect["EffectName"].split(" ")
            if len(effect_names) == 1 and effect_names[0] == "":
                effect_names = list()

            effect_entry["EffectName"] = effect_names

            add_non_default(effect, effect_entry, "ParentName", "")
            add_non_default(effect, effect_entry, "JointName", "")
            add_non_default(effect, effect_entry, "OffsetX", 0.0)
            add_non_default(effect, effect_entry, "OffsetY", 0.0)
            add_non_default(effect, effect_entry, "OffsetZ", 0.0)
            add_non_default(effect, effect_entry, "StartFrame", 0)
            add_non_default(effect, effect_entry, "EndFrame", -1)
            add_non_default(effect, effect_entry, "Affect", "")
            add_non_default(effect, effect_entry, "Follow", "")
            add_non_default(effect, effect_entry, "ScaleValue", 1.0)
            add_non_default(effect, effect_entry, "RateValue", 1.0)
            add_non_default(effect, effect_entry, "PrmColor", "")
            add_non_default(effect, effect_entry, "EnvColor", "")
            add_non_default(effect, effect_entry, "LightAffectValue", 0.0)
            add_non_default(effect, effect_entry, "DrawOrder", "")

            out_effects_json.append(effect_entry)

        # Write AutoEffectList entries
        write_json_file(effects_json_file, out_effects_json)

    def pack_bin(self, jpc_file: str, names_file: str, effects_file: str):
        particle_container = jpac210.JParticlesContainer()
        particle_container.textures = self.textures

        # Create folders if necessary
        os.makedirs(os.path.dirname(jpc_file), exist_ok=True)
        os.makedirs(os.path.dirname(names_file), exist_ok=True)
        os.makedirs(os.path.dirname(effects_file), exist_ok=True)

        # Pack particles and names
        particle_names = bcsv.Bcsv()
        particle_names.new_field("name", bcsv.FIELD_TYPE_STRING)
        particle_names.new_field("id", bcsv.FIELD_TYPE_S32)

        # Names have to be alphabetically sorted as the game performs binary search
        index = 0
        for particle_name in sorted(self.particles.keys()):
            particle_names.entries.append({"name": particle_name, "id": index})

            particle = self.particles[particle_name]
            particle_container.particles.append(particle)
            particle.index = index

            index += 1

        # Pack effects
        effects_data = bcsv.Bcsv()
        effects_data.new_field("No", bcsv.FIELD_TYPE_S32)
        effects_data.new_field("GroupName", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("AnimName", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("ContinueAnimEnd", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("UniqueName", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("EffectName", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("ParentName", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("JointName", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("OffsetX", bcsv.FIELD_TYPE_F32)
        effects_data.new_field("OffsetY", bcsv.FIELD_TYPE_F32)
        effects_data.new_field("OffsetZ", bcsv.FIELD_TYPE_F32)
        effects_data.new_field("StartFrame", bcsv.FIELD_TYPE_S32)
        effects_data.new_field("EndFrame", bcsv.FIELD_TYPE_S32)
        effects_data.new_field("Affect", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("Follow", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("ScaleValue", bcsv.FIELD_TYPE_F32)
        effects_data.new_field("RateValue", bcsv.FIELD_TYPE_F32)
        effects_data.new_field("PrmColor", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("EnvColor", bcsv.FIELD_TYPE_STRING)
        effects_data.new_field("LightAffectValue", bcsv.FIELD_TYPE_F32)
        effects_data.new_field("DrawOrder", bcsv.FIELD_TYPE_STRING)
        effects_data.entries = self.effects

        # Write all the files
        print("Write JPC file...")
        write_file(jpc_file, particle_container.pack())

        print("Write names BCSV...")
        write_file(names_file, particle_names.pack())

        print("Write effects BCSV...")
        write_file(effects_file, effects_data.pack("GroupName"))


def dump_particle_data(in_folder: str, out_folder: str):
    """
    Loads all data from Particles.jpc, ParticleNames.bcsv and AutoEffectList.bcsv and dumps the retrieved data to
    readable and editable JSON files. The particle textures will be stored as BTI images in a separate folder.
    The following files have to be supplied:
    - 'in_folder'/Particles.jpc
    - 'in_folder'/ParticleNames.bcsv
    - 'in_folder'/AutoEffectList.bcsv

    The output files and structure look like this:
    - 'out_folder'/Particles.json
    - 'out_folder'/Effects.json
    - 'out_folder'/Particles/<particle name>.json
    - 'out_folder'/Textures/<texture name>.bti

    Particles.json contains lists of particles and textures that belong to the particles container. If you want
    to add new particles and textures, make sure to add their names to the respective lists. Effects.json is a
    simplified version of AutoEffectList containing only the non-default values for every effect.
    """
    # Setup input file paths
    fp_particles = os.path.join(in_folder, "Particles.jpc")
    fp_particle_names = os.path.join(in_folder, "ParticleNames.bcsv")
    fp_effects = os.path.join(in_folder, "AutoEffectList.bcsv")

    # Setup output file paths
    fp_out_particles_json = os.path.join(out_folder, "Particles.json")
    fp_out_particles = os.path.join(out_folder, "Particles")
    fp_out_textures = os.path.join(out_folder, "Textures")
    fp_out_effects_json = os.path.join(out_folder, "Effects.json")

    # Unpack data from JPC and BCSV files
    pd = ParticleData()
    pd.unpack_bin(fp_particles, fp_particle_names, fp_effects)

    # Dump data to JSON and BTI files
    pd.pack_json(fp_out_particles_json, fp_out_particles, fp_out_textures, fp_out_effects_json)


def pack_particle_data(in_folder: str, out_folder: str):
    """
    Packs particle data using the information located in 'in_folder'. Please refer to above function's documentation
    if you want to see what each file's usage is.
    The following files and folders have to be supplied:
    - 'in_folder'/Particles.json
    - 'in_folder'/Effects.json
    - 'in_folder'/Particles/<particle name>.json
    - 'in_folder'/Textures/<texture name>.bti

    The output files look like this:
    - 'out_folder'/Particles.jpc
    - 'out_folder'/ParticleNames.bcsv
    - 'out_folder'/AutoEffectList.bcsv
    """
    # Setup input file paths
    fp_particles_json = os.path.join(in_folder, "Particles.json")
    fp_particles = os.path.join(in_folder, "Particles")
    fp_textures = os.path.join(in_folder, "Textures")
    fp_effects_json = os.path.join(in_folder, "Effects.json")

    # Setup output file paths
    fp_out_particles = os.path.join(out_folder, "Particles.jpc")
    fp_out_particle_names = os.path.join(out_folder, "ParticleNames.bcsv")
    fp_out_effects = os.path.join(out_folder, "AutoEffectList.bcsv")

    # Load data from JSON and BTI files
    pd = ParticleData()
    pd.unpack_json(fp_particles_json, fp_particles, fp_textures, fp_effects_json)

    # Pack data to JPC and BCSV files
    pd.pack_bin(fp_out_particles, fp_out_particle_names, fp_out_effects)


parser = argparse.ArgumentParser(description="pygapa")
parser.add_argument("mode", type=str)
parser.add_argument("in_dir", type=str)
parser.add_argument("out_dir", type=str)
args = parser.parse_args()

if args.mode == "dump":
    dump_particle_data(args.in_dir, args.out_dir)
elif args.mode == "pack":
    pack_particle_data(args.in_dir, args.out_dir)

import os

import formats.bcsv as bcsv
import formats.jpac210 as jpac210
from formats.helper import *

DRAW_ORDERS = [
    "(undefined)",
    "3D",
    "PAUSE_IGNORE",
    "INDIRECT",
    "AFTER_INDIRECT",
    "BLOOM_EFFECT",
    "AFTER_IMAGE_EFFECT",
    "2D",
    "2D_PAUSE_IGNORE",
    "FOR_2D_MODEL"
]

MATRIX_FLAGS = ["T", "R", "S"]


def fix_draw_order(val: str):
    if val not in DRAW_ORDERS:
        return DRAW_ORDERS[0]
    return val


class ParticleEffect:
    def __init__(self):
        self.index = -1
        self.group_name = ""
        self.anim_name = list()
        self.continue_anim_end = False
        self.unique_name = ""
        self.effect_name = list()
        self.parent_name = ""
        self.joint_name = ""
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.offset_z = 0.0
        self.start_frame = 0
        self.end_frame = -1
        self.affect = {"T": False, "R": False, "S": False}
        self.follow = {"T": False, "R": False, "S": False}
        self.scale_value = 1.0
        self.rate_value = 1.0
        self.prm_color = ""
        self.env_color = ""
        self.light_affect_value = 0.0
        self.draw_order = "3D"

    def unpack(self, entry: dict):
        def split_list(key: str):
            split = entry[key].split(" ")
            if len(split) == 1 and split[0] == "":
                return list()
            return split

        self.index = entry["No"]
        self.group_name = entry["GroupName"]
        self.anim_name = split_list("AnimName")
        self.continue_anim_end = entry["ContinueAnimEnd"] == "on"
        self.unique_name = entry["UniqueName"]
        self.effect_name = split_list("EffectName")
        self.parent_name = entry["ParentName"]
        self.joint_name = entry["JointName"]
        self.offset_x = entry["OffsetX"]
        self.offset_y = entry["OffsetY"]
        self.offset_z = entry["OffsetZ"]
        self.start_frame = entry["StartFrame"]
        self.end_frame = entry["EndFrame"]
        self.scale_value = entry["ScaleValue"]
        self.rate_value = entry["RateValue"]
        self.prm_color = entry["PrmColor"]
        self.env_color = entry["EnvColor"]
        self.light_affect_value = entry["LightAffectValue"]
        self.draw_order = fix_draw_order(entry["DrawOrder"])

        def get_TRS(key: str, data: dict):
            flags = entry[key].split("/")
            for flag in MATRIX_FLAGS:
                data[flag] = flag in flags

        get_TRS("Affect", self.affect)
        get_TRS("Follow", self.follow)

    def unpack_json(self, entry: dict):
        def get_or_def(key: str, defval):
            if key in entry:
                return entry[key]
            return defval

        self.index = -1
        self.group_name = get_or_def("GroupName", "")
        self.anim_name = get_or_def("AnimName", list())
        self.continue_anim_end = get_or_def("ContinueAnimEnd", False)
        self.unique_name = get_or_def("UniqueName", "")
        self.effect_name = get_or_def("EffectName", list())
        self.parent_name = get_or_def("ParentName", "")
        self.joint_name = get_or_def("JointName", "")
        self.offset_z = get_or_def("OffsetX", 0.0)
        self.offset_y = get_or_def("OffsetY", 0.0)
        self.offset_z = get_or_def("OffsetZ", 0.0)
        self.start_frame = get_or_def("StartFrame", 0)
        self.end_frame = get_or_def("EndFrame", -1)
        self.scale_value = get_or_def("ScaleValue", 1.0)
        self.rate_value = get_or_def("RateValue", 1.0)
        self.prm_color = get_or_def("PrmColor", "")
        self.env_color = get_or_def("EnvColor", "")
        self.light_affect_value = get_or_def("LightAffectValue", 0.0)
        self.draw_order = get_or_def("DrawOrder", "3D")
        self.draw_order = fix_draw_order(self.draw_order)

        def get_TRS(key: str, data: dict):
            flags = entry[key] if key in entry else list()
            for flag in MATRIX_FLAGS:
                data[flag] = flag in flags

        get_TRS("Affect", self.affect)
        get_TRS("Follow", self.follow)

    def pack(self) -> dict:
        entry = dict()
        entry["No"] = self.index
        entry["GroupName"] = self.group_name
        entry["AnimName"] = " ".join(self.anim_name)
        entry["ContinueAnimEnd"] = "on" if self.continue_anim_end else ""
        entry["UniqueName"] = self.unique_name
        entry["EffectName"] = " ".join(self.effect_name)
        entry["ParentName"] = self.parent_name
        entry["JointName"] = self.joint_name
        entry["OffsetX"] = self.offset_x
        entry["OffsetY"] = self.offset_y
        entry["OffsetZ"] = self.offset_z
        entry["StartFrame"] = self.start_frame
        entry["EndFrame"] = self.end_frame
        entry["ScaleValue"] = self.scale_value
        entry["RateValue"] = self.rate_value
        entry["PrmColor"] = self.prm_color
        entry["EnvColor"] = self.env_color
        entry["LightAffectValue"] = self.light_affect_value
        entry["DrawOrder"] = "" if self.draw_order == "(undefined)" else self.draw_order

        def set_TRS(data: dict, key: str):
            flags = list()
            for flag in MATRIX_FLAGS:
                if data[flag]:
                    flags.append(flag)
            entry[key] = "/".join(flags)

        set_TRS(self.affect, "Affect")
        set_TRS(self.follow, "Follow")

        return entry

    def pack_json(self) -> dict:
        entry = dict()

        def put_non_def(key: str, val, defval):
            if val is not defval:
                entry[key] = val

        def put_non_empty(key: str, val):
            if len(val) > 0:
                entry[key] = val

        put_non_def("GroupName", self.group_name, "")
        put_non_empty("AnimName", self.anim_name)
        put_non_def("ContinueAnimEnd", self.continue_anim_end, False)
        put_non_def("UniqueName", self.unique_name, "")
        put_non_empty("EffectName", self.effect_name)
        put_non_def("ParentName", self.parent_name, "")
        put_non_def("JointName", self.joint_name, "")
        put_non_def("OffsetX", self.offset_x, 0.0)
        put_non_def("OffsetY", self.offset_y, 0.0)
        put_non_def("OffsetZ", self.offset_z, 0.0)
        put_non_def("StartFrame", self.start_frame, 0)
        put_non_def("EndFrame", self.end_frame, -1)
        put_non_def("ScaleValue", self.scale_value, 1.0)
        put_non_def("RateValue", self.rate_value, 1.0)
        put_non_def("PrmColor", self.prm_color, "")
        put_non_def("EnvColor", self.env_color, "")
        put_non_def("LightAffectValue", self.light_affect_value, 0.0)
        put_non_def("DrawOrder", self.draw_order, "(undefined)")

        def put_TRS(data: dict, key: str):
            flags = list()
            for flag in MATRIX_FLAGS:
                if data[flag]:
                    flags.append(flag)
            if len(flags) > 0:
                entry[key] = flags

        put_TRS(self.affect, "Affect")
        put_TRS(self.follow, "Follow")

        return entry

    def description(self):
        first = self.group_name if self.group_name != "" else "(undefined)"
        second = self.unique_name if self.unique_name != "" else "(undefined)"
        return f"{first}::{second}"


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

        index = 0
        for effect_entry in in_effects_json:
            effect = ParticleEffect()
            effect.unpack_json(effect_entry)
            effect.index = index

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
        self.effects.clear()

        for effect_entry in auto_effects.entries:
            effect = ParticleEffect()
            effect.unpack(effect_entry)

            self.effects.append(effect)

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
        print("Dump effects ...")
        out_effects_json = [effect.pack_json() for effect in self.effects]

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

        effects_data.entries = [effect.pack() for effect in self.effects]

        # Write all the files
        print("Write JPC file...")
        write_file(jpc_file, particle_container.pack())

        print("Write names BCSV...")
        write_file(names_file, particle_names.pack())

        print("Write effects BCSV...")
        write_file(effects_file, effects_data.pack("GroupName"))

import os

import formats.bcsv as bcsv
import formats.jpac210 as jpac210
from formats import rarc
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
        self.index = -1  # This will be calculated when saving
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

    def replace_with(self, other):
        self.anim_name.clear()
        self.effect_name.clear()

        self.group_name = other.group_name
        self.anim_name += other.anim_name
        self.continue_anim_end = other.continue_anim_end
        self.unique_name = other.unique_name
        self.effect_name += other.effect_name
        self.parent_name = other.parent_name
        self.joint_name = other.joint_name
        self.offset_x = other.offset_x
        self.offset_y = other.offset_y
        self.offset_z = other.offset_z
        self.start_frame = other.start_frame
        self.end_frame = other.end_frame
        self.scale_value = other.scale_value
        self.rate_value = other.rate_value
        self.prm_color = other.prm_color
        self.env_color = other.env_color
        self.light_affect_value = other.light_affect_value
        self.draw_order = other.draw_order

        def copy_TRS(src: dict, dest: dict):
            for flag in MATRIX_FLAGS:
                dest[flag] = src[flag]

        copy_TRS(other.affect, self.affect)
        copy_TRS(other.follow, self.follow)

    def description(self):
        first = self.group_name if self.group_name != "" else "(undefined)"
        second = self.unique_name if self.unique_name != "" else "(undefined)"
        return f"{first}::{second}"


class ParticleData:
    def __init__(self):
        self.textures = dict()
        self.particles = list()
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
            particle.name = particle_name
            in_particle_json = read_json_file(os.path.join(particles_folder, f"{particle_name}.json"))
            particle.unpack_json(in_particle_json)

            for texture_name in particle.texture_names:
                if texture_name in unused_texture_names:
                    unused_texture_names.remove(texture_name)

            self.particles.append(particle)

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

    def __unpack_bin_files(self, jpc_data, names_data, effects_data):
        # Load JPAResource and JPATexture entries
        print("Load JPC file ...")
        particle_container = jpac210.JParticlesContainer()
        particle_container.unpack(jpc_data)
        self.textures = particle_container.textures
        self.particles.clear()

        # Load ParticleNames entries
        print("Load names BCSV ...")
        particle_names = bcsv.Bcsv()
        particle_names.unpack(names_data)
        particle_names = particle_names.entries

        # Load AutoEffectList entries
        print("Load effects BCSV ...")
        auto_effects = bcsv.Bcsv()
        auto_effects.unpack(effects_data)
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

            particle = particle_container.particles[particle_index]
            particle.name = particle_name

            self.particles.append(particle)

    def unpack_bin(self, jpc_file: str, names_file: str, effects_file: str):
        jpc_data = read_file(jpc_file)
        names_data = read_file(names_file)
        effects_data = read_file(effects_file)
        self.__unpack_bin_files(jpc_data, names_data, effects_data)

    def unpack_rarc(self, rarc_file: str):
        effect_arc = rarc.JKRArchive()
        effect_arc.unpack(read_file(rarc_file))

        jpc_data = effect_arc.find_file("Effect/Particles.jpc").get_data()
        names_data = effect_arc.find_file("Effect/ParticleNames.bcsv").get_data()
        effects_data = effect_arc.find_file("Effect/AutoEffectList.bcsv").get_data()
        self.__unpack_bin_files(jpc_data, names_data, effects_data)

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
        for jpa in self.particles:
            out_json["particles"].append(jpa.name)
            write_json_file(os.path.join(particles_folder, f"{jpa.name}.json"), jpa.pack_json())

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
        for particle in sorted(self.particles, key=lambda x: x.name):
            particle_names.entries.append({"name": particle.name, "id": index})

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

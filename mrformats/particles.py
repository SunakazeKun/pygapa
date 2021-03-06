import jsystem
import os
import pyaurum

__all__ = [
    # Classes
    "ParticleEffect",
    "ParticleData",
    # Functions
    "fix_draw_order",
    # Data
    "PARTICLE_DRAW_ORDERS",
    "PARTICLE_MATRIX_FLAGS"
]

PARTICLE_DRAW_ORDERS = ["(undefined)", "3D", "PAUSE_IGNORE", "INDIRECT", "AFTER_INDIRECT", "BLOOM_EFFECT",
                        "AFTER_IMAGE_EFFECT", "2D", "2D_PAUSE_IGNORE", "FOR_2D_MODEL", "WORLD_MAP_MINI_ICON"]
PARTICLE_MATRIX_FLAGS = ["T", "R", "S"]


def fix_draw_order(val: str):
    if val not in PARTICLE_DRAW_ORDERS:
        return PARTICLE_DRAW_ORDERS[0]
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
            for flag in PARTICLE_MATRIX_FLAGS:
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
        self.offset_x = get_or_def("OffsetX", 0.0)
        self.offset_y = get_or_def("OffsetY", 0.0)
        self.offset_z = get_or_def("OffsetZ", 0.0)
        self.start_frame = get_or_def("StartFrame", 0)
        self.end_frame = get_or_def("EndFrame", -1)
        self.scale_value = get_or_def("ScaleValue", 1.0)
        self.rate_value = get_or_def("RateValue", 1.0)
        self.prm_color = get_or_def("PrmColor", "")
        self.env_color = get_or_def("EnvColor", "")
        self.light_affect_value = get_or_def("LightAffectValue", 0.0)
        self.draw_order = fix_draw_order(get_or_def("DrawOrder", "3D"))

        def get_TRS(key: str, data: dict):
            flags = entry[key] if key in entry else list()
            for flag in PARTICLE_MATRIX_FLAGS:
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
            for flag in PARTICLE_MATRIX_FLAGS:
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
            for flag in PARTICLE_MATRIX_FLAGS:
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
            for flag in PARTICLE_MATRIX_FLAGS:
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

        in_json = pyaurum.read_json_file(json_file)
        in_effects_json = pyaurum.read_json_file(effects_json_file)

        unused_texture_names = list()

        print("Loading texture files...")
        for texture_name in in_json["textures"]:
            texture = jsystem.JPATexture()
            texture.file_name = texture_name
            texture.bti_data = pyaurum.read_bin_file(os.path.join(bti_folder, f"{texture_name}.bti"))

            self.textures[texture_name] = texture
            unused_texture_names.append(texture_name)

        print("Loading particle files...")
        for particle_name in in_json["particles"]:
            particle = jsystem.JPAResource()
            particle.name = particle_name
            in_particle_json = pyaurum.read_json_file(os.path.join(particles_folder, f"{particle_name}.json"))
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
        particle_container = jsystem.JParticlesContainer()
        particle_container.unpack(jpc_data)
        self.textures = particle_container.textures
        self.particles.clear()

        # Load ParticleNames entries
        print("Load names BCSV ...")
        particle_names = jsystem.JMapInfo()
        particle_names.unpack(names_data)
        particle_names = particle_names.entries

        # Load AutoEffectList entries
        print("Load effects BCSV ...")
        auto_effects = jsystem.JMapInfo()
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
        jpc_data = pyaurum.read_bin_file(jpc_file)
        names_data = pyaurum.read_bin_file(names_file)
        effects_data = pyaurum.read_bin_file(effects_file)
        self.__unpack_bin_files(jpc_data, names_data, effects_data)

    def unpack_rarc(self, archive: jsystem.JKRArchive):
        jpc_data = archive.find_file("/Particles.jpc").data
        names_data = archive.find_file("/ParticleNames.bcsv").data
        effects_data = archive.find_file("/AutoEffectList.bcsv").data
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
            pyaurum.write_json_file(os.path.join(particles_folder, f"{jpa.name}.json"), jpa.pack_json())

        # Collect texture names and write texture BTIs
        print("Dump textures ...")
        for jpatex_name, jpatex in self.textures.items():
            out_json["textures"].append(jpatex_name)

            pyaurum.write_file(os.path.join(bti_folder, f"{jpatex_name}.bti"), jpatex.bti_data)

        # Write lists of particles and textures
        pyaurum.write_json_file(json_file, out_json)

        # Pack AutoEffectList entries
        print("Dump effects ...")
        out_effects_json = [effect.pack_json() for effect in self.effects]

        # Write AutoEffectList entries
        pyaurum.write_json_file(effects_json_file, out_effects_json)

    def __pack_bin(self):
        particle_container = jsystem.JParticlesContainer()
        particle_container.textures = self.textures

        # Pack particles and names
        particle_names = jsystem.JMapInfo()
        particle_names.new_field("name", jsystem.JMapFieldType.STRING_OFFSET)
        particle_names.new_field("id", jsystem.JMapFieldType.LONG)

        # Names have to be alphabetically sorted as the game performs binary search
        index = 0
        for particle in sorted(self.particles, key=lambda x: x.name):
            particle_names.entries.append({"name": particle.name, "id": index})

            particle_container.particles.append(particle)
            particle.index = index

            index += 1

        # Pack effects
        effects_data = jsystem.JMapInfo()
        effects_data.new_field("No", jsystem.JMapFieldType.LONG)
        effects_data.new_field("GroupName", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("AnimName", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("ContinueAnimEnd", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("UniqueName", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("EffectName", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("ParentName", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("JointName", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("OffsetX", jsystem.JMapFieldType.FLOAT)
        effects_data.new_field("OffsetY", jsystem.JMapFieldType.FLOAT)
        effects_data.new_field("OffsetZ", jsystem.JMapFieldType.FLOAT)
        effects_data.new_field("StartFrame", jsystem.JMapFieldType.LONG)
        effects_data.new_field("EndFrame", jsystem.JMapFieldType.LONG)
        effects_data.new_field("Affect", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("Follow", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("ScaleValue", jsystem.JMapFieldType.FLOAT)
        effects_data.new_field("RateValue", jsystem.JMapFieldType.FLOAT)
        effects_data.new_field("PrmColor", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("EnvColor", jsystem.JMapFieldType.STRING_OFFSET)
        effects_data.new_field("LightAffectValue", jsystem.JMapFieldType.FLOAT)
        effects_data.new_field("DrawOrder", jsystem.JMapFieldType.STRING_OFFSET)

        effects_data.entries.clear()

        for i, effect in enumerate(self.effects):
            effect.index = i
            effects_data.entries.append(effect.pack())

        # Pack all data
        print("Pack JPC data...")
        self.__tmp_packed_particle_container = particle_container.pack()

        print("Pack names BCSV...")
        self.__tmp_packed_particle_names = particle_names.pack()

        print("Write effects BCSV...")
        self.__tmp_packed_effects_data = effects_data.pack("GroupName")

    def pack_bin(self, jpc_file: str, names_file: str, effects_file: str):
        self.__pack_bin()

        # Write all the files
        pyaurum.write_file(jpc_file, self.__tmp_packed_particle_container)
        pyaurum.write_file(names_file, self.__tmp_packed_particle_names)
        pyaurum.write_file(effects_file, self.__tmp_packed_effects_data)

        # Release buffered data
        del self.__tmp_packed_particle_container
        del self.__tmp_packed_particle_names
        del self.__tmp_packed_effects_data

    def pack_rarc(self, archive: jsystem.JKRArchive):
        self.__pack_bin()

        # Get files from RARC folder if existent
        particle_container_file = archive.find_file("/Particles.jpc")
        particle_names_file = archive.find_file("/ParticleNames.bcsv")
        effects_data_file = archive.find_file("/AutoEffectList.bcsv")

        # Try to create non-existent files if necessary
        if particle_container_file is None:
            particle_container_file = archive.create_file(archive.get_root(), "/Particles.jpc")
        if particle_names_file is None:
            particle_names_file = archive.create_file(archive.get_root(), "/ParticleNames.bcsv")
        if effects_data_file is None:
            effects_data_file = archive.create_file(archive.get_root(), "/AutoEffectList.bcsv")

        # Set file data
        particle_container_file.data = self.__tmp_packed_particle_container
        particle_names_file.data = self.__tmp_packed_particle_names
        effects_data_file.data = self.__tmp_packed_effects_data

        # Release buffered data
        del self.__tmp_packed_particle_container
        del self.__tmp_packed_particle_names
        del self.__tmp_packed_effects_data

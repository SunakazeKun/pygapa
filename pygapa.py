import argparse
import os
import sys
from copy import deepcopy

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt5 import uic, QtGui, QtCore

from formats.helper import *
import formats.particle_data as particle_data


# General application info
APP_NAME = "pygapa"
APP_VERSION = "v0.2"
APP_CREATOR = "Aurum"
APP_TITLE = f"{APP_NAME} {APP_VERSION} -- by {APP_CREATOR}"

# Setup QT application
PROGRAM = QApplication([])
ICON = QtGui.QIcon()
ICON.addFile("ui/icon.png", QtCore.QSize(32, 32))
PROGRAM.setWindowIcon(ICON)


class PygapaEditor(QMainWindow):
    EDITOR_MODE_EFFECT = 0
    EDITOR_MODE_PARTICLE = 1
    EDITOR_MODE_TEXTURE = 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi("ui/main.ui", self)
        self.setWindowTitle(APP_TITLE)

        # Particle data holders
        self.particle_data = particle_data.ParticleData()
        self.particle_data_folder = None
        self.current_effect = None
        self.copied_effect = None

        # File menu actions
        self.actionExit.triggered.connect(lambda: PROGRAM.exit())
        self.actionOpen.triggered.connect(self.open_particle_data)
        self.actionSave.triggered.connect(self.save_particle_data)
        self.actionSaveAs.triggered.connect(self.save_as_particle_data)

        # Register effect editing actions
        self.listEffects.itemSelectionChanged.connect(self.select_effect)

        self.actionToolAdd.triggered.connect(self.add_effect)
        self.actionToolDelete.triggered.connect(self.delete_effects)
        self.actionToolClone.triggered.connect(self.clone_effects)
        self.actionToolCopy.triggered.connect(self.copy_effect)
        self.actionToolReplace.triggered.connect(self.replace_effect)
        self.actionToolExport.triggered.connect(self.export_effects)
        self.actionToolImport.triggered.connect(self.import_effects)

        self.textEffectGroupName.textEdited.connect(self.set_effect_group_name)
        self.textEffectUniqueName.textEdited.connect(self.set_effect_unique_name)
        self.textEffectParentName.textEdited.connect(self.set_effect_parent_name)
        self.textEffectEffectName.textChanged.connect(self.set_effect_effect_name)
        self.textEffectJointName.textEdited.connect(self.set_effect_joint_name)
        self.textEffectAnimName.textChanged.connect(self.set_effect_anim_name)
        self.checkEffectContinueAnimEnd.stateChanged.connect(lambda s: self.set_effect_continue_anim_end(s == 2))
        self.spinnerEffectStartFrame.valueChanged.connect(self.set_effect_start_frame)
        self.spinnerEffectEndFrame.valueChanged.connect(self.set_effect_end_frame)
        self.spinnerEffectOffsetX.valueChanged.connect(self.set_effect_offset_x)
        self.spinnerEffectOffsetY.valueChanged.connect(self.set_effect_offset_y)
        self.spinnerEffectOffsetZ.valueChanged.connect(self.set_effect_offset_z)
        self.checkEffectAffectT.stateChanged.connect(lambda s: self.set_effect_affect_flag(s == 2, "T"))
        self.checkEffectAffectR.stateChanged.connect(lambda s: self.set_effect_affect_flag(s == 2, "R"))
        self.checkEffectAffectS.stateChanged.connect(lambda s: self.set_effect_affect_flag(s == 2, "S"))
        self.checkEffectFollowT.stateChanged.connect(lambda s: self.set_effect_follow_flag(s == 2, "T"))
        self.checkEffectFollowR.stateChanged.connect(lambda s: self.set_effect_follow_flag(s == 2, "R"))
        self.checkEffectFollowS.stateChanged.connect(lambda s: self.set_effect_follow_flag(s == 2, "S"))
        self.spinnerEffectScaleValue.valueChanged.connect(self.set_effect_scale_value)
        self.spinnerEffectRateValue.valueChanged.connect(self.set_effect_rate_value)
        self.spinnerEffectLightAffectValue.valueChanged.connect(self.set_effect_light_affect_value)
        self.textEffectPrmColor.textEdited.connect(self.set_effect_prm_color)
        self.textEffectEnvColor.textEdited.connect(self.set_effect_env_color)
        self.comboEffectDrawOrder.currentIndexChanged.connect(self.set_effect_draw_order)

        # Register particle editing actions
        # nothing here yet lol

        # Register effect editing actions
        self.actionToolExport.triggered.connect(self.export_textures)

        # Finalize UI and show it to user
        self.enable_all_components(False)
        self.show()

    @staticmethod
    def text_block_to_list(text):
        return text.replace(" ", "").replace("\r", "").split("\n")

    # ---------------------------------------------------------------------------------------------
    # Particle data I/O
    # ---------------------------------------------------------------------------------------------
    def open_particle_data(self):
        particle_folder_name = QFileDialog.getExistingDirectory(self, "Select particle data folder")

        if len(particle_folder_name) == 0:
            return

        self.reset_editor()
        self.particle_data_folder = particle_folder_name

        # Get input file paths
        fp_particles = os.path.join(self.particle_data_folder, "Particles.jpc")
        fp_particle_names = os.path.join(self.particle_data_folder, "ParticleNames.bcsv")
        fp_effects = os.path.join(self.particle_data_folder, "AutoEffectList.bcsv")

        # Try to unpack particle data
        try:
            self.particle_data.unpack_bin(fp_particles, fp_particle_names, fp_effects)
        except Exception:  # Will be handled better in the future, smh
            self.status("An error occured while loading particle data.", True)
            return

        # Populate data
        for effect in self.particle_data.effects:
            self.listEffects.addItem(effect.description())

        for particle in self.particle_data.particles.keys():
            self.listParticles.addItem(particle)

        for texture in self.particle_data.textures.keys():
            self.listTextures.addItem(texture)

        self.enable_all_components(True)
        self.widgetEffects.setEnabled(False)

        self.status(f"Successfully loaded particle data from \"{self.particle_data_folder}\"")

    def save_particle_data(self):
        if self.particle_data_folder is None:
            particle_folder_name = QFileDialog.getExistingDirectory(self, "Select particle data folder")
            if len(particle_folder_name) == 0:
                return

            self.particle_data_folder = particle_folder_name
        self.save_particle_data_to_folder()

    def save_as_particle_data(self):
        particle_folder_name = QFileDialog.getExistingDirectory(self, "Select particle data folder")
        if len(particle_folder_name) == 0:
            return

        self.particle_data_folder = particle_folder_name
        self.save_particle_data_to_folder()

    def save_particle_data_to_folder(self):
        # Get output file paths
        fp_out_particles = os.path.join(self.particle_data_folder, "Particles.jpc")
        fp_out_particle_names = os.path.join(self.particle_data_folder, "ParticleNames.bcsv")
        fp_out_effects = os.path.join(self.particle_data_folder, "AutoEffectList.bcsv")

        # Output packed data to JPC and BCSV files
        self.particle_data.pack_bin(fp_out_particles, fp_out_particle_names, fp_out_effects)

        self.status(f"Saved particle data to \"{self.particle_data_folder}\"")

    # ---------------------------------------------------------------------------------------------
    # General UI helpers
    # ---------------------------------------------------------------------------------------------
    def status(self, text: str, fail: bool = False, duration: int = 5000):
        color = "red" if fail else "green"
        self.statusBar.setStyleSheet(f"QStatusBar{{padding:8px;color:{color};}}")
        self.statusBar.showMessage(text, duration)

    def get_editor_mode(self):
        return self.tabContents.currentIndex()

    def enable_all_components(self, state: bool):
        self.toolBar.setEnabled(state)
        self.tabEffects.setEnabled(state)
        self.tabParticles.setEnabled(state)
        self.tabTextures.setEnabled(state)

    def reset_editor(self):
        self.listEffects.clear()
        self.listParticles.clear()
        self.listTextures.clear()
        self.enable_all_components(False)

    # ---------------------------------------------------------------------------------------------
    # Effect editing
    # ---------------------------------------------------------------------------------------------
    def select_effect(self):
        # Make sure only one effect is selected
        if len(self.listEffects.selectedItems()) != 1:
            self.widgetEffects.setEnabled(False)
            self.current_effect = None
            return

        # Enable all effect editing components and get currently selected effect instance
        self.widgetEffects.setEnabled(True)
        self.current_effect = self.particle_data.effects[self.listEffects.currentRow()]

        # Block signals temporarily to prevent invoking textChanged
        self.textEffectAnimName.blockSignals(True)
        self.textEffectEffectName.blockSignals(True)

        # Populate effect data for currently selected item
        self.textEffectGroupName.setText(self.current_effect.group_name)
        self.textEffectAnimName.setPlainText("\n".join(self.current_effect.anim_name))
        self.checkEffectContinueAnimEnd.setChecked(self.current_effect.continue_anim_end)
        self.textEffectUniqueName.setText(self.current_effect.unique_name)
        self.textEffectEffectName.setPlainText("\n".join(self.current_effect.effect_name))
        self.textEffectParentName.setText(self.current_effect.parent_name)
        self.textEffectJointName.setText(self.current_effect.joint_name)
        self.spinnerEffectOffsetX.setValue(self.current_effect.offset_x)
        self.spinnerEffectOffsetY.setValue(self.current_effect.offset_y)
        self.spinnerEffectOffsetZ.setValue(self.current_effect.offset_z)
        self.spinnerEffectStartFrame.setValue(self.current_effect.start_frame)
        self.spinnerEffectEndFrame.setValue(self.current_effect.end_frame)
        self.checkEffectAffectT.setChecked(self.current_effect.affect["T"])
        self.checkEffectAffectR.setChecked(self.current_effect.affect["R"])
        self.checkEffectAffectS.setChecked(self.current_effect.affect["S"])
        self.checkEffectFollowT.setChecked(self.current_effect.follow["T"])
        self.checkEffectFollowR.setChecked(self.current_effect.follow["R"])
        self.checkEffectFollowS.setChecked(self.current_effect.follow["S"])
        self.spinnerEffectScaleValue.setValue(self.current_effect.scale_value)
        self.spinnerEffectRateValue.setValue(self.current_effect.rate_value)
        self.spinnerEffectLightAffectValue.setValue(self.current_effect.light_affect_value)
        self.textEffectPrmColor.setText(self.current_effect.prm_color)
        self.textEffectEnvColor.setText(self.current_effect.env_color)
        self.comboEffectDrawOrder.setCurrentIndex(particle_data.DRAW_ORDERS.index(self.current_effect.draw_order))

        # Release blocked signals
        self.textEffectAnimName.blockSignals(False)
        self.textEffectEffectName.blockSignals(False)

    def add_effect(self):
        if self.get_editor_mode() != self.EDITOR_MODE_EFFECT:
            return

        # Create new effect
        effect = particle_data.ParticleEffect()
        self.particle_data.effects.append(effect)

        # Update effects list
        new_index = self.listEffects.count()
        self.listEffects.addItem(effect.description())
        self.listEffects.clearSelection()
        self.listEffects.setCurrentRow(new_index)

        self.status("Added new effect entry.")

    def delete_effects(self):
        if self.get_editor_mode() != self.EDITOR_MODE_EFFECT:
            return

        # Get selected list indexes
        delete_indexes = [i.row() for i in self.listEffects.selectionModel().selectedIndexes()]

        # The selected indexes are shuffled, so we remove entries starting from the end of the list
        delete_indexes.sort(reverse=True)

        # Go through indexes and delete list item and the actual effect entry
        for delete_index in delete_indexes:
            self.listEffects.takeItem(delete_index)
            self.particle_data.effects.pop(delete_index)

        self.status(f"Deleted {len(delete_indexes)} effect(s).")

    def clone_effects(self):
        if self.get_editor_mode() != self.EDITOR_MODE_EFFECT:
            return

        # Get selected list indexes
        clone_indexes = [i.row() for i in self.listEffects.selectionModel().selectedIndexes()]

        # The selected indexes are shuffled, but we want to retain the original order of the clones
        clone_indexes.sort()

        # Make sure the first clone is selected afterwards
        new_index = self.listEffects.count()

        # Create deep clones of all effects and populate them to the respective lists
        for clone_index in clone_indexes:
            clone = deepcopy(self.particle_data.effects[clone_index])
            self.particle_data.effects.append(clone)
            self.listEffects.addItem(clone.description())

        # Update list selection
        self.listEffects.clearSelection()
        self.listEffects.setCurrentRow(new_index)

        self.status(f"Cloned {len(clone_indexes)} effect(s).")

    def copy_effect(self):
        if self.get_editor_mode() != self.EDITOR_MODE_EFFECT:
            return
        if self.current_effect is None:
            self.status("No effect selected!", True)
            return

        self.copied_effect = deepcopy(self.particle_data.effects[self.listEffects.currentRow()])

        self.status(f"Copied effect {self.copied_effect.description()}")

    def replace_effect(self):
        if self.get_editor_mode() != self.EDITOR_MODE_EFFECT:
            return
        if self.current_effect is None:
            self.status("No effect selected!", True)
            return
        if self.copied_effect is None:
            self.status("No effect copy available!", True)
            return

        # Copy into current effect, we want to retain references to the effect entry
        old_description = self.current_effect.description()

        self.current_effect.anim_name.clear()
        self.current_effect.effect_name.clear()

        self.current_effect.group_name = self.copied_effect.group_name
        self.current_effect.anim_name += self.copied_effect.anim_name
        self.current_effect.continue_anim_end = self.copied_effect.continue_anim_end
        self.current_effect.unique_name = self.copied_effect.unique_name
        self.current_effect.effect_name += self.copied_effect.effect_name
        self.current_effect.parent_name = self.copied_effect.parent_name
        self.current_effect.joint_name = self.copied_effect.joint_name
        self.current_effect.offset_x = self.copied_effect.offset_x
        self.current_effect.offset_y = self.copied_effect.offset_y
        self.current_effect.offset_z = self.copied_effect.offset_z
        self.current_effect.start_frame = self.copied_effect.start_frame
        self.current_effect.end_frame = self.copied_effect.end_frame
        self.current_effect.scale_value = self.copied_effect.scale_value
        self.current_effect.rate_value = self.copied_effect.rate_value
        self.current_effect.prm_color = self.copied_effect.prm_color
        self.current_effect.env_color = self.copied_effect.env_color
        self.current_effect.light_affect_value = self.copied_effect.light_affect_value
        self.current_effect.draw_order = self.copied_effect.draw_order

        def copy_TRS(src: dict, dest: dict):
            for flag in particle_data.MATRIX_FLAGS:
                dest[flag] = src[flag]

        copy_TRS(self.copied_effect.affect, self.current_effect.affect)
        copy_TRS(self.copied_effect.follow, self.current_effect.follow)

        # Update widgets and list
        self.select_effect()
        self.update_current_effect_description()

        self.status(f"Replaced effect {old_description} with {self.copied_effect.description()}")

    def export_effects(self):
        if self.get_editor_mode() != self.EDITOR_MODE_EFFECT:
            return
        if len(self.listEffects.selectedItems()) == 0:
            self.status("No effect(s) selected!", True)
            return

        # Get file to export data to
        export_file = QFileDialog.getSaveFileName(self, "Export to JSON file...", filter="JSON file (*.json)")[0]

        if len(export_file) == 0:
            return

        # Get selected list indexes
        export_indexes = [i.row() for i in self.listEffects.selectionModel().selectedIndexes()]
        export_indexes.sort()

        # Get effects to be exported as a list of JSON objects
        exported_effects = list()

        for export_index in export_indexes:
            exported_effects.append(self.particle_data.effects[export_index].pack_json())

        # Write JSON file
        write_json_file(export_file, exported_effects)

        self.status(f"Exported {len(export_indexes)} effect(s) to \"{export_file}\".")

    def import_effects(self):
        if self.get_editor_mode() != self.EDITOR_MODE_EFFECT:
            return

        import_file = QFileDialog.getOpenFileName(self, "Import from JSON file...", filter="JSON file (*.json)")[0]

        if len(import_file) == 0:
            return

        try:
            imported_effects = read_json_file(import_file)
        except Exception:
            self.status(f"An error occured when importing from \"{import_file}\"", True)
            return

        # Select the first imported entry
        new_index = self.listEffects.count()

        # Convert JSON entries to effects and add them to the respective lists
        for effect_entry in imported_effects:
            effect = particle_data.ParticleEffect()
            effect.unpack_json(effect_entry)

            self.particle_data.effects.append(effect)
            self.listEffects.addItem(effect.description())

        # Update effects list
        self.listEffects.clearSelection()
        self.listEffects.setCurrentRow(new_index)

        self.status(f"Imported {len(imported_effects)} effect(s) from \"{import_file}\"")

    def update_current_effect_description(self):
        self.listEffects.selectedItems()[0].setText(self.current_effect.description())

    def set_effect_group_name(self, text: str):
        self.current_effect.group_name = text
        self.update_current_effect_description()

    def set_effect_unique_name(self, text: str):
        self.current_effect.unique_name = text
        self.update_current_effect_description()

    def set_effect_effect_name(self):
        self.current_effect.effect_name = self.text_block_to_list(self.textEffectEffectName.toPlainText())

    def set_effect_parent_name(self, text: str):
        self.current_effect.parent_name = text

    def set_effect_joint_name(self, text: str):
        self.current_effect.joint_name = text

    def set_effect_anim_name(self):
        self.current_effect.anim_name = self.text_block_to_list(self.textEffectAnimName.toPlainText())

    def set_effect_continue_anim_end(self, checked: bool):
        self.current_effect.continue_anim_end = checked

    def set_effect_start_frame(self, val: int):
        self.current_effect.start_frame = val

    def set_effect_end_frame(self, val: int):
        self.current_effect.end_frame = val

    def set_effect_offset_x(self, val: float):
        self.current_effect.offset_x = round(val, 7)

    def set_effect_offset_y(self, val: float):
        self.current_effect.offset_y = round(val, 7)

    def set_effect_offset_z(self, val: float):
        self.current_effect.offset_z = round(val, 7)

    def set_effect_affect_flag(self, checked: bool, flag: str):
        self.current_effect.affect[flag] = checked

    def set_effect_follow_flag(self, checked: bool, flag: str):
        self.current_effect.follow[flag] = checked

    def set_effect_scale_value(self, val: float):
        self.current_effect.scale_value = round(val, 7)

    def set_effect_rate_value(self, val: float):
        self.current_effect.rate_value = round(val, 7)

    def set_effect_light_affect_value(self, val: float):
        self.current_effect.light_affect_value = round(val, 7)

    def set_effect_prm_color(self, text: str):
        self.current_effect.prm_color = text

    def set_effect_env_color(self, text: str):
        self.current_effect.env_color = text

    def set_effect_draw_order(self, index: int):
        self.current_effect.draw_order = particle_data.DRAW_ORDERS[index]

    # ---------------------------------------------------------------------------------------------
    # Particle editing
    # ---------------------------------------------------------------------------------------------
    # ~Placeholder section~

    # ---------------------------------------------------------------------------------------------
    # Texture editing
    # ---------------------------------------------------------------------------------------------
    def export_textures(self):
        if self.get_editor_mode() != self.EDITOR_MODE_TEXTURE:
            return
        if len(self.listTextures.selectedItems()) == 0:
            self.status("No texture(s) selected!", True)
            return

        export_folder = QFileDialog.getExistingDirectory(self, "Export textures to...")
        if len(export_folder) == 0:
            return

        texture_names = [t.text() for t in self.listTextures.selectedItems()]

        for texture_name in texture_names:
            fp_out_texture = os.path.join(export_folder, f"{texture_name}.bti")
            write_file(fp_out_texture, self.particle_data.textures[texture_name].bti_data)

        self.status(f"Exported {len(texture_names)} effect(s) to \"{export_folder}\".")


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
    pd = particle_data.ParticleData()
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
    pd = particle_data.ParticleData()
    pd.unpack_json(fp_particles_json, fp_particles, fp_textures, fp_effects_json)

    # Pack data to JPC and BCSV files
    pd.pack_bin(fp_out_particles, fp_out_particle_names, fp_out_effects)


if __name__ == "__main__":
    # Batch mode
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="pygapa")
        parser.add_argument("mode", type=str)
        parser.add_argument("in_dir", type=str)
        parser.add_argument("out_dir", type=str)
        args = parser.parse_args()

        if args.mode == "dump":
            dump_particle_data(args.in_dir, args.out_dir)
        elif args.mode == "pack":
            pack_particle_data(args.in_dir, args.out_dir)
    # Editor mode
    else:
        main_window = PygapaEditor()
        sys.exit(PROGRAM.exec_())

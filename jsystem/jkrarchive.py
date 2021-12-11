import enum
import pyaurum
import struct

from jsystem import jkrcomp

__all__ = [
    # Classes
    "JKRFileAttr",
    "JKRPreloadType",
    "JKRFolderNode",
    "JKRDirectory",
    "JKRArchive",

    # Errors
    "JKRArchiveException"
]


# ----------------------------------------------------------------------------------------------------------------------
# Exceptions thrown by JKRArchive
# ----------------------------------------------------------------------------------------------------------------------
class JKRArchiveException(Exception):
    pass


# ----------------------------------------------------------------------------------------------------------------------
# File attribute flags/masks and preload types
# ----------------------------------------------------------------------------------------------------------------------
class JKRFileAttr(enum.IntFlag):
    FILE = 1
    FOLDER = 2
    COMPRESSED = 4
    LOAD_TO_MRAM = 16
    LOAD_TO_ARAM = 32
    LOAD_FROM_DVD = 64
    USE_YAZ0 = 128

    FILE_AND_COMPRESSION = 133
    FILE_AND_PRELOAD = 113


class JKRPreloadType(enum.IntEnum):
    NONE = -1
    MRAM = 0
    ARAM = 1
    DVD = 2


# ----------------------------------------------------------------------------------------------------------------------
# Helper functions to calculate identifiers and hashes for nodes and directories.
# ----------------------------------------------------------------------------------------------------------------------
def _file_name_to_hash_(file_name: str) -> int:
    file_hash = 0
    for ch in file_name.encode("ascii"):
        file_hash *= 3
        file_hash += ch
    return file_hash & 0xFFFF


def _calc_dir_identifier_(dir_name: str, is_first: bool) -> int:
    # Root node uses "ROOT" as identifier
    if is_first:
        return 0x524F4F54

    enc_upper = dir_name.upper().encode("ascii")
    len_enc_name = len(enc_upper)

    identifier = 0
    for i in range(4):
        identifier <<= 8
        if i >= len_enc_name:
            identifier += 0x20
        else:
            identifier += enc_upper[i]

    return identifier


# ----------------------------------------------------------------------------------------------------------------------
# JKRFolderNode definition
# ----------------------------------------------------------------------------------------------------------------------
class JKRFolderNode:
    def __init__(self):
        self._identifier_ = 0        # Automatically calculated when setting name
        self._off_name_ = -1         # Temporary. Handled by unpack and pack
        self._hash_ = 0              # Automatically calculated when setting name
        self._num_files_ = 0         # Temporary. Handled by unpack and _fix_nodes_and_directories_
        self._idx_files_start_ = 0   # Temporary. Handled by unpack and _fix_nodes_and_directories_

        self._name_ = None           # The node's name
        self._directory_ = None      # The directory that represents this node
        self._directories_ = list()  # List of subdirectories that belong to this node
        self._archive_ = None        # The archive to which this node belongs
        self._is_root_ = False       # Declares if this node is an archive's root node

    def __repr__(self):
        return self._name_

    @property
    def name(self):
        return self._name_

    @name.setter
    def name(self, val):
        self._set_name_internal_(val)

        if self._directory_ is not None:
            self._directory_._set_name_internal_(val)

    def _set_name_internal_(self, val):
        self._identifier_ = _calc_dir_identifier_(val, self._is_root_)
        self._hash_ = _file_name_to_hash_(val)
        self._name_ = val

    @property
    def archive(self):
        return self._archive_

    @property
    def directory(self):
        return self._directory_

    @property
    def files(self):
        return tuple(filter(lambda d: d.is_file, self._directories_))

    @property
    def folders(self):
        return tuple([f.folder for f in filter(lambda d: d.is_folder and not d.is_shortcut, self._directories_)])

    def create_folder(self, folder_name: str):
        return self._archive_.create_folder(self, folder_name)

    def create_file(self, file_name: str):
        return self._archive_.create_file(self, file_name)

    def remove_folder(self, folder) -> bool:
        if folder._directory_ is None or folder._directory_._parent_node_ != self:
            return False
        return self._archive_.remove_folder(folder)

    def remove_file(self, file) -> bool:
        if file._parent_node_ != self:
            return False
        return self._archive_.remove_file(file)


# ----------------------------------------------------------------------------------------------------------------------
# JKRDirectory definition
# ----------------------------------------------------------------------------------------------------------------------
class JKRDirectory:
    def __init__(self):
        self._index_ = 0xFFFF       # Automatically calculated if file identifiers are synchronized
        self._hash_ = 0             # Automatically calculated when setting name
        self._attributes_ = 0       # Stores the attributes that declare the directory's type, compression and memory
        self._off_name_ = -1        # Temporary. Handled by unpack and pack
        self._off_file_data_ = -1   # Temporary. Handled by unpack and pack
        self._len_file_data_ = 0    # Temporary. Handled by unpack and _fix_nodes_and_directories_
        self._unk10_ = 0            # Unknown, seems to always be 0

        self._name_ = None          # The directory's name
        self._data_ = None            # Files-only. This is the file's actual data
        self._node_ = None          # Folders-only. This is the node that represents this directory
        self._parent_node_ = None   # The parent node to which this directory belongs
        self._archive_ = None       # The archive to which this directory belongs

    def __repr__(self):
        return self._name_

    @property
    def index(self):
        return self._index_

    @index.setter
    def index(self, val: int):
        if self.is_file:
            if not 0 < val < 0xFFFF:
                raise ValueError(f"Index out of range: 0 < {val} < 65535 not fulfilled!")
            self._index_ = val
        else:
            self._index_ = 0xFFFF

    @property
    def name(self):
        return self._name_

    @name.setter
    def name(self, val: str):
        self._set_name_internal_(val)

        if self._node_ is not None:
            self._node_._set_name_internal_(val)

    def _set_name_internal_(self, val):
        self._hash_ = _file_name_to_hash_(val)
        self._name_ = val

    @property
    def data(self):
        if self._attributes_ & JKRFileAttr.FILE:
            return self._data_
        return None

    @data.setter
    def data(self, val: pyaurum.ByteBuffer):
        if self._attributes_ & JKRFileAttr.FILE:
            self._data_ = val
        else:
            raise JKRArchiveException(f"Cannot set file contents. Directory {self._name_} is not a file!")

    @property
    def folder(self):
        return self._node_

    @property
    def parent_folder(self):
        return self._parent_node_

    @property
    def archive(self):
        return self._archive_

    @property
    def is_file(self) -> bool:
        return bool(self._attributes_ & JKRFileAttr.FILE)

    @property
    def is_folder(self) -> bool:
        return bool(self._attributes_ & JKRFileAttr.FOLDER)

    @property
    def is_shortcut(self) -> bool:
        return bool(self._attributes_ & JKRFileAttr.FOLDER) and self._name_ in [".", ".."]

    @property
    def preload_type(self) -> JKRPreloadType:
        if self._attributes_ & JKRFileAttr.FILE:
            if self._attributes_ & JKRFileAttr.LOAD_TO_MRAM:
                return JKRPreloadType.MRAM
            elif self._attributes_ & JKRFileAttr.LOAD_TO_ARAM:
                return JKRPreloadType.ARAM
            elif self._attributes_ & JKRFileAttr.LOAD_FROM_DVD:
                return JKRPreloadType.DVD
        return JKRPreloadType.NONE

    @preload_type.setter
    def preload_type(self, val: JKRPreloadType):
        if self._attributes_ & JKRFileAttr.FILE:
            self._attributes_ &= JKRFileAttr.FILE_AND_COMPRESSION

            if val == JKRPreloadType.MRAM:
                self._attributes_ |= JKRFileAttr.LOAD_TO_MRAM
            elif val == JKRPreloadType.ARAM:
                self._attributes_ |= JKRFileAttr.LOAD_TO_ARAM
            elif val == JKRPreloadType.DVD:
                self._attributes_ |= JKRFileAttr.LOAD_FROM_DVD
        else:
            self._attributes_ = JKRFileAttr.FOLDER

    @property
    def compression_type(self) -> jkrcomp.JKRCompressionType:
        if self._attributes_ & JKRFileAttr.FILE:
            if self._attributes_ & JKRFileAttr.COMPRESSED:
                if self._attributes_ & JKRFileAttr.USE_YAZ0:
                    return jkrcomp.JKRCompressionType.SZS
                else:
                    return jkrcomp.JKRCompressionType.SZP
        return jkrcomp.JKRCompressionType.NONE

    @compression_type.setter
    def compression_type(self, val: jkrcomp.JKRCompressionType):
        if self._attributes_ & JKRFileAttr.FILE:
            self._attributes_ &= JKRFileAttr.FILE_AND_PRELOAD

            if val == jkrcomp.JKRCompressionType.SZP:
                self._attributes_ |= JKRFileAttr.COMPRESSED
            elif val == jkrcomp.JKRCompressionType.SZS:
                self._attributes_ |= JKRFileAttr.COMPRESSED
                self._attributes_ |= JKRFileAttr.USE_YAZ0
        else:
            self._attributes_ = JKRFileAttr.FOLDER


# ----------------------------------------------------------------------------------------------------------------------
# JKRArchive definition
# ----------------------------------------------------------------------------------------------------------------------
class JKRArchive:
    _STRUCT_HEADER_ = struct.Struct(">4s6I")
    _STRUCT_INFO_ = struct.Struct(">6IH?")
    _STRUCT_NODE_ = struct.Struct(">2I2HI")
    _STRUCT_DIRECTORY_ = struct.Struct(">2H4I")

    def __init__(self, sync_file_ids: bool = True, reduce_string_pool: bool = False):
        self._nodes_ = list()                 # Stores all nodes
        self._directories_ = list()           # Stores all directories
        self._root_ = None                    # The root node
        self._next_file_id_ = 0               # The next free file identifier
        self.sync_file_ids = sync_file_ids    # Causes recalculation of file identifiers

        # This is an option that allows the user to generate archives with a reduced string pool. Normally, occurrences
        # are not properly handled by Nintendo's archive tool which causes the files to be a bit bigger than they have
        # to be...
        self.reduce_strings = reduce_string_pool

        # These are temporary lists that store what files belong to what RAM section. These are meant to be populated in
        # the _fix_nodes_and_directories_ function and used in the pack function. After that these lists will be cleared
        # again to save up space.
        self._mram_files_ = []
        self._aram_files_ = []
        self._dvd_files_ = []

    # ------------------------------------------------------------------------------------------------------------------
    # Functions for loading and saving archives
    # ------------------------------------------------------------------------------------------------------------------
    def unpack(self, buffer: pyaurum.ByteBuffer) -> None:
        self._nodes_.clear()
        self._directories_.clear()
        self._root_ = None

        # In SMG1/2, and possibly other games, RARC files are usually compressed. We have to try decompressing our
        # buffer before we can start parsing the actual archive data.
        buffer = jkrcomp.decompress(buffer)

        # Parse header
        if pyaurum.get_magic4(buffer) != "RARC":
            raise JKRArchiveException("Fatal! No RARC data provided.")

        # Parse the RARC and info headers. Some information will be ignored as they are not needed for unpacking.
        _, _, off_info, len_info, _, _, _\
            = buffer.read_from(JKRArchive._STRUCT_HEADER_, 0)

        num_nodes, off_nodes, num_dirs, off_files, _, off_strings, self._next_file_id_, self.sync_file_ids\
            = buffer.read_from(JKRArchive._STRUCT_INFO_, off_info)

        # Calculate absolute offsets
        off_nodes += off_info
        off_files += off_info
        off_strings += off_info
        off_data = off_info + len_info

        # Parse all folder nodes
        buffer.set_position(off_nodes)

        for _ in range(num_nodes):
            # Parse and create folder node
            node = JKRFolderNode()
            node._identifier_, node._off_name_, node._hash_, node._num_files_, node._idx_files_start_\
                = buffer.read(JKRArchive._STRUCT_NODE_)
            node._name_ = pyaurum.read_string(buffer, off_strings + node._off_name_)

            # First node is root
            if self._root_ is None:
                self._root_ = node
                self._root_._is_root_ = True

            node._archive_ = self
            self._nodes_.append(node)

        # Parse all directories
        buffer.set_position(off_files)

        for _ in range(num_dirs):
            dir = JKRDirectory()
            dir._index_, dir._hash_, dir._attributes_, dir._off_file_data_, dir._len_file_data_, dir._unk10_\
                = buffer.read(JKRArchive._STRUCT_DIRECTORY_)

            # Attributes and name offset are stored as one dword. We have to split the two first. Then, read the name.
            dir._off_name_ = dir._attributes_ & 0x00FFFFFF
            dir._attributes_ = (dir._attributes_ >> 24) & 0xFF
            dir._name_ = pyaurum.read_string(buffer, off_strings + dir._off_name_)

            dir._archive_ = self
            self._directories_.append(dir)

            if dir.is_folder and dir._off_file_data_ != 0xFFFFFFFF:
                # Assign folder node to this directory
                dir._node_ = self._nodes_[dir._off_file_data_]

                # If node and directory hashes are the same, the directory directly represents the node
                if dir._node_._hash_ == dir._hash_:
                    dir._node_._directory_ = dir
            elif dir.is_file:
                # Read file data
                file_start = off_data + dir._off_file_data_
                file_end = file_start + dir._len_file_data_
                buf_file_data = pyaurum.ByteBuffer(buffer[file_start:file_end])

                # Decompress the file's data if necessary
                if dir.compression_type == jkrcomp.JKRCompressionType.SZS:
                    buf_file_data = jkrcomp.decompress_szs(buf_file_data, False)
                elif dir.compression_type == jkrcomp.JKRCompressionType.SZP:
                    buf_file_data = jkrcomp.decompress_szp(buf_file_data, False)

                dir._data_ = buf_file_data

        # Attach directories to nodes
        for node in self._nodes_:
            for i in range(node._idx_files_start_, node._idx_files_start_ + node._num_files_):
                child_dir = self._directories_[i]
                child_dir._parent_node_ = node
                node._directories_.append(child_dir)

    def pack(self) -> pyaurum.ByteBuffer:
        # Fix order of nodes and directories. This will also fix any indices and sizes for both nodes and dirs.
        self._fix_nodes_and_directories_()

        # Gather information about the archive and prepare output buffer
        num_nodes = len(self._nodes_)
        off_nodes = 0x20
        num_dirs = len(self._directories_)
        off_dirs = pyaurum.alignsize32(off_nodes + num_nodes * 0x10)
        total_file_size = pyaurum.alignsize32(0x20 + off_dirs + num_dirs * 0x14)

        buffer = pyaurum.ByteBuffer(total_file_size)

        # Collect strings
        off_strings = total_file_size - 0x20
        string_pool = pyaurum.StringPool(format=pyaurum.StringPoolFormat.NULL_TERMINATED)
        string_pool.write(".")
        string_pool.write("..")
        self._root_._off_name_ = string_pool.write(self._root_.name)

        # We'll look through all nodes and directories first to finish the string pool. This ensures that only one
        # occurrence of a string is stored in the pool. However, this is not the method Nintendo has used themselves.
        if self.reduce_strings:
            def collect_strings(node: JKRFolderNode):
                for directory in node._directories_:
                    directory._off_name_ = string_pool.write(directory.name)

                    if directory.is_folder and not directory.is_shortcut:
                        directory._node_._off_name_ = directory._off_name_
                        collect_strings(directory._node_)
            collect_strings(self._root_)
        # By default, the string pool is not reduced properly and contains duplicated string occurrences. If we want to
        # produce files that match the original archives 1:1, we have to account for this oversight. However, there is
        # a convenient option available to reduce the string pool size drastically.
        else:
            string_pool.toggle_lookup()

            def collect_strings(node: JKRFolderNode):
                for directory in node._directories_:
                    is_shortcut = directory.is_shortcut

                    if is_shortcut:
                        directory._off_name_ = string_pool.find(directory.name)
                    else:
                        directory._off_name_ = string_pool.write(directory.name)

                    if directory.is_folder and not is_shortcut:
                        directory._node_._off_name_ = directory._off_name_
                        collect_strings(directory._node_)
            collect_strings(self._root_)

        # Append string pool
        string_pool.align32()
        buffer += string_pool.get_bytes()
        len_strings = len(string_pool)
        del string_pool

        # Write all nodes
        buffer.set_position(0x40)

        for node in self._nodes_:
            buffer.write(JKRArchive._STRUCT_NODE_, node._identifier_, node._off_name_, node._hash_, node._num_files_, node._idx_files_start_)

        # Write file data
        data_start = len(buffer)
        buffer.set_position(0x20 + off_dirs)

        def write_file_data(files: list) -> int:
            nonlocal buffer
            categorized_data_start = len(buffer)

            for file_dir in files:
                file_dir._off_file_data_ = len(buffer) - data_start
                buffer += file_dir.data
                buffer.align32()

            files.clear()
            return len(buffer) - categorized_data_start

        mram_size = write_file_data(self._mram_files_)
        aram_size = write_file_data(self._aram_files_)
        write_file_data(self._dvd_files_)

        # Write directories
        for directory in self._directories_:
            attributes = (directory._attributes_ << 24) | directory._off_name_
            buffer.write(JKRArchive._STRUCT_DIRECTORY_, directory._index_, directory._hash_, attributes, directory._off_file_data_, directory._len_file_data_, directory._unk10_)

        # Write header and info block
        total_file_size = len(buffer)
        buffer.write_into(JKRArchive._STRUCT_HEADER_, 0, "RARC".encode("ascii"), total_file_size, 0x20, data_start - 0x20,
                          total_file_size - data_start, mram_size, aram_size)
        buffer.write_into(JKRArchive._STRUCT_INFO_, 0x20, num_nodes, off_nodes, num_dirs, off_dirs, len_strings, off_strings,
                          self._next_file_id_, self.sync_file_ids)

        return buffer

    def _fix_nodes_and_directories_(self):
        self._directories_.clear()
        self._fix_node_and_directories_(self._root_)

        if self.sync_file_ids:
            self._next_file_id_ = len(self._directories_)

        for dir in self._directories_:
            if dir.is_folder:
                dir._off_file_data_ = self._nodes_.index(dir.folder) if dir.folder is not None else 0xFFFFFFFF
            else:
                # Keep index synchronized
                if self.sync_file_ids:
                    dir._index_ = self._directories_.index(dir)

                # Update file size
                dir._len_file_data_ = len(dir.data)

                # Put file into preload group
                if dir.preload_type == JKRPreloadType.MRAM:
                    self._mram_files_.append(dir)
                elif dir.preload_type == JKRPreloadType.ARAM:
                    self._aram_files_.append(dir)
                elif dir.preload_type == JKRPreloadType.DVD:
                    self._dvd_files_.append(dir)

    def _fix_node_and_directories_(self, node: JKRFolderNode):
        # Put the shortcut directories ("." and "..") at the end of the node's directory list
        shortcuts = list()

        for subdir in node._directories_:
            if subdir.is_shortcut:
                shortcuts.append(subdir)
        for subdir in shortcuts:
            node._directories_.remove(subdir)
            node._directories_.append(subdir)

        shortcuts.clear()

        # Update the node's first file index, number of directories and add the actual directories to the archive
        node._idx_files_start_ = len(self._directories_)
        node._num_files_ = len(node._directories_)
        self._directories_ += node._directories_

        # Handle the subdirectory nodes as well
        for subdir in node._directories_:
            if subdir.is_folder and not subdir.is_shortcut:
                self._fix_node_and_directories_(subdir.folder)

    # ------------------------------------------------------------------------------------------------------------------
    # Functions to find, create and remove nodes and directories
    # ------------------------------------------------------------------------------------------------------------------
    def reset_and_create_root(self, root_name: str):
        self._nodes_.clear()
        self._directories_.clear()
        self._root_ = None
        self._next_file_id_ = 0

        return self.create_root(root_name)

    def _create_directory_(self, name: str, attr: int, node: JKRFolderNode, parent_node: JKRFolderNode) -> JKRDirectory:
        new_dir = JKRDirectory()
        new_dir.name = name
        new_dir._attributes_ = attr
        new_dir._node_ = node
        new_dir._parent_node_ = parent_node
        new_dir._archive_ = self

        parent_node._directories_.append(new_dir)
        self._directories_.append(new_dir)

        return new_dir

    def create_root(self, root_name: str) -> JKRFolderNode:
        if self._root_:
            raise JKRArchiveException("Root already exists!")

        root_node = JKRFolderNode()
        root_node._is_root_ = True
        root_node.name = root_name
        root_node._archive_ = self
        self._root_ = root_node
        self._nodes_.append(root_node)

        self._create_directory_(".", JKRFileAttr.FOLDER, root_node, root_node)
        self._create_directory_("..", JKRFileAttr.FOLDER, None, root_node)

        return root_node

    def _validate_node_and_dir_name_(self, node: JKRFolderNode, dir_name: str) -> None:
        # Check if parent node belongs to this archive
        if node.archive != self:
            raise JKRArchiveException(f"The folder {node.name} does not belong to this archive!")

        # Check if the node already contains a directory with the same name
        for subdir in node._directories_:
            if subdir.name == node:
                raise JKRArchiveException(f"The directory at {node.name}/{dir_name} already exists!")

    def create_folder(self, parent_node: JKRFolderNode, folder_name: str) -> JKRFolderNode:
        self._validate_node_and_dir_name_(parent_node, folder_name)

        folder = JKRFolderNode()
        folder.name = folder_name
        folder._archive_ = self
        self._nodes_.append(folder)

        self._create_directory_(folder_name, JKRFileAttr.FOLDER, folder, parent_node)
        self._create_directory_(".", JKRFileAttr.FOLDER, folder, folder)
        self._create_directory_("..", JKRFileAttr.FOLDER, parent_node, folder)

        return folder

    def create_file(self, parent_node: JKRFolderNode, file_name: str) -> JKRDirectory:
        self._validate_node_and_dir_name_(parent_node, file_name)

        new_file = self._create_directory_(file_name, JKRFileAttr.FILE | JKRFileAttr.LOAD_TO_MRAM, None, parent_node)
        new_file._data_ = pyaurum.ByteBuffer()

        if not self.sync_file_ids:
            new_file.index = self._next_file_id_
            self._next_file_id_ += 1

        return new_file

    def get_root(self):
        return self._root_

    def find_folder(self, folder_path: str) -> JKRFolderNode:
        split_path = folder_path.lower().split("/")
        len_split = len(split_path)
        ret_node = None

        # Searching for root node
        if len_split == 1:
            if split_path[0] == ".":
                return self._root_
            elif split_path[0] == "..":
                return ret_node

        # Nothing returns nothing, of course
        if len_split == 0:
            return ret_node

        # Last name cannot be "." or ".."
        if split_path[-1] in [".", ".."]:
            return ret_node

        # If the first file name is "..", we'll have to return the folder's parent folder
        if split_path[0] in [".", ".."]:
            find_parent = split_path[0] == ".."
        else:
            if split_path[0] not in ["", self._root_.name.lower()]:
                return ret_node
            find_parent = False

        split_path.pop(0)
        cur_node = self._root_

        while len(split_path) > 0 and ret_node is None:
            for subfolder in cur_node.folders:
                if subfolder.name.lower() == split_path[0]:
                    cur_node = subfolder
                    if len(split_path) == 1:
                        ret_node = cur_node
                    break

            split_path.pop(0)

        if find_parent and ret_node is not None:
            ret_node = ret_node.directory.parent_folder

        return ret_node

    def find_file(self, file_path: str) -> JKRDirectory:
        split_path = file_path.lower().lstrip(".").rsplit("/", 1)

        if len(split_path) != 2:
            return None

        if split_path[0] == "":
            folder_node = self._root_
        else:
            folder_node = self.find_folder(split_path[0])

        if folder_node is not None:
            for file_dir in folder_node.files:
                if file_dir.name.lower() == split_path[1]:
                    return file_dir

        return None

    def _remove_directory_(self, directory: JKRDirectory):
        directory._parent_node_._directories_.remove(directory)
        directory._parent_node_ = None
        directory._node_ = None
        directory._archive_ = None
        self._directories_.remove(directory)

    def remove_folder(self, folder: JKRFolderNode) -> bool:
        if folder.archive != self:
            return False

        # Recursively remove subdirectories
        for subdir in folder._directories_.copy():
            if subdir.is_folder and not subdir.is_shortcut:
                self.remove_folder(subdir.folder)
            else:
                self._remove_directory_(subdir)

        # Detach folder node and directory
        if folder != self._root_:
            self._remove_directory_(folder._directory_)
        self._nodes_.remove(folder)
        folder._directory_ = None
        folder._archive_ = None
        folder._directories_.clear()

        return True

    def remove_file(self, file: JKRDirectory) -> bool:
        if not file.is_file and file.archive != self:
            return False

        self._remove_directory_(file)

        return True

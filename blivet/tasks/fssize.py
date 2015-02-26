# fssize.py
# Filesystem size gathering classes.
#
# Copyright (C) 2015  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
# Red Hat Author(s): Anne Mulhern <amulhern@redhat.com>

import abc
from collections import namedtuple

from six import add_metaclass

from ..errors import FSError
from ..size import Size
from .. import util

from . import availability
from . import task

_tags = ("count", "size")
_Tags = namedtuple("_Tags", _tags)

@add_metaclass(abc.ABCMeta)
class FSSize(task.Task):
    """ An abstract class that represents size information extraction. """
    description = "current filesystem size"

    tags = abc.abstractproperty(
        doc="Strings used for extracting components of size.")

    def __init__(self, an_fs):
        """ Initializer.

            :param FS an_fs: a filesystem object
        """
        self.fs = an_fs

    # TASK methods

    @classmethod
    def available(cls):
        return True

    @property
    def unavailable(self):
        return False

    @property
    def unready(self):
        return False

    @property
    def unable(self):
        if self.fs._current_info is None:
            return "No filesystem info available to extract current size from."
        return False

    # IMPLEMENTATION methods

    def doTask(self):
        """ Returns the size of the filesystem.

            :returns: the size of the filesystem or None
            :rtype: :class:`~.size.Size` or NoneType
            :raises FSError: on failure
        """
        error_msg = self.impossible
        if error_msg:
            raise FSError(error_msg)

        # Setup initial values
        values = {}
        for k in _tags:
            values[k] = None

        # Attempt to set values from info
        for line in (l.strip() for l in self.fs._current_info.splitlines()):
            key = next((k for k in _tags if line.startswith(getattr(self.tags, k))), None)
            if not key:
                continue

            if values[key] is not None:
                raise FSError("found two matches for key %s" % key)

            # Look for last numeric value in matching line
            fields = line.split()
            fields.reverse()
            for field in fields:
                try:
                    values[key] = int(field)
                    break
                except ValueError:
                    continue

        # Raise an error if a value is missing
        missing = next((k for k in _tags if values[k] is None), None)
        if missing is not None:
            raise FSError("Failed to parse info for %s." % missing)

        return values["count"] * Size(values["size"])

class Ext2FSSize(FSSize):
    tags = _Tags(size="Block size:", count="Block count:")

class JFSSize(FSSize):
    tags = _Tags(size="Physical block size:", count="Aggregate size:")

class NTFSSize(FSSize):
    tags = _Tags(size="Cluster Size:", count="Volume Size in Clusters:")

class ReiserFSSize(FSSize):
    tags = _Tags(size="Blocksize:", count="Count of blocks on the device:")

class XFSSize(FSSize):
    tags = _Tags(size="blocksize =", count="dblocks =")

class TmpFSSize(task.Task):
    description = "current filesystem size"

    app_name = "df"
    _app = availability.Application(availability.Path(), app_name)

    def __init__(self, an_fs):
        """ Initializer.

           :param FS an_fs: a filesystem object
        """
        self.fs = an_fs

    @classmethod
    def available(cls):
        return cls._app.available

    @property
    def unavailable(self):
        if not self._app.available:
            return "application %s is not available" % self._app
        return False

    @property
    def unready(self):
        if not self.fs.status:
            return "filesystem is not mounted"
        return False

    @property
    def unable(self):
        return False

    @property
    def _sizeCommand(self):
        return [str(self._app), self.fs.systemMountpoint, "--output=size"]

    def doTask(self):
        error_msg = self.impossible
        if error_msg:
            raise FSError(error_msg)

        try:
            (ret, out) = util.run_program_and_capture_output(self._sizeCommand)
            if ret:
                raise FSError("Failed to execute command %s." % self._sizeCommand)
        except OSError:
            raise FSError("Failed to execute command %s." % self._sizeCommand)

        lines = out.splitlines()
        if len(lines) != 2 or lines[0].strip() != "1K-blocks":
            raise FSError("Failed to parse output of command %s." % self._sizeCommand)

        return Size("%s KiB" % lines[1])
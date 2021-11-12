# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""This module provides classes to handle custom BIDS derivatives file input."""

from traits.api import (HasTraits, Directory, Str)


class CustomBIDSFile(HasTraits):
    """Base class used to represent a BIDS-formatted file inside a custom BIDS derivatives directory.

    Attributes
    ----------
    custom_derivatives_dir : Directory
        Path to custom BIDS derivatives directory

    suffix : Str
        Filename suffix e.g. `sub-01_T1w.nii.gz` has suffix `T1w`

    acquisition : Str
        Label used in `_acq-<label>_`

    resolution : Str
        Label used in `_res-<label>_`

    extension : Str
        File extension

    atlas : Str
        Label used in `_atlas-<label>_`

    label : Str
        Label used in `_label-<label>_`

    desc : Str
        Label used in `_desc-<label>_`

    """
    custom_derivatives_dir = Directory
    suffix = Str
    acquisition = Str
    resolution = Str
    extension = Str
    atlas = Str
    label = Str
    desc = Str

    def __init__(
            self,
            p_custom_derivatives_dir="",
            p_suffix="",
            p_extension="",
            p_acquisition="",
            p_atlas="",
            p_resolution="",
            p_label="",
            p_desc=""
    ):
        self.custom_derivatives_dir = p_custom_derivatives_dir
        self.suffix = p_suffix
        self.extension = p_extension
        self.acquisition = p_acquisition
        self.atlas = p_atlas
        self.resolution = p_resolution
        self.label = p_label
        self.desc = p_desc

    def __str__(self):
        msg = "{"
        msg += f' "custom_derivatives_dir": {self.custom_derivatives_dir}, '
        msg += f' "suffix": {self.suffix}, '
        msg += f' "extension": {self.extension}, '
        msg += f' "acquisition": {self.acquisition}, '
        msg += f' "atlas": {self.atlas}, '
        msg += f' "resolution": {self.resolution}, '
        msg += f' "label": {self.label}, '
        msg += f' "desc": {self.desc}'
        msg += "}"
        return msg


class CustomParcellationBIDSFile(CustomBIDSFile):
    """Represent a custom parcellation files in the form `sub-<label>_atlas-<label>[_res-<label>]_dseg.<extension>`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_atlas="L2018")


class CustomWMMaskBIDSFile(CustomBIDSFile):
    """Represent a custom white-matter mask in the form `sub-<label>_label-WM_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_label="WM")


class CustomGMMaskBIDSFile(CustomBIDSFile):
    """Represent a custom gray-matter mask in the form `sub-<label>_label-GM_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_label="GM")


class CustomCSFMaskBIDSFile(CustomBIDSFile):
    """Represent a custom CSF mask in the form `sub-<label>_label-CSF_dseg.nii.gz`."""

    def __init__(self):
        super().__init__(p_suffix="dseg", p_label="CSF")

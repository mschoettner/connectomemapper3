# Copyright (C) 2009-2020, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

"""Definition of diffusion tracking config UI classes."""

from traits.api import *
from traitsui.api import *

from cmp.stages.diffusion.tracking import Dipy_tracking_config, MRtrix_tracking_config


class Dipy_tracking_configUI(Dipy_tracking_config):
    """Class that extends the :class:`Dipy_tracking_config` with graphical components.

    Attributes
    ----------
    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g. 
        the parameters for diffusion tractography using Dipy

    See also
    ---------
    cmp.stages.diffusion.tracking.Dipy_tracking_config
    """

    traits_view = View(VGroup(
        Group(
            Item('seed_density', label="Seed density"),
            Item('step_size', label="Step size"),
            Item('max_angle', label="Max angle (degree)"),
            Item('fa_thresh', label="FA threshold (classifier)",
                 visible_when='seed_from_gmwmi is False'),
            label='Streamlines settings',
            orientation='vertical'
        ),
        Group(
            Item('use_act', label="Use PFT"),
            Item('seed_from_gmwmi', visible_when='use_act'),
            # Item('fast_number_of_classes', label='Number of tissue classes (FAST)')
            label='Particle Filtering Tractography (PFT)',
            visible_when='tracking_mode=="Probabilistic"',
            orientation='vertical'
        )
    ),
    )


class MRtrix_tracking_configUI(MRtrix_tracking_config):
    """Class that extends the :class:`MRtrix_tracking_config` with graphical components.

    Attributes
    ----------
    traits_view : traits.ui.View
        TraitsUI view that displays the attributes of this class, e.g.
        the parameters for tractography using MRtrix

    See also
    ---------
    cmp.stages.diffusion.reconstruction.MRtrix_tracking_config
    """

    traits_view = View(VGroup(
        Group(
            'desired_number_of_tracks',
            # 'max_number_of_seeds',
            HGroup('min_length', 'max_length'),
            'angle',
            Item('curvature', label="Curvature radius"),
            'step_size',
            'cutoff_value',
            label='Streamline settings',
            orientation='vertical'),
        Group(
            Item('use_act', label='Use ACT'),
            Item('crop_at_gmwmi', visible_when='use_act'),
            Item('backtrack', visible_when='use_act',
                 enabled_when='tracking_mode=="Probabilistic"'),
            Item('seed_from_gmwmi', visible_when='use_act'),
            label='Anatomically-Constrained Tractography (ACT)',
            orientation='vertical'
        ),
        Group(
            Item('sift2', label="Perform SIFT2 to compute fiber weights"),
            label='Streamline filtering',
            orientation='vertical'
        ),
    ),
    )
# Copyright (C) 2009-2017, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

""" CMP Stage for Diffusion reconstruction and tractography
"""

# General imports
from traits.api import *
from traitsui.api import *
import gzip
import pickle

# Nipype imports
import nipype.pipeline.engine as pe
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.fsl as fsl
import nipype.interfaces.utility as util

import nibabel as nib

# Own imports
from cmp.stages.common import Stage
from reconstruction import *
from tracking import *
from cmp.interfaces.misc import ExtractImageVoxelSizes, Tck2Trk


class DiffusionConfig(HasTraits):

    diffusion_imaging_model_editor = List(['DSI','DTI','HARDI'])
    diffusion_imaging_model = Str('DSI')
    #resampling = Tuple(2,2,2)
    #interpolation = Enum(['interpolate','weighted','nearest','sinc','cubic'])
    # processing_tool_editor = List(['DTK','MRtrix','Camino','FSL','Gibbs'])
    # processing_tool_editor = List(['Dipy','MRtrix','Custom'])
    dilate_rois = Bool(True)
    dilation_kernel = Enum(['Box','Gauss','Sphere'])
    dilation_radius = Enum([1,2,3,4])
    # processing_tool = Str('MRtrix')
    recon_processing_tool_editor = List(['Dipy','MRtrix','Custom'])
    tracking_processing_tool_editor = List(['Dipy','MRtrix','Custom'])
    processing_tool_editor = List(['Dipy','MRtrix','Custom'])
    recon_processing_tool = Str('MRtrix')
    tracking_processing_tool = Str('MRtrix')
    custom_track_file = File
    dtk_recon_config = Instance(HasTraits)
    dipy_recon_config = Instance(HasTraits)
    mrtrix_recon_config = Instance(HasTraits)
    camino_recon_config = Instance(HasTraits)
    fsl_recon_config = Instance(HasTraits)
    gibbs_recon_config = Instance(HasTraits)
    dtk_tracking_config = Instance(HasTraits)
    dtb_tracking_config = Instance(HasTraits)
    dipy_tracking_config = Instance(HasTraits)
    mrtrix_tracking_config = Instance(HasTraits)
    camino_tracking_config = Instance(HasTraits)
    fsl_tracking_config = Instance(HasTraits)
    gibbs_tracking_config = Instance(HasTraits)
    diffusion_model_editor = List(['Deterministic','Probabilistic'])
    diffusion_model = Str('Probabilistic')
    ## TODO import custom DWI and tractogram (need to register anatomical data to DWI to project parcellated ROIs onto the tractogram)

    traits_view = View(#HGroup(Item('resampling',label='Resampling (x,y,z)',editor=TupleEditor(cols=3)),
                       #'interpolation'),
                      Item('diffusion_imaging_model',editor=EnumEditor(name='diffusion_imaging_model_editor')),
		              #Item('processing_tool',editor=EnumEditor(name='processing_tool_editor')),
                      HGroup(
                           Item('dilate_rois'),#,visible_when='processing_tool!="DTK"'),
                           Item('dilation_radius',visible_when='dilate_rois',label="radius")
                           ),
                       Group(Item('recon_processing_tool',label='Reconstruction processing tool',editor=EnumEditor(name='recon_processing_tool_editor')),
                             #Item('dtk_recon_config',style='custom',visible_when='processing_tool=="DTK"'),
                             Item('dipy_recon_config',style='custom',visible_when='recon_processing_tool=="Dipy"'),
			                 Item('mrtrix_recon_config',style='custom',visible_when='recon_processing_tool=="MRtrix"'),
			                 #Item('camino_recon_config',style='custom',visible_when='processing_tool=="Camino"'),
                             #Item('fsl_recon_config',style='custom',visible_when='processing_tool=="FSL"'),
                             #Item('gibbs_recon_config',style='custom',visible_when='processing_tool=="Gibbs"'),
                             label='Reconstruction', show_border=True, show_labels=False,visible_when='tracking_processing_tool!=Custom'),
                       Group(Item('tracking_processing_tool',label='Tracking processing tool',editor=EnumEditor(name='tracking_processing_tool_editor')),
                             Item('diffusion_model',editor=EnumEditor(name='diffusion_model_editor'),visible_when='tracking_processing_tool!="Custom"'),
                             #Item('dtb_tracking_config',style='custom',visible_when='processing_tool=="DTK"'),
                             Item('dipy_tracking_config',style='custom',visible_when='tracking_processing_tool=="Dipy"'),
			                 Item('mrtrix_tracking_config',style='custom',visible_when='tracking_processing_tool=="MRtrix"'),
			                 #Item('camino_tracking_config',style='custom',visible_when='processing_tool=="Camino"'),
                             #Item('fsl_tracking_config',style='custom',visible_when='processing_tool=="FSL"'),
                             #Item('gibbs_tracking_config',style='custom',visible_when='processing_tool=="Gibbs"'),
                             label='Tracking', show_border=True, show_labels=False),
                        Group(
                            Item('custom_track_file', style='simple'),
                            visible_when='tracking_processing_tool=="Custom"'),
                       )

    # dipy_traits_view = View(#HGroup(Item('resampling',label='Resampling (x,y,z)',editor=TupleEditor(cols=3)),
    #                    #'interpolation'),
    #                     Item('processing_tool',editor=EnumEditor(name='processing_tool_editor')),
    #                     Item('dilate_rois'),
    #                     Group(
    #                         Item('dipy_recon_config',style='custom'),
    #                         label='Reconstruction', show_border=True, show_labels=False),
    #                     Group(
    #                         Item('diffusion_model',editor=EnumEditor(name='diffusion_model_editor')),
    #                         Item('dipy_tracking_config',style='custom'),
    #                         label='Tracking', show_border=True, show_labels=False),
    #                     )

    # mrtrix_traits_view = View(#HGroup(Item('resampling',label='Resampling (x,y,z)',editor=TupleEditor(cols=3)),
    #                    #'interpolation'),
    #                    Item('processing_tool',editor=EnumEditor(name='processing_tool_editor')),
    #                    Item('dilate_rois'),
    #                    Group(
    #                         Item('mrtrix_recon_config',style='custom'),
    #                         label='Reconstruction', show_border=True, show_labels=False),
    #                    Group(
    #                         Item('diffusion_model',editor=EnumEditor(name='diffusion_model_editor')),
    #                         Item('mrtrix_tracking_config',style='custom'),
    #                         label='Tracking', show_border=True, show_labels=False),
    #                    )

    def __init__(self):
        self.dtk_recon_config = DTK_recon_config(imaging_model=self.diffusion_imaging_model)
        self.dipy_recon_config = Dipy_recon_config(imaging_model=self.diffusion_imaging_model,recon_mode=self.diffusion_model,tracking_processing_tool=self.tracking_processing_tool)
        self.mrtrix_recon_config = MRtrix_recon_config(imaging_model=self.diffusion_imaging_model,recon_mode=self.diffusion_model)
        self.camino_recon_config = Camino_recon_config(imaging_model=self.diffusion_imaging_model)
        self.fsl_recon_config = FSL_recon_config()
        self.gibbs_recon_config = Gibbs_recon_config()
        self.dtk_tracking_config = DTK_tracking_config()
        self.dtb_tracking_config = DTB_tracking_config(imaging_model=self.diffusion_imaging_model)
        self.dipy_tracking_config = Dipy_tracking_config(imaging_model=self.diffusion_imaging_model,tracking_mode=self.diffusion_model,SD=self.mrtrix_recon_config.local_model)
        self.mrtrix_tracking_config = MRtrix_tracking_config(tracking_mode=self.diffusion_model,SD=self.mrtrix_recon_config.local_model)
        self.camino_tracking_config = Camino_tracking_config(imaging_model=self.diffusion_imaging_model,tracking_mode=self.diffusion_model)
        self.fsl_tracking_config = FSL_tracking_config()
        self.gibbs_tracking_config = Gibbs_tracking_config()

        #self.mrtrix_recon_config.on_trait_change(self.update_mrtrix_tracking_SD,'local_model')
        #self.on_trait_change(self._processing_tool_changed,'processing_tool')

        self.mrtrix_recon_config.on_trait_change(self.update_mrtrix_tracking_SD,'local_model')
        self.dipy_recon_config.on_trait_change(self.update_dipy_tracking_SD,'local_model')

        self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'model_type')
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_model,'local_model')
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'inversion')
        self.camino_recon_config.on_trait_change(self.update_camino_tracking_inversion,'fallback_index')

    def _tracking_processing_tool_changed(self,new):
        if new == 'MRtrix':
            self.mrtrix_recon_config.tracking_processing_tool = new
            # self.recon_processing_tool_editor = ['Dipy','MRtrix']
            # self.recon_processing_tool = new
            # self.recon_processing_tool_editor = ['Dipy','MRtrix']
        elif new == 'Dipy':
            self.dipy_recon_config.tracking_processing_tool = new
            # self.recon_processing_tool_editor = ['Dipy']
            # self.recon_processing_tool = new
        # else:
            # self.recon_processing_tool_editor = ['Custom']
            # self.recon_processing_tool = new


    def _diffusion_imaging_model_changed(self, new):
        self.dtk_recon_config.imaging_model = new
        self.mrtrix_recon_config.imaging_model = new
        self.dipy_recon_config.imaging_model = new
        #self.camino_recon_config.diffusion_imaging_model = new
        self.dtk_tracking_config.imaging_model = new
        self.dtb_tracking_config.imaging_model = new
        # Remove MRtrix from recon and tracking methods and Probabilistic from diffusion model if diffusion_imaging_model is DSI
        if new == 'DSI':
            #self.processing_tool = 'Dipy'
            #self.processing_tool_editor = ['Dipy']
            self.recon_processing_tool = 'Dipy'
            self.recon_processing_tool_editor = ['Dipy','Custom']
            self.tracking_processing_tool = 'Dipy'
            self.tracking_processing_tool_editor = ['Dipy','Custom']
            self.diffusion_model_editor = ['Deterministic','Probabilistic']
        else:
            # self.processing_tool_editor = ['DTK','MRtrix','Camino','FSL','Gibbs']
            #self.processing_tool_editor = ['Dipy','MRtrix']
            self.recon_processing_tool_editor = ['Dipy','MRtrix','Custom']
            self.tracking_processing_tool_editor = ['Dipy','MRtrix','Custom']
            #if self.processing_tool == 'DTK':
            #    self.diffusion_model_editor = ['Deterministic']
            #else:
            #    self.diffusion_model_editor = ['Deterministic','Probabilistic']
            if self.tracking_processing_tool == 'DTK':
                self.diffusion_model_editor = ['Deterministic']
            else:
                self.diffusion_model_editor = ['Deterministic','Probabilistic']

    # def _processing_tool_changed(self, new):
    #     print "processing_tool_changed"
    #     if new == 'DTK' or new == 'Gibbs':
    #         self.diffusion_model_editor = ['Deterministic']
    #         self.diffusion_model = 'Deterministic'
    #         self._diffusion_model_changed('Deterministic')
    #     elif new == "FSL":
    #         self.diffusion_model_editor = ['Probabilistic']
    #         self.diffusion_model = 'Probabilistic'
    #     elif new == "Dipy":
    #         self.diffusion_model_editor = ['Deterministic','Probabilistic']
    #         self.diffusion_model = 'Deterministic'
    #         # self.configure_traits(view='dipy_traits_view')
    #     elif new == "MRtrix":
    #         self.diffusion_model_editor = ['Deterministic','Probabilistic']
    #         self.diffusion_model = 'Deterministic'
            # self.configure_traits(view='mrtrix_traits_view')
        #self.edit_traits()
        #self.trait_view('traits_view').updated = True

    def _recon_processing_tool_changed(self, new):
        print "recon_processing_tool_changed"
        # self.tracking_processing_tool = new
        if new == 'Dipy':
            self.tracking_processing_tool_editor = ['Dipy','MRtrix','Custom']
        elif new == 'MRtrix':
            self.tracking_processing_tool_editor = ['MRtrix','Custom']
        elif new == 'Custom':
            self.tracking_processing_tool_editor = ['Custom']

    def _diffusion_model_changed(self,new):
        # self.mrtrix_recon_config.recon_mode = new # Probabilistic tracking only available for Spherical Deconvoluted data
        self.mrtrix_tracking_config.tracking_mode = new
        self.dipy_tracking_config.tracking_mode = new
        self.camino_tracking_config.tracking_mode = new
        self.update_camino_tracking_model()

    def update_mrtrix_tracking_SD(self,new):
        self.mrtrix_tracking_config.SD = new

    def update_dipy_tracking_SD(self,new):
        self.dipy_tracking_config.SD = new

    def update_camino_tracking_model(self):
        if self.diffusion_model == 'Probabilistic':
            self.camino_tracking_config.tracking_model = 'pico'
        elif self.camino_recon_config.model_type == 'Single-Tensor' or self.camino_recon_config.local_model == 'restore' or self.camino_recon_config.local_model == 'adc':
            self.camino_tracking_config.tracking_model = 'dt'
        elif self.camino_recon_config.local_model == 'ball_stick':
            self.camino_tracking_config.tracking_model = 'ballstick'
        else:
            self.camino_tracking_config.tracking_model = 'multitensor'

    def update_camino_tracking_inversion(self):
        self.camino_tracking_config.inversion_index = self.camino_recon_config.inversion
        self.camino_tracking_config.fallback_index = self.camino_recon_config.fallback_index


def strip_suffix(file_input, prefix):
    import os
    from nipype.utils.filemanip import split_filename
    path, _, _ = split_filename(file_input)
    return os.path.join(path, prefix+'_')

class DiffusionStage(Stage):

    def __init__(self):
        self.name = 'diffusion_stage'
        self.config = DiffusionConfig()
        self.inputs = ["diffusion","partial_volumes","wm_mask_registered","roi_volumes","grad","bvals","bvecs"]
        self.outputs = ["diffusion_model","track_file","fod_file","gFA","ADC","skewness","kurtosis","P0","roi_volumes","mapmri_maps"]


    def create_workflow(self, flow, inputnode, outputnode):
        # # resampling diffusion image and setting output type to short
        # fs_mriconvert = pe.Node(interface=fs.MRIConvert(out_type='nii',out_file='diffusion_resampled.nii'),name="diffusion_resample")
        # fs_mriconvert.inputs.vox_size = self.config.resampling
        # fs_mriconvert.inputs.resample_type = self.config.interpolation
        # flow.connect([(inputnode,fs_mriconvert,[('diffusion','in_file')])])

        # fs_mriconvert_wm_mask = pe.Node(interface=fs.MRIConvert(out_type='nii',resample_type='nearest',out_file='wm_mask_resampled.nii'),name="mask_resample")
        # fs_mriconvert_wm_mask.inputs.vox_size = self.config.resampling
        # flow.connect([(inputnode,fs_mriconvert_wm_mask,[('wm_mask_registered','in_file')])])

        # if self.config.processing_tool != 'DTK':

        #     fs_mriconvert_ROIs = pe.MapNode(interface=fs.MRIConvert(out_type='nii',resample_type='nearest'),name="ROIs_resample",iterfield=['in_file'])
        #     fs_mriconvert_ROIs.inputs.vox_size = self.config.resampling
        #     flow.connect([(inputnode,fs_mriconvert_ROIs,[('roi_volumes','in_file')])])

        #     if self.config.dilate_rois:
        #         dilate_rois = pe.MapNode(interface=fsl.DilateImage(),iterfield=['in_file'],name='dilate_rois')
        #         dilate_rois.inputs.operation = 'modal'
        #         flow.connect([
        #                       (fs_mriconvert_ROIs,dilate_rois,[("out_file","in_file")]),
        #                       (dilate_rois,outputnode,[("out_file","roi_volumes")])
        #                     ])
        #     else:
        #         flow.connect([
        #                     (fs_mriconvert_ROIs,outputnode,[("out_file","roi_volumes")])
        #                     ])
        # else:
        #     flow.connect([
        #                   (inputnode,outputnode,[("roi_volumes","roi_volumes")])
        #                 ])

        if self.config.recon_processing_tool != 'DTK':

            if self.config.dilate_rois:

                dilate_rois = pe.MapNode(interface=fsl.DilateImage(),iterfield=['in_file'],name='dilate_rois')
                dilate_rois.inputs.operation = 'modal'

                if self.config.dilation_kernel == 'Box':
                    kernel_size = 2*self.config.dilation_radius + 1
                    dilate_rois.inputs.kernel_shape = 'boxv'
                    dilate_rois.inputs.kernel_size = kernel_size
                else:
                    extract_sizes = pe.Node(interface=ExtractImageVoxelSizes(),name='extract_sizes')
                    flow.connect([
                                (inputnode,extract_sizes,[("diffusion","in_file")])
                                ])
                    extract_sizes.run()
                    print "Voxel sizes : ",extract_sizes.outputs.voxel_sizes

                    min_size = 100
                    for voxel_size in extract_sizes.outputs.voxel_sizes:
                        if voxel_size < min_size:
                            min_size = voxel_size

                    print("voxel size (min): %g"%min_size)
                    if self.confi.dilation_kernel == 'Gauss':
                        kernel_size = 2*extract_sizes.outputs.voxel_sizes + 1
                        sigma = kernel_size / 2.355 # FWHM criteria, i.e. sigma = FWHM / 2(sqrt(2ln(2)))
                        dilate_rois.inputs.kernel_shape = 'gauss'
                        dilate_rois.inputs.kernel_size = sigma
                    elif self.config.dilation_kernel == 'Sphere':
                        radius =  0.5*min_size + self.config.dilation_radius * min_size
                        dilate_rois.inputs.kernel_shape = 'sphere'
                        dilate_rois.inputs.kernel_size = radius

                flow.connect([
                            (inputnode,dilate_rois,[("roi_volumes","in_file")]),
                            (dilate_rois,outputnode,[("out_file","roi_volumes")])
                            ])
            else:
                flow.connect([
                            (inputnode,outputnode,[("roi_volumes","roi_volumes")])
                            ])
        else:
            flow.connect([
                          (inputnode,outputnode,[("roi_volumes","roi_volumes")])
                        ])

        # Reconstruction
        if self.config.recon_processing_tool == 'DTK':
            recon_flow = create_dtk_recon_flow(self.config.dtk_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion_resampled')]),
                        ])

        elif self.config.recon_processing_tool == 'Dipy':
            recon_flow = create_dipy_recon_flow(self.config.dipy_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (inputnode,recon_flow,[('bvals','inputnode.bvals')]),
                        (inputnode,recon_flow,[('bvecs','inputnode.bvecs')]),
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion_resampled')]),
                        (inputnode, recon_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
                        (recon_flow,outputnode,[("outputnode.FA","gFA")]),
                        (recon_flow,outputnode,[("outputnode.mapmri_maps","mapmri_maps")]),
                        ])

        elif self.config.recon_processing_tool == 'MRtrix':
            recon_flow = create_mrtrix_recon_flow(self.config.mrtrix_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (inputnode,recon_flow,[('grad','inputnode.grad')]),
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion_resampled')]),
			            (inputnode, recon_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
                        (recon_flow,outputnode,[("outputnode.FA","gFA")]),
                        (recon_flow,outputnode,[("outputnode.ADC","ADC")]),
                        ])

        elif self.config.recon_processing_tool == 'Camino':
            recon_flow = create_camino_recon_flow(self.config.camino_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion')]),
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion_resampled')]),
                        (inputnode, recon_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
                        (recon_flow,outputnode,[("outputnode.FA","gFA")])
                        ])

        elif self.config.recon_processing_tool == 'FSL':
            recon_flow = create_fsl_recon_flow(self.config.fsl_recon_config)
            flow.connect([
                        (inputnode,recon_flow,[('diffusion','inputnode.diffusion_resampled')]),
                        (inputnode, recon_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')])
                        ])

        elif self.config.recon_processing_tool == 'Gibbs':
            recon_flow = create_gibbs_recon_flow(self.config.gibbs_recon_config)
            flow.connect([
                          (inputnode,recon_flow,[("diffusion","inputnode.diffusion_resampled")])
                        ])

        # Tracking
        if self.config.tracking_processing_tool == 'DTK':
            track_flow = create_dtb_tracking_flow(self.config.dtb_tracking_config)
            flow.connect([
                        (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_registered')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')])
                        ])

        elif self.config.tracking_processing_tool == 'Dipy':
            track_flow = create_dipy_tracking_flow(self.config.dipy_tracking_config)
            flow.connect([
                        (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
                        (recon_flow, outputnode,[('outputnode.DWI','fod_file')]),
                        (recon_flow, track_flow,[('outputnode.model','inputnode.model')]),
                        (inputnode,track_flow,[('bvals','inputnode.bvals')]),
                        (inputnode,track_flow,[('bvecs','inputnode.bvecs')]),
                        (inputnode,track_flow,[('diffusion','inputnode.DWI')]), # Diffusion resampled
                        (inputnode,track_flow,[('partial_volumes','inputnode.partial_volumes')]),
                        # (inputnode, track_flow,[('diffusion','inputnode.DWI')]),
                        (recon_flow,track_flow,[("outputnode.FA","inputnode.FA")]),
                        (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')])
                        # (recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                        ])

            flow.connect([
                        (track_flow,outputnode,[('outputnode.track_file','track_file')])
                        ])

        elif self.config.tracking_processing_tool == 'MRtrix' and self.config.recon_processing_tool == 'MRtrix':
            track_flow = create_mrtrix_tracking_flow(self.config.mrtrix_tracking_config)
            flow.connect([
                        (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
                        (recon_flow, outputnode,[('outputnode.DWI','fod_file')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI'),('outputnode.grad','inputnode.grad')]),
                        (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')])
			             #(recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                        ])

            flow.connect([
                        (track_flow,outputnode,[('outputnode.track_file','track_file')])
                        ])

        elif self.config.tracking_processing_tool == 'MRtrix' and self.config.recon_processing_tool == 'Dipy':
            track_flow = create_mrtrix_tracking_flow(self.config.mrtrix_tracking_config)
            flow.connect([
                        (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_resampled'),('grad','inputnode.grad')]),
                        (recon_flow, outputnode,[('outputnode.DWI','fod_file')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI')]),
                        (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')])
			             #(recon_flow, track_flow,[('outputnode.SD','inputnode.SD')]),
                        ])

           #  if self.config.diffusion_model == 'Probabilistic':
           #      flow.connect([
    			    # (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')]),
    			    # ])

            flow.connect([
                        (track_flow,outputnode,[('outputnode.track_file','track_file')])
                        ])

        elif self.config.tracking_processing_tool == 'Camino':
            track_flow = create_camino_tracking_flow(self.config.camino_tracking_config)
            flow.connect([
                        (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
                        (recon_flow, track_flow,[('outputnode.DWI','inputnode.DWI'), ('outputnode.grad','inputnode.grad')])
                        ])
            if self.config.diffusion_model == 'Probabilistic':
                flow.connect([
                    (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')]),
                    ])
            flow.connect([
                        (track_flow,outputnode,[('outputnode.track_file','track_file')])
                        ])

        elif self.config.tracking_processing_tool == 'FSL':
            track_flow = create_fsl_tracking_flow(self.config.fsl_tracking_config)
            flow.connect([
                        (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
                        (dilate_rois,track_flow,[('out_file','inputnode.gm_registered')]),
                        (recon_flow,track_flow,[('outputnode.fsamples','inputnode.fsamples')]),
                        (recon_flow,track_flow,[('outputnode.phsamples','inputnode.phsamples')]),
                        (recon_flow,track_flow,[('outputnode.thsamples','inputnode.thsamples')]),
                        ])
            flow.connect([
                        (track_flow,outputnode,[("outputnode.targets","track_file")]),
                        ])
        elif self.config.tracking_processing_tool == 'Gibbs':
            track_flow = create_gibbs_tracking_flow(self.config.gibbs_tracking_config)
            flow.connect([
                          (inputnode, track_flow,[('wm_mask_registered','inputnode.wm_mask_resampled')]),
                          (recon_flow,track_flow,[("outputnode.recon_file","inputnode.recon_file")]),
                          (track_flow,outputnode,[('outputnode.track_file','track_file')])
                        ])


        if self.config.tracking_processing_tool == 'DTK':
            flow.connect([
			    (recon_flow,outputnode, [("outputnode.gFA","gFA"),("outputnode.skewness","skewness"),
			                             ("outputnode.kurtosis","kurtosis"),("outputnode.P0","P0")]),
			    (track_flow,outputnode, [('outputnode.track_file','track_file')])
			    ])

        temp_node = pe.Node(interface=util.IdentityInterface(fields=["diffusion_model"]),name="diffusion_model")
        temp_node.inputs.diffusion_model = self.config.diffusion_model
        flow.connect([
                    (temp_node,outputnode,[("diffusion_model","diffusion_model")])
                    ])

        if self.config.tracking_processing_tool == 'Custom':
            # FIXME make sure header of TRK / TCK are consistent with DWI
            custom_node = pe.Node(interface=util.IdentityInterface(fields=["custom_track_file"]),name="read_custom_track")
            custom_node.inputs.custom_track_file = self.config.custom_track_file
            if nib.streamlines.detect_format(self.config.custom_track_file) is nib.streamlines.TrkFile:
                print "load TRK tractography file"
                flow.connect([
                            (custom_node,outputnode,[("custom_track_file","track_file")])
                            ])
            elif nib.streamlines.detect_format(self.config.custom_track_file) is nib.streamlines.TckFile:
                print "load TCK tractography file and convert to TRK format"
                converter = pe.Node(interface=Tck2Trk(),name="trackvis")
                converter.inputs.out_tracks = 'converted.trk'

                flow.connect([
                    (custom_node,converter,[('custom_track_file','in_tracks')]),
                    (inputnode,converter,[('wm_mask_registered','in_image')]),
                    (converter,outputnode,[('out_tracks','track_file')])
                    ])
            else:
                print "Invalid tractography input format. Valid formats are .tck (MRtrix) and .trk (DTK/Trackvis)"

    def define_inspect_outputs(self):
        print "stage_dir : %s" % self.stage_dir

        # if self.config.processing_tool == 'DTK':
        #     diff_results_path = os.path.join(self.stage_dir,"tracking","dtb_streamline","result_dtb_streamline.pklz")
        #     if(os.path.exists(diff_results_path)):
        #         diff_results = pickle.load(gzip.open(diff_results_path))
        #         self.inspect_outputs_dict['DTK streamline'] = ['trackvis',diff_results.outputs.out_file]

        if self.config.tracking_processing_tool == 'Dipy':
            if self.config.mrtrix_recon_config.local_model:
                if self.config.diffusion_model == 'Deterministic':
                    diff_results_path = os.path.join(self.stage_dir,"tracking","dipy_deterministic_tracking","result_dipy_deterministic_tracking.pklz")
                    if os.path.exists(diff_results_path):
                        diff_results = pickle.load(gzip.open(diff_results_path))
                        streamline_res = diff_results.outputs.tracks
                        self.inspect_outputs_dict[self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = ['trackvis',streamline_res]
                if self.config.diffusion_model == 'Probabilistic':
                    diff_results_path = os.path.join(self.stage_dir,"tracking","dipy_probabilistic_tracking","result_dipy_probabilistic_tracking.pklz")
                    if os.path.exists(diff_results_path):
                        diff_results = pickle.load(gzip.open(diff_results_path))
                        streamline_res = diff_results.outputs.tracks
                        self.inspect_outputs_dict[self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = ['trackvis',streamline_res]
            else:
                diff_results_path = os.path.join(self.stage_dir,"tracking","dipy_dtieudx_tracking","result_dipy_dtieudx_tracking.pklz")
                if os.path.exists(diff_results_path):
                    diff_results = pickle.load(gzip.open(diff_results_path))
                    streamline_res = diff_results.outputs.tracks
                    self.inspect_outputs_dict[self.config.tracking_processing_tool + ' Tensor-based EuDX streamline'] = ['trackvis',streamline_res]


        elif self.config.tracking_processing_tool == "MRtrix":
            if self.config.diffusion_model == 'Deterministic':
                diff_results_path = os.path.join(self.stage_dir,"tracking","trackvis","result_trackvis.pklz")
                if os.path.exists(diff_results_path):
                    diff_results = pickle.load(gzip.open(diff_results_path))
                    streamline_res = diff_results.outputs.out_tracks
                    print streamline_res
                    self.inspect_outputs_dict[self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = ['trackvis',streamline_res]
            elif self.config.diffusion_model == 'Probabilistic':
                diff_results_path = os.path.join(self.stage_dir,"tracking","trackvis","mapflow","_trackvis0","result__trackvis0.pklz")
                print diff_results_path
                if os.path.exists(diff_results_path):
                    diff_results = pickle.load(gzip.open(diff_results_path))
                    streamline_res = diff_results.outputs.out_tracks
                    print streamline_res
                    self.inspect_outputs_dict[self.config.tracking_processing_tool + ' ' + self.config.diffusion_model + ' streamline'] = ['trackvis',streamline_res]

            if self.config.mrtrix_recon_config.local_model:

                RF_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_rf","result_mrtrix_rf.pklz")
                if(os.path.exists(RF_path)):
                    RF_results = pickle.load(gzip.open(RF_path))
                    self.inspect_outputs_dict['MRTRIX Response function'] = ['shview','-response',RF_results.outputs.response]

                CSD_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_CSD","result_mrtrix_CSD.pklz")
                tensor_path = os.path.join(self.stage_dir,"reconstruction","mrtrix_make_tensor","result_mrtrix_make_tensor.pklz")
                if(os.path.exists(CSD_path) and os.path.exists(tensor_path)):
                    CSD_results = pickle.load(gzip.open(CSD_path))
                    self.inspect_outputs_dict['MRTrix Spherical Harmonics image'] = ['mrview',CSD_results.outputs.spherical_harmonics_image]
                    Tensor_results = pickle.load(gzip.open(tensor_path))
                    self.inspect_outputs_dict['MRTrix SH/tensor images'] = ['mrview',CSD_results.outputs.spherical_harmonics_image,'-odf.load_tensor',Tensor_results.outputs.tensor]
                    self.inspect_outputs = self.inspect_outputs_dict.keys()

                FA_path = os.path.join(self.stage_dir,"reconstruction","convert_FA","result_convert_FA.pklz")
                if(os.path.exists(FA_path)):
                    FA_results = pickle.load(gzip.open(FA_path))
                    self.inspect_outputs_dict['MRTrix FA'] = ['mrview',FA_results.outputs.converted]


        # else:
        #     if self.config.diffusion_model == 'Deterministic':
        #         diff_results_path = os.path.join(self.stage_dir,"tracking","trackvis","result_trackvis.pklz")
        #         FA_path = os.path.join(self.stage_dir,"reconstruction","convert_FA","result_convert_FA.pklz")
        #         if os.path.exists(diff_results_path):
        #             diff_results = pickle.load(gzip.open(diff_results_path))
        #             streamline_res = diff_results.outputs.trackvis
        #             self.inspect_outputs_dict[self.config.processing_tool + ' streamline'] = ['trackvis',streamline_res]

        self.inspect_outputs = sorted( [key.encode('ascii','ignore') for key in self.inspect_outputs_dict.keys()],key=str.lower)




    def has_run(self):
        # if self.config.processing_tool == 'DTK':
        #     return os.path.exists(os.path.join(self.stage_dir,"tracking","dtb_streamline","result_dtb_streamline.pklz"))
        if self.config.tracking_processing_tool == 'Dipy':
            if self.config.diffusion_model == 'Deterministic':
                return os.path.exists(os.path.join(self.stage_dir,"tracking","dipy_deterministic_tracking","result_dipy_deterministic_tracking.pklz"))
            elif self.config.diffusion_model == 'Probabilistic':
                return os.path.exists(os.path.join(self.stage_dir,"tracking","dipy_probabilistic_tracking","result_dipy_probabilistic_tracking.pklz"))
        elif self.config.tracking_processing_tool == 'MRtrix':
            return os.path.exists(os.path.join(self.stage_dir,"tracking","trackvis","result_trackvis.pklz"))
        # elif self.config.processing_tool == 'Camino':
        #     return os.path.exists(os.path.join(self.stage_dir,"tracking","trackvis","result_trackvis.pklz"))
        # elif self.config.processing_tool == 'FSL':
        #     return os.path.exists(os.path.join(self.stage_dir,"tracking","probtrackx","result_probtrackx.pklz"))
        # elif self.config.processing_tool == 'Gibbs':
        #     return os.path.exists(os.path.join(self.stage_dir,"reconstruction","match_orientations","result_match_orientations.pklz"))

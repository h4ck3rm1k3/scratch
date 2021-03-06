
#-------------------------------------------------------------------------------
#
# Copyright (c) 2009, IMB, RWTH Aachen.
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD
# license included in simvisage/LICENSE.txt and may be redistributed only
# under the conditions described in the aforementioned license.  The license
# is also available online at http://www.simvisage.com/licenses/BSD.txt
#
# Thanks for using Simvisage open source!
#
# Created on Jul 10, 2010 by: rch


from enthought.traits.api import \
    HasTraits, Float, Array, implements, Property, cached_property, Instance, Enum, \
    Dict, Bool, Int, List

from numpy import \
    array, tensordot, dot, zeros, c_, ix_, mgrid, arange, \
    where, sum, sin, cos, vstack, hstack, argmax, newaxis, size, \
    shape, fabs

from os.path import join

from math import pi

from ibvpy.api import \
    TStepper as TS, RTraceGraph, RTraceDomainListField, TLoop, \
    TLine, BCDof, BCDofGroup, BCSlice, IBVModel

from ibvpy.rtrace.rt_domain_list_field import \
    RTraceDomainListField

#from ibvpy.mats.mats2D.mats2D_elastic.mats2D_elastic import \
#    MATS2DElastic
from ibvpy.mats.mats1D5.mats1D5bond import \
    MATS1D5Bond
from ibvpy.mats.mats3D.mats3D_elastic.mats3D_elastic import \
    MATS3DElastic
from ibvpy.mats.mats3D.mats3D_sdamage.mats3D_sdamage import \
    MATS3DScalarDamage
from ibvpy.mats.mats3D.mats3D_cmdm.mats3D_cmdm import \
    MATS3DMicroplaneDamage
from ibvpy.mats.mats2D5.mats2D5_cmdm.mats2D5_cmdm import \
    MATS2D5MicroplaneDamage, PhiFnGeneral, PhiFnStrainHardening

from ibvpy.fets.fets_eval import \
    FETSEval
from ibvpy.fets.fets3D.fets3D8h import \
    FETS3D8H
from ibvpy.fets.fets3D.fets3D8h20u import \
    FETS3D8H20U
from ibvpy.fets.fets3D.fets3D8h27u import \
    FETS3D8H27U
from ibvpy.fets.fets2D5.fets2D58h import \
    FETS2D58H
from ibvpy.fets.fets2D5.fets2D58h20u import \
    FETS2D58H20U

from ibvpy.mesh.fe_grid import \
    FEGrid

from ibvpy.mesh.fe_refinement_grid import \
    FERefinementGrid

from ibvpy.mesh.fe_domain import \
    FEDomain

from mathkit.mfn.mfn_line.mfn_line import MFnLineArray
from numpy import array, tensordot, dot, zeros, c_, ix_, unique
from ibvpy.mats.mats3D.mats3D_tensor import map3d_sig_eng_to_mtx
from math import sqrt, asin, acos

from simiter.sim_pstudy import ISimModel, SimOut, SimPStudy

from math import fabs as float_abs

class Hypar( HasTraits ):

    lx = Float( 1.0 )
    ly = Float( 1.0 )
    z00 = Float( 0.0 )
    z11 = Float( 0.2 )
    z01 = Float( 0.1 )
    z10 = Float( 0.1 )
    thickness = Float( 0.01 )

    def __call__( self, X_arr ):

        # derive the function

        xi, yi, zi = X_arr[:, 0], X_arr[:, 1], X_arr[:, 2]

        # number of local grid points for each coordinate direction
        # values must range between 0 and 1

        x = ( xi ) * self.lx
        y = ( yi ) * self.ly
        z = ( -( self.z00 - self.z10 ) / self.lx * x -
               ( self.z00 - self.z01 ) / self.ly * y +
               ( self.z00 - self.z10 - self.z01 + self.z11 ) / ( self.lx * self.ly ) * x * y +
               self.z00 ) + zi * self.thickness

        return c_[ x, y, z ]


class HyparModel( IBVModel ):
    '''SFB - Demontrator model specification.
    '''
    implements( ISimModel )

    # number of elements in all dims
    n_dofs_xy = Int( 16, ps_levels = ( 10, 30, 3 ) )

    shape_xy = Property
    def _get_shape_xy( self ):
        if self.fets == self.fe_linear:
            return self.n_dofs_xy - 1
        elif self.fets == self.fe_quad_serendipity \
            or self.fets == self.fe2d5_quad_serendipity \
            or self.fets == self.fe_quad_lagrange:
            return int( self.n_dofs_xy / 2 )
        else:
            raise ValueError

    shape_z = Int( 1, ps_levels = ( 1, 3, 1 ) )

    # dimensions of the shell structure
    length_xy = Float( 1.0, ps_levels = ( 4.0, 5.0, 3 ) ) # [m]
    length_z = Float( 0.01, ps_levels = ( 1.0, 2.0, 4 ) ) # [m]

    E = Float( 28700 ) # [MPa]
    nu = Float( 0.2 ) # [-]

    # variable type of the finite element
    fets = Instance( FETSEval,
                     ps_levels = [ 'fe_linear',
                                  'fe2d5_quad_serendipity',
                                  'fe_quad_serendipity',
                                  'fe_quad_lagrange' ] )
    def _fets_default( self ):
        return self.fe_linear
#        return self.fe2d5_quad_serendipity

    mats = Instance( MATS3DElastic )
    def _mats_default( self ):
        return MATS3DElastic( E = self.E, nu = self.nu )

    fe_linear = Instance( FETSEval, transient = True )
    def _fe_linear_default( self ):
        return FETS3D8H( mats_eval = self.mats )

    fe_quad_serendipity = Instance( FETSEval, transient = True )
    def _fe_quad_serendipity_default( self ):
        return FETS3D8H20U( mats_eval = self.mats )

    fe2d5_quad_serendipity = Instance( FETSEval, transient = True )
    def _fe2d5_quad_serendipity_default( self ):
        return FETS2D58H20U( mats_eval = self.mats )

    fe_quad_lagrange = Instance( FETSEval, transient = True )
    def _fe_quad_lagrange_default( self ):
        return FETS3D8H27U( mats_eval = self.mats )

    def get_sim_outputs( self ):
        '''
        Specifies the results and their order returned by the model
        evaluation.
        '''
        return [ SimOut( name = 'u_z_free_corner', unit = 'm' ),
                 SimOut( name = 'maximum principle stress', unit = 'MPa' ), ]

    def peval( self ):
        '''
        Evaluate the model and return the array of results specified
        in the method get_sim_outputs.
        '''
        U = self.tloop.eval()

        u_center_top_z = U[ self.center_top_dof ][0, 0, 2]

        max_princ_stress = max( self.max_princ_stress._get_field_data().flatten() )

        return array( [ u_center_top_z, max_princ_stress ],
                        dtype = 'float_' )

    tline = Instance( TLine )
    def _tline_default( self ):
        return TLine( min = 0.0, step = 1.0, max = 1.0 )

    max_princ_stress = Instance( RTraceDomainListField )
    def _max_princ_stress_default( self ):
        return RTraceDomainListField( name = 'max principle stress' , idx = 0,
                                      var = 'max_principle_sig', warp = True,
                                      record_on = 'update', )

    rtrace_list = List
    def _rtrace_list_default( self ):
        return [  self.max_princ_stress,
                            RTraceDomainListField( name = 'Epsilon 0' ,
                                   var = 'eps0_app',
                                   record_on = 'update' ),
#                                 RTraceDomainListField( name = 'Displacement' ,
#                                                var = 'u', idx = 0, warp = True ),
                                 RTraceDomainListField( name = 'Stress' ,
                                                var = 'sig_app', idx = 0, warp = True,
                                                record_on = 'update', ),
                                                ]

    hypar = Property( Instance( Hypar ) )
    @cached_property
    def _get_hypar( self ):
        return Hypar( lx = self.length_xy,
                      ly = self.length_xy,
                      thickness = self.length_z )


    fe_domain = Property( Instance( FEDomain ) )
    @cached_property
    def _get_fe_domain( self ):

        fets_4u = FETS3D8H( mats_eval = MATS3DElastic( E = 10 ) )

        # Discretization
        fe_domain = FEDomain()

        fe_rgrid = FERefinementGrid( domain = fe_domain, fets_eval = self.fets )

        fe_grid = FEGrid( level = fe_rgrid,
                          coord_min = ( 0, 0, 0 ),
                          coord_max = ( 1.0, 1.0, 1.0 ),
                          geo_transform = self.hypar,
                          shape = ( self.shape_xy, self.shape_xy, self.shape_z ),
                          fets_eval = self.fets )


        return fe_domain

    # time loop
    tloop = Property( depends_on = '+ps_levels' )
    @cached_property
    def _get_tloop( self ):

        self.fets.vtk_r *= 0.95

        domain = self.fe_domain
        fe_grid = domain.subdomains[0].fe_subgrids[0]

        self.center_top_dof = fe_grid[-1, -1, -1, -1, -1, -1].dofs

        #----------------------------------------------------
        # loading cases (LC):
        #----------------------------------------------------

        #--- LC1: dead load
        # g = 22.4 kN/m^3 
        # orientation: global z-direction; 
        material_density = -0.0224 # [MN/m^3]

        #--- LC2 additional dead load 
        # gA = 0,20 kN/m^2 
        # orientation: global z-direction (following the curved structure); 
        surface_load_gA = -0.20e-3 # [MN/m^2]

        #--- LC3 snow
        # s = 0,79 kN/m^2 
        # orientation: global z-direction (projection); 
        surface_load_s = -0.79e-3 # [MN/m^2]

        #--- LC4 wind (pressure) 
        # w = 0,13 kN/m^2 
        # orientation: local t-direction (surface normal); 
        surface_load_w = -0.13e-3 # [MN/m^2]

        # NOTE: additional line-loads at the edge of the roof need to be considered!  

        upper_surface = fe_grid[:, :, -1, :, :, -1]
        whole_domain = fe_grid[:, :, :, :, :, :]

        force_bc = [
                     # LC1: dead load
                     BCSlice( var = 'f', value = material_density, dims = [2],
                              integ_domain = 'global',
                              slice = whole_domain ),
                     # LC3: snow load         
                     BCSlice( var = 'f', value = surface_load_s, dims = [2],
                              integ_domain = 'global',
                              slice = upper_surface )
                   ]

        bc_fix_yz = BCSlice( var = 'u', value = 0, dims = [1, 2], slice = fe_grid[:, 0, 0, :, 0, 0] )
        bc_fix_xz = BCSlice( var = 'u', value = 0, dims = [0, 2], slice = fe_grid[0, :, 0, 0, :, 0] )

        bc_list = [ bc_fix_xz, bc_fix_yz ] + force_bc

        w_z = fe_grid[-1, -1, -1, -1, -1, -1].dofs[0, 0, 2]

        self.f_w_diagram = RTraceGraph( name = 'load - corner deflection',
                                           var_x = 'U_k', idx_x = w_z,
                                           var_y = 'time', idx_y = 0,
                                           record_on = 'update' )

        rtrace_list = [ self.f_w_diagram ] + self.rtrace_list

        ts = TS( sdomain = domain,
                 dof_resultants = True,
                 bcond_list = bc_list,
                 rtrace_list = rtrace_list
               )

        # Add the time-loop control
        tloop = TLoop( tstepper = ts,
                       tolerance = 1e-4,
                       tline = self.tline )

        return tloop

if __name__ == '__main__':

    sim_model = HyparModel( n_dofs_xy = 10, shape_z = 1 )
#    interior_elems = sim_model.fe_grid[ 1:-1, 1:-1, 1:-1, :, :, : ].elems
#    sim_model.fe_grid.inactive_elems = list( interior_elems )
    print sim_model.tloop

    do = 'ui'

    if do == 'eval':
        print 'eval', sim_model.peval()

    if do == 'ui':

        print 'eval', sim_model.peval()
        from ibvpy.plugins.ibvpy_app import IBVPyApp
        app = IBVPyApp( ibv_resource = sim_model )
        app.main()

    elif do == 'ps':

        sim_ps = SimPStudy( sim_model = sim_model )
        sim_ps.configure_traits()

    elif do == 'pickle':

        import pickle
        filename = '/tmp/sim.pickle'
        file = open( filename, 'w' )
        pickle.dump( sim_model, file )
        file.close()
        file = open( filename, 'r' )
        sm = pickle.load( file )
        file.close()


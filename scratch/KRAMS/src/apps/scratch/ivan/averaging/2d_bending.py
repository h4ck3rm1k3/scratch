from ibvpy.core.api import \
    TStepper as TS, RTraceGraph, TLoop, \
    TLine, BCDof, IBVPSolve as IS

from ibvpy.api import MGridDomain, RTraceDomainField

from ibvpy.fets.fets2D.fets2D4q9u import  FETS2D4Q9U
#from lib.fets.fets2D.fets2D4q8u import  FETS2D4Q8U
#from lib.fets.fets2D.fets2D9q import  FETS2D9Q
#from averaging import UniformDomainAveraging, LinearAF, QuarticAF
from ibvpy.api import DOTSEval
from ibvpy.mats.mats2D.mats2D_sdamage.mats2D_sdamage import MATS2DScalarDamage
from ibvpy.mats.mats2D.mats2D_sdamage.strain_norm2d import Energy, Euclidean, Mises, Rankine, Mazars
from ibvpy.mats.mats_proxy import MATSProxy
from mathkit.geo.geo_ndgrid import GeoNDGrid
from mathkit.mfn.mfn_ndgrid.mfn_ndgrid import MFnNDGrid, GridPoint

#fets_eval = FETS2D4Q9U(mats_eval = MATS2DScalarDamage(E = 34e3,
#                                               nu = 0.2,
#                                               epsilon_0 = 59e-6,
#                                               epsilon_f = 1.e-3,
#                                               #stiffness  = "algorithmic",
#                                               strain_norm = Mazars()))
#                                               #stiffness  = "algorithmic"))

length = 1.
heigth = 0.5

##mp = MATSProxy( mats_eval_type = 'MATS2DScalarDamage')
#mp = MATSProxy( mats_eval = MATS2DScalarDamage(E = 34e3,
#                                               nu = 0.2,
#                                               epsilon_0 = 59e-6,
#                                               epsilon_f = 3.2e-5,
#                                               #stiffness  = "algorithmic",
#                                               strain_norm_type = 'Mazars'))
#                                               #stiffness  = "algorithmic")))
#mp.varpars['epsilon_0'].switch = 'varied'
#mp.varpars['epsilon_0'].spatial_fn = MFnNDGrid( shape = (8,5,1),
#                                    active_dims = ['x', 'y'],
#                                    x_mins = GridPoint( x = 0., y = 0. ),
#                                    x_maxs = GridPoint( x = length, y = heigth ) )
#mp.varpars['epsilon_0'].spatial_fn.set_values_in_box( 500., [0,0,0], [0.2,0.2,0.] )
#mp.varpars['epsilon_0'].spatial_fn.set_values_in_box( 500., [0.8,0,0], [1.,0.2,0.] )
#mp.varpars['epsilon_0'].spatial_fn.set_values_in_box( 50., [0.,0.46,0], [1.,0.5,0.] )



fets_eval = FETS2D4Q9U( mats_eval = mp )
#fets_eval = FETS2D4Q9U()

# Tseval for a discretized line domain
#
#tseval  = UniformDomainAveraging( fets_eval = fets_eval,
#                                  correction = True ,\
#                                  avg_function = QuarticAF(Radius = 0.2))
tseval = DOTSEval( fets_eval = fets_eval )

# Discretization
#
#line_domain = MGridDomain( lengths = (1.,1.,0.), shape = (1,1,0), n_nodal_dofs = 2 ) 

from ibvpy.mesh.mgrid_domain import MeshGridAdaptor

mgrid_adaptor = MeshGridAdaptor( n_nodal_dofs = 2,
                                 n_e_nodes_geo = ( 1, 1, 0 ),
                                 n_e_nodes_dof = ( 2, 2, 0 ),
                                 node_map_geo = [0, 1, 3, 2],
                                 node_map_dof = [0, 2, 8, 6, 1, 5, 7, 3, 4] )

domain = MGridDomain( lengths = ( length, heigth, 0. ),
                          shape = ( 8, 4, 0 ),
                          adaptor = mgrid_adaptor )

# Put the tseval (time-stepper) into the spatial context of the
# discretization and specify the response tracers to evaluate there.
#

ts = TS( tse = tseval,
     sdomain = domain,
         bcond_list = [ BCDof( var = 'u', dof = i, value = 0. ) for i in [domain.get_bottom_left_dofs()[0, 0]]  ] +
                    [ BCDof( var = 'u', dof = i, value = 0. ) for i in [domain.get_bottom_left_dofs()[0, 1]] ] +
                    [ BCDof( var = 'u', dof = i, value = 0. ) for i in [domain.get_bottom_right_dofs()[0, 1]] ] +
                    [ BCDof( var = 'u', dof = i, value = -1.2e-4 ) for i in [domain.get_top_middle_dofs()[0, 1]] ],
     rtrace_list = [
                        RTraceGraph( name = 'Fi,right over u_right (iteration)' ,
                      var_y = 'F_int', idx_y = domain.get_bottom_left_dofs()[0, 0],
                      var_x = 'U_k', idx_x = domain.get_bottom_left_dofs()[0, 0],
                      record_on = 'update' ),
#                      RTraceDomainField(name = 'Flux field' ,
#                      var = 'eps', idx = 0,
#                      record_on = 'update'),
              RTraceDomainField( name = 'Deformation' ,
              var = 'u', idx = 1,
              record_on = 'update',
              warp = True ),
              RTraceDomainField( name = 'Damage' ,
              var = 'omega', idx = 0,
              record_on = 'update',
              warp = True ),
              RTraceDomainField( name = 'Stress' ,
              var = 'sig_app', idx = 0,
              record_on = 'update',
              warp = False ),
#                      RTraceDomainField(name = 'N0' ,
#                                     var = 'N_mtx', idx = 2,
#                                     record_on = 'update')
#                      
         ]
     )

# Add the time-loop control

tl = TLoop( tstepper = ts,
     DT = .05,
     tline = TLine( min = 0.0, max = .1 ),
     tolerance = 1e-5 )
if __name__ == '__main__':
    tl.eval()
    # Put the whole stuff into the simulation-framework to map the
    # individual pieces of definition into the user interface.
    #
    from ibvpy.plugins.ibvpy_app import IBVPyApp
    app = IBVPyApp( ibv_resource = tl )
    app.main()

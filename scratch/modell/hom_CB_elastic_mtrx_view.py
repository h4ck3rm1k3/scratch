
from enthought.traits.api import HasTraits, Int, Float, Str, Property, Range, Array
from etsproxy.traits.ui.api import ModelView, View, Item, Label
from enthought.chaco.chaco_plot_editor import ChacoPlotItem
from etsproxy.traits.api import Instance, cached_property 
import numpy as np
from spirrid.rv import RV
from scipy.optimize import brentq, fminbound, newton
from scipy.integrate import cumtrapz
from mathkit.mfn.mfn_line.mfn_line import MFnLineArray
import time
from scipy.optimize import minimize
from scipy.interpolate import interp1d
from hom_CB_elastic_mtrx import CompositeCrackBridge
from matplotlib import pyplot as plt

# from quaducom.meso.homogenized_crack_bridge.elastic_matrix.hom_CB_elastic_mtrx_py_loop import CompositeCrackBridgeLoop


class CompositeCrackBridgeView( ModelView ):

    model = Instance( CompositeCrackBridge )
    
    results = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_results( self ):
        # if self.model.w <= 0.0:
        #    self.model.w = 1e-15
        self.model.damage
        sigma_c = np.sum( self.model._epsf0_arr * self.model.Kf * ( 1. - self.model.damage ) )
        # condition = ( np.sum( self.model.damage[self.model.c_mask] ) / np.sum( self.model.c_mask ) > 1 - 1e-12 )
        Kf_broken = np.sum( self.model.sorted_V_f * self.model.sorted_nu_r * \
            self.model.sorted_stats_weights * self.model.sorted_E_f * self.model.damage )
        E_mtrx = ( 1. - self.model.V_f_tot ) * self.model.E_m + Kf_broken
        x_arr, epsm_arr = self.filter( self.model._x_arr, self.model._epsm_arr )
        mu_epsf_arr = ( sigma_c - E_mtrx * epsm_arr ) / ( self.model.E_c - E_mtrx )
        # if condition:
        #    sigma_c = 1e-6
        #    mu_epsf_arr = 1e-6 * np.ones_like( mu_epsf_arr )
        #    E_mtrx = self.model.E_m * np.ones_like( mu_epsf_arr )
        # Kf_broken = np.sum( self.model.sorted_V_f * self.model.sorted_nu_r * \
        #    self.model.sorted_stats_weights * self.model.sorted_E_f * self.model.damage )
        # mu_epsf_arr = np.maximum( mu_epsf_arr, self.model._epsm_arr )
        
        epsm_arr = np.minimum( mu_epsf_arr, epsm_arr )
        epsm_arr = np.minimum( epsm_arr, np.ones_like( epsm_arr ) * max( epsm_arr[-1], epsm_arr[0] ) ) 
        if self.model.Ll > self.model.Lr:
            return -x_arr[::-1], epsm_arr[::-1], sigma_c, mu_epsf_arr[::-1], E_mtrx
        else:
            return x_arr, epsm_arr, sigma_c, mu_epsf_arr, E_mtrx

    d_int = Int( 1 )
    def filter_mask( self, length ):
        filter_level = self.d_int
        base = np.hstack( ( np.repeat( 0, filter_level - 1 ), 1 ) )
        mpc = length / filter_level
        rest = length % filter_level
        return np.hstack( ( np.tile( base, mpc ), np.ones( rest ) ) )
        
    def filter( self, x_arr, epsm_arr ):
        # cut at both ends
        # mask_r = x_arr[-1] == x_arr
        # mask_l = x_arr[0] == x_arr
        # r_stop = np.argmax( mask_r ) + 1
        # l_stop = len( mask_r ) - 1 - np.argmax( mask_l[::-1] )
        # x_cut = x_arr[l_stop:r_stop]
        # epsm_cut = epsm_arr[l_stop:r_stop]
        x_cut = x_arr
        epsm_cut = epsm_arr
        ix_0 = np.argmin( np.abs( x_cut ) )
        mask_l = self.filter_mask( len( x_cut[:ix_0] ) - 1 )
        mask_r = self.filter_mask( len( x_cut[ix_0 + 1:] ) - 1 )
        full_mask = np.hstack( ( 1, mask_l, 1, mask_r, 1 ) )
        full_mask = full_mask.astype( bool )
        return x_cut[full_mask], epsm_cut[full_mask]

    x_arr = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_x_arr( self ):
        return self.results[0]
 
    epsm_arr = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_epsm_arr( self ):
        return self.results[1]

    sigma_c = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_sigma_c( self ):
        return self.results[2]

    mu_epsf_arr = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_mu_epsf_arr( self ):
        return self.results[3]

    w_evaluated = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_w_evaluated( self ):
        return np.trapz( self.mu_epsf_arr - self.epsm_arr, self.x_arr )

    def sigma_c_arr( self, w_arr, u = False ):
        sigma_c_lst = []
        u_lst = []
        for w in w_arr:
            self.model.w = w
            sigma_c_lst.append( self.sigma_c )
            if u == True:
                u_lst.append( self.u_evaluated )
        if u == True:
            return np.array( sigma_c_lst ), np.array( u_lst )
        return np.array( sigma_c_lst )

    u_evaluated = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_u_evaluated( self ):
        u_debonded = np.trapz( self.mu_epsf_arr , self.x_arr )
        u_compact = ( ( self.model.Ll - np.abs( self.x_arr[0] ) ) * self.mu_epsf_arr[0]
                    + ( self.model.Lr - np.abs( self.x_arr[-1] ) ) * self.mu_epsf_arr[-1] )
        return u_debonded + u_compact

    sigma_c_max = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_sigma_c_max( self ):
        w_max_max = min( ( self.model.Ll + self.model.Lr ), 10. )
        def minfunc_sigma( w ):
            self.model.w = w
            stiffness_loss = np.sum( self.model.Kf * self.model.damage ) / np.sum( self.model.Kf )
            if stiffness_loss > 0.90:
                return 1. + w
            # plt.plot(w, self.sigma_c, 'ro')
            return -self.sigma_c
        def residuum_stiffness( w ):
            self.model.w = w
            stiffness_loss = np.sum( self.model.Kf[self.model.c_mask] * self.model.damage[self.model.c_mask] ) / np.sum( self.model.Kf[self.model.c_mask] )
            if stiffness_loss > 0.90:
                return 1. + w
            if stiffness_loss < 0.65 and stiffness_loss > 0.45:
                residuum = 0.0
            else:
                residuum = stiffness_loss - 0.5
            return residuum
        w_max = brentq( residuum_stiffness, 0.0, w_max_max )
        w_points = np.linspace( 0., w_max, 5 )
        w_maxima = []
        sigma_maxima = []
        for i, w in enumerate( w_points[1:] ):
            w_maxima.append( fminbound( minfunc_sigma, w_points[i], w_points[i + 1], maxfun = 5, disp = 0 ) )
            sigma_maxima.append( self.sigma_c )
        return sigma_maxima[np.argmax( np.array( sigma_maxima ) )], w_maxima[np.argmax( np.array( sigma_maxima ) )]
    

    def w_x_results( self, w_arr, x ):
        epsm = np.zeros( ( len( w_arr ), len( x ) ) )
        mu_epsf = np.zeros( ( len( w_arr ), len( x ) ) )
        sigma_c = []
        for i, w in enumerate( w_arr ):
            self.model.w = w
            epsm_line = MFnLineArray( xdata = self.x_arr, ydata = self.epsm_arr )
            mu_epsf_line = MFnLineArray( xdata = self.x_arr, ydata = self.mu_epsf_arr )
            epsm[i, :] = epsm_line.get_values( x )
            mu_epsf[i, :] = mu_epsf_line.get_values( x )
            sigma_c.append( self.sigma_c )
        return epsm, mu_epsf, np.array( sigma_c )

    def w_x_res( self, w_arr, ll, lr, maxBC ):
        self.model.Ll = ll
        self.model.Lr = lr
        epsm = np.array( [] )
        mu_epsf = np.array( [] )
        x = np.array( [] )
        sigma_c = np.array( [] )
        for i, w in enumerate( w_arr ):
            self.model.w = w
            epsm = np.hstack( ( epsm, self.epsm_arr[0], self.epsm_arr, self.epsm_arr[-1] ) )
            mu_epsf = np.hstack( ( mu_epsf, self.mu_epsf_arr[0], self.mu_epsf_arr, self.mu_epsf_arr[-1] ) )
            x = np.hstack( ( x, -maxBC, self.x_arr, maxBC ) )
            sigma_c = np.hstack( ( sigma_c, np.ones( len( self.x_arr ) + 2 ) * self.sigma_c ) )
        return sigma_c, x, mu_epsf, epsm

    def apply_load( self, sigma ):
        if sigma > self.sigma_c_max[0]:
            raise ValueError( 'applied load ', sigma , 'MPa is larger than composite strength ', self.sigma_c_max[0], 'MPa' )
        else:
            def residuum( w ):
                self.model.w = float( w )
                return sigma - self.sigma_c
            brentq( residuum, 0.0, min( self.sigma_c_max[1], 20. ) )

    def sigma_f_lst( self, w_arr ):
        sigma_f_arr = np.zeros( len( w_arr ) * 
                               len( self.model.reinforcement_lst ) ).reshape( len( w_arr ),
                                len( self.model.reinforcement_lst ) )
        masks = [( ( self.model.sorted_xi == reinf.xi ) * 
                          ( self.model.sorted_E_f == reinf.E_f ) * 
                          ( self.model.sorted_V_f == reinf.V_f ) )
                 for reinf in self.model.reinforcement_lst]
        for i, w in enumerate( w_arr ):
            if w == 0.0:
                self.model.w = 1e-15
            else:
                self.model.w = w
            self.model.damage
            for j, reinf in enumerate( self.model.reinforcement_lst ):
                sigma_fi = np.sum( self.model._epsf0_arr * self.model.sorted_stats_weights * self.model.sorted_nu_r * 
                              self.model.sorted_E_f * ( 1. - self.model.damage ) * masks[j] )
                sigma_f_arr[i, j] = sigma_fi
        return sigma_f_arr
    
    Welm = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_Welm( self ):
        Km = self.results[4]
        bonded_l = self.epsm_arr[0] ** 2 * Km * ( self.model.Ll - np.abs( self.x_arr[0] ) )
        bonded_r = self.epsm_arr[-1] ** 2 * Km * ( self.model.Lr - np.abs( self.x_arr[-1] ) )
        return 0.5 * ( np.trapz( self.epsm_arr ** 2 * Km, self.x_arr ) + bonded_l + bonded_r ) 

    Welf = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_Welf( self ):
        Kf = self.model.E_c - self.results[4]
        bonded_l = self.mu_epsf_arr[0] ** 2 * Kf * ( self.model.Ll - np.abs( self.x_arr[0] ) )
        bonded_r = self.mu_epsf_arr[-1] ** 2 * Kf * ( self.model.Lr - np.abs( self.x_arr[-1] ) )
        return 0.5 * ( np.trapz( self.mu_epsf_arr ** 2 * Kf, self.x_arr ) + bonded_l + bonded_r )

    W_el_tot = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_W_el_tot( self ):
        '''total elastic energy stored in the specimen'''
        return self.Welf + self.Welm

    W_inel_tot = Property( depends_on = 'model.E_m, model.w, model.Ll, model.Lr, model.reinforcement_lst+' )
    @cached_property
    def _get_W_inel_tot( self ):
        '''total inelastic energy dissipated during loading up to w'''
        return self.U - self.W_el_tot

    U_line = Property( depends_on = 'model.E_m, model.Ll, model.Lr, model.reinforcement_lst+, w_arr_energy' )
    @cached_property
    def _get_U_line( self ):
        '''work done by external force - mfn_line'''
        w_arr = self.w_arr_energy
        u_lst = []
        F_lst = []
        for w in w_arr:
            self.model.w = w
            u_lst.append( self.u_evaluated )
            F_lst.append( self.sigma_c )
        u_arr = np.array( u_lst )
        F_arr = np.array( F_lst )
        U_line = MFnLineArray( xdata = w_arr, ydata = np.hstack( ( 0, cumtrapz( F_arr, u_arr ) ) ) )
        return U_line  # self.piers

    U = Property( depends_on = 'model.E_m, model.Ll, model.Lr, model.reinforcement_lst+, model.w' )
    @cached_property
    def _get_U( self ):
        '''work done by external force U(w)'''
        return self.U_line.get_values( self.model.w )

    w_arr_energy = Array

    def get_sigma_m_x_input( self, sigma ):
        self.apply_load( sigma )
        line = MFnLineArray( xdata = self.x_arr,
                            ydata = self.epsm_arr )
        return line.get_values( self.x_input )

if __name__ == '__main__':

    from reinforcement import ContinuousFibers, ShortFibers
    from stats.pdistrib.weibull_fibers_composite_distr import WeibullFibers
    


    tex_carbonfibers = ContinuousFibers( r = 0.0035,
                          tau = RV( 'weibull_min', loc = 0.04, shape = 2., scale = .05 ),  # RV( 'weibull_min', loc = 0.006, shape = .23, scale = .03 ),  # RV( 'uniform', loc = 0.5, scale = 1.5 ),  # RV( 'weibull_min', loc = 0.006, shape = .23, scale = .03 ),
                          V_f = 0.011,
                          E_f = 180e3,
                          n_int = 300,
                          xi = WeibullFibers( shape = 5.00001, sV0 = 0.002501 ) )

    
    sf_glas = ShortFibers( r = 9.5 * 1e-3,
                          tau = 1.5,
                          lf = 10. ,
                          snub = 0.7,
                          phi = RV( 'sin2x', loc = 0., scale = 1. ),
                          V_f = 0.01,
                          E_f = 72e3,
                          xi = np.infty,
                          n_int = 200,
                          label = 'SFGlas' )


    model = CompositeCrackBridge( E_m = 25e3,
                                 reinforcement_lst = [tex_carbonfibers, sf_glas],
                                 Ll = 6.5,
                                 Lr = 6.5 )
    

    ccb_view = CompositeCrackBridgeView( model = model )

    def profile( w ):
        ccb_view.model.w = w
        plt.plot( ccb_view.x_arr, ccb_view.epsm_arr, lw = 2, label = 'Ll=' + str( ccb_view.model.Ll ) )
        # plt.plot( ccb_view.x_arr, ccb_view.mu_epsf_arr, color = 'red', lw = 2 )
        plt.xlabel( 'position [mm]' )
        plt.ylabel( 'strain' )

    def sigma_c_w( w_arr ):
        sigma_c_arr, u_arr = ccb_view.sigma_c_arr( w_arr, u = True )
        plt.plot( w_arr, sigma_c_arr, lw = 2, color = 'black', label = 'w-sigma' )
        # plt.plot(u_arr, sigma_c_arr, lw=2, label='u-sigma')
        # plt.plot(ccb_view.sigma_c_max[1], ccb_view.sigma_c_max[0], 'bo')
        plt.xlabel( 'w,u [mm]' )
        plt.ylabel( '$\sigma_c$ [MPa]' )
        plt.legend( loc = 'best' )

    def sigma_f( w_arr ):
        sf_arr = ccb_view.sigma_f_lst( w_arr )
        for i, reinf in enumerate( ccb_view.model.reinforcement_lst ):
            plt.plot( w_arr, sf_arr[:, i], label = reinf.label )

    def energy( w_arr ):
        ccb_view.w_arr_energy = w_arr
        Welm = []
        Welf = []
        Wel_tot = []
        U = []
        Winel = []
        u = []
        ccb_view.U_line
        for w in w_arr:
            ccb_view.model.w = w
            Wel_tot.append( ccb_view.W_el_tot )
            Welm.append( ccb_view.Welm )
            Welf.append( ccb_view.Welf )
            U.append( ccb_view.U )
            Winel.append( ccb_view.W_inel_tot )
            u.append( ccb_view.u_evaluated )
        plt.plot( w_arr, Welm, lw = 2, label = 'Welm' )
        plt.plot( w_arr, Welf, lw = 2, label = 'Welf' )
        plt.plot( w_arr, Wel_tot, lw = 2, color = 'black', label = 'elastic strain energy' )
        plt.plot( w_arr, Winel, lw = 2, ls = 'dashed', color = 'black', label = 'inelastic energy' )
        plt.plot( w_arr, U, lw = 3, color = 'red', label = 'work of external force' )
        plt.xlabel( 'w [mm]' )
        plt.ylabel( 'W' )
        plt.ylim( 0.0 )
        plt.legend( loc = 'best' )

    # TODO: check energy for combined reinf
    # energy(np.linspace(.0, .15, 100))
#    sigma_c = np.linspace(1., 7., 7)
#    for i, s in enumerate(sigma_c):
#        ccb_view.apply_load(s)
#        profile(ccb_view.model.w)
    w = np.linspace( 0, .08, 20 )
    # w = 0.05
    r = ccb_view.sigma_c_arr( w )
    plt.plot( w, r )
    print ( r[-5] - r[-10] ) / ( w[-5] / 13. - w[-10] / 13 )
    # profile( w )
    # energy(w)
    # bundle at 20 mm
    # sigma_bundle = 70e3*w/20.*np.exp(-(w/20./0.03)**5.)
    # plt.plot(w,sigma_bundle)
    # plt.plot( ccb_view.sigma_c_max[1], ccb_view.sigma_c_max[0], 'bo' )
    # sigma_f(np.linspace(.0, .16, 50))
    # plt.ylim( 0, 25. )
    # plt.xlim( 0, 0.25 )
    plt.legend( loc = 'best' )
    plt.show()


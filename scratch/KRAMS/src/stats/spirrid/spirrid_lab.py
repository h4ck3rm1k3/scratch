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
# Created on Sep 8, 2011 by: rch

from enthought.traits.api import \
    HasTraits, Float, Array, Property, \
    DelegatesTo, Instance, Int, Str, List

from spirrid import \
    SPIRRID
from error_eval import ErrorEval
import numpy as np
import pylab as p  # import matplotlib with matlab interface
import os.path
import types
from itertools import combinations, chain
from scipy.misc import comb
from matplotlib.patches import Polygon
from matplotlib.ticker import MaxNLocator
from matplotlib import rc
from socket import gethostname

#===============================================================================
# Helper functions
#===============================================================================
def Heaviside(x):
    ''' Heaviside function '''
    return (np.sign(x) + 1.0) / 2.0

def powerset(iterable):
    '''
        Return object of all combination of iterable. 
        powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)
    '''
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

#===============================================================================
# convergence_study
#===============================================================================

class SPIRRIDLAB(HasTraits):
    '''
    '''
    s = Instance(SPIRRID)

    evars = DelegatesTo('s')

    tvars = DelegatesTo('s')

    q = DelegatesTo('s')

    exact_arr = Array('float')

    e_arr = Property
    def _get_e_arr(self):
        return self.s.evar_list[0]

    qname = Str

    def get_qname(self):
        if self.qname == '':
            if isinstance(self.q, types.FunctionType):
                qname = self.q.__name__
            else: # if isinstance(self.q, types.ClassType):
                qname = self.q.__class__.__name__
        else:
            qname = self.qname
        return qname

    show_output = False

    save_output = True

    def _plot_sampling(self,
                      sampling_type,
                      ylim = None,
                      xlim = None,
                      plot_idx = [0, 1]):
        '''Construct a spirrid object, run the calculation
        plot the mu_q / e curve and save it in the subdirectory.
        '''

        s = self.s
        s.sampling_type = sampling_type

        qname = self.get_qname()

        # get n randomly selected realizations from the sampling
        theta = s.sampling.get_samples(500)
        tvar_x = s.tvar_list[plot_idx[0]]
        tvar_y = s.tvar_list[plot_idx[1]]
        min_x, max_x, d_x = s.sampling.get_theta_range(tvar_x)
        min_y, max_y, d_y = s.sampling.get_theta_range(tvar_y)
        # for vectorized execution add a dimension for control variable
        theta_args = [ t[:, np.newaxis] for t in theta]
        q_arr = s.q(self.e_arr[None, :], *theta_args)

        f = p.figure(figsize = (7., 6.))
        f.subplots_adjust(left = 0.11, right = 0.98, bottom = 0.12, top = 0.94)

        p.plot(theta[plot_idx[0]], theta[plot_idx[1]], 'o', color = 'grey')
        p.xlabel('$\lambda$', fontsize = 22)
        p.ylabel('$\\xi$', fontsize = 22)

        p.xlim(min_x, max_x)
        p.ylim(min_y, max_y)
        p.title(s.sampling_type)

        if self.save_output:
            fname = os.path.join('fig', qname + '_sampling_' + s.sampling_type + '.png')
            p.savefig(fname)

        f = p.figure(figsize = (7., 5))
        f.subplots_adjust(left = 0.11, right = 0.98, bottom = 0.12, top = 0.94)

        p.plot(self.e_arr, q_arr.T, color = 'grey')

        if len(self.exact_arr) > 0:
            p.plot(self.e_arr, self.exact_arr, label = 'exact solution',
                    color = 'black', linewidth = 2)

        # numerically obtained result
        p.plot(self.e_arr, s.mu_q_arr, label = 'numerical integration',
               linewidth = 3, color = 'red')
        p.title(s.sampling_type)
        p.xlabel('$\\varepsilon$ [-]', fontsize = 22)
        p.ylabel('$\\mu_{q}$', fontsize = 22)
        if ylim:
            p.ylim(0.0, ylim)
        if xlim:
            p.xlim(0.0, xlim)
        p.legend(loc = 2)

        if self.save_output:
            fname = os.path.join('fig', qname + '_' + s.sampling_type + '.png')
            p.savefig(fname)

    def sampling_structure(self, **kw):
        '''Plot the response into the file in the fig subdirectory.
        '''
        for s in ['TGrid', 'PGrid', 'MCS', 'LHS']:
            self._plot_sampling(sampling_type = s, **kw)

        if self.show_output:
            p.show()

    def sampling_efficiency(self, n_int_range):
        '''
        Run the code for all available sampling types.
        Plot the results.
        '''
        qname = self.get_qname()

        def run_estimation(n_int, sampling_type):
            # instantiate spirrid with samplingetization methods 
            print 'running', sampling_type, n_int
            self.s.set(n_int = n_int, sampling_type = sampling_type)
            n_sim = self.s.sampling.n_sim
            return self.s.mu_q_arr, self.s.exec_time, n_sim

        # vectorize the estimation to accept arrays
        run_estimation_vct = np.vectorize(run_estimation, [object, float, int])

        #===========================================================================
        # Generate the inspected domain of input parameters using broadcasting
        #===========================================================================

        run_estimation_vct([5], ['PGrid'])

        # studied samplingetization methods
        sampling_types = np.array(['TGrid', 'PGrid', 'MCS', 'LHS'], dtype = str)
        sampling_colors = np.array(['blue', 'green', 'red', 'magenta'], dtype = str)

        # run the estimation on all combinations of n_int and sampling_types
        mu_q, exec_time, n_sim_range = run_estimation_vct(n_int_range[:, None],
                                                          sampling_types[None, :])

        f = p.figure(figsize = (12, 6))
        f.subplots_adjust(left = 0.06, right = 0.94)

        #===========================================================================
        # Plot the results
        #===========================================================================
        p.subplot(1, 2, 1)
        p.title('response for %d $n_\mathrm{sim}$' % n_sim_range[-1, -1])
        for i, (sampling, color) in enumerate(zip(sampling_types, sampling_colors)):
            p.plot(self.e_arr, mu_q[-1, i], color = color, label = sampling)

        if len(self.exact_arr) > 0:
            p.plot(self.e_arr, self.exact_arr, color = 'black', label = 'Exact solution')

        p.legend(loc = 1)
        p.xlabel('e', fontsize = 18)
        p.ylabel('q', fontsize = 18)

        # @todo: get n_sim - x-axis
        p.subplot(1, 2, 2)
        for i, (sampling, color) in enumerate(zip(sampling_types, sampling_colors)):
            p.loglog(n_sim_range[:, i], exec_time[:, i], color = color, label = sampling)

        p.legend(loc = 2)
        p.xlabel('$n_\mathrm{sim}$', fontsize = 18)
        p.ylabel('$t$ [s]', fontsize = 18)

        if self.save_output:
            fname = os.path.join('fig', qname + '_' + 'time_nint' + '.png')
            p.savefig(fname)

        #===========================================================================
        # Evaluate the error
        #===========================================================================

        if len(self.exact_arr) > 0:

            er = ErrorEval(exact_arr = self.exact_arr)

            def eval_error(mu_q, error_measure):
                return error_measure(mu_q)
            eval_error_vct = np.vectorize(eval_error)

            error_measures = np.array([er.eval_error_max,
                                        er.eval_error_energy,
                                        er.eval_error_rms ])
            error_table = eval_error_vct(mu_q[:, :, None],
                                          error_measures[None, None, :])

            f = p.figure(figsize = (14, 6))
            f.subplots_adjust(left = 0.07, right = 0.97, wspace = 0.26)

            p.subplot(1, 2, 1)
            p.title('max rel. lack of fit')
            for i, (sampling, color) in enumerate(zip(sampling_types, sampling_colors)):
                p.loglog(n_sim_range[:, i], error_table[:, i, 0], color = color, label = sampling)

            #p.ylim( 0, 10 )
            p.legend()
            p.xlabel('$n_\mathrm{sim}$', fontsize = 18)
            p.ylabel('$\mathrm{e}_{\max}$ [-]', fontsize = 18)

            p.subplot(1, 2, 2)
            p.title('rel. root mean square error')
            for i, (sampling, color) in enumerate(zip(sampling_types, sampling_colors)):
                p.loglog(n_sim_range[:, i], error_table[:, i, 2], color = color, label = sampling)
            p.legend()
            p.xlabel('$n_{\mathrm{sim}}$', fontsize = 18)
            p.ylabel('$\mathrm{e}_{\mathrm{rms}}$ [-]', fontsize = 18)

            if self.save_output:
                fname = os.path.join('fig', qname + '_' + 'error_nint' + '.png')
                p.savefig(fname)

            f = p.figure(figsize = (14, 6))
            f.subplots_adjust(left = 0.07, right = 0.97, wspace = 0.26)

            p.subplot(1, 2, 1)
            p.title('rel. max lack of fit')
            for i, (sampling, color) in enumerate(zip(sampling_types, sampling_colors)):
                p.loglog(exec_time[:, i], error_table[:, i, 0], color = color, label = sampling)
            p.legend()
            p.xlabel('time [s]', fontsize = 18)
            p.ylabel('$\mathrm{e}_{\max}$ [-]', fontsize = 18)

            p.subplot(1, 2, 2)
            p.title('rel. root mean square error')
            for i, (sampling, color) in enumerate(zip(sampling_types, sampling_colors)):
                p.loglog(exec_time[:, i], error_table[:, i, 2], color = color, label = sampling)
            p.legend()
            p.xlabel('time [s]', fontsize = 18)
            p.ylabel('$\mathrm{e}_{\mathrm{rms}}$ [-]', fontsize = 18)

            if self.save_output:
                fname = os.path.join('fig', qname + '_' + 'error_time' + '.png')
                p.savefig(fname)

        if self.show_output:
            p.show()

    #===========================================================================
    # Efficiency of numpy versus C code
    #===========================================================================
    run_list_detailed_config = Property(List)
    def _get_run_list_detailed_config(self):
        run_lst = []
        if hasattr(self.q, 'c_code'):
            run_lst += [
#                ('c',
#                 {'cached_dG'         : True,
#                  'compiled_eps_loop' : True },
#                  'go-',
#                  '$\mathsf{C}_{\\varepsilon} \{\, \mathsf{C}_{\\theta} \{\,  q(\\varepsilon,\\theta) \cdot G[\\theta] \,\}\,\} $ - %4.2f sec',
#                  ),
                ('c',
                 {'cached_dG'         : True,
                  'compiled_eps_loop' : False },
                 'r-2',
                 '$\mathsf{Python} _{\\varepsilon} \{\, \mathsf{C}_{\\theta} \{\,  q(\\varepsilon,\\theta) \cdot G[\\theta] \,\}\,\} $ - %4.2f sec'
                 ),
#                ('c',
#                 {'cached_dG'         : False,
#                  'compiled_eps_loop' : True },
#                 'r-2',
#                 '$\mathsf{C}_{\\varepsilon} \{\, \mathsf{C}_{\\theta} \{\, q(\\varepsilon,\\theta) \cdot g[\\theta_1] \cdot \ldots \cdot g[\\theta_m] \,\}\,\} $ - %4.2f sec'
#                 ),
                ('c',
                 {'cached_dG'         : False,
                  'compiled_eps_loop' : False },
                  'bx-',
                  '$\mathsf{Python} _{\\varepsilon} \{\, \mathsf{C}_{\\theta}  \{\, q(\\varepsilon,\\theta) \cdot g[\\theta_1] \cdot \ldots \cdot g[\\theta_m] \,\} \,\} $ - %4.2f sec',
                 )]
        if hasattr(self.q, 'cython_code'):
            run_lst += [
#                ('cython',
#                 {'cached_dG'         : True,
#                  'compiled_eps_loop' : True },
#                  'go-',
#                  '$\mathsf{Cython}_{\\varepsilon} \{\, \mathsf{Cython}_{\\theta} \{\,  q(\\varepsilon,\\theta) \cdot G[\\theta] \,\}\,\} $ - %4.2f sec',
#                  ),
                ('cython',
                 {'cached_dG'         : True,
                  'compiled_eps_loop' : False },
                 'r-2',
                 '$\mathsf{Python} _{\\varepsilon} \{\, \mathsf{Cython}_{\\theta} \{\,  q(\\varepsilon,\\theta) \cdot G[\\theta] \,\}\,\} $ - %4.2f sec'
                 ),
#                ('cython',
#                 {'cached_dG'         : False,
#                  'compiled_eps_loop' : True },
#                 'r-2',
#                 '$\mathsf{Cython}_{\\varepsilon} \{\, \mathsf{Cython}_{\\theta} \{\, q(\\varepsilon,\\theta) \cdot g[\\theta_1] \cdot \ldots \cdot g[\\theta_m] \,\}\,\} $ - %4.2f sec'
#                 ),
                ('cython',
                 {'cached_dG'         : False,
                  'compiled_eps_loop' : False },
                  'bx-',
                  '$\mathsf{Python} _{\\varepsilon} \{\, \mathsf{Cython}_{\\theta}  \{\, q(\\varepsilon,\\theta) \cdot g[\\theta_1] \cdot \ldots \cdot g[\\theta_m] \,\} \,\} $ - %4.2f sec',
                 )]
        if hasattr(self.q, '__call__'):
            run_lst += [
                ('numpy',
                 {},
                 'y--',
                 '$\mathsf{Python}_{\\varepsilon} \{\,  \mathsf{Numpy}_{\\theta} \{\,  q(\\varepsilon,\\theta) \cdot G[\\theta] \,\} \,\} $ - %4.2f sec'
                 )]
        return run_lst


    def codegen_efficiency(self):
        # define a tables with the run configurations to start in a batch

        qname = self.get_qname()

        s = self.s

        legend = []
        legend_lst = []
        time_lst = []
        p.figure()

        for idx, run in enumerate(self.run_list_detailed_config):
            code, run_options, plot_options, legend_string = run
            s.codegen_type = code
            s.codegen.set(**run_options)
            print 'run', idx, run_options

            for i in range(2):
                s.recalc = True
                s.sampling.recalc = True
                print 'execution time', s.exec_time

            p.plot(s.evar_list[0], s.mu_q_arr, plot_options)

            legend.append(legend_string % s.exec_time)
            legend_lst.append(legend_string[:-12])
            time_lst.append(s.exec_time)

        p.xlabel('strain [-]')
        p.ylabel('stress')
        p.legend(legend, loc = 2)
        p.title(qname)

        if self.save_output:
            print 'saving codegen_efficiency'
            fname = os.path.join('fig', qname + '_' + 'codegen_efficiency' + '.png')
            p.savefig(fname)

        self._bar_plot(legend_lst, time_lst)
        p.title('%s' % s.sampling_type)
        fname = os.path.join('fig', qname + '_' + 'codegen_efficiency_%s' % s.sampling_type + '.png')
        p.savefig(fname)

        if self.show_output:
            p.show()

    #===========================================================================
    # Efficiency of numpy versus C code
    #===========================================================================
    run_list_language_config = Property(List)
    def _get_run_list_language_config(self):
        run_lst = []
        if hasattr(self.q, 'c_code'):
            run_lst += [
                ('c',
                 {'cached_dG'         : False,
                  'compiled_eps_loop' : False },
                  'bx-',
                  '$\mathsf{Python} _{\\varepsilon} \{\, \mathsf{C}_{\\theta}  \{\, q(\\varepsilon,\\theta) \cdot g[\\theta_1] \cdot \ldots \cdot g[\\theta_m] \,\} \,\} $ - %4.2f sec',
                 )]
        if hasattr(self.q, 'cython_code'):
            run_lst += [
                ('cython',
                 {'cached_dG'         : False,
                  'compiled_eps_loop' : False },
                  'bx-',
                  '$\mathsf{Python} _{\\varepsilon} \{\, \mathsf{Cython}_{\\theta}  \{\, q(\\varepsilon,\\theta) \cdot g[\\theta_1] \cdot \ldots \cdot g[\\theta_m] \,\} \,\} $ - %4.2f sec',
                 )]
        if hasattr(self.q, '__call__'):
            run_lst += [
                ('numpy',
                 {},
                 'y--',
                 '$\mathsf{Python}_{\\varepsilon} \{\,  \mathsf{Numpy}_{\\theta} \{\,  q(\\varepsilon,\\theta) \cdot G[\\theta] \,\} \,\} $ - %4.2f sec'
                 )]
        return run_lst

    def codegen_language_efficiency(self, extra_compiler_args = True):
        # define a tables with the run configurations to start in a batch

        os.system('rm -fr ~/.python27_compiled')

        hostname = gethostname()

        qname = self.get_qname()

        for extra in [extra_compiler_args]:
            print 'extra compilation args:', extra
            legend_lst = []
            time_lst = []
            meth_lst = ['LHS', 'PGrid']
            for item in meth_lst:
                print 'sampling method:', item
                s = self.s
                s.sampling_type = item

                for idx, run in enumerate(self.run_list_language_config):
                    code, run_options, plot_options, legend_string = run

                    #os.system('rm -fr ~/.python27_compiled')

                    s.codegen_type = code
                    s.codegen.set(**run_options)
                    if s.codegen_type == 'c':
                        s.codegen.set(**dict(use_extra = extra))
                    print 'run', idx, run_options

                    for i in range(2):
                        s.recalc = True
                        s.sampling.recalc = True
                        print 'execution time', s.exec_time

                    legend_lst.append(legend_string[:-12])
                    time_lst.append(s.exec_time)

            self._bar_plot_2(meth_lst, legend_lst, time_lst)
            fname = os.path.join('fig',
                                 '%s_codegen_efficiency_%s_extra_%s.png' % (qname, hostname, extra))
            p.savefig(fname)

        if self.show_output:
            p.show()

    def combination_efficiency(self, tvars_det, tvars_rand):
        '''
        Run the code for all available random parameter combinations.
        Plot the results.
        '''
        qname = self.get_qname()

        s = self.s
        s.set(sampling_type = 'TGrid')

        # list of all combinations of response function parameters
        rv_comb_list = list(powerset(s.tvars.keys()))

        p.figure()
        exec_time_lst = []

        for id, rv_comb in enumerate(rv_comb_list[163:219]): # [1:-1]
            s.tvars = tvars_det
            print 'Combination', rv_comb

            for rv in rv_comb:
                s.tvars[rv] = tvars_rand[rv]

            #legend = []
            #p.figure()
            time_lst = []
            for idx, run in enumerate(self.run_list):
                code, run_options, plot_options, legend_string = run
                print 'run', idx, run_options
                s.codegen_type = code
                s.codegen.set(**run_options)

                #p.plot(s.evar_list[0], s.mu_q_arr, plot_options)

                #print 'integral of the pdf theta', s.eval_i_dG_grid()
                print 'execution time', s.exec_time
                time_lst.append(s.exec_time)
                #legend.append(legend_string % s.exec_time)
            exec_time_lst.append(time_lst)
        p.plot(np.array((1, 2, 3, 4)), np.array(exec_time_lst).T)
        p.xlabel('method')
        p.ylabel('time')

        if self.save_output:
            print 'saving codegen_efficiency'
            fname = os.path.join('fig', qname + '_' + 'combination_efficiency' + '.png')
            p.savefig(fname)

        if self.show_output:
            p.title(s.q.title)
            p.show()

    def _bar_plot(self, legend_lst, time_lst):
        rc('font', size = 15)
        #rc('font', family = 'serif', style = 'normal', variant = 'normal', stretch = 'normal', size = 15)
        fig = p.figure(figsize = (10, 5))

        numTests = len(time_lst)
        times = np.array(time_lst)
        x_norm = times[1]
        xmax = times.max()
        rel_xmax = xmax / x_norm
        rel_times = times / x_norm
        m = int(rel_xmax % 10)

        if m < 5:
            x_max_plt = int(rel_xmax) - m + 10
        else:
            x_max_plt = int(rel_xmax) - m + 15

        ax1 = fig.add_subplot(111)
        p.subplots_adjust(left = 0.45, right = 0.88)
        #fig.canvas.set_window_title('window title')
        pos = np.arange(numTests) + 0.5
        rects = ax1.barh(pos, rel_times, align = 'center',
                          height = 0.5, color = 'w', edgecolor = 'k')

        ax1.set_xlabel('normalized execution time [-]')
        ax1.axis([0, x_max_plt, 0, numTests])
        ax1.set_yticks(pos)
        ax1.set_yticklabels(legend_lst)

        for rect, t in zip(rects, rel_times):
           width = rect.get_width()

           xloc = width + (0.03 * rel_xmax)
           clr = 'black'
           align = 'left'

           yloc = rect.get_y() + rect.get_height() / 2.0
           ax1.text(xloc, yloc, '%4.2f' % t, horizontalalignment = align,
                    verticalalignment = 'center', color = clr)#, weight = 'bold')

        ax2 = ax1.twinx()
        ax1.plot([1, 1], [0, numTests], 'k--')
        ax2.set_yticks([0] + list(pos) + [numTests])
        ax2.set_yticklabels([''] + ['%4.2f s' % s for s in list(times)] + [''])
        ax2.set_xticks([0, 1] + range(5 , x_max_plt + 1, 5))
        ax2.set_xticklabels(['%i' % s for s in ([0, 1] + range(5 , x_max_plt + 1, 5))])


    def _bar_plot_2(self, title_lst, legend_lst, time_lst):
        rc('font', size = 15)
        #rc('font', family = 'serif', style = 'normal', variant = 'normal', stretch = 'normal', size = 15)
        fig = p.figure(figsize = (15, 5))
        idx = int(len(time_lst) / 2.)
        numTests = len(time_lst[:idx])
        times = np.array(time_lst[:idx])
        x_norm = np.min(times)
        xmax = times.max()
        rel_xmax = xmax / x_norm
        rel_times = times / x_norm
        m = int(rel_xmax % 10)

        if m < 5:
            x_max_plt = int(rel_xmax) - m + 10
        else:
            x_max_plt = int(rel_xmax) - m + 15

        ax1 = fig.add_subplot(121)
        p.subplots_adjust(left = 0.35, right = 0.88, wspace = 0.3)
        #fig.canvas.set_window_title('window title')
        pos = np.arange(numTests) + 0.5
        rects = ax1.barh(pos, rel_times, align = 'center',
                          height = 0.5, color = 'w', edgecolor = 'k')

        ax1.set_xlabel('normalized execution time [-]')
        ax1.axis([0, x_max_plt, 0, numTests])
        ax1.set_title(title_lst[0])
        ax1.set_yticks(pos)
        ax1.set_yticklabels(legend_lst[:idx])

        for rect, t in zip(rects, rel_times):

            width = rect.get_width()
            xloc = width + (0.03 * rel_xmax)
            clr = 'black'
            align = 'left'

            yloc = rect.get_y() + rect.get_height() / 2.0
            ax1.text(xloc, yloc, '%4.2f' % t, horizontalalignment = align,
                    verticalalignment = 'center', color = clr)#, weight = 'bold')

        ax2 = ax1.twinx()
        ax2.plot([1, 1], [0, numTests], 'k--')
        ax2.set_yticks([0] + list(pos) + [numTests])
        ax2.set_yticklabels([''] + ['%4.2f s' % s for s in list(times)] + [''])
        ax2.set_xticks([0, 1] + range(5 , x_max_plt + 1, 5))
        ax2.set_xticklabels(['%i' % s for s in ([0, 1] + range(5 , x_max_plt + 1, 5))])

        numTests = len(time_lst[idx:])
        times = np.array(time_lst[idx:])
        x_norm = times[1]
        xmax = times.max()
        rel_xmax = xmax / x_norm
        rel_times = times / x_norm
        m = int(rel_xmax % 10)

        if m < 5:
            x_max_plt = int(rel_xmax) - m + 10
        else:
            x_max_plt = int(rel_xmax) - m + 15

        ax3 = fig.add_subplot(122)
        #fig.canvas.set_window_title('window title')
        pos = np.arange(numTests) + 0.5
        rects = ax3.barh(pos, rel_times, align = 'center',
                          height = 0.5, color = 'w', edgecolor = 'k')

        ax3.set_xlabel('normalized execution time [-]')
        ax3.axis([0, x_max_plt, 0, numTests])
        ax3.set_title(title_lst[1])
        ax3.set_yticks(pos)
        ax3.set_yticklabels([])

        for rect, t in zip(rects, rel_times):
            width = rect.get_width()
            xloc = width + (0.03 * rel_xmax)
            clr = 'black'
            align = 'left'

            yloc = rect.get_y() + rect.get_height() / 2.0
            ax3.text(xloc, yloc, '%4.2f' % t, horizontalalignment = align,
                     verticalalignment = 'center', color = clr)#, weight = 'bold')

        ax4 = ax3.twinx()
        ax3.plot([1, 1], [0, numTests], 'k--')
        ax4.set_yticks([0] + list(pos) + [numTests])
        ax4.set_yticklabels([''] + ['%4.2f s' % s for s in list(times)] + [''])
        ax4.set_xticks([0, 1] + range(5 , x_max_plt + 1, 5))
        ax4.set_xticklabels(['%i' % s for s in ([0, 1] + range(5 , x_max_plt + 1, 5))])

if __name__ == '__main__':

    from stats.spirrid import RV
    from scipy.special import erf
    import math

    # response function
    def fiber_tt_2p(e, la, xi):
        ''' Response function of a single fiber '''
        return la * e * Heaviside(xi - e)

    # statistical characteristics (mean, stdev)
    m_la, std_la = 10., 1.0
    m_xi, std_xi = 1.0, 0.1

    # discretize the control variable (x-axis)
    e_arr = np.linspace(0, 1.2, 40)

    # Exact solution
    def mu_q_ex(e, m_xi, std_xi, m_la):
        return e * (0.5 - 0.5 * erf(0.5 * math.sqrt(2) * (e - m_xi) / std_xi)) * m_la

    mu_q_ex_arr = mu_q_ex(e_arr, m_xi, std_xi, m_la)

    g_la = RV('norm', m_la, std_la)
    g_xi = RV('norm', m_xi, std_xi)

    s = SPIRRID(q = fiber_tt_2p,
                e_arr = e_arr,
                n_int = 4000,
                tvars = dict(la = g_la, xi = g_xi),
                )

    mu_q_ex_arr = mu_q_ex(e_arr, m_xi, std_xi, m_la)

    slab = SPIRRIDLAB(s = s, save_output = False, show_output = True,
                      exact_arr = mu_q_ex(e_arr, m_xi, std_xi, m_la))

    powers = np.linspace(1, math.log(200, 10), 50)
    n_int_range = np.array(np.power(10, powers), dtype = int)

    slab.sampling_efficiency(n_int_range = n_int_range)

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
# Created on Aug 7, 2009 by: rchx

from enthought.traits.api import TraitType, HasTraits, TraitError
from enthought.traits.trait_base import ClassTypes

class EitherType( TraitType ):
    
    def __init__( self, types = [], **metadata ):
        # validate that these are trait types
        self._klasses = types
        
        super( EitherType, self ).__init__( **metadata ) 
        self._trait_value_history = {}
    
    def validate( self, object, name, value ):
        ''' Set the trait value '''
        # first check if the value is a class
        if isinstance( value, ClassTypes ):
            klass = value
            if not klass in self._klasses:
                raise TraitError, 'type %s not in the type scope' % klass
            # check if the last instance of the klass has been
            # registered earlier in the trait history
            new_value = self._trait_value_history.get( klass, None )
            if new_value == None:
                # construct a new value
                new_value = klass()
        else:
            # the value must be one of those in _klasses
            if isinstance( value, tuple( self._klasses ) ):
                new_value = value
            else:
                raise TraitError, 'value of type %s out of the scope' % value.__class__ 
        return new_value
    
    def get_default_value( self ):
        '''Take the first class to construct the value'''
        klass = self._klasses[0]
        value = klass()
        return (0, value)

if __name__ == '__main__':

    from types  import StringType, IntType
    
    class UseEitherType( HasTraits ):
        int_or_string = EitherType( types = [ IntType, StringType ] )

    uet = UseEitherType( )

    print 'default value', uet.int_or_string
        
    uet.int_or_string = 4
    
    print 'value', uet.int_or_string
    
    uet.int_or_string = StringType

    print 'value after type reset', uet.int_or_string 
    
    uet.int_or_string = 'is now the string'
    
    print 'value', uet.int_or_string
    
    uet.int_or_string = 8.9 # exception
    
        
        
        
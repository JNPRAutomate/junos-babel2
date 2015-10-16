import logging

class ParsingError:
    __nbr_error = 0
    def __init__( self ):
        self.errors = []

    def add( self, msg ):
        self.errors.append(msg)
        self.__nbr_error += 1

    def has_error( self ):
        if self.__nbr_error == 0 :
            return 0
        else:
            return 1

    def display( self ):
        for msg in self.errors:
            logging.warning( msg )

    def exit_on_error( self ):
        if self.has_error():
            self.display()
            exit()

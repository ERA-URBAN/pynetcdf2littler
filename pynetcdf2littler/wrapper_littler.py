#!/usr/bin/env python2

'''
description:  Wrapper to create a single output file in LITTLE_R format from a
              list of netcdf files defined in an input file.
              Uses netcdf2littler tool.
license:      APACHE 2.0
author:       Ronald van Haren, NLeSC (r.vanharen@esciencecenter.nl)
'''

import os
import shutil
import fileinput
import glob
import subprocess
import sys
import f90nml


class wrapper_littler:
    '''
    Wrapper class to create a single output file in LITTLE_R format from a
    list of netcdf files defined in an input file.
    '''
    def __init__(self, filelist, netcdf2littler_namelist, outputdir,
                 outputfile, startdate=None, enddate=None):
        self.filelist = filelist
        self.workdir = os.path.join(outputdir, 'tmp')
        self.netcdf2littler_namelist = netcdf2littler_namelist
        self.outputdir = outputdir
        self.outputfile = outputfile
        self.startdate = startdate
        self.enddate = enddate
        self.cleanup_workdir()
        self.test_input()
        self.read_filelist()  # create list of filenames
        for idx, filename in enumerate(self.files):  # loop over all files
            self.process_file(filename, idx)  # process file
        self.combine_output_files()  # combine all LITTLE_R files
        # cleanup workdir
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir)

    def test_input(self):
        '''
        verify that all input files exist
        '''
        if not os.path.exists(self.filelist):
            raise IOError(self.filelist + ' not found.')
        else:
            self.filelist = os.path.abspath(self.filelist)
        if not os.path.exists(self.netcdf2littler_namelist):
            raise IOError(self.netcdf2littler_namelist + ' not found.')
        else:
            self.netcdf2littler_namelist = os.path.abspath(
              self.netcdf2littler_namelist)

    def cleanup_workdir(self):
        '''
        cleanup previous results and copy files to workdir
        '''
        if os.path.exists(self.workdir):
            # remove workdir if exists
            shutil.rmtree(self.workdir)
        # create workdir
        try:
            os.makedirs(self.workdir)
        except IOError:
            raise IOError('Cannot create work directory: ' + self.workdir)

    def read_filelist(self):
        '''
        read list of files from file
        discard lines with length 0
        add files to list
        '''
        self.files = [line.strip() for line in open(
          self.filelist, 'r') if len(line.strip()) > 0]

    def process_file(self, filename, idx):
        '''
        process input file:
          - extract time interval netcdf file
          - convert extracted time interval to LITTLE_R format
        '''
        nml = f90nml.read(self.netcdf2littler_namelist)
        nml['group_name']['filename'] = filename
        nml['group_name']['outfile'] = 'results' + str(idx).zfill(3) + '.txt'
        # change startdate and enddate if arguments supplied
        if self.startdate:
            nml['group_name']['startdate'] = self.startdate
        if self.enddate:
            nml['group_name']['enddate'] = self.enddate
        # output namelist
        namelist_tmp = os.path.abspath(os.path.join
                                       (self.workdir, os.path.basename
                                        (self.netcdf2littler_namelist)))
        f90nml.write(nml, namelist_tmp,
                     force=True)
        # convert resulting ncdf file to little_R format
        owd = os.getcwd()
        try:
            os.chdir(os.path.join(self.outputdir, 'tmp'))
            subprocess.call(['netcdf2littler',
                             '--namelist',
                             namelist_tmp],
                            stdout=open(os.devnull, 'wb'))
        except OSError as e:
            print >>sys.stderr, "Execution failed:", e
            exit()
        finally:
            os.chdir(owd)

    def combine_output_files(self):
        '''
        concatenate all txt files to a single outputfile
        '''
        filenames = glob.glob(os.path.join(self.workdir,
                                           'results*txt'))
        if filenames:
            with open(os.path.join
                      (self.outputdir, self.outputfile), 'w') as fout:
                for line in fileinput.input(filenames):
                    fout.write(line)
        else:
            with open(self.outputfile, 'a'):
                os.utime(self.outputfile, None)
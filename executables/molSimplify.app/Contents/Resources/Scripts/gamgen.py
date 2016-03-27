# Written by Tim Ioannidis for HJK Group
# Dpt of Chemical Engineering, MIT

#####################################################
########## This script generates input  #############
##########    for GAMESS calculations   #############
#####################################################

import glob
import sys
import os
import shutil
from Classes.mol3D import mol3D
from Classes.atom3D import atom3D
from Classes.globalvars import *

### convert xyz to gxyz ###
def xyz2gxyz(filename):
    # convert normal xyz file to gamess format
    mol=mol3D() # create mol3D object
    mol.readfromxyz(filename) # read molecule
    gfilename = filename.replace('.xyz','.gxyz') # new file name
    mol.writegxyz(gfilename) # write gamess formatted xyz file
    return gfilename.split('.gxyz')[0]

### generate multiple runs if multiple methods requested ###
def multigamgen(args,strfiles):
    method = False
    jobdirs=[]
    if args.method and len(args.method) > 1:
        methods = args.method
        for method in methods:
            jobdirs.append(gamgen(args,strfiles,method))
    else:
        jobdirs.append(gamgen(args,strfiles,method))
    # remove original files
    for xyzf in strfiles:
        os.remove(xyzf+'.xyz')
        os.remove(xyzf+'.gxyz')
    return jobdirs

### generate input files ###
def gamgen(args,strfiles,method):
    # get global variables
    globs = globalvars()
    jobdirs = []
    coordfs = []
    # Initialize the jobparams dictionary with mandatory/useful keywords.
    jobparams={'RUNTYP': 'OPTIMIZE',
           'GBASIS': 'N21',
           'MAXIT': '500',
           'DFTTYP': 'B3LYP',
           'SCFTYP': 'UHF',
           'ICHARG': '0',
           'MULT': '1',
            }
    # Overwrite plus add any new dictionary keys from commandline input.       
    for xyzf in strfiles:
        # convert to "gamess format"
        xyzf = xyz2gxyz(xyzf+'.xyz')
        rdir = xyzf.rsplit('/',1)[0]
        xyzft = xyzf.rsplit('/',1)[-1]
        xyzf += '.gxyz'
        coordfs.append(xyzf)
        coordname = xyzft
        # Setting jobname for files + truncated name for queue.
        if len(coordname) > 10:
            nametrunc=coordname[0:6]+coordname[-4:]
        else:
            nametrunc=coordname
        if not os.path.exists(rdir+'/'+nametrunc):
            os.mkdir(rdir+'/'+nametrunc) 
        mdir = rdir+'/'+nametrunc
        if method:
            if method[0]=='U' or method[0]=='u':
                mmd = '/'+method[1:]
            else:
                mmd = '/'+method
                jobparams['SCFTYP']='RHF'
            mdir = rdir+'/'+nametrunc+mmd
            if not os.path.exists(mdir):
                os.mkdir(mdir)
        jobdirs.append(mdir)
        shutil.copy2(xyzf,mdir)
    if method:
        if method[0]=='U' or method[0]=='u':
            method = method[1:]
    # Just carry over spin and charge keywords if they're set. Could do checks, none for now.
    if args.spin:
       jobparams['MULT']=args.spin
    if args.charge:
       jobparams['ICHARG']=args.charge
    # Check for existence of basis and sanitize name
    if args.gbasis:
          jobparams['GBASIS']=args.gbasis.upper()
    if args.ngauss:
          jobparams['NGAUSS']=args.ngauss.upper()
    if method:
          jobparams['DFTTYP']=method.upper()
    # Now we're ready to start building the input file and the job script
    for i,jobd in enumerate(jobdirs):
        output=open(jobd+'/gam.inp','w')
        f=open(coordfs[i])
        s = f.read() # read coordinates
        f.close()
        jobparams['coordinates'] = s
        output.write('! File created using %s\n' % globs.PROGRAM)
        # write $BASIS block
        output.write(' $BASIS ')
        if args.ngauss:
            output.write(' GBASIS='+jobparams['GBASIS'])
            output.write(' NGAUSS='+jobparams['NGAUSS']+' $END\n')
        else:
            output.write(' GBASIS='+jobparams['GBASIS']+' $END\n')
        # write $SYSTEM block
        output.write(' $SYSTEM ')
        # check if MWORDS specified by the user
        if not args.sysoption or not ('MWORDS' in args.sysoption):
            output.write(' MWORDS=16')
        # write additional options
        if (args.sysoption):
            if len(args.sysoption)%2 > 0:
                print 'WARNING: wrong number of arguments in -sysoption'
            else:
                for elem in range(0,int(0.5*len(args.sysoption))):
                    key,val=args.sysoption[2*elem],args.sysoption[2*elem+1]
                    output.write(' '+key+'='+val+' ')
        output.write(' $END\n')
        # write CONTRL block
        output.write(' $CONTRL SCFTYP='+jobparams['SCFTYP']+' DFTTYP=')
        output.write(jobparams['DFTTYP']+' RUNTYP='+jobparams['RUNTYP'])
        output.write('\n  ICHARG='+jobparams['ICHARG']+' MULT=')
        # check if CC basis set specified and add spherical
        if 'CC' in jobparams['GBASIS']:
            output.write(jobparams['MULT']+' ISPHER=1\n')
        else:
            output.write(jobparams['MULT']+'\n')
        # write additional options
        if (args.ctrloption):
            if len(args.ctrloption)%2 > 0:
                print 'WARNING: wrong number of arguments in -ctrloption'
            else:
                for elem in range(0,int(0.5*len(args.ctrloption))):
                    key,val=args.ctrloption[2*elem],args.ctrloption[2*elem+1]
                    output.write(' '+key+'='+val+' ')
        output.write(' $END\n')
        # write $SCF block
        output.write(' $SCF ')
        # check if options specified by the user
        if not args.scfoption or not ('DIRSCF' in args.scfoption):
            output.write(' DIRSCF=.TRUE.')
        if not args.scfoption or not ('DIIS' in args.scfoption):
            output.write(' DIIS=.TRUE.')
        if not args.scfoption or not ('SHIFT' in args.scfoption):
                output.write(' SHIFT=.TRUE.')
        # write additional options
        if (args.scfoption):
            if len(args.scfoption)%2!=0:
                print 'WARNING: wrong number of arguments in -scfoption'
            else:
                for elem in range(0,int(0.5*len(args.scfoption))):
                    key,val=args.scfoption[2*elem],args.scfoption[2*elem+1]
                    output.write(' '+key+'='+val+' ')
        output.write(' $END\n')
        # write $STATPT block
        output.write(' $STATPT ')
        # check if NSTEP specified by the user
        if not args.statoption or not ('NSTEP' in args.statoption):
            output.write(' NSTEP=100')
        # write additional options
        if (args.statoption):
            if len(args.statoption)%2 > 0:
                print 'WARNING: wrong number of arguments in -statoption'
            else:
                for elem in range(0,int(0.5*len(args.statoption))):
                    key,val=args.statoption[2*elem],args.statoption[2*elem+1]
                    output.write(' '+key+'='+val+' ')
        output.write(' $END\n')
        # write $DATA block
        output.write(' $DATA\n')
        output.write(jobparams['coordinates']+' $END\n')
        output.close()
    return jobdirs

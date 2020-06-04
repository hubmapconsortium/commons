#utilities for file and os access

import subprocess
import os
import shutil
from hubmap_commons import string_helper
import logging

#checks the fpath parameter to see if the file exists and
#is executable.  Returns True or False.
def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

#checks to see if an executable exists in the currently 
#configured path
def executableExists(prgmName):
    fpath, fname = os.path.split(prgmName)
    if fpath:
        if is_exe(prgmName):
            return True
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, fname)
            if is_exe(exe_file):
                return True

    return False

#shell call to execute a program
#procArry- is a list of arguments to execute,
#with the first element being the name of the
#executable
#
#inputFile- an optional file to take input from
#
def callExecutable(procArry, inputFile = None):    
    try:
        #get the logger
        logger = logging.getLogger('move-wp')

        #print the command to the log file
        cmd = ""
        for arg in procArry:
            cmd = cmd + arg + " "
        logger.info(cmd)

        #if there is no input file execute without it
        #if there is an input file send it into the process
        #redirect stdout and stderr to the subprocess
        #which will be intercepted (by process.poll)
        #via the inline check_io
        if inputFile is None:
            process = subprocess.Popen(procArry, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        else:
            inpt = open(inputFile)
            process = subprocess.Popen(procArry, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=inpt)

        #method to output stdout and stderr to the log file
        def check_io():
            while True:
                output = process.stdout.readline().decode()
                if output:
                    if not string_helper.isBlank(output):
                        logger.log(logging.INFO, output.rstrip())
                else:
                    break
        
        #loop while the proccess is active to record output in log file
        while process.poll() is None:
            check_io()
        
        #return True if the process returns a zero code
        #False, otherwise
        if process.returncode != 0:
            return False
        else:
            return True
    
    #catch any excptions, record the error to the log file and return a False
    except Exception as e:
        logger.error("Error while executing " + str(procArry)[1:-1] + "\n" + str(e))
        logger.error(e, exc_info=True)
        return False 

def log_subprocess_output(pipe):
    for line in iter(pipe.readline, b''): # b'\n'-separated lines
        logging.info('got line from subprocess: %r', line)

#make sure the supplied argument (val) ends
#with a file path separator
def ensureTrailingSlash(val):
    v2 = val.strip()
    if not v2.endswith(os.sep):
        v2 = v2 + os.sep
    return v2

def ensureTrailingSlashURL(val):
    v = val.strip()
    if not v.endswith('/'):
        v = v + '/'
    return v

def ensureBeginningSlashURL(val):
    v = val.strip()
    if not v.startswith('/'):
        v = '/' + v
    return v

def removeTrailingSlashURL(val):
    v = val.strip()
    if v.endswith('/'):
        v = v[:-1]
    return v

#check to make sure the ssh command is available
def hasSSH():
    return shutil.which("ssh") is not None

#create a directory
def mkDir(path):
    try:  
        os.mkdir(path)
    except:  
        return False
    else:  
        return True

def linkDir(src_path, dest_path):

    dest_root_path = os.path.split(dest_path)[0]
    #if the directory where we need to create the link doesn't exist..
    if not os.path.exists(dest_root_path) or not os.path.isdir(dest_root_path):
        raise Exception("ERROR linking, destination does not exist or is not a directory: " + dest_root_path)
    
    #if we don't have write access in the directory where the link needs to be created..
    if not os.access(dest_root_path, os.W_OK) or not os.access(dest_root_path, os.X_OK):
        raise Exception("ERROR linking, not write access in destination directory: " + dest_root_path)

    #the src doesn't exist or isn't a directory
    if not os.path.exists(src_path) or not os.path.isdir(src_path):
        raise Exception("ERROR linking, source dir does not exist or is not a directory: " + src_path)

    
    #if that link already exists find out why..
    if os.path.exists(dest_path):
        #already a link
        if os.path.islink(dest_path):
            #src is already linked to the 
            if ensureTrailingSlash(os.path.realpath(dest_path)) == ensureTrailingSlash(src_path):
                return
            #already linked to a different place, remove and replace
            else:
                os.unlink(dest_path)
        else:
            raise Exception("Error linking, destination directory exists: " + dest_path)

    os.symlink(src_path, dest_path)

def unlinkDir(linked_path):

    base_path = os.path.split(linked_path)[0]
    if not os.path.exists(base_path):
        raise Exception("Error unlinking, the base directory doesn't exist for: " + linked_path)
    
    if not os.access(base_path, os.W_OK) or not os.access(base_path, os.X_OK):
        raise Exception("ERROR unlinking, no write access to base directory when trying to  unlink: " + linked_path)
    
    if not os.path.exists(linked_path) or not os.path.isdir(linked_path):
        raise Exception("ERROR unlinking, the linked resource doesn't exist or isn't a directory: " + linked_path)
    
    if not os.path.islink(linked_path):
        raise Exception("ERROR unlinking, the resource to unlink is not a symbolic link: " + linked_path)
    
        
    os.unlink(linked_path)


#parse a file and return the first line that
#doesn't start with a #
def getFirstNonComment(file):     
    with open(file) as f:
        foundLine = ""
        for line in f:
            if not string_helper.isBlank(line):
                checkline = line.strip()
                if not checkline.startswith('#'):
                    foundLine = checkline
                    break
        return foundLine

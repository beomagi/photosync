#!/usr/bin/env python3
"""
This will carry out the following tasks:
1. Check for new files in the SOURCEPICS directory
2. intent is to copy source file, to new file with path containing creation yyyy\mm\dd, and rename the file with creation time.
3. as RAW and JPG files can be created at dofferent times, we'll create a dict with file basename+prefix as key, 
2. for each file prefix, create a dict with prefix:date hh-mm-ss
   The same date will be used for all file types - so the raw, jpg, etc will all have the same timestamp
3. For each file, copy from SOURCEPICS to LOCALSTORE with the new filename - filenameprefix-date.extension
4. quick compare source and destination files to ensure they are the same
if REMOVEONCOPY is true, remove the file from the SOURCEPICS directory
"""

import glob
import os
import datetime
import shutil
import zlib
import time

SOURCEPICS = "G:\\DCIM" #any
LOCALSTORE = "D:\\library\\htdocs\\Pics"
COPYNEWS = True
REMOVEONCOPY = True

#powershell colors
RED="\033[31m"
GREEN="\033[32m"
RESET="\033[0m"


# Ensure the paths end with the correct separator
if (LOCALSTORE[-1] != os.sep): LOCALSTORE = LOCALSTORE+os.sep

if (SOURCEPICS[-1] != os.sep): SOURCEPICS = SOURCEPICS+os.sep

def lzero(number):
    """add a leading zero"""
    strnum = str(number)
    if len(strnum) == 1:
        strnum = "0"+strnum
    return strnum


def get_files(directory):
    """get all files in the directory"""
    print(f"Loading new file list for {directory} ...")
    allfilelist = glob.glob(directory+"**", recursive=True)
    filesonly = []
    for file in allfilelist:
        if os.path.isfile(file):
            filesonly.append(file)
    print(f"Loaded {len(filesonly)} files")
    return filesonly 


def filekey(fullfilepath):
    """create a key using file's base dir and prefix"""
    filename = os.path.basename(fullfilepath)
    prefix, ext = os.path.splitext(filename)
    filebasedir = os.path.dirname(fullfilepath)
    filebasedirsanitized = filebasedir.replace("\\", "").replace("/", "").replace(":", "")
    key=filebasedirsanitized+"_"+prefix
    return key


def create_date_dict(filelist):
    """create a dictionary with file basedir+prefix as key and file creation date as value
    can account for same name files in different directories"""
    date_dict = {}
    for file in filelist:
        if os.path.isfile(file):
            key=filekey(file)
            if key not in date_dict:
                filecttime = os.path.getctime(file)
                filedate = datetime.datetime.fromtimestamp(filecttime)
                filedateYMD = f"{filedate.year}{os.sep}{lzero(filedate.month)}{os.sep}{lzero(filedate.day)}"
                filedateHMS = f"{lzero(filedate.hour)}-{lzero(filedate.minute)}-{lzero(filedate.second)}"
                nd={}
                nd["date"] = filedateYMD
                nd["time"] = filedateHMS
                date_dict[key] = nd
    print(f"Created date dictionary with {len(date_dict)} entries")
    return date_dict


def newfilepath(file, date_dict):
    """create a new filename with the date from the dictionary"""
    filename = os.path.basename(file)
    prefix, ext = os.path.splitext(filename)
    fkey = filekey(file)
    newdirectory = LOCALSTORE + date_dict[fkey]["date"]
    newfilepath = newdirectory + os.sep + prefix +"_"+ date_dict[fkey]["time"] +ext
    return newfilepath


def create_jobs(filelist, date_dict):
    """create a list of jobs to do"""
    joblist = []
    for file in filelist:
        if os.path.isfile(file):
            newfile = newfilepath(file, date_dict)
            joblist.append((file, newfile))
    print(f"Created job list with {len(joblist)} entries")
    return joblist


def create_directory_if_not_exists(newfile):
    """create the directory if it doesn't exist"""
    newdirectory = os.path.dirname(newfile)
    if not os.path.exists(newdirectory):
        os.makedirs(newdirectory)


def copy_files(joblist):
    """copy files from source to destination"""
    total_files = len(joblist)
    print(f"Copying {total_files} files")
    count = 0
    start_time = time.time()
    timeleft = 999
    for file, newfile in joblist:
        if os.path.isfile(file):
            count += 1
            timenow=time.time()
            elapsed_time = timenow - start_time
            if count > 0:
                timeleft = (total_files - count) * elapsed_time / count
            print(f"Copying {file} to {newfile} - {count}/{total_files}. ", end="")
            if COPYNEWS:
                create_directory_if_not_exists(newfile)
                shutil.copy2(file, newfile)
            print(f"est. {timeleft:.2f} seconds")


def adler32sum(filename, blocksize=65536):
    """Calculates the Adler32 checksum of a file efficiently."""
    checksum = 0
    with open(filename, "rb") as f:
        # Read the file in chunks to avoid loading the whole file into memory
        for block in iter(lambda: f.read(blocksize), b""):
            # Update the checksum for each block
            checksum = zlib.adler32(block, checksum)
    return checksum & 0xffffffff # Ensure a positive result


def compare_files(filea, fileb):
    """compare the source and destination files to ensure they are the same"""
    if adler32sum(filea) == adler32sum(fileb):
        return True
    else:
        return False


def compare_files_in_joblist(joblist):
    """compare the source and destination files for each job in the list
    return list of files that match and that don't"""
    failed_files = []
    matched_files = []
    total_files = len(joblist)
    start_time = time.time()
    count = 0
    timeleft = 999
    for file, newfile in joblist:
        count += 1
        timenow=time.time()
        elapsed_time = timenow - start_time
        print(f"Comparing {file} and {newfile} - {count}/{total_files}. ", end="")
        compareflag = compare_files(file, newfile)
        timeleft = (total_files - count) * elapsed_time / count
        print(f"est. {timeleft:.2f} seconds ", end="")
        if compareflag:
            matched_files.append((file, newfile))
            print(f"{GREEN}OK{RESET}")            
        else:
            failed_files.append((file, newfile))
            print(f"{RED}ERROR MISMATCH{RESET}")
    return failed_files, matched_files


def remove_files_from_source(joblist):
    """remove files from the source directory"""
    if REMOVEONCOPY:
        print(f"Removing {len(joblist)} files from source directory")
    else:
        print(f"Skipping removal of {len(joblist)} files from source directory")
        return
    for file, newfile in joblist:
        if os.path.isfile(file):
            print(f"Removing {file}")
            if REMOVEONCOPY:
                os.remove(file)


if __name__ == "__main__":
    global_start_time = time.time()
    newfilelist = get_files(SOURCEPICS)
    date_dict = create_date_dict(newfilelist)
    job_list = create_jobs(newfilelist, date_dict)
    copy_files(job_list)
    failed_files, matched_files = compare_files_in_joblist(job_list)
    remove_files_from_source(matched_files) # Only remove files that matched
    if len(failed_files) > 0:
        print(f"{RED}Some files failed to copy or compare{RESET}")
        for file, newfile in failed_files:
            print(f"{RED}Failed:{RESET} {file} -> {newfile}")
        print("These files have not been removed from the source directory")
    else:
        print(f"{GREEN}All files copied and compared successfully{RESET}")
    global_end_time = time.time()
    global_elapsed_time = global_end_time - global_start_time
    print(f"Total time taken: {global_elapsed_time:.2f} seconds")


import os, stat
import argparse
import sys
import filecmp, shutil
import time
from os.path import *
import threading

SECONDS = 60

class Synchronizer:
    def __init__(self):
        self.dir1 = ""
        self.dir2 = ""
        self.minutesPerriod = 0
        self.logFile = "operations.log"
        self.dcmp = None
        self.removedDirs = 0
        self.removedFiles = 0
        self.removedDirsError = 0
        self.removedFilesError = 0
        self.copiedFiles = 0
        self.copiedDirs = 0 
        self.copiedFilesError = 0
        self.copiedDirsError = 0 
        self.createdDirs = 0
        self.createdDirsError = 0
        self.updatedFiles = 0
        self.updatedFilesError = 0


    def args_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('path1', help="Use a valid path")
        parser.add_argument('path2', help="Use a valid path")
        parser.add_argument('interval', type=int, help="Interval in minutes (Int type)")
        args = parser.parse_args()

        if args.path1 == "" or args.path2 == "":
            sys.exit("Argument Error: Dyrectory paths must be given")
        elif not os.path.isdir(args.path1):
            sys.exit("Argument Error: Source directory does not exist :(")
        elif not os.path.isdir(args.path2):
            sys.exit("Argument Error: Destination directory does not exist :(")
        elif args.interval < 1:
            sys.exit("Argument Error: Interval must be a positive Integer in minutes") 
        else:
            self.dir1 = args.path1
            self.dir2 = args.path2
            self.minutesPerriod = args.interval

    def sycn(self, dir1, dir2, insideDir):
        initFormat = "########################################################################################\n########################################################################################\n"
        date = "This Syncrhonization dates on: " + str(time.ctime(time.time())) + ".\n"
        logFile = None
        try:  #Try to open the existing logFile
            if not insideDir:
                logFile = open(os.path.join(dir1, "operations.log"), 'a')
                printAndLog(initFormat, logFile)
                printAndLog(date, logFile)
        except FileNotFoundError:  #If it does not exits, then create it
            if not insideDir:
                logFile = open(os.path.join(dir1, "operations.log"), 'w')
                printAndLog(initFormat, logFile)
                printAndLog(date, logFile)


        printAndLog("The next operations will be held: \n\n", logFile)

        self.dcmp = filecmp.dircmp(dir1, dir2) #Comparison between both directories
        
        #First, we will delete the files and directories that exist only in the target directory (only right side)
        for f in self.dcmp.right_only:
            path = os.path.join(dir2, f)
            operation = "Deleting file: " + path + " .\n"
            printAndLog(operation, logFile)
            try:
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                        printAndLog("The file " + f + " has been successfully removed from " + dir2 + " .\n", logFile)
                        self.removedFiles += 1
                    except OSError:
                        printAndLog("The file " + f + " no longer exists or can not be removed.\n", logFile)
                        self.removedFilesError += 1
                elif os.path.isdir(path):
                    try:
                        shutil.rmtree(path, True) #with true we will ignore the failed removals (as it is no possible to remove them)
                        printAndLog("The directory " + f + " has been successfully removed from " + dir2 + " .\n", logFile)
                        self.removedDirs += 1
                    except shutil.Error:
                        printAndLog("The file " + f + " no longer exists or can not be removed.\n", logFile)
                        self.removedDirsError += 1
            except Exception:
                printAndLog(f + " is not a file or directory.\n", logFile)
                continue

        #Second, we will copy the files that are only in the source directory to the target one
        for f in self.dcmp.left_only:
            try:
                status = os.stat(os.path.join(dir1, f))
            except os.error:
                continue
            
            if stat.S_ISREG(status.st_mode):
                if not os.path.exists(dir2):
                    try:
                        os.makedirs(dir2)
                        printAndLog("New directory " + dir2 + " has been successfully created.\n", logFile)
                        self.createdDirs +=1
                    except OSError:
                        printAndLog("There has been an error creating directory " + dir2 + " .\n", logFile)
                        self.createdDirsError += 1

                path = os.path.join(dir1, f)
                try:
                    shutil.copy(path, dir2)
                    printAndLog("File " + f + " has been successfully copied in " + dir2 + " .\n", logFile) 
                    self.copiedFiles += 1
                except(IOError, OSError):
                    printAndLog(f + " could not be copied to " + dir2 + " .\n", logFile)
                    self.copiedFilesError += 1

            elif stat.S_ISDIR(status.st_mode):
                dir1New = os.path.join(dir1, f)
                dir2New = os.path.join(dir2, f)
                try:
                    shutil.copytree(dir1New, dir2New)
                    self.copiedDirs += 1
                    printAndLog("The directory " + dir1New + " has been succesfully copied in " + dir2 + " .\n", logFile)
                except shutil.Error:
                    printAndLog("The directory " + dir1New + " could not be created in " + dir2 + " .\n", logFile)
                    self.copiedDirsError += 1
                    continue

        #Finally, we will rewrite files with the same name but different content on them
        for f in self.dcmp.diff_files:
            try:
                status = os.stat(os.path.join(dir1, f))
            except os.error:
                continue
            if stat.S_ISREG(status.st_mode):
                dir1New = os.path.join(dir1, f)
                dir2New = os.path.join(dir2, f)
                try:
                    shutil.copy(dir1New, dir2New)
                    printAndLog("File " + f + " has been successfully updated in " + dir2 + ".\n", logFile) 
                    self.updatedFiles += 1
                except(IOError, OSError):
                    printAndLog(f + " could not be updated to " + dir2 + ".\n", logFile)
                    self.updatedFilesError += 1

            elif stat.S_ISDIR(status.st_mode):
                dir1New = os.path.join(dir1, f)
                dir2New = os.path.join(dir2, f)
                
                self.sycn(self, dir1New, dir2New)

        #And the same for the common directories (sometimes just seen with the common atribute of dcmp)
        for f in self.dcmp.common_dirs:
            try:
                status = os.stat(os.path.join(dir1, f))
            except os.error:
                continue

            if stat.S_ISDIR(status.st_mode):
                dir1New = os.path.join(dir1, f)
                dir2New = os.path.join(dir2, f)
                
                self.sycn(dir1New, dir2New, True)

        
        if logFile != None:
            self.finalReport(logFile)
            printAndLog("\nSynchorinization finished at: " + str(time.ctime(time.time())) + ".\n", logFile)
            printAndLog(initFormat + "\n\n", logFile)
            logFile.close()

    def finalReport(self, logFile):
        report = "Final Report:\n-Copied Files: " + str(self.copiedFiles) + "\n-Copied Files Errors: " + str(self.copiedFilesError) + "\n-Copied Directories: " + str(self.copiedDirs) + "\n-Copied Directories Errors: " + str(self.copiedDirsError) + "\n-Removed Files: " + str(self.removedFiles) + "\n-Removed Files Errors: " + str(self.removedFilesError) + "\n-Updated Files: " + str(self.updatedFiles) + "\n-Updated Files Errors: " + str(self.updatedFilesError) + "\n-Removed Directories: " + str(self.removedDirs) + "\n-Removed Directories Errors: " + str(self.removedDirsError)
        printAndLog(report, logFile)
        self.removedDirs = 0
        self.removedFiles = 0
        self.removedDirsError = 0
        self.removedFilesError = 0
        self.copiedFiles = 0
        self.copiedDirs = 0 
        self.copiedFilesError = 0
        self.copiedDirsError = 0 
        self.createdDirs = 0
        self.createdDirsError = 0
        self.updatedFiles = 0
        self.updatedFilesError = 0
        
            
        

        
            

def printAndLog(text, logFile):
    if logFile != None:
        print(text)
        logFile.write(text)

def main():
    synchronizer = Synchronizer()
    synchronizer.args_parser()
    ticker = threading.Event()
    synchronizer.sycn(synchronizer.dir1, synchronizer.dir2, False)
    while not ticker.wait(SECONDS*synchronizer.minutesPerriod):
        synchronizer.sycn(synchronizer.dir1, synchronizer.dir2, False)

main()
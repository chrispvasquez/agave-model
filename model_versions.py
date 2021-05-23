from jetlag import RemoteJobWatcher
from subprocess import Popen, PIPE
import re
import glob
import json
from command import cmd
from write_env import write_env
import jetlag_conf
import os, sys
        
class HiddenPrint:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open("spack-log.txt", 'a')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

def get_package(pack):
    temp = pack.split('@')
    return temp[0]    
        
def get_versions(model):

    VERSIONS = []

    p = open("spack-info.txt").read()
    for g in re.finditer(r'(\w+)@([\d.]+)', p):
        package = g.group(1)
        version = g.group(2)

        if package == model:
            VERSIONS.append(version)

    return VERSIONS
# Function to get the
# different versions of
# spack packages for
# a given model
          
    
def tarballHandler(tarName):
    mainPath = os.environ["HOME"]+"/agave-model/"
    installedPath = path+"installed_models/"
    folderName = tarName.split('.t')
    # Split the tarball's name according to '.t' since all
    # tarball extensions begin with 't'
    # Ideally, the tarball will be named "model-version.tar/.tgz/.tar.gz"
    os.system("mkdir "+installedPath+folderName[0])
    os.system("tar -xvf "+tarName+" -C "+installedPath+folderName[0])
    os.system("mv "+tarname+" "+installedPath+"tarballs")
    untar_path = installedPath+folderName[0]+"/"
    # Extracted files should be a tarball of the source code
    # for the model and a JSON file containing model details
    return untar_path
           
    
def installNewModels():
    
    newModelsPath = os.environ["HOME"]+"/agave-model/models_to_install"
    print("Finding new models to Build...")
    
    if len(os.listdir(newModelsPath)) != 0:
        print("Preparing to install new models...")
        uv = jetlag_conf.get_uv()
        cmd("rm -fr input.tgz run_dir")
        os.system("mkdir -p run_dir")
        
        spackPackList = []
        
        # Here, we make a list of all the models to be installed according
        # to their respective spack package
        for tarball in os.listdir(newModelsPath):
            tb = os.path.join(tarDir, tarball)
            if os.path.isfile(tb):     
                modelSetupPath = tarballHandler(tb)
                with open(modelSetupPath+"*.json") as f:
                    modelJSON = json.load(f) 
                print("New Model Found and Preparing: " + modelJSON["name"]+"@"+modelJSON["version"])
                spackPackList.append(modelJSON["package"]+'@'+modelJSON["version"])
                # Additionally, we move a copy of the tarball of the
                # model's source code to the run_dir so it can be placed
                # on the server in the proper tarball directory (if needed)
                os.system("cp "+modelSetupPath+ " run_dir --exclude *.json")
                
            print("Installing New Models. This may take a few minutes...")
                
            with HiddenPrint():
                write_env()
                
                with open("run_dir/move-tarballs.sh","w") as v:
                    print("#!/bin/bash", file=v)
                    print("mv *.tar /build-dir/tarballs/", file=v)
                    print("mv *.tgz /build-dir/tarballs/", file=v)
                    print("mv *.tar.gz /build-dir/tarballs/", file=v)
                os.system("chmod 755 run_dir/get-versions.sh")
                
                with open("run_dir/build-models.sh","w") as v:
                    print("#!/bin/bash", file=v)
                    print("source /build-dir/ubuntu_xenial/spack/share/spack/setup-env.sh", file=v)
                    for pack in range(len(spackPackList)):
                        buildCommand = "spack install " + spackPackList[pack]
                        print(buildCommand, file=v)
                os.system("chmod 755 run_dir/get-versions.sh")
                
                with open("run_dir/runapp.sh","w") as fd:
                    print("singularity exec $SING_OPTS --pwd $PWD $IMAGE bash ./move-tarballs.sh", file=fd)
                    print("singularity exec $SING_OPTS --pwd $PWD $IMAGE bash ./build-models.sh", file=fd)
                os.system("tar czvf input.tgz run_dir")
                jobid = uv.run_job("build-models", nx=4, ny=4, nz=1, jtype="queue", run_time="1:00:00")
                uv.wait_for_job(jobid)
                print("Done!")
            gen_spack_pack_list()
    else:
        print("No New Models Found!")
        

def gen_spack_pack_list():
    uv = jetlag_conf.get_uv()
    os.system("rm -fr input.tgz run_dir")
    os.system("mkdir -p run_dir")
    print("Retrieving Model Versions List...")
    print("This may take a few minutes")
    with HiddenPrint():
        write_env()
        with open("run_dir/get-versions.sh","w") as v:
            print("#!/bin/bash", file=v)
            print("source /build-dir/ubuntu_xenial/spack/share/spack/setup-env.sh", file=v)
            print("spack find > spack-info.txt", file=v)
        os.system("chmod 755 run_dir/get-versions.sh")
        with open("run_dir/runapp.sh","w") as fd:
            print("singularity exec $SING_OPTS --pwd $PWD $IMAGE bash ./get-versions.sh", file=fd)
        os.system("tar czvf input.tgz run_dir")
        jobid = uv.run_job("get_model_versions", nx=4, ny=4, nz=1, jtype="queue", run_time="1:00:00")
        uv.wait_for_job(jobid)
        uv.get_file(jobid, "run_dir/spack-info.txt",as_file="spack-info.txt")
    print("Done!\n\n")
    
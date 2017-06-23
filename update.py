from packaging import version
from urllib.request import urlopen
from urllib.error import URLError
import wget
from flask import Flask, jsonify
import logging
from time import sleep
import subprocess
import os
import shutil

SERVER='http://www.marzocca.net'
SRV_FOLDER='/cotg/'
APP_NAME = "cotg.zip"
VER_FILENAME = 'current_version.txt'
srv_version=""
HOME='/home/pi'
	
# check if device is connected to internet	
def internet_on():
    try:
        urlopen(SERVER, timeout=2)
        return True
    except URLError as err: 
        return False


def check_version(curr_version):
	global srv_version
	wget.download(SERVER+SRV_FOLDER+VER_FILENAME,out='/tmp')
	with open('/tmp/'+VER_FILENAME, "r") as f:
		srv_version = f.readline()
	srv_version = srv_version.replace('\n','')
	os.remove('/tmp/'+VER_FILENAME)
	if (version.parse(srv_version) > version.parse(curr_version)):
		return True
	else:
		return False 
		
		
def action_Update():
	logger = logging.getLogger(__name__)
	global srv_version
	
	# Download zip file with new version in /tmp
	try:
		wget.download(SERVER+SRV_FOLDER+APP_NAME, out='/tmp')
	except Exception as e:
		logging.warning("CRITICAL! Aborted update "+ str(e))
		return jsonify(message='Update aborted!\n'+str(e)) ,500
	
	# Unzip new version in /tmp
	try:
		cmd = 'unzip -o /tmp/'+APP_NAME+' -d /tmp'
		subprocess.call(cmd, shell=True)
		os.remove('/tmp/'+APP_NAME)
	except OSError as e:
			logging.warning("CRITICAL! Aborted update "+ str(e))
			os.remove('/tmp/'+APP_NAME)
			return jsonify(message='Update aborted!\n'+str(e)) ,500
			
	# Copy new version over old one	
	src='/tmp/cotg/'
	dest=HOME+'/cotg'
	recursive_overwrite(src,dest)
	
	# Update Successfull!	
	shutil.rmtree(src)
	logging.warning("Update to v. "+srv_version+" successfully performed")
	return("Update to v. "+srv_version+" successfully performed\nPlease restart you device now!")
	
# Can't use copytree here as the directories already exist
def recursive_overwrite(src, dest, ignore=None):
    if os.path.isdir(src):
        if not os.path.isdir(dest):
            os.makedirs(dest)
        files = os.listdir(src)
        if ignore is not None:
            ignored = ignore(src, files)
        else:
            ignored = set()
        for f in files:
            if f not in ignored:
                recursive_overwrite(os.path.join(src, f), 
                                    os.path.join(dest, f), 
                                    ignore)
    else:
        shutil.copyfile(src, dest)	
	
	
	
	
#!/usr/bin/python3


# Camera On The Go
# Fabio Marzocca © 2017

from flask import Flask, abort, flash, redirect, render_template, request, url_for, jsonify, json

import os
import datetime 
from time import sleep
import subprocess
import shutil
import errno
import logging

from update import internet_on, check_version, action_Update


BASE="/media/pi"
EXCLUDE="SETTINGS"
COPYING=False
VERSION="1.0.0"


LOGFORMAT = '%(asctime)s - %(message)s'
path=os.path.dirname(os.path.abspath(__file__))
LOGFILE = path+"/"+'cotg-activity.log'
logging.basicConfig(filename=LOGFILE, format=LOGFORMAT,level=logging.WARN)
logging.warning("Application started")

# myDisk class. Handle all objects for the dest and source disks
class myDisk(object):
	import shlex
	
	def __init__(self, name):
		self.name = name
		fd = os.open(self.name,os.O_RDONLY)
		disk = os.fstatvfs(fd)
		self.totalBytes = float(disk.f_bsize*disk.f_blocks)
		self.totalUsed = float(disk.f_bsize*(disk.f_blocks-disk.f_bfree))
		self.totalAvail = float(disk.f_bsize*disk.f_bfree)
		os.close(fd)

	def diskTotal(self):
		return self.totalBytes
		
	def diskUsed(self):
		return self.totalUsed
		
	def diskAvail(self):
		return self.totalAvail

	def diskName(self):
		return self.name

	def unmountDisk(self):
		try:
			subprocess.check_call(['umount', self.name],stderr= subprocess.STDOUT)  
			print ("Disk: " + self.name +" has been successfully unmounted.")
		except subprocess.CalledProcessError as e:
			print (e.output)

# end class

cotg = Flask(__name__)

def getDrives():
	names = os.listdir(BASE)
	#fill array of disk names
	arr=[]
	for out in names:
        	if out != EXCLUDE:
        		arr.append(BASE + "/" + out)
	return arr
	
def getDestSource(d1,d2):
	# detect which is DEST and SOURCE
	if d1.diskTotal() > d2.diskTotal():
		DestDisk = d1
		SourceDisk = d2
	else:
		DestDisk = d2
		SourceDisk = d1
	return(DestDisk, SourceDisk)

def getArray(disk):
	arr=[]
	label = disk.name.split(BASE)[1]
	arr.append(label)
	tot = disk.diskTotal()/1024/1024/1024
	tot="{0:.2f}".format(tot)
	arr.append(tot)
	used=disk.diskUsed()/1024/1024/1024
	used="{0:.2f}".format(used)
	arr.append(used)
	free=disk.diskAvail()/1024/1024/1024
	free="{0:.2f}".format(free)
	arr.append(free)
	return arr
	
def generateFolderName():
	return (datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
	

@cotg.route('/')
def index():
	drives = getDrives()
	#check if array is <2
	if len(drives) < 2:
		mess = ("Please insert the two USB disks, then press the button.")	
		howmany = len(drives)
		diskname = None
		return redirect(url_for('welcome', mess=mess, howmany=howmany))
	#check if array is > 2
	if len(drives) > 2:
		err = ("USB disks cannot be more than 2!")
		err2 = ("Correct the error and press NEXT")
		return redirect(url_for('error', err=err,err2=err2))
	d1 = myDisk(drives[0])
	d2 = myDisk(drives[1])
	disks=getDestSource(d1,d2)
	destDisk = disks[0]
	sourceDisk = disks[1]
	destArray = getArray(destDisk)
	sourceArray = getArray(sourceDisk)
	return render_template('index.html', deststats=destArray, sourcestats=sourceArray)

# Eject one drive. Drive label name is sent through a
# POST message from FORM in the index page

@cotg.route('/eject', methods=['POST'])
def ejectDisk():
	disk=request.form['disk']
	disk = BASE+disk
	try:
		subprocess.check_call(['umount', disk],stderr= subprocess.STDOUT)  
		logging.warning("Ejected disk: "+disk)
		return redirect(url_for('index'))
	except subprocess.CalledProcessError as e:
		logging.warning("ERROR. Disk: "+disk+" not ejected")
		return redirect(url_for('error', err=e.output))
 
# About. Displays version number and copyright

@cotg.route('/about')
def about():
	mess = "<b>v. "+VERSION+"</b><br /><br />"
	mess = mess+"A computer-free tool to backup your media SD on the field<br />"
	mess = mess + "<br /><span class='copyright'>© Fabio Marzocca - 2017</span><br />"
	return render_template('about.html', mess=mess)
	
@cotg.route('/ejectall')
def ejectall():
	drives = getDrives()
	for i in range(0,len(drives)):
		try:
			subprocess.check_call(['umount', drives[i]],stderr= subprocess.STDOUT) 
			logging.warning("Ejected disk: "+drives[i])
		except subprocess.CalledProcessError as e:
			logging.warning("ERROR. Disk: "+drives[i]+" not ejected")
			return redirect(url_for('error', err=e.output))
	return redirect(url_for('index'))

@cotg.route('/error')
def error():
	err = request.args.get('err')
	try:
		err2 = request.args.get('err2')
	except NameError:
		return render_template('error.html', err=err)
	else:
		return render_template('error.html', err=err, err2=err2)
	
@cotg.route('/', methods=['POST'])
def startCopy():
	source = request.form.getlist('sourcedisk[]')
	dest= request.form.getlist('destdisk[]')
	source[0]=BASE+source[0]
	dest[0]=BASE+dest[0]
	logging.warning("Started copy of " + source[1]+"GB")
	return action_Copy(source[0],dest[0])
		#return ('OK')
		
	
def action_Copy(src,dest):		
		COPYING=True
		folder = generateFolderName()
		dest = dest+"/"+folder
		try:
			shutil.copytree(src,dest, ignore=_feedback)
			src=src.split(BASE)[1]
			COPYING=False
			logging.warning("Disk "+src+ " copied to folder: "+folder)
		except shutil.Error as e:
			COPYING=False
			return jsonify(message='Copy aborted! '+str(e)),500
		except OSError as e:
			COPYING=False
			return jsonify(message='Copy aborted! '+str(e)),500
		return("Successfully copied disk "+src +" to folder: "+folder)

		
# used only to have a feedback of copied folders from copytree		
def _feedback(path, names):
	path=path.split(BASE)[1]
	logging.warning('Copying folder: %s' % path)
	return []   # nothing will be ignored
    
    
def generateFolderName():
	return (datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
	
@cotg.route('/welcome')
def welcome():
	mess = request.args.get('mess')
	howmany= request.args.get('howmany')
	return render_template('welcome.html', mess=mess, howmany=howmany)
	
# Update COTG id the device is connected
@cotg.route('/update')
def update():
	if internet_on()==True:
		if check_version(VERSION)==True:
			logging.warning('An update is available')
			return redirect(url_for('firmware'))
		else:
			mess="Your application is already running latest version"
	else:
		mess = "Can't reach the update server!<br />"
		mess = mess+"<br>Please connect <b>Camera On The Go</b><br />"
		mess = mess+"to internet by a standard ethernet cable<br />"
		mess = mess+"then come back here.<br />"
	return render_template('about.html', mess=mess)
	
# Activity Log
@cotg.route('/activity')
def activity():
	with open(LOGFILE, "r") as f:
		content = f.read()
		content= "<br />".join(content.split("\n"))
		if content=="":
			content = "Activity log file is empty."
	return render_template('activity.html', content=content)

@cotg.route('/clearlog')
def clearlog():
	open(LOGFILE, 'w').close()
	logging.warning("Cleared activity log file")
	return redirect(url_for('activity'))

@cotg.route('/firmware')
def firmware():
	mess="<span style='font-size:60%'>A new version of the application is available<br />"
	mess=mess+"Press the button to upgrade<br>"
	mess=mess+"<b>WARNING</b>: do not interrupt download process once started!</span><br />"
	return render_template('firmware.html', mess=mess)

@cotg.route('/firmware', methods=['POST'])
def firmUpdate():
	return action_Update()

@cotg.route('/poweroff')
def poweroff():
	mess = "Your device is powering off.<br />"
	mess = mess + "Pls wait 7 sec. then	unplug it.</br /><br />"
	logging.warning("Powering off....")
	os.system("sudo poweroff")
	return render_template('about.html', mess=mess)
	
@cotg.context_processor
def include_copyright():
	copyright=get_Copyright()
	return dict(copyright=copyright, version=VERSION, COPYING=COPYING)


# copyright for footer
def get_Copyright():
	#set start to date your site was published
	startCopyright='2017'
	copyright_interval=''
	#check if start year is this year
	now = datetime.datetime.now()
	if str(now.year) == startCopyright:
		copyright_interval = startCopyright
	else:
		copyright_interval = startCopyright + ' - ' + str(now.year)
	return(copyright_interval) 

if __name__ == '__main__':
    cotg.run(debug=True, host='0.0.0.0')


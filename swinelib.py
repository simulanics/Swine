# -*- coding: utf-8 -*-
############################################################################
#    Copyright (C) 2007 by Dennis Schwerdel, Thomas Schmidt                #
#                                                                          #
#                                                                          #
#    This program is free software; you can redistribute it and or modify  #
#    it under the terms of the GNU General Public License as published by  #
#    the Free Software Foundation; either version 2 of the License, or     #
#    (at your option) any later version.                                   #
#                                                                          #
#    This program is distributed in the hope that it will be useful,       #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#    GNU General Public License for more details.                          #
#                                                                          #
#    You should have received a copy of the GNU General Public License     #
#    along with this program; if not, write to the                         #
#    Free Software Foundation, Inc.,                                       #
#    59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             #
############################################################################

import sys, os, shutil, ConfigParser, array, pipes, urllib, subprocess, codecs
import shortcutlib
from tarfile import TarFile
from subprocess import Popen

VERSION = "0.5"

reload(sys)
sys.setdefaultencoding("utf-8")

os.environ['PATH'] += ":" + os.path.dirname(__file__)

SWINE_PATH = os.getenv("HOME") + "/.swine"
SWINE_SLOT_PATH = SWINE_PATH
SWINE_DEFAULT_SLOT_NAME = "DEFAULT"
SWINE_DEFAULT_SLOT_PATH = SWINE_PATH + "/" + SWINE_DEFAULT_SLOT_NAME
SWINE_DEFAULT_SECTION = "__SYSTEM__"
WINE_PATH = os.getenv("HOME") + "/.wine"
WINETRICKS = "winetricks"
WISRUN = os.path.dirname(os.path.realpath(__file__)) + "/wisrun"
DESKTOP_MENU_DIR = os.getenv("HOME") + "/.local/share/applications/swine"

class SwineException(Exception):
	pass

class Shortcut:
	def __init__(self,name,slot,data={}):
		if len(name) == 0:
			raise SwineException ("Shortcut name cannot be empty.")
		self.name = unicode(name)
		if len(data) == 0:
			self.data = {}
		else:
			self.data = data
		self.slot = slot
	
	def __str__(self):
		return self.name
	
	def save (self):
		# NOTE: Slot.saveConfig needs to be called to make this permanent
		section = self.name
		config = self.slot.config
		if not section:
			raise SwineException ( "Shortcut name cannot be empty" )
		if not config.has_section ( section ):
			config.add_section ( section )
		for o in config.options(section):
			config.remove_option(section,o)
		for k, v in self.data.iteritems():
			config.set(section,k,v)
		
	def delete (self):
		# NOTE: Slot.saveConfig needs to be called to make this permanent
		if self.isDefault():
			self.slot.unsetDefaultShortcut()
		self.slot.config.remove_section (self.name)
		self.removeMenuEntry()
		
	def rename (self, newname):
		# NOTE: Slot.saveConfig needs to be called to make this permanent
		newname = unicode(newname)
		if len(newname) == 0:
			raise SwineException ("Shortcut name cannot be empty.")
		if newname == self.name:
			return None
		self.delete ()
		self.name = newname
		self.save ()
		
	def clone (self, newname):
		# NOTE: Slot.saveConfig needs to be called to make this permanent
		newname = unicode(newname)
		if len(newname) == 0:
			raise SwineException ("Shortcut name cannot be empty.")
		shortcut = Shortcut(newname,self.slot,self.data)
		shortcut.save ()

	def run (self,wait=False,args=[]):
		prog=str2args(self.data['program'])
		workingDirectory=self.data['working_directory']
		runInTerminal=self.data.has_key("interminal") and int(self.data["interminal"]) == 1
		desktop=None
		if self.data.has_key("desktop"):
			desktop=self.data["desktop"]
		return self.slot.runWin (prog=prog+args,wait=wait,workingDirectory=workingDirectory,runInTerminal=runInTerminal,desktop=desktop)

	def isDefault (self):
		return ( not self.slot.loadDefaultShortcut() == None ) and self.name == self.slot.loadDefaultShortcut().name
	
	def setDefault (self):
		# NOTE: Slot.saveConfig needs to be called to make this permanent
		self.slot.setDefaultShortcut(self)

	def iconsDir (self):
		if self.data.has_key("iconsdir"):
			return self.slot.getPath() + "/" + self.data["iconsdir"]
		return None

	def extractIcons (self):
		file = self.slot.winPathToUnix(str2args(self.data["program"])[0])
		iconsdir = self.slot.getPath() + "/icons/" + os.path.basename(file)
		if os.path.splitext(file)[1].lower() == '.exe':
			self.data['iconsdir']="icons/" + os.path.basename(file)
			self.slot.extractExeIcons ( file, iconsdir )
	
	def hasMenuEntry (self):
		file_name = DESKTOP_MENU_DIR + "/" + self.slot.name + "-" + self.name + ".desktop"
		return os.path.exists(file_name)
	
	def createMenuEntry (self):
		if not os.path.exists (DESKTOP_MENU_DIR):
			os.mkdir (DESKTOP_MENU_DIR)
		file_name = DESKTOP_MENU_DIR + "/" + self.slot.name + "-" + self.name + ".desktop"
		file = open ( file_name, "w" )
		file.write("[Desktop Entry]\nEncoding=UTF-8\nVersion=1.0\n")
		file.write("Name="+self.slot.name+": "+self.name+"\n")
		file.write("Type=Application\n")
		file.write("Exec=swinecli --slot \""+self.slot.name+"\" --shortcut \""+self.name+"\" --translate-paths --run %U\n")
		file.write("Icon="+self.data["icon"]+"\n")
		file.write("Categories=Wine;\n")
		file.close()
		
	def removeMenuEntry (self):
		file_name = DESKTOP_MENU_DIR + "/" + self.slot.name + "-" + self.name + ".desktop"
		if self.hasMenuEntry():
			os.remove(file_name)


class Slot:
	def __init__(self, name):
		if len(name) == 0:
			raise SwineException ("Slot name cannot be empty.")
		self.name = unicode(name)
		self.config = None
		self.settings = None
		
	def __str__(self):
		return self.name
		
	def getPath(self):
		return SWINE_SLOT_PATH + "/" + self.name

	def getDrivePath(self, drive):
		drive = drive.lower()
		if len(drive) == 1:
			drive = drive + ":"
		if not len(drive) == 2:
			raise SwineException (drive + " is not a valid drive")
		if not os.path.exists ( self.getPath() + "/dosdevices/" + drive ):
			raise SwineException (drive + " does not exist")
		return self.getPath() + "/dosdevices/" + drive
	
	def getDosDrivesPath(self):
		return self.getPath() + "/dosdevices"
	
	def getConfigFile(self):
		return SWINE_SLOT_PATH + "/" + self.name + "/swine.ini"

	def loadConfig(self):
		self.config = ConfigParser.ConfigParser()
		if os.path.exists(self.getConfigFile()):
			self.config.readfp(codecs.open(self.getConfigFile(), "r", "utf8"))
		if not self.config.has_section ( SWINE_DEFAULT_SECTION ):
			self.config.add_section ( SWINE_DEFAULT_SECTION )
		self.settings = dict(self.config.items(SWINE_DEFAULT_SECTION))

	def saveConfig(self):
		# NOTE: This needs to be called after any Shortcut changes to make them permanent
		for k, v in self.settings.iteritems():
			self.config.set(SWINE_DEFAULT_SECTION,k,v)
		self.config.write ( open ( self.getConfigFile(), "w" ) )

	def exists (self):
		return os.path.exists ( self.getPath() )
	
	def create (self):
		if self.exists():
			raise SwineException ("Slot already exists: " + unicode(self.name))
		os.mkdir(self.getPath())
		self.loadConfig()
		self.saveConfig()
	
	def delete (self):
		if self.name == SWINE_DEFAULT_SLOT_NAME:
			raise SwineException ("Default slot cannot be deleted")
		if not self.exists ():
			raise SwineException ("Slot does not exist: " + unicode(self.name))
		for s in self.getAllShortcuts():
			s.delete()
		shutil.rmtree ( self.getPath() )

	def clone (self,newname):
		newname = unicode(newname)
		if len(newname) == 0:
			raise SwineException ("Slot name cannot be empty.")
		if not self.exists():
			raise SwineException ("Slot does not exist: " + unicode(self.name))
		if Slot(newname).exists():
			raise SwineException ("Slot does already exist: " + unicode(newname))
		shutil.copytree ( self.getPath(), Slot(newname).getPath(), True )

	def rename (self,newname):
		newname = unicode(newname)
		if len(newname) == 0:
			raise SwineException ("Slot name cannot be empty.")
		if self.name == SWINE_DEFAULT_SLOT_NAME:
			raise SwineException ("Default slot cannot be renamed")
		if not self.exists():
			raise SwineException ("Slot does not exist: " + unicode(self.name))
		if Slot(newname).exists():
			raise SwineException ("Slot does already exist: " + unicode(newname))
		shortcutMenus = []
		for s in self.getAllShortcuts():
			if s.hasMenuEntry():
				shortcutMenus.append(s)
				s.removeMenuEntry()
		shutil.move ( self.getPath(), Slot(newname).getPath() )
		self.name = newname
		for s in shortcutMenus:
			s.createMenuEntry()

	def getAllShortcuts (self):
		shortcuts = []
		for section in self.config.sections():
			if not section == SWINE_DEFAULT_SECTION:
				shortcuts.append ( self.loadShortcut ( section ) )
		return shortcuts
		
	def loadShortcut (self,name):
		if not self.config.has_section (name ):
			return None
		return Shortcut ( name, self, dict(self.config.items(name)))
	
	def loadDefaultShortcut (self):
		try:
			return self.loadShortcut ( self.settings['default_shortcut'] )
		except:
			return None
	
	def setDefaultShortcut (self,shortcut):
		# NOTE: saveConfig needs to be called to make this permanent
		self.settings['default_shortcut'] = shortcut.name
	
	def unsetDefaultShortcut (self):
		# NOTE: saveConfig needs to be called to make this permanent
		self.settings['default_shortcut'] = None
	
	def extractExeIcons (self, file, iconsdir, onlyNr=None):
		if not os.path.exists ( iconsdir ):
			os.makedirs ( iconsdir )
		if onlyNr == None:
			self.runNative (["wrestool","-x","-t14","--output",iconsdir,file],wait=True)
		else:
			self.runNative (["wrestool","-x","-t14","-n"+str(onlyNr),"--output",iconsdir,file],wait=True)
		files = os.listdir ( iconsdir )
		for file in files:
			if os.path.splitext(file)[1].lower() == '.ico':
				self.runNative (["icotool","-x","-o",iconsdir,iconsdir+"/"+file],wait=True)
				os.remove(iconsdir+"/"+file)
	
	def createShortcutFromFile (self, file):
		if not os.path.exists ( file ):
			file = self.winPathToUnix(file)
		if not os.path.exists ( file ):
			raise Exception ( "File does not exist" )
		lnk = shortcutlib.readlnk ( file )
		name = os.path.splitext(os.path.basename(file))[0]
		shortcut = Shortcut(name,self)
		prg = [lnk['target']]
		prg.extend ( str2args ( lnk['command_line_arguments'] ) )
		shortcut.data['program']=str(prg)
		shortcut.data['working_directory']=lnk['working_directory']
		#shortcut.data['description']=lnk['description']
		if str(lnk['custom_icon']):
			file = self.winPathToUnix(lnk['custom_icon'],"c:\windows")
		else:
			file = self.winPathToUnix(lnk['target'])
		iconsdir = self.getPath() + "/icons/" + os.path.basename(file)
		shortcut.data['iconsdir']="icons/" + os.path.basename(file)
		if os.path.splitext(file)[1].lower() == '.exe':
			self.extractExeIcons ( file, iconsdir, lnk['icon_number'] )
			icons = os.listdir ( iconsdir )
			if len(icons) == 0:
				self.extractExeIcons ( file, iconsdir )
				icons = os.listdir ( iconsdir )
        			icons.sort()
        		best = [ i for i in icons if i.find("32x32x8") > -1 ]
			if len(best) >= 1:
				shortcut.data['icon'] = iconsdir + "/" + best[0]
			else:
				shortcut.data['icon'] = iconsdir + "/" + icons[0]
		else:
			shortcut.data['icon'] = self.winPathToUnix ( file )
		if not os.path.exists ( shortcut.data['icon'] ):
			shortcut.data['icon'] = ""
		else:
			shortcut.data['icon'] = relpath(shortcut.data['icon'],self.getPath())
		return shortcut

	def findShortcutsCallback ( self, shortcuts, dirname, fnames ):
		for file in fnames:
			if os.path.splitext(file)[1].lower() == ".lnk":
				try:
					shortcuts.append(self.createShortcutFromFile(os.path.join(dirname,file)))
				except Exception, inst:
					print os.path.join(dirname,file) + ": " + str(inst)
	
	def findShortcuts (self,exeonly=False):
		shortcuts = []
		os.path.walk(self.getPath()+"/drive_c",self.findShortcutsCallback,shortcuts)
		if exeonly:
			for shortcut in shortcuts:
				if not os.path.splitext(str2args(shortcut.data['program'])[0])[1].lower() == '.exe':
					shortcuts.remove ( shortcut )
		return shortcuts

	def runNative (self, prog, cwd=None, wait=False, env=None, stdin=None, stdout=None, stderr=None):
		"""Run any native program (no windows binaries)
		Parameters:
			prog: this is the program with all paramters as a list
			cwd: the working directory (unix-path)
			wait: wait until the process terminates
			env: custom environment, NOTE: this overwrites the normal environment
			stdin, stdout, stderr: if this is set to "subprocess.PIPE" a new pipe is created to be accessed later
			                       if this is set to a file descriptor, the file is used as input/output
		"""
		if cwd == None and self.exists():
			cwd = self.getPath()
		proc = Popen ( prog, stdin=stdin, stderr=stderr, stdout=stdout, cwd=cwd, env=env)
		if wait:
			proc.wait()
		return proc
	
	def runWineTool (self, prog, cwd=None, wait=False, stdin=None, stdout=None, stderr=None, debug=None):
		"""Run a wine tool (eg wine itself) with prefix and debug environment set
		This is only a wrapper for runNative
		"""
		env = os.environ
		env["WINEPREFIX"] = self.getPath()
		env["WINEDEBUG"] = "err+all,warn-all,fixme-all,trace-all"
		global WINE_WRAPPER
		if WINE_WRAPPER and os.path.exists(self.getPath()):
			open(self.getPath()+"/.no_prelaunch_window_flag","wc").close()
		if debug:
			env["WINEDEBUG"] = debug
		return self.runNative ( prog, cwd, wait, env, stdin, stdout, stderr )

	def runWis (self, file):
		env = os.environ
		env["WINEPREFIX"] = self.getPath()
		env["SLOT"] = self.name
		return self.runNative ( ["xterm","-T","WIS","-hold","-e",WISRUN,file], cwd=".", wait=True, env=env )
	
	def runWinetricks (self, prog):
		"""Run a winetricks command
		This is only a wrapper for runNative
		"""
		return self.runWineTool (["xterm", "-T", "Winetricks "+str(prog), "-hold", "-e", WINETRICKS, str(prog)])
	
	def runWin (self,prog,workingDirectory=".",wait=False,runInTerminal=False,desktop=None,debug=None,log=None):
		"""Run a windows program
		Parameters:
			prog: this is the program with all paramters as a list
			workingDirectory: the working directory, unix- and windows-paths will work
			wait: wait until the process terminates
			runInTerminal: if this is set the wine call is done with wineconsole instead of wine
			debug: user-defines WINEDEBUG-String (see wine manpage)
			log: if this is set, wine stderr output will be written to that file
			desktop: if this is set, program will be run in a window
		"""
		if not os.path.splitext(prog[0])[1].lower() == ".exe":
			prog.insert(0,"start")
			if wait:
				prog.insert(1,"/W")
		if desktop:
			prog.insert(0,"explorer")
			prog.insert(1,"/desktop="+desktop)
		if runInTerminal:
			prog.insert(0,"wineconsole")
			prog.insert(1,"--backend=user")
		else:
			prog.insert(0,"wine")
		cwd = None
		if os.path.exists(workingDirectory):
			cwd = workingDirectory
		if os.path.exists(self.winPathToUnix(workingDirectory)):
			cwd = self.winPathToUnix(workingDirectory)
		stderr = None
		if log:
			stderr = open(log,"w")
		return self.runWineTool (prog, cwd, wait=wait, stderr=stderr, debug=debug)	
		
	def runWinecfg (self):
		return self.runWineTool (["wine", "winecfg"],wait=False)

	def runRegedit (self):
		return self.runWineTool (["wine", "regedit"],wait=False)
	
	def runWineboot (self):
		return self.runWineTool (["wine", "wineboot"],wait=False)
		
	def runWinefile (self,directory="C:"):
		return self.runWineTool (["wine", "winefile",directory],wait=False)
	
	def runUninstaller (self):
		return self.runWineTool (["wine", "uninstaller"],wait=False)
		
	def runWineControl (self):
		return self.runWineTool (["wine", "control"],wait=False)
	
	def runEject (self):
		return self.runWin (["wine", "eject"],wait=False)
	
	def winPathToUnix (self,path,basedir=None):
		if basedir:
			basedir = self.winPathToUnix ( basedir )
		return self.runWinePath (["wine", "winepath","-u",path],basedir)
	
	def unixPathToWin (self,path,basedir=None):
		return self.runWinePath (["wine", "winepath","-w",path],basedir)

	def runWinePath (self,prog,basedir):
		proc = self.runWineTool (prog,wait=True,stdout=subprocess.PIPE,cwd=basedir)
		output = proc.communicate()[0][:-1] #cut the last \n
		if len(output.split("\n")) > 1: #workaround for broken output of winelauncher
			return output.split("\n")[1]
		else:
			return output

	def exportData (self,file):
		if len(file) == 0:
			raise SwineException ("File name cannot be empty.")
		os.chdir(self.getPath ())
		tar = TarFile.gzopen ( file, "w" )
		tar.add ( "." ) #recursive
		tar.close ()

	def importData (self, file):
		if len(file) == 0:
			raise SwineException ("File name cannot be empty.")
		os.chdir(self.getPath ())
		tar = TarFile.gzopen ( file, "r" )
		for file in tar:
			tar.extract(file)
		tar.close ()
		self.loadConfig()
		
def importSlot (name, file):
	if len(file) == 0:
		raise SwineException ("File name cannot be empty.")
	slot = Slot ( name )
	slot.create()
	os.chdir(slot.getPath ())
	tar = TarFile.gzopen ( file, "r" )
	for file in tar:
		tar.extract(file)
	tar.close ()
	slot.loadConfig()
	return slot

def str2args ( s ):
	"""Convert a string-encoded list to a real list
	This understands 2 formats of string encoded lists:
		- The normal representation as understood by the python parser (eg "['a','b','c']")
		- Space separated representation (eg "a b c")
	"""
	if len(s) == 0:
		return []
	if s[0] == "[":
		try:
			return eval ( s )
		except Exception:
			pass
	return s.split ( " " )

def relpath(target, base=os.curdir):
    """
    Return a relative path to the target from either the current dir or an optional base dir.
    Base can be a directory specified either as absolute or relative to current dir.
    """

    if not os.path.exists(target):
        raise OSError, 'Target does not exist: '+target

    if not os.path.isdir(base):
        raise OSError, 'Base is not a directory or does not exist: '+base

    base_list = (os.path.abspath(base)).split(os.sep)
    target_list = (os.path.abspath(target)).split(os.sep)

    # On the windows platform the target may be on a completely different drive from the base.
    if os.name in ['nt','dos','os2'] and base_list[0] <> target_list[0]:
        raise OSError, 'Target is on a different drive to base. Target: '+target_list[0].upper()+', base: '+base_list[0].upper()

    # Starting from the filepath root, work out how much of the filepath is
    # shared by base and target.
    for i in range(min(len(base_list), len(target_list))):
        if base_list[i] <> target_list[i]: break
    else:
        # If we broke out of the loop, i is pointing to the first differing path elements.
        # If we didn't break out of the loop, i is pointing to identical path elements.
        # Increment i so that in all cases it points to the first differing path elements.
        i+=1

    rel_list = [os.pardir] * (len(base_list)-i) + target_list[i:]
    return os.path.join(*rel_list)

def init ():
	if not os.path.exists ( SWINE_PATH ):
		os.mkdir ( SWINE_PATH )
		print "created " + SWINE_PATH
	if not os.path.exists ( SWINE_SLOT_PATH ):
		os.mkdir ( SWINE_SLOT_PATH )
		print "created " + SWINE_SLOT_PATH
	if not os.path.exists ( SWINE_DEFAULT_SLOT_PATH ) and os.path.exists ( WINE_PATH ):
		os.symlink ( WINE_PATH, SWINE_DEFAULT_SLOT_PATH )
		print "symlinked " + SWINE_DEFAULT_SLOT_PATH + " to " + WINE_PATH
	global WINE_WRAPPER
	WINE_WRAPPER = (os.popen('file `which wine`', 'r').read().find('text') != -1)

def getAllSlots ():
	slist = os.listdir ( SWINE_SLOT_PATH )
	slist.sort()
	slots = []
	for slot in slist:
		if os.path.isdir(SWINE_SLOT_PATH+"/"+slot):
			slots.append ( loadSlot(slot) )
	return slots

def loadSlot (name):
	slot = Slot(name)
	if not slot.exists():
		raise SwineException ("Slot does not exist: " + name)
	slot.loadConfig()
	return slot

def loadDefaultSlot ():
	return loadSlot ( SWINE_DEFAULT_SLOT_NAME )

try:
	init()
except Exception, data:
	print data
	sys.exit(-1)

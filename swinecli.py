#!/usr/bin/env python

############################################################################
#    Copyright (C) 2007-2012 by Dennis Schwerdel, Thomas Schmidt           #
#                                                                          #
#                                                                          #
#    This program is free software; you can redistribute it and#or modify  #
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

import os, sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import swinelib, getopt
from swinelib import *

def usage():
  print '''Usage:
  -l  --list				List all slots or all shortcuts if --slot is specified
  -s  --slot SLOT			Selects a slot
  -S  --shortcut SHORTCUT		Selects a shortcut
  -t  --translate-paths			Translates paths to windows format
  -r  --run ARGS			Runs a shortcut
  -R  --run-direct PROGRAM ARGS		Runs a program
  -w  --run-wis PROGRAM			Runs a program
    --import-lnk FILE			Imports a .lnk file
'''

class Mode:
  Nothing = 0
  List = 1
  Run = 2
  RunDirect = 3
  RunWis = 4
  ImportLnk = 5

try:
  opts, otherargs = getopt.getopt(sys.argv[1:], "hls:S:rR:tw:", ["help", "list", "slot=", "shortcut=", "run", "run-direct=", "import-lnk=", "translate-paths", "run-wis="])
except getopt.GetoptError:
  # print help information and exit:
  usage()
  sys.exit(1)

slot_name = None
slot = None
shortcut_name = None
shortcut = None
mode = Mode.Nothing
program = None
path = None
translate_paths = False

for opt, val in opts:
  if opt in ("-h", "--help"):
    usage()
    sys.exit(0)
  elif opt in ("-s","--slot"):
    slot_name = val
  elif opt in ("-S","--shortcut"):
    shortcut_name = val
  elif opt in ("-l","--list"):
    mode = Mode.List
  elif opt in ("-t","--translate-paths"):
    translate_paths = True
  elif opt in ("-r","--run"):
    mode = Mode.Run
  elif opt in ("-R","--run-direct"):
    mode = Mode.RunDirect
    program = val
  elif opt in ("-w","--run-wis"):
    mode = Mode.RunWis
    path = val
  elif opt in ("--import-lnk"):
    mode = Mode.ImportLnk
    path = val

if slot_name:
  slot = loadSlot(slot_name)
  if not slot:
    print "Slot %s does not exist" % slot_name
    sys.exit(2)

def need_slot():
  global slot
  if not slot:
    print "Need to specify the slot"
    sys.exit(2)

if shortcut_name:
  need_slot()
  shortcut = slot.loadShortcut(shortcut_name)
  if not shortcut:
    print "Shortcut %s does not exist" % shortcut_name
    sys.exit(3)

def need_shortcut_def ():
  need_slot()
  global shortcut, slot, slot_name
  if not shortcut:
    shortcut = slot.loadDefaultShortcut()
    if not shortcut:
      print "Slot %s does not have a default shortcut" % slot_name
      sys.exit(3)

def need_shortcut():
  need_slot()
  global shortcut, slot, slot_name
  if not shortcut:
    print "Need to specify the shortcut"
    sys.exit(3)

if translate_paths:
  for i in xrange(0, len(otherargs)):
    if os.path.exists(otherargs[i]):
      otherargs[i] = slot.unixPathToWin(otherargs[i])

try:
  if mode == Mode.List:
    if slot:
      for shortcut in slot.getAllShortcuts():
        if shortcut.isDefault():
          print "%s(default)\tCommand: %s" % (shortcut.getName(), " ".join(shortcut.getProgram()))
        else:
          print "%s\tCommand: %s" % (shortcut.getName(), " ".join(shortcut.getProgram()))
    else:
      for slot in getAllSlots():
        print slot.getName()
  elif mode == Mode.Run:
    need_shortcut_def()
    shortcut.run(args=otherargs)
  elif mode == Mode.RunDirect:
    need_slot()
    slot.runWin([program]+atherargs)
  elif mode == Mode.RunWis:
    need_slot()
    slot.runWis(path)
  elif mode == Mode.ImportLnk:
    need_slot()
    slot.createShortcutFromFile(path)
  else:
    usage()
except Exception, ex:
  print ex

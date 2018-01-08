# coding=utf-8

# the following functions are lifted in whole or in part from the preheat plugin:
# https://github.com/marian42/octoprint-preheat
#  -- parse_temp
#  -- get_temperatures
#  -- preheat_bed
#  -- preheat_tools

from __future__ import absolute_import

import re
import octoprint.plugin
from octoprint.events import Events
from octoprint.util.comm import strip_comment
import sys

this = sys.modules[__name__]

this.temperatures=dict()
this.paused=False

class PrintrbotError(Exception):
    def __init__(self, message):
	super(PrintrbotError, self).__init__(message)

class Printrbot_simple_proPlugin(octoprint.plugin.StartupPlugin,
                             octoprint.plugin.EventHandlerPlugin):

    def on_event(self, event, payload):
        self._logger.info("received event: " + event);
        if event is Events.PRINT_STARTED:
            this.paused=True
            self.get_temperatures()
            self.preheat_bed()
            self._printer.pause_print()

    def command_filter(self,comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        """
        Filter out commands that g2core does not accept
        """
        supported_m = [0,1,2,3,4,5,6,7,8,9,18,20,21,22,23,30,48,50,51,60,100,101,82,83,84,85,104,105,106,107,108,109,110,111,114,115,117,140,190]
        supported_g = [0,1,2,3,4,10,17,18,19,20,21,28,29,30,38,40,43,53,54,55,5,57,58,59,61,64,80,90,91,92,93,94]
    
        if cmd.startswith('M'):
            match = re.search('M(\d*)',cmd)
            if match is not None:
                if int(match.group(1)) not in supported_m:
                    self._logger.info("Rejecting unknown M code:" + match.group(1))
                    return None,
        if cmd.startswith('G'):
            match = re.search('G(\d*)',cmd)
            if match is not None:
                if int(match.group(1)) not in supported_g:
                    self._logger.info("Rejecting unknown G code: " + match.group(1))
                    return None,

    def received_filter(self,comm_instance, line, *args, **kwargs):
        """
        parse received messages
        """
        errmatch = re.search("\"er\".*msg\".\"(.*)\"}}", line)
        if this.paused and self._printer.is_paused():
            match = re.search("B:(\d+\.\d+)", line)
            if match is not None:
                temp = match.group(1);
                if float(temp) >= float(this.temperatures["bed"]-0.5):
                    this.paused=False
                    self._printer.resume_print()
                elif float(temp) >= (float(this.temperatures["bed"]) - 10):
                    self.preheat_tools()
        elif errmatch is not None:
            self._printer.commands(["M2",])        
        return line

    def on_after_startup(self):
        self._logger.info("Simple Pro Was Here")

    def parse_temp(self, line):
	line = strip_comment(line)

        tool = "tool0"
	temperature = None
	for item in line.split(" "):
	    if item.startswith("S"):
		try:
		    value = float(item[1:])
		    if value > 0:
			temperature = value
		except ValueError:
		    self._logger.warn("Error parsing heat command: {}".format(line))
		    pass
		if item.startswith("T"):
		    tool = "tool" + item[1:].strip()
	return tool, temperature

    def get_temperatures(self):
	printer = self._printer

	if (printer.get_current_job()["file"]["path"] == None):
	    raise PrintrbotError("No gcode file loaded.")

	file_name = printer.get_current_job()["file"]["path"]

	if printer.get_current_job()["file"]["origin"] != octoprint.filemanager.FileDestinations.LOCAL:
	    raise PrintrbotError("Can't read the temperature from a gcode file stored on the SD card.")
        path_on_disk = octoprint.server.fileManager.path_on_disk(octoprint.filemanager.FileDestinations.LOCAL, file_name)

	file = open(path_on_disk, 'r')
	line = file.readline()
	max_lines = 1000
	try:
	    with open(path_on_disk, "r") as file:
		while max_lines > 0:
		    line = file.readline()
		    if line == "":
			break
		    if (line.startswith("M104") or line.startswith("M109")):	# Set tool temperature
			tool, temperature = self.parse_temp(line)
			if temperature != None and tool not in this.temperatures:
                            self._logger.info("Setting Preheat: Tool " + tool + " to " + str(temperature))
			    this.temperatures[tool] = temperature
		    if (line.startswith("M190") or line.startswith("M140")):	# Set bed temperature
			_, temperature = self.parse_temp(line)
			if temperature != None and "bed" not in this.temperatures:
                            self._logger.info("Setting Preheat: Bed to " + str(temperature))
			    this.temperatures["bed"] = temperature
		    max_lines -= 1
	except:
	    self._logger.exception("Something went wrong while trying to read the preheat temperature from {}".format(path_on_disk))

	if len(this.temperatures) == 0:
	    raise PrintrbotError("Could not find a preheat command in the gcode file.")
		
    def preheat_bed(self):
	if not self._printer.is_operational():
	    raise PrintrbotError("Can't set the temperature because the printer is not ready.")

	try:
            if "bed" in this.temperatures:
                self._logger.info("Preheating bed to " + str(this.temperatures["bed"]))
		self._printer.set_temperature("bed", this.temperatures["bed"])

	except PrintrbotError as error:
	    raise PrintrbotError(str(error.message))

    def preheat_tools(self):
	if not self._printer.is_operational():
	    raise PrintrbotError("Can't set the temperature because the printer is not ready.")

	try:
	    for key in this.temperatures:
		self._logger.info("Preheating " + key + " to " + str(this.temperatures[key]))
		self._printer.set_temperature(key, this.temperatures[key])

	except PrintrbotError as error:
	    raise PrintrbotError(str(error.message))
        

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Octoprint Simple Pro"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = Printrbot_simple_proPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        'octoprint.comm.protocol.gcode.sending': __plugin_implementation__.command_filter,
        'octoprint.comm.protocol.gcode.received': __plugin_implementation__.received_filter,
    }


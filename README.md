# Printrbot Simple Pro support for OctoPrint

This plugin makes it easier to use your Printrbot Simple Pro with Octoprint.

**NOTE:** You still need to set a few more settings after installing
this plugin to make it work. See below.

## Installation

```bash
pip install octoprint-wtf-plugin
```

## Recommended Configuration

* _Serial Connection_ > Not only cancel ongoing prints [mumble] > _*uncheck*_

## What this plugin does:

* Changes "Print" to "Preheat and print". My Simple Pro pauses on an M190, but continues to accept commands into it's buffer for a time. It also does not report back temperatures as warms. This plugin changes the "Print" button to behave as follows:
    1. Pause Print
    1. Preheat Bed
    1. When bed gets to within 10 degrees of warm, preheat tools
    1. When bed gets to within 0.5 degrees of warm, resume print
* Filter out unsupported M codes.
* Catch Alarms:
    1. Clear alarm state
    1. Pass error through and allow Octoprint to handle it as configured.
* TODO: Add G55 offset to configuration page ... that way WHEN it changes you don't have to edit or regenerate all your gcode files.

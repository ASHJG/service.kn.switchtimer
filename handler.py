#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import time
import datetime
import xbmc, xbmcaddon, xbmcgui
import os
import operator
import json

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

__IconDefault__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'default.png'))
__IconAlert__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'alert.png'))
__IconOk__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'ok.png'))

__confirmTmrAdded__ = True if __addon__.getSetting('confirmTmrAdded').upper() == 'TRUE' else False

OSD = xbmcgui.Dialog()
OSDProgress = xbmcgui.DialogProgress()
HOME = xbmcgui.Window(10000)

__timer__ = xbmc.translatePath(os.path.join('special://userdata', 'addon_data', __addonid__, 'timer.json'))
__timerdict__ = {'channel': None, 'icon': None, 'date': None, 'title': None, 'plot': None}

def putTimer(timers):
    for timer in timers:
        if not timer['utime']: timers.pop(0)
    with open(__timer__, 'w') as handle:
        json.dump(timers, handle)

def getTimer():
    try:
        with open(__timer__, 'r') as handle:
            timers = json.load(handle)
    except IOError:
        return []
    return timers

def getSetting(setting):
    return __addon__.getSetting(setting)

def getDateFormat():
    df = xbmc.getRegion('dateshort')
    tf = xbmc.getRegion('time').split(':')

    try:
        # time format is 12h with am/pm
        return df + ' ' + tf[0][0:2] + ':' + tf[1] + ' ' + tf[2].split()[1]
    except IndexError:
        # time format is 24h with or w/o leading zero
        return df + ' ' + tf[0][0:2] + ':' + tf[1]

def notifyLog(message, level=xbmc.LOGDEBUG):
    xbmc.log('[%s]: %s' % (__addonid__, message.encode('utf-8')), level)

def notifyOSD(header, message, icon=__IconDefault__, time=5000):
    OSD.notification(header.encode('utf-8'), message.encode('utf-8'), icon, time)

def date2timeStamp(date, format=getDateFormat()):
    try:
        dtime = datetime.datetime.strptime(date, format)
    except TypeError:
        try:
            dtime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, format)))
        except ValueError:
            notifyLog('Couldn\'t parse date: %s' % (date), xbmc.LOGERROR)
            notifyOSD(__LS__(30000), __LS__(30020), icon=__IconAlert__)
            return False
    except Exception:
        notifyLog('Couldn\'t parse date: %s' % (date), xbmc.LOGERROR)
        notifyOSD(__LS__(30000), __LS__(30020), icon=__IconAlert__)
        return False
    return int(time.mktime(dtime.timetuple()))

def setTimer(params):
    utime = date2timeStamp(params['date'])
    if not utime: return False

    if int(time.time()) > utime:
        notifyLog('Timer date is in the past')
        notifyOSD(__LS__(30000), __LS__(30022), icon=__IconAlert__)
        return False

    timers = getTimer()
    for timer in timers:
        if date2timeStamp(timer['date']) == utime:
            notifyLog('Timer already set')
            notifyOSD(__LS__(30000), __LS__(30023), icon=__IconAlert__)
            return False

    if len(timers) > 9:
        notifyLog('Timer limit exceeded, no free slot', xbmc.LOGERROR)
        notifyOSD(__LS__(30000), __LS__(30024), icon=__IconAlert__)
        return False

    # append timer and sort timerlist

    params['utime'] = utime
    timers.append(params)
    timers.sort(key=operator.itemgetter('utime'))

    _idx = 0
    for prefix in ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9']:

        if _idx < len(timers):
            # Set properties
            for element in __timerdict__:
                try:
                    HOME.setProperty('%s:%s' % (prefix, element), timers[_idx][element])
                except KeyError:
                    pass
            _idx += 1
        else:
            # Clear properties
            clearTimerProperties(prefix)

    putTimer(timers)
    HOME.setProperty('SwitchTimerActiveItems', str(_idx))
    notifyLog('Timer added @%s, %s, %s' % (params['date'], params['channel'].decode('utf-8'), params['title'].decode('utf-8')))
    notifyLog('Plot: %s...' % (params['plot'].decode('utf-8')[0:63]))
    if __confirmTmrAdded__: notifyOSD(__LS__(30000), __LS__(30021), icon=__IconOk__)
    return True

def clearTimerProperties(prefix=None):
    if not prefix:
        for prefix in ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9']:
            for element in __timerdict__: HOME.clearProperty('%s:%s' % (prefix, element))
        timers = []
        notifyLog('Properties of all timers deleted, timerlist cleared')
    else:
        date = HOME.getProperty('%s:date' % (prefix))
        timers = getTimer()
        for timer in timers:
            if timer['date'] == date: timer['utime'] = None
            for element in __timerdict__: HOME.clearProperty('%s:%s' % (prefix, element))
            notifyLog('Properties for timer %s @%s deleted' % (prefix, date))

    putTimer(timers)
    return True

if __name__ ==  '__main__':

    notifyLog('Parameter handler called')
    try:
        if sys.argv[1]:
            args = {'action':None, 'channel':'', 'icon': '', 'date':'', 'title':'', 'plot': ''}
            pars = sys.argv[1:]
            for par in pars:
                try:
                    item, value = par.split('=')
                    args[item] = value.replace(',', '&comma;')
                    notifyLog('Provided parameter %s: %s' % (item, args[item]), xbmc.LOGDEBUG)
                except ValueError:
                    args[item] += ', ' + par
            if args['action'] == 'add':
                if not setTimer(args):
                    notifyLog('Timer couldn\'t or wouldn\'t set', xbmc.LOGERROR)
            elif args['action'] == 'del':
                clearTimerProperties(args['timer'])
            elif args['action'] == 'delall':
                for prefix in ['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't8', 't9']: clearTimerProperties()
    except IndexError:
            notifyLog('Calling this script without parameters is not allowed', xbmc.LOGERROR)
            OSD.ok(__LS__(30000),__LS__(30030))
    except Exception, e:
            notifyLog('Script error, Timer couldn\'t set', xbmc.LOGERROR)

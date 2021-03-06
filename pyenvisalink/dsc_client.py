import logging
import json
import re
import asyncio
from pyenvisalink import EnvisalinkClient
from pyenvisalink.dsc_envisalinkdefs import *

_LOGGER = logging.getLogger(__name__)

class DSCClient(EnvisalinkClient):
    """Represents a dsc alarm client."""

    def to_chars(self, string):
        chars = []
        for char in string:
            chars.append(ord(char))
        return chars

    def get_checksum(self, code, data):
        """part of each command includes a checksum.  Calculate."""
        return ("%02X" % sum(self.to_chars(code)+self.to_chars(data)))[-2:]

    def send_command(self, code, data):
        """Send a command in the proper honeywell format."""
        to_send = code + data + self.get_checksum(code, data)
        self.send_data(to_send)

    def dump_zone_timers(self):
        """Send a command to dump out the zone timers."""
        self.send_command(evl_Commands['DumpZoneTimers'], '')

    def keypresses_to_partition(self, partitionNumber, keypresses):
        """Send keypresses (max of 6) to a particular partition."""
        self.send_command(evl_Commands['PartitionKeypress'], str.format("{0}{1}", partitionNumber, keypresses[:6]))

    @asyncio.coroutine        
    def keep_alive(self):
        """Send a keepalive command to reset it's watchdog timer."""
        while not self._shutdown:
            if self._loggedin:
                self.send_command(evl_Commands['KeepAlive'], '')
            yield from asyncio.sleep(self._alarmPanel.keepalive_interval, loop=self._eventLoop)

    @asyncio.coroutine
    def periodic_zone_timer_dump(self):
        """Used to periodically get the zone timers to make sure our zones are updated."""
        while not self._shutdown:
            if self._loggedin:
                self.dump_zone_timers()
            yield from asyncio.sleep(self._alarmPanel.zone_timer_interval, loop=self._eventLoop)

    def arm_stay_partition(self, code, partitionNumber):
        """Public method to arm/stay a partition."""
        self._cachedCode = code
        self.send_command(evl_Commands['ArmStay'], str(partitionNumber))

    def arm_away_partition(self, code, partitionNumber):
        """Public method to arm/away a partition."""
        self._cachedCode = code
        self.send_command(evl_Commands['ArmAway'], str(partitionNumber))

    def arm_max_partition(self, code, partitionNumber):
        """Public method to arm/max a partition."""
        self._cachedCode = code
        self.send_command(evl_Commands['ArmMax'], str(partitionNumber))

    def disarm_partition(self, code, partitionNumber):
        """Public method to disarm a partition."""
        self._cachedCode = code
        self.send_command(evl_Commands['Disarm'], str(partitionNumber) + str(code))

    def panic_alarm(self, panicType):
        """Public method to raise a panic alarm."""
        self.send_command(evl_Commands['Panic'], evl_PanicTypes[panicType])

    def command_output(self, partitionNumber, outputNumber):
        """Used to activate the selected command output"""
        self.send_command(evl_Commands['CommandOutput'], str.format("{0}{1}", partitionNumber, outputNumber))	

    def parseHandler(self, rawInput):
        """When the envisalink contacts us- parse out which command and data."""
        cmd = {}
        dataoffset = 0
        if rawInput != '':
            if re.match('\d\d:\d\d:\d\d\s', rawInput):
                dataoffset = dataoffset + 9
            code = rawInput[dataoffset:dataoffset+3]
            cmd['code'] = code
            cmd['data'] = rawInput[dataoffset+3:][:-2]
            
            try:
                #Interpret the login command further to see what our handler is.
                if evl_ResponseTypes[code]['handler'] == 'login':
                    if cmd['data'] == '3':
                      handler = 'login'
                    elif cmd['data'] == '2':
                      handler = 'login_timeout'
                    elif cmd['data'] == '1':
                      handler = 'login_success'
                    elif cmd['data'] == '0':
                      handler = 'login_failure'

                    cmd['handler'] = "handle_%s" % handler
                    cmd['callback'] = "callback_%s" % handler

                else:
                    cmd['handler'] = "handle_%s" % evl_ResponseTypes[code]['handler']
                    cmd['callback'] = "callback_%s" % evl_ResponseTypes[code]['handler']
            except KeyError:
                _LOGGER.debug(str.format('No handler defined in config for {0}, skipping...', code))
                
        return cmd

    def handle_login(self, code, data):
        """When the envisalink asks us for our password- send it."""
        self.send_command(evl_Commands['Login'], self._alarmPanel.password) 

    def handle_login_success(self, code, data):
        """Handler for when the envisalink accepts our credentials."""
        super().handle_login_success(code, data)
        self.send_command(evl_Commands['StatusReport'], '')
        
    def handle_command_response(self, code, data):
        """Handle the envisalink's initial response to our commands."""
        _LOGGER.debug("DSC ack recieved.")

    def handle_command_response_error(self, code, data):
        """Handle the case where the DSC passes back a checksum failure."""
        _LOGGER.error("The previous command resulted in a checksum failure.")

    def handle_poll_response(self, code, data):
        """Handle the response to our keepalive messages."""
        self.handle_command_response(code, data)

    def handle_zone_state_change(self, code, data):
        """Handle when the envisalink sends us a zone change."""
        """Event 601-610."""
        parse = re.match('^[0-9]{3,4}$', data)
        if parse:
            zoneNumber = int(data[-3:])
            self._alarmPanel.alarm_state['zone'][zoneNumber]['status'].update(evl_ResponseTypes[code]['status'])
            _LOGGER.debug(str.format("(zone {0}) state has updated: {1}", zoneNumber, json.dumps(evl_ResponseTypes[code]['status'])))
            return zoneNumber
        else:
            _LOGGER.error("Invalid data has been passed in the zone update.")

    def handle_partition_state_change(self, code, data):
        """Handle when the envisalink sends us a partition change."""
        """Event 650-674, 652 is an exception, because 2 bytes are passed for partition and zone type."""
        if code == '652':
            parse = re.match('^[0-9]{2}$', data)
            if parse:
                partitionNumber = int(data[0])
                self._alarmPanel.alarm_state['partition'][partitionNumber]['status'].update(evl_ArmModes[data[1]]['status'])
                _LOGGER.debug(str.format("(partition {0}) state has updated: {1}", partitionNumber, json.dumps(evl_ArmModes[data[1]]['status'])))
                return partitionNumber
            else:
                _LOGGER.error("Invalid data has been passed when arming the alarm.") 
        else:
            parse = re.match('^[0-9]+$', data)
            if parse:
                partitionNumber = int(data[0])
                self._alarmPanel.alarm_state['partition'][partitionNumber]['status'].update(evl_ResponseTypes[code]['status'])
                _LOGGER.debug(str.format("(partition {0}) state has updated: {1}", partitionNumber, json.dumps(evl_ResponseTypes[code]['status'])))
                
                '''Log the user who last armed or disarmed the alarm'''
                if code == '700':
                    lastArmedBy = {'last_armed_by_user': int(data[1:5])}
                    self._alarmPanel.alarm_state['partition'][partitionNumber]['status'].update(lastArmedBy)
                elif code == '750':
                    lastDisarmedBy = {'last_disarmed_by_user': int(data[1:5])}
                    self._alarmPanel.alarm_state['partition'][partitionNumber]['status'].update(lastDisarmedBy)

                return partitionNumber
            else:
                _LOGGER.error("Invalid data has been passed in the parition update.")

    def handle_send_code(self, code, data):
        """The DSC will, depending upon settings, challenge us with the code.  If the user passed it in, we'll send it."""
        if self._cachedCode is None:
            _LOGGER.error("The envisalink asked for a code, but we have no code in our cache.")
        else:
            self.send_command(evl_Commands['SendCode'], self._cachedCode)
            self._cachedCode = None

    def handle_keypad_update(self, code, data):
        """Handle general- non partition based info"""
        for part in self._alarmPanel.alarm_state['partition']:
            self._alarmPanel.alarm_state['partition'][part]['status'].update(evl_ResponseTypes[code]['status'])
        _LOGGER.debug(str.format("(All partitions) state has updated: {0}", json.dumps(evl_ResponseTypes[code]['status'])))

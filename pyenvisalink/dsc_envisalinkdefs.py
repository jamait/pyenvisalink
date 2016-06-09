## Alarm Server
## Supporting Envisalink 2DS/3
##
## This code is under the terms of the GPL v3 license.

evl_Commands = {
    'KeepAlive' : '000',
    'DumpZoneTimers' : '008',
    'PartitionKeypress' : '071',
    'Disarm' : '040',
    'ArmStay' : '031',
    'ArmAway' : '030',
    'ArmMax' : '032',
    'Login' : '005'
}

evl_ArmModes = {
        '0' : {'name' : 'Arm Away'},
        '1' : {'name' : 'Arm Stay'},
        '2' : {'name' : 'Arm Zero Entry Away'},
        '3' : {'name' : 'Arm Zero Entry Stay'}
    }

evl_ResponseTypes = {
    '505' : {'name':'Login Prompt', 'handler':'login'},
    '615' : {'name':'Envisalink Zone Timer Dump', 'handler':'zone_timer_dump'},
    '500' : {'name':'Poll', 'handler':'poll_response'},
    '501' : {'name':'Checksum', 'handler':'command_response_error'},

#ZONE UPDATES

    '601' : {'name':'Zone Alarm', 'handler':'zone_state_change', 'status':{'alarm' : True}},
    '602' : {'name':'Zone Alarm Restore', 'handler':'zone_state_change', 'status':{'alarm' : False}},
    '603' : {'name':'Zone Tamper', 'handler':'zone_state_change', 'status':{'tamper' : True}},
    '604' : {'name':'Zone Tamper Restore', 'handler':'zone_state_change', 'status':{'tamper' : False}},
    '605' : {'name':'Zone Fault', 'handler':'zone_state_change', 'status':{'fault' : True}},
    '606' : {'name':'Zone Fault Restore', 'handler':'zone_state_change', 'status':{'fault' : False}},
    '609' : {'name':'Zone Open', 'handler':'zone_state_change', 'status':{'open' : True}},
    '610' : {'name':'Zone Restored', 'handler':'zone_state_change', 'status':{'open' : False}},

#PARTITION UPDATES
    '650' : {'name':'Ready', 'handler':'partition_state_change', 'status':{'ready' : True, 'alpha' : 'Ready'}},
    '651' : {'name':'Not Ready', 'handler':'partition_state_change', 'status':{'ready' : False, 'alpha' : 'Not Ready'}},
    '652' : {'name':'Armed', 'handler':'partition_state_change', 'status':{'armed' : True, 'exit_delay' : False, 'alpha' : 'Armed {0}'}},
    '653' : {'name':'Ready - Force Arming Enabled', 'handler':'partition_state_change', 'status':{'ready': True, 'alpha' : 'Ready - Force Arm'}},
    '654' : {'name':'Alarm', 'handler':'partition_state_change', 'status':{'alarm' : True, 'alpha' : 'Alarm'}},
    '655' : {'name':'Disarmed', 'handler':'partition_state_change', 'status' : {'alarm' : False, 'armed' : False, 'exit_delay' : False, 'entry_delay' : False, 'alpha' : 'Disarmed'}},
    '656' : {'name':'Exit Delay in Progress', 'handler':'partition_state_change', 'status':{'exit_delay' : True, 'alpha' : 'Exit Delay In Progress'}},
    '657' : {'name':'Entry Delay in Progress', 'handler':'partition_state_change', 'status':{'entry_delay' : True, 'alpha' : 'Entry Delay in Progress'}},
}
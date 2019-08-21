# -*- coding: utf-8 -*-
"""
Created on Thu Apr 25 16:39:39 2019

@author: sayala
"""

#import bifacial_radiance
#from   bifacial_radiance.config import *
#import os

# DATA_PATH = bifacial_radiance.main.DATA_PATH  # directory with module.json etc.

"""
# Check that torque tube dictionary parameters exist, and set defaults
def _checkTorqueTubeParams(d):
    diameter = 0
    tubetype = None
    material = None
    if d is not None:
        if 'diameter' in d:
            diameter = float(d['diameter'])
        if 'tubetype' in d:
            tubetype = d['tubetype']
        if 'torqueTubeMaterial' in d:
            material = d['torqueTubeMaterial']
    return diameter, tubetype, material
"""
def _append_dicts(x, y):
    """python2 compatible way to append 2 dictionaries
    """
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

# create start/end string and list for the 1-axis tracking hourly workflow
def _returnTimeVals(t, trackerdict=None):
    """
    input:  timeControlParamsDict,  trackerdict (optional)
    return startday (string), endday (string) in MM_DD format
    return timelist (list) in MM_DD_HH format only if trackerdict passed in
    """
    import datetime as dt
    start = dt.datetime(2000,t['MonthStart'],
                        t['DayStart'],t['HourStart'])
    end = dt.datetime(2000,t['MonthEnd'],
                        t['DayEnd'],t['HourEnd'])
    startday = start.strftime("%m_%d")
    endday = end.strftime("%m_%d")
    if trackerdict is None:
        timelist = []
    else:
        #dd = [(start + dt.timedelta(days=x/24)).strftime("%m_%d_%H") for x in range(((end-start).days + 1)*24)]
        dd = [(start + dt.timedelta(seconds=x*3600)).strftime("%m_%d_%H") for x in range(int((end-start).total_seconds()/3600) +1)]
        timelist = (set(dd) & set(trackerdict.keys()))
    return startday, endday, timelist


def runModelChain(simulationParamsDict, sceneParamsDict, timeControlParamsDict=None, moduleParamsDict=None, trackingParamsDict=None, torquetubeParamsDict=None, analysisParamsDict=None, cellLevelModuleParamsDict=None):
    '''

    This calls config.py values, which are arranged into dictionaries,
    and runs all the respective processes based on the varaibles in the config.py.

    Still under testing!
    
    to import the variables from a .ini file, use:
        (simulationParamsDict, sceneParamsDict, timeControlParamsDict, moduleParamsDict, 
         trackingParamsDict,torquetubeParamsDict,analysisParamsDict,cellLevelModuleParamsDict) = 
        bifacial_radiance.load.readconfigurationinputfile(inifile)
    '''
    import bifacial_radiance
    import os
    
    if 'testfolder' not in simulationParamsDict:
        simulationParamsDict['testfolder'] = bifacial_radiance.main._interactive_directory(
            title='Select or create an empty directory for the Radiance tree')

    testfolder = simulationParamsDict['testfolder']
    demo = bifacial_radiance.RadianceObj(
        simulationParamsDict['simulationname'], path=testfolder)  # Create a RadianceObj 'object'

    # Save INIFILE in folder
    inifilename = os.path.join(
        simulationParamsDict['testfolder'],  'simulation.ini')
    bifacial_radiance.load.savedictionariestoConfigurationIniFile(simulationParamsDict, sceneParamsDict, timeControlParamsDict,
                                                                  moduleParamsDict, trackingParamsDict, torquetubeParamsDict, analysisParamsDict, cellLevelModuleParamsDict, inifilename)

    # All options for loading data:
    if simulationParamsDict['weatherFile'][-3:] == 'epw':
        if simulationParamsDict['getEPW']:
            simulationParamsDict['weatherFile'] = demo.getEPW(
                simulationParamsDict['latitude'], simulationParamsDict['longitude'])  # pull TMY data for any global lat/lon
        # If file is none, select a EPW file using graphical picker
        metdata = demo.readEPW(simulationParamsDict['weatherFile'])
    else:
        # If file is none, select a TMY file using graphical picker
        metdata = demo.readTMY(simulationParamsDict['weatherFile'])

    # input albedo number or material name like 'concrete'.  To see options, run this without any input.
    demo.setGround(sceneParamsDict['albedo'])
    analysis = None  # initialize default analysis return value to none.

    A = demo.printModules()
    
    #cellLeveLParams are none by default.
    cellLevelModuleParams = None 
    try:
        if simulationParamsDict['cellLevelModule']:
            cellLevelModuleParams = cellLevelModuleParamsDict
    except: pass
    
    if torquetubeParamsDict:
        #kwargs = {**torquetubeParamsDict, **moduleParamsDict} #Py3 Only
        kwargs = _append_dicts(torquetubeParamsDict, moduleParamsDict)
    else:
        kwargs = moduleParamsDict
        
    if simulationParamsDict['moduletype'] in A:
        if simulationParamsDict['rewriteModule'] is True:
            moduleDict = demo.makeModule(name=simulationParamsDict['moduletype'],
                                         torquetube=simulationParamsDict['torqueTube'],
                                         axisofrotationTorqueTube=simulationParamsDict[
                                             'axisofrotationTorqueTube'],
                                         cellLevelModuleParams=cellLevelModuleParams,
                                         **kwargs)

        print("\nUsing Pre-determined Module Type: %s " %
              simulationParamsDict['moduletype'])
    else:
        moduleDict = demo.makeModule(name=simulationParamsDict['moduletype'],
                                     torquetube=simulationParamsDict['torqueTube'],
                                     axisofrotationTorqueTube=simulationParamsDict['axisofrotationTorqueTube'],
                                     cellLevelModuleParams=cellLevelModuleParams,
                                     **kwargs)

    # TODO:  Refactor as a state machine to run specific routines based on 
    #        input flags.  That might clean things up here a bit...
    
    
    if simulationParamsDict['tracking'] is False:  # Fixed Routine

        # makeScene creates a .rad file with 20 modules per row, 7 rows.
        scene = demo.makeScene(
            moduletype=simulationParamsDict['moduletype'], sceneDict=sceneParamsDict, hpc=simulationParamsDict['hpc'])

        if simulationParamsDict["cumulativeSky"]:
            if simulationParamsDict['daydateSimulation']: # was timestampRangeSimulation
                import datetime
                startdate = datetime.datetime(2001, timeControlParamsDict['MonthStart'],
                                              timeControlParamsDict['DayStart'],
                                              timeControlParamsDict['HourStart'])
                enddate = datetime.datetime(2001, timeControlParamsDict['MonthEnd'],
                                            timeControlParamsDict['DayEnd'],
                                            timeControlParamsDict['HourEnd'])
                # entire year.
                demo.genCumSky(demo.epwfile, startdate, enddate)
            else:
                demo.genCumSky(demo.epwfile)  # entire year.
            # makeOct combines all of the ground, sky and object files into a .oct file.
            octfile = demo.makeOct(demo.getfilelist())
            # return an analysis object including the scan dimensions for back irradiance
            analysis = bifacial_radiance.AnalysisObj(octfile, demo.name)
            frontscan, backscan = analysis.moduleAnalysis(scene, analysisParamsDict['modWanted'],
                                                          analysisParamsDict['rowWanted'],
                                                          analysisParamsDict['sensorsy'])
            analysis.analysis(octfile, demo.name, frontscan, backscan)
            print('Bifacial ratio yearly average:  %0.3f' %
                  (sum(analysis.Wm2Back) / sum(analysis.Wm2Front)))

        else:  # Hourly simulation fixed tilt.  Use new modified 1-axis tracking workflow 
            #    Largely copies the existing 1-axis workflow from below, but 
            #    forces trackerdict tilt and azimuth to be fixed.
            
            #
            print('\n***Starting Fixed-tilt hourly simulation ***\n')
          
            
            ##  All the rest here is copied from below...
            # Timestamp range selection 
            if simulationParamsDict['daydateSimulation']: # fixed tilt hourly day date
                # _returnTimeVals returns proper string formatted start and end days.
                startday, endday,_= _returnTimeVals(timeControlParamsDict)
                
                trackerdict = demo.set1axis(cumulativesky=False, 
                                        limit_angle=sceneParamsDict['tilt'],
                                        axis_azimuth=sceneParamsDict['azimuth'],
                                        angledelta=0) # angledelta=0 switches to constant fixed tilt mode.
                           
                # optional parameters 'startdate', 'enddate' inputs = string 'MM/DD' or 'MM_DD'
                trackerdict = demo.gendaylit1axis(startdate=startday, enddate=endday)
                _,_,timelist = _returnTimeVals(timeControlParamsDict, trackerdict)
                print("\n***Timerange from %s to %s. ***\n" % (sorted(timelist)[0], 
                                                    sorted(timelist)[-1]))

                def _addRadfile(trackerdict):
                    # need to add trackerdict[time]['radfile'] = radfile and 
                    # trackerdict[time]['scene'] = scene since we don't do makeScene1axis
                    for i in trackerdict:
                        trackerdict[i]['scene'] = scene
                        trackerdict[i]['radfile'] = scene.radfiles
                    return trackerdict
                
                trackerdict = _addRadfile(trackerdict)  # instead of makeScene1axis
                
                
                for time in sorted(timelist):  
                    trackerdict = demo.makeOct1axis(trackerdict, singleindex=time,
                                                    hpc=simulationParamsDict['hpc'])
                    trackerdict = demo.analysis1axis(trackerdict, singleindex=time,
                                                     modWanted=analysisParamsDict['modWanted'],
                                                     rowWanted=analysisParamsDict['rowWanted'],
                                                     sensorsy=analysisParamsDict['sensorsy'])
                    analysis = trackerdict[time]['AnalysisObj']  # save and return the last run

            
            elif simulationParamsDict["timestampRangeSimulation"]: # fixed tilt timestamp range
                for timeindex in range(timeControlParamsDict['timeindexstart'], timeControlParamsDict['timeindexend']):
                    demo.gendaylit(metdata, timeindex)  # Noon, June 17th
                    # makeOct combines all of the ground, sky and object files into a .oct file.
                    octfile = demo.makeOct(demo.getfilelist())
                    # return an analysis object including the scan dimensions for back irradiance
                    analysis = bifacial_radiance.AnalysisObj(
                        octfile, demo.name)
                    frontscan, backscan = analysis.moduleAnalysis(scene, analysisParamsDict['modWanted'],
                                                                  analysisParamsDict['rowWanted'],
                                                                  analysisParamsDict['sensorsy'])
                    analysis.analysis(octfile, demo.name, frontscan, backscan)
                    print('Bifacial ratio for %s average:  %0.3f' % (
                        metdata.datetime[timeindex], sum(analysis.Wm2Back) / sum(analysis.Wm2Front)))
            
            else:  
                print('\n***Full - year hourly simulation ***\n')
                # optional parameters 'startdate', 'enddate' inputs = string 'MM/DD' or 'MM_DD'
                
                trackerdict = demo.set1axis(cumulativesky=False, 
                                        limit_angle=sceneParamsDict['tilt'],
                                        axis_azimuth=sceneParamsDict['azimuth'],
                                        angledelta=0) # angledelta=0 switches to constant fixed tilt mode.
                trackerdict = demo.gendaylit1axis(metdata)          
                # Tracker dict should go here becuase sky routine reduces the size of trackerdict.
                trackerdict = demo.makeScene1axis(trackerdict=trackerdict,
                                              moduletype=simulationParamsDict['moduletype'],
                                              sceneDict=sceneParamsDict,
                                              cumulativesky=False,
                                              hpc=simulationParamsDict['hpc'])
                
                trackerdict = demo.makeOct1axis(
                    trackerdict, hpc=simulationParamsDict['hpc'])
                trackerdict = demo.analysis1axis(trackerdict, modWanted=analysisParamsDict['modWanted'],
                                                 rowWanted=analysisParamsDict['rowWanted'],
                                                 sensorsy=analysisParamsDict['sensorsy'])
                analysis = trackerdict[time]['AnalysisObj']  # save and return the last run??
            

    else:  # Tracking
        print('\n***Starting 1-axis tracking simulation***\n')
        if 'gcr' not in sceneParamsDict:  # didn't get gcr passed - need to calculate it
            sceneParamsDict['gcr'] = moduleDict['sceney'] / \
                sceneParamsDict['pitch']
        trackerdict = demo.set1axis(metdata, axis_azimuth=sceneParamsDict['axis_azimuth'],
                                    gcr=sceneParamsDict['gcr'],
                                    limit_angle=trackingParamsDict['limit_angle'],
                                    angledelta=trackingParamsDict['angle_delta'],
                                    backtrack=trackingParamsDict['backtrack'],
                                    cumulativesky=simulationParamsDict["cumulativeSky"])

        if simulationParamsDict["cumulativeSky"]:  # cumulative sky routine

            # This option doesn't work currently.!
            if simulationParamsDict['timestampRangeSimulation']:
                import datetime
                startdate = datetime.datetime(2001, timeControlParamsDict['MonthStart'],
                                              timeControlParamsDict['DayStart'],
                                              timeControlParamsDict['HourStart'])
                enddate = datetime.datetime(2001, timeControlParamsDict['MonthEnd'],
                                            timeControlParamsDict['DayEnd'],
                                            timeControlParamsDict['HourEnd'])
                trackerdict = demo.genCumSky1axis(
                    trackerdict, startdt=startdate, enddt=enddate)
            else:
                trackerdict = demo.genCumSky1axis(trackerdict)

            trackerdict = demo.makeScene1axis(trackerdict=trackerdict,
                                              moduletype=simulationParamsDict['moduletype'],
                                              sceneDict=sceneParamsDict,
                                              cumulativesky=simulationParamsDict['cumulativeSky'],
                                              hpc=simulationParamsDict['hpc'])

            trackerdict = demo.makeOct1axis(
                trackerdict, hpc=simulationParamsDict['hpc'])

            trackerdict = demo.analysis1axis(trackerdict, modWanted=analysisParamsDict['modWanted'],
                                             rowWanted=analysisParamsDict['rowWanted'],
                                             sensorsy=analysisParamsDict['sensorsy'])
            print('Annual RADIANCE bifacial ratio for 1-axis tracking: %0.3f' %
                  (sum(demo.Wm2Back)/sum(demo.Wm2Front)))

        else: # Hourly tracking

            # Timestamp range selection
            #workflow currently identical for timestampRangeSimulation and daydateSimulation

            startday, endday,_= _returnTimeVals(timeControlParamsDict)
            trackerdict = demo.gendaylit1axis(startdate=startday, enddate=endday)                
            # reduce trackerdict to only hours in timeControlParamsDict
            _,_,timelist = _returnTimeVals(timeControlParamsDict, trackerdict)
            trackerdict  = {t: trackerdict[t] for t in timelist} 

            # Tracker dict should go here becuase sky routine reduces the size of trackerdict.
            trackerdict = demo.makeScene1axis(trackerdict=trackerdict,
                                              moduletype=simulationParamsDict['moduletype'],
                                              sceneDict=sceneParamsDict,
                                              cumulativesky=simulationParamsDict['cumulativeSky'],
                                              hpc=simulationParamsDict['hpc'])
            if simulationParamsDict['timestampRangeSimulation']:

                for time in timelist:  
                    trackerdict = demo.makeOct1axis(trackerdict, singleindex=time,
                                                    hpc=simulationParamsDict['hpc'])
                    trackerdict = demo.analysis1axis(trackerdict, singleindex=time,
                                                     modWanted=analysisParamsDict['modWanted'],
                                                     rowWanted=analysisParamsDict['rowWanted'],
                                                     sensorsy=analysisParamsDict['sensorsy'])

            else: #daydateSimulation.  Not sure this is much different from the above...
                trackerdict = demo.makeOct1axis(
                    trackerdict, hpc=simulationParamsDict['hpc'])
                trackerdict = demo.analysis1axis(trackerdict, modWanted=analysisParamsDict['modWanted'],
                                                 rowWanted=analysisParamsDict['rowWanted'],
                                                 sensorsy=analysisParamsDict['sensorsy'])
    return demo, analysis

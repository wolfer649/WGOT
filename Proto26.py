#!/usr/bin/python
# Copyright (c) 2014 Adafruit Industries, 2019 R.S. Fowler
# Author: Tony DiCola - for content from simpletest.py
# Author: R.S. Fowler for WG Oven Thermometer project
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Can enable debug output by uncommenting:
#import logging
#logging.basicConfig(level=logging.DEBUG)
# ---- End of Adafruit disclaimer - RSF too

# -----Define testing variables - up front for ease of access.
Forcetft = True # if False, SDL will try X11 first. If True, the PiTFT will be forced.
Debugprt = False # if True, some debug printing will be enabled
Tempadj = -3.2 # Fixed temperature adjustment in C - from calibration testing
Glitchless = False # Cheat - if True, one time temp differences will be removed
# The following should really be made arguments for the command line
Csvfilename = '/home/pi/WGOTdata.csv'
Graphfile = '/home/pi/WGOTgraph.png'
# -----End testing variables

# -----Define some colour tuple names for shorthand use
BLACK = (0,0,0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

########################################
# ----- Menu/Screen Definitions
########################################

# Each dictionary describes a screen format
# Each dictionary key is a relative line value - they could be on the same physical line
# Each dictionary value item is a list for that line
# {line_value: [line_position, textsize, indent, font, text]}
# where:
# - line_value is a unique line number
# - line_position is the position of the line from the top of the screen in pixels*textsize
# - textsize is the text height in pixels
# - indent is the left indentation in pixels
# - font is an available Sysfont name in quotes or None
# - Text is the text to be shown, in quotes
# Values can be updated from code before showing the screen

# Define a basic Splash screen
splash_screen = {
    0:[3, 30, 120, None, 'Starting ...']}

# Define the Temperature(s) screen for normal mode
temp_screen = {
    0: [0, 28, 0, None, 'Current Temperature'],
    1: [1, 28, 0, None, '60.9 C'],
    2: [2, 28, 0, None, '69.5 F'],
    3: [3, 28, 0, None, 'Time (min:sec) = mm.ss'],
    4: [4.6, 28, 0, None, 'Save/Hold Temperature'],
    5: [5.6 ,28, 0, None, '20.1 C'],
    6: [6.6, 28, 0, None, '10.7 F'],
    7: [7.6, 28, 0, None, 'Time (min:sec) = mmm.ss']}

# Define the main menu for menu mode
main_menu = {
    0: [0, 28, 110, None, 'Menu'],
    1: [2, 28, 0, None, 'Adjust Temperature'],
    2: [3, 28, 0, None, 'Adjust Time Interval'],    
    3: [4, 28, 0, None, 'Return'],
    4: [5, 28, 0, None, 'Exit']}
Mmenumax = 4 # maximum number of selectable lines on main menu (1 thru 4)

# Define the Temperature Adjustment menu for menu mode
tempadj_menu = {
    0: [0, 28, 40, None, 'Temperature Adjustment*'],
    1: [2, 28, 0, None, 'Adjustment Value (C)'],
    2: [4, 28, 0, None, '0.0'], # a dummy placeholder
    3: [14, 16, 0, None, '* Only Affects Ongoing Readings']}

# Define Time Interval Selection menu for menu mode
timeadj_menu = {
    0: [0, 28, 40, None, 'Time Interval Selection*'],
    1: [2, 28, 0, None, 'Time Interval (sec)'],
    2: [4, 28, 0, None, '6'], # a dummy placeholder
    3: [14, 16, 0, None, '* Only Affects Ongoing Readings']}
# Matching time adjust values for the above menu, in seconds
Timevals = [6, 30, 60, 120, 600, 1800, 3600]

# Define button labels dictionary to go with the tempatures screen
# (right alignment is hard, hence the leading blanks and mono-spaced font)
button_menu1 = {
    0: [3, 12, 240, 'DejavuSansMono', ' Shutdown->'],
    1: [8, 12, 240, 'DejavuSansMono', 'Save/Hold->'],
    2: [13, 12, 240, 'DejavuSansMono', '  Restart->'],
    3: [18, 12, 240, 'DejavuSansMono', '     Menu->']}

# Define button labels dictionary for menu mode
button_menu2 = {
    0: [3, 12, 245, 'DejavuSansMono', 'Shutdown->'],
    1: [8, 12, 245, 'DejavuSansMono', '      Up->'],
    2: [13, 12, 245, 'DejavuSansMono', '    Down->'],
    3: [18, 12, 245, 'DejavuSansMono', '  Select->']}


########################################
# ----- Import all required packages
########################################
# Note: all packages except MAX31855 and Matplotlib are part of Raspian Stretch

import time
import os # used to update environment variables
import sys # used to exit and to get command line arguments
import getopt # used to parse command line arguments
import pygame # used to manage the display contents and timers
from pygame.locals import *
from pygame import event, fastevent # fastevent is for multithreaded posts
import RPi.GPIO as GPIO # GPIO is a shorthand name
# The following require prior s/w installations.
# Follow the directions on the back of the box for details.
import Adafruit_GPIO.SPI as SPI # From Adafruit MAX31855 package
import Adafruit_MAX31855.MAX31855 as MAX31855 # to talk to the MAX31855 board
import matplotlib # used to make graphs
# the following line allows this program to start from rc.local to avoid errors
matplotlib.use('Agg') # Needed to run screenless matplotlib - BEFORE importing pyplot
import matplotlib.pyplot as plt # plt is a shorthand name for Python Matplotlib
import numpy as np # np is a shorthand name

########################################
#----- Function Definitions
########################################

# --Define a function to turn GPIO PiTFT button events into Pygame events using fastevent
# Note: This function runs in a separate thread from the main programme.
# Note: using pygame.event.post causes "video system not initialized" error
#  so we use fastevent.post, based on (very terse) pygame doc.
def gpiobut(channel): # 'channel' is PiTFT button's BCM GPIO value for GPIO event
# post pygame event based on PiTFT button pushed
    if channel == 22: # using literals for clarity. e.g. GPIO 22 is button 2
        fastevent.post(pygame.event.Event(pygame.USEREVENT+3, button=2)) # use fastevent for separate thread pygame post
    elif channel == 23: # check for button 3
        fastevent.post(pygame.event.Event(pygame.USEREVENT+3, button=3))
    elif channel == 27: # check for button 4
        fastevent.post(pygame.event.Event(pygame.USEREVENT+3, button=4))
# ignore anything else
#--End gpiobut callback function

# --Define a function to convert Celsius to Fahrenheit.
def c_to_f(c):
    return c * 9.0 / 5.0 + 32.0
# -- End c_to_f function
    
# --Define a function to get the temperature from the MAX31855 board
def get_temp():
# Get the external probe and internal chip temperatures in Celsius
    tempc = sensor.readTempC() + Tempadj # get the termperature and adjust for calibration
    itempc = sensor.readInternalC() # Debug
#    if Debugprt == True:
#        print ('Ctemp=',tempc, 'Itemp=',itempc) # track results against observed
    return tempc; # Return the temperature in Celsius only, for now
# --End get_temp function
    
# --Define  a function to plot a graph to a file
def make_graph(): 
#    if Debugprt == True: # print the timing in debug mode        
#        print (pygame.time.get_ticks()/1000,Timex, 'make_graph start') #debug
    fig, ax = plt.subplots() # define the
    fig.subplots_adjust(left=0.11, right=0.97, top=0.94, bottom=0.11) # reduce margin size
    if Curtemp > 0: # check if current temperature is above freezing
        ax.plot(Timelist, Templist, 'red') # if so, plot the graph in red
    else: # for temperatures at or below freezing
        ax.plot(Timelist, Templist, 'blue') # if so, plot the graph in blue        
    ax.set(xlabel='Time (min)', ylabel='Temp (F)',title='Temperature') # add axis labels
    ax.grid() #show with default grid for major axes
# The following creates a 320 x 240 pixel (for now) graph imsge file
#   after experimenting with 'dpi' values.
    fig.savefig(Graphfile, bbox="tight", dpi=50.1) # save graph
    plt.close('all') # free up memory from graph creation
#    if Debugprt == True: # print the timing in debug mode        
#        print (pygame.time.get_ticks()/1000,Timex, 'make_graph end') #debug
# --End make_graph function

# --Define a function to show a graph from a file onto the screen
def show_graph():
# Will show the graph on the PiTFT (or X11) with PyGame
# Show an image (320x240) - created previously by matplotlib
    Lcd.fill (BLACK) # Blank the display  
    graph = pygame.image.load(Graphfile)
    Lcd.blit(graph, (0,0)) # place in upper left corner
    pygame.display.update() # Show it
# --End show graph function

# --Define a function to show a screen of text with button labels
# Note: text items in the screen dictionary can be changed before displaying
def show_text_menu(menuname, highlite, buttons): # buttons can be None
    Lcd.fill(BLACK) # blank the display
# Build button labels first, so menu can overlap on leading blanks
    if buttons != None: # see if there are buttons to show
        line = 0 # reset our line count for the labels
        for line in buttons: # go through the  button line vslues
            linedata = buttons[line]
            myfont = pygame.font.SysFont(linedata[3], linedata[1]) # use the font selected        
            textsurface = myfont.render(linedata[4], False,WHITE,BLACK) # write the text
            Lcd.blit(textsurface,(linedata[2],linedata[1]*linedata[0])) # show the text
            line = line + 1 # go to the next line    
# Build the rest of the menu
    line = 0 # start showing at line zero
    for line in menuname: # go through the line values
        linedata = menuname[line] # get the value list from the menu dictionary
        myfont = pygame.font.SysFont(linedata[3], linedata[1]) # use the font selected
# Build text and position & highlighting a line, if within range
        if line == highlite: # check if we should highlight this line
            textsurface = myfont.render(linedata[4], False, BLACK,WHITE) # highlight it
        else:
            textsurface = myfont.render(linedata[4], False, WHITE,BLACK)  # no highlight           
        Lcd.blit(textsurface,(linedata[2],linedata[1]*linedata[0])) # add the line to the screen        
        line=line+1
# Show the new screen
    pygame.display.update() # show it all
# --End show_text_menu function

# --Define a function to show the temperatures/times in text
def show_temp(): # shows hold temperatures too
#    if Debugprt == True: # print the event in debug mode
#        print ('show_temp', Updtimex, Updinterval, Minx, Secx) #debug 
    Lcd.fill (BLACK) # blank the display
    curtemp = get_temp() # get the current temperature in a local variable
    tempf = c_to_f(curtemp) #calulate temperature in F
# Update the dictionary for this screen with new temperature/time values
# Each line updates the text element[4] in the associated dictionary line's value list
    temp_screen[1][4] = str.format("%.1f" % curtemp +" C") # change the text, 4 in the list
    temp_screen[2][4] = str.format("%.1f" % tempf +" F") # update menu text in dictionary
    temp_screen[3][4] = str.format("Time (min:sec) = "+str(Minx)+":"+str(Secx).zfill(2)) # change the text content
# Update Hold values too
    temp_screen[5][4] = str.format("%.1f" % Htemp +" C") # change the text content
    temp_screen[6][4] = str.format("%.1f" % Htempf +" F") # change the text content
    temp_screen[7][4] = str.format("Time (min:sec) = "+str(Hminx)+":"+str(Hsecx).zfill(2)) # change the text content
    show_text_menu(temp_screen, None, button_menu1) # Put it on the screen
# --End show_temp function

# --Define a function to flip between temperature and graph displays
def show_flip():       
    global Displayshow # make this global
    if Displayshow == Displaytemp: # if showing the temps, 
        Displayshow = Displaygraph # switch to showing a graph
        make_graph() # get a current graph right now
        show_graph() # put it on the screen
    else: # otherwise,
        Displayshow = Displaytemp # switch to showing temps
        show_temp() # show the temps right now
# ---- End show_flip function

# --Define a function to do time/temp display updates on a timer 2 pop
# Note: this only affects the temperature/time display and activity LED
def Do_ttimer_updates(): # 
    global Led, Updtimex, Minx, Secx # declare globals as needed
# Perform common timer 1 pop updates
    Updtimex=Updtimex + Updinterval # update increment to seconds
    Minx = Updtimex // 60 # get elapsed time in minutes
    Secx = Updtimex % 60 # get remainder secs elapsed
# Toggle a basic LED activity indicator, since this timer never changes
    if Led == True: # check if the LED is on
        GPIO.output(Ledgpio, GPIO.LOW) # if so, then turn it off
        Led = False # record that it is off
    else:
        GPIO.output(Ledgpio,GPIO.HIGH) # otherwise, turn on the LED
        Led = True # record that it is on           
# --End of ttimer_updates updates function for timer 2
    
# --Define a function to perform common timer 1 pop updates for all modes
# Note: this affects data saving/recording and graphs
def Do_rectimer_updates():
    global Timex, Minx, Secx, Curtemp # declare global variables required    
# Perform common timer 1 pop updates
    Timex = Timex + Tinterval # update increment in seconds
    Curtemp=get_temp() # get current temp
    Templist.append(c_to_f(Curtemp)) # add to list
    Timelist.append(Timex/60.0) # add the new value, but in mintes
# Filter out one-time temperature glitches - works only in steady state for now.
# This is a cheat for cosmetic purpose for now. Still get bumpy graphs.
    if Glitchless == True and len(Templist) >2: # see if we want to reduce temp glitches
        if Templist[-3] == Templist[-1] and Templist[-2] != Templist[-1]: # chk glitch
            Templist[-2]=Templist[-1] # smooth over the glitch
# Write data to log
    Csvlog.write("{0},{1},{2}\n".format(str(int(Timex)),str(Curtemp),str(c_to_f(Curtemp)))) # write time (sec) and temp (F)
    Csvlog.flush() # make sure the file is updated immediately     
# --End of Do_rectimer_updates function    

#---------------End Function Definitions-----------
########################################
#----- Begin Main Programme
########################################
#---------------Initialization---------------------

# --Initialize the PiTFT LCD and touchscreen

LCD_WIDTH = 320 # the width of the PiTFT in pixels
LCD_HEIGHT = 240 # the height of the PiTFT in pixels
LCD_SIZE = (LCD_WIDTH, LCD_HEIGHT) # make it into a tuple for later
# Setup SDL system variables to use the PiTFT
os.putenv('SDL_FBDEV', '/dev/fb1') # specify device as frame buffer1
os.putenv('SDL_MOUSEDRV', 'TSLIB') # TSLIB doesn't work too well with Stretch
os.putenv('SDL_MOUSEDEV', '/dev/input/touchscreen') # Mouse is PiTFT touchscreen
# The following checks whether to take the SDL default screen (usually X11) or not
# Note: HDMI (X11) display will blank during this test on an actual PiTFT
if Forcetft == True: # See if we want to force using the PiTFT
    os.putenv('SDL_VIDEODRIVER','fbcon') # force PyGame display to the PiTFT
# --End PiTFT Initialization

# --Intialize MAX31855 configuration - from Adafruit sample code
# Must run as Root (sudo) for this to work
# Raspberry Pi software SPI configuration
CLK = 5 # RSF - was 25 - avoid piTFT conflict
CS  = 6 # RSF - was 24 - avoid piTFT conflict
DO  = 16 # RSF - was 18 - avoid potential piTFT or PWM conflict
sensor = MAX31855.MAX31855(CLK, CS, DO)
# --End MAX31855 initialization

# --Initialize Pygame
pygame.init() #Initialize Pygame
pygame.mouse.set_visible(False) # Hide the useless mouse pointer   
Lcd = pygame.display.set_mode(LCD_SIZE) # Create a pyame 'display surface' all we'll need
fastevent.init() # Initialize fastevents for multithreaded GPIO detect
pygame.event.set_blocked(pygame.MOUSEMOTION) # Block these from filling the event queue
pygame.event.set_blocked(pygame.MOUSEBUTTONUP) # Block these from filling the event queue too
pygame.font.init() # Required to use fonts

# -Initialize pygame timer events
# Initialize the pygame time event and variables for recording purposes
Timeval = 0 # start sample rate at first entry in list
Tinterval = Timevals[Timeval] # set the timer interval in msec
# Define  a pygame user event for the recording timer
pygame.time.set_timer(USEREVENT+1, Tinterval*1000) # create a timer event 1

# -Initialize a pygame timer event to update the time/temperature display
Updinterval = 1 # Update interval in sec (may be longer for easier save/hold)
Updtimex = 0 # Initialize update timer value since start
pygame.time.set_timer(USEREVENT+2, Updinterval*1000) # create timer event #2
# --End Pygame initialization

# --Show a splash screen during initialization, in case it takes some time to start
show_text_menu(splash_screen,None,None) # Show the splash screen - no buttons
# --End show splash screen

# --Initialize GPIO for PiTFT 2.8" touchscreen P/N 2423 buttons and activity LED
# Note: PiTFT buttons connect GPIO port to ground, hence pull them up when open
GPIO.setmode(GPIO.BCM) # use BCM chip's numbering scheme vs. pin numbers
# Note: Button 17 (top right) is assumed reserved for OS shutdown here
#  by configuring it in /boot/config.txt with dtoverlay=gpio-shutdown,gpio_pin=17
# Wiring it directly to GPIO 3 also makes it an OS revive button
GPIO.setup(22, GPIO.IN, pull_up_down=GPIO.PUD_UP) #PiTFT button 2
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP) #PiTFT button 3
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP) #PiTFT button 4
Ledgpio = 21 # pick a free GPIO for the activity LED, handy location on PiHat too
GPIO.setup(Ledgpio, GPIO.OUT) # Define a pin for simple LED activity indicator
GPIO.output(Ledgpio, GPIO.HIGH) # turn on the LED to show we're running
Led = True # record the state of the LED
# Define GPIO button event handlers for the PiTFT 2423
GPIO.add_event_detect(22, GPIO.FALLING, callback=gpiobut, bouncetime=300)
GPIO.add_event_detect(23, GPIO.FALLING, callback=gpiobut, bouncetime=300)
GPIO.add_event_detect(27, GPIO.FALLING, callback=gpiobut, bouncetime=300)
# --End GPIO Initialization

# --Initialize main variables
Timex=0 # total time since execution started in seconds
Minx=0 # total time since execution started in minutes
Secx=0 # leftover seconds for Minx:Secx display
Ttempadj = Tempadj # Set temporary timer interval to the same, for Time Adj menu
Curtemp=get_temp() # get current temperature to start
Timelist=[Timex/60.0] # dummy list for make_graph
Templist=[c_to_f(Curtemp)] # dummy list for make_graph
Displaytemp=1 # value if we're showing temperature
Displaygraph=2 # value if we're showing a graph
Displayshow=Displaytemp # default to show temperature initially
Htemp = Curtemp # Initialize Hold data as well
Htempf = c_to_f(Curtemp)
Htimex = 0 # init hold time
Hminx = 0 # init hold time min
Hsecx = 0 # init hold time sec
Mousetimer = pygame.time.get_ticks()/1000 # init timer (sec) for mouse/touch debounce
Mousewait = 2 # choose 2 sec between MOUSEDOWN events for touch debounce
Menumode = False # Start without a menu
Mmenuline = 1 # start with line 1 on main menu
# --End main variables initialization

# --Intitialize a csv-format log file and save two previous ones
# - Try to save some csv file to avoid data loss over reboot/restarts
try: # only if it exists, remove the oldest save file
    os.remove(Csvfilename+'save2') # remove oldest (save2) file first
except: # if it's not there, we don't care
    pass
try: # only if it exists, rename the old save file to oldest
    os.rename(Csvfilename+'save1',Csvfilename+'save2') # rename save1 to save2
except: # if it's not there, we don't care
    pass
try: # only if it exists rename the last  csv log file to save1
    os.rename(Csvfilename,Csvfilename+'save1') # rename the last to save1
except: # if it's not there, we don't care
    pass
# - Open the new file, regardless of what happened just above   
Csvlog = open(Csvfilename,"w") # open the csv log file fresh, for writing
Csvlog.write("{0},{1},{2}\n".format(str(int(Timex)),str(Curtemp),str(c_to_f(Curtemp)))) # write time (sec) and temp (F)
Csvlog.flush() # make sure the file is updated immediately 
# --End csv log file initialization

#------------End Initialization----------------

################################################
# ----- Main code event loops - there are two:
# ------  One for non-menu mode and one for menu mode
################################################
while True: # loop forever, waiting for events in any mode

########################################
# ----- Handle events in non-menu mode
########################################
    while Menumode == False: # loops waiting for events in 'normal' mode
        event = pygame.fastevent.wait() # wait for an event object to check
#        if Debugprt == True: # print the event in debug mode
#            print (pygame.time.get_ticks()/1000,Timex, event, "normal mode") # annoying debug

# --Handle Quit if window is closed  - in X11 display mode only
        if event.type == QUIT: # only works in an X11 window
            Csvlog.close() # close the csv log file
            pygame.display.quit() # clean up
            GPIO.output(Ledgpio, GPIO.LOW) # turn off the LED
            sys.exit() # exit this programme
# -- End of Quit event handler            

# --Handle the recording timer pop 1 event           
        elif event.type == pygame.USEREVENT+1: # using literal here for timer pop 1
            Do_rectimer_updates() # update variables and log
# Show graph, if that's the mode we're in           
            if Displayshow == Displaygraph: # show a graph, if required
                 make_graph() # build the graph
                 show_graph() # show the graph
# -- End of timer pop 1 event handling

# --Handle the time/temp/LED display update for timer pop event 2         
        elif event.type == pygame.USEREVENT+2: # using literal here for timer pop 2
            Do_ttimer_updates() # Update the time/temp display values
            if Displayshow == Displaytemp: # if we're supposed to be showing the temp
                show_temp() # Show the new time/temp screen
# -- End of timer pop 2 event handling                

            
# --Handle a PiTFT button is press - driven by the gpiobut GPIO callback function thread
        elif event.type == USEREVENT+3: # check for a PiTFT button press, literal value
            if Debugprt == True:
                print ("button =", event.button) # debug
########################################
# ----- Non-Menu Mode Button  button event tests
########################################                
# --Check for button 2 - Capture Hold data
            if event.button==2: # button 2 = GPIO 22
                if Debugprt == True:
                    print ("Button 2 captures a Hold event")                
# Capture Hold data            
                Htimex = Updtimex # Capture the time in seconds
                Hminx = Minx # capture minutes ...
                Hsecx = Secx # and in seconds too
                Htemp = Curtemp # Capture the current temp in Celsius
                Htempf = c_to_f(Htemp) # Capture the temp in Farenheit
# Update the display immediately, to show we've got it
                if Displayshow == Displaytemp: # Update the display, if showing temps
                    show_temp() # show the temperatures again
# --End of Button 2 - Hold handling                   

# --Check for button 3 - Restart data capture      
            elif event.button==3: # restart/reset data capture
                if Debugprt == True:
                    print ("Button 3 resets the time, temperature and graph")
# Initialize variables all over again and show temperatures to start
                Timex=0 # total time since execution started in seconds
                Minx=0 # total time since execution started in minutes
                Secx=0 # leftover seconds for Minx:Secx display
                Updtimex = 0 # Total time since execution started, for temp display
                Curtemp=get_temp() # get new current temperature
                Timelist=[Timex/60.0] # dummy list for make_graph
                Templist=[c_to_f(Curtemp)] # dummy list for make_graph
                Displayshow=Displaytemp # default to show temperature again
                Htemp = Curtemp # restart hold data too
                Htempf = c_to_f(Curtemp) # get this in Farenheit
                Htimex = 0 # init hold time
                Hminx = 0 # init hold time min
                Hsecx = 0 # init hold time sec
                Csvlog.write("00,00,00\n") # write zeros line to record a restart
                Csvlog.write("{0},{1},{2}\n".format(str(int(Timex)),str(Curtemp),str(c_to_f(Curtemp)))) # write time (sec) and temp (F)
                Csvlog.flush() # make sure the file is updated immediately 
                show_temp() # show the temperature and time
# -- End of button 3 - Restart handling                

# --Check for button 4 --- switch to Menu mode
            elif event.button==4: # check for button 4
                if Debugprt == True:
                    print ("Button 4 switches to Menu mode")
                Menumode = True # Turn on Menu Mode for future events
                Mmenuline = 1 # start main menu with line 1 highlighted
# Note: Menunow is just a reference to a menu and not the contents of the menu itself
# This makes for easy, efficient checks for the current menu
                Menunow = main_menu # set the current menu, for the record
                show_text_menu(main_menu,Mmenuline,button_menu2) # Show the main menu, 1st line highlighted            
# -- End of button 4 - Select Menu Mode

# --Handle touchscreen events in non-menu mode ------
# Switches display show type (graph or temp) if the screen is clicked/touched
#   because it frees up a GPIO button for other uses 
        elif event.type == pygame.MOUSEBUTTONDOWN: # check for mouse click/touch
# -Cleanup for noisy MOUSEBUTTON events on PiTFT, which causes problems
# Note: Mouse position info for the touchscreen is currently useless on Stretch.
# SDL TSLIB support used to do this stuff
                if event.button == 1: # only watch for button 1 - touch screen filter #1
                    mousetime = pygame.time.get_ticks()/1000 # get the relative time in sec
# Ignore too many MOUSEDOWN events together - touch screen filter #2
                    if mousetime - Mousetimer > Mousewait: # check if enough time has passed
                        Mousetimer = mousetime # if so, record this last touch/click   
                        show_flip() #switch between temp and latest graph display
# --End touchscreen event handler                   

# --Handle Keyboard events in non menu mode ------
        elif event.type==pygame.KEYDOWN: # Replicate PiTFT buttons on keyboard for testing
                if Debugprt == True:
                    print ("Key Pressed ", event.unicode)
# Turn keys into button events                    
                if event.unicode == "h": # "h" key will replicate button 2 - Hold
                    fastevent.post(pygame.event.Event(pygame.USEREVENT+3, button=2))
                elif event.unicode == "r": # "r" key will replicate button 3 - restart
                    fastevent.post(pygame.event.Event(pygame.USEREVENT+3, button=3))
                elif event.unicode == "m": # "m" key will replicate buttton 4, menu mode
                    fastevent.post(pygame.event.Event(pygame.USEREVENT+3, button=4)) 
# emergency exit key is "x" 
                elif event.unicode == "x": # x key will exit the programme
                    Csvlog.close() # close the log file
                    pygame.display.quit() #clean up Pygame
                    sys.exit()
# ---- end of non-menu keyboard event handler

#--------End of normal (non-menu) mode event handler

#############################################
# ----- Menu Mode Event handler 
#############################################
    while Menumode == True: # loop forever, waiting for events in 'menu' mode
        event = pygame.fastevent.wait() # wait for an event object to check
#        if Debugprt == True: # print the event in debug mode
#            print (pygame.time.get_ticks()/1000,Timex, event, "Menu mode") # annoying debug
            
# --Handle Quit if window is closed - X11 display mode only
        if event.type == QUIT: # only works in an X11 window
            Csvlog.close() # close the csv log file
            GPIO.output(Ledgpio, GPIO.LOW) # turn off the LED
            pygame.display.quit() # clean up
            sys.exit() # exit this programme
# -- End of Quit handler

# --Handle the timer pop 1 event, even in Menu mode, to keep recording data up to date         
        elif event.type == pygame.USEREVENT+1: # using literal here for timer pop
            Do_rectimer_updates() # update record variables and log
# -- End of Timper pop 1 event handler in menu mode            

# --Handle the time/temp/LED display update timer pop event 2 in menu mode          
        elif event.type == pygame.USEREVENT+2: # using literal here for timer pop
            Do_ttimer_updates() # Update the LED & time/temp display values
# --End of time pop 2 event handler in menu mode            

# --Handle PiTFT button presses in menu mode driven by gpiobut GPIO callback function thread
        elif event.type == USEREVENT+3: # check for a PiTFT button press, literal value
            if Debugprt == True:
                print ("menu button =", event.button) # debug

########################################
# ---- Menu Mode Button event testing
########################################                
# --Check for button 2 - Menu mode - Up
            if event.button==2: # button 2 = GPIO 22
                if Debugprt == True:
                    print ("Button 2 is Up")
# -Handle Up on the main menu
                if Menunow == main_menu: # Check if we're on the main menu
                    if Mmenuline == 1: # if we're at the top
                        Mmenuline = Mmenumax # roll to the bottom line
                    else:
                        Mmenuline = Mmenuline-1 # otherwise, just go up a line
                    show_text_menu(main_menu,Mmenuline,button_menu2) # show the new highlighted menu line
# -End of Up for the main menu

# -Handle Up in the Temperature Adjustment menu
# Note: the following is a reference comparison and not a content comparison
# i.e. Even if the contents of the tempadj_menu have changed it can be True
                elif Menunow == tempadj_menu: # check if we're in the temp adjust menu
                    if Ttempadj <10: # upper limit is 10 for now
                        Ttempadj = Ttempadj + 0.1 # increment Temperature adjustment
# Handle the binary to decimal conversion problem near zero
                        if Ttempadj<0.001 and Ttempadj>-0.001: # check if almost zero
                            Ttempadj = 0 # if so, make it actually zero
                    tempadj_menu[2][4] = str(Ttempadj) #show current temperature adjustment
                    show_text_menu(tempadj_menu,2,button_menu2) # show updated menu
# -End of Up in the Temperature Adjustment menu                    

# -Handle Up in the Time Adjustment menu
                elif Menunow == timeadj_menu and Ttimeval < len(Timevals)-1: # chk if we're in the time adjust menu
                    Ttimeval = Ttimeval + 1 # move to the next highest value
                    timeadj_menu[2][4] = str(Timevals[Ttimeval]) #show current time adjustment
                    show_text_menu(timeadj_menu,2,button_menu2) # show new menu                    Timeval = Timeval - 1 #go up one item if not at the start value
# -End of Up in the Time Adjustment  menu

# --Check for button 3 --- Down - in memu mode     
            elif event.button==3: # Check for Down
                if Debugprt == True:
                    print ("Button 3 is Down")
# -Handle Down on main menu                    
                if Menunow == main_menu: # Check if we're on the main menu
                    if Mmenuline == Mmenumax: # if we're at the bottom
                        Mmenuline = 1 # roll to the top line (line 0 is the title)
                    else:
                        Mmenuline = Mmenuline+1 # Otherwise just go to the next line
                    show_text_menu(main_menu,Mmenuline,button_menu2) # show the new highlighted menu line                    
# -End Down handler for the main menu

# -Handle Down on the Temperature Adjustment menu
                elif Menunow == tempadj_menu: # Check if we're on the temp adjust menu
                    if Ttempadj > -10.0: # lower limit is -10 for now
                        Ttempadj = Ttempadj - 0.1 # increment Temperature adjustment
# Handle the binary to decimal conversion imprecision problem near zero
                        if Ttempadj<0.001 and Ttempadj>-0.001: # chk if almost zero
                            Ttempadj = 0 # if so, make it actually zero                        
                    tempadj_menu[2][4] = str(Ttempadj) #show current temperature adjustment
                    show_text_menu(tempadj_menu,2,button_menu2) # show new menu 
# -End of Down on the Temperature Adjustment menu

# -Handle Down in Time adjustment menu
                elif Menunow == timeadj_menu and Ttimeval > 0: # chk if we're in the time adjust menu
                    Ttimeval = Ttimeval - 1 # go down one item if not at the first value
                    timeadj_menu[2][4] = str(Timevals[Ttimeval]) #show current time adjustment
                    show_text_menu(timeadj_menu,2,button_menu2) # show updated menu 
# -End of Down in the Time Adjustment menu

# --Check for button 4 --- Select, in menu mode
            elif event.button==4:
                if Debugprt == True:
                    print ("Button 4 is Select")

########################################
# ---- Handle Select on the main menu
########################################
                if Menunow == main_menu: # check if we're on the main menu
                  
# -Handle 'Exit' selected from main menu  - always first, for debugging              
                    if Mmenuline == 4: # check for line 4 select - Exit programme
                        Csvlog.close() # close the csv log file
                        GPIO.output(Ledgpio, GPIO.LOW) # turn off the LED
                        pygame.display.quit() # clean up
                        sys.exit() # exit this programme

# -Handle Temp Adjust selected from main menu menu                       
                    elif Mmenuline == 1: # Check for Temp Adj
                        if Debugprt == True:
                            print ("Selected on Temp Adj menu")
                        Menunow = tempadj_menu # update what menu we're in now
                        Ttempadj = Tempadj # Get the current adjustment for the menu
                        tempadj_menu[2][4] = str(Ttempadj) #show current temperature adjustment
                        show_text_menu(tempadj_menu,2,button_menu2) # show new menu

# -Handle Time Adjust selected from main menu                       
                    elif Mmenuline == 2: # Check for Time Adj
                        if Debugprt == True:
                            print ("Selected Time Adj")
                        Menunow = timeadj_menu # update what menu we're in now
                        Ttimeval = Timeval # Set a temporary index for menu purposes
                        timeadj_menu[2][4] = str(Timevals[Ttimeval]) #show current time adjustment
                        show_text_menu(timeadj_menu,2,button_menu2) # show new menu

# -Handle 'Return' selected from main menu                    
                    elif Mmenuline == 3: # check for Return selected                        
# Show updated display now, as appropriate to the mode we were in before menu mode
                        if Displayshow==Displaytemp: # if we were showing the temperature
                            show_temp() # show current temperature
# Show graph, if that's the mode we were in           
                        elif Displayshow == Displaygraph: # show a graph, if required
                            make_graph()
                            show_graph()
                        Menumode = False # Turn off menu mode for now, as if 'Return' was selected       
########################################
# ---- Handle Select in secondary menus
########################################

# -Handle Select in Temperature Adjustment menu
                elif Menunow == tempadj_menu: # check if we're on the temp adjust menu
                    Tempadj = Ttempadj # Put the new adjustment value into effect
# Note: it might be good to also reset values, but there might be a need not to do this                    
                    Menunow = main_menu # Update current menu to main_menu
                    show_text_menu(main_menu,Mmenuline,button_menu2) # show it
# -End Select in Temperature Adjustment menu

# -Handle Select in Time Adjustment menu
                elif Menunow == timeadj_menu: #check if we're in the time adj menu
                    Tinterval = Timevals[Ttimeval] # set the new timer interval in msec
# Define an updated pygame user event for the new recording timer value
                    pygame.time.set_timer(USEREVENT+1, Tinterval*1000) # create a timer event
                    Menunow = main_menu # Update current menu to the main_menu
                    show_text_menu(main_menu,Mmenuline,button_menu2) # show it                    
# -End Select in Time Adjustment menu                

# --End of button handler in menu mode

########################################
# ---- Handle Keyboard events in Menu mode
########################################
        elif event.type==pygame.KEYDOWN: # Replicate PiTFT buttons on keyboard for testing
            if Debugprt == True:
                print ("Menu mode Key Pressed ", event.unicode)
# --Simulate PiTFT buttons from keyboard - as if they were GPIO events                
            if event.unicode == "u": # "u" key will replicate button 2 - Up
                fastevent.post(pygame.event.Event(pygame.USEREVENT+3, button=2))
            elif event.unicode == "d": # "d" key will replicate button 3 - Down
                fastevent.post(pygame.event.Event(pygame.USEREVENT+3, button=3))
            elif event.unicode == "s": # "s" key will replicate button 4 - Select
                fastevent.post(pygame.event.Event(pygame.USEREVENT+3, button=4))
            elif event.unicode == "x": # x key will exit the programme
                Csvlog.close() # close the log file
                GPIO.output(Ledgpio, GPIO.LOW) # turn off the LED
                pygame.display.quit() # clean up Pygame
                sys.exit()
# --End of menu mode keyboard event handler
            
# ---------End  of Menu mode event loop -------

# ---------End of all event loops --------

if Debugprt == True:
    print ("Fell through the bottom of the code") # Debug - should not happen, eh
Csvlog.close() # close the log file
GPIO.output(Ledgpio, GPIO.LOW) # turn off the LED
pygame.display.quit() # clean up and revert to X11 on main display, if available

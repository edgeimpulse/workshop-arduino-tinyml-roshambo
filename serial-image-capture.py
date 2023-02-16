#!/usr/bin/env python3

"""
Serial Image Capture

Simple GUI to display and save images received over a serial port. Images
must be encoded in base64 with the appropriate EIML protocol header. 

Required dependencies:

    python -m pip install Pillow pyserial

Run with:

    python serial-image-capture.py

Author: EdgeImpulse, Inc.
Date: January 5, 2023
License: Apache-2.0
"""

import tkinter as tk
import threading
import time
import base64
import io
import uuid
import os

# Install with `python -m pip install Pillow pyserial`
from PIL import Image, ImageTk
import serial
import serial.tools.list_ports

# Settings
INIT_BAUD = 230400          
MAX_REFRESH = 10            # Milliseconds
SERIAL_LIST_REFRESH = 1000  # Milliseconds
EMBIGGEN_FACTOR = 4         # Scale image by this amount for viewport
IMG_EXT = ".png"            # Extension for image (.png or .jpg)

# EIML constants for header
# |     SOF     |  format  |   width   |   height  |
# | xFF xA0 XFF | [1 byte] | [4 bytes] | [4 bytes] |
EIML_HEADER_SIZE = 12
EIML_SOF_SIZE = 3
EIML_FORMAT_SIZE = 1
EIML_WIDTH_SIZE = 4
EIML_HEIGHT_SIZE = 4
EIML_SOF_B64 = b'/6D/'
EIML_RESERVED = 0
EIML_GRAYSCALE = 1
EIML_RGB888 = 2

#-------------------------------------------------------------------------------
# Classes

class GUI:
    """Main GUI class
    
    Controls the window used to visualize the received images. Buttons allow for
    connecting to a device and saving images.
    
    Note that the refresh_ method(s) are called in an independent thread.
    If another thread calls update_ method(s), data is passed safely between
    threads using a mutex.
    """

    # Return codes
    OK = 0
    ERR = 1
    
    def __init__(self, root):
        """Constructor"""
    
        self.root = root
        self.connected = False
        self.port = ""
        
        # Start image Rx thread
        self.rx_task = ImageRxTask(self)
        self.rx_task.daemon = True
        self.rx_task.start()

        # Get initial list of ports
        self.available_ports = []
        serial_list = sorted(self.rx_task.get_serial_list())
        print("Available serial ports:")
        if serial_list:
            for port, desc, hwid in serial_list:
                print("  {} : {} [{}]".format(port, desc, hwid))
                self.available_ports.append(port)
        else:
            self.available_ports = [""]

        # Create the main container
        self.frame_main = tk.Frame(self.root)
        self.frame_main.pack(fill=tk.BOTH, expand=True)

        # Allow middle cell of grid to grow when window is resized
        self.frame_main.columnconfigure(1, weight=1)
        self.frame_main.rowconfigure(0, weight=1)
        
        # TkInter variables
        self.var_port = tk.StringVar()
        if self.available_ports:
            self.var_port.set(self.available_ports[0])
        self.var_baud = tk.IntVar()
        self.var_baud.set(INIT_BAUD)
        self.var_big = tk.IntVar()
        self.var_res = tk.StringVar()
        self.var_res.set("Resolution: ")
        self.var_fps = tk.StringVar()
        self.var_fps.set("FPS: ")
        self.var_label = tk.StringVar()
        
        # Create control widgets
        self.frame_control = tk.Frame(self.frame_main)
        self.label_port = tk.Label( self.frame_control,
                                    text="Port:")
        self.menu_port = tk.OptionMenu(self.frame_control, self.var_port, *self.available_ports)
        self.label_baud = tk.Label( self.frame_control,
                                    text="Baud:")
        self.entry_baud = tk.Entry( self.frame_control,
                                    textvariable=self.var_baud)
        self.button_connect = tk.Button(    self.frame_control,
                                            text="Connect",
                                            padx=5,
                                            command=self.on_connect_clicked)
        self.checkbox_big = tk.Checkbutton(self.frame_control,
                                            text="Embiggen view",
                                            variable=self.var_big,
                                            onvalue=1,
                                            offvalue=0)
        self.label_res = tk.Label(  self.frame_control,
                                    textvariable=self.var_res)
        self.label_fps = tk.Label(  self.frame_control, 
                                    textvariable=self.var_fps)
        self.label_label = tk.Label(self.frame_control,
                                    text="Label:")
        self.entry_label = tk.Entry(self.frame_control,
                                    textvariable=self.var_label)
        self.button_save = tk.Button(   self.frame_control, 
                                        text="Save Image", 
                                        padx=5,
                                        command=self.on_save_clicked)

        # Create canvas
        self.canvas = tk.Canvas(self.frame_main, width=100, height=100)

        # Lay out control frame on main frame
        self.frame_control.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NW)

        # Lay out widgets on control frame
        self.label_port.grid(row=0, column=0, padx=5, pady=3, sticky=tk.W)
        self.menu_port.grid(row=0, column=1, padx=5, pady=3, sticky=tk.W)
        self.label_baud.grid(row=1, column=0, padx=5, pady=3, sticky=tk.W)
        self.entry_baud.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)
        self.button_connect.grid(row=2, column=0, columnspan=2, padx=5, pady=3)
        self.checkbox_big.grid(row=3, column=0, columnspan=2, padx=5, pady=0, sticky=tk.W)
        self.label_res.grid(row=4, column=0, columnspan=2, padx=5, pady=0, sticky=tk.W)
        self.label_fps.grid(row=5, column=0, columnspan=2, padx=5, pady=0, sticky=tk.W)
        self.label_label.grid(row=6, column=0, padx=5, pady=3, sticky=tk.W)
        self.entry_label.grid(row=6, column=1, padx=5, pady=3, sticky=tk.W)
        self.button_save.grid(row=7, column=0, columnspan=2, padx=5, pady=3)

        # Lay out canvas on main frame grid
        self.canvas.grid(row=0, column=1, padx=5, pady=5, sticky=tk.NW)

        # Place focus on port entry button by default
        self.menu_port.focus_set()
        
        # Start refresh loop
        self.img_mutex = threading.Lock()
        self.img_mutex.acquire()
        self.timestamp = time.monotonic()
        self.canvas.after(MAX_REFRESH, self.refresh_image)

        # Update serial port list every 1 seconds
        self.canvas.after(SERIAL_LIST_REFRESH, self.refresh_serial_list)
        
    def __del__(self):
        """Desctructor: make sure we close that serial port!"""
        self.rx_task.close()
        
    def on_connect_clicked(self):
        """Attempt to connect to the given serial port"""
        
        # Check to make sure baud rate is an integer
        try:
            baud_rate = int(self.var_baud.get())
        except:
            print("ERROR: baud rate must be an integer")
            return

        # Don't connect if no port is selected
        self.port = self.var_port.get()
        if self.port == "":
            print("No port selected")
            return

        # Say that we're trying to connect
        print("Connecting to {} at a baud rate of {} ...".format(self.port, baud_rate))
        
        # Attempt to connect to device
        res = self.rx_task.connect(self.port, baud_rate)
        if (res == self.rx_task.OK):
            print("Connected!")
            self.connected = True
        else:
            print("Could not connect")
            self.connected = False
        
    def on_save_clicked(self):
        """Save current image to the disk drive"""

        # Set focus (just press 'enter' to capture more photos)
        self.button_save.focus_set()

        # Only capture image if connected to device
        if self.connected:

            # Generate unique filename (last 12 characters from uuid4 method)
            # and make sure it does not conflict with any existing filenames
            label = str(self.entry_label.get())
            while True:
                uid = str(uuid.uuid4())[-12:]
                if label == "":
                    filename = uid + IMG_EXT
                else:
                    filename = label + "." + uid + IMG_EXT
                if not os.path.exists(filename):
                    break

            # Ensure there's only acceptable characters in the filename
            filename = "".join(i for i in filename if i not in "\/:*?<>|")

            # Save file
            try:
                self.img.save(filename)
                print("Saved: " + filename)
            except Exception as e:
                print("ERROR:", e)
        
        # Do nothing if not connected
        else:
            print("ERROR: Not connected to capture device")
        

    def refresh_image(self):
        """Update canvas periodically
        
        Updates only happen if there is a new image to be saved. To make this
        function thread-safe, it checkes if a mutex/lock is available first.
        """
    
        # If new image is ready, update the canvas
        if self.img_mutex.acquire(blocking=False):
        
            # If we're interrupted, just fail gracefully
            try:

                # Get width and height
                img_w, img_h = self.img.size

                # Resize image for display
                if (int(self.var_big.get()) == 1):
                    disp_w = EMBIGGEN_FACTOR * img_w
                    disp_h = EMBIGGEN_FACTOR * img_h
                    disp_img = self.img.resize((disp_w, disp_h))
                else:
                    disp_w = img_w
                    disp_h = img_h
                    disp_img = self.img
        
                # Convert to TkInter image class member to avoid garbage collection
                self.tk_img = ImageTk.PhotoImage(disp_img)

                #Show image on canvas
                self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
                self.canvas.config(width=disp_w, height=disp_h)

                # Update FPS
                self.fps = 1 / (time.monotonic() - self.timestamp)
                self.timestamp = time.monotonic()
                self.var_fps.set("FPS: {:.1f}".format(self.fps))

                # Update resolution
                self.var_res.set("Resolution: {}x{}".format(img_w, img_h))
            
            except:
                pass
        
        self.canvas.after(MAX_REFRESH, self.refresh_image)

    def update_image(self, img):
        """Method to update the image in the cavas
        
        This will release a lock to notify the other thread that new image data
        is ready.
        """
    
        # Save image to class member
        self.img = img
        
        # Release lock to notify other thread that it can update the canvas
        self.img_mutex.release()

    def refresh_serial_list(self):
        """Update serial port list periodically"""

        # Update available ports
        serial_list = sorted(self.rx_task.get_serial_list())
        if serial_list:
            new_ports = []
            for port, desc, hwid in serial_list:
                new_ports.append(port)
        else:
            new_ports = [""]

        # See if we're still connected
        if (self.connected) and (self.port not in new_ports):
            print("Disconnected")
            self.connected = False
            self.port = ""
            self.var_port.set(self.port)

        # If list has changed, update menu
        if new_ports != self.available_ports:
            self.available_ports = new_ports
            self.menu_port['menu'].delete(0, 'end')
            if self.available_ports:
                for port in self.available_ports:
                    self.menu_port['menu'].add_command(label=port, 
                                                        command=tk._setit(self.var_port, port))
            else:
                self.available_ports = [""]

        # Reschedule function
        self.canvas.after(SERIAL_LIST_REFRESH, self.refresh_serial_list)
        
class ImageRxTask(threading.Thread):
    """Background thread to read image data and send to GUI"""

    # Receiver state machine constants
    RX_STRING = 0
    RX_JPEG = 1
    RX_EIML = 2

    # Return codes
    OK = 0
    ERR = 1

    def __init__(self, parent):
        """Constructor"""

        self.gui = parent
        super().__init__()
        
        # Create serial port
        self.ser = serial.Serial()
            
    def __del__(self):
        """Desctructor"""
        self.close()

    def get_serial_list(self):
        """Get a list of serial ports"""
        return serial.tools.list_ports.comports()
            
    def connect(self, port, baud_rate):
        """Connect to the given serial port"""
        
        # Try closing the port first (just in case)
        try:
            self.ser.close()
        except Exception as e:
            print("ERROR:", e)
        
        # Update port settings
        self.ser.port = port
        self.ser.baudrate = baud_rate

        # Try to open a connection
        try:
            self.ser.open()
            ret = self.OK
        except Exception as e:
            print("ERROR:", e)
            ret = self.ERR

        return ret
            
    def close(self):
        """Close serial port"""
        self.ser.close()
        
    def run(self):
        """Main part of the thread"""
    
        # Rx state machine state
        rx_mode = self.RX_STRING
        
        # Where we store the base64 encoded image message
        rx_buf = b''
            
        # Forever loop
        while True:
                
            # Read bytes if there are some waiting
            try:
                if self.ser.in_waiting > 0:
                    while(self.ser.in_waiting):

                        # Read those bytes
                        rx_buf = rx_buf + self.ser.read()
                    
                        # Look for start of JPEG or EIML header
                        if rx_mode == self.RX_STRING:
                            if rx_buf == b'/9j/':
                                rx_mode = self.RX_JPEG
                            if rx_buf == EIML_SOF_B64:
                                rx_mode = self.RX_EIML
                        
                        # Look for newline ('\n')
                        if rx_buf[-1] == 10:
                        
                            # If we're not recording anything, print it
                            if rx_mode == self.RX_STRING:
                                try:
                                    print("Recv:", rx_buf.decode("utf-8").strip())
                                except:
                                    pass
                        
                            # If we're recording the JPEG image data, display it
                            elif rx_mode == self.RX_JPEG:
                                rx_mode = self.RX_STRING
                                
                                # Remove \r\n at the end
                                rx_buf = rx_buf[:-2]
                                
                                # Attempt to decode image and display in GUI
                                try:
                                    img_dec = base64.b64decode(rx_buf)
                                    img_stream = io.BytesIO(img_dec)
                                    img = Image.open(img_stream)
                                    self.gui.update_image(img)
                                except:
                                    pass
                                    
                            # If we're recording the raw image data, display it
                            elif rx_mode == self.RX_EIML:
                                rx_mode = self.RX_STRING
                                
                                # Remove \r\n at the end
                                rx_buf = rx_buf[:-2]
                                
                                # Attempt to decode image and display in GUI
                                try:
                                    # Decode message
                                    msg_dec = base64.b64decode(rx_buf)
                                    
                                    # Extract info from header
                                    idx = EIML_SOF_SIZE
                                    format = msg_dec[idx]
                                    idx += EIML_FORMAT_SIZE                                       
                                    width = int.from_bytes(msg_dec[idx:(idx + EIML_WIDTH_SIZE)], 
                                                                                        'little')
                                    idx += EIML_WIDTH_SIZE
                                    height = int.from_bytes(msg_dec[idx:(idx + EIML_HEIGHT_SIZE)],
                                                                                        'little')
                                    idx += EIML_HEIGHT_SIZE
                                    
                                    # Create image and update GUI
                                    if format == EIML_RGB888:
                                        img = Image.frombytes(  'RGB', 
                                                                (width, height), 
                                                                msg_dec[idx:], 
                                                                'raw')
                                    elif format == EIML_GRAYSCALE:
                                        img = Image.frombytes(  'L',
                                                                (width, height),
                                                                msg_dec[idx:],
                                                                'raw')
                                        img = img.convert(mode='RGB')
                                    self.gui.update_image(img)
                                    
                                except:
                                    print(idx)
                                    pass
                            
                            # Clear buffer
                            rx_buf = b''
                
                # Make sure the thread sleeps for a bit to let other things run
                time.sleep(MAX_REFRESH / 1000)
            except:
                time.sleep(MAX_REFRESH / 1000)
                pass

#-------------------------------------------------------------------------------
# Main

if __name__ == "__main__":

    # Initialize TkInter
    root = tk.Tk()
    root.title("Serial Image Capture")

    # Allow for 'enter' as hotkey for interacting with buttons/checkbuttons
    root.bind_class("Button", "<Key-Return>", lambda event: event.widget.invoke())
    root.bind_class("Checkbutton", "<Key-Return>", lambda event: event.widget.toggle())

    # Start GUI
    main_ui = GUI(root)
    root.mainloop()

# Roshambo Image Classification Workshop

Welcome to the Roshambo workshop! We will build an image classification system that automatically identifies the rock, paper, scissors hand gestures on a low-power embedded system. Specifically, we will perform the following steps:

 1. Capture raw data using the Arduino board
 2. Automatically generate new samples using data augmentation
 3. Train a convolutional neural network on the dataset using Edge Impulse
 4. Test inference locally on the Arduino using a static buffer
 5. Perform live, continuous inference that identifies hand gestures in real time

> **Note**
> Helpful information will be highlighted in boxes like this. As the written documentatation and code for this workshop are all open source, you are welcome to use parts (or all) of this workshop to create your own course, workshop, etc. We just ask for attribution!
{% endnote %}

## Required Hardware

This workshop is designed for the [Arduino Tiny Machine Learning Kit](https://store-usa.arduino.cc/products/arduino-tiny-machine-learning-kit).

If you do not have the kit, then you will need an [Arduino Nano 33 BLE Sense](https://store-usa.arduino.cc/products/arduino-nano-33-ble-sense) and an [OV7675 camera](https://www.arducam.com/products/camera-breakout-board/0-3mp-ov7675/). Connect the camera to the Arduino pins given at the top of [this sketch](01-data-capture/nano33_tinyml_kit_image_serial/nano33_tinyml_kit_image_serial.ino).

## Prerequisites

Install the following programs:

 * [Arduino IDE](https://www.arduino.cc/en/software) (this workshop was tested with v2.0.3)
 * [Python](https://www.python.org/downloads/) (this workshop was tested with v3.10.2)

[Download this repository](https://github.com/edgeimpulse/workshop-arduino-tinyml-roshambo/archive/refs/heads/main.zip) as a .zip file. Unzip it somewhere on your computer.

You will also need a [Gmail account](https://accounts.google.com/SignUp) if you do not already have one in order to run Google Colab scripts.

## 01: Data Capture

Almost every supervised machine learning project starts with some kind of dataset. Rather than using a pre-made dataset, we will create our own. This process provides hands-on experience working with raw data and demonstrates how bias might be introduced into machine learning models.

> **Note**
> The data we collect for this workshop will be just enough to build our quick demo. As a result, you can expect a model accuracy of only around 90%. For most production-ready models, you will need a LOT more data! Collecting quality data can be an expensive and time-consuming process.

Open the Arduino IDE. Go to **Tools > Board > Boards Manager...**. Search for "nano 33" in the boards manager pane. Install the **Arduino Mbed OS Nano Boards** board package.

%%%screen-01

Go to **Sketch > Include Library > Add .ZIP Librar...**. Select **Arduino_OV767X.zip** file. This library is required for the Arduino Nano 33 BLE Sense to communicate with the camera on the TinyML kit.

Go to **File > Open...** and open the sketch **01-data-capture/nano33_tinyml_kit_image_serial/nano33_tinyml_kit_image_serial.ino**. Feel free to examine the code in the file to understand how images are captured, scaled, and cropped.

Make sure the Arduino board is plugged into your computer. Select **Tools > Board > Arduino Mbed OS Nano Boards > Arduino Nano 33 BLE**. Go to **Tools > Port** and select the associated port for your Arduino board. Select **Sketch > Upload** to compile and upload the program to your Arduino board.

You should see "Done" if your program uploaded successfully. You are welcome to open the Serial Monitor to see the base64 image data being sent from the Arduino. However, you must close the Serial Monitor when finished for the next part (i.e. you need to free the serial port).

Open a terminal window and navigate to this directory. For example:

```shell
cd Downloads/workshop-arduino-tinyml-roshambo/
```

Install the [PySerial](https://pyserial.readthedocs.io/en/latest/) and [Pillow](https://pillow.readthedocs.io/en/stable/) Python packages:

```shell
python -m pip install Pillow pyserial
```

Run the Serial Image Capture Python script:

```shell
python 01-data-capture/serial-image-capture.py
```

Pay attention to the serial ports printed to the console! Copy the serial port location for your Arduino board. For example, this might be something like *COM7* on Windows or */dev/cu.usbmodem1442201* on macOS.

%%%screen-02

Paste that serial port location into the *Port* entry in the *Serial Image Capture* GUI. Make sure that the baud rate matches that found in the Arduino sketch (should be 230400 unless you changed it).

Press **Connect**. You should see a live view of the Arduino camera. Click *Embiggen view* to make the image bigger. Due to the slow nature of converting and transmitting raw image data over a serial connection, do not expect more than a few frames per second.

Enter "rock" for your first label. Hold your fist over the camera and ensure that you can see your whole hand in the viewer. Click **Save Image**. This will save the image shown in the viewer at the original resolution (default: 30x30, grayscale) in the directory you ran Python (e.g. this directory).

%%%screen-03

Repeat this process about 50 times. Each time, you should move your fist slightly (to help ensure the model is robust), but make sure your fist is fully visible in the viewer each time.

Repeat the data collection process for "paper" (hand flat out over the camera). Once again, ensure that your hand is almost entirely visible where possible. 

%%%screen-04

Do the same thing to gather around 50 images for "scissors" (index and middle finger making a 'V').

%%%screen-05

Next, we want to capture some background and unkown samples so that the model can tell that you are not giving one of the target labels. Use the label "_background" and capture around 50 images of your background.

%%%screen-06

> **Note**
> We recommend using an underscore ('_') prefix to differentiate non-target labels. It makes reading labels a little easier in future steps.

Finally, set the label to "_unknown" and capture around 50 images of your hand performing a gesture that is clearly not one of "rock," "paper," or "scissors."

%%%screen-07

When you are done, exit out of the *Serial Image Capture* program (click the 'X' in the corner of the window like you would for any application). Add all of your newly created images to a ZIP file named **dataset.zip**. If you are using macOS or Linux, you can accomplish this with the following command:

```shell
zip -FS -r dataset.zip *.png
```

> **Note**
> If you are unable to collect data for this project, you are welcome to use the dataset provided in this repository: [Arduino_OV767X.zip](Arduino_OV767X.zip?raw=true). Note that this dataset is unique to one hand and in one environment. It likely will not work as well for you, as your hands are different size/shape/color, and your environment is different.

## License


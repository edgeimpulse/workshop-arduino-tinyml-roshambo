# Roshambo Image Classification Workshop

Welcome to the Roshambo workshop! We will create an image classification system that automatically identifies the rock, paper, scissors hand gestures on a low-power embedded system. Specifically, we will perform the following steps:

 1. Capture raw data using the Arduino board
 2. Automatically generate new samples using data augmentation
 3. Train a convolutional neural network on the dataset using Edge Impulse
 4. Test inference locally on the Arduino using a static buffer
 5. Perform live, continuous inference that identifies hand gestures in real time

## Prerequisites

Install the following programs:

 * [Arduino IDE](https://www.arduino.cc/en/software) (this workshop was tested with v2.0.3)
 * [Python](https://www.python.org/downloads/) (this workshop was tested with v3.10.2)

## 01: Data Capture


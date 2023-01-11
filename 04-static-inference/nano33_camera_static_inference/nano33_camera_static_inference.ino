/**
 * Arduino Nano 33 BLE Sense TinyML Kit - Static Classification
 * 
 * Perform inference with a static buffer to ensure that results match with
 * those from Edge Impulse. Change the library to your library and paste in
 * known-good sample array for input_buf[].
 * 
 * Author: Shawn Hymel (EdgeImpulse, Inc.)
 * Date: January 6, 2023
 * License: Apache-2.0
 */


// Include the Edge Impulse Arduino library here
#include <YOUR_EI_LIBRARY.h>

// Constants (from <library-name>/src/model-parameters/model_metadata.h)
#define NUM_CLASSES         EI_CLASSIFIER_LABEL_COUNT           // 5 classes

// Function declarations
static int get_signal_data(size_t offset, size_t length, float *out_ptr);

// Raw features copied from test sample (Edge Impulse > Model testing)
static float input_buf[] = {
  // Paste features here
};

// Wrapper for raw input buffer
static signal_t sig;

// Setup function that is called once as soon as the program starts
void setup() {
  
  // Initialize serial and wait to connect
  Serial.begin(115200);
  while (!Serial);

  // run_classifier() uses a callback function to fill its internal buffer
  // from your input_buf when requested. We need to assign the inference
  // buffer length and callback function here.
  sig.total_length = EI_CLASSIFIER_DSP_INPUT_FRAME_SIZE;
  sig.get_data = &get_signal_data;
}

// Loop function that is called repeatedly after setup()
void loop() {

  ei_impulse_result_t result; // Used to store inference output
  EI_IMPULSE_ERROR res;       // Return code from inference

  // Call run_classifier(). Pass in the addresses for the sig struct and
  // the result struct. Set debug to false. Save the return code in the res
  // variable. See here for more information and an example:
  // https://docs.edgeimpulse.com/reference/c++-inference-sdk-library/functions/run_classifier
  res = run_classifier(&sig, &result, false);

  // Print return code, time it took to perform inference, and inference
  // results. Note that the grader will ignore these outputs.
  ei_printf("run_classifier returned: %d\r\n", res);
  ei_printf("Timing: DSP %d ms, inference %d ms, anomaly %d ms\r\n", 
            result.timing.dsp, 
            result.timing.classification, 
            result.timing.anomaly);
  ei_printf("Predictions:\r\n");
  for (uint16_t i = 0; i < EI_CLASSIFIER_LABEL_COUNT; i++) {
    ei_printf("  %s: ", ei_classifier_inferencing_categories[i]);
    ei_printf("%.5f\r\n", result.classification[i].value);
  }

  // Sleep for a bit
  ei_sleep(1000);
}

// Callback: fill a section of the out_ptr buffer when requested
static int get_signal_data(size_t offset, size_t length, float *out_ptr) {
  for (size_t i = 0; i < length; i++) {
    out_ptr[i] = (input_buf + offset)[i];
  }

  return EIDSP_OK;
}
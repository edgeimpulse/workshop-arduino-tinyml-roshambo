// Include the Edge Impulse Arduino library here
#include <aaai-image-test-01_inferencing.h>

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

  //***TEST: Print memory info
  char msg[50];
  printMemoryInfo(msg, 50);

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

void printMemoryInfo(char* printEvent, int iSize) {
    // allocate enough room for every thread's stack statistics
    int cnt = osThreadGetCount();
    mbed_stats_stack_t *stats = (mbed_stats_stack_t*) malloc(cnt * sizeof(mbed_stats_stack_t));
 
    cnt = mbed_stats_stack_get_each(stats, cnt);
    for (int i = 0; i < cnt; i++) {
        snprintf_P(printEvent, iSize, "Thread: 0x%lX, Stack size: %lu / %lu\r\n", stats[i].thread_id, stats[i].max_size, stats[i].reserved_size);
        Serial.println(printEvent);
    }
    free(stats);
 
    // Grab the heap statistics
    mbed_stats_heap_t heap_stats;
    mbed_stats_heap_get(&heap_stats);
    snprintf_P(printEvent, iSize, "Heap size: %lu / %lu bytes\r\n", heap_stats.current_size, heap_stats.reserved_size);
    Serial.println(printEvent);
}
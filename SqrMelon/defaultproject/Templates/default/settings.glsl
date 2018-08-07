
// Fog at 100% at this distance, break condition for the raymarch loop.
const float FAR = 400.0;
// Maximum iterations in raymarch loop.
const int STEPS = 400;

const float REFL_NEAR = 0.1;
const float REFL_FAR = 40.0;
const int REFL_STEPS = 100;

// Reflection pass downscale factor, do not define to disable reflections
#define REFL_FACTOR 4

// ambient occlusion
#define AO_WEIGHT 1.0
#define AO_RADIUS 1.0
/*
The given fog is linear 0-1 depth, so at the far clipping plane we always have 100% fog
This is the place to change the fog response, square it for better view distance,
smoothstep it for no fog at a certain region, or raise it to a small power (< 1) to make it really foggy!
*/
float FogRemap(float fog)
{
    return fog; // no change
    // return pow(fog, 3.0); // better view distance
    // return smoothstep(0.5, 1.0, fog); // fog only kicks in halfway towards the FAR plane
    // return pow(fog, 0.1); // really foggy
}

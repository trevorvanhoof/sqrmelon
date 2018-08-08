// Prepass cone tracing at a lower resolution, more advanced implementation can be found in:
// https://www.shadertoy.com/view/XdycWy by Henrik Münther
void main()
{
    Ray ray = ScreenRay();

    Hit hit = Trace(ray, 0.0, FAR, STEPS);

    outColor0 = vec4(hit.totalDistance-1.0,0,0,0);
}

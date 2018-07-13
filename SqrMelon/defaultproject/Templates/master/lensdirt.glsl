void main()
{
    vec2 c,b=(gl_FragCoord.xy*2-uResolution)/uResolution.y;
    float d,r,v=.7*perlin(b*16+snoise(b*8),8,2,.5)+perlin(b*16+snoise(b*16),8,2,.5)*.35;
    vec3 a=vec3(0);
    for(int i=0;i<1000;++i){
        r=cub(h1(i*2.2-1000)+.2)*.1+.05;
        c=b-(h2(i*.8+2000)*4.-2.);
        if(h1(i*.22 + 1500)>0.8){pR(c,h1(i));d=-fHexagon(c,r);}else d=r-length(c);if(h1(i*.12+40)>.75)d=(r*.1-abs(d))*2;
        vec4 cl=h4(i);
        a+=sat(d*(30+30*h1(i*PI-2000)))*hsv2rgb(vec3(fract(cub(cl.x*.8)+.1),cl.y*cl.z*.6,cl.w*sqr(cl.w)/(.5+r*80)));
    }
    outColor0=vec4(a,1)+pow(v,8)+vec4(0,.01,.05,0)*(.5-.5*a.y)+vec4(.02,0,.01,0)*(.5-.5*a.x);
}

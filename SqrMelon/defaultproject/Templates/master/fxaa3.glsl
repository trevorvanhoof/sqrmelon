#version 420
uniform vec2 uResolution;uniform sampler2D uImages[1];out vec4 z;float aa(vec3 a){vec3 b=vec3(.299,.587,.114);return dot(a,b);}
#define bb(a)texture(uImages[0],a)
#define cc(a)aa(texture(uImages[0],a).rgb)
#define dd(a,b)aa(texture(uImages[0],a+(b*c)).rgb)
void main(){vec2 a=gl_FragCoord.xy/uResolution,c=1/uResolution;vec4 b=bb(a);b.y=aa(b.rgb);float d=dd(a,vec2(0,1)),e=dd(a,vec2(1,0)),f=dd(a,vec2(0,-1)),g=dd(a,vec2(-1,0)),h=max(max(f,g),max(e,max(d,b.y))),i=h-min(min(f,g),min(e,min(d,b.y)));if(i<max(.0833,h*.166)){z=bb(a);return;}h=dd(a,vec2(-1,-1));float j=dd(a,vec2( 1,1)),k=dd(a,vec2( 1,-1)),l=dd(a,vec2(-1,1)),m=f+d,n=g+e,o=k+j,p=h+l,q=c.x;
bool r=abs((-2*g)+p)+(abs((-2*b.y)+m)*2)+abs((-2*e)+o)>=abs((-2*d)+l+j)+(abs((-2*b.y)+n)*2)+abs((-2*f)+h+k);if(!r){f=g;d=e;}else q=c.y;h=f-b.y,e=d-b.y,f=f+b.y,d=d+b.y,g=max(abs(h),abs(e));i=clamp((abs((((m+n)*2+p+o)*(1./12))-b.y)/i),0,1);if(abs(e)<abs(h))q=-q;else f=d;vec2 s=a,t=vec2(!r?0:c.x,r?0:c.y);if(!r)s.x+=q*.5;else s.y+=q*.5;
vec2 u=vec2(s.x-t.x,s.y-t.y);s=vec2(s.x+t.x,s.y+t.y);j=((-2)*i)+3;d=cc(u);e=i*i;h=cc(s);g*=.25;i=b.y-f*.5;j=j*e;d-=f*.5;h-=f*.5;bool v,w,x,y=i<0;
#define ee(Q) v=abs(d)>=g;w=abs(h)>=g;if(!v)u.x-=t.x*Q;if(!v)u.y-=t.y*Q;x=(!v)||(!w);if(!w)s.x+=t.x*Q;if(!w)s.y+=t.y*Q;
#define ff if(!v)d=cc(u.xy);if(!w)h=cc(s.xy);if(!v)d=d-f*.5;if(!w)h=h-f*.5;
ee(1.5)if(x){ff ee(2.)if(x){ff ee(4.)if(x){ff ee(12.)}}}e=a.x-u.x;f=s.x-a.x;if(!r){e=a.y-u.y;f=s.y-a.y;}q*=max((e<f?(d<0)!=y:(h<0)!=y)?(min(e,f)*(-1/(f+e)))+.5:0,j*j*.75);if(!r)a.x+=q;else a.y+=q;z=bb(a);}

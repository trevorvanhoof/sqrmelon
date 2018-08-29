/// Utilities for noise

// hash functions
vec4 h4(vec4 p4)
{
	p4 = fract(p4 * vec4(1031, .1030, .0973, .1099));
    p4 += dot(p4, p4.wzxy + 19.19);
    return fract((p4.xxyz + p4.yzzw) * p4.zywx);
}
vec4 h4(float p){return h4(vec4(p));}
vec4 h4(vec2 p){return h4(p.xyxy);}
vec4 h4(vec3 p){return h4(p.xyzx);}
vec3 h3(vec4 p){return h4(p).xyz;}
vec3 h3(float p){return h3(vec4(p));}
vec3 h3(vec2 p){return h3(p.xyxy);}
vec3 h3(vec3 p){return h3(p.xyzx);}
vec2 h2(vec4 p){return h4(p).xy;}
vec2 h2(float p){return h2(vec4(p));}
vec2 h2(vec2 p){return h2(p.xyxy);}
vec2 h2(vec3 p){return h2(p.xyzx);}
float h1(vec4 p){return h4(p).x;}
float h1(float p){return h1(vec4(p));}
float h1(vec2 p){return h1(p.xyxy);}
float h1(vec3 p){return h1(p.xyzx);}

// tiled smooth noise, up to 3D
float snoise(float v,float s){v*=s;float f=floor(v);v-=f;v=v*v*(3-2*v);return mix(h1(mod(f,s)+11.),h1(mod(f+1,s)+11.),v);}
float snoise(vec2 v,vec2 s){v*=s;vec2 f=floor(v);v-=f;v=v*v*(3-2*v);return mix(mix(h1(mod(f,s)+11.),h1(mod(f+vec2(1,0),s)+11.),v.x),mix(h1(mod(f+vec2(0,1),s)+11.),h1(mod(f+1,s)+11.),v.x),v.y);}
float snoise(vec3 v,vec3 s){v*=s;vec3 f=floor(v);v-=f;v=v*v*(3-2*v);return mix(mix(mix(h1(mod(f,s)+11.),h1(mod(f+vec3(1,0,0),s)+11.),v.x),mix(h1(mod(f+vec3(0,1,0),s)+11.),h1(mod(f+vec3(1,1,0),s)+11.),v.x),v.y),mix(mix(h1(mod(f+vec3(0,0,1),s)+11.),h1(mod(f+vec3(1,0,1),s)+11.),v.x),mix(h1(mod(f+vec3(0,1,1),s)+11.),h1(mod(f+1,s)+11.),v.x),v.y),v.z);}
float snoise(vec2 v,float s){return snoise(v,vec2(s));}
float snoise(vec3 v,float s){return snoise(v,vec3(s));}
// without the tiling
float snoise(float v){float f=floor(v);v-=f;v=v*v*(3-2*v);return mix(h1(f),h1(f+1),v);}
float snoise(vec2 v){vec2 f=floor(v);v-=f;v=v*v*(3-2*v);return mix(mix(h1(f),h1(f+vec2(1,0)),v.x),mix(h1(f+vec2(0,1)),h1(f+1),v.x),v.y);}
float snoise(vec3 v){vec3 f=floor(v);v-=f;v=v*v*(3-2*v);return mix(mix(mix(h1(f),h1(f+vec3(1,0,0)),v.x),mix(h1(f+vec3(0,1,0)),h1(f+vec3(1,1,0)),v.x),v.y),mix(mix(h1(f+vec3(0,0,1)),h1(f+vec3(1,0,1)),v.x),mix(h1(f+vec3(0,1,1)),h1(f+1),v.x),v.y),v.z);}

// tiled 3D worley noise
//float _wrap(vec3 v,float s){return mix(mod(v,s),v+s,max(0,-sign(v)));}
vec2 _wrap(vec2 v,vec2 s){return mix(mod(v,s),v+s,max(vec2(0),-sign(v)));}
vec3 _wrap(vec3 v,vec3 s){return mix(mod(v,s),v+s,max(vec3(0),-sign(v)));}
vec4 worley(vec3 v,vec3 s)
{
	vec3 g,z,q,o,r,n=floor(v*s),
	f=fract(v*s);
	float d,m=8;
	int i,j,k;
	for(k=-1;k<=1;k++)
	for(j=-1;j<=1;j++)
	for(i=-1;i<=1;i++)
	{
		g=vec3(i,j,k);
		q=_wrap(n+g,s);
		o=h3(q);
		r=g-f+o;
		d=dot(r,r);
		if(d<m)
		{m=d;z=q;}
	}
	return vec4(m,z);
}
vec4 worley(vec3 v,float s){return worley(v,vec3(s));}
vec3 worley(vec2 v,vec2 s)
{
	vec2 g,z,q,o,r,n=floor(v*s),
	f=fract(v*s);
	float d,m=8;
	int i,j;
	for(j=-1;j<=1;j++)
	for(i=-1;i<=1;i++)
	{
		g=vec2(i,j);
		q=_wrap(n+g,s);
		o=h2(q);
		r=g-f+o;
		d=dot(r,r);
		if(d<m)
		{m=d;z=q;}
	}
	return vec3(m,z);
}
vec3 worley(vec2 v,float s){return worley(v,vec2(s));}
// Non-tiled worley noise
vec4 worley(vec3 v)
{
	vec3 g,z,q,o,r,n=floor(v),
	f=fract(v);
	float d,m=8;
	int i,j,k;
	for(k=-1;k<=1;k++)
	for(j=-1;j<=1;j++)
	for(i=-1;i<=1;i++)
	{
		g=vec3(i,j,k);
		q=n+g;
		o=h3(q);
		r=g-f+o;
		d=dot(r,r);
		if(d<m)
		{m=d;z=q;}
	}
	return vec4(m,z);
}
vec3 worley(vec2 v)
{
	vec2 g,z,q,o,r,n=floor(v),
	f=fract(v);
	float d,m=8;
	int i,j;
	for(j=-1;j<=1;j++)
	for(i=-1;i<=1;i++)
	{
		g=vec2(i,j);
		q=n+g;
		o=h2(q);
		r=g-f+o;
		d=dot(r,r);
		if(d<m)
		{m=d;z=q;}
	}
	return vec3(m,z);
}

// procedural fbm noise
#define FBM(l,c,q) float l(c v,int n,float f, float w){float t=0,a=0,b=1;for(int i=0;i<n;++i){t+=q(v)*b;a+=b;b*=w;v*=f;}return t/a;}
// procedural tiled fbm noise, useable by texture functions
#define FBM_TILED(l,c,q) float l(c v,c s,int n,float f, float w){v=mod(v,s);float t=0,a=0,b=1;for(int i=0;i<n;++i){t+=q(v,s)*b;a+=b;b*=w;s*=f;}return t/a;}
FBM(perlin,float,snoise)
FBM(perlin,vec2,snoise)
FBM(perlin,vec3,snoise)
FBM_TILED(perlin,float,snoise)
FBM_TILED(perlin,vec2,snoise)
float perlin(vec2 v,float s,int n,float f, float w){return perlin(v,vec2(s),n,f,w);}
FBM_TILED(perlin,vec3,snoise)
float perlin(vec3 v,float s,int n,float f, float w){return perlin(v,vec3(s),n,f,w);}

#undef FBM
#undef FBM_TILED

// procedural fbm noise
#define FBM(l,c,q) float l(c v,int n,float f, float w){float t=0,a=0,b=1;for(int i=0;i<n;++i){t+=q(v).x*b;a+=b;b*=w;v*=f;}return t/a;}
// procedural tiled fbm noise, useable by texture functions
#define FBM_TILED(l,c,q) float l(c v,c s,int n,float f, float w){v=mod(v,s);float t=0,a=0,b=1;for(int i=0;i<n;++i){t+=q(v,s).x*b;a+=b;b*=w;s*=f;}return t/a;}
FBM(billows,vec2,worley)
FBM(billows,vec3,worley)
FBM_TILED(billows,vec2,worley)
float billows(vec2 v,float s,int n,float f, float w){return billows(v,vec2(s),n,f,w);}
FBM_TILED(billows,vec3,worley)
float billows(vec3 v,float s,int n,float f, float w){return billows(v,vec3(s),n,f,w);}

#undef FBM
#undef FBM_TILED

vec4 voronoiFast(vec2 x)
{
    vec2 n = floor(x);
    vec2 f = fract(x);

	vec2 mr, s;

    float md1 = 8.0;
    for( int j=-1; j<=1; j++ )
    for( int i=-1; i<=1; i++ )
    {
        vec2 g = vec2(float(i),float(j));
		vec2 o = h2(n + g);
        vec2 r = g + o - f;
        float d = dot(r,r);

        if( d<md1 )
        {
            md1 = d;
            mr = r;
            s = g + n;
        }
    }

    float md = 8.0;
    for( int j=-1; j<=1; j++ )
    for( int i=-1; i<=1; i++ )
    {
        vec2 g = vec2(float(i),float(j));
        vec2 o = h2( n + g );
        vec2 r = g + o - f;
        vec2 _ = abs(mr-r);
        if(dot(mr-r,mr-r) > EPSILON)
            md = min( md, dot( 0.5*(mr+r), normalize(r-mr) ) );
    }

    // md1 is worley
    return vec4(md, s, mr);
}

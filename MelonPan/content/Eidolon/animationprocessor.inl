__forceinline static float Dot(const __m128& a, const __m128& b)
{
    __m128 c = _mm_mul_ps(a, b);
    return c.m128_f32[3] + c.m128_f32[2] + c.m128_f32[1];
}

__forceinline static float Magnitude(const __m128& a)
{
    return sqrtf(Dot(a,a));
}

struct ImplicitToExplicit
{
protected:
    // state
    __m128 pos;
    __m128 velocity;

public:
    // settings
    float radius;
    float stiffness;
    float damping;
    float leaning;

    // accessible data
    float rotate[3];

    ImplicitToExplicit() :
        pos(_mm_setzero_ps()),
        velocity(_mm_setzero_ps())
    {
        rotate[0] = 0.0f;
    }

    float ioTarget[3];

    void Update(float deltaTime, const float*const inFutureTarget)
    {
        if(deltaTime == 0)
            return;

        __m128 target = _mm_set_ps(ioTarget[0], ioTarget[1], ioTarget[2], 0);

        // teleport on large jumps
        __m128 diff = _mm_sub_ps(target, pos);
        if(Dot(diff, diff) > 25.0f)
        {
            __m128 future = _mm_set_ps(inFutureTarget[0], inFutureTarget[1], inFutureTarget[2], 0);
            __m128 deltaToFuture = _mm_sub_ps(future, target);
            velocity = _mm_div_ps(deltaToFuture, _mm_set_ps1(0.01f));
            pos = _mm_sub_ps(target, _mm_mul_ps(velocity, _mm_set_ps1(damping / stiffness)));
            diff = _mm_setzero_ps();
        }

        __m128 prevVelocity = velocity;

        // friction
        velocity = _mm_sub_ps(velocity, _mm_mul_ps(velocity, _mm_set_ps1(damping * deltaTime)));

        // spring force
        velocity = _mm_add_ps(velocity, _mm_mul_ps(diff, _mm_set_ps1(stiffness * deltaTime)));

        // integrate position 
        pos = _mm_add_ps(pos, _mm_mul_ps(velocity, _mm_set_ps1(deltaTime)));

        // calculate/integrate rotation
        float m = Magnitude(velocity);
        float ax = m / radius * deltaTime;
        rotate[1] =  atan2f(velocity.m128_f32[3], velocity.m128_f32[1]);
        rotate[2] = 0.0f;
        float m1 = Magnitude(prevVelocity);

        if(m1 != 0.0f && m != 0.0f)
        {
            // sign of (velocity X prevVelocity).Y
            float sgn = (prevVelocity.m128_f32[1] * velocity.m128_f32[3] - prevVelocity.m128_f32[3] * velocity.m128_f32[1]) < 0.0f ? -1.0f : 1.0f;
            float dt = Dot(_mm_div_ps(prevVelocity, _mm_set_ps1(m1)), _mm_div_ps(velocity, _mm_set_ps1(m)));
            // argument range check for acosf (which the function normally provides, but this is the intro asm one)
            if (dt > 1.0) dt = 1.0;
            if (dt < -1.0) dt = -1.0;
            rotate[2] = acosf(dt) * sgn * m * leaning / deltaTime * 0.001f;
        }

        rotate[0] += ax;

        ioTarget[0] = pos.m128_f32[3];
        ioTarget[1] = pos.m128_f32[2];
        ioTarget[2] = pos.m128_f32[1];
    }
};

static ImplicitToExplicit physics[4];
float cache[3];
float future[3];

inline void animationprocessor_init() {
    // initialize physics objects
    physics[0].radius = 0.25f;
    physics[0].stiffness = 3.5f;
    physics[0].damping = 2.0f;
    physics[0].leaning = 320.0f;
    physics[1].radius = 1.0f;
    physics[1].stiffness = 1.5f;
    physics[1].damping = 2.0f;
    physics[1].leaning = 400.0f;
    physics[2].radius = 1.0f;
    physics[2].stiffness = 2.5f;
    physics[2].damping = 1.0f;
    physics[2].leaning = 400.0f;
    physics[3].radius = 1.0f;
    physics[3].stiffness = 1.5f;
    physics[3].damping = 1.0f;
    physics[3].leaning = 400.0f;
}

inline void animationprocessor_curveEvaluated(float localBeats, float value, const Curve& curve, const char* curveName, unsigned char j, float deltaSeconds) {
    if (lstrcmpiA(curveName, "uMainCharacterPos") == 0) {
        physics[0].ioTarget[j] = value;
        future[j] = curve.evaluate(localBeats + 0.01f);
        if(j == 2) physics[0].Update(deltaSeconds, future);
    } else if (lstrcmpiA(curveName,  "uEvilCharacterPos1") == 0) {
        physics[1].ioTarget[j] = value;
        future[j] = curve.evaluate(localBeats + 0.01f);
        if(j == 2) physics[1].Update(deltaSeconds, future);
    } else if (lstrcmpiA(curveName,  "uEvilCharacterPos2") == 0) {
        physics[2].ioTarget[j] = value;
        future[j] = curve.evaluate(localBeats + 0.01f);
        if(j == 2) physics[2].Update(deltaSeconds, future);
    } else if (lstrcmpiA(curveName,  "uEvilCharacterPos3") == 0) {
        physics[3].ioTarget[j] = value;
        future[j] = curve.evaluate(localBeats + 0.01f);
        if(j == 2) physics[3].Update(deltaSeconds, future);
    }
}

inline const void animationprocessor_finalize(GLuint program) {
    glUniform3fv(glGetUniformLocation(program, "uMainCharacterPos"), 1, physics[0].ioTarget);
    glUniform3fv(glGetUniformLocation(program, "uMainCharacterRotation"), 1, physics[0].rotate);

    glUniform3fv(glGetUniformLocation(program, "uEvilCharacterPos1"), 1, physics[1].ioTarget);
    glUniform3fv(glGetUniformLocation(program, "uEvilCharacterRotation1"), 1, physics[1].rotate);

    glUniform3fv(glGetUniformLocation(program, "uEvilCharacterPos2"), 1, physics[2].ioTarget);
    glUniform3fv(glGetUniformLocation(program, "uEvilCharacterRotation2"), 1, physics[2].rotate);

    glUniform3fv(glGetUniformLocation(program, "uEvilCharacterPos3"), 1, physics[3].ioTarget);
    glUniform3fv(glGetUniformLocation(program, "uEvilCharacterRotation3"), 1, physics[3].rotate);
}

// This allows the user to pass in different locals. Though the contextual code may change over time it should hopefully only introduce new locals that may or may not be used here.
#define animationprocessor__doCallback() animationprocessor_curveEvaluated(localBeats, value, curve, currentShot->uniformName(i), element, deltaSeconds)
#define animationprocessor__doFinalize() animationprocessor_finalize(program)

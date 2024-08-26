__declspec(align(16))
struct Mat44 {
    union {
        __m128 rows[4];
        struct {
            __m128 row0;
            __m128 row1;
            __m128 row2;
            __m128 row3;
        };
        float elems[16];
    } data;

    Mat44& operator*=(const Mat44& other) {
        __m128 x = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(0, 0, 0, 0));
        __m128 y = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(1, 1, 1, 1));
        __m128 z = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(2, 2, 2, 2));
        __m128 w = _mm_shuffle_ps(data.row0, data.row0, _MM_SHUFFLE(3, 3, 3, 3));
        data.row0 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
            _mm_mul_ps(y, other.data.row1)),
            _mm_add_ps(_mm_mul_ps(z, other.data.row2),
                _mm_mul_ps(w, other.data.row3)));

        x = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(0, 0, 0, 0));
        y = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(1, 1, 1, 1));
        z = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(2, 2, 2, 2));
        w = _mm_shuffle_ps(data.row1, data.row1, _MM_SHUFFLE(3, 3, 3, 3));
        data.row1 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
            _mm_mul_ps(y, other.data.row1)),
            _mm_add_ps(_mm_mul_ps(z, other.data.row2),
                _mm_mul_ps(w, other.data.row3)));

        x = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(0, 0, 0, 0));
        y = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(1, 1, 1, 1));
        z = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(2, 2, 2, 2));
        w = _mm_shuffle_ps(data.row2, data.row2, _MM_SHUFFLE(3, 3, 3, 3));
        data.row2 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
            _mm_mul_ps(y, other.data.row1)),
            _mm_add_ps(_mm_mul_ps(z, other.data.row2),
                _mm_mul_ps(w, other.data.row3)));

        x = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(0, 0, 0, 0));
        y = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(1, 1, 1, 1));
        z = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(2, 2, 2, 2));
        w = _mm_shuffle_ps(data.row3, data.row3, _MM_SHUFFLE(3, 3, 3, 3));
        data.row3 = _mm_add_ps(_mm_add_ps(_mm_mul_ps(x, other.data.row0),
            _mm_mul_ps(y, other.data.row1)),
            _mm_add_ps(_mm_mul_ps(z, other.data.row2),
                _mm_mul_ps(w, other.data.row3)));

        return *this;
    }

    inline static Mat44 RotateX(float radians) {
        float sa = sinf(radians);
        float ca = cosf(radians);
        return { 1,0,0,0,
            0,ca,sa,0,
            0,-sa,ca,0,
            0,0,0,1 };
    }

    inline static Mat44 RotateY(float radians) {
        float sa = sinf(radians);
        float ca = cosf(radians);
        return { ca,0,-sa,0,
            0,1,0,0,
            sa,0,ca,0,
            0,0,0,1 };
    }

    inline static Mat44 RotateZ(float radians) {
        float sa = sinf(radians);
        float ca = cosf(radians);
        return { ca,sa,0,0,
            -sa,ca,0,0,
            0,0,1,0,
            0,0,0,1 };
    }
};

float uAngles[3];
float uV[16];
float uFrustum[16];

// Public API, must be implemented
inline void animationprocessor_init() {
}

inline void animationprocessor_curveEvaluated(const char* curveName, unsigned char curveElementIndex, float evaluatedValue, float width, float height) {
    if (lstrcmpiA(curveName, "uOrigin") == 0)
        uV[12 + curveElementIndex] = evaluatedValue;

    if (lstrcmpiA(curveName, "uAngles") == 0)
        uAngles[curveElementIndex] = evaluatedValue;

    if(lstrcmpiA(curveName, "uFovBias") == 0) {
        float tfov = tanf(evaluatedValue);
        float xfov = tfov * ((float)width / (float)height);
        uFrustum[0] = -xfov; uFrustum[1] = -tfov; uFrustum[2] = 1.0f;
        uFrustum[4] = xfov; uFrustum[5] = -tfov; uFrustum[6] = 1.0f;
        uFrustum[8] = -xfov; uFrustum[9] = tfov; uFrustum[10] = 1.0f;
        uFrustum[12] = xfov; uFrustum[13] = tfov; uFrustum[14] = 1.0f;
    }
}

inline void animationprocessor_finalize(unsigned int program) {
    Mat44 orient = Mat44::RotateY(-uAngles[1]);
    orient *= Mat44::RotateX(uAngles[0]);
    orient *= Mat44::RotateZ(uAngles[2]);

    uV[0] = orient.data.elems[0];
    uV[1] = orient.data.elems[1];
    uV[2] = orient.data.elems[2];

    uV[4] = orient.data.elems[4];
    uV[5] = orient.data.elems[5];
    uV[6] = orient.data.elems[6];

    uV[8] = orient.data.elems[8];
    uV[9] = orient.data.elems[9];
    uV[10] = orient.data.elems[10];

    uV[15] = 1.0f;

    glUniformMatrix4fv(glGetUniformLocation(program, "uV"), 1, false, uV);

    glUniformMatrix4fv(glGetUniformLocation(program, "uFrustum"), 1, false, uFrustum);
}

// This allows the user to pass in different locals. Though the contextual code may change over time it should hopefully only introduce new locals that may or may not be used here.
#define animationprocessor__doCallback() animationprocessor_curveEvaluated(currentShot->uniformName(i), element, value, screenWidth, screenHeight)
#define animationprocessor__doFinalize() animationprocessor_finalize(program)

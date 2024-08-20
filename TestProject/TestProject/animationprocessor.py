import cgmath

r = cgmath.Mat44.rotateY(-cameraData.rotate[1]) * cgmath.Mat44.rotateX(cameraData.rotate[0]) * cgmath.Mat44.rotateZ(cameraData.rotate[2])
uniforms['uV'] = r[:]
uniforms['uV'][12:15] = cameraData.translate

from math import tan
tfov = tan(uniforms.get('uFovBias', 0.5))
buf = scene.frameBuffers[scene.passes[-1].targetBufferId]
bufferWidth = buf.width()
bufferHeight = buf.height()
ar = bufferWidth / float(bufferHeight)
xfov = (tfov * ar)
uniforms['uFrustum'] = (-xfov, -tfov, 1.0, 0.0,
                        xfov, -tfov, 1.0, 0.0,
                        -xfov, tfov, 1.0, 0.0,
                        xfov, tfov, 1.0, 0.0)

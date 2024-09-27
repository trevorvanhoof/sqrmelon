"""
TODO: thinking out loud about scenes here
A scene should point to a template index
A template's draw consumes program indices stored in the template
A scene should thus also store its local program indices
and WHEN to use them. I think it is easiest to have a list
of draw command indices where this is needed?
Alternatively we can store bools for each draw command found in the template
"""
import struct
from dataclasses import dataclass
from typing import Iterable

from OpenGL.GL import GL_FRAGMENT_SHADER, GL_COMPUTE_SHADER, GL_VERTEX_SHADER, GL_GEOMETRY_SHADER

from flex_project.utils import tt_json5
from flex_project.export.binary_pool import BinaryPool, serializeArray
from flex_project.structure import DrawRect, Project, Template, Command, DrawMesh, DispatchCompute


@dataclass
class Demo:
    project: Project
    templates: tuple[Template, ...]

    def serialize(self, target: BinaryPool) -> bytes:
        args = self.project.commandSerializationArgs()
        return self.project.serialize(target, *args) + serializeArray(self.templates, target, *args)


def addShaders(commands: Iterable[Command], target: BinaryPool) -> None:
    for command in commands:
        if isinstance(command, DrawRect):
            assert command.fragment
            target.addShader(command.fragment, GL_FRAGMENT_SHADER)
        if isinstance(command, DispatchCompute):
            assert command.compute
            target.addShader(command.compute, GL_COMPUTE_SHADER)
        if isinstance(command, DrawMesh):
            if command.fragment: target.addShader(command.fragment, GL_FRAGMENT_SHADER)
            if command.vertex: target.addShader(command.vertex, GL_VERTEX_SHADER)
            if command.geometry: target.addShader(command.geometry, GL_GEOMETRY_SHADER)


def main():
    with open('project.json5', 'rb') as fh:
        project = Project(**tt_json5.parse(tt_json5.SStream(fh.read())))

    with open('template.json5', 'rb') as fh:
        template = Template(**tt_json5.parse(tt_json5.SStream(fh.read())))

    target = BinaryPool()

    demo = Demo(project, (template,))

    addShaders(project.staticDraw, target)
    for template in demo.templates:
        addShaders(template.draw, target)
    target.buildShaderIndices()

    demoContent = demo.serialize(target)
    demoInts = struct.unpack('IIIIIIIIII', demoContent)
    demoStr = 'constexpr const Demo demo { { { %d, %d }, { %d, %d }, { %d, %d }, { %d, %d } }, { %d, %d } };' % demoInts

    numAttachments = max(framebuffer.outputs for framebuffer in project.framebuffers.values())
    attachments = ', '.join(f'GL_COLOR_ATTACHMENT0 + {i}' for i in range(numAttachments))
    attachmentsStr = f'GLenum attachments[{numAttachments}] {{ {attachments} }};'

    numCbosStr = f'constexpr const unsigned char numCbos = {len(project.commandSerializationArgs()[3])};'

    with open('content.h', 'w') as fh:
        fh.write('namespace content {\n')
        fh.write('  constexpr const unsigned char data[] = {')
        fh.write(', '.join(str(int(number)) for number in target.data()))
        fh.write('};\n')
        fh.write('  constexpr const unsigned int shaderData[] = {')
        fh.write(', '.join(str(number) for number in target.shaderData()))
        fh.write('};\n')
        fh.write(f'  constexpr const unsigned short numPrograms = {target.numPrograms()};\n')
        fh.write('  constexpr const unsigned char programData[] = {')
        fh.write(', '.join(str(number) for number in target.programData()))
        fh.write('};\n')
        fh.write(f'  {demoStr}\n')
        fh.write(f'  {attachmentsStr}\n')
        fh.write(f'  {numCbosStr}\n')
        fh.write(f'  constexpr const int maxStitches = {target.maxStitches};\n')
        fh.write('};\n')


if __name__ == '__main__':
    main()

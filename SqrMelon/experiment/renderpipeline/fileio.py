import json
import uuid

from experiment.serializable import serializeObjects, deserializeObjects
from model import Node, Plug, OutputPlug, Stitch, EStitchScope


def deserializeGraph(fileHandle):
    data = json.load(fileHandle)
    return [node for node in deserializeObjects(data) if isinstance(node, Node)]

    graph = []
    uuidMap = {}

    for nodeData in data['graph']:
        node = Node(nodeData['name'], nodeData['x'], nodeData['y'])
        uuidMap[nodeData['uuid']] = node
        graph.append(node)
        for plugData in nodeData['inputs']:
            plug = Plug(plugData['name'], graph[-1])
            uuidMap[plugData['uuid']] = plug
            node.inputs.append(plug)
        for plugData in nodeData['outputs']:
            plug = OutputPlug(plugData['name'], graph[-1], plugData.get('size', -1))
            uuidMap[plugData['uuid']] = plug
            node.outputs.append(plug)
        for stitchData in nodeData['stitches']:
            stitch = Stitch(stitchData['name'], EStitchScope(stitchData['scope']))
            node.stitches.append(stitch)
        node.layout()

    for nodeData in data['graph']:
        for plugData in nodeData['inputs']:
            plug = uuidMap[plugData['uuid']]
            for uuid in plugData['connections']:
                plug.connections.append(uuidMap[uuid])
        for plugData in nodeData['outputs']:
            plug = uuidMap[plugData['uuid']]
            for uuid in plugData['connections']:
                plug.connections.append(uuidMap[uuid])

    return graph


def serializeGraph(graph, fileHandle):
    data = serializeObjects(graph)
    json.dump(data, fileHandle, indent=4, sort_keys=True)
    return

    data = {'graph': []}
    uuidCache = {}
    for node in graph:
        nodeData = {
            'uuid': str(uuidCache.setdefault(node, uuid.uuid4())),
            'name': node.name,
            'x': node.x,
            'y': node.y,
            'inputs': [],
            'outputs': [],
            'stitches': []
        }
        for input in node.inputs:
            inputData = {
                'uuid': str(uuidCache.setdefault(input, uuid.uuid4())),
                'name': input.name,
                'connections': [str(uuidCache.setdefault(connection, uuid.uuid4())) for connection in input.connections]
            }
            nodeData['inputs'].append(inputData)
        for output in node.outputs:
            outputData = {
                'uuid': str(uuidCache.setdefault(output, uuid.uuid4())),
                'name': output.name,
                'size': output.size,
                'connections': [str(uuidCache.setdefault(connection, uuid.uuid4())) for connection in output.connections]
            }
            nodeData['outputs'].append(outputData)
        for stitch in node.stitches:
            stitchData = {
                'name': stitch.name,
                'scope': str(stitch.scope)
            }
            nodeData['stitches'].append(stitchData)
        data['graph'].append(nodeData)
    json.dump(data, fileHandle)

from experiment.model import Clip, Event, Shot
from experiment.curvemodel import HermiteCurve, HermiteKey


def serializeCurve(curve):
    return {'name': curve[0],
            'loopMode': curve[1],
            'keys': [{'x': key.x, 'y': key.y, 'inTangentY': key.inTangentY, 'outTangentY': key.outTangentY} for key in curve.keys]}


def serializeClip(clip):
    curves = []
    curvesModel = clip.curves
    for row in xrange(curvesModel.rowCount()):
        pyObj = curvesModel.item(row, 0).data()
        assert isinstance(pyObj, HermiteCurve)
        curves.append(serializeCurve(pyObj))
    return {'name': clip[0],
            'loopMode': clip[1],
            'curves': curves,
            'textures': {uniformName: filePath for uniformName, filePath in clip.textures.iteritems()}}


def serializeShot(shot):
    return {'name': shot[0],
            'sceneName': shot[1],
            'start': shot[2],
            'end': shot[3],
            'track': shot[4]}


def serializeEvent(event):
    return {'name': event[0],
            'clipName': event[1][0],
            'start': event[2],
            'end': event[3],
            'speed': event[3],
            'roll': event[3],
            'track': event[4]}


def serialize(clipModel, shotModel, eventModel):
    clips = []
    shots = []
    events = []
    for row in xrange(clipModel.rowCount()):
        pyObj = clipModel.item(row, 0).data()
        assert isinstance(pyObj, Clip)
        clips.append(serializeClip(pyObj))

    for row in xrange(shotModel.rowCount()):
        pyObj = shotModel.item(row, 0).data()
        assert isinstance(pyObj, Shot)
        shots.append(serializeShot(pyObj))

    for row in xrange(eventModel.rowCount()):
        pyObj = eventModel.item(row, 0).data()
        assert isinstance(pyObj, Event)
        events.append(serializeEvent(pyObj))
    return {'clips': clips, 'shots': shots, 'events': events}


def deserialize(data, clipModel, shotModel, eventModel):
    eventModel.clear()
    shotModel.clear()
    clipModel.clear()

    clips = {}
    for clip in data['clips']:
        clip = Clip(clip['name'], clip['loopMode'])
        for curve in clip['curves']:
            keys = [HermiteKey(key['x'], key['y'], key['inTangentY'], key['outTangentY']) for key in curve['keys']]
            clip.curves.appendRow(HermiteCurve(curve['name'], curve['loopMode'], keys).items)
        clip.textures.updatex(clip['textures'])
        clipModel.appendRow(clip.items)
        clips[clip['name']] = clip

    for shot in data['shots']:
        shotModel.appendRow(Shot(shot['name'], shot['sceneName'], float(shot['start']), float(shot['end'])).items)

    for event in data['event']:
        eventModel.appendRow(Event(event['name'], clips[event['clip']], event['start'], event['end'], event['speed'], event['roll'], event['track']).items)

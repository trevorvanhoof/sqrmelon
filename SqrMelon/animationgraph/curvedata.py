from __future__ import annotations

from functools import lru_cache
from typing import Iterator, NamedTuple, Optional, List, Union

from mathutil import Vec2


class Key:
    """A single key in a curve.

    Currently tangent X values, tangentBorken and the TANGENT_USER mode are unused.
    """
    # TODO: Use enums
    TYPE_MANUAL, TYPE_LINEAR, TYPE_FLAT = range(3)
    TANGENT_AUTO, TANGENT_SPLINE, TANGENT_LINEAR, TANGENT_FLAT, TANGENT_STEPPED, TANGENT_USER = range(6)

    def __init__(self, time: float, value: float, parent: Curve) -> None:
        self.__point = Vec2(time, value)
        self.__parent = parent
        # note that tangent X values have been deprecated and is not exported;
        #   they were for cubic bezier curves that never got made
        self.__inTangent = Vec2(0.0, 0.0)
        self.__outTangent = Vec2(0.0, 0.0)
        self.__inTangentType = Key.TYPE_LINEAR
        self.__outTangentType = Key.TYPE_LINEAR
        self.__tangentBroken = False
        self.__tangentMode = Key.TANGENT_AUTO

    def clone(self, parent: Curve) -> Key:
        key = self.__class__(self.time(), self.value(), parent)
        key.__inTangent = Vec2(self.__inTangent)
        key.__outTangent = Vec2(self.__outTangent)
        key.__tangentBroken = self.tangentBroken
        key.__tangentMode = self.tangentMode
        return key

    @property
    def tangentBroken(self) -> bool:
        return self.__tangentBroken

    @tangentBroken.setter
    def tangentBroken(self, tangentBroken: bool) -> None:
        self.__tangentBroken = tangentBroken
        self.updateTangents()

    @property
    def tangentMode(self) -> int:
        return self.__tangentMode

    @tangentMode.setter
    def tangentMode(self, tangentMode: int) -> None:
        self.__tangentMode = tangentMode
        self.updateTangents()

    def setTangentModeSilent(self, tangentMode: int) -> None:
        self.__tangentMode = tangentMode

    def inTangent(self) -> Vec2:
        return Vec2(self.__inTangent)

    def setInTangent(self, value: Vec2) -> None:
        self.__inTangent = Vec2(value)

    def outTangent(self) -> Vec2:
        return Vec2(self.__outTangent)

    def setOutTangent(self, value: Vec2) -> None:
        self.__outTangent = Vec2(value)

    def updateTangents(self) -> None:
        if self.__tangentMode == Key.TANGENT_USER:
            return
        if self.__tangentMode == Key.TANGENT_STEPPED:
            # this leaves the input tangent as is, so you can go set e.g.
            #   "linear" to get the input, then back to "stepped"
            # TODO: have "output is stepped" as separate state ("in tangent" with "stepped output" control is tedious)
            self.setOutTangent(Vec2(0.0, float('inf')))
            return
        if self.__tangentMode == Key.TANGENT_FLAT:
            self.setInTangent(Vec2(0.0, 0.0))
            self.setOutTangent(Vec2(0.0, 0.0))
        else:
            self.__parent.updateTangents(self, self.__tangentMode)

    def time(self) -> float:
        return self.__point.x

    def setTime(self, time: float) -> None:
        self.__point.x = time
        self.__parent.sortKeys()

    def value(self) -> float:
        return self.__point.y

    def setValue(self, value: float) -> None:
        self.__point.y = value
        self.__parent.keyChanged(self)

    def point(self) -> Vec2:
        """Retruns by copy."""
        return Vec2(self.__point)

    def setPoint(self, point: Vec2) -> None:
        self.__point = Vec2(point)
        self.__parent.sortKeys()
        self.__parent.keyChanged(self)

    def delete(self) -> None:
        self.__parent.deleteKey(self)

    def reInsert(self) -> None:
        self.__parent.reInsert(self)

    def parentCurve(self) -> Curve:
        return self.__parent


class Curve:
    """Animation data with Cubic Hermite Spline interpolation."""

    def __init__(self) -> None:
        self.__keys: list[Key] = []
        # TODO: Why sort empty list?
        self.sortKeys()

    def clone(self) -> Curve:
        curve = Curve()
        for key in self.__keys:
            k = key.clone(curve)
            curve.__keys.append(k)
        curve.sortKeys()
        return curve

    def keyAt(self, time: float) -> Optional[Key]:
        for key in self.__keys:
            if key.time() == time:
                return key
        return None

    def deleteKey(self, key: Key) -> None:
        idx = self.__keys.index(key)
        self.__keys.pop(idx)
        if idx != 1 and len(self.__keys):
            self.__keys[idx - 1].updateTangents()
        if idx != len(self.__keys):
            self.__keys[idx].updateTangents()

    def addKeyWithTangents(self,
                           inTangentX: float, inTangentY: float,
                           time: float, value: float,
                           outTangentX: float, outTangentY: float,
                           tangentBroken: bool, tangentMode: int) -> Key:
        key = Key(time, value, self)
        self.__keys.append(key)
        self.sortKeys()
        key.setInTangent(Vec2(inTangentX, inTangentY))
        key.setOutTangent(Vec2(outTangentX, outTangentY))
        key.tangentBroken = tangentBroken
        key.tangentMode = tangentMode
        return key

    def reInsert(self, key: Key) -> None:
        self.__keys.append(key)
        self.sortKeys()

    def keyChanged(self, key: Key) -> None:
        idx = self.__keys.index(key)
        first = idx == 0
        last = idx == len(self.__keys) - 1

        if not first:
            self.__keys[idx - 1].updateTangents()
        key.updateTangents()
        if not last:
            self.__keys[idx + 1].updateTangents()

    def updateTangents(self, key: Key, mode: int) -> None:
        idx = self.__keys.index(key)
        first = idx == 0
        last = idx == len(self.__keys) - 1

        if first and last:
            return

        def keyDirection(a: Key, b: Key) -> Vec2:
            keyDifference = b.point() - a.point()
            try:
                keyDifference.normalize()
            except ZeroDivisionError:
                return Vec2(0.0, 0.0)
            keyDifference.x = abs(keyDifference.x)
            return keyDifference

        def finalize() -> None:
            if not first and key.inTangent().length() != 0:
                pd = self.__keys[idx].time() - self.__keys[idx - 1].time()
                try:
                    key.setInTangent(key.inTangent() * pd / key.inTangent().x)
                except ZeroDivisionError:
                    pass
            if not last and key.outTangent().length() != 0:
                nd = self.__keys[idx + 1].time() - self.__keys[idx].time()
                try:
                    key.setOutTangent(key.outTangent() * nd / key.outTangent().x)
                except ZeroDivisionError:
                    pass

        if mode == Key.TANGENT_LINEAR:
            if first:
                key.setInTangent(Vec2(0.0, 0.0))
            else:
                t = keyDirection(self.__keys[idx], self.__keys[idx - 1])
                t.x = -t.x
                key.setInTangent(t)

            if last:
                key.setOutTangent(Vec2(0.0, 0.0))
            else:
                key.setOutTangent(keyDirection(self.__keys[idx], self.__keys[idx + 1]))

            finalize()
            return

        elif mode == Key.TANGENT_SPLINE:
            if first:
                key.setOutTangent(keyDirection(self.__keys[idx], self.__keys[idx + 1]))
                key.setInTangent(-key.outTangent())  # TODO: I flipped the sign, check if that was the right thing to do
            elif last:
                t = keyDirection(self.__keys[idx], self.__keys[idx - 1])
                t.x = -t.x
                key.setInTangent(t)
                key.setOutTangent(-key.inTangent())
            else:
                key.setOutTangent(keyDirection(self.__keys[idx - 1], self.__keys[idx + 1]))
                key.setInTangent(-key.outTangent())

            finalize()
            return

        elif mode == Key.TANGENT_AUTO:
            def sgn(x: float) -> float:
                return -1.0 if x < 1.0 else 1.0 if x > 1.0 else 0.0

            if first or last or sgn(self.__keys[idx - 1].value() - key.value()) == sgn(
                    self.__keys[idx + 1].value() - key.value()):
                key.setInTangent(Vec2(0.0, 0.0))
                key.setOutTangent(Vec2(0.0, 0.0))
            else:
                key.setOutTangent(keyDirection(self.__keys[idx - 1], self.__keys[idx + 1]))
                key.setInTangent(-key.outTangent())

            finalize()
            return

        elif mode in (Key.TANGENT_USER, Key.TANGENT_STEPPED):
            return

        assert False, 'Invalid tangent mode for key.'

    def sortKeys(self) -> None:
        # TODO: optimize in any way?
        self.__keys.sort(key=lambda k: k.time())
        for key in self.__keys:
            key.updateTangents()

    def __iter__(self) -> Iterator[Key]:
        for key in self.__keys:
            yield key

    def __getitem__(self, index: int) -> Key:
        return self.__keys[index]

    def __setitem__(self, index: int, key: Key) -> None:
        self.__keys[index] = key

    def __len__(self) -> int:
        return len(self.__keys)

    def scale(self, speed: float) -> None:
        """Speed up the animation by the given multiplier."""
        # reverse to avoid auto-sorting messing up anything
        for key in reversed(self.__keys):
            key.setTime(key.time() / speed)

    def move(self, deltaTime: float) -> None:
        """Move the animation by the given addition."""
        # shifting to the right, reverse application order to avoid auto-sorting messing up anything
        if deltaTime > 0.0:
            for key in reversed(self.__keys):
                key.setTime(key.time() + deltaTime)
        else:
            for key in self.__keys:
                key.setTime(key.time() + deltaTime)

    def trim(self, start: float, end: float) -> None:
        """Delete keys outside of the given time range."""
        assert start <= end
        startIdx = -1
        endIdx = len(self.__keys)
        for i, key in enumerate(self.__keys):
            if startIdx < 0 and key.time() > start:
                startIdx = i - 1
            if key.time() >= end:
                endIdx = i + 1
                break
        self.__keys = self.__keys[max(startIdx, 0):min(endIdx, len(self.__keys))]

    @staticmethod
    @lru_cache
    def _evaluate(lhs_time: float, lhs_value: float, lhs_tangent: float, rhs_tangent: float, rhs_time: float, rhs_value: float, time: float) -> float:
        # stepped tangents
        if lhs_tangent == float('inf'):
            return lhs_value
        dx = rhs_time - lhs_time
        dy = rhs_value - lhs_value
        c0 = (lhs_tangent + rhs_tangent - dy - dy)
        c1 = (dy + dy + dy - lhs_tangent - lhs_tangent - rhs_tangent)
        c2 = lhs_tangent
        c3 = lhs_value
        t = (time - lhs_time) / dx
        return t * (t * (t * c0 + c1) + c2) + c3

    # Define a type that encapsulates the curve evaluation result
    class Evaluation(NamedTuple):
        y: float
        prevKeyIndex: int
        keyIndex: int

    def evaluate(self, time: float, precision: float = 0.0) -> Evaluation:
        """
        Hermite spline interpolation at the given time.
        Times outside the bounds are just clamped to the endpoints.
        """
        if not self.__keys:
            return Curve.Evaluation(0.0, -1, -1)

        if time <= self.__keys[0].time():
            return Curve.Evaluation(self.__keys[0].value(), 0, 0)

        for i in range(1, len(self.__keys)):
            key = self.__keys[i]
            p3 = key.point()
            # points are sorted so the first one that is > time is the one that defines the segment to evaluate
            if p3.x <= time:
                continue
            # snap to key values if the time is close to it (for rendering)
            if abs(p3.x - time) < precision:
                return Curve.Evaluation(p3.y, i - 1 if time < p3.x else i, i)
            prevKey = self.__keys[i - 1]
            p0 = prevKey.point()
            y = self._evaluate(p0.x, p0.y, prevKey.outTangent().y, key.inTangent().y, p3.x, p3.y, time)
            return Curve.Evaluation(y, i - 1, i)

        last = len(self.__keys) - 1
        return Curve.Evaluation(self.__keys[last].value(), last, last)

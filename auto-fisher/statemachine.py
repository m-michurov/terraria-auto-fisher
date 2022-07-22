import time
from typing import Any, Callable


def _distance(p1: tuple[int, int], p2: tuple[int, int]) -> float:
    x1, y1 = p1
    x2, y2 = p2
    return abs(x1 - x2) + abs(y1 - y2)


class _State:

    @property
    def description(self) -> str:
        raise NotImplemented()

    @property
    def next(self) -> Any:
        raise NotImplemented()

    def act(self, motion: bool) -> None:
        raise NotImplemented()


class _StateFactory:
    def __init__(
            self,
            cast_fn: Callable[[], None],
            reel_in_fn: Callable[[], None]
    ) -> None:
        self._cast_fn = cast_fn
        self._reel_in_fn = reel_in_fn

    def waiting_before_cast(self) -> _State:
        return _WaitingBeforeCast(self, self._cast_fn)

    def casting(self) -> _State:
        return _Casting(self)

    def catching(self) -> _State:
        return _Catching(self, self._reel_in_fn)


class _WaitingBeforeCast(_State):
    CAST_DELAY = 0.25

    def __init__(
            self,
            state_factory: _StateFactory,
            cast_fn: Callable[[], None]
    ) -> None:
        self._state_factory: _StateFactory = state_factory
        self._cast_fn: Callable[[], None] = cast_fn

        self._wait_start_time: float = time.time()
        self._casted: bool = False

    @property
    def description(self) -> str:
        return 'Waiting'

    @property
    def next(self) -> _State:
        if self._casted:
            return self._state_factory.casting()

        return self

    def act(self, _: bool) -> None:
        elapsed = time.time() - self._wait_start_time
        if elapsed < _WaitingBeforeCast.CAST_DELAY:
            return

        self._cast_fn()
        self._casted = True


class _Casting(_State):
    CAST_DURATION = 1.0

    def __init__(
            self,
            state_factory: _StateFactory,
    ) -> None:
        self._state_factory: _StateFactory = state_factory
        self._wait_start_time: float = time.time()

    @property
    def description(self) -> str:
        return 'Casting'

    @property
    def next(self) -> _State:
        elapsed = time.time() - self._wait_start_time

        if elapsed < _Casting.CAST_DURATION:
            return self

        return self._state_factory.catching()

    def act(self, _: bool) -> None:
        pass


class _Catching(_State):
    MAX_WAIT_TIME = 10

    def __init__(
            self,
            state_factory: _StateFactory,
            reel_in_fn: Callable[[], None]
    ) -> None:
        self._state_factory: _StateFactory = state_factory
        self._reel_in_fn: Callable[[], None] = reel_in_fn

        self._cumulative_difference: float = 0.0
        self._caught: bool = False

        self._start: float = time.time()

    @property
    def description(self) -> str:
        if self._cumulative_difference > 0:
            return 'Caught something'

        elapsed = time.time() - self._start
        if elapsed > self.MAX_WAIT_TIME:
            return 'Wait time exceeded'

        return 'Waiting for something to catch'

    @property
    def next(self) -> _State:
        elapsed = time.time() - self._start

        if self._caught or elapsed > self.MAX_WAIT_TIME:
            return self._state_factory.waiting_before_cast()

        return self

    def act(self, motion: bool) -> None:
        elapsed = time.time() - self._start
        if elapsed > self.MAX_WAIT_TIME:
            self._reel_in_fn()

        if not motion:
            return

        self._reel_in_fn()
        self._caught = True


class FishingStateMachine:
    def __init__(
            self,
            cast: Callable[[], None],
            reel_in: Callable[[], None]
    ) -> None:
        self._args = (cast, reel_in)

        self._state: _State = _StateFactory(cast, reel_in).waiting_before_cast()

    def update(self, motion: bool) -> None:
        self._state.act(motion)
        self._state = self._state.next

    @property
    def state_description(self) -> str:
        """
        Human-readable description of current state.
        """
        return self._state.description

    def reset(self) -> None:
        self.__init__(*self._args)

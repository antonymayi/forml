"""
Flow segments represent partial pipeline blocks during pipeline assembly.
"""

import abc
import collections
import typing
import weakref

from forml.flow.graph import node, view


class Track(collections.namedtuple('Track', 'apply, train, label')):
    """Structure for holding related flow parts of different modes.
    """
    def __new__(cls, apply: typing.Optional[view.Path] = None,
                train: typing.Optional[view.Path] = None,
                label: typing.Optional[view.Path] = None):
        return super().__new__(cls, apply or view.Path(node.Future()),
                               train or view.Path(node.Future()),
                               label or view.Path(node.Future()))

    def extend(self, apply: typing.Optional[view.Path] = None,
               train: typing.Optional[view.Path] = None,
               label: typing.Optional[view.Path] = None) -> 'Track':
        """Helper for creating new Track with specified paths extended by provided values.

        Args:
            apply: Optional path to be connected to apply track.
            train: Optional path to be connected to train track.
            label: Optional path to be connected to label track.

        Returns: New Track instance.
        """
        return Track(self.apply.extend(apply) if apply else self.apply,
                     self.train.extend(train) if train else self.train,
                     self.label.extend(label) if label else self.label)

    def use(self, apply: typing.Optional[view.Path] = None,
            train: typing.Optional[view.Path] = None,
            label: typing.Optional[view.Path] = None) -> 'Track':
        """Helper for creating new Track with specified paths replaced by provided values.

        Args:
            apply: Optional path to be used as apply track.
            train: Optional path to be used as train track.
            label: Optional path to be used as label track.

        Returns: New Track instance.
        """
        return Track(apply or self.apply, train or self.train, label or self.label)


class Composable(metaclass=abc.ABCMeta):
    """Common base for operators and expressions.
    """
    @abc.abstractmethod
    def expand(self) -> Track:
        """Compose and return a segment track.

        Args:
            context: Worker context instance.

        Returns: Segment track.
        """

    def __rshift__(self, right: 'Composable') -> 'Expression':
        """Semantical composition construct.
        """
        return Expression(right, self)

    def __str__(self):
        return self.__class__.__name__

    @abc.abstractmethod
    def compose(self, left: 'Composable') -> Track:
        """Expand the left segment producing new composed segment track.

        Args:
            left: Left side composable.
            context: Worker context instance.

        Returns: Composed segment track.
        """


class Expression(Composable):
    """Operator chaining descriptor.
    """
    _TERMS = weakref.WeakSet()

    def __init__(self, right: Composable, left: Composable):
        for term in (left, right):
            if not isinstance(term, Composable):
                raise ValueError(f'{type(term)} not composable')
            if term in self._TERMS:
                raise ArithmeticError(f'Non-linear composition of {term}')
            self._TERMS.add(term)
        self._right: Composable = right
        self._left: Composable = left

    def __str__(self):
        return f'{self._left} >> {self._right}'

    def expand(self) -> Track:
        """Compose the segment track.

        Args:
            context: Worker context instance.

        Returns: Segment track.
        """
        return self._right.compose(self._left)

    def compose(self, left: 'Composable') -> Track:
        """Expression composition is just extension of its tracks.

        Args:
            left: Left side composable.
            context: Worker context instance.

        Returns: Segment track.
        """
        return left.expand().extend(*self.expand())


class Origin(Composable):
    """Initial builder without a predecessor.
    """
    def expand(self) -> Track:
        """Track of future nodes.

        Args:
            context: Worker context instance.

        Returns: Segment track.
        """
        return Track()

    def compose(self, left: 'Composable') -> Track:
        """Origin composition is just the left side track.

        Args:
            left: Left side composable.
            context: Worker context instance.

        Returns: Segment track.
        """
        return left.expand()

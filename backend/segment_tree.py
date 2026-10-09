"""segment_tree.py - Segment Tree abstract data type used by BudgetBuddy.

A segment tree stores one value per index (here: one value per DAY of the month)
and answers "combine everything from day L to day R" in O(log n), while a
point update also costs only O(log n).

The tree is generic: pass any associative `combine` function and its `identity`.
    sum tree : combine=add, identity=0   -> total spending in a range of days
    max tree : combine=max, identity=0   -> biggest single day in a range
Indexes are 0-based and ranges are inclusive on both ends.
"""
import operator


class SegmentTree:
    def __init__(self, size, combine=operator.add, identity=0):
        if not isinstance(size, int) or size <= 0:
            raise ValueError("size must be a positive integer")
        self.n = size
        self.combine = combine
        self.identity = identity
        self.tree = [identity] * (4 * size)   # 4n slots is always enough
        self.leaves = [identity] * size       # current value of every index

    @classmethod
    def from_list(cls, values, combine=operator.add, identity=0):
        st = cls(len(values), combine, identity)
        st.leaves = list(values)
        st._build(1, 0, st.n - 1)
        return st

    def _build(self, node, lo, hi):
        if lo == hi:
            self.tree[node] = self.leaves[lo]
            return
        mid = (lo + hi) // 2
        self._build(2 * node, lo, mid)
        self._build(2 * node + 1, mid + 1, hi)
        self.tree[node] = self.combine(self.tree[2 * node], self.tree[2 * node + 1])

    def _check(self, i):
        if not isinstance(i, int) or not 0 <= i < self.n:
            raise IndexError(f"index {i} out of range 0..{self.n - 1}")

    def get(self, index):
        self._check(index)
        return self.leaves[index]

    def update(self, index, value):
        """Replace the value at `index`. O(log n)."""
        self._check(index)
        self.leaves[index] = value
        self._update(1, 0, self.n - 1, index, value)

    def add(self, index, delta):
        """Add `delta` to the value at `index`. O(log n)."""
        self.update(index, self.get(index) + delta)

    def _update(self, node, lo, hi, index, value):
        if lo == hi:
            self.tree[node] = value
            return
        mid = (lo + hi) // 2
        if index <= mid:
            self._update(2 * node, lo, mid, index, value)
        else:
            self._update(2 * node + 1, mid + 1, hi, index, value)
        self.tree[node] = self.combine(self.tree[2 * node], self.tree[2 * node + 1])

    def query(self, left, right):
        """Combine all values from `left` to `right`, inclusive. O(log n)."""
        self._check(left)
        self._check(right)
        if left > right:
            raise ValueError("left must be <= right")
        return self._query(1, 0, self.n - 1, left, right)

    def _query(self, node, lo, hi, left, right):
        if right < lo or hi < left:            # no overlap
            return self.identity
        if left <= lo and hi <= right:         # fully inside
            return self.tree[node]
        mid = (lo + hi) // 2                   # partial overlap: split
        return self.combine(
            self._query(2 * node, lo, mid, left, right),
            self._query(2 * node + 1, mid + 1, hi, left, right),
        )


class SumSegmentTree(SegmentTree):
    def __init__(self, size):
        super().__init__(size, operator.add, 0)


class MaxSegmentTree(SegmentTree):
    def __init__(self, size):
        super().__init__(size, max, 0)

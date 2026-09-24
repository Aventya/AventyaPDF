"""
history.py
Deshacer / rehacer basado en instantáneas completas del documento.

El documento PyMuPDF no ofrece un modelo de cambios reversible, así que cada
acción que modifica el PDF guarda antes una copia en bytes (`doc.tobytes()`).
Es sencillo y robusto: restaurar es reabrir esos bytes. Para no agotar la
memoria con PDF grandes se limita tanto el número de pasos como el total de
bytes retenidos (se descartan los pasos más antiguos).
"""
from dataclasses import dataclass


@dataclass
class Snapshot:
    data: bytes
    page: int
    label: str


class UndoStack:
    def __init__(self, max_steps: int = 40, max_bytes: int = 400 * 1024 * 1024):
        self.max_steps = max_steps
        self.max_bytes = max_bytes
        self._undo: list[Snapshot] = []
        self._redo: list[Snapshot] = []

    # ── estado ─────────────────────────────────────────────────────────── #

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo_label(self) -> str:
        return self._undo[-1].label if self._undo else ""

    def redo_label(self) -> str:
        return self._redo[-1].label if self._redo else ""

    # ── operaciones ────────────────────────────────────────────────────── #

    def push(self, snap: Snapshot) -> None:
        """Registra el estado ANTERIOR a una acción. Invalida el rehacer."""
        self._undo.append(snap)
        self._redo.clear()
        self._trim()

    def undo(self, current: Snapshot) -> Snapshot | None:
        """Devuelve el estado a restaurar; `current` pasa a la pila de rehacer."""
        if not self._undo:
            return None
        snap = self._undo.pop()
        self._redo.append(Snapshot(current.data, current.page, snap.label))
        return snap

    def redo(self, current: Snapshot) -> Snapshot | None:
        if not self._redo:
            return None
        snap = self._redo.pop()
        self._undo.append(Snapshot(current.data, current.page, snap.label))
        self._trim()
        return snap

    def discard_last(self) -> None:
        """Quita el último punto de deshacer sin restaurarlo (la acción no cambió nada)."""
        if self._undo:
            self._undo.pop()

    def discard_redo(self) -> None:
        """Tras revertir una operación fallida no debe poder «rehacerse»."""
        self._redo.clear()

    def _trim(self) -> None:
        while len(self._undo) > self.max_steps:
            self._undo.pop(0)
        total = sum(len(s.data) for s in self._undo) + sum(len(s.data) for s in self._redo)
        while total > self.max_bytes and len(self._undo) > 1:
            total -= len(self._undo.pop(0).data)

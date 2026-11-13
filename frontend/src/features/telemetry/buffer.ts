/** Circular buffer: O(1) insertion, bounded memory, chronological snapshots. */
export class CircularBuffer<T> {
  private readonly values: (T | undefined)[];
  private cursor = 0;
  private count = 0;
  constructor(readonly capacity: number) {
    if (!Number.isInteger(capacity) || capacity < 1) throw new Error('Capacidad inválida');
    this.values = new Array(capacity);
  }
  push(value: T) { this.values[this.cursor] = value; this.cursor = (this.cursor + 1) % this.capacity; this.count = Math.min(this.count + 1, this.capacity); }
  clear() { this.values.fill(undefined); this.cursor = 0; this.count = 0; }
  snapshot(): T[] {
    return Array.from({ length: this.count }, (_, index) => this.values[(this.cursor - this.count + index + this.capacity) % this.capacity]!);
  }
}

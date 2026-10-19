/** Keep the rig hidden throughout consecutive transparent frames. */
export function isModelVisible(opacity: number): boolean {
  return opacity >= 0.005;
}

/** Compact layouts take priority; low-power desktop devices use the middle tier. */
export function deviceDprLimit(compact: boolean, lowPower: boolean): number {
  return compact ? 1.25 : lowPower ? 1.35 : 1.5;
}

// A response from an older edit must never replace the active model or estimates.
export class Revision {
  value = 0;
  next() { return ++this.value; }
  current(value) { return value === this.value; }
}

export function restoreParameters(saved, config) {
  const values = { ...config.defaults };
  for (const field of config.fields) {
    const value = saved?.[field.id];
    const valid = field.type === 'boolean' ? typeof value === 'boolean' :
      typeof value === 'number' && Number.isFinite(value) && value >= field.min && value <= field.max &&
      (field.type !== 'integer' || Number.isInteger(value));
    if (valid) values[field.id] = value;
  }
  return values;
}

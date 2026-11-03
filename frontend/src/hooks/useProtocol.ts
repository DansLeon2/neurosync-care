import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ProtocolOut } from '../types/neuro';

export function useProtocol() {
  const [protocol, setProtocol] = useState<ProtocolOut | null>(null);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let alive = true;
    api.getProtocol().then(value => { if (alive) { setProtocol(value); setError(''); } })
      .catch(err => { if (alive) setError((err as Error).message); });
    return () => { alive = false; };
  }, [revision]);
  return { protocol, error, retry: () => setRevision(value => value + 1) };
}

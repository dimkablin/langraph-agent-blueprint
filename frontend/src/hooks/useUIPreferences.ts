import { useCallback, useEffect, useState } from "react";

import {
  loadUIPreferences,
  saveUIPreferences,
  type UIPreferences,
  updateUIPreferences,
} from "../runtime/uiPreferences.ts";

export function useUIPreferences() {
  const [preferences, setPreferences] = useState(loadUIPreferences);

  useEffect(() => {
    saveUIPreferences(preferences);
  }, [preferences]);

  const updatePreferences = useCallback((patch: Partial<UIPreferences>) => {
    setPreferences((current) => updateUIPreferences(current, patch));
  }, []);

  return { preferences, updatePreferences };
}

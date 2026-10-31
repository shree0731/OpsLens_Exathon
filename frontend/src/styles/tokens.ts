/**
 * OpsLens Design Tokens
 * Follows reference UI: light grey background, rounded white cards,
 * dark navy buttons, subtle blue accents, and accessible status colors.
 */

export const tokens = {
  colors: {
    background: '#F8FAFC',
    surface: '#FFFFFF',
    border: '#E2E8F0',
    borderLight: '#F1F5F9',
    textPrimary: '#0F172A',
    textSecondary: '#64748B',
    textMuted: '#94A3B8',
    
    navy: {
      primary: '#0F172A',
      hover: '#1E293B',
      light: '#334155',
    },
    
    brand: {
      50: '#EFF6FF',
      100: '#DBEAFE',
      500: '#3B82F6',
      600: '#2563EB',
      700: '#1D4ED8',
    },

    status: {
      green: {
        base: '#10B981',
        bg: '#ECFDF5',
        border: '#A7F3D0',
        text: '#065F46',
      },
      amber: {
        base: '#F59E0B',
        bg: '#FFFBEB',
        border: '#FDE68A',
        text: '#92400E',
      },
      red: {
        base: '#EF4444',
        bg: '#FEF2F2',
        border: '#FECACA',
        text: '#991B1B',
      },
    },
  },

  radii: {
    sm: '0.375rem',  // 6px
    md: '0.5rem',    // 8px - inputs, buttons
    lg: '0.75rem',   // 12px - cards, dialogs
    xl: '1rem',      // 16px - left rail, main containers
    full: '9999px',
  },

  shadows: {
    soft: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
    card: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.03)',
    elevated: '0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -4px rgba(0, 0, 0, 0.04)',
    glowRed: '0 0 15px rgba(239, 68, 68, 0.35)',
    glowAmber: '0 0 15px rgba(245, 158, 11, 0.35)',
    glowGreen: '0 0 15px rgba(16, 185, 129, 0.35)',
  },
} as const;

export type StatusLevel = 'GREEN' | 'AMBER' | 'RED';

export function getStatusColor(status: StatusLevel | string) {
  const norm = (status || '').toUpperCase();
  if (norm === 'RED' || norm === 'CRITICAL' || norm === 'FAILED') {
    return tokens.colors.status.red;
  }
  if (norm === 'AMBER' || norm === 'WARNING') {
    return tokens.colors.status.amber;
  }
  return tokens.colors.status.green;
}

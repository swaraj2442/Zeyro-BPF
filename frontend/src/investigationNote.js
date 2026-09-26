// Dynamically composes a Trade Sentinel investigation note from live evidence.
// Every value here is read from the API response for the selected entity —
// nothing is precomputed or hardcoded per entity.

function riskLabel(score) {
  if (score > 70) return 'HIGH RISK';
  if (score > 40) return 'MEDIUM RISK';
  return 'LOW RISK';
}

function fmtMoney(n) {
  return `$${Math.round(n).toLocaleString()}`;
}

function patternLine(pattern) {
  const labels = {
    duplicate_invoice_financing: 'Duplicate Invoice Financing',
    fan_in_out_concentration: 'Fan-in/Fan-out Concentration',
    dormant_then_active: 'Dormant-then-Active Relationship',
    circular_invoicing: 'Circular Invoicing',
    volume_spike: 'Volume/Velocity Spike',
    kyc_mismatch: 'KYC / Declared Volume Mismatch',
  };
  return labels[pattern] || pattern;
}

export function buildInvestigationNote(entity) {
  const { entity_id, business_name, entity_type, risk_score, matched_patterns, features, suspicious_invoices, counterparty_entities } = entity;
  const label = riskLabel(risk_score);
  const lines = [];

  lines.push({
    type: 'header',
    text: `${business_name} (${entity_id})`,
    sub: `${entity_type.toUpperCase()} · Trade Risk Score ${risk_score.toFixed(1)}/100 · ${label}`,
  });

  if (matched_patterns.length === 0) {
    lines.push({
      type: 'body',
      text: `No behavioral risk patterns triggered for this entity. Observed network position, transaction velocity, and declared-vs-actual volume are all within normal range.`,
    });
    return lines;
  }

  lines.push({
    type: 'section',
    title: 'Primary Signal',
    text: patternLine(matched_patterns[0]),
  });

  if (suspicious_invoices && suspicious_invoices.length > 0) {
    const totalExposure = suspicious_invoices.reduce((sum, [, , amt]) => sum + amt, 0);
    const evidenceLines = suspicious_invoices.map(([invRef, factors, amt]) => {
      const factorList = Array.isArray(factors) ? factors.join(', ') : factors;
      return `Invoice ${invRef} — ${fmtMoney(amt)} submitted across factors: ${factorList}`;
    });
    lines.push({
      type: 'section',
      title: 'Evidence Chain',
      list: evidenceLines,
    });
    lines.push({
      type: 'section',
      title: 'Estimated Exposure',
      text: fmtMoney(totalExposure) + ' in duplicate financing across ' + suspicious_invoices.length + ' invoice(s)',
    });
  }

  const otherPatterns = matched_patterns.slice(1);
  if (otherPatterns.length > 0) {
    lines.push({
      type: 'section',
      title: 'Additional Signals',
      list: otherPatterns.map(patternLine),
    });
  }

  lines.push({
    type: 'section',
    title: 'Network',
    text: `Connected to ${counterparty_entities.length} counterpart${counterparty_entities.length === 1 ? 'y' : 'ies'}: ${counterparty_entities.slice(0, 6).join(', ')}${counterparty_entities.length > 6 ? '…' : ''}`,
  });

  const actions = [];
  if (matched_patterns.includes('duplicate_invoice_financing')) {
    actions.push('Freeze all pending financing requests from this exporter');
    actions.push('Alert affected factors of duplicate submission');
    actions.push('Cross-check invoice(s) against GSTN / eWay Bill records');
  }
  if (matched_patterns.includes('fan_in_out_concentration')) {
    actions.push('Review counterparty concentration for AML layering risk');
  }
  if (matched_patterns.includes('circular_invoicing')) {
    actions.push('Verify goods movement matches payment flow (TBML check)');
  }
  if (matched_patterns.includes('dormant_then_active')) {
    actions.push('Trigger KYC refresh given sudden activity resumption');
  }
  if (actions.length === 0) {
    actions.push('Continue standard monitoring cadence');
  }

  lines.push({
    type: 'section',
    title: 'Recommended Actions',
    list: actions,
  });

  lines.push({
    type: 'footer',
    text: risk_score > 70
      ? 'Recommendation: ESCALATE TO FRAUD INVESTIGATION'
      : risk_score > 40
      ? 'Recommendation: FLAG FOR ANALYST REVIEW'
      : 'Recommendation: NO ACTION REQUIRED',
  });

  return lines;
}

#!/usr/bin/env bash
# Operator-approved global provider configuration; never a research profile.
# Requires a GitHub identity with repository Actions-variable read/write access.
set -euo pipefail

case "${1:-}" in
  --check|--apply) horizon_config_action="$1" ;;
  *) echo 'Usage: bash scripts/configure-production-decisions.sh --check|--apply' >&2; exit 2 ;;
esac

horizon_config_repo='JsonLord/Horizon'
horizon_config_names=(HORIZON_DECISION_BASE_URL HORIZON_DECISION_CHAT_URL HORIZON_DECISION_MODEL HORIZON_DECISION_RESPONSE_MODEL HORIZON_DECISION_API_MODE)
horizon_config_values=('https://test-d.blablador.fz-juelich.de/v1/systemone' 'https://test-d.blablador.fz-juelich.de/v1/systemone' 'alias-clef' 'alias-clef' 'systemone')

# Fail before any mutation when the current identity cannot inspect variables.
if ! gh api "repos/$horizon_config_repo/actions/variables" >/dev/null; then
  echo 'Cannot inspect Actions variables; use an identity with repository Variables read/write permission. No changes applied.' >&2
  exit 1
fi

if [[ "$horizon_config_action" == --apply ]]; then
  # Protocol last: each API request is independent, so this is not atomic.
  for horizon_config_index in "${!horizon_config_names[@]}"; do
    if ! gh variable set "${horizon_config_names[$horizon_config_index]}" \
      --repo "$horizon_config_repo" --body "${horizon_config_values[$horizon_config_index]}"; then
      echo 'Variable update failed. Earlier writes may have succeeded; inspect settings before retrying. API key was not modified.' >&2
      exit 1
    fi
  done
fi

for horizon_config_index in "${!horizon_config_names[@]}"; do
  horizon_config_actual="$(gh api "repos/$horizon_config_repo/actions/variables/${horizon_config_names[$horizon_config_index]}" --jq '.value')"
  if [[ "$horizon_config_actual" != "${horizon_config_values[$horizon_config_index]}" ]]; then
    echo "Configuration mismatch: ${horizon_config_names[$horizon_config_index]}" >&2
    exit 1
  fi
done
echo 'All five production decision variables verified. API key unchanged.'

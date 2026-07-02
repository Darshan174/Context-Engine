export function sourceFamily(component = {}) {
  const raw = [
    component.source_type,
    component.fact_type,
    component.model_name,
    component.source_metadata_summary?.tool,
    component.source_metadata_summary?.item_type,
  ].filter(Boolean).join(" ").toLowerCase();

  if (/(github|pull_request|github_pr|github_issue|\bpr\b|issue|changed_file|commit)/.test(raw)) return "github";
  if (/(agent_session|ai_context|codex|claude|opencode|open_code|kimi|glm|ai_step|ai_task|ai_decision)/.test(raw)) return "agent";
  if (/(slack|discord|gmail|email|zoom|meeting|message)/.test(raw)) return "communication";
  if (/(local|browser_upload|paste|document|gdrive|notion|source)/.test(raw)) return "local";
  return "other";
}

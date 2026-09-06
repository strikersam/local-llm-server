# Graph Report - autonomous-ai-agency  (2026-09-06)

## Corpus Check
- 1497 files · ~2,169,638 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 30323 nodes · 56650 edges · 1300 communities (1136 shown, 116 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 3329 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0d84c231`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- ExecutionRequest
- backend/server.py
- TaskStatus
- proxy.py
- llm/router.py
- WebsiteScanner
- CompanyGraphService
- TaskSpec
- api.js
- company_api.py
- config.py
- test_llm_router_queue_cache.py
- test_llm_router_strategies.py
- Task
- PolicyEngine
- test_ceo_supervision.py
- _fixture
- E2BSandboxSession
- SelfHealingAgent
- test_governance_sandbox.py
- LLMRequest
- TaskWorkflowService
- BrainConfig
- test_render_mcp.py
- test_ceo_micromanager.py
- SQLiteStore
- test_user_research_skill.py
- test_llm_router_resilience.py
- RuntimeCapabilityRegistry
- AnthropicProvider
- tasks/service.py
- AgentRunner
- CEODispatcher
- test_agent_tool_governance.py
- ImprovementLoop
- MongoDBStore
- test_failover_client_shared.py
- test_unit8_model_catalog.py
- MultiAgentSwarm
- get_workflow_orchestrator
- test_model_router.py
- test_mcp_registry.py
- ToolRegistry
- PrimeAgentAdapter
- services/seo_audit.py
- UserRole
- settings.py
- resolve_active_brain
- post
- AgentJobManager
- test_governance_enforcement.py
- agent/workspace.py
- test_ceo_router.py
- get_registry
- get_runtime_manager
- FetchResult
- test_sam_livekit.py
- Agency
- AgentSessionStore
- test_agent_runner.py
- lifespan
- test_webui_provider_priority.py
- ChatHistoryStore
- api.ts
- AgentSwarm
- seo_portfolio_bridge.py
- detector.py
- BrainWatchdog
- FeatureMatrix
- setup/api.py
- test_cost_aware_routing_eval.py
- V5App.jsx
- test_model_catalog.py
- CompanyGraphStore
- services/background.py
- HybridSystem
- ResearchTask
- RenderOpsMonitor
- TestClient
- test_ai_insights.py
- test_startup_warmup.py
- get_scheduler
- test_repo_connection.py
- test_procedural_memory.py
- CoworkSession
- tasks/api.py
- App.js
- test_llm_router_e2e.py
- TestClient
- ArtifactStore
- direct_chat.py
- FreeBuffAgent
- test_brain_config_api.py
- resolve_e2b_config
- telegram_bot.py
- WorkflowEngine
- BackgroundAgent
- test_web_reach.py
- TokenBudget
- FinancialMetrics
- LogWatcher
- Agent
- test_issue_intake.py
- audit
- Settings
- Page
- WorkspaceManager
- portfolio_intelligence.py
- AgileSprint
- test_provider_router.py
- ai_runner.py
- test_sqlite_store.py
- BrowserSession
- UserMemoryStore
- LLMRouter
- test_integration_c4_c5_c6_d3.py
- KeyStore
- failover_client.py
- _scanner
- get_self_healing_agent
- Command
- test_context_rulebook.py
- Company
- frontend/package.json
- run_task
- ProviderConfig
- diagnostics.py
- InferenceCache
- CheckpointStore
- test_trend_scoping.py
- RepowiseIntelligence
- FeatureMaturity
- seo_api.py
- OnboardingScreen.jsx
- test_governance_api.py
- _cfg
- ReactScratchpad
- _StubProvider
- test_response_cache.py
- E2BAdapter
- _step
- test_slop_gate.py
- SpecialistService
- test_trend_watcher.py
- PortfolioManager
- useSafeData
- ProviderRouter
- claim
- call_llm
- TestHarnessAdapter
- persist_plan_spec
- TestEstimateTokensForMessages
- ScheduledJob
- ContextWindowManager
- MCPClient
- test_portfolio_intake.py
- BudgetTracker
- probe_catalogues.py
- clear_cooldowns
- test_telegram_freebuff.py
- WorkspaceManager
- test_daily_2026_07_27.py
- QuickNoteQueue
- enforcement.py
- KnowledgeGraph
- chat_handlers.py
- KeyPool
- MetricsRegistry
- test_pr923_fixes.py
- StreamingDeltaReconstructor
- SetupChecker
- pr_approval_gate.py
- _resolve_brain_provider
- test_e2b_task_wiring.py
- activation.py
- activation_api.py
- fmtErr
- OllamaCircuitBreaker
- PromptCacheManager
- _job_text
- TestRuntimeControl
- AgentJobRequest
- test_audit.py
- TaskBoardScreen.jsx
- ai/router.py
- test_runtime_governance.py
- test_classify_dependabot_update.py
- WorkspaceManifest
- test_dashboard_cache.py
- rbac.py
- ProvidersScreen.jsx
- ApprovalStore
- WorkflowRun
- test_features_api.py
- test_schedule_backlog_drain.py
- test_video_transcript.py
- test_operational_incidents.py
- portfolio_api.py
- Part A — CodeRabbit review fixes for this PR (do first, small)
- Docker Agent Runtimes Setup
- anthropic_compat.py
- SchedulerStore
- model_router.py
- render_ops.py
- _payload
- TestRecordUsageAndStats
- test_process_quick_note_workflow.py
- Persistent Memory System
- nvidia_models.py
- test_unit6_resolve_component_model.py
- AgentScheduler
- test_bedrock_provider.py
- TrendWatcher
- timedelta
- v4_api.py
- Kept Rules — the 44 that survive the audit
- configuration-reference.md
- governance.py
- compare_runtimes.py
- NotificationDispatcher
- RewardScorer
- WorkspaceTools
- ScheduleStore
- Artifact
- emit_chat_observation
- distributed.py
- JCodeAdapter
- test_v4_reliability_regression.py
- _run
- Workflow
- test_llm_router_disabled.py
- InternalAgentAdapter
- service_daemon.py
- daily_digest.py
- TestClient
- WorkflowBuildRequest
- test_portfolio_intelligence.py
- test_schedule_growth_invariants.py
- GitHubTools
- test_knowledge_sync.py
- AutonomyTracker
- loop.py
- PatternConsolidation
- [Unreleased]
- [Unreleased]
- test_daily_2026_06_04.py
- system_instruction
- NIMConnectionPool
- TestCatalogFable51
- TestAuthAndTaskOwnership
- test_one_model_catalogue.py
- AdaptiveHalter
- ContextPruner
- AgileManager
- provider_max_rpm
- test_agent_api.py
- _Collection
- SyncService
- TaskDispatcher
- PlaybookLibrary
- test_verification_strategies.py
- Screens
- REWRITE_PLAN.md — Phased Migration Strategy
- test_background_services.py
- test_persistent_memory.py
- SecurityScanner
- test_provider_render_env.py
- agent_runtime.py
- api_keys_for
- local_controller.py
- test_live_server.py
- test_all_providers_discovery.py
- ._log_event
- SpecEntry
- test_loop_registry.py
- OutputFilter
- _resolve_user_github_token
- DashboardScreen.jsx
- context_rules.py
- _plan
- brain_config.py
- test_platform_controls.py
- ContextCompressor
- ContextManager
- SparkProvider
- ResourceWatchdog
- README.md
- Configuration Reference
- Workspace
- test_rate_limiter.py
- RateLimitTracker
- report_to_markdown
- test_brain_failover.py
- app.py
- skill_bindings.py
- test_sam_voice.py
- test_microagents.py
- Security Analysis — local-llm-server
- facade.py
- _get_provider_policy
- openclaw_gateway.py
- Langfuse Observability Guide
- v3_models.py
- BrainFailoverManager
- TestDiagCommand
- test_nvidia_model_discovery.py
- test_workspace_isolation.py
- test_direct_chat_evolution.py
- SkillLibrary
- StuckDetector
- agents/api.py
- High-Agency Frontend Skill
- LlmProviderConfig
- Quick-Note GitHub Issues Processing - Session Summary
- test_failover_silent_exhaustion.py
- sync/service.py
- test_mcp_governance.py
- switch_brain.py
- OrchestratorCheckpointStore
- session_retro.py
- test_autonomy_gate.py
- test_backend_server_features.py
- SeoFixer
- test_colibri_provider.py
- analyze_page
- _execute_skill_impl
- test_force_cleanup_conditional_delete.py
- test_rag_context.py
- ProjectScaffolder
- Initiative
- test_tasks_awaiting_approval_api.py
- generate_context.py
- v3_auth.py
- SeoFixRequest
- SteeringInjector
- test_claude_setup_audit.py
- decide
- OrchestratorQueue
- test_internal_agent_did_work.py
- test_purge_backlog.py
- TerminalPanel
- Python Dependencies (`requirements.txt`)
- Technical Debt Register — local-llm-server
- FeatureEntry
- ProviderConsole.jsx
- SeoAuditReport
- webui/router.py
- TrafficDirector
- webui/frontend/package.json
- CostAttributor
- test_regression.py
- test_agent_scripts_share_one_model_list.py
- test_crispy_burn_in.py
- _Recorder
- test_skill_registry_boot_refresh.py
- SprintMetrics
- tests/conftest.py
- Deploy: FreeBuff Telegram bot (24×7)
- Claude Code + Qwen Local Setup
- provider_base_url
- model_discovery.py
- ModelRouter
- keepalive.py
- test_brain_availability_doctor.py
- _is_dns_failure
- CompanyAgencyService
- isolated_telegram_config
- _captured_request_headers
- TestNoNvidiaFallbackIsRetired
- test_scheduler_hydration_bounded.py
- CommitTracker
- VoiceCommandInterface
- Performance Analysis — local-llm-server
- LLM Router — troubleshooting
- autonomous_fix.py
- implement_agent.py
- output_filter.py
- control_registry.py
- analyze
- monitor_lib.py
- brain_failover.py
- get_failover_manager
- test_telegram_approval_e2e.py
- test_brain_migration_writes_a_live_model.py
- test_daily_automation_2026_08_03.py
- test_provider_enable_disable.py
- test_telegram_mutating_commands.py
- TestWorkflow
- CheckRun
- _undeclared
- 1. The Rules
- reset_store
- Session Handoff — 2026-06-15
- TASK 4 — End-to-end approval-gate test
- models/seo_audit.py
- test_connector_registry.py
- test_rate_limit_backoff_survives.py
- TemporalContextGraph
- TestClassifyPlainText
- test_service_token.py
- verify_token
- github_tools.py
- test_harness_spec.py
- audit_drift
- TestStreamableHTTPTransport
- Findings
- Local AI Stack with Docker
- Traffic Distribution Across Providers
- Implementation Prompt: Rich TaskBoard + Agile Sprint Integration
- Telegram Bot Setup
- video_transcript.py
- launcher.py
- test_agent_free_brain.py
- control_overrides.py
- CollectionLike
- Native operations
- test_all_features.py
- test_agency_fix.py
- test_v3_auth.py
- refine
- _status_snapshot
- Agent Governance Guide
- The fifteen strategies
- SetupWizardPage.js
- getBackendUrl
- PrioritizedTask
- TestModelRegistryUpdates
- _Cursor
- WindowsServiceManager
- SyntheticDataPipeline
- test_task_source_id_race.py
- _get
- test_cerebras_catalogue.py
- test_monitor_lib.py
- Path
- test_mostly_failed_steps.py
- test_v4_api.py
- HarnessEnrichment
- classify_direct_chat_intent
- operational_incidents.py
- OperationalIncidentTracker
- FilterResult
- AdaptivePermissions
- ._connect
- LocalBrainStore
- AdminScreen.jsx
- Harness
- TestLegacyRouterCacheTTL
- test_anthropic_refusal_fallback.py
- test_telegram_diag_endpoint.py
- _P
- create_wiki_page
- PersistentMemoryStore
- RegistrySkill
- _ensure_tasks_source_id_unique_index
- V3 API Migration Plan — LLM Relay Platform
- test_north_mini_code.py
- test_chat_mode_regressions.py
- _env_float
- AgentMessageBus
- DecisionsStoreTests
- GuardrailEngine
- test_issue_triage.py
- weekly_digest.py
- test_autonomous_agency_e2e.py
- _FakeSandbox
- test_local_controller.py
- test_provider_state_durability.py
- run_trend_analysis
- test_unit5_ui_provider_surface.py
- test_agent_tools.py
- LocalWorkspace
- MemoryCategory
- Skill: modularity-review
- Design Audit
- Findings
- test_minimax_bug_fixes.py
- Skill: modularity-review
- crispy_client.py
- 4. Troubleshooting
- Docker AI Governance Audit — Final Report
- 1. Capability-by-capability
- 4. Threats
- Dynamic Model Routing
- FeatureUnavailableError
- PortfolioScreen.jsx
- infra_cost.py
- ai/__init__.py
- ClaudeCodeAdapter
- build_workflow.py
- context_plan_gate.py
- run_bot
- HarnessRegistry
- test_kimi_bridge_server.py
- ProviderCircuit
- PriorityTaskQueue
- APIClient
- Page
- TestBrainFailoverModelUpdates
- ._call
- TestAdapterMetadata
- test_tasks_cache_ttl_env.py
- test_voice_pipeline.py
- TestUpdateTask
- MemoryKernel
- open_phase_report
- SamAgent
- _extract_tech_relevance
- HarnessAdapter
- Skill: fabric-patterns
- Analysis & Synthesis Instructions
- Production Readiness Assessment — local-llm-server
- _is_admin
- clear_override
- verify_service_token
- TestNormalizeResponseFormat
- Skill: fabric-patterns
- db/__init__.py
- Admin Dashboard Guide
- Implementation Plan
- Feature Guide
- resolve_free_nvidia_brain
- scripts/doctor.py
- build_matrix
- Delegation Plan (agent-ready work packages)
- test_p0_roadmap_a4_a5_b2.py
- RuntimeHealthService
- agency_fix.py
- LocalLLMSetup
- test_brain_patch_service_token.py
- TestSelfHealingInfrastructureClassification
- test_fabric_patterns.py
- test_fixes_reliability.py
- _Recorder
- test_repowise_intelligence.py
- validate_session_id
- ErrorInterceptorMiddleware
- SkillRegistry
- agile_sprints.py
- DreamMemory
- Comprehensive Skill Index (By Category)
- Agent Skill: Principal UI/UX Architect & Motion Choreographer (Awwwards-Tier)
- Component Map
- render_router.py
- Architecture Overview — local-llm-server
- Pending Activities — Implementation Playbook
- Platform Guide — the full tour
- The rules
- Part A — Health Report
- WorkflowScreen.jsx
- sync_readme_gallery.py
- test_p0_roadmap_b3_b4_b5.py
- TrainingSample
- test_company_api.py
- TestStopSlopChecker
- test_schedule_persistence.py
- test_telegram_service_webhook.py
- test_telegram_webhook.py
- handle_workflow_ide_chat
- harness_spec.py
- scrub
- _extract_tags
- agile_api.py
- SKILL: Industrial Brutalism & Tactical Telemetry UI
- Skill: data-quality-audit
- What "Slop" Looks Like
- local_brain_router.py
- run
- Section-by-Section Acceptance Criteria
- McpCard.jsx
- Provider
- redact_connection_url
- agent_readiness_audit.py
- sync_ngrok.py
- test_ci.sh
- test_task_brain_preflight.py
- test_activation_api.py
- TestAListingFailureDoesNotVetoTheAnswer
- test_daily_automation_2026_07_11.py
- test_frontend_deployment_guards.py
- test_health_endpoints.py
- test_keepalive.py
- test_openclaw_endpoints.py
- test_orchestrator_merge_decision.py
- TestRoutes
- test_skill_registry.py
- hermes_prompt.py
- test_lessons.py
- MemoryMiddleware
- .force_cleanup
- ._resolve_path
- AITellIssue
- Skill: repowise-intelligence
- ARCHITECTURE.md — Target Architecture
- _valid_login_state
- Skill: repowise-intelligence
- The 10-Step Workflow
- Nothing is blocked on an agent. Two things need a human.
- Contributing to local-llm-server
- refresh_agent_built_proof.py
- CEO Micro-Management
- 467 Brutal Audit — File-by-File Status
- Migration Notes
- Runbook — Apply the Fast Free NVIDIA Brain to Render (TASK 2)
- test_agent_chat_integration.py
- NvidiaProvider
- SQLiteStore
- fabric_cli.py
- AdminDigestRouterAuthTests
- GuardResult
- test_telegram_auto_approve.py
- ManagedAgentDreams
- e2e/test_browser.py
- test_agency_workflows_carry_the_failover_chain.py
- test_autonomy_status.py
- test_dockerfile_ships_root_modules.py
- test_langfuse_agency_wide.py
- test_local_brain_state.py
- TestMCPServer
- test_migrate_local_brain_env.py
- test_phase5_doctor.py
- TestBrainFailoverBackoff
- test_refresh_agent_built_proof.py
- test_tasks_reconciler_todo_requeue.py
- _hash_component
- check_kwargs
- .build
- Skill: agent-harness
- Skill: checkpoint-strategy
- Process
- Skill: local-ai-query
- Skill: parallel-agents
- Skill: parallel-worktrees
- Design System: Taste Standard
- Process
- cost_tracker.py
- Skill: user-research
- Agency Core — Progress & Resume Log
- Attention Mechanisms Internals
- ChatScreen.jsx
- _push_down_where
- verify_api_key
- router/health.py
- check_model_catalog_consistency.py
- TestDecisionsBotLinks
- DecisionsStore
- clear_wizard_state_cache
- test_critical_flows.py
- TestBrainConfigUpdates
- test_dockerfile_ships_config_dir.py
- test_scanner_live.py
- test_task_service_failed_comment.py
- compilerOptions
- migrate_local_brain_env.py
- _TFIDFIndex
- StopSlopChecker
- Process
- Skill: lr-schedule-advisor
- Instructions
- Instructions
- Process
- Checks Performed
- Skill: training-stability-monitor
- test_new_features_e2e.py
- admin_digest_router.py
- Skill: branch-cleanup
- Skill: perplexity — Web Research via Perplexity API
- Instructions
- Instructions
- Quick-Note Issues Processing Summary
- DirectChatSession
- Main proxy (`proxy.py`)
- Implementation Plan — DB-persisted, UI-switchable Brain (no redeploy)
- Backend changes
- Render MCP — autonomous platform debugging and environment monitoring
- Runbook: Auto-Resume After Cooldown / Interruption
- SEO / GEO / AIO Audit Engine
- overrides
- _build_request
- _parse_reset_epoch
- extract_failures
- _RedisBackend
- cmd_autonomy
- _process_task_callback
- TestAnthropicToolListCaching
- TestMCPToolsListCache
- TestWorkspace
- test_openclaw_gateway.py
- TestDisabledReasonRendering
- AGENTS.md — Codebase Map & Operations Reference
- CollaborationContext
- EdgeType
- Process
- Skill: Brain Dump
- Process
- Instructions
- Skill: duplicate-thread
- Skill: Email Triage
- Process
- Process
- Skill: graphify — Knowledge Graph Token Optimization
- Skill: prompt-library
- Skill: prompt-transparency
- Skill: Research
- Skill: scope-guard
- admin_update_task_router.py
- Instructions
- Skill: graphify — Knowledge Graph Token Optimization
- Skill: platform-setup — Autonomous Agency Bootstrap
- Device compatibility and model picks
- Autonomy Uplift — Living Roadmap & Detailed Implementation Specs
- OpenClaw — iOS Control of the Agency (Single-Service Free-Tier Deploy)
- rules
- ApplyReviewAgent
- ChatResponse
- HealthStatus
- _Budget
- ._order_group
- _is_bedrock_model_id
- Summary
- Agent Transparency Report
- update_provider_policy
- .publish
- _InMemoryBackend
- .on_task_complete
- _provider
- TestModelCostTableUpdates
- TestMCPClientStructuredOutput
- test_deploy_trigger_covers_image.py
- TestKillSwitchDurability
- test_quick_note_engine.py
- test_task_clarification.py
- validate_job_id
- skill_registry.py
- Trajectory
- Instructions
- Instructions
- Process
- Instructions
- Skill: system-prompt-audit
- Skill: task-alive-updates
- Process
- Instructions
- Skill: agent-browser — Real Chrome Browser Automation
- Instructions
- Instructions
- Skill: dev-browser — Browser Automation via Sandboxed JS
- Instructions
- Agent Orchestration Design
- Universality: case-coverage matrix
- Quantization Internals
- Implementation — DB-persisted, UI-switchable Brain (PR #824 follow-up)
- 2. Pending ⬜ — detailed implementation specs
- 467 Public Site Truth Spec
- GovernanceScreen.jsx
- extract_refusal
- install-agents.sh
- TestModelsEndpointAliases
- check_container_posture.py
- test_pytest_failure_parser.py
- Kimi Web-Bridge Service
- setup_ngrok.py
- ._coerce_ts
- test_admin_local_brain_router.py
- test_agile_api.py
- test_app_settings.py
- test_brain_default_consistency.py
- TestAnthropicWorkspaceIdCapture
- _FakeFiles
- test_providers_live_e2e.py
- BenchmarkReport
- MCPToolResult
- _keyword_search
- _extractive_compress
- Instructions
- Skill: pro-workflow
- Instructions
- Instructions
- Skill: resource-panel
- Skill: sandboxed-exec
- Workflow
- ECC Harness Patterns Skill
- Instructions
- Instructions
- Stop-Slop Quality Skill
- Agency Core — Ruthless Architecture Audit & Migration Plan
- AUTONOMY_CHARTER.md
- Tailored Onboarding, Editable Companies & Dynamic Roles
- Issue #467 — Section 1: Pulled State + PR Inventory
- Autonomy Charter — Telegram-Gated Self-Running Agency
- Context: Agentic Agile + Portfolio Management
- Deploy to Google Cloud Run
- Key Components
- Sampling Strategies Internals
- LLM Router — architecture
- Killer TODO Roadmap — local-llm-server
- NVIDIA NIM — Free Tier Setup
- What to clean up
- Worker Service — Operations Runbook
- LoopsScreen.jsx
- test_bedrock_live.py
- ProviderManager
- ._prune
- mask_secret
- capture_screens.py
- run_proxy.sh
- build_tech_db.py
- Security Policy
- test_conftest_hermetic_env.py
- test_empirical_verify.py
- test_event_log.py
- TestCrawl
- test_telegram_task_callback.py
- SavingsTracker
- Instructions
- Protocol: Premium Utilitarian Minimalism UI Architect
- The 5-Step Wrap-Up Ritual
- admin_local_brain_router.py
- connectors_api.py
- _normalize_tool_choice
- Agent: Reviewer (Verifier)
- Skill: Agentic Agile
- Skill: browserbase-ui-test — Adversarial UI Testing
- Skill: financial-analyst (Agentic CFO)
- Graphiti Temporal Context Skill
- Skill: seo-audit-report
- ADR-008: LLMRouter — the single multi-provider routing gateway
- Core Pillars
- 467 Golden Path — Locked Implementation Order
- Competitor Analysis — Autonomous AI Agency
- Issue #1427: quick-note:https://github.com/bingreeky/JIT
- LLM Router — configuration guide
- LLM Router — provider guide
- CI Troubleshooting Runbook
- _is_denied_path
- OutputFilter
- CircuitState
- enrich_quick_note_issues.py
- Dream
- _resolve_push_token
- _redact_for_notification
- test_catalogue_probe.py
- TestZeroAttemptDiagnostics
- TestPoliciesGovernanceStableClaim
- TestSessionMemory
- test_model_catalog_guard.py
- TestParsing
- TestMongoGate
- _FakeInner
- TestAnthropicPayloadStructuredOutput
- _Recorder
- test_workflow_api_mount.py
- synthesize
- Path
- rag_context.py
- _extract_workflow_relevance
- task.py
- Skill: changelog-enforcer
- Skill: learn-rule
- Instructions
- prompts/README.md
- Skill: Agentic Portfolio Management
- Skill: changelog-enforcer
- Skill: cowork-session (Claude Cowork)
- Skill: video-context — read a video without watching it
- Active Task Tracker
- Decision
- ADR 003: Multi-Agent Orchestration with Plan-Execute-Verify Loop
- Autonomous SDLC Loop (Agency Core, repo-agnostic)
- The 8-Step Golden Path
- Issue #1356: quick-note:https://searchengineland.com/turn-seo-backlog-into-roadmap-485713
- PR #634 Implementation Tracker
- KV Cache Internals
- Platform Controls
- Release Procedure
- V2.0 Modernization — Runbook
- Setup
- Troubleshooting
- ENGINEERING_STANDARDS.md — Patterns & Reference
- apply_overrides
- TestSwarmRoleRouting
- test_backend_requirements_cover_runtime_imports.py
- TestOpenAiToBedrockConverse
- test_changelog_parity_guard.py
- _StubManager
- TestPolicyAuthoringUiStableClaim
- TestPaidPolicyDurability
- test_scanner_deps_parity.py
- test_serve_spa_prefixes.py
- _safe_resolve
- stt.py
- EvalHarness
- navigation_metrics.py
- agent/output_filter.py
- _score_turns
- Task
- TrajectoryStep
- quality_checker.py
- Skill: docs-sync
- Agent: Implementer (Executor)
- Agent: Judge (Release / QA Gate)
- Agent: Planner (Architect)
- Skill: browserbase-browser — Real Browser Automation
- Skill: docs-sync
- Skill: memory-consolidation (Dream Memory)
- GitHub Branch Protection Settings
- ADR 001: Self-Hosted OpenAI-Compatible Proxy
- ADR 002: Dynamic Model Routing with Task Classification
- AGENTS.md — AI Agent Configuration for local-llm-server
- Advisor Strategy — Local Proxy Handling
- ceo-micromanagement.md
- Web UI + Admin (Claude Code–style)
- 467 Skill Inventory — load / wire / test status
- Free NVIDIA brain + UI-controlled provider policy + no silent spend
- Issue #362: Nvidia repo setup
- Issue #364: quick-note:https://www.marktechpost.com/2026/06/01/meet-memory-os-a-6-layer-open-source-memory-stack-built-on-top-of-hermes-agent/
- Issue #378: quick-note:https://www.marktechpost.com/2026/06/02/tinyfish-launches-bigset-an-open-source-multi-agent-system-that-builds-structured-live-datasets-from-plain-english-descriptions/
- Issue #379: quick-note:https://searchengineland.com/schema-markup-optimize-agentic-web-479080
- Issue #380: quick-note:https://cursor.com/blog/cloud-agent-lessons
- Issue #381: quick-note:https://www.xda-developers.com/claude-code-with-opus-48-is-expensive-but-i-made-it-efficient-with-my-local-ai-workflow/
- Issue #382: quick-note:https://claude.com/blog/how-coderabbit-used-claude-to-build-an-agent-orchestration-system
- Issue #383: quick-note:https://www.marktechpost.com/2026/05/29/hexo-labs-open-sources-sia-a-self-improving-agent-that-updates-both-the-harness-and-the-model-weights/
- Issue #416: feat: Self-hosted Codebuff (freebuff) on free NVIDIA models + Telegram bot phone control
- Issue #485: [Trend Digest] Week of 2026-06-08
- Issue #488: quick-note:https://github.com/cookiy-ai/user-research-skill
- Issue #491: Implement whatever is necessary from https://github.com/BehiSecc/awesome-claude-skills
- Issue #493: Use the https://github.com/mvanhorn/last30days-skill skill to get the trend updated
- Issue #495: Read https://www.anthropic.com/news/claude-fable-5-mythos-5 and understand if mythos or fable can be added to the repo
- Issue #504: EPIC: Autonomy hardening — live-verified defects 2026-06-10
- Issue #581: Sprint tracker: pending work after brand rename + mobile-first pass
- Issue #656: Bugs
- Issue #657: quick-note:https://github.com/earendil-works/pi
- Issue #659: quick-note:https://github.com/nex-agi/Nex-N2
- Issue #660: quick-note:https://github.com/getsentry/sentry-for-ai
- Issue #661: quick-note:https://github.com/XiaomiMiMo/MiMo-Code
- Issue #664: quick-note:https://github.com/Grominet95/jarvis-OS
- Issue #666: quick-note:https://github.com/porokka/jarvis-os
- Issue #670: quick-note:https://github.com/perplexityai/bumblebee
- Issue #672: quick-note:https://github.com/Chachamaru127/claude-code-harness
- Issue #676: quick-note:https://github.com/WeiboAI/VibeThinker
- Issue #820: quick-note:https://github.com/cobusgreyling/loop-engineering
- Positional Encoding Internals
- Setup
- TOP 6 — Highest-ROI Items (Validated by Opus Research Agent)
- SECTION A — Agent Efficiency (Hermes / AOS / MYT)
- SECTION C — Direct Chat Improvements (CBF / HRM)
- Runbook — Instance Activation
- Continual Harness (`agent/harness_spec.py`)
- Prime Agent Runtime
- PULL_REQUEST_TEMPLATE.md
- fetch_url.py
- security_fix_agent.py
- OllamaProvider
- Sol Advisor
- verify.sh
- Prompt Library
- crispy_burn_in.py
- e2e_smoke.py
- run_patched_colibri.py
- SessionMemory
- _NoopStore
- task_runner.py
- ._sprint
- TestTheWorkflowIsSafeAndReadOnly
- TestItIsNotBuiltForOneVendor
- test_compose_and_coordinate_api.py
- test_daily_automation_2026_07_09.py
- test_generate_context_standing_instructions.py
- test_local_brain_router_smoke.py
- TestAgentLoopMCPIntegration
- test_ping.py
- test_provider_models_db_outage.py
- test_runtimes_health_endpoint.py
- test_seo_audit_pending_expiry.py
- TestCatalog
- TestRevenuePortfolio
- test_task_store_fails_loud_in_production.py
- dry_clone_repo
- TOOLS.md — Available Tools for AI Agents
- CLAUDE.md — agent/
- SamConversation
- SIA
- Full-Output Enforcement
- summarise.sh
- updater.py
- ModelRegistry
- Changelog
- [5.0.0]
- Changelog
- AI Engineering Insights Skill
- Skill: hybrid-reasoning (Hybrid AI)
- Karpathy Guidelines Skill
- Skill: Managed Agents Dreams
- Skill: Multi-Agent Coordinator
- Skill: Obsidian Knowledge Graph
- Multi-Agent Research Coordinator Skill
- Skill: SuperClaude Slash Commands
- Skill: SuperClaude Workflow Engine
- _AllSignatures
- ADR-006: Strangler Fig migration with backward-compat shims
- Changelog
- [5.0.0]
- Changelog
- claude-mem Plugin — Persistent Memory for All Sessions
- Implementation plan + TO-DO (check off as you go)
- Topics Covered
- LLM Router — migration guide
- What's New
- Cloudflare = the real working app
- Workspace Issues
- Model and Response Issues
- Cost-aware routing evaluation
- GitHubScreen
- launch-claude-code.sh
- PRD — README Marketing Refresh
- CLAUDE.md — router/
- _replace
- check_changelog_parity.py
- check_doc_images.py
- client
- TestDashboard
- test_daily_2026_06_14.py
- TestSupportMatrixDocsSync
- test_doctor_coding_brain.py
- TestGithubTokenSQLiteRegression
- TestReasonsAreActionable
- TestProvidersScreen
- TestCli
- TestTechSkillMap
- TestActiveStrategy
- InitiativeProgress
- _brain_provider_status
- brain_providers
- openclaw_mobile_ui
- /fix-bug — Bug Fix Agent
- Command: /plan
- pre-commit
- Skill: browserbase-fetch — Lightweight Web Fetch
- Twitter Insights — Issue #228
- Twitter Insights — Issue #231
- OpenAI Codex CLI — Local LLM Server Config
- ADR-001: Adopt packages/ directory structure
- ADR-002: Centralize configuration in packages/config/
- ADR-003: Provider abstraction with unified interface
- ADR-004: Event bus for loosely coupled communication
- ADR-005: Merge Hermes into the main backend service
- ADR-007: Storage backend duck-typing over formal ABC
- Phases
- 5. The five autonomous loops
- Master Goal Prompt — Autonomous Agency CEO
- Agency Core — Operational Knowledge (verified live, 2026-06-10/11)
- The full agent capability roster
- Pre-Mortem Analysis: Agency Core autonomy story (Cloudflare deployment)
- SECTION B — NVIDIA / Cloud Model Integration (Nemotron / NVD)
- SECTION D — Deployment & Infrastructure (CHM / NVD)
- Feature Support Matrix
- Startup Issues
- StatusPill.jsx
- scripts/agile_ceremonies.py
- get_control
- apply_phase1_changes.py
- gen_screenshots.py
- gen_v4_screenshots.py
- parse_pytest_failures.py
- reset_kv_state
- setup-claude-code.sh script
- TestRuntimes
- Report
- TestCompany
- TestCli
- TestAgentRunnerExecution
- TestDirectChatAgentExecution
- TestDisabledProvidersAreNotFalselyReportedUnreachable
- _auth_headers
- TestNoHardcodedModels
- TestDelegationPlan
- .update_status
- harness.py
- heartbeat.sh
- feature-implementer.md
- /arch-review — Architecture Agent
- /devops-check — DevOps Agent
- /docs-update — Documentation Agent
- /qa-check — QA Agent
- Command: /review
- /security-audit — Security Agent
- pre-push
- Skill: browserbase-search — Structured Web Search
- Issue #230 — DUPLICATE
- python_client_example.py
- Agent job lifecycle
- Docker (local or any container host)
- Rollout
- Who is this for?
- SECTION E — Autonomy & Self-Healing (AOS / MYT / ECC)
- SECTION F — Developer Experience (CBF / ECC)
- Runtime troubleshooting
- Admin Dashboard Issues
- Agent API Issues
- Network and Tunnel Issues
- knowledgeGraphTab.test.js
- loginFlowNoTimeout.test.js
- test_company_stale_id_recovery.test.js
- worker_no_cache.test.js
- .chat
- governance/__init__.py
- inspect-agent-runtime.sh
- Prompt Library Changelog
- _add_colibri_shim_changelog_entry.py
- build_llama_cpp.ps1
- download_glm52_weights.ps1
- download_glm52_weights.sh script
- _fetch_pytest_failures.py
- setup_colibri.ps1
- setup_colibri.sh script
- status_colibri_server.ps1
- ._resolve_merge_decision
- start_tunnel.py
- TestAuth
- TestMobileNavigation
- test_v5_screens_smoke.py
- nvidia_live_test.py
- test_activity_feed.py
- test_agent_runtime_wrapper.py
- TestLegacyRouterServerFallback
- TestNoKeyEverReachesTheLog
- TestTheProbeIdentifiesItself
- TestModelRoleSeparation
- worker/index.js
- gather_render_evidence
- _clean_phases
- recovery.py
- test_activity_logs.py
- _InMemoryErrorLogHandler
- codebase-explorer.md
- docs-auditor.md
- risk-reviewer.md
- verification-reviewer.md
- aider_config.sh
- providers.yaml
- Issue → Context → Draft PR automation
- The 24x7 agency — your agents never go idle
- Privacy, security, and cost
- Credential Rotation Runbook
- Runbook: `make doctor`
- Authentication Issues
- Feature Maturity Issues
- Claude Code Specific Issues
- Langfuse Issues
- Runtime & Onboarding Issues
- render
- portfolio_refresh.py
- _resolve_default_executor_model
- stop_colibri_server.ps1
- test_nim_models.py
- .consolidate
- start_server.sh
- e2e_nvidia_fallback.py
- TestHealth
- TestProviders
- TestProviders
- TestWiki
- TestAgents
- _FakeSwarm
- sam
- test_local_brain_router_actor_regression.py
- test_no_exception_detail_leaks.py
- test_skills_route_order.py
- github
- .team_summary
- graphify-refresh
- [Unreleased]
- Session Learnings
- Configuration reference
- frontend/.eslintrc.json
- fix_regression_locators.py
- ProviderRouter
- branch_cleanup.sh
- fix_admin_digest_include.py
- local-ai-health-check.sh
- pull-ai-models.sh
- .consolidation_threshold
- start_tunnel_simple.py
- test-anthropic.js
- TestActivity
- TestApiKeys
- TestChat
- TestDoctor
- TestFeatures
- TestGitHub
- TestSchedules
- TestTasks
- TestWorkflowUsesTheGate
- test_docker_binary_missing.py
- test_docker_gating.py
- test_the_reserve_is_bounded_when_read_from_the_environment
- TestAdminEndpoints
- maintenance_section.md
- duplicate.sh
- hello_claude.py
- backend/__init__.py
- build-workflow
- commit-msg
- post-commit
- session-plan-bootstrap
- start_web_with_openclaw.sh
- frontend-redesign-prompt.md
- NEXT-SESSION-PROMPT.md
- docs/script.js
- specialists-skills-matrix.md
- get_tunnel_url.sh script
- prepare-commit-msg
- redact_secrets.sh
- handlers/__init__.py
- install.sh script
- models/README.md
- auth/__init__.py
- events/__init__.py
- integrations/__init__.py
- orchestration/__init__.py
- scheduler/__init__.py
- security/__init__.py
- shared/__init__.py
- storage/__init__.py
- packages/tasks/__init__.py
- telemetry/__init__.py
- providers/__init__.py
- run_ollama.sh
- run_tunnel.sh
- .__init__
- .__init__
- runtimes/adapters/__init__.py
- .__init__
- .stop
- .cleanup_workspace
- script.js
- insert_provider_policy.py
- replace_failover_block.py
- setup-autostart.sh
- kimi_bridge_server/__init__.py
- .dream_count
- .memory_count
- .replay
- setup_autostart_macos.sh
- start.sh
- stop-proxy.sh script
- stop_server.sh script
- .test_cleans_removes_double_spaces
- .test_detects_multiple_throat_clearing
- .test_detects_wh_starters
- .test_cleans_emphasis_crutches
- voice/__init__.py

## God Nodes (most connected - your core abstractions)
1. `_fixture()` - 308 edges
2. `Task` - 221 edges
3. `AgentRunner` - 192 edges
4. `TaskStatus` - 141 edges
5. `ProviderRouter` - 138 edges
6. `TaskStore` - 136 edges
7. `LLMRequest` - 124 edges
8. `TaskSpec` - 113 edges
9. `WorkspaceManager` - 104 edges
10. `ProviderConfig` - 102 edges

## Surprising Connections (you probably didn't know these)
- `test_all_roles_in_enum()` --uses--> `AgentRole`  [INFERRED]
  tests/test_agency.py → agent/agency.py
- `test_new_issue_categories_exist()` --uses--> `IssueCategory`  [INFERRED]
  tests/test_trend_watcher.py → agent/improvement_loop.py
- `test_client_sends_no_identity_headers_when_none_is_attached()` --uses--> `MCPClient`  [INFERRED]
  tests/test_mcp_governance.py → agent/mcp_client.py
- `test_hermes_dispatch_is_a_coroutine()` --uses--> `TrendWatcher`  [INFERRED]
  tests/test_autonomy_hardening_audit.py → agent/trend_watcher.py
- `test_from_env_anthropic_comes_last()` --uses--> `ProviderRouter`  [INFERRED]
  tests/test_failover_order.py → packages/ai/router.py

## Import Cycles
- None detected.

## Communities (1300 total, 116 thin omitted)

### Community 0 - "ExecutionRequest"
Cohesion: 0.02
Nodes (155): get_orchestrator_checkpoint_store(), BoundContext, ClassifyOutput, ExecutionRequest, ExecutionResult, _get_ceo_dispatcher(), get_ceo_fallback_stats(), JudgeVerdict (+147 more)

### Community 1 - "backend/server.py"
Cohesion: 0.02
Nodes (207): admin_seed(), ApiKeyCreate, auth_me(), AuthorizeReposBody, auto_recommend_skills(), brain_failover_status(), _build_auto_skill_guidance(), _classify_complexity() (+199 more)

### Community 2 - "TaskStatus"
Cohesion: 0.02
Nodes (157): autonomy_tick(), Execute ONE pending task synchronously. Called by the cron workflow every 2…, packages/ai/self_heal.py — automatic brain self-healing. When the active brain…, _env_flag(), Read a boolean env var. Accepts 'true'/'1'/'yes' (case-insensitive)., _blocked_retire_age_sec(), _heal_blocked_backlog(), _heal_brain_failover() (+149 more)

### Community 3 - "proxy.py"
Cohesion: 0.03
Nodes (168): get_skill_registry_safe(), Return the global SkillRegistry if set, else None. Used by onboarding and other…, middleware, admin_control(), admin_create_key(), admin_create_user(), admin_delete_user(), admin_list_users() (+160 more)

### Community 4 - "llm/router.py"
Cohesion: 0.03
Nodes (105): int, failover_chat_completion_via_router(), openai_body_from_response(), Any, packages/llm/compat.py — backwards-compatible bridges to the legacy call paths.…, Router-backed implementation of ``packages.ai.failover_client``'s entry point.…, Whether the compat bridges should delegate to ``LLMRouter``. Reads the flag on…, Translate an OpenAI-shaped chat payload into an ``LLMRequest``. Unknown keys… (+97 more)

### Community 5 - "WebsiteScanner"
Cohesion: 0.02
Nodes (124): DetectedSystem, Evidence, OnboardingProgress, Result of a website scan with detected systems and stack inference., Evidence supporting a system detection., Tracks the onboarding progress for a company., Result of a repository scan with detected stack and systems., A business system detected on a company's website or in their stack. (+116 more)

### Community 6 - "CompanyGraphService"
Cohesion: 0.02
Nodes (108): ApprovalPolicy, BusinessSystem, CompanyCreateRequest, CompanyGraph, CompanyGraphSnapshot, CompanyResponse, CompanyUpdateRequest, Connector (+100 more)

### Community 7 - "TaskSpec"
Cohesion: 0.04
Nodes (91): kimi_bridge_runtime_config(), Return Kimi bridge config for external runtimes (Hermes, Goose, Aider). Returns…, AiderAdapter, TaskResult, runtimes/adapters/aider.py — Aider adapter (TIER 3 — specialized). Aider…, Run aider non-interactively via `--message` flag., Adapter for Aider — TIER 3 specialized git-aware code editor., json_safe() (+83 more)

### Community 8 - "api.js"
Cohesion: 0.01
Nodes (36): approveGovernanceRequest(), autoRecommendCompanySkills(), createMcpServer(), createQuickNote(), deleteCompany(), deleteMcpServer(), deleteModel(), denyGovernanceRequest() (+28 more)

### Community 9 - "company_api.py"
Cohesion: 0.03
Nodes (144): ephemeral_ttl_hours(), Async read of the ephemeral TTL (hours) straight from the DB., account_lifecycle(), AccountLifecycleResponse, auto_recommend_skills(), cancel_onboarding(), create_company(), delete_company_endpoint() (+136 more)

### Community 10 - "config.py"
Cohesion: 0.02
Nodes (118): get_budget(), The process-wide budget tracker., _Entry, get_cache(), LRUCache, T, packages/llm/cache.py — layered caching. Five independent layers, each with its…, Live (unexpired) entries — used by the semantic layer's scan. (+110 more)

### Community 11 - "test_llm_router_queue_cache.py"
Cohesion: 0.02
Nodes (105): CacheManager, cosine_similarity(), payload_key(), Any, Exact-match cache key over the fields that change the answer. Routing…, Cosine similarity between two vectors, 0.0 when either is degenerate., Owns every cache layer and the policy for what may enter them., Whether a response to ``request`` may be stored. Deliberately conservative — a… (+97 more)

### Community 12 - "test_llm_router_strategies.py"
Cohesion: 0.04
Nodes (96): count, HealthConfig, Strategy selection and degradation behaviour., Circuit breaker + health tracking thresholds., RoutingConfig, HealthTracker, _Outcome, ProviderHealth (+88 more)

### Community 13 - "Task"
Cohesion: 0.04
Nodes (80): Full task/issue document., Update the updated_at timestamp., Task, _is_outward_facing(), Any, TaskSpec, One-line human explanation of why this task needs human approval. Reads risk…, Best-effort label of who will run this task once approved. Returns… (+72 more)

### Community 14 - "PolicyEngine"
Cohesion: 0.03
Nodes (96): _egress_policy_reason(), agent/web_reach.py — Web Reach: zero-key internet access for agents. Gives…, Return why governance policy blocks *host*, or None. Runs strictly *after* the…, _load(), Import the governance layer once, recording why if it is absent., governance_enabled(), True when the governance layer should run at all. A single global off switch…, AgentIdentity (+88 more)

### Community 15 - "test_ceo_supervision.py"
Cohesion: 0.04
Nodes (93): _harvest_changed_files(), Extract the files a runtime touched. Returns ``(files, reported)``. Adapters…, _backend(), CEOLedger, GoalRecord, _now(), Any, services/ceo_ledger.py — durable record of what the CEO is driving to closure.… (+85 more)

### Community 16 - "_fixture"
Cohesion: 0.02
Nodes (99): parse_event_stream(), ParsedRun, Structured view of one ``--mode json`` event stream., Reduce a ``--mode json`` NDJSON stream to a :class:`ParsedRun`. Kept a module-…, app_client(), _clear_discovered_models(), _clear_response_cache(), client() (+91 more)

### Community 17 - "E2BSandboxSession"
Cohesion: 0.04
Nodes (86): MCPUnavailableError, agent/mcp_client.py — Async MCP client for the mcp-server Docker container.…, Raised when the MCP server is unreachable or the circuit is open., E2BSandboxSession, _inject_token(), maybe_attach_e2b(), Any, services/e2b_sandbox.py — E2B Firecracker micro-VM sandbox session. Implements… (+78 more)

### Community 18 - "SelfHealingAgent"
Cohesion: 0.03
Nodes (79): FailureCategory, heal_signature(), HealingEvent, HealState, _now(), Any, Enum, str (+71 more)

### Community 19 - "test_governance_sandbox.py"
Cohesion: 0.04
Nodes (74): build_docker_run_argv(), detect_backend(), DockerBackend, E2BBackend, load_profiles(), LocalBackend, Any, Path (+66 more)

### Community 20 - "LLMRequest"
Cohesion: 0.04
Nodes (97): ProviderConfig, One configured endpoint. ``kind`` selects the adapter: ``openai`` (any OpenAI-…, Normalise a configured ``kind`` to an adapter key., resolve_kind(), LLMRequest, Cheap character-based token estimate (~4 chars/token). Deliberately dependency-…, A provider-neutral chat request. ``model`` is a *hint*: the router may…, tests/test_anthropic_tool_list_caching.py — C6 extension: tool-list prompt… (+89 more)

### Community 21 - "TaskWorkflowService"
Cohesion: 0.04
Nodes (66): AgentDefinition, AgentStore, Any, field_validator, agents/store.py — Persistent store for user-defined agent configurations.…, CRUD store for AgentDefinition objects. Uses MongoDB when a `db` client is…, Return an agent by ID. If *owner_id* is provided, enforces that the agent…, Delete an agent. Returns True on success, False if not found/unauthorised. (+58 more)

### Community 22 - "BrainConfig"
Cohesion: 0.03
Nodes (91): Call-time resolver for an agent role model id. Delegates to…, _resolve_role_model(), BrainConfig, BrainConfigPatch, BrainConfigStore, default_brain_config(), get_brain_config(), BaseModel (+83 more)

### Community 23 - "test_render_mcp.py"
Cohesion: 0.04
Nodes (51): _as_list(), _coerce_payload(), Any, RuntimeError, packages/integrations/render_mcp.py — Render platform access over MCP. The…, Return tool output as Python data. MCP tool results arrive either as…, Normalise a tool payload into a list of dicts. Upstream tools variously return…, Unwrap a nested envelope such as ``{"service": {...}}`` when present. (+43 more)

### Community 24 - "test_ceo_micromanager.py"
Cohesion: 0.05
Nodes (97): build_subtask_brief(), _coerce_subtasks(), decompose(), _env_flag(), _env_int(), _extract_json_object(), fallback_decomposition(), MicroManagerConfig (+89 more)

### Community 25 - "SQLiteStore"
Cohesion: 0.03
Nodes (56): Create a new company in SQLite., Update a company in SQLite., Delete a company and all associated data from SQLite., List companies from SQLite., Count total companies in SQLite., Reconstruct a Website from a SQLite row, preferring the full JSON blob (which…, Create a new website in SQLite. The full model is stored in ``data`` so scan…, Get a website by ID from SQLite. (+48 more)

### Community 26 - "test_user_research_skill.py"
Cohesion: 0.04
Nodes (57): analyze_qualitative(), analyze_quantitative(), _classify_sentiment(), _extract_keywords(), plan_research(), Any, BaseModel, field_validator (+49 more)

### Community 27 - "test_llm_router_resilience.py"
Cohesion: 0.03
Nodes (75): Backoff policy for retryable failures., RetryConfig, BreakerState, Enum, str, packages/llm/health.py — provider health tracking and circuit breaking. Two…, Test hook — clear all health state., reset() (+67 more)

### Community 28 - "RuntimeCapabilityRegistry"
Cohesion: 0.03
Nodes (40): Any, Return health status for all registered runtimes., Return routing decision audit log (newest first)., Actively wake every sleeping/circuit-open runtime. The default health service…, True if the runtime is healthy enough for the router to select it., Return cached health snapshot for a runtime (sync, non-blocking)., Return all registered runtimes with their cached health status., Return the active routing policy as a plain dict. (+32 more)

### Community 29 - "AnthropicProvider"
Cohesion: 0.04
Nodes (46): AnthropicProvider, Any, AsyncClient, Translate OpenAI-shaped messages into Anthropic's system/turn split., OpenAI carries a tool result as role="tool" with a tool_call_id; Anthropic…, OpenAI puts a tool call alongside the assistant's text; Anthropic needs…, Return the cache_control block appropriate for this provider's TTL setting.…, Add a rolling cache_control breakpoint to the most-recent stable message. In a… (+38 more)

### Community 30 - "tasks/service.py"
Cohesion: 0.04
Nodes (83): add_pr_comment(), _find_existing_pr(), get_branch_sha(), get_default_branch(), _headers(), Any, agent/safe_agency.py — Safe GitHub operations for the workflow engine. All…, Create a pull request. Returns the PR object dict. If a PR already exists for… (+75 more)

### Community 31 - "AgentRunner"
Cohesion: 0.04
Nodes (52): AgentRunner, _check_extra_kwargs(), _enforce_signature(), Any, Path, Raise TypeError if fn's signature drifts from the locked contract (Pydantic…, Raise TypeError on unknown kwarg (runtime extra='forbid' for non-Pydantic…, Append an event to the durable session log if a store is wired in. (+44 more)

### Community 32 - "CEODispatcher"
Cohesion: 0.04
Nodes (79): CEODispatcher, CEOResult, _complexity_rank(), _decompose_into_subtasks(), get_ceo_dispatcher(), _merge_changed_files(), _offload(), Any (+71 more)

### Community 33 - "test_agent_tool_governance.py"
Cohesion: 0.04
Nodes (80): Replace the process-wide store. Tests only., reset_approval_store(), AuditEvent, AuditLog, Any, packages/governance/audit.py — the evidence trail for every governed action.…, Redact secret-shaped substrings, then truncate., One governed action, fully described. Field order follows the… (+72 more)

### Community 34 - "ImprovementLoop"
Cohesion: 0.06
Nodes (65): DetectedIssue, ImprovementLoop, ImprovementLoopState, IssueCategory, IssueSeverity, _now(), Any, Enum (+57 more)

### Community 35 - "MongoDBStore"
Cohesion: 0.04
Nodes (49): MongoDBStore, Any, ObjectId, Prepare a Pydantic model for SQLite storage., Prepare a SQLite row for Pydantic model., Get a company by ID from SQLite., MongoDB implementation of the Company Graph store. Uses Motor (async MongoDB…, Get or create the MongoDB database connection. (+41 more)

### Community 36 - "test_failover_client_shared.py"
Cohesion: 0.06
Nodes (86): BrainFailoverExhausted, failover_chat_completion(), RuntimeError, Every provider in the failover chain failed — the terminal error. Carries the…, Run one chat completion across the brain-failover chain. Tries each healthy…, _free_tier(), _hit_ids(), _many_providers() (+78 more)

### Community 37 - "test_unit8_model_catalog.py"
Cohesion: 0.04
Nodes (75): all_provider_ids(), provider_key_present(), Resolve the model id for a component's role on a provider. Parameters…, Return every provider id recognised by the brain config system. Iterates the…, True when the env var for *provider*'s key is set (or it's Ollama)., resolve_component_model(), CatalogActiveBrain, CatalogMirror (+67 more)

### Community 38 - "MultiAgentSwarm"
Cohesion: 0.05
Nodes (69): AgentConfig, build_agent_specs(), build_swarm(), build_task_specs(), coordinate_v2(), CoordinateRequestV2, CoordinateResponse, Any (+61 more)

### Community 39 - "get_workflow_orchestrator"
Cohesion: 0.04
Nodes (43): Called by APScheduler when a cron fires. Dispatches to the orchestrator. This…, _scheduler_on_fire(), OrchestratorSupervisor, Any, Emit an alert to the activity feed and log., Deterministic supervisor for the orchestrator. Runs as a background coroutine.…, stop_orchestrator_supervisor(), get_workflow_orchestrator() (+35 more)

### Community 40 - "test_model_router.py"
Cohesion: 0.05
Nodes (82): classify_task(), _extract_recent_text(), Any, Task classification from request context. Classifies an incoming request into a…, Concatenate plain text from the last *last_n* messages., Return the most likely task category for this request. Args: messages: OpenAI-…, Reset the singleton and clear the cached model map (test helper)., reset_router() (+74 more)

### Community 41 - "test_mcp_registry.py"
Cohesion: 0.05
Nodes (53): get_mcp_client(), Return the module-level MCPClient. Reads MCP_SERVER_BASE_URL at call time (not…, _internal_configured(), list_specs(), MCPServerSpec, _not_dialable(), _playwright_configured(), _playwright_spec() (+45 more)

### Community 42 - "ToolRegistry"
Cohesion: 0.04
Nodes (42): get_tool_registry(), _infer_parameters_from_func(), Any, Path, Register a tool definition., Decorator to register a function as an agent tool. Usage::…, Remove a tool from the registry. Returns True if removed., Look up a tool by name. (+34 more)

### Community 43 - "PrimeAgentAdapter"
Cohesion: 0.04
Nodes (42): _accumulate_usage(), _assistant_messages(), _child_env(), _iter_events(), _kill_and_reap(), _message_text(), PrimeAgentAdapter, Any (+34 more)

### Community 44 - "services/seo_audit.py"
Cohesion: 0.05
Nodes (53): BaseModel, field_validator, A single occurrence of a check firing on a specific URL., Snapshot of one crawled page with the on-page facts the checks used., Aggregated report row - Screaming Frog CSV compatible., Site-level facts discovered during the crawl., Request to run an SEO/GEO/AIO audit against a website., SeoAuditRequest (+45 more)

### Community 45 - "UserRole"
Cohesion: 0.06
Nodes (58): UserRole, _can_read(), _can_write(), create_secret(), _decrypt(), delete_secret(), _encrypt(), _get_master_key() (+50 more)

### Community 46 - "settings.py"
Cohesion: 0.05
Nodes (44): build_governance_router(), Any, APIRouter, backend/governance_router.py — read and operate the governance layer. Mounted…, Reject non-admin callers. Mirrors the RBAC check used elsewhere in this backend…, _require_admin(), packages.config — single source of truth for all configuration. Every module…, packages/config/settings.py — typed configuration. This is the ONLY module in… (+36 more)

### Community 47 - "resolve_active_brain"
Cohesion: 0.04
Nodes (77): BrainResolution, get_active_brain_sync(), get_provider_role_tags(), _host_is_openai_compatible(), invalidate_brain_cache(), _norm(), _pick_from_records(), Any (+69 more)

### Community 48 - "post"
Cohesion: 0.03
Nodes (72): AgentJobSnapshot, Complete point-in-time view of a job, safe to serialise as API response., Convenience: the canonical text response, whether success or failure., Build a snapshot from an ``AgentJob`` dataclass instance., AgentStatusEntry, AgentStatusResponse, AgentToolCallEntry, BrainTestRequest (+64 more)

### Community 49 - "AgentJobManager"
Cohesion: 0.05
Nodes (40): AgentJob, AgentJobManager, make_isolated_workspace(), _now(), Any, Path, agent/job_manager.py — Async agent job lifecycle manager. Manages agent jobs…, Run a job using the provided runner and update the job's lifecycle, progress,… (+32 more)

### Community 50 - "test_governance_enforcement.py"
Cohesion: 0.05
Nodes (66): BudgetTracker, GovernanceGate, Per-session consumption counters and their ceilings. Ceilings come from the…, Return the name of the first exhausted session-wide limit, or None. Only covers…, Return a reason string if *tool* has hit its per-tool session cap. Checks only…, Holds live session budgets, bounded so it cannot leak. Sessions end without…, The one seam through which governed actions pass., SessionBudget (+58 more)

### Community 51 - "agent/workspace.py"
Cohesion: 0.05
Nodes (46): _get_workspace_lock(), get_workspace_manager(), _hash_component(), _iso_now(), _iso_offset_hours(), _load_workspace(), _parse_iso(), Any (+38 more)

### Community 52 - "test_ceo_router.py"
Cohesion: 0.05
Nodes (57): build_ceo_router(), Any, APIRouter, CEOSupervisor, _env_flag(), _env_int(), Any, services/ceo_supervisor.py — the CEO's 24x7 babysitting loop. Delegation alone… (+49 more)

### Community 53 - "get_registry"
Cohesion: 0.04
Nodes (44): best_model_for(), best_vision_model(), get_registry(), has_image_content(), ModelCapability, Model capability registry. Defines the known local models, their strengths, and…, # NOTE: suspended under US export-control directive as of 2026-06-12., Return model registry, extended with ROUTER_EXTRA_MODELS env entries.… (+36 more)

### Community 54 - "get_runtime_manager"
Cohesion: 0.05
Nodes (70): _enrich_runtimes(), get_decision_log(), get_policy(), get_runtime(), list_runtimes(), PolicyUpdateBody, Any, BaseModel (+62 more)

### Community 55 - "FetchResult"
Cohesion: 0.05
Nodes (31): MockTransport, AsyncBaseTransport, browser_backend_available(), BrowserFetcher, FetchResult, HttpxFetcher, looks_blocked(), make_fetcher() (+23 more)

### Community 56 - "test_sam_livekit.py"
Cohesion: 0.04
Nodes (62): auth_headers(), livekit_env(), no_livekit_env(), _normalize_dockerfile(), parametrize, tests/test_sam_livekit.py — SAM realtime voice (LiveKit) integration. Covers: -…, Empty key/secret/identity/room must raise ValueError., SAM_LLM_* env vars must override the NVIDIA defaults (Hermes/proxy routing). (+54 more)

### Community 57 - "Agency"
Cohesion: 0.05
Nodes (49): Agency, AgencyCycleResult, AgentDirective, AgentRole, _build_ceo_prompt(), _build_quick_note_instruction(), _close_github_issue(), _collect_recent_git_context() (+41 more)

### Community 58 - "AgentSessionStore"
Cohesion: 0.06
Nodes (43): Agent subsystem — planner / executor / verifier loop., AgentEvent, AgentRunRequest, AgentSession, AgentSessionCreateRequest, AgentSessionMessage, AgentStep, _known_tool_names() (+35 more)

### Community 59 - "test_agent_runner.py"
Cohesion: 0.04
Nodes (72): AgentPhaseError, _note_phase_end(), _note_phase_start(), Exception, Raised when a named agent phase (planning, verification, etc.) fails., Log start/elapsed for one phase of the plan/execute/verify loop. A task that…, Open a tracked phase, returning the token that closes it. Never raises., Close the tracked phase *token* opened above. Never raises. (+64 more)

### Community 60 - "lifespan"
Cohesion: 0.04
Nodes (57): all_settings(), _as_bool(), _as_int(), ephemeral_ttl_hours_cached(), get_setting(), _maybe_schedule_refresh(), onboarding_gate_enabled(), onboarding_gate_enabled_cached() (+49 more)

### Community 61 - "test_webui_provider_priority.py"
Cohesion: 0.07
Nodes (52): AdminIdentity, _load_rich_policy(), Return the persisted rich UI policy (pools + policy + triggers), or {}., _fake_user_auth(), Path, test_admin_can_create_anthropic_provider_via_webui_admin_api(), test_admin_can_create_provider_via_webui_admin_api(), test_ui_providers_and_workspaces_use_app_state() (+44 more)

### Community 62 - "ChatHistoryStore"
Cohesion: 0.04
Nodes (29): ChatHistoryStore, get_chat_history(), Any, Connection, Delete a session and all its messages. Returns True if deleted., List sessions ordered by most recently updated., Return total session and message counts., Append a message to the session. Returns the message's sequence number.… (+21 more)

### Community 63 - "api.ts"
Cohesion: 0.07
Nodes (61): adminBootstrap(), adminCreateProvider(), adminCreateWorkspace(), adminDeleteProvider(), adminDeleteWorkspace(), adminGetBrainPolicy(), adminGetProviderRoleTags(), adminHeaders() (+53 more)

### Community 64 - "AgentSwarm"
Cohesion: 0.06
Nodes (40): agents/__init__.py — CRISPY multi-agent coding system., AgentProfile, _catalog_defaults(), _catalog_provider(), _get_defaults(), load_all_profiles(), make_architect_profile(), make_coder_profile() (+32 more)

### Community 65 - "seo_portfolio_bridge.py"
Cohesion: 0.05
Nodes (45): CapacityAllocation, Enum, Agentic Portfolio Management — initiative prioritisation, capacity allocation,…, Result of fitting initiatives into a fixed capacity by WSJF priority., Total job size of initiatives that fit within capacity., Unused capacity after committing the selected initiatives., Fraction of capacity consumed (0.0–1.0)., Roadmap placement for an initiative (Now/Next/Later planning). (+37 more)

### Community 66 - "detector.py"
Cohesion: 0.06
Nodes (46): batch_compatibility(), check_model_compatibility(), _detect_amd_gpus(), _detect_apple_silicon_gpu(), _detect_cpu(), detect_hardware(), _detect_intel_arc_gpu(), _detect_nvidia_gpus() (+38 more)

### Community 67 - "BrainWatchdog"
Cohesion: 0.04
Nodes (50): emit_agency_observation(), Record an agency platform operation in Langfuse. Unlike…, Any, One-shot self-healing pass. 1. Checks if the active brain provider is in a…, self_heal_brain_and_unblock_tasks(), BrainWatchdog, get_watchdog(), _is_provider_actually_available() (+42 more)

### Community 68 - "FeatureMatrix"
Cohesion: 0.05
Nodes (17): FeatureMatrix, Central support matrix — single source of truth. Loads the canonical feature…, Return True if the feature is enabled and not disabled., Return a warning string for beta/experimental features, or None., Render the matrix as a Markdown table for docs., Integration test: admin endpoint returns feature matrix JSON., TestAdminVisibility, TestConfigOverrides (+9 more)

### Community 69 - "setup/api.py"
Cohesion: 0.07
Nodes (65): is_user_onboarding_allowed(), Return True if this user may run the onboarding wizard. Resolution order: 1. If…, complete_wizard(), _delete_wizard_state(), detect_configured_providers(), detect_hardware_for_wizard(), detect_models_for_wizard(), _detect_ollama_models() (+57 more)

### Community 70 - "test_cost_aware_routing_eval.py"
Cohesion: 0.06
Nodes (56): Cost-aware routing evaluation harness. Measures the cost-aware subagent routing…, main(), CLI for the cost-aware routing evaluation. python -m evals.cost_aware_routing…, ModelPrice, Model pricing for the cost-aware routing evaluation. Rates are first-party…, Per-token price for one model, in USD per 1,000,000 tokens., Override the price for a tier (e.g. a discounted or partner rate)., USD cost of one model call. Raises KeyError on an unknown tier. (+48 more)

### Community 71 - "V5App.jsx"
Cohesion: 0.04
Nodes (40): API, getActivity(), HubTabs(), Spinner(), ActivationGate(), activityToAlert(), AlertsBell(), priorityConfig (+32 more)

### Community 72 - "test_model_catalog.py"
Cohesion: 0.05
Nodes (67): _build_base_url_env_from_yaml(), _build_candidates_from_yaml(), _build_default_base_url_from_yaml(), _build_display_names_from_yaml(), _build_key_env_from_yaml(), _build_presets_from_yaml(), _build_tier_from_yaml(), get_provider_candidates() (+59 more)

### Community 73 - "CompanyGraphStore"
Cohesion: 0.03
Nodes (34): requires_db, Initialize the service. Args: store: Optional CompanyGraphStore instance. If…, CompanyGraphStore, Delete a company and all its associated data., List companies with optional filtering., Count total companies in the store., Create a new company graph., Get the complete company graph for a company. (+26 more)

### Community 74 - "services/background.py"
Cohesion: 0.05
Nodes (60): get_improvement_loop(), get_trend_watcher(), agent/trend_watcher.py — Internet-connected AI trend intelligence. Fetches from…, set_trend_watcher(), _await_hermes_ready(), _env_float(), _env_on(), Any (+52 more)

### Community 75 - "HybridSystem"
Cohesion: 0.05
Nodes (29): ConfidenceLevel, DeterministicEngine, HybridSystem, LLMReasoner, Any, Enum, str, Hybrid AI — combine deterministic rule engines with LLM reasoning. Implements a… (+21 more)

### Community 76 - "ResearchTask"
Cohesion: 0.06
Nodes (44): AgentRole, Enum, str, Multi-Agent Research Coordinator — orchestrate a team of specialized research…, Run the task and return it (mutated) with status set., Coordinates a multi-agent research workflow. Workflow: 1. plan(question) → list…, Decompose a research question into a default DAG. Default plan: web → docs…, Round-robin pick within a role (least-loaded first). (+36 more)

### Community 77 - "RenderOpsMonitor"
Cohesion: 0.06
Nodes (30): BaseModel, Response shape of ``GET /api/render/ops/status``. Declared here rather than in…, RenderOpsStatus, One deploy, normalised from whatever shape the tool returned., RenderDeploy, Polls Render for platform-level failures and files them as issues., Snapshot for ``/api/render/ops/status`` and the dashboard. ``self_heal_ready``…, True when a filed finding will actually be scheduled as a fix. Detection and… (+22 more)

### Community 78 - "TestClient"
Cohesion: 0.10
Nodes (29): bare_repo(), _call(), _data(), git_config_env(), _is_error(), mcp_workspace_root(), Path, skipif (+21 more)

### Community 79 - "test_ai_insights.py"
Cohesion: 0.05
Nodes (49): AIToolMetrics, build_report(), EngagementMetrics, PerformanceAnalytics, datetime, Enum, str, AI-Assisted Engineering Insights — track AI tool usage, engagement, and… (+41 more)

### Community 80 - "test_startup_warmup.py"
Cohesion: 0.04
Nodes (60): _bootstrap_within_budget(), _create_bootstrap_indexes(), ensure_bootstrap(), Await one warm-up step, deferring it to the background if it overruns.…, The task store the background services should use, wiring it if needed.…, Point the feature stores at the shared database connection. Deliberately…, Create every boot index concurrently rather than one round-trip at a time.…, Idempotent bootstrap for indexes + seeded admin/providers. FastAPI startup… (+52 more)

### Community 81 - "get_scheduler"
Cohesion: 0.05
Nodes (42): legacy_scheduler_delete(), legacy_scheduler_get(), legacy_scheduler_trigger(), get_scheduler(), agent/scheduler.py — Scheduled Agent Jobs Cron-based job scheduler. Each job…, set_scheduler(), create_schedule(), delete_schedule() (+34 more)

### Community 82 - "test_repo_connection.py"
Cohesion: 0.06
Nodes (49): DeliveryPolicy, How code lands on a repo's default branch (detected, GitHub-only for now). The…, A company's connection to a code repository (GitHub-only this pass). URL-only…, RepoConnection, attach_repo_connection(), build_repo_connection(), decide_merge(), detect_delivery_policy() (+41 more)

### Community 83 - "test_procedural_memory.py"
Cohesion: 0.05
Nodes (26): get_procedural_memory(), _overlap_score(), ProceduralMemoryStore, ProceduralRecord, Any, agent/procedural_memory.py — Skill/Procedural Memory for the agent loop (★4).…, Store a successful step pattern and return its record id. Duplicate step…, Return up to *limit* stored patterns relevant to *query*. Relevance is scored… (+18 more)

### Community 84 - "CoworkSession"
Cohesion: 0.05
Nodes (21): ContributorState, CoworkSession, Any, Enum, str, Claude Cowork — shared AI coding sessions with real-time sync. Enables multiple…, A shared AI coding session with multiple human contributors. Manages turn-…, Request editing control. Returns True if granted. Grant rules: - Host can… (+13 more)

### Community 85 - "tasks/api.py"
Cohesion: 0.11
Nodes (62): BackgroundTasks, add_comment(), approve_checkpoint(), approve_execution(), clarify_task(), create_task(), _current_user(), delete_task() (+54 more)

### Community 86 - "App.js"
Cohesion: 0.05
Nodes (32): getAccountLifecycle(), getDefaultBackendUrl(), getMe(), login(), logout(), App(), AppRoutes(), ProtectedRoute() (+24 more)

### Community 87 - "test_llm_router_e2e.py"
Cohesion: 0.06
Nodes (52): get_tracker(), The process-wide health tracker., get_metrics(), The process-wide metrics registry., _ok(), parametrize, End-to-end routing against mock providers (ADR-008). These are the tests that…, A router wired to three mock providers, with all singletons isolated. (+44 more)

### Community 88 - "TestClient"
Cohesion: 0.08
Nodes (43): _auth_headers(), _build_agent_http_mock(), _exec(), _fake_request(), _mcp_tool_response(), _multi_step_plan(), _nim_post_factory(), _one_step_plan() (+35 more)

### Community 89 - "ArtifactStore"
Cohesion: 0.06
Nodes (26): TestTeamSummary, Path, tests/test_artifact_store.py — Unit tests for workflow/artifact_store.py., Verify artifacts that are stored as JSON (e.g., CheckRun results)., Writing the same (run_id, name) twice should update, not duplicate., store(), TestArtifactStoreDeletion, TestArtifactStoreJSONArtifact (+18 more)

### Community 90 - "direct_chat.py"
Cohesion: 0.07
Nodes (57): Any, Translate technical preflight issues into a conversational assistant reply., translate_error_to_conversational(), AcceptedJob, AgentJobEnvelope, CompletedJob, DirectChatState, FailedJob (+49 more)

### Community 91 - "FreeBuffAgent"
Cohesion: 0.05
Nodes (49): free_nvidia_models(), FreeBuffAgent, _nvidia_api_key(), Return the curated list of free NVIDIA NIM models FreeBuff may use., Codebuff-style coding agent pinned to free NVIDIA NIM models. FreeBuff is a…, List the free NVIDIA NIM models a user may pick (e.g. via Telegram)., True when *model* is in the curated free NVIDIA NIM set., Coerce *requested* to a free NVIDIA model. Returns *requested* when it is… (+41 more)

### Community 92 - "test_brain_config_api.py"
Cohesion: 0.05
Nodes (49): provider_api_key(), Return the live API key for *provider* (env-only — never persisted)., _describe_http_status(), probe_model_liveness(), _probe_ollama(), _probe_openai_compat(), ProbeResult, BaseModel (+41 more)

### Community 93 - "resolve_e2b_config"
Cohesion: 0.05
Nodes (55): Available iff config resolves AND the SDK is importable. Never raises — a…, e2b_status(), Return the E2B sandbox integration status for the ProvidersScreen badge. Does…, e2b_enabled(), E2BConfig, _env_falsy(), _env_truthy(), is_e2b_sdk_importable() (+47 more)

### Community 94 - "telegram_bot.py"
Cohesion: 0.07
Nodes (60): get_decisions_store(), Process-wide DecisionsStore singleton (resettable via db_path arg)., Return a Markdown-v1-safe preview string under ``max_chars``. Used by the…, sanitize_paste_for_preview(), _admin_headers(), _answer_callback(), _api_headers(), _check_rate_limit() (+52 more)

### Community 95 - "WorkflowEngine"
Cohesion: 0.07
Nodes (53): approve(), build(), cancel(), _engine(), get_agent_team(), get_artifact_content(), get_events(), get_run() (+45 more)

### Community 96 - "BackgroundAgent"
Cohesion: 0.06
Nodes (41): BackgroundAgent, BackgroundTask, _now(), Any, agent/background.py — Background Agent An always-on worker thread that…, Enqueue *task* for processing. Returns the task (with task_id set)., Convenience: create a task and submit it in one call., Real handler — dispatches through AgentRunner when available. HARDENED (PR… (+33 more)

### Community 97 - "test_web_reach.py"
Cohesion: 0.07
Nodes (49): Register the Web Reach capability (agent/web_reach.py): zero-key internet…, _register_web_reach_tools(), get_web_reach(), _load_script_module(), Any, ModuleType, Response, Dynamically load a pure-stdlib helper module from .github/scripts/. Returns… (+41 more)

### Community 98 - "TokenBudget"
Cohesion: 0.05
Nodes (31): BudgetExceededError, BudgetUsage, Any, Exception, agent/token_budget.py — Per-Session Token Spend Caps Track token usage per…, Raise :class:`BudgetExceededError` if the session has exceeded its cap., Reset usage counters for *session_id* (cap is preserved)., Reset token counters for all sessions (caps preserved). Called at the start of… (+23 more)

### Community 99 - "FinancialMetrics"
Cohesion: 0.06
Nodes (46): BudgetOptimizer, CostLine, FinancialAgent, FinancialMetrics, Enum, str, Agentic CFO — autonomous financial analyst for AI infrastructure spend.…, Reallocate budget across cost lines to maximize total ROI under a fixed budget… (+38 more)

### Community 100 - "LogWatcher"
Cohesion: 0.05
Nodes (33): _auto_file_enabled(), ErrorFingerprint, LogEntry, LogWatcher, log_watcher.py — Automated log monitoring agent. Watches log files, detects…, A single error entry extracted from a log file., Generates stable fingerprints for error deduplication., Create a hash from error type, file, and normalized message pattern. (+25 more)

### Community 101 - "Agent"
Cohesion: 0.05
Nodes (24): Agent, Grab Multi-Agent Support — Agent and TeamCoordinator with capability matching.…, Release a task from an agent., List all currently available agents., List agents with a capability, ordered by load., Average load across all team members., Number of agents in the team., An agent with capabilities and workload tracking. (+16 more)

### Community 102 - "test_issue_intake.py"
Cohesion: 0.07
Nodes (54): _autonomy_bg_cycle(), Background CEO cycle + task dispatch. Runs fire-and-forget., _capability_tags(), create_task_from_oldest_open_issue(), intake_issue(), _issue_labels(), issue_source_id(), map_issue_to_task() (+46 more)

### Community 103 - "audit"
Cohesion: 0.06
Nodes (26): audit(), get_audit_log(), get_user_role(), has_permission(), is_admin(), is_power_user_or_above(), Any, Request (+18 more)

### Community 104 - "Settings"
Cohesion: 0.04
Nodes (34): _env_int(), _get_settings(), Read an int env var, falling back to *default* on a missing/bad value. Never…, Typed configuration loaded from environment variables., When True, the governance layer evaluates and audits agent actions. This is…, When True, approval-gated actions self-approve. Local dev only., ``RENDER_SERVICE_IDS`` split into a clean list (empty when unset)., True when there is both an API key and an endpoint to reach. (+26 more)

### Community 105 - "Page"
Cohesion: 0.05
Nodes (38): _login_api(), main(), _navigate_auth_callback(), _navigate_logged_out(), Page, Navigate directly to the AuthCallback page with query params., Social login buttons on the LoginPage., Verify the login page renders. (+30 more)

### Community 106 - "WorkspaceManager"
Cohesion: 0.05
Nodes (20): Agent jobs created with workspace integration should have a workspace_path…, Only expired workspaces (past retention TTL) are cleaned up., Two threads creating the same session/job should not corrupt state., TestConcurrency, TestCrossSessionIsolation, TestWorkspaceCleanup, TestWorkspaceLifecycle, TestWorkspaceManifest (+12 more)

### Community 107 - "portfolio_intelligence.py"
Cohesion: 0.06
Nodes (51): _bullets(), generate_backlog_retro(), generate_standup(), plan_next_sprint(), Agentic Agile — autonomous ceremonies (standup, retro, sprint planning). Where…, Render a :class:`Retrospective` as a markdown section., Derive a retrospective from the task tracker when no sprint is active. DONE /…, The result of allocating portfolio capacity into a new sprint. (+43 more)

### Community 108 - "AgileSprint"
Cohesion: 0.05
Nodes (23): AgileSprint, An agile sprint containing user stories., Add a user story to the sprint., Remove a user story from the sprint., Total story points in the sprint., Completed story points., Return completed points history for burndown chart., Number of stories in the sprint. (+15 more)

### Community 109 - "test_provider_router.py"
Cohesion: 0.05
Nodes (54): _acquire_provider_probe(), extract_openai_text(), _normalize_nvidia_base_url(), _openai_url(), Try to acquire a distributed probe lock for *provider_id*. Returns True if this…, Release the probe lock for *provider_id*., Normalize NVIDIA base URLs to avoid double /v1 when openai_compat_url appends…, _release_provider_probe() (+46 more)

### Community 110 - "ai_runner.py"
Cohesion: 0.07
Nodes (53): append_checkpoint(), _build_claude_command(), cmd_audit(), cmd_changelog_check(), cmd_logs(), cmd_manifest(), cmd_resume(), cmd_start() (+45 more)

### Community 111 - "test_sqlite_store.py"
Cohesion: 0.06
Nodes (58): asyncio, tests/test_sqlite_store.py — Unit tests for the SQLite storage adapter. These…, The exact query shape backend/server.py's provider "Set default" uses: clear…, Unfiltered count uses the SELECT COUNT(*) fast path and must match the number…, estimated_document_count mirrors an unfiltered count_documents., db['tasks'] must work like db.tasks (motor exposes both)., TaskStore(db=SQLiteStore) must not raise 'not subscriptable'. This is the exact…, B608 guard: _Collection.__init__ must reject names outside _COLLECTIONS.… (+50 more)

### Community 112 - "BrowserSession"
Cohesion: 0.06
Nodes (33): browse_page(), BrowserAction, BrowserSession, _not_started(), PageState, Any, agent/browser.py — Browser Automation Controls a real browser via Playwright so…, True if browser automation is enabled and Playwright is importable. (+25 more)

### Community 113 - "UserMemoryStore"
Cohesion: 0.06
Nodes (31): _now(), Any, Path, agent/memory.py — Session Memory Snapshots Persists agent session state to disk…, Save and restore agent state snapshots to/from a local directory. Usage:: mem =…, Persist *state* to disk under *session_id*. Returns the file path., Load a saved snapshot. Returns the state dict or *None* if absent., Return metadata for all saved snapshots (session_id, saved_at, path). (+23 more)

### Community 114 - "LLMRouter"
Cohesion: 0.06
Nodes (29): Attempt, text_key(), Read the environment variables named in ``env_names`` into a key list. Order is…, resolve_keys(), LLMRouter, Any, AsyncClient, BaseException (+21 more)

### Community 115 - "test_integration_c4_c5_c6_d3.py"
Cohesion: 0.06
Nodes (36): get_current_trace_id(), get_tracer(), langfuse_metadata_with_trace(), _NoOpSpan, _NoOpTracer, otel_middleware_factory(), otel_status_error(), otel_status_ok() (+28 more)

### Community 116 - "KeyStore"
Cohesion: 0.07
Nodes (38): Browser admin UI for login, service control, key management, and diagnostics., Update or append a KEY=value line in the .env file., register_admin_gui(), _save_env_var(), Backward-compatibility shim — use scripts/generate_api_key.py instead. This…, _check_rate_limit(), default_keys_path(), issue_new_api_key() (+30 more)

### Community 117 - "failover_client.py"
Cohesion: 0.05
Nodes (53): _auto_disable(), _describe_registry(), _disabled_ids(), FailoverResult, _is_billing_refusal(), _is_ollama(), _key_pool(), _log_exhaustion() (+45 more)

### Community 118 - "_scanner"
Cohesion: 0.06
Nodes (27): _is_blocked_host(), Cheap (no-DNS) SSRF check for headless-browser subrequests. A rendered page's…, Tests for the scanner's headless-render fallback (JS-rendered / bot-protected…, The scan flow must invoke the render fallback when static detection is empty…, BuiltWith-style off-site identification: a CNAME chain that points at a known…, A scan must never hang past its wall-clock budget — a slow/blocked domain has…, Last-resort fallback that asks builtwith.com what it already knows about a…, Replace curl_cffi's AsyncSession.get with a canned response. (+19 more)

### Community 119 - "get_self_healing_agent"
Cohesion: 0.07
Nodes (45): _dispatch_async(), _ErrorCaptureHandler, get_log_monitor(), LogMonitor, _note_recurrence(), Any, LogRecord, agent/log_monitor.py — Application Log Monitor Captures ERROR/CRITICAL log… (+37 more)

### Community 120 - "Command"
Cohesion: 0.06
Nodes (22): Command, CommandCategory, CommandDispatcher, Enum, SuperClaude Slash Commands — CommandDispatcher with registration, role gating,…, Parse and execute a slash command from raw text. Args: text: Raw command text,…, Return all enabled commands in a given category., Return all registered commands. (+14 more)

### Community 121 - "test_context_rulebook.py"
Cohesion: 0.06
Nodes (53): Module, stmt, _bound_names(), _good_result(), _guard_statements(), _load(), ModuleType, parametrize (+45 more)

### Community 122 - "Company"
Cohesion: 0.05
Nodes (21): BusinessCategory, Company, Any, field_validator, The core company entity - root of the Company Graph., Coerce unrecognised system_type values to 'custom' so the model never crashes…, Company, Get a company by ID. Args: company_id: Company ID Returns: Company instance or… (+13 more)

### Community 123 - "frontend/package.json"
Cohesion: 0.04
Nodes (53): browserslist, development, production, dependencies, axios, fast-uri, livekit-client, lucide-react (+45 more)

### Community 124 - "run_task"
Cohesion: 0.05
Nodes (38): Resolve the model id to force for a code-execution run, or ``None``. Returns…, resolve_coding_model_preference(), _check_auth(), health(), Any, BaseModel, get, post (+30 more)

### Community 125 - "ProviderConfig"
Cohesion: 0.06
Nodes (38): provider_access_tier(), _provider_field(), provider_sort_key(), ProviderConfig, Regression tests for the agent loop's multi-provider failover wire format.…, The pieces the failover loop assembles for an Anthropic-native provider., TestAnthropicRequestShape, Tests that verify the exact provider priority ordering. (+30 more)

### Community 126 - "diagnostics.py"
Cohesion: 0.06
Nodes (48): _check_background_liveness(), _check_ci_parity(), _check_company_graph(), _check_disk(), _check_event_log_integrity(), _check_feature_matrix(), _check_github_readiness(), _check_ollama() (+40 more)

### Community 127 - "InferenceCache"
Cohesion: 0.05
Nodes (27): CachedLLMClient, Any, Cached LLM Client wrapper. Drop-in wrapper around any LLM API call that…, Return performance metrics for this client instance., Try to extract token count from various response formats., Wraps an LLM call function with inference caching. Usage: from agent.cached_llm…, Execute an LLM completion, using cache when available. Args: model: Model…, CacheEntry (+19 more)

### Community 128 - "CheckpointStore"
Cohesion: 0.09
Nodes (27): Checkpoint, checkpoint_agent_state(), _checkpointing_enabled(), CheckpointStore, cleanup_checkpoints(), _get_checkpoint_store(), Any, Path (+19 more)

### Community 129 - "test_trend_scoping.py"
Cohesion: 0.09
Nodes (51): Issue title: the failure mode plus how hard it is recurring., _company_attr(), company_stack_tags(), extract_stack_tags(), fan_out_trend(), fan_out_trends(), is_code_change_trend(), map_trend_to_company_task() (+43 more)

### Community 130 - "RepowiseIntelligence"
Cohesion: 0.06
Nodes (27): Any, Path, Build symbol-level dependency graph for Python files., Build git intelligence: hotspots, ownership, co-change pairs., Run a git command and return stdout as string., Compute cyclomatic complexity for Python files. Returns 0 for non-Python files…, Extract docstrings and store as documentation., Get the latest commit hash. (+19 more)

### Community 131 - "FeatureMaturity"
Cohesion: 0.06
Nodes (32): __init__.py — Feature flag/matrix package., FeatureMaturity, get_feature_matrix(), Enum, str, features/matrix.py — Feature maturity tiers and support matrix. Single source…, Feature maturity classification., Return the global FeatureMatrix singleton. (+24 more)

### Community 132 - "seo_api.py"
Cohesion: 0.06
Nodes (52): build_seo_roadmap(), delegate_seo_findings(), _expire_stale_pending_report(), export_seo_audit(), get_seo_audit(), list_seo_audits(), plan_seo_sprint(), BaseModel (+44 more)

### Community 133 - "OnboardingScreen.jsx"
Cohesion: 0.05
Nodes (35): createCompany(), delegateSeoFindings(), getCompany(), getOnboardingProgress(), getSeoAudit(), listSeoAudits(), listSpecialists(), runSeoAudit() (+27 more)

### Community 134 - "test_governance_api.py"
Cohesion: 0.06
Nodes (50): get_approval_store(), Replace the process-wide gate. Tests only., reset_gate(), _client(), parametrize, TestClient, Tests for the governance HTTP surface and the AgentRunner integration. The…, Policy is a git-reviewed file. An HTTP mutation route would make "who changed… (+42 more)

### Community 135 - "_cfg"
Cohesion: 0.06
Nodes (18): _cfg(), tests/test_daily_automation_2026_08_25.py — Daily automation tests…, Mythos-class models should be priced above Opus 5., Fable 5 is more capable than Opus 5, so lower priority number., Verify the claude-mythos-5 entry in config/llm/models.yaml., Same underlying model — pricing must be identical., Cross-check that models known to the router registry are in models.yaml., Paid Anthropic models must have a non-zero output cost. (+10 more)

### Community 136 - "ReactScratchpad"
Cohesion: 0.06
Nodes (22): Declarative configuration for a specialized sub-agent role. Each sub-agent gets…, SubAgentConfig, build_react_prompt(), parse_react_response(), Any, Parse a ReAct-format response into structured components. Intended caller:…, Structured scratchpad that accumulates across tool calls within a step. Each…, Record a reasoning step before taking action. (+14 more)

### Community 137 - "_StubProvider"
Cohesion: 0.09
Nodes (28): _disable_unless_key_serves_other_models(), _models_to_try(), Order the models to attempt on *provider*, correcting a stale catalogue. Cache-…, Auto-disable *provider*, unless its key demonstrably serves other models. "No…, attempted(), Return every model of *provider_id* tried so far by a failed round., _mock_get(), _ok() (+20 more)

### Community 138 - "test_response_cache.py"
Cohesion: 0.11
Nodes (50): _cache_key(), cache_stats(), clear_cache(), get_cached(), is_cacheable(), put_cached(), Any, packages/ai/response_cache.py — LRU+TTL in-memory response cache for the… (+42 more)

### Community 139 - "E2BAdapter"
Cohesion: 0.06
Nodes (37): E2BAdapter, Any, TaskResult, Declare ``E2B_API_KEY`` as a required env dependency. The base ``preflight``…, Execute a task inside a fresh E2B sandbox. Flow: 1. Open an…, Run ``pytest`` inside the sandbox. Returns ``(output, passed)``.…, Runtime adapter that executes tasks inside an E2B sandbox. Activation:…, _FakeAsyncSandboxClass (+29 more)

### Community 140 - "_step"
Cohesion: 0.06
Nodes (22): _job(), parametrize, Path, quick_note(), The autonomous pipeline must not treat "I could not tell" as "yes". Every…, `--missing-ok` is correct for an unplanned issue and wrong otherwise., `continue-on-error: true` means a crash must be its own state., Waiting is not reviewing. (+14 more)

### Community 141 - "test_slop_gate.py"
Cohesion: 0.06
Nodes (47): _extract_mentioned_paths(), Autonomous agent: fetch oldest open issue, generate implementation, create PR.…, Pick the auto-PR model from the recommended free-cloud chain by key. Mirrors…, Extract plausible file paths from issue text., Read existing files for codebase context (max 8000 chars total)., _read_grounding_files(), _select_brain(), tool_write_file() (+39 more)

### Community 142 - "SpecialistService"
Cohesion: 0.05
Nodes (30): Any, SpecialistFamily, SystemType, Auto-provision specialists based on detected system types. Args: company_id:…, Deprovision (delete) a specialist. Args: specialist_id: Specialist ID Returns:…, Enable a specialist. Args: specialist_id: Specialist ID Returns: Updated…, Disable a specialist. Args: specialist_id: Specialist ID reason: Reason for…, Get specialists that can handle a task with given capabilities. Args:… (+22 more)

### Community 143 - "test_trend_watcher.py"
Cohesion: 0.07
Nodes (33): _FakeClient, _FakeResp, asyncio, Tests for agent/trend_watcher.py, Ensure expanded keyword set covers key new categories., A release is scored by its notes, never the old blanket 0.95 that let five…, Only the newest release is force-surfaced; older routine patch releases in the…, A routine latest release still surfaces (our niche) but is informational — not… (+25 more)

### Community 144 - "PortfolioManager"
Cohesion: 0.05
Nodes (24): PortfolioManager, PortfolioMetrics, Aggregate metrics across the whole portfolio., Manages a portfolio of initiatives with WSJF prioritisation and roadmapping., Remove an initiative from the portfolio., Number of initiatives in the portfolio., Return initiatives sorted by WSJF (highest first). Cancelled initiatives are…, Greedily fill ``capacity`` (in job-size units) by WSJF priority. Walks the… (+16 more)

### Community 145 - "useSafeData"
Cohesion: 0.06
Nodes (33): createAgent(), createSchedule(), pauseSchedule(), resumeSchedule(), triggerSchedule(), useSafeData(), AgentCard(), AgentsScreen() (+25 more)

### Community 146 - "ProviderRouter"
Cohesion: 0.08
Nodes (23): CommercialFallbackRequiredError, _get_director(), _normalized_provider_type(), ProviderAttempt, ProviderFallbackError, ProviderRouter, Any, Response (+15 more)

### Community 147 - "claim"
Cohesion: 0.07
Nodes (28): claim(), cooldown_clear(), cooldown_get(), cooldown_set(), _get_backend(), incr_window(), Shared-state abstraction — in-memory (default) and Redis backends. Provides…, Reset the singleton (for tests). (+20 more)

### Community 148 - "call_llm"
Cohesion: 0.05
Nodes (48): get_sam(), agent/sam.py — SAM Voice Agent (System Autonomy Manager) SAM is the voice-…, _agent_timeout_fallback_response(), _build_direct_chat_schedule_suggestion(), _build_direct_chat_tags(), _build_direct_chat_task_suggestion(), _build_provider_router(), _builtin_provider_records() (+40 more)

### Community 149 - "TestHarnessAdapter"
Cohesion: 0.05
Nodes (27): get_harness_adapter(), harness_active(), harness_catalog(), harness_session_close(), harness_session_start(), HarnessSessionBody, HarnessSessionCloseBody, Return orchestrator queue depth, active runs, and supervisor state (#522). (+19 more)

### Community 150 - "persist_plan_spec"
Cohesion: 0.07
Nodes (37): build_spec_router(), Any, APIRouter, backend/spec_router.py — review/approve persisted plan specifications. Surfaces…, await_spec_approval(), _db(), _flag(), get_spec() (+29 more)

### Community 151 - "TestEstimateTokensForMessages"
Cohesion: 0.05
Nodes (18): _estimate_tokens_for_messages(), _normalize_anthropic_output_format(), Estimate input token count for an Anthropic-format message list. Uses a simple…, Translate Anthropic ``output_format`` into an Ollama ``format`` field. Modifies…, Daily automation tests — 2026-05-15 Covers three features implemented in this…, Integration tests for POST /v1/messages/count_tokens., Unit tests for extended thinking detection in handle_anthropic_messages., When thinking.type == enabled, routing should use agent_plan endpoint type. (+10 more)

### Community 152 - "ScheduledJob"
Cohesion: 0.06
Nodes (22): _now(), Any, Reconstruct a ScheduledJob from its as_dict() output., Register a new job. Returns the created :class:`ScheduledJob`.…, Fire a job immediately (webhook / manual trigger)., Update the display name of a job., Enable or disable a job without deleting it., Return the running event loop, or ``None`` when called synchronously. Used so… (+14 more)

### Community 153 - "ContextWindowManager"
Cohesion: 0.08
Nodes (21): ContextWindowManager, get_context_window_manager(), Any, Enum, Return True if the estimated tokens exceed the model's context limit., Truncate messages to fit within the model's context window. Args: messages:…, Return the context window size for a model. Looks up the model in the…, Estimate token count for a list of messages. Uses a character-based heuristic… (+13 more)

### Community 154 - "MCPClient"
Cohesion: 0.07
Nodes (20): MCPClient, Any, RuntimeError, Thin async MCP client with open/close circuit breaker. Thread-safe only within…, Full URL of the JSON-RPC endpoint this client posts to., Build the request headers shared by ``_rpc`` and ``notify``. ``Accept`` lists…, Propagate the calling agent's identity across the process boundary. The MCP…, Attach the agent identity whose actions this client executes. (+12 more)

### Community 155 - "test_portfolio_intake.py"
Cohesion: 0.07
Nodes (39): fetch_research_alerts(), Run an async coroutine from sync code, safe even inside a running loop.…, Best-effort fetch of trend alerts. Returns [] if offline or unavailable., _run_coro_sync(), Weighted Shortest Job First score — higher schedules sooner., map_initiative_to_task(), materialize_committed(), _portfolio_materialize_enabled() (+31 more)

### Community 156 - "BudgetTracker"
Cohesion: 0.07
Nodes (30): AlertHandler, BudgetTracker, Counter, _Dimensions, _month(), Any, packages/llm/budget.py — token and cost accounting with spend alerts. Tracks…, Register a callback fired when a spend threshold is crossed. (+22 more)

### Community 157 - "probe_catalogues.py"
Cohesion: 0.07
Nodes (32): _auth_headers(), _chat_targets(), _dump_matching(), _kind(), list_models(), _list_or_report(), main(), _parse_args() (+24 more)

### Community 158 - "clear_cooldowns"
Cohesion: 0.07
Nodes (41): clear_cooldowns(), get_dead_models(), _is_model_dead(), is_provider_on_cooldown(), mark_provider_failed(), Snapshot of active dead-model entries {provider_id/model: expiry_ts}. Also…, Put provider_id on cooldown for *cooldown_seconds* (default:…, Return True if provider_id is currently on cooldown. (+33 more)

### Community 159 - "test_telegram_freebuff.py"
Cohesion: 0.07
Nodes (43): cmd_freebuff(), _model_keyboard(), _parse_callback(), _parse_user_ids(), _process_callback(), Accept / reject keyboard shown after a FreeBuff plan is generated., Start a FreeBuff flow: fetch free models and present a picker keyboard., Handle an inline-button press for the FreeBuff accept/reject/model flow. (+35 more)

### Community 160 - "WorkspaceManager"
Cohesion: 0.09
Nodes (31): test_git_ref_rejects_empty(), test_git_ref_rejects_flag_injection(), test_git_ref_rejects_shell_metacharacters(), test_git_ref_rejects_traversal(), test_git_ref_valid(), test_git_scheme_allows_ssh(), test_http_scheme_rejects_ssh(), test_https_public_host_allowed() (+23 more)

### Community 161 - "test_daily_2026_07_27.py"
Cohesion: 0.07
Nodes (22): filter_safe_tools(), get_tool_annotations(), Typed representation of MCP tool annotations (spec 2025-11-05 §5.6.1). All…, Return True only when the tool is definitively read-only and non-destructive.…, Extract ``ToolAnnotations`` for a named tool from a ``list_tools()`` result.…, Return tools where ``readOnlyHint`` is True and ``destructiveHint`` is not…, ToolAnnotations, asyncio (+14 more)

### Community 162 - "QuickNoteQueue"
Cohesion: 0.10
Nodes (32): _fetch_text(), _now(), process_note(), Any, Path, QuickNote, QuickNoteQueue, agent/quick_note.py — iPhone Quick Note integration. Persistent URL queue +… (+24 more)

### Community 163 - "enforcement.py"
Cohesion: 0.07
Nodes (36): BudgetExceeded, classify(), evaluate_call(), guard_tool_call(), GuardResult, _host_of(), _is_write_tool(), _more_restrictive() (+28 more)

### Community 164 - "KnowledgeGraph"
Cohesion: 0.07
Nodes (18): KnowledgeGraph, KnowledgeNode, Find all connected components (treating edges as undirected)., Find all nodes with a given tag., Export all edges as (source, target, edge_type) tuples., Number of nodes in the graph., Number of edges in the graph., A node in the knowledge graph representing a concept or fact. (+10 more)

### Community 165 - "chat_handlers.py"
Cohesion: 0.08
Nodes (39): _apply_chat_defaults(), _apply_reasoning_budget(), _emit_safely(), _extract_exact_output(), _filter_fragment(), _filter_openai_sse_line(), handle_ollama_native_chat(), handle_openai_chat_completions() (+31 more)

### Community 166 - "KeyPool"
Cohesion: 0.06
Nodes (23): _digest(), KeyPool, _KeyState, _PoolState, Round-robin key selection with per-key rate-limit cooldowns., Return the next usable key, or None when every key is cooling. With one key…, Cool a single key after a 429 from it. Honours the provider's own ``Retry-…, True when every key in the pool is resting. This is the signal that the… (+15 more)

### Community 167 - "MetricsRegistry"
Cohesion: 0.07
Nodes (23): _Counter, _escape(), _Gauge, _Histogram, _labels(), MetricsRegistry, Any, packages/llm/metrics.py — Prometheus metrics without the client library. The… (+15 more)

### Community 168 - "test_pr923_fixes.py"
Cohesion: 0.06
Nodes (38): cleanup_stale_jobs(), _is_stale(), nuclear_cleanup(), Any, packages/scheduler/cleanup.py — schedule deduplication + stale removal.…, Remove a job from the store. Returns True on success, False on failure. Logs…, Directly delete ALL stale jobs from the DB collection. More aggressive than…, Check if a created_at timestamp is older than ttl_seconds. Handles multiple… (+30 more)

### Community 169 - "StreamingDeltaReconstructor"
Cohesion: 0.07
Nodes (23): PostProcessHook, create_streaming_reconstructor(), DeltaChunk, Any, Register a post-processing hook (runs before re-streaming)., Remove a post-processing hook., Feed a raw SSE line from the upstream stream., Feed raw text (e.g., from a non-streaming response) for re-emission. (+15 more)

### Community 170 - "SetupChecker"
Cohesion: 0.06
Nodes (26): main(), OllamaManager, OsDetector, Path, Detect operating system and available interpreters., Return normalized OS name., Detect PowerShell (Windows) or Bash (Unix)., Print colored message. (+18 more)

### Community 171 - "pr_approval_gate.py"
Cohesion: 0.08
Nodes (32): _card_keyboard(), _card_text(), _dedupe_key(), default_run_sweep(), _gh_get(), _gh_token(), interval_sec(), load_notified() (+24 more)

### Community 172 - "_resolve_brain_provider"
Cohesion: 0.06
Nodes (36): Resolve the LLM endpoint for agent execution (module-level, #522 failover).…, _resolve_brain_provider(), Regression tests for: brain-skip-paid, provider-priority persistence, scanner…, Critical failover-safety test: if every free provider's base URL is excluded…, When the ONLY configured provider is a paid one (e.g. operator set…, When only Anthropic is configured AND allow_paid=False (default), the resolver…, The PUT /api/providers/{id} endpoint did not persist priority edits because the…, scanner.py used to end with a bare `systems` statement at module level, which… (+28 more)

### Community 173 - "test_e2b_task_wiring.py"
Cohesion: 0.08
Nodes (42): TaskUpdateRequest, _build_coordinator(), _FakeCompany, _FakeCompanyGraphStore, _FakeRepoConnection, _make_task(), Task, tests/test_e2b_task_wiring.py — Task.company_id → spec.context repo_url wiring.… (+34 more)

### Community 174 - "activation.py"
Cohesion: 0.08
Nodes (42): activation_required(), ActivationResult, _b64url_decode(), _b64url_encode(), _decode_jwt_unverified(), _generate_token_for_owner(), get_activation(), get_or_create_instance_id() (+34 more)

### Community 175 - "activation_api.py"
Cohesion: 0.09
Nodes (44): activate_instance(), ActivateRequest, ActivateResponse, activation_audit_log(), activation_status(), ActivationStatusResponse, _append_audit(), AuditLogEntry (+36 more)

### Community 176 - "fmtErr"
Cohesion: 0.06
Nodes (36): chatSend(), createWikiPage(), deleteSource(), fmtErr(), getAgentChatJob(), getCompanyGraph(), getPlatformControls(), getSession() (+28 more)

### Community 177 - "OllamaCircuitBreaker"
Cohesion: 0.08
Nodes (36): _Circuit, _enabled(), _failure_threshold(), get_circuit_breaker(), OllamaCircuitBreaker, Per-model circuit breaker for Ollama backend health. Tracks consecutive failure…, Record a successful response; close the circuit., Record a 5xx error; open the circuit after threshold is reached. (+28 more)

### Community 178 - "PromptCacheManager"
Cohesion: 0.06
Nodes (20): CacheEntry, CacheStats, get_prompt_cache(), PromptCacheManager, Any, Compute a deterministic cache key from the stable prefix. The stable prefix is…, Hash a system prompt and model for KV cache fingerprinting., Return the instance ID that has this prefix cached, or None. Performs an LRU… (+12 more)

### Community 179 - "_job_text"
Cohesion: 0.05
Nodes (26): _job_text(), Guards on ``.github/workflows/dependabot-auto-merge.yml``. Three separate gates…, `unknown` must be handled like `major`, never waved through., The classifier is a repo script, so the job needs a checkout., A sweep that cannot keep up with Dependabot is not a fix. Branch protection…, Daily could never catch up: ~14 PRs arrive weekly, 7 would drain., Refreshing the rest burns two CI runs each and merges none of them. Asserted…, A conflicted PR is neither BEHIND nor mergeable, so it falls through. Without… (+18 more)

### Community 180 - "TestRuntimeControl"
Cohesion: 0.04
Nodes (26): Test iteration 6 features: - POST /api/tasks/ auto-assigns an available agent…, POST /api/tasks/ without agent_id should attempt auto-assignment if agents exist, Test runtime start/stop endpoints return informational payloads in remote…, Get authentication token for admin user, GET /runtimes/ should return list of runtimes, POST /runtimes/{id}/start should return non-blocking informational payload in…, POST /runtimes/stop-all should return non-blocking informational payload, PUT /runtimes/policy should work with valid auth (+18 more)

### Community 181 - "AgentJobRequest"
Cohesion: 0.07
Nodes (18): AgentJobError, AgentJobRequest, AgentJobResult, Any, BaseModel, field_validator, agent/contract.py — Typed public contract for the agent job lifecycle. Phase 1…, Structured error payload attached to a failed job. (+10 more)

### Community 182 - "test_audit.py"
Cohesion: 0.07
Nodes (39): AuditMessage, AuditSession, create_session(), delete_session(), get_session(), list_sessions(), Any, Audit session management for multi-turn conversations. This module provides in-… (+31 more)

### Community 183 - "TaskBoardScreen.jsx"
Cohesion: 0.06
Nodes (36): addTaskComment(), approveTaskCheckpoint(), approveTaskExecution(), clarifyTask(), createSprint(), createTask(), escalateTask(), fetchSprints() (+28 more)

### Community 184 - "ai/router.py"
Cohesion: 0.06
Nodes (41): Record token usage for *model* (fire-and-forget, never raises). ``tag`` is a…, record_usage(), _dead_model_key(), _exponential_backoff_cooldown(), _mark_model_dead(), _notify_watchdog(), _ollama_reasoning_effort(), provider_router.py — auto-generated module docstring (user-research skill scan). (+33 more)

### Community 185 - "test_runtime_governance.py"
Cohesion: 0.12
Nodes (42): _governance_check(), Evaluate a runtime dispatch against policy; audit it either way. Returns…, _decision(), _engine(), Any, RoutingDecision, TaskSpec, Governance on runtime dispatch — the last coverage gap.… (+34 more)

### Community 186 - "test_classify_dependabot_update.py"
Cohesion: 0.07
Nodes (28): classify(), classify_pull_request(), compare_versions(), _component(), is_auto_mergeable(), main(), parse_version(), Return the update type for a Dependabot PR. *branch* is ``headRefName``;… (+20 more)

### Community 187 - "WorkspaceManifest"
Cohesion: 0.07
Nodes (25): _derive_workspace_root(), WorkspaceStatusLiteral, Create an isolated workspace for a session and optional job. Creates the…, Retrieve the WorkspaceManifest for a given session and optional job. Looks up…, List all known workspaces, optionally filtered by status., Mark a workspace as active (in-use)., Pause a workspace (e.g. between agent steps)., Mark a workspace as completed. (+17 more)

### Community 188 - "test_dashboard_cache.py"
Cohesion: 0.06
Nodes (33): _cached(), _check_storage_health(), cost_attribution_stats(), doctor_health(), _fast_count(), get_active_provider(), get_activity(), get_stats() (+25 more)

### Community 189 - "rbac.py"
Cohesion: 0.08
Nodes (33): compute_savings(), compute_time_series(), get_savings(), get_usage(), get_user_savings(), _period_start(), Any, BaseModel (+25 more)

### Community 190 - "ProvidersScreen.jsx"
Cohesion: 0.06
Nodes (33): createProvider(), deleteProvider(), getBrainConfig(), getBrainProviders(), getLocalBrainState(), getProviderPolicy(), patchBrainConfig(), postLocalBrainToggle() (+25 more)

### Community 191 - "ApprovalStore"
Cohesion: 0.07
Nodes (29): Event, publish(), packages/events/bus.py — In-process event bus. Loosely couples components via…, An event published on the bus., Subscribe to an event type., Publish an event to all subscribers., subscribe(), ApprovalRequest (+21 more)

### Community 192 - "WorkflowRun"
Cohesion: 0.08
Nodes (23): _fake_artifact(), _make_engine(), tests/test_crispy_workflow.py — CRISPY workflow engine hardening tests. Tests…, Create a WorkflowEngine with isolated storage., TestAbortOnFailure, TestPhaseSequence, TestPhaseSequenceError, TestWorkspaceIsolation (+15 more)

### Community 193 - "test_features_api.py"
Cohesion: 0.05
Nodes (4): _auth_override(), client(), _fake_auth(), Integration tests for all new feature API routes in proxy.py.

### Community 194 - "test_schedule_backlog_drain.py"
Cohesion: 0.08
Nodes (39): _every_minute_one_shot(), _FakePersistence, _one_shot(), asyncio, Why the 2026-08-01 backlog never drained, despite a fix already existing.…, A timestamp we cannot parse must not authorise a delete., An agency-directive-shaped row: cron="* * * * *", uniquely named., 2026-08-03: the 7-day fallback let a live crash loop regrow the backlog from a… (+31 more)

### Community 195 - "test_video_transcript.py"
Cohesion: 0.05
Nodes (33): parametrize, Tests for video transcript extraction (`.github/scripts/video_transcript.py`).…, Events without `segs` carry no text and must not produce stray spaces., This format double-encodes: `&amp;#39;` must resolve to a single quote., Regex-terminated matching truncates this; brace matching must not. The blob…, A title containing a brace must not unbalance the matcher., An unfamiliar page shape must yield empties, never raise., A non-video URL must short-circuit before any request is attempted. (+25 more)

### Community 196 - "test_operational_incidents.py"
Cohesion: 0.06
Nodes (39): normalise(), Collapse the volatile parts of *message* so recurrences group together. ``Task…, Stable dedup key over the *normalised* message., Find agent phases that started but never finished.…, signature_for(), summarise_phases(), Recurring operational failures must diagnose and file themselves. The gap these…, The reported scenario, end to end: four real timeouts, one incident. (+31 more)

### Community 197 - "portfolio_api.py"
Cohesion: 0.08
Nodes (38): add_initiative(), AllocationOut, BoardOut, get_board(), get_service(), InitiativeIn, InitiativeOut, _materialize_and_log() (+30 more)

### Community 198 - "Part A — CodeRabbit review fixes for this PR (do first, small)"
Cohesion: 0.05
Nodes (42): A1 — `docs/changelog.md`: add the two autonomy docs under `### Added` ✅ trivial, A2 — `docs/telegram-bot.md`: fix broken charter links (MD + path), A3 — `docs/telegram-bot.md`: add language to fenced block (MD040), A4 — `.env.example`: use exact var name in the shortcut comment, A5 — `services/workflow_orchestrator.py`: surface notify failures at WARNING, A6 — `telegram_bot.py`: avoid double-approve in the `wfo_approve` path ⚠️ behavioural, A7 — `telegram_service.py`: escape Markdown-v1 reserved chars in approval text ⚠️ correctness, A8 — `render.yaml`: propagate Telegram vars to the worker service (+34 more)

### Community 199 - "Docker Agent Runtimes Setup"
Cohesion: 0.05
Nodes (41): 1. Register Runtimes, 2. Verify Installation, 3. Access Agents via API, Agent Runtime Setup, Agents not appearing in API responses, Initial Setup, MongoDB Connection, No agents showing after registration (+33 more)

### Community 200 - "anthropic_compat.py"
Cohesion: 0.09
Nodes (31): _build_anthropic_response(), _emit_safely(), _finish_reason_to_stop_reason(), get_local_model(), handle_anthropic_messages(), _messages_to_openai(), _openai_choice_to_anthropic_content(), _post_anthropic_with_fallback() (+23 more)

### Community 201 - "SchedulerStore"
Cohesion: 0.07
Nodes (17): _MemCollection, _MemCursor, _MemDB, _MemDeleteResult, Any, services/scheduler_store.py — Durable scheduler persistence. Issue #505:…, Delete a persisted job., Return the total number of persisted jobs. (+9 more)

### Community 202 - "model_router.py"
Cohesion: 0.06
Nodes (41): _build_builtin_model_map(), _default_model(), _default_reasoning_model(), _nvidia_key_present(), Dynamic model router. Central routing logic for all chat and agent requests.…, Build the built-in alias table — Nvidia NIM models when key is set, local…, Resolve the default executor model via the catalog (UNIT 7). Was a hardcoded…, Resolve the default planner (reasoning) model via the catalog (UNIT 7). (+33 more)

### Community 203 - "render_ops.py"
Cohesion: 0.07
Nodes (29): _latest_metric_value(), _note_recurrence(), _parse_timestamp(), Any, datetime, services/render_ops.py — autonomous Render debugging + environment monitoring.…, Parse an RFC3339 timestamp from Render, tolerating a trailing ``Z``., Pull the most recent numeric sample out of a ``get_metrics`` payload. Render… (+21 more)

### Community 204 - "_payload"
Cohesion: 0.08
Nodes (12): _make_anthropic_provider(), _payload(), ProviderConfig, Response, Tests for Anthropic-specific router features. Covers: - Prompt caching…, Adaptive-thinking Claude models 400 on temperature / legacy thinking. The…, TestAnthropicPayloadExtendedThinking, TestAnthropicPayloadModelGuards (+4 more)

### Community 205 - "TestRecordUsageAndStats"
Cohesion: 0.05
Nodes (10): Tests for packages/ai/cost_tracker.py — per-model cost attribution. Covers: -…, Verify all Opus models referenced by brain_config are priced., A repeated key in a dict literal is silent: the later value wins. Found on…, TestClaudeOpusModelCoverage, TestClearStats, TestCostForTokens, TestEnvOverrides, TestGetCostTable (+2 more)

### Community 206 - "test_process_quick_note_workflow.py"
Cohesion: 0.06
Nodes (24): _full_suite_jobs(), parametrize, Tests for ``.github/workflows/process-quick-note.yml``. Two defects, one…, No issue to pick up means the retry handler never runs, so the job must not go…, Order matters: the label bump and issue reopen must complete before the job…, The invariant, stated once for the whole repo. Adding the service to two…, Guards the guard: a regex that matches nothing would pass silently., A pytest that starts a moment early reproduces the very defect the service… (+16 more)

### Community 207 - "Persistent Memory System"
Cohesion: 0.05
Nodes (41): 1. **Semantic Memory Categorization**, 1. **Use Appropriate Scopes**, 2. **Prioritize Effectively**, 2. **Scope-Based Auto-Loading**, 3. **Priority-Based Retrieval**, 3. **Use Semantic Categories**, 4. **Cross-Tool Compatibility**, 4. **Tag Liberally** (+33 more)

### Community 208 - "nvidia_models.py"
Cohesion: 0.07
Nodes (38): build_review_context(), _gh(), main(), Aggregate all review feedback for the PR into a single context string., _fetch_models_json(), _is_chat_model(), live_model_ids(), _rank_key() (+30 more)

### Community 209 - "test_unit6_resolve_component_model.py"
Cohesion: 0.06
Nodes (41): invalidate_brain_config_cache(), Clear the singleton's cache (used by tests + brain_policy invalidation)., Convenience: resolve all four role models for a component. Returns a dict with…, resolve_component_role_models(), tests/test_unit6_resolve_component_model.py — UNIT 6 regression tests. Verifies…, When the DB cache is fresh AND provider matches the active primary, the DB-…, When the DB primary differs from the requested provider, the catalog preset for…, When `provider` is None, the DB primary's saved model wins. (+33 more)

### Community 210 - "AgentScheduler"
Cohesion: 0.07
Nodes (27): AgentScheduler, Register, list, trigger, and delete cron-scheduled agent jobs. Usage:: sched =…, Remove a job. Returns *True* if it existed., Capture the FastAPI main event loop so APScheduler's background thread can…, Attach a durable store and immediately rehydrate from it (#505). Called at…, Async variant of :meth:`attach_persistence` for callers already on an event…, Sync entry-point for attach_persistence(); delegates to hydrate(). With no…, #505: Rehydrate persisted schedules on boot. Skips stale run-once jobs (already… (+19 more)

### Community 211 - "test_bedrock_provider.py"
Cohesion: 0.08
Nodes (18): _bedrock_api_response(), _bedrock_provider(), _mock_boto3(), Any, asyncio, ProviderConfig, Tests for AWS Bedrock provider support in ProviderRouter., Inject a mock boto3 module into sys.modules for the duration of the block. (+10 more)

### Community 212 - "TrendWatcher"
Cohesion: 0.15
Nodes (14): Any, AsyncClient, Path, Fetches AI trend signals from many public sources and surfaces relevant ones., Fetch all sources in parallel; return new alerts sorted by relevance., Fan trends out to onboarded companies whose stack matches (G4). For each…, Dispatch high-relevance alerts to the Hermes sidecar for action. Only…, TrendAlert (+6 more)

### Community 213 - "timedelta"
Cohesion: 0.08
Nodes (34): PR throughput per cohort over the last `days` days., Count distinct sessions per user. A session ends when there's a gap of more…, _as_aware_utc(), _company_alive(), _company_id_for_agent(), _env_float(), ephemeral_reaper_loop(), datetime (+26 more)

### Community 214 - "v4_api.py"
Cohesion: 0.10
Nodes (40): _get_cached_tasks(), _get_tasks_cache_lock(), _load_improvement_state(), Any, BaseModel, get, Lock, post (+32 more)

### Community 215 - "Kept Rules — the 44 that survive the audit"
Cohesion: 0.05
Nodes (37): C1 — The bill of materials is wrong in both directions, C2 — Three different answers to "where do I read env vars?", C3 — Two different file-size limits, C4 — The frontend does not deploy to Vercel, C5 — The documented P0 escape hatch does not exist, C6 — `CLAUDE.md` §14.11 conflicts with §14.9, C7 — Two `§10` headings in `CLAUDE.md`, C8 — Duplicated rule sets that have already drifted (+29 more)

### Community 216 - "configuration-reference.md"
Cohesion: 0.07
Nodes (25): Beta, Config Overrides, Disabled (demoted per issue #467 Section I), Enforcement, Experimental, Feature Maturity / Support Matrix, Maturity Tiers, Stable Core (+17 more)

### Community 217 - "governance.py"
Cohesion: 0.07
Nodes (32): guard(), identity_from_headers(), Any, mcp_server/governance.py — governance adapter for the MCP HTTP surface. Closes…, Build an AgentIdentity from the caller's ``X-Agent-*`` headers. Absent headers…, Evaluate *tool* before it runs. Returns ``(allowed, message, decision)``.…, Write the audit row for a completed (or blocked) MCP tool call., Wall-clock timer for the audit row's ``duration_ms``. (+24 more)

### Community 218 - "compare_runtimes.py"
Cohesion: 0.07
Nodes (21): compare(), main(), Any, scripts/compare_runtimes.py — head-to-head runtime comparison. Answers the…, Check an operator-supplied task file before anything executes., render(), _run_one(), RunRecord (+13 more)

### Community 219 - "NotificationDispatcher"
Cohesion: 0.08
Nodes (29): NotificationDispatcher, Path, service_manager.py — Telegram & Notification Integration Extension Extends the…, Start the Telegram bot. Returns True if started successfully., Signal the bot to stop and wait for graceful shutdown., Run the Telegram bot long-poll loop (inline, not subprocess)., Run the bot with stop-event awareness., Routes background task results to configured notification channels. Currently… (+21 more)

### Community 220 - "RewardScorer"
Cohesion: 0.07
Nodes (20): get_reward_scorer(), _nvidia_api_key(), BaseModel, Score a response against a prompt using the Nemotron reward model. Returns a…, Call the NVIDIA NIM reward endpoint and return the score. The Nemotron reward…, Parse the reward score from the model's JSON response., Return the module-level RewardScorer singleton., Result of a single reward model scoring operation. (+12 more)

### Community 221 - "WorkspaceTools"
Cohesion: 0.07
Nodes (24): repowise.py — RepowiseIntelligence: context packing and dependency analysis., tools.py — WorkspaceTools: read/write/search and diff application (risky…, Delegate to RepowiseIntelligence for a natural-language codebase question., Delegate to RepowiseIntelligence for a semantic/text codebase search., Delegate to RepowiseIntelligence to list architectural decision nodes., Return a high-level repository map and hotspot summary., Return a formatted context block for the given file paths., Return a risk summary for the workspace or a subset of files. (+16 more)

### Community 222 - "ScheduleStore"
Cohesion: 0.07
Nodes (30): _backend(), _json_default(), Any, agent/schedule_store.py — durable persistence for scheduled agent jobs. Fixes…, Return all persisted schedule docs (for boot rehydration)., Persist (insert or update) a single schedule by job_id., Delete a persisted schedule., Fallback JSON encoder for schedule docs (datetimes, sets, etc.). (+22 more)

### Community 223 - "Artifact"
Cohesion: 0.09
Nodes (25): AgentRole, TestSlice, workflow/artifact_store.py — Durable artifact persistence. Artifacts are stored…, _extract_slices_from_plan(), workflow/engine.py — WorkflowEngine: CRISPY phase sequencer. The engine is the…, Extract slice definitions from a plan.md artifact. Looks for sections matching:…, Reset the singleton (test helper)., reset_engine() (+17 more)

### Community 224 - "emit_chat_observation"
Cohesion: 0.10
Nodes (32): observability_diag_public(), PUBLIC diagnostic endpoint for Langfuse — no auth required. Returns exactly…, CommercialEquivalent, estimate_commercial_equivalent_usd(), get_prices(), _load_from_env(), _parse_mapping(), Any (+24 more)

### Community 225 - "distributed.py"
Cohesion: 0.07
Nodes (20): DistributedRateLimiter, get_limiter(), get_persistent_queue(), _LocalBucket, PersistedRequest, PersistentQueue, Any, packages/llm/distributed.py — cross-instance coordination. Two facilities that… (+12 more)

### Community 226 - "JCodeAdapter"
Cohesion: 0.07
Nodes (21): JCodeAdapter, Any, Path, Write .jcode/mcp.json in the workspace, pointing at our proxy's MCP endpoint.…, Resolve the default executor model via the catalog (UNIT 7). Was hardcoded to…, Adapter for jcode — TIER 2 high-performance Rust coding agent., _resolve_default_executor_model(), _build_default_manager() (+13 more)

### Community 227 - "test_v4_reliability_regression.py"
Cohesion: 0.08
Nodes (19): Fail preflight when the provider extension is configured but missing. Without…, Any, Structured, actionable preflight validation issue., Preflight result returned before a runtime task starts., Return runtime-specific dependency declarations for preflight., Return a best-effort tool availability report for diagnostics., Ensure the requested workspace exists and is writable., Validate task-specific prerequisites beyond runtime dependencies. (+11 more)

### Community 228 - "_run"
Cohesion: 0.07
Nodes (18): _patch_send_message(), tests/test_telegram_inbound.py Pytest coverage for the Step 1 inbound-routing…, ``_resolve_reply_to_decision`` returns the durable link from SQLite.\n, ``/redirect`` command: admin-only, prefix-dispatched, idempotent shape., ``/paste <abs-path>`` command: admin gate + path check + truncation., ``_handle_big_paste`` writes to disk and short-replies., ``_route_plain_text`` classifies and dispatches per the documented map., Return a Telegram nested-message-shaped dict for resolve-reply-to tests. (+10 more)

### Community 229 - "Workflow"
Cohesion: 0.06
Nodes (23): Enum, SuperClaude Workflow Engine — Workflow, Task, and topological DAG execution.…, Return tasks whose dependencies are all satisfied., Number of tasks in the workflow., Number of completed tasks., Number of failed tasks., Executes workflows using topological ordering., Register a workflow with the engine. (+15 more)

### Community 230 - "test_llm_router_disabled.py"
Cohesion: 0.09
Nodes (37): auto_disable(), _billing_signals(), describe(), disabled_provider_ids(), is_unfixable(), packages/llm/disabled.py — bridge to the durable provider on/off switch. The…, Provider ids currently switched off. Empty when the store is unreachable., Persist a provider as disabled, through the store that already owns it. (+29 more)

### Community 231 - "InternalAgentAdapter"
Cohesion: 0.06
Nodes (28): _best_cloud_primary_base(), InternalAgentAdapter, TaskResult, Built-in agent loop — Nvidia NIM primary, Ollama fallback., Return runtime dependencies required by this adapter. Returns:…, Determine availability of the internal agent runtime. Checks cloud providers in…, Execute a TaskSpec using the internal AgentRunner and convert the agent's…, Create an isolated execution context for a single task. Tries ``git worktree… (+20 more)

### Community 232 - "service_daemon.py"
Cohesion: 0.07
Nodes (27): configure(), get_status(), health(), BaseModel, get, post, Validate configured paths., Check if proxy is running. (+19 more)

### Community 233 - "daily_digest.py"
Cohesion: 0.11
Nodes (25): aggregate_last_24h(), build_daily_digest(), compute_cutoff(), DigestSummary, format_digest_markdown(), _md_escape(), _now_utc(), Any (+17 more)

### Community 234 - "TestClient"
Cohesion: 0.07
Nodes (25): backend_jwt(), proxy_client(), MonkeyPatch, TestClient, Regression test for /api/auth/me — verifies the critical endpoint on both the…, TestClient against proxy.py:app with a known API key seeded., API-key-based /api/auth/me on proxy.py (port 8000)., GET /api/auth/me with valid API key → 200 with derived profile. (+17 more)

### Community 235 - "WorkflowBuildRequest"
Cohesion: 0.08
Nodes (28): engine(), WorkflowEngine, tests/test_contracts_agency.py — Contract tests for agency core autonomy…, Contract: WorkflowEngine cannot skip the gate state machine., Contract: No code path may advance past awaiting_approval unless gate.status ==…, Create a run and manually place it in awaiting_approval., Contract: Cannot approve a run in 'pending' state., Contract: Can approve a run in 'awaiting_approval' state. (+20 more)

### Community 236 - "test_portfolio_intelligence.py"
Cohesion: 0.06
Nodes (15): FakeResp, asyncio, Tests for agents/portfolio_intelligence.py — autonomous signal → initiative.…, DEFAULT_REPO was hardcoded to the stale pre-rename repo name…, fetch_github_signals must degrade gracefully (log + return empty lists) on a…, Even with a 200, a malformed/rate-limited body that isn't a list must not be…, fetch_research_alerts used asyncio.run() to await TrendWatcher().fetch(), which…, The exact scenario that crashed before the fix: called from code that is itself… (+7 more)

### Community 237 - "test_schedule_growth_invariants.py"
Cohesion: 0.06
Nodes (25): _FakeMongoStore, _FakePersistence, _FakeSQLiteStore, asyncio, parametrize, Workstream D — Never again: dedup + growth invariants. These tests enforce…, Simulates a Mongo-style store with find/aggregate/replace_one., Simulates a SQLite-style store with load_all/upsert/remove. (+17 more)

### Community 238 - "GitHubTools"
Cohesion: 0.12
Nodes (14): GitHubTools, Any, List issues (excludes pull requests) for triage/intake pipelines., Add labels to an issue (used to mark it as triaged, preventing reprocessing)., Merge an open pull request via the GitHub API., Backwards-compat: accepts 'owner/repo' format., Backwards-compat: accepts 'owner/repo' format., Commit a single file change. Accepts 'owner/repo' format for repo_name. (+6 more)

### Community 239 - "test_knowledge_sync.py"
Cohesion: 0.12
Nodes (33): _api_key(), _auth_headers(), _build_digest_markdown(), get_knowledge_sync(), KnowledgeSync, _now_iso(), agent/knowledge_sync.py — Wiki + Sources knowledge ingestion pipeline. Bridges…, Render a markdown digest from a list of TrendAlert dicts. (+25 more)

### Community 240 - "AutonomyTracker"
Cohesion: 0.06
Nodes (13): AutonomyCounter, AutonomySnapshot, AutonomyTracker, Any, agent/kpi.py — Autonomy KPIs: evidence capture and metrics tracking. Tracks key…, Return a point-in-time snapshot of all KPIs., Reset all counters (test helper)., Thread-safe counter for a single KPI metric. (+5 more)

### Community 241 - "loop.py"
Cohesion: 0.09
Nodes (32): loop.py — AgentRunner: plan → execute → verify loop with locked tool signatures., Governance seam: judge the call, run it, audit the outcome. Deliberately a thin…, Condense a tool result down to what belongs in an audit row. A tool result can…, # NOTE: "ollama_base" is kept for backwards compatibility; this runner only…, Feed LLM token/cost spend into the governance session budget. Kept separate…, Charge sub-agent nesting depth and enforce the ``max_depth`` ceiling. Isolates…, _summarise_tool_result(), build_compaction_prompt() (+24 more)

### Community 242 - "PatternConsolidation"
Cohesion: 0.10
Nodes (9): PatternConsolidation, Group memories into clusters by tag overlap., Jaccard similarity of tag sets., Run the full consolidation cycle., Identifies clusters of related DreamMemory fragments and consolidates them into…, _make_memory(), Tests for agents.memory_consolidation — Dream Memory Consolidation., TestDreamMemory (+1 more)

### Community 243 - "[Unreleased]"
Cohesion: 0.05
Nodes (38): Added, Added, Added, Added, Added, Added, Added, Added (+30 more)

### Community 244 - "[Unreleased]"
Cohesion: 0.05
Nodes (38): Added, Added, Added, Added, Added, Added, Added, Added (+30 more)

### Community 245 - "test_daily_2026_06_04.py"
Cohesion: 0.08
Nodes (37): _content_block_to_text(), Convert a single Anthropic content block to a plain text string., is_anthropic_model(), True when *model* names a paid Anthropic/Bedrock-Claude model. Covers native…, _opus_model(), Return an Opus model ID iff the operator explicitly opted into a paid brain.…, test_is_anthropic_model(), _content_block_to_text() (+29 more)

### Community 246 - "system_instruction"
Cohesion: 0.09
Nodes (13): is_strict(), Any, Structured output normalization across LLM providers. Translates the OpenAI…, Return True when the caller has requested strict schema enforcement. Strict…, Return a plain-English JSON instruction for a ``response_format`` dict. Returns…, system_instruction(), Daily automation tests — 2026-07-24. Covers three features added in this…, is_strict() detects strict: true inside json_schema. (+5 more)

### Community 247 - "NIMConnectionPool"
Cohesion: 0.08
Nodes (19): get_nim_pool(), NIMConnectionPool, Any, AsyncClient, Response, Persistent httpx.AsyncClient pool with circuit breaker and retry logic. Manages…, Get or create the shared httpx.AsyncClient., Context manager for a pooled client session. (+11 more)

### Community 248 - "TestCatalogFable51"
Cohesion: 0.09
Nodes (13): _cfg(), _cost_table(), tests/test_daily_automation_2026_09_04.py — Daily automation tests…, claude-fable-5 was 3.0/15.0 in the tracker but 30.0/120.0 in models.yaml., generate() populates Usage.reasoning_tokens from output_tokens_details., Exercise the same parsing path as AnthropicProvider.generate()., Verify the claude-fable-5-1 entry in config/llm/models.yaml., 5.1 is the newer release, so it should be preferred over 5.0. (+5 more)

### Community 249 - "TestAuthAndTaskOwnership"
Cohesion: 0.06
Nodes (21): skip, Test iteration 7 features: - POST /api/tasks/ auto-assigns an available agent…, Test runtime start/stop endpoints return informational payloads in remote…, POST /runtimes/{id}/start should return 200 with informational payload (not 500), POST /runtimes/stop-all should return 200 with informational payload, Test that routing policy defaults allow paid fallback only with approval, GET /runtimes/policy should show never_use_paid_providers=false and…, Test authentication and task creation with owner assignment (+13 more)

### Community 250 - "test_one_model_catalogue.py"
Cohesion: 0.08
Nodes (20): _hardcoded_candidates(), parametrize, Model ids belong in a catalogue, not in Python. Four files in this repo each…, A frozen record of the divergence found on 2026-08-28. Reconciling these eleven…, These two are the ones this work reconciled, and each was reconciled because…, A shrinking divergence is progress, but the list must be trimmed to match or it…, ``config/llm/models.yaml`` drives capability filtering. An entry for a retired…, A sixth model source, found on 2026-08-28 while verifying a fix.… (+12 more)

### Community 251 - "AdaptiveHalter"
Cohesion: 0.08
Nodes (13): AdaptiveHalter, Any, ★7 Adaptive Loop Halting — velocity-based agent run termination. Complements…, Return current halter state for logging / telemetry., Tracks step-level progress and signals when a run should halt early. The halter…, Ratio of applied steps to steps attempted (0.0–1.0). Returns 1.0 when no steps…, Record one step outcome; return a halt reason or None to continue. ``status``…, tests/test_daily_automation_2026_07_13.py — Daily automation tests… (+5 more)

### Community 252 - "ContextPruner"
Cohesion: 0.09
Nodes (29): ContextPruner, Any, context_pruner.py — auto-generated module docstring (user-research skill scan)., Walk messages backward, accumulating per-role char counts. Returns…, Wrap evicted messages into ``<historical_memory_only>`` XML. The XML block is…, Reset the prune timer so the next call always runs the pipeline., 3-phase context window management middleware. Phase 1 — Truncate: Strips…, Apply 3-phase pruning if the context is over budget or cache expired. Returns… (+21 more)

### Community 253 - "AgileManager"
Cohesion: 0.07
Nodes (11): AgileManager, Manages multiple agile sprints with velocity tracking., List all active sprints., Predict next sprint velocity from historical data., Number of managed sprints., Tests for agents/agile_ceremonies.py — autonomous agile ceremonies. Loads…, TestGenerateBacklogRetro, TestGenerateStandup (+3 more)

### Community 254 - "provider_max_rpm"
Cohesion: 0.08
Nodes (31): provider_max_parallel(), provider_max_rpm(), provider_max_tpm(), _provider_positive_float(), provider_weight(), Shared parse/validate for the numeric per-provider traffic budgets. Returns…, Return the operator-configured requests/min cap for *provider*, or None if…, Return the operator-configured tokens/min cap for *provider*. Reads… (+23 more)

### Community 255 - "test_agent_api.py"
Cohesion: 0.07
Nodes (10): AdminAuthManager, AdminSession, AdminSessionStore, _is_truthy(), admin_auth.py — auto-generated module docstring (user-research skill scan)., WindowsCredentialAuthenticator, patch, TestWindowsAuth (+2 more)

### Community 256 - "_Collection"
Cohesion: 0.11
Nodes (16): _apply_update(), _Collection, _DeleteResult, _InsertResult, _match(), _new_id(), _now_iso(), db/sqlite_store.py — Async SQLite storage backend. Provides a Motor-compatible… (+8 more)

### Community 257 - "SyncService"
Cohesion: 0.09
Nodes (17): sync/ — Syncthing-style workspace synchronisation service., Any, Path, A single synchronised file fragment., Orchestrates workspace synchronisation across peers. Maintains an in-memory…, Return metadata for all files in a sync folder., Read a file from a sync folder., Write a file into a sync folder, creating parent dirs as needed. (+9 more)

### Community 258 - "TaskDispatcher"
Cohesion: 0.08
Nodes (23): Re-queue BLOCKED tasks that have cooled down and are ready for retry., Polls for queued task work and executes it through the coordinator. Crash…, Re-queue tasks stranded by a prior crash or hard-kill., TaskDispatcher, _make_task(), asyncio, Task, tests/test_dispatcher_iso8601.py — regression test for the TaskDispatcher auto-… (+15 more)

### Community 259 - "PlaybookLibrary"
Cohesion: 0.10
Nodes (21): _now(), Playbook, PlaybookLibrary, PlaybookRun, PlaybookStep, Any, Path, agent/playbook.py — Automation Playbooks Pre-defined, named multi-step… (+13 more)

### Community 260 - "test_verification_strategies.py"
Cohesion: 0.11
Nodes (32): cross_verify(), Any, race(), agent/verification_strategies.py — opt-in parallel patterns for high-stakes…, Heuristic fallback score when the reward model is unavailable.…, Run *n* independent attempts at *instruction* concurrently; return the winner.…, True if any path matches the repo's risky-module trigger list., Have an independent agent re-check a completed task's changed files. Returns… (+24 more)

### Community 261 - "Screens"
Cohesion: 0.06
Nodes (36): 🛡 Admin — users & access, 🤖 Agents — autonomous team, Architecture, security, license, Autonomous AI Agency, 💬 Chat — unified assistant, 🏢 Company — operating context, Contributing, 📊 Dashboard — system overview (+28 more)

### Community 262 - "REWRITE_PLAN.md — Phased Migration Strategy"
Cohesion: 0.06
Nodes (35): Already completed (pre-migration fixes), Current Status, Inventory of suspected dead code, Migration Safety Checklist, Phase 1: Foundation (Weeks 1-2), Phase 2: Provider Abstraction (Weeks 3-4), Phase 3: Auth Consolidation (Week 5), Phase 4: Scheduler Redesign (Week 6) (+27 more)

### Community 263 - "test_background_services.py"
Cohesion: 0.08
Nodes (23): Return True when the web process should also run background services., run_background_in_web(), anyio, Unit tests for services/background.py — start_background_services wiring.…, Scheduler's on_fire handler is set to TaskAutomation.handle_scheduled_job., Calling bg.stop() twice must not raise or double-stop., RUN_BACKGROUND_IN_WEB defaults to True., The constant itself must leave real margin under Render's 5s timeout. (+15 more)

### Community 264 - "test_persistent_memory.py"
Cohesion: 0.06
Nodes (35): memory_store(), Tests for persistent memory system., Test auto-loading global memories., Test auto-loading includes workspace-specific memories., Test that auto-load respects priority ordering., Test filtering memories by category., Create a temporary database for testing., Test searching memories. (+27 more)

### Community 265 - "SecurityScanner"
Cohesion: 0.11
Nodes (25): _now(), Any, Path, agent/security_scanner.py — Security & Vulnerability Scanner Runs static…, Run all available scanners and aggregate results., Run a cross-harness security audit. Checks that the agent harness configuration…, Return True if *name* is on PATH., Return current UTC timestamp as ISO string. (+17 more)

### Community 266 - "test_provider_render_env.py"
Cohesion: 0.09
Nodes (24): Write a provider's key and/or base_url to the Render service environment. This…, sync_provider_to_render(), provider_env_names(), RuntimeError, packages/integrations/render_env.py — write a single Render env var over REST.…, Raised when Render rejects or cannot serve an env-var write., Return ``(key_env, base_url_env)`` for a provider id, or ``None``. Sourced from…, Set one environment variable on a Render service via the REST API. Updates a… (+16 more)

### Community 267 - "agent_runtime.py"
Cohesion: 0.09
Nodes (33): _active_cloud_provider(), _candidate_ollama_bases(), _chat(), chat_completions(), _chat_with_ollama(), _chat_with_openai_compat(), ChatRequest, ChatResponse (+25 more)

### Community 268 - "api_keys_for"
Cohesion: 0.08
Nodes (17): api_keys_for(), Per-provider API key rotation — the one lever that adds capacity. Every other…, Clear pool state (tests only)., All keys configured for *provider_id*, primary first. Thin delegate to…, reset(), _clean_pool(), parametrize, Tests for packages/ai/key_pool.py — per-provider API key rotation. Rotation is… (+9 more)

### Community 269 - "local_controller.py"
Cohesion: 0.12
Nodes (33): _bin_exists(), _choose_local_brain(), _default_agency_url(), _default_machine_id_file(), _env_int(), _get_or_create_machine_id(), _http_json(), _log() (+25 more)

### Community 270 - "test_live_server.py"
Cohesion: 0.21
Nodes (33): check(), main(), ok(), Any, Client, Response, Returns access token for subsequent tests., E2E smoke-test suite — runs against a live local-llm-server instance. Every… (+25 more)

### Community 271 - "test_all_providers_discovery.py"
Cohesion: 0.17
Nodes (34): _get(), asyncio, Verify every supported provider is correctly discovered, prioritised, and…, Check if url hostname matches expected domain (exact or subdomain)., Build a ProviderRouter from_env() with only the supplied env vars active., _router(), test_anthropic_discovery(), test_anthropic_no_base_url_required() (+26 more)

### Community 272 - "._log_event"
Cohesion: 0.11
Nodes (19): Path, PhaseType, WorkflowRun, Append an event to the workflow event log., Create a new WorkflowRun and begin pre-gate phase execution. The run is…, Return current WorkflowRun snapshot or None., Approve the plan — lifts the ApprovalGate and resumes execution. Raises…, Reject the plan — marks run as failed. (+11 more)

### Community 273 - "SpecEntry"
Cohesion: 0.11
Nodes (18): get_enrichment(), agent/harness_enrichment.py — Automatic Harness Enrichment for Agent Prompts…, Return the enrichment instance for a workspace. Keyed by workspace root rather…, build_block(), _flag(), Rewrite the spec file, preserving any non-entry (hand-written) lines., Compact prompt block of standing instructions, or '' when there are none.…, One standing instruction plus the evidence that earned it. (+10 more)

### Community 274 - "test_loop_registry.py"
Cohesion: 0.12
Nodes (27): DriftReport, loop_readiness(), LoopRegistry, LoopSpec, BaseModel, field_validator, loop-cost: approximate tokens this loop spends over 30 days., The full fleet catalogue. (+19 more)

### Community 275 - "OutputFilter"
Cohesion: 0.08
Nodes (33): OutputFilter, Filter and compress command outputs to reduce LLM token consumption. Provides…, _enable_filter(), tests/test_output_filter.py — Unit tests for output_filter.py Verifies token…, pytest output with many passing tests should be compressed., pytest output with failures should preserve failure details., Deep Python traceback should collapse intermediate frames., Large curl output should be truncated with head/tail. (+25 more)

### Community 276 - "_resolve_user_github_token"
Cohesion: 0.10
Nodes (30): _DoctorCheck, _DoctorReport, get_doctor_diagnostics(), get_doctor_report(), get_public_doctor(), Consolidated system health report: preflight checks + runtime health. Returns a…, Public Doctor endpoint — no authentication required. Returns system-level…, Authenticated Doctor endpoint — full diagnostics. Returns all system-level… (+22 more)

### Community 277 - "DashboardScreen.jsx"
Cohesion: 0.07
Nodes (10): BarChart(), Charts, Donut(), ExecutionTimeline(), Sparkline(), ErrorBoundary, DashboardScreen(), fmtTokens() (+2 more)

### Community 278 - "context_rules.py"
Cohesion: 0.11
Nodes (32): _check_constitution_echo(), _check_files_exist(), _check_grounding(), _check_hedges(), _check_project_identity(), _check_risk_flags(), _check_source_summary(), _check_todos() (+24 more)

### Community 279 - "_plan"
Cohesion: 0.09
Nodes (16): _build_grounding_block(), Render the Source Grounding table — rulebook R1. A reader must be able to tell…, _plan(), parametrize, Path, A plan that says "do not build this" must stop the thing that builds. On…, The real thing, reconstructed from the merged plan.…, An unreadable plan is not an approved plan. (+8 more)

### Community 280 - "brain_config.py"
Cohesion: 0.08
Nodes (30): _active_primary_provider(), get_brain_config_store(), is_north_mini_code_default(), provider_api_keys(), _provider_env_value(), _provider_ids_from_literal(), provider_key_rotation_enabled(), services/brain_config_store.py — DB-persisted, UI-switchable "brain" config.… (+22 more)

### Community 281 - "test_platform_controls.py"
Cohesion: 0.08
Nodes (26): all_controls(), controls_by_group(), Every control in the catalogue, in display order., The catalogue grouped for the dashboard, groups in display order., clean_overrides(), _python_sources(), Tests for the dashboard platform-controls surface. Covers the three things that…, Secrets stay environment-only per the repository constitution. (+18 more)

### Community 282 - "ContextCompressor"
Cohesion: 0.11
Nodes (24): ContextCompressor, ContextStats, _estimate_tokens(), Strategy, agent/context.py — Smart Context Compression Three strategies for keeping…, Drop the oldest non-system messages until under the token threshold., Remove exact-duplicate and near-empty messages., Compress conversation history when it approaches the token limit. Usage:: cc =… (+16 more)

### Community 283 - "ContextManager"
Cohesion: 0.10
Nodes (24): ContextManager, Any, True when the history is long enough to warrant compaction., Replace the old portion of *history* with a single compaction note. The…, True when the harness should use head_file instead of read_file. When a file is…, Trim a step result so sub-agent outputs stay within ~1-2k tokens. The Anthropic…, Manages context window state for a single agent run. The Brain (LLM) stays…, Return a copy of *observations* with old tool outputs truncated. JetBrains… (+16 more)

### Community 284 - "SparkProvider"
Cohesion: 0.07
Nodes (21): get_spark_provider(), NotarizeResult, Any, agent/spark_provider.py — SPARK API Integration Inspired by SPARK API (spark-…, Return True if SPARK API key is set., Register this agent on the SPARK network. If *bsv_address* is not provided,…, Notarize content hash on the BSV blockchain. Args: content: String or bytes to…, Verify a hash against the BSV blockchain. Args: content_hash: SHA-256 hash to… (+13 more)

### Community 285 - "ResourceWatchdog"
Cohesion: 0.10
Nodes (20): _now(), Any, agent/watchdog.py — Resource Watchdog Monitors URLs, files, or any resource…, Register a resource to monitor. Returns the :class:`WatchedResource`., Stop monitoring a resource. Returns *True* if it existed., Check a single resource right now. Returns a :class:`WatchEvent` if changed., Poll resources at a fixed interval and fire *on_change* when content changes.…, ResourceWatchdog (+12 more)

### Community 286 - "README.md"
Cohesion: 0.07
Nodes (18): Agent Readiness Report, Build System — 100/100, Dev Environment — 100/100, Documentation — 100/100, Observability — 100/100, Security — 100/100, Style And Validation — 100/100, Task Discovery — 100/100 (+10 more)

### Community 287 - "Configuration Reference"
Cohesion: 0.06
Nodes (33): Agent governance — identity, policy, approvals, audit, sandboxes, Agent Models, Anthropic API Compatibility / Claude Code, Authentication and Keys, Browser automation for agents, Claude Code setup, Configuration Reference, Continual Harness (+25 more)

### Community 288 - "Workspace"
Cohesion: 0.10
Nodes (14): Any, Path, mcp_server/workspace.py — Isolated workspace manager for the MCP server. Each…, Run a shell command inside the workspace via an explicit shell binary., Resolve rel against root, reject path traversal., Run a subprocess. Never uses shell=True., Manages a single isolated workspace directory., Canonical root path (follows macOS /var → /private/var symlinks). (+6 more)

### Community 289 - "test_rate_limiter.py"
Cohesion: 0.09
Nodes (29): get_tracker(), pace(), Proactive rate-limit throttling for LLM providers — two complementary layers.…, Return the process-singleton RateLimitTracker., Rate limiter using virtual scheduling (GCRA-style): each caller atomically…, Block until this caller's reserved slot arrives, or *max_wait* elapses. Returns…, Proactively pace a request to *provider_id*. No-op (returns 0.0 immediately)…, Clear all token-bucket state (tests only). Does not touch the header tracker's… (+21 more)

### Community 290 - "RateLimitTracker"
Cohesion: 0.10
Nodes (11): RateLimitTracker, Sleep if remaining quota for *provider_id* is critically low. Returns the…, Snapshot of all tracked provider quotas. Safe to call from any context., Reset all state (primarily for tests)., In-memory tracker for per-provider rate-limit state., asyncio, _response(), TestClear (+3 more)

### Community 291 - "report_to_markdown"
Cohesion: 0.10
Nodes (25): _build_curl_cffi_fetcher(), _build_pdf(), main(), _parse_args(), Namespace, Path, Render an executive-level PDF from the audit report dict., scripts/run_seo_audit.py — Parameterised full-site SEO / GEO / AEO / AIO audit.… (+17 more)

### Community 292 - "test_brain_failover.py"
Cohesion: 0.12
Nodes (32): ProviderHealth, Circuit-breaker state for a provider., _make_manager(), tests/test_brain_failover.py — Universal multi-provider brain failover tests.…, Guards the three tests below from pinning a retired id again: if the fixture…, Status snapshot doesn't leak API keys., Make a fresh manager (bypasses the singleton for isolation)., No API keys set → no providers in the registry. (+24 more)

### Community 293 - "app.py"
Cohesion: 0.09
Nodes (25): chat_completions(), ChatCompletionRequest, _content_to_str(), _ContentPart, health(), lifespan(), list_models(), _Message (+17 more)

### Community 294 - "skill_bindings.py"
Cohesion: 0.09
Nodes (24): BaseModel, Enum, str, services/skill_bindings.py — Runtime Skill Bindings for Specialist Agents Wires…, A runtime-callable skill that specialists can execute through the workflow…, Set the singleton SkillBindings instance (for testing)., Central registry that maps skills to specialist families and provides runtime…, List all registered skills. (+16 more)

### Community 295 - "test_sam_voice.py"
Cohesion: 0.07
Nodes (32): asyncio, tests/test_sam_voice.py — Integration tests for SAM voice agent. Tests the SAM…, Same session_id must return the same session., SAM's system prompt must address the user as Commander., SAM's system prompt must instruct concise responses., _build_context must return a dict with expected keys., A hung LLM call must not block SAM — it must time out and fall back., A stalled context read must not block process_command indefinitely. (+24 more)

### Community 296 - "test_microagents.py"
Cohesion: 0.15
Nodes (29): load_microagents(), match_microagents(), Microagent, microagents_block(), _parse_file(), Path, OpenHands-compatible microagents: keyword-triggered repo knowledge. OpenHands…, Parse one microagent markdown file; None when it isn't one. (+21 more)

### Community 297 - "Security Analysis — local-llm-server"
Cohesion: 0.06
Nodes (30): Fable 5 — Read-Only Audit & Skill-Distillation Notes, Finding A — `list_for_user` Mongo query diverges from the `_can_read` policy, Finding B — `/api/secrets` router is mounted with no authentication dependency, How I would make the smaller model behave like me, Minor, non-security, Part 0 — A caveat on how this task started, Part 1 — The audit, Part 2 — Handing frontier skills to a smaller model (+22 more)

### Community 298 - "facade.py"
Cohesion: 0.09
Nodes (28): create_refresh_token(), google_callback(), create_access_token(), create_refresh_token(), get_current_user(), get_optional_user(), github_exchange_code(), github_fetch_user() (+20 more)

### Community 299 - "_get_provider_policy"
Cohesion: 0.08
Nodes (31): _get_provider_policy(), get_provider_policy_route(), Read the durable provider policy from DB, falling back to a safe default.…, Return the provider policy (paid-provider kill switch state)., seed_default_providers(), Resolve the LLM endpoint for a named surface (task/chat/ceo/sdlc/…). Honours…, resolve_provider_for(), asyncio (+23 more)

### Community 300 - "openclaw_gateway.py"
Cohesion: 0.08
Nodes (31): openclaw_command(), _openclaw_instructions(), openclaw_reverse_proxy(), openclaw_status(), openclaw_websocket(), api_route, websocket, Return the OpenClaw Gateway integration status + pairing QR data. The gateway… (+23 more)

### Community 301 - "Langfuse Observability Guide"
Cohesion: 0.06
Nodes (32): 1. Create a Langfuse project, 2. Configure credentials, 3. Optional tuning, 4. Verify the connection, Commercial savings metrics, Cost analysis dashboard, Cost dashboard, Customising Commercial Reference Prices (+24 more)

### Community 302 - "v3_models.py"
Cohesion: 0.13
Nodes (31): _get_current_user, UserResponse, delete_model(), get_activity(), get_model(), _get_ollama_model_info(), _get_ollama_models(), get_stats() (+23 more)

### Community 303 - "BrainFailoverManager"
Cohesion: 0.09
Nodes (18): BrainFailoverManager, ProviderInfo, Any, Record a successful call — resets the circuit breaker., Permit one probe call without claiming the provider succeeded. This is the…, Seconds until the soonest cooling provider is probeable again. ``None`` when no…, True when a provider's cooldown window is wider than any it could legitimately…, Record a provider failure — opens the circuit breaker on threshold. (+10 more)

### Community 304 - "TestDiagCommand"
Cohesion: 0.09
Nodes (12): TestCase, _GlobalsRestorer, tests/test_telegram_diag.py Regression test for the new ``/diag`` (admin)…, Drive _process_update with a /diag message and return the response. Restores…, The Operator Charter §"Telegram bot" silent-drop path MUST surface a…, Once we've warned once, subsequent silent drops must NOT spam the log., Snapshot/restore tb globals + TELEGRAM_POLLER_DISABLED env var., ``/diag`` behaviour under admin + non-admin + empty-allowlist states. (+4 more)

### Community 305 - "test_nvidia_model_discovery.py"
Cohesion: 0.06
Nodes (15): _clear_cache(), nm(), Tests for `.github/scripts/nvidia_models.py` — live model discovery. The static…, Discovery must never be the reason a run dies., What callers actually use: live ids when available, static otherwise., Every id that answered 410 on 2026-08-27 must be gone from it., Silent degradation is the defect this whole module exists to end.…, resolve_model_ids memoises; a cached value would leak across tests. (+7 more)

### Community 306 - "test_workspace_isolation.py"
Cohesion: 0.16
Nodes (16): Tests for workspace isolation model (Area A). Covers: - Unique workspace path…, Security-oriented tests for workspace isolation (Area C4). Covers: - No path…, InvalidJobIdError, InvalidSessionIdError, Exception, workspace/errors.py — Structured, actionable workspace errors. Every error…, Base class for all workspace errors., WorkspaceCleanupBlockedError (+8 more)

### Community 307 - "test_direct_chat_evolution.py"
Cohesion: 0.11
Nodes (25): DirectChatDoctor, PreflightIssue, PreflightReport, BaseModel, doctor.py — Agent-side doctor diagnostics: environment, provider, and workspace…, asyncio, When git is missing and no GitHub token is present, the doctor should report…, test_missing_git_and_token() (+17 more)

### Community 308 - "SkillLibrary"
Cohesion: 0.11
Nodes (21): Any, Path, agent/skills.py — Skill Library Indexes and searches agent skills from local…, Discover, search, and retrieve agent skills. Usage:: lib = SkillLibrary() #…, Full-text search across name, description, and content., Register an MCP-hosted skill pack entry., Skill, SkillLibrary (+13 more)

### Community 309 - "StuckDetector"
Cohesion: 0.13
Nodes (24): Any, Stuck detection for the agent tool loop — adapted from OpenHands. OpenHands…, Canonical identity of one observation, ignoring incidental fields., Consecutive repetitions required before a pattern counts as stuck., Detects repeating patterns in a step's observation history., Return a human-readable reason when the loop looks stuck, else None., _signature(), StuckDetector (+16 more)

### Community 310 - "agents/api.py"
Cohesion: 0.14
Nodes (30): _apply_activity_status(), create_agent(), delete_agent(), get_agent(), _get_user(), list_agents(), list_runtime_agents(), Any (+22 more)

### Community 311 - "High-Agency Frontend Skill"
Cohesion: 0.06
Nodes (30): 10. FINAL PRE-FLIGHT CHECK, 1. ACTIVE BASELINE CONFIGURATION, 2. DEFAULT ARCHITECTURE & CONVENTIONS, 3. DESIGN ENGINEERING DIRECTIVES (Bias Correction), 4. CREATIVE PROACTIVITY (Anti-Slop Implementation), 5. PERFORMANCE GUARDRAILS, 6. TECHNICAL REFERENCE (Dial Definitions), 7. AI TELLS (Forbidden Patterns) (+22 more)

### Community 312 - "LlmProviderConfig"
Cohesion: 0.16
Nodes (29): _anthropic_headers(), _anthropic_payload(), _anthropic_response_text(), _auth_headers(), chat_completion_text(), list_openai_models(), LlmProviderConfig, normalize_base_url() (+21 more)

### Community 313 - "Quick-Note GitHub Issues Processing - Session Summary"
Cohesion: 0.06
Nodes (30): 1. Stop-Slop Quality Filter (Issue #229), 2. ECC Integration Study (Issue #266 & #230), ✅ Analysis & Comments (16 items), Architecture Alignment, Branch: `docs/ecc-adoption-analysis`, Branch: `feat/stop-slop-quality-filter`, Deliverables, ECC Patterns Adopted (+22 more)

### Community 314 - "test_failover_silent_exhaustion.py"
Cohesion: 0.11
Nodes (23): Paid-tier providers admitted to the chain and not yet attempted. Empty when the…, _untried_paid(), _FM, _P, Regression tests for a chain that fails silently. From a real incident:…, Reserve logic must never break the chain it is meant to protect., The incident case: providers ran, none reported a reason., The genuinely-empty chain keeps its original, correct wording. (+15 more)

### Community 315 - "sync/service.py"
Cohesion: 0.14
Nodes (30): FastAPI dependency: require Power User or Admin role. Raises 403 otherwise., require_power_user(), add_peer(), get_folder_index(), get_sync_file(), get_sync_service(), list_conflicts(), list_peers() (+22 more)

### Community 316 - "test_mcp_governance.py"
Cohesion: 0.12
Nodes (29): get_audit_log(), Return the process-wide audit log, created on first use., _call(), _engine(), Governance on the MCP HTTP surface — threat-model T11. Before this,…, Same Golden Rule guarantee as the in-process gate., No UI is attached to this surface, so holding the socket would hang it., Headers are a hint, not a credential — and the baseline holds anyway. A caller… (+21 more)

### Community 317 - "switch_brain.py"
Cohesion: 0.15
Nodes (30): detect_ollama_models(), dim(), fail(), get_auth_headers(), get_brain_config(), get_ngrok_tunnel_url(), header(), info() (+22 more)

### Community 318 - "OrchestratorCheckpointStore"
Cohesion: 0.09
Nodes (14): _NoopDB, OrchestratorCheckpointStore, Any, services/orchestrator_checkpoint.py — Durable step-level checkpointing Issue…, Restore in-flight runs at startup. Called during backend bootstrap. Returns a…, Fallback in-memory store when no DB is available., Persist orchestrator runs so they survive restarts., Persist a WorkflowRun snapshot. (+6 more)

### Community 319 - "session_retro.py"
Cohesion: 0.13
Nodes (29): cluster_friction(), clusters_to_issues(), collect_friction_events(), FrictionCluster, FrictionEvent, judge_cluster(), Any, services/session_retro.py — session retrospective mining. Closes the gap… (+21 more)

### Community 320 - "test_autonomy_gate.py"
Cohesion: 0.12
Nodes (28): agent_branch_name(), assert_agent_can_merge(), assert_agent_can_write(), AutonomyViolation, is_protected_branch(), _protected_branches(), Autonomy gate — enforce 'agents propose via PR, humans merge'. The agency can…, Raised when an agent-initiated action would exceed the propose-PR policy. (+20 more)

### Community 321 - "test_backend_server_features.py"
Cohesion: 0.08
Nodes (16): _append_agent_session_message(), _mask_observations(), Truncate tool/observation content in older messages to prevent context bloat., _run_agent_loop(), anyio, Tests for backend/server.py cloud model catalog, multi-agent loop, and context…, Planner and Verifier should be assigned to reasoning (DeepSeek/QwQ) models., Verify _run_agent_loop calls AgentRunner.run and returns the summary. (+8 more)

### Community 322 - "SeoFixer"
Cohesion: 0.15
Nodes (13): One concrete remediation performed (or proposed) by the fixer., Result of a fixer run., SeoFixAction, SeoFixResult, _humanize_filename(), BeautifulSoup, Path, services/seo_fixer.py - Repo-Aware SEO Auto-Fixer When a company has a code… (+5 more)

### Community 323 - "test_colibri_provider.py"
Cohesion: 0.12
Nodes (28): colibri_enabled(), colibri_provider_config(), colibri_status(), ProviderConfig, providers/colibri.py — Free local GLM-5.2 brain served by JustVugg/colibri.…, Return True iff the operator opted in via ``COLIBRI_ENABLED=true``., Cheap status snapshot for tests + admin UI., Return the ``ProviderConfig`` for the local colibri server, or ``None`` when… (+20 more)

### Community 324 - "analyze_page"
Cohesion: 0.13
Nodes (11): analyze_page(), BeautifulSoup, Run every page-scoped check against one HTML document (no network). Returns a…, _visible_text(), codes(), parametrize, TestBadPage, TestCleanPage (+3 more)

### Community 325 - "_execute_skill_impl"
Cohesion: 0.10
Nodes (26): _execute_skill_impl(), _get_agile_manager(), _get_portfolio_manager(), Any, Live Graphify executor — queries the codebase knowledge graph. Order of…, Live council reviewer — deterministic, rules-based multi-perspective review…, Recommend skills based on detected systems and provisioned specialists. With no…, Execute a skill by ID and update its execution counters. (+18 more)

### Community 326 - "test_force_cleanup_conditional_delete.py"
Cohesion: 0.10
Nodes (14): _FlakyPersistence, _memory_store(), _orphan(), asyncio, _RaceLostPersistence, _RaceWonPersistence, tests/test_force_cleanup_conditional_delete.py Covers two changes to the…, Every removal path fails at the durable store. (+6 more)

### Community 327 - "test_rag_context.py"
Cohesion: 0.12
Nodes (23): RAGContextBuilder, Retrieve, decay, and compress context to fit a configurable token budget.…, Tests for agent/rag_context.py — Advanced RAG context management layer. Imports…, test_builder_doc_budget_fraction(), test_builder_docs_dropped_count(), test_builder_empty_both(), test_builder_empty_documents(), test_builder_empty_history() (+15 more)

### Community 328 - "ProjectScaffolder"
Cohesion: 0.13
Nodes (20): ProjectScaffolder, Any, Path, agent/scaffolding.py — Project Scaffolding Creates new project skeletons from…, Apply named project templates to a target directory. Usage:: s =…, Write template files into *target_dir*. Skips existing files unless…, ScaffoldResult, Template (+12 more)

### Community 329 - "Initiative"
Cohesion: 0.09
Nodes (13): Initiative, Create and register a new initiative, returning it., Add a pre-built Initiative (e.g. from the intelligence layer)., Look up an initiative by ID., A portfolio initiative (epic) prioritised via WSJF. WSJF (Weighted Shortest Job…, Aggregate cost of delay (CoD) used as the WSJF numerator., Associate an agile sprint that delivers part of this initiative., Tests for the Initiative dataclass and WSJF maths. (+5 more)

### Community 330 - "test_tasks_awaiting_approval_api.py"
Cohesion: 0.14
Nodes (26): quick_notes_submit(), _QuickNoteBody, Submit a quick-note URL or instruction from the dashboard FAB., Comment or reply on a task., TaskComment, Set the global task store instance (e.g., during app startup with MongoDB)., set_task_store(), _inmem_store() (+18 more)

### Community 331 - "generate_context.py"
Cohesion: 0.12
Nodes (28): _build_caller_chain(), _build_context_doc(), _build_pr_description(), _build_todos_md(), _build_user_message(), _call_cerebras(), _call_claude(), _call_groq() (+20 more)

### Community 332 - "v3_auth.py"
Cohesion: 0.11
Nodes (28): _get_admin_email(), _get_admin_name(), _get_admin_secret(), _get_bearer_token(), _get_current_user(), login(), LoginRequest, LoginResponse (+20 more)

### Community 333 - "SeoFixRequest"
Cohesion: 0.14
Nodes (11): Request to remediate auto-fixable findings in a local code repository., SeoFixRequest, Convenience wrapper used by the API layer and skill executor., run_fixes(), Path, tests/test_seo_fixer.py - repo-aware SEO auto-fixer tests (issue #533)., repo(), TestApply (+3 more)

### Community 334 - "SteeringInjector"
Cohesion: 0.11
Nodes (10): Any, Inject steering instructions into the message list. Args: messages: The…, Inject steering into an OpenAI chat payload dict. Modifies and returns the…, Build the steering instruction text based on format., Build steering as natural-language quality instructions., Build steering as ChatML-formatted tokens., Build steering as Nemotron-specific steering tags., Inject steering tokens into prompts for quality-biased generation. Supports… (+2 more)

### Community 335 - "test_claude_setup_audit.py"
Cohesion: 0.16
Nodes (23): AuditReport, _check_agents_config(), _check_claude_md_sections(), _check_hooks(), _check_skills(), _check_state(), CheckResult, main() (+15 more)

### Community 336 - "decide"
Cohesion: 0.12
Nodes (16): decide(), Decision, issue_number_from_branch(), main(), scripts/triage_orphaned_context_prs.py Decide what to do about a draft context…, Return the issue number a context branch was generated for, if any., Decide how to recover the *issue* behind an orphaned draft PR. *issue* is the…, _issue() (+8 more)

### Community 337 - "OrchestratorQueue"
Cohesion: 0.08
Nodes (11): OrchestratorQueue, Any, _QueueEntry, Async FIFO queue that limits concurrent orchestrator run executions.…, Enqueue a run for async execution. Returns immediately. ``fn(*args, **kwargs)``…, Enqueue a run and return a future that resolves when it completes., enqueue_and_wait() callers DO await the future, so failures must still raise…, Drain loop must handle dequeue from empty queue gracefully. (+3 more)

### Community 338 - "test_internal_agent_did_work.py"
Cohesion: 0.12
Nodes (28): _compute_did_work(), tests/test_internal_agent_did_work.py — step-success-ratio gate tests. Tests…, judge_verdict=BLOCKED → always FAILURE, even with 10/10 applied., judge_verdict=BLOCKED → always FAILURE, even with a long report., Even with unique_files, 1/22 applied → FAILURE (steps_ok gate)., With 9/10 applied + unique_files → SUCCESS., Replicate the did_work logic from internal_agent.py:509-533., 1/22 applied (4.5%) → should be FAILURE (the bug case). (+20 more)

### Community 339 - "test_purge_backlog.py"
Cohesion: 0.09
Nodes (20): FakeTaskStore, MonkeyPatch, Task, tests/test_purge_backlog.py — 2026-07-03 crash-loop remediation. Covers: - POST…, The per-minute tick must requeue at most ONE blocked task, keep its…, Drive _maybe_boot_purge with fakes; return (purged, marker_writes). ``core``…, A failed purge must NOT record the nonce — it retries next boot., A PARTIAL purge (error markers inside the summary) must not record the nonce… (+12 more)

### Community 340 - "TerminalPanel"
Cohesion: 0.13
Nodes (20): _is_command_not_found(), _powershell_quote(), Any, agent/terminal.py — Terminal Panel Reads the rendered terminal output buffer —…, Try to read the pane buffer via tmux capture-pane., Return a minimal snapshot with terminal dimensions only., Capture the current terminal buffer as a :class:`TerminalSnapshot`. Usage::…, Capture the current terminal state. Never raises. (+12 more)

### Community 341 - "Python Dependencies (`requirements.txt`)"
Cohesion: 0.07
Nodes (27): AI / LLM, AI Tooling, Browser Automation, Cloud / Infrastructure, Core Web Framework, Data Processing, DEP-001 [HIGH] — No Python Lockfile, DEP-002 [HIGH] — `playwright` as a Runtime Dependency (+19 more)

### Community 342 - "Technical Debt Register — local-llm-server"
Cohesion: 0.07
Nodes (27): Category 10 — Patch Files in Root, Category 1 — God Files, Category 2 — API Key Naming Confusion, Category 3 — Dual App Architecture, Category 4 — Dual Storage Backend, Category 5 — Test File Sprawl, Category 6 — Environment Variable Documentation, Category 7 — Missing Type Annotations (+19 more)

### Community 343 - "FeatureEntry"
Cohesion: 0.08
Nodes (11): FeatureEntry, Any, BaseModel, One entry in the support matrix., Load canonical features and apply per-feature then bulk env overrides., Apply a config override string like 'stable', 'beta', 'disabled', 'enabled',…, Return the feature entry if available, or raise FeatureUnavailableError., Alias for check_available() — returns the entry or raises… (+3 more)

### Community 344 - "ProviderConsole.jsx"
Cohesion: 0.08
Nodes (19): discoverLlmModels(), getLlmProviders(), getLlmStatus(), probeLlmProviders(), reloadLlmConfig(), setLlmProviderEnabled(), setLlmStrategy(), ALIASES (+11 more)

### Community 345 - "SeoAuditReport"
Cohesion: 0.21
Nodes (22): An agent-delegable remediation work package derived from the findings. Findings…, Complete result of one audit run., SeoAuditReport, SeoDelegationTask, Paragraph, _appendix_full_findings(), _appendix_worst_pages(), _appendix_wsjf_roadmap() (+14 more)

### Community 346 - "webui/router.py"
Cohesion: 0.11
Nodes (27): get_brain_preference(), Return the operator's brain provider preference. Values: - ``"nvidia"`` —…, Operator can set BRAIN_PREFERENCE=colibri without it being rejected., test_get_brain_preference_accepts_colibri(), _admin_out(), AdminCommandBody, _anthropic_chat_payload(), _anthropic_text() (+19 more)

### Community 347 - "TrafficDirector"
Cohesion: 0.11
Nodes (11): get_director(), In-process traffic distribution and budget accounting for providers., EWMA latency in ms; never-sampled providers sort first. Returning -1.0 for an…, Clear all counters (tests only)., Return the process-singleton TrafficDirector., TrafficDirector, Tests for packages/ai/traffic_director.py — traffic distribution across…, `int(0.5)` is 0, and a cap of 0 makes `in_flight >= cap` true at zero in-flight… (+3 more)

### Community 348 - "webui/frontend/package.json"
Cohesion: 0.07
Nodes (26): @types/react, @types/react-dom, typescript, vite, @vitejs/plugin-react, dependencies, react, react-dom (+18 more)

### Community 349 - "CostAttributor"
Cohesion: 0.10
Nodes (16): CostAttributor, CostReport, get_cost_attributor(), Any, Tracks and attributes LLM costs per model, phase, and provider. Usage:: attr =…, Record a single LLM call's usage., Batch record multiple usage entries. Returns number recorded., Estimate USD cost for a given model and token count. Looks up the per-model… (+8 more)

### Community 350 - "test_regression.py"
Cohesion: 0.10
Nodes (22): browser_login(), main(), Full desktop regression suite., Full mobile regression suite (navigation + key page loads)., Log in through the browser UI. Returns True on success., Comprehensive Playwright Regression Suite — LLM Relay Control Plane Covers…, API Key CRUD: create, copy, list, delete., Tasks: create, list, view. (+14 more)

### Community 351 - "test_agent_scripts_share_one_model_list.py"
Cohesion: 0.10
Nodes (17): _assigned_names(), models(), parametrize, The three autonomous agent scripts must share one NVIDIA model list.…, `review_agent.py` does `for model in ...` and passes it as `model=`., `apply_review.py` does `for model, desc in ...`., Breadth now comes from discovery, not from this list. The old list held three…, apply_review.py listed the same model twice, wasting a retry. (+9 more)

### Community 352 - "test_crispy_burn_in.py"
Cohesion: 0.07
Nodes (27): burn_in(), tests/test_crispy_burn_in.py — N4 follow-up: burn-in criteria evaluator. Tests…, window_days below 7 → not ready (need at least a week of evidence)., PhaseSequenceError in last_failure_reasons → not ready (workspace isolation…, Non-PhaseSequenceError failures (assertion errors, etc.) don't block promotion…, Exact threshold values meet the criteria (>=, not >)., window_days=None (no runs yet, but total_runs > 0 somehow) is treated as 0 —…, The --json flag lets the workflow (and tests) run offline against a saved… (+19 more)

### Community 353 - "_Recorder"
Cohesion: 0.09
Nodes (14): What the loop sends, and just as importantly what it does not., Anything but NVIDIA resolves its own default_model., response_cache keys on (model, messages, temperature, max_tokens, stop) — not…, The router hands back parsed JSON, not SDK objects. Rewriting the loop for…, Guards the specific slip: attribute access on a parsed-JSON dict., A provider that omits `function` must not take the run down., Codex review, #1369 (P1): naming no model is not safe for NVIDIA. With no model…, Pins the premise, so this guard cannot quietly stop applying. Not that the… (+6 more)

### Community 354 - "test_skill_registry_boot_refresh.py"
Cohesion: 0.12
Nodes (16): clean_task(), _install(), _NullDispatcher, _NullRuntimeManager, asyncio, Exception, The configured remote skill repos must be fetched without a human trigger.…, Remote skills are optional; a rate limit must not surface as an error. (+8 more)

### Community 355 - "SprintMetrics"
Cohesion: 0.10
Nodes (12): Complete the sprint and record velocity., Calculate current sprint metrics., Velocity and burndown metrics for a sprint., Percentage of story points completed., Points per day needed to complete on time., Whether the sprint is on track to complete., Derive a qualitative health signal from the metrics. - COMPLETE: all points…, SprintMetrics (+4 more)

### Community 356 - "tests/conftest.py"
Cohesion: 0.10
Nodes (25): _get_current_user_thunk(), _get_optional_user_thunk(), Request, get_current_user(), get_optional_user(), Get user if authenticated, otherwise return None (for public endpoints)., Item, Config (+17 more)

### Community 357 - "Deploy: FreeBuff Telegram bot (24×7)"
Cohesion: 0.07
Nodes (25): Agents, Environment variables, Free model set, FreeBuff — free-NVIDIA coding agent, `/freebuff <task>`, HTTP API, Running 24×7, Telegram phone control (+17 more)

### Community 358 - "Claude Code + Qwen Local Setup"
Cohesion: 0.07
Nodes (27): 1. Set environment variables, 2. Start Claude Code, 3. Verify model routing, Anthropic SDK (Python), Architecture, "Authentication error" or 401, Claude Code + Qwen Local Setup, Claude Code reports "token limit exceeded" (+19 more)

### Community 359 - "provider_base_url"
Cohesion: 0.09
Nodes (19): provider_base_url(), Resolve the Ollama base URL the UI controls — DB value wins over env.…, Return the OpenAI-compatible base URL for *provider* (env- and UI-aware)., resolve_ollama_base_url(), Any, _FakeResp, tests/test_brain_ollama_base_url.py The Ollama base URL is UI-configurable and…, An Ollama probe with base_url must hit THAT url's /api/tags, not the saved one. (+11 more)

### Community 360 - "model_discovery.py"
Cohesion: 0.10
Nodes (23): dead_models(), discover_models(), _fresh_entry(), _models_url(), _parse_ids(), Any, Ask a provider which models the configured API key may actually use.…, Return the unexpired cache entry, distinguishing "absent" from "asked and got… (+15 more)

### Community 361 - "ModelRouter"
Cohesion: 0.13
Nodes (13): Dynamic model router package. Public API:: from router import get_router,…, ModelRouter, Any, Central model router. Create one instance (use ``get_router()``). ``route()``…, Decide which Ollama model to use for this request. Args: requested_model: Model…, Return *model* if it is available in Ollama, else the first available fallback.…, Full record of a routing decision — both what was chosen and why. Fields:…, Build an ordered list of alternative models to try if *primary* fails. (+5 more)

### Community 362 - "keepalive.py"
Cohesion: 0.14
Nodes (26): _check_ollama(), _check_render(), _default_ollama_base(), _default_render_url(), _env_bool(), _loaded_ollama_prefixes(), _log(), _log_path() (+18 more)

### Community 363 - "test_brain_availability_doctor.py"
Cohesion: 0.16
Nodes (24): brain_availability_summary(), Non-secret answer to "can the brain answer a request right now?". Three callers…, _doctor(), _P, _patch_providers(), Tests for the public brain-availability diagnosis and the supervisor's use of…, Minimal provider stand-in matching what the summary reads., Wrongly pausing every goal is worse than one wasted re-drive. (+16 more)

### Community 364 - "_is_dns_failure"
Cohesion: 0.10
Nodes (18): _is_dns_failure(), _probe_failure_reason(), BaseException, Turn a probe exception into an operator-actionable one-line reason. A dead…, True when *exc* (or anything it wraps) is a name-resolution failure., asyncio, Exception, parametrize (+10 more)

### Community 365 - "CompanyAgencyService"
Cohesion: 0.09
Nodes (17): CompanyAgencyService, _is_runtime_available_sync(), _pick_available_runtime(), Any, SpecialistFamily, Orchestrates specialist activation, runtime startup, and 24x7 scheduling for a…, Return the best available runtime for a specialist family. Checks available…, Return the ordered runtime preferences for a specialist family. (+9 more)

### Community 366 - "isolated_telegram_config"
Cohesion: 0.11
Nodes (11): isolated_telegram(), isolated_telegram_config(), tests/_telegram_test_utils.py Snapshot/restore helper for ``telegram_bot``…, Pytest fixture alias for ``isolated_telegram_config``. Use this in tests that…, Snapshot+restore ``tb`` globals + ``TELEGRAM_POLLER_DISABLED``. Keyword args…, tests/test_telegram_test_utils.py Self-test suite for…, The helper's ``__exit__`` runs ``if original is _MISSING: if hasattr:…, If a tracked attr is absent under ``tb`` at scope entry, the helper snapshots… (+3 more)

### Community 367 - "_captured_request_headers"
Cohesion: 0.13
Nodes (13): _captured_request_headers(), _make_client(), Any, tests/test_mcp_routing_headers.py — MCP 2026-07-28 Mcp-Method / Mcp-Name…, Run client.call_tool() and capture the request headers., Extra headers must not displace existing required headers., extra_headers passed to _rpc are method-specific; this tests isolation., Run a single _rpc() call against a mock httpx.AsyncClient and return the… (+5 more)

### Community 368 - "TestNoNvidiaFallbackIsRetired"
Cohesion: 0.09
Nodes (14): _nvidia_default(), parametrize, The platform-wide NVIDIA default must not be a retired model.…, The defect was never confined to one file. Eight modules independently spelled…, ``(path, model_id)`` for every literal used as the env-var fallback., A regex that silently matched nothing would pass every assertion., ``PROVIDER_CANDIDATES['nvidia']`` is tried in order, so a dead entry is a…, Planner/executor/verifier fall back to a literal when no ``AGENT_*_MODEL`` is… (+6 more)

### Community 369 - "test_scheduler_hydration_bounded.py"
Cohesion: 0.09
Nodes (20): _BrokenScheduler, _fake_schedule_store(), _FakeStore, _FastScheduler, _HangingScheduler, _isolate_warmup_overflow(), asyncio, NoReturn (+12 more)

### Community 370 - "CommitTracker"
Cohesion: 0.16
Nodes (20): CommitAttribution, CommitTracker, Path, agent/commit_tracker.py — AI Commit Attribution Tags git commits with metadata…, Create git commits enriched with agent-session attribution trailers. Usage::…, Return ``--trailer`` arguments ready to append to a ``git commit`` call., Stage *files* and create an attributed commit. Returns the commit SHA on…, _init_repo() (+12 more)

### Community 371 - "VoiceCommandInterface"
Cohesion: 0.14
Nodes (15): Any, agent/voice.py — Voice Command Interface Hands-free agent interaction: record…, Transcribe raw PCM *audio_bytes* to text., Record then transcribe in one call., Record → transcribe → return text for hands-free agent prompting. Usage:: vc =…, Record *duration_s* seconds of audio. Returns raw PCM bytes (int16 LE, 16 kHz…, _stub_result(), TranscriptionResult (+7 more)

### Community 372 - "Performance Analysis — local-llm-server"
Cohesion: 0.08
Nodes (25): 1. Rate Limiter Performance, 2. Ollama Connection Handling, 3. Model Router Performance, 4. Agent Execution Performance, 5. Backend Server Performance, 6. Frontend Performance, 7. Streaming Performance, PERF-001 [HIGH] — Synchronous Lock in Async Context (+17 more)

### Community 373 - "LLM Router — troubleshooting"
Cohesion: 0.08
Nodes (24): Embeddings, LiteLLM compatibility mode, LLM Router — local model guide, LM Studio, LocalAI, Ollama, Preferring local, Registering local models (+16 more)

### Community 374 - "autonomous_fix.py"
Cohesion: 0.14
Nodes (18): _decline(), _extract_pytest_failure(), _fetch_failure_context(), _list_target_prs(), main(), _post_comment(), _pr_head(), _prior_attempt_count() (+10 more)

### Community 375 - "implement_agent.py"
Cohesion: 0.11
Nodes (22): build_tool_calling_router(), main(), _nvidia_candidates(), _openai_tools_to_anthropic(), Any, Safely insert an entry under ## [Unreleased] without touching the rest of the…, Convert OpenAI function-calling tool schemas to Anthropic tool schemas., Run the implementation agent loop using Claude Opus via Anthropic SDK. Returns… (+14 more)

### Community 376 - "output_filter.py"
Cohesion: 0.08
Nodes (22): _count_remaining(), _filter_curl(), _filter_docker(), _filter_generic(), _filter_git(), _filter_ls(), _filter_npm(), _filter_pip() (+14 more)

### Community 377 - "control_registry.py"
Cohesion: 0.14
Nodes (20): packages/config/control_catalogue.py — the 109 operator-facing controls. The…, coerce(), _coerce_choice(), _coerce_number(), _coerce_toggle(), Any, packages/config/control_registry.py — the platform-control API. The public…, Normalise *value* into the env string this control stores. Raises… (+12 more)

### Community 378 - "analyze"
Cohesion: 0.11
Nodes (16): Analysis, analyze(), _classify(), _failure_table(), main(), Return the exhaustion :class:`Analysis` for a run's captured *output*., scripts/analyze_exhaustion.py Decide whether a run that ran out of retries has…, The verdict plus the human-readable justification behind it. (+8 more)

### Community 379 - "monitor_lib.py"
Cohesion: 0.17
Nodes (25): colibri_dir(), download_log_path(), download_status(), DownloadStatus, _heartbeat_to_file(), is_process_alive(), model_dir(), monitor_log_path() (+17 more)

### Community 380 - "brain_failover.py"
Cohesion: 0.12
Nodes (25): _disabled_from_mongo(), _disabled_from_sqlite(), _is_paid_allowed_db(), _kv_connect(), _kv_path(), _mongo_db(), _mongo_enabled(), _mongo_unavailable() (+17 more)

### Community 381 - "get_failover_manager"
Cohesion: 0.09
Nodes (18): get_failover_manager(), Return the singleton BrainFailoverManager., Reset the singleton (for tests)., reset_failover_manager(), _clean_env(), _FakeAsyncClient, _FakeResponse, Regression test: HTTP 413 (Payload Too Large) must fail over to the next… (+10 more)

### Community 382 - "test_telegram_approval_e2e.py"
Cohesion: 0.12
Nodes (25): _approve_execution_via_rest(), _delete_task(), _extract_admin_token(), _login_admin(), _looks_like_admin_token(), _open_dashboard(), _poll_task_execution_approved(), Any (+17 more)

### Community 383 - "test_brain_migration_writes_a_live_model.py"
Cohesion: 0.10
Nodes (17): _migration_block(), parametrize, Path, The migration that rescues a stale brain config must not write a dead model.…, Rows this migration poisoned must be able to recover. `needs_reset` is the only…, Groq's configured ids were not in the account's catalogue at all., A role preset the rotation cannot fall back to is a single point of failure., The class-level guard. Four writers exist; two carried literals. Chasing… (+9 more)

### Community 384 - "test_daily_automation_2026_08_03.py"
Cohesion: 0.11
Nodes (16): _load_yaml(), tests/test_daily_automation_2026_08_03.py — Daily automation (2026-08-03).…, The rotation losing every entry is the outage this series began with., brain_config.py anthropic candidates must exactly match models.yaml (order and…, brain_config.py aerolink candidates must exactly match models.yaml (order and…, test_aerolink_candidates_match_yaml(), test_anthropic_candidates_match_yaml(), test_brain_config_nvidia_candidates_are_not_empty() (+8 more)

### Community 385 - "test_provider_enable_disable.py"
Cohesion: 0.10
Nodes (13): one_provider(), asyncio, parametrize, Per-provider on/off switch, with auto-disable for unfixable failures only.…, The critical guard: disabling on 429 would switch off every free provider., Storage problems must degrade, not raise., _run(), _StubManager (+5 more)

### Community 386 - "test_telegram_mutating_commands.py"
Cohesion: 0.08
Nodes (19): _catalogue_preset(), _make_mock_response(), tests/test_telegram_mutating_commands.py — N5 acceptance: /setbrain + /merge.…, Build a mock httpx.Response., A successful /setbrain call must: 1. send the X-Service-Token header 2. PATCH…, When the backend's liveness probe fails (HTTP 422), the bot reply must surface…, 503 = backend doesn't have SERVICE_TOKEN set. The bot reply must tell the…, A successful /merge call returns the merge SHA + actor attribution so the… (+11 more)

### Community 387 - "TestWorkflow"
Cohesion: 0.08
Nodes (6): Tests for agents/workflow_engine.py — SuperClaude Workflow Engine. Uses…, Tests for WorkflowEngine., Tests for Task dataclass., TestTask, TestWorkflow, TestWorkflowEngine

### Community 388 - "CheckRun"
Cohesion: 0.12
Nodes (10): WorkflowRun, tests/test_workflow_models.py — Unit tests for workflow/models.py., TestApprovalGate, TestCheckRun, TestWorkflowRun, Trigger verification for all applied-but-unverified slices., ApprovalGate, CheckRun (+2 more)

### Community 389 - "_undeclared"
Cohesion: 0.10
Nodes (15): _cases(), parametrize, Path, A shell variable a workflow never sets expands to empty, and says nothing. On…, A selector that matched nothing would make every assertion vacuous., A guard that cannot fail is not a guard. These reconstruct the 2026-08-29…, The specific regression: the squash subject that reached master., Declared is not the same as non-empty — `steps.issue` can be skipped. (+7 more)

### Community 390 - "1. The Rules"
Cohesion: 0.08
Nodes (25): 1. The Rules, 2. Standing Instructions — agent discipline, 3. What this repo is, 4. Architecture reference, 5. Bill of materials, 6. Key commands, 7. Environment variables, 8. Where else to look (+17 more)

### Community 391 - "reset_store"
Cohesion: 0.11
Nodes (23): Reset the store singleton (used in tests). Also resets the motor client…, reset_store(), tests/test_motor_event_loop_isolation.py — regression test for the flaky…, ``reset_store()`` must clear ``db.mongo_store._client`` and ``_db``, not just…, ``reset_store()`` must also clear the ``db._store`` wrapper (the original…, The ``client`` fixture in conftest.py must call ``reset_store()`` before…, After ``reset_store()``, the next ``MongoStore._get_db()`` call must create a…, test_client_fixture_calls_reset_store_before_lifespan() (+15 more)

### Community 392 - "Session Handoff — 2026-06-15"
Cohesion: 0.08
Nodes (24): Context the next session will need, Critical environment variables, Files changed today (for code archaeology), How to resume, Key files to know, Key labels, P0 — Add a regression test for the draft-PR safety guards, P1 — Watch Run 27481814863 for issue #504 and verify end-to-end (+16 more)

### Community 393 - "TASK 4 — End-to-end approval-gate test"
Cohesion: 0.08
Nodes (24): 3.1 — Confirm env vars on the **web** service, 3.2 — Confirm single-poller guard on the **worker**, 3.3 — Verify the bot responds (human-in-the-loop), 3.4 — TASK 3 acceptance, 4.1 — Acquire an admin session, 4.2 — Trigger an outward-facing workflow run, 4.3 — Watch the run until it pauses, 4.4 — Confirm the Telegram message arrived (+16 more)

### Community 394 - "models/seo_audit.py"
Cohesion: 0.10
Nodes (13): models/seo_audit.py - SEO / GEO / AIO Audit Contracts Typed Pydantic models for…, Static definition of a single audit check (catalog entry)., SeoCheckDefinition, auto_fixable_checks(), _c(), get_check(), list_checks(), services/seo_checks.py - SEO / GEO / AIO Check Catalog The authoritative… (+5 more)

### Community 395 - "test_connector_registry.py"
Cohesion: 0.12
Nodes (19): _connectors(), ConnectorSpec, get_connector(), list_connectors(), Any, packages/integrations/connector_registry.py — the connector catalogue. The…, Execute the ``webhook`` connector: POST *payload* as JSON to *url*. Fails soft…, A declared connector, independent of whether it is currently usable.… (+11 more)

### Community 396 - "test_rate_limit_backoff_survives.py"
Cohesion: 0.12
Nodes (14): clear_all_locks(), Clear all probe-lock entries (for test teardown). Companion to…, Clear module-level cooldown + probe-lock state before every test so tests don't…, reset_provider_cooldowns(), anyio, Regression guard: a rate-limit cooldown must survive, on every route.…, All providers cooling from 429s: the bypass must decline, not spend a request…, TestRouterBypassSkipsRateLimited (+6 more)

### Community 397 - "TemporalContextGraph"
Cohesion: 0.10
Nodes (14): demo_agent_tracking(), datetime, Temporal context graph inspired by Graphiti…, Get history of an entity between two times, Get current state of an entity (most recent fact), Query facts with pattern matching, Get source (provenance) of a specific fact, A fact at a specific point in time (+6 more)

### Community 398 - "TestClassifyPlainText"
Cohesion: 0.08
Nodes (6): tests/test_inbound_router.py Pytest coverage for…, The 3500-char default matches the design recommendation; below the delivered…, TestBigPasteThreshold, TestClassifyPlainText, TestSanitizePasteForPreview, TestSavePaste

### Community 399 - "test_service_token.py"
Cohesion: 0.08
Nodes (19): tests/test_service_token.py — N5 acceptance: service-token auth surface. Tests…, Near-miss tokens must not pass (no prefix-match, no fuzzy match)., After verification, the module must NOT hold the plaintext token — only the…, The token plaintext must NEVER appear in logs. Capture every log record emitted…, The module must use hmac.compare_digest (not ==) for the comparison — timing…, The service token must only gate a narrow allowlist of endpoints — not all of…, When SERVICE_TOKEN is rotated in the env, the new token must verify (within the…, Load services.service_token fresh in each test so env-var changes take effect. (+11 more)

### Community 400 - "verify_token"
Cohesion: 0.12
Nodes (24): Test JWT token creation and verification., Test refresh token creation and validation., Test that access token fails with refresh validation., Test refreshing access token with refresh token., Test that invalid refresh tokens fail gracefully., test_invalid_refresh_token(), test_invalid_token_type(), test_refresh_access_token() (+16 more)

### Community 401 - "github_tools.py"
Cohesion: 0.20
Nodes (23): get_repo(), _get_token(), _get_user(), init_workspace(), list_branches(), list_prs(), list_repos(), BaseModel (+15 more)

### Community 402 - "test_harness_spec.py"
Cohesion: 0.12
Nodes (14): LessonStore, Any, Connection, Path, SQLite-backed store of failure lessons. Thread-safe, zero deps., tests/test_harness_spec.py — the Continual Harness spec. Covers the property…, refine() cannot cite what the store does not return., A workspace is often a third-party repo — its spec file is untrusted. Without… (+6 more)

### Community 403 - "audit_drift"
Cohesion: 0.13
Nodes (22): audit_drift(), _cmd_audit(), _grade(), load_registry(), load_registry_sync(), main(), Namespace, Path (+14 more)

### Community 404 - "TestStreamableHTTPTransport"
Cohesion: 0.13
Nodes (12): Decode a JSON-RPC response body from either JSON or an SSE stream. Streamable-…, SSE uses CRLF on the wire; the trailing \\r must not corrupt the JSON., Existing callers pass a base URL and expect /mcp appended., Render's URL already names the endpoint, so nothing is appended., Build an httpx.Response the client can parse, with a bound request., The plain-JSON path (/mcp-internal) must be unchanged., A Streamable-HTTP reply arrives as SSE data: frames., Progress notifications precede the response; the response wins. (+4 more)

### Community 405 - "Findings"
Cohesion: 0.08
Nodes (23): E2E Tests, Findings, Immediate (Current Sprint), Integration Tests, Live/External Tests (skipped in standard CI), Missing Test Areas, Sprint 1, Sprint 2 (+15 more)

### Community 406 - "Local AI Stack with Docker"
Cohesion: 0.08
Nodes (23): 1. Clone and configure, 2. Start the stack (GPU), 3. Start the stack (CPU only), 4. Pull models (first run), 5. Access services, CPU Only, Data Persistence, Default (GPU) (+15 more)

### Community 407 - "Traffic Distribution Across Providers"
Cohesion: 0.08
Nodes (22): Agent Autonomy Roadmap, Design constraints honored, New environment variables, Proactive rate-limit pacing (free-tier reliability), The eight gaps and what closed them, Verification performed, What was already strong (verified, no changes needed), Why this document exists (+14 more)

### Community 408 - "Implementation Prompt: Rich TaskBoard + Agile Sprint Integration"
Cohesion: 0.08
Nodes (23): 1. Task model extensions (`tasks/models.py`), 2. New task endpoint (`tasks/api.py`), 3. Agile REST endpoints (`backend/server.py`), 4. TaskBoardScreen upgrade (`frontend/src/v5/screens/TaskBoardScreen.jsx`), 4a. "Needs Clarification" 7th column, 4b. Right-side detail panel, 4c. Sprint view mode toggle, 4d. Create-task modal enhancements (+15 more)

### Community 409 - "Telegram Bot Setup"
Cohesion: 0.08
Nodes (24): Admin commands (immediate, no confirmation), Admin commands with approval required, Approval Workflow, Authorization Model, Command Reference, Debugging message delivery, Debugging proxy connection failures, Linux (systemd) (+16 more)

### Community 410 - "video_transcript.py"
Cohesion: 0.12
Nodes (23): caption_tracks(), extract_player_response(), fetch_transcript(), _get(), is_video_url(), parse_json3(), parse_timedtext_xml(), Extract a usable text transcript from a video URL, without an API key. Why this… (+15 more)

### Community 411 - "launcher.py"
Cohesion: 0.11
Nodes (15): get_status(), BaseModel, get, post, Autonomous AI Agency Launcher - One-button service start with web UI. Run this…, Start the FastAPI proxy server., Serve the launcher UI., Get current service status. (+7 more)

### Community 412 - "test_agent_free_brain.py"
Cohesion: 0.09
Nodes (16): allow_paid_brain(), True only when the operator explicitly opted into a paid (Anthropic) brain.…, _FakeAsyncClient, _FakeResponse, _free_env(), Free-brain policy regression tests for the agent runtime (issue #656).…, The core #656 regression: an Anthropic-shaped model must NOT hit…, Free policy + Anthropic-shaped model + NO NVIDIA key → refuse loudly, never… (+8 more)

### Community 413 - "control_overrides.py"
Cohesion: 0.12
Nodes (23): _as_int(), _control_state(), effective_value(), load_overrides(), _policy_updates(), Any, packages/config/control_overrides.py — DB-persisted overrides for platform…, Read the stored overrides. Returns ``{}`` on any storage failure. The fail-open… (+15 more)

### Community 414 - "CollectionLike"
Cohesion: 0.12
Nodes (12): get_storage(), packages/storage/factory.py — storage backend factory. Returns the appropriate…, Return the active storage backend. During migration, this delegates to the…, Reset the storage singleton (for tests)., reset_storage(), CollectionLike, Any, Protocol (+4 more)

### Community 415 - "Native operations"
Cohesion: 0.09
Nodes (21): Maintainer verification, Native operations, Read-only reviewer interpretation, Role pins and spawn contract, Runtime routing evidence, Selective route declaration, preflight, and caching, Worker packet and parent acceptance, Exact mode contracts (+13 more)

### Community 416 - "test_all_features.py"
Cohesion: 0.08
Nodes (10): Comprehensive E2E smoke-test suite — covers every menu, page, and feature of…, TestActivation, TestAgents, TestCompany, TestDashboard, TestOnboarding, TestSecrets, TestSetup (+2 more)

### Community 417 - "test_agency_fix.py"
Cohesion: 0.08
Nodes (23): agency_fix(), tests/test_agency_fix.py — N3 acceptance tests for scripts/agency_fix.py. The…, An edit that produces a syntactically-broken Python file must be rejected —…, An edit that truncates a real code file to a trivial body must be rejected —…, With no issue linked, decline is just an exit-code signal — no API call., When an issue is linked but no GH_PAT/GH_TOKEN is set, the decline fails loudly…, When an issue is linked and the API call succeeds, decline_cleanly returns True…, When the API call itself fails (network error), decline_cleanly returns False… (+15 more)

### Community 418 - "test_v3_auth.py"
Cohesion: 0.19
Nodes (23): _configured_v3_email(), _configured_v3_password(), asyncio, skip, TestClient, Tests for v3 API authentication., Test login endpoint returns valid tokens., Test login with invalid credentials. (+15 more)

### Community 419 - "refine"
Cohesion: 0.17
Nodes (10): propose_entries(), Turn qualifying lessons into candidate entries. A lesson qualifies only when it…, Promote repeated lessons into the spec. Returns the entries added. No-op unless…, refine(), _lesson(), Regressions for defects found in review of this module., The core guarantee: no citation, no entry., TestProposal (+2 more)

### Community 420 - "_status_snapshot"
Cohesion: 0.15
Nodes (22): ArgumentParser, build_parser(), cmd_autostart_install(), cmd_status(), cmd_supervise(), cmd_wait(), _configure_logging(), main() (+14 more)

### Community 421 - "Agent Governance Guide"
Cohesion: 0.09
Nodes (23): A tool call is judged twice, Agent Governance Guide, `[]` and absent mean opposite things, API, Approvals, Architecture, Audit trail, Backends (+15 more)

### Community 422 - "The fifteen strategies"
Cohesion: 0.09
Nodes (22): adaptive *(default)*, automatic_failover, Candidate selection, Choosing one, context_length_optimized, cost_optimized, fallback_chain, highest_success_rate (+14 more)

### Community 423 - "SetupWizardPage.js"
Cohesion: 0.13
Nodes (17): completeSetup(), createSecret(), detectHardwareForSetup(), detectModelsForSetup(), getPublicPath(), getSetupState(), saveSetupStep(), setBackendUrl() (+9 more)

### Community 424 - "getBackendUrl"
Cohesion: 0.19
Nodes (16): getAccessToken(), getApiUrl(), getAuthHeaders(), getBackendUrl(), { getAccessToken, getAuthHeaders, getBackendUrl }, { getBackendUrl }, buildAgentStatusUrl(), buildAgentStreamUrl() (+8 more)

### Community 425 - "PrioritizedTask"
Cohesion: 0.11
Nodes (12): IntEnum, Queue, PrioritizedTask, Priority, Any, Start the worker pool., Submit a task to the queue. Returns True if accepted, False if rejected due to…, Return queue introspection data for status endpoints. (+4 more)

### Community 426 - "TestModelRegistryUpdates"
Cohesion: 0.14
Nodes (7): Test hook — rebuild the registry on next access., reset(), tests/test_daily_automation_2026_07_10.py — Daily automation tests…, Verify Llama 4 and Claude Sonnet 5 cross-provider aliases are registered., Verify new models are in the packages/ai/registry., TestBrainFailoverModelAliases, TestModelRegistryUpdates

### Community 427 - "_Cursor"
Cohesion: 0.10
Nodes (7): _Cursor, _PendingCursor, Async iterator wrapping a list of dicts (already decoded from JSON)., Return a sort key that tolerates mixed float/str timestamp values. Some code…, Return a _Cursor (evaluated lazily on first await/iteration)., A cursor that fetches its data lazily on first use., _safe_sort_key()

### Community 428 - "WindowsServiceManager"
Cohesion: 0.18
Nodes (7): _creationflags(), CompletedProcess, Path, service_manager.py — auto-generated module docstring (user-research skill scan)., Spawn a new proxy process on Linux/Mac using the current Python interpreter., ServiceState, WindowsServiceManager

### Community 429 - "SyntheticDataPipeline"
Cohesion: 0.13
Nodes (8): Return samples filtered by minimum reward score., Export samples in Alpaca JSONL format. Returns the path to the exported file., Export samples in ShareGPT JSONL format. Returns the path to the exported file., Export all samples as a structured JSON array. Returns the path to the exported…, Clear all accumulated samples., Pipeline to generate synthetic training data from agent sessions. Usage::…, SyntheticDataPipeline, TestSyntheticDataPipeline

### Community 430 - "test_task_source_id_race.py"
Cohesion: 0.13
Nodes (20): _is_duplicate_key_error(), Exception, Create a task. Deduplicates by source_id if set (Charter G3). If a task with…, Return the task previously created for an external ``source_id`` (e.g.…, True if *exc* is a pymongo E11000 duplicate-key error. Checked by class name…, _FakeDuplicateKeyError, _mock_mongo_db(), asyncio (+12 more)

### Community 431 - "_get"
Cohesion: 0.12
Nodes (9): _get(), Contract tests for the provider on/off endpoints. ``GET /api/brain/providers``…, Silently storing a typo'd id would leave a switch nothing can turn back on., The operator has to know WHY before deciding to switch it back on. The raw…, The response reaches the browser — a leaked key would be a disclosure., The switch has to reach the dispatcher, not just the listing., TestDisabledReasonIsReadableNextToTheSwitch, TestListing (+1 more)

### Community 432 - "test_cerebras_catalogue.py"
Cohesion: 0.13
Nodes (13): _agency_catalogue(), _cerebras_block(), _names_exactly(), parametrize, The first link of the failover chain was pointed at models that do not exist.…, Whole-id match. ``llama-3.3-70b`` must not match Groq's ``-versatile``., `config/models.yaml` wins at import, so a stale Python copy is invisible., 402 means nothing was measured. Undeclared capability must read as false.… (+5 more)

### Community 433 - "test_monitor_lib.py"
Cohesion: 0.11
Nodes (8): _isolate_env(), MonkeyPatch, tests/test_monitor_lib.py — unit tests for scripts/monitor_lib.py. Covers the…, Pin all env-overridable paths to tmp_path for hermetic tests., TestAwaitReady, TestIsProcessAlive, TestSuperviseLoopGiveUp, TestSupervisorTick

### Community 434 - "Path"
Cohesion: 0.16
Nodes (6): Path, Old log + done signal + no .incomplete = complete (caller can cleanup the log…, TestDownloadStatus, TestReadPidFile, TestSupervisorStateAtomic, _write_log()

### Community 435 - "test_mostly_failed_steps.py"
Cohesion: 0.12
Nodes (22): _make_result(), _make_step(), tests/test_mostly_failed_steps.py — regression test for the "21/22 failed steps…, A BLOCKED judge verdict should never be success, regardless of steps., When mostly_failed, the output should contain a clear failure summary., 0 steps → no gate (division by zero avoided, total_steps < 4)., 6 failed + 2 applied = 75% failure, 2 applied < 3 → mostly_failed., Build a mock agent result dict (the shape InternalAgentAdapter expects). (+14 more)

### Community 436 - "test_v4_api.py"
Cohesion: 0.12
Nodes (22): auth_headers(), TestClient, tests/test_v4_api.py — Tests for the v4 dashboard API endpoints., Return the test client — reuses conftest client which has bootstrap., Get auth headers by logging in as admin via the admin API., GET /v4/status returns 200 with improvement_loop and self_healing keys., GET /v4/improvements returns 200 with active and resolved lists., GET /v4/tasks returns 200 with tasks array. (+14 more)

### Community 437 - "HarnessEnrichment"
Cohesion: 0.14
Nodes (9): HarnessEnrichment, Any, Build a compact catalog of available runtime skills. Discovers from…, Standing instructions from the Continual Harness spec. Deliberately uncached:…, Build the complete enrichment block (tools + skills). Returns empty string when…, Inject enrichment blocks into a system prompt string. Appends blocks after the…, Auto-discovers skills and tools for agent prompt injection. Usage:: enrichment…, Build a compact, token-efficient catalog of available agent tools. Discovers… (+1 more)

### Community 438 - "classify_direct_chat_intent"
Cohesion: 0.13
Nodes (19): classify_direct_chat_intent(), _contains_keyword(), detect_intent(), intent.py — Intent classification for direct chat (answer_only, execute_now,…, Return True if content contains any execution or analysis keyword., Detect the user's intent from message content., Map lower-level intents into conversation-driven action categories. Returns one…, classify_plain_text() (+11 more)

### Community 439 - "operational_incidents.py"
Cohesion: 0.13
Nodes (21): _diagnose_and_file(), _file_incident(), _format_incident(), get_operational_incident_tracker(), _now(), OperationalIncident, agent/operational_incidents.py — recurring operational failures, auto-…, Monotonic clock, behind an indirection so tests can freeze it. Patching… (+13 more)

### Community 440 - "OperationalIncidentTracker"
Cohesion: 0.10
Nodes (15): _iso_from_monotonic(), OperationalIncidentTracker, Count operational failures; diagnose and file the ones that persist. Every…, Start with no tracked signatures and no filing history., Note one operational failure. Returns True when it filed an incident. Called…, Reconcile the admission granted in ``_may_file`` with what happened. Admission…, Drop all state. Used by tests., Count one failure; return True when this crossed into an incident. (+7 more)

### Community 441 - "FilterResult"
Cohesion: 0.15
Nodes (11): FilterResult, Compact git status output — keep only changed file paths., Compact git log — one line per commit., Compact git diff — keep file headers, collapse hunks., Compact test output — keep only failures and summary., Deduplicate log lines and keep only unique patterns., Group files by directory for compact listing., Generic smart filtering — remove empty lines, truncate long output. (+3 more)

### Community 442 - "AdaptivePermissions"
Cohesion: 0.18
Nodes (17): AdaptivePermissions, PermissionAssessment, Any, agent/permissions.py — Adaptive Permission Classifier Reads the session…, Convenience helper — True when the inferred level is read_write or full_access., Infer permission level from a list of chat messages (session transcript).…, Analyse *messages* and return a :class:`PermissionAssessment`., _msgs() (+9 more)

### Community 443 - "._connect"
Cohesion: 0.10
Nodes (10): Any, Connection, Path, Recall a specific memory entry., Auto-load relevant memories based on context. Returns memories prioritized by:…, Get all memories in a specific category., Delete a memory entry., Export all memories for a user (for backup/migration). (+2 more)

### Community 444 - "LocalBrainStore"
Cohesion: 0.16
Nodes (13): LocalBrainStore, _now_iso(), Any, Connection, backend/local_brain_store.py — DB-persisted state for the local GLM 5.2 brain.…, Return the desired + last-reported state for the admin UI., Operator flips the toggle. Persists + clears any prior lease. Returns the new…, Local daemon POSTs its heartbeat. If the operator's desired_state=on AND the… (+5 more)

### Community 445 - "AdminScreen.jsx"
Cohesion: 0.11
Nodes (12): changeUserRole(), createApiKey(), deleteApiKey(), setUserOnboarding(), AdminOnboardingPanel(), AdminScreen(), errText(), NewKeyForm() (+4 more)

### Community 446 - "Harness"
Cohesion: 0.14
Nodes (16): detect_harness(), Harness, harness_context_limit(), harness_stats(), HarnessProfile, Any, Enum, Detect which AI coding tool is calling the proxy. Checks in priority order: 1.… (+8 more)

### Community 447 - "TestLegacyRouterCacheTTL"
Cohesion: 0.13
Nodes (10): tests/test_anthropic_prompt_cache_ttl.py — extended-TTL prompt caching on the…, 1h TTL must not add the extended beta if caching is turned off — the extended…, The OpenAI→Anthropic translator applies the configured TTL to system., No env override → the block stays ``{"type": "ephemeral"}`` — no ``ttl`` key.…, ``5m`` is the API default. Sending ``ttl: "5m"`` is legal but redundant, and…, Anthropic only accepts ``5m`` and ``1h`` today. An unknown value is an operator…, ``ANTHROPIC_PROMPT_CACHING=off`` disables the cache_control block entirely —…, The legacy adapter sets ``anthropic-beta`` on the wire. ``1h`` TTL requires the… (+2 more)

### Community 448 - "test_anthropic_refusal_fallback.py"
Cohesion: 0.19
Nodes (8): _make_provider(), Tests for Anthropic server-side fallbacks and refusal logging. Covers: -…, Anthropic API shape for a content refusal (HTTP 200, stop_reason=refusal)., Only "default" mode is sent — never a custom string., _refusal_response(), _request(), TestRefusalLogging, TestServerFallbackPayload

### Community 449 - "test_telegram_diag_endpoint.py"
Cohesion: 0.09
Nodes (21): client(), tests/test_telegram_diag_endpoint.py — /api/telegram/diag HTTP endpoint.…, The endpoint does not require authentication (it's a diagnostic tool)., When TELEGRAM_BOT_TOKEN is unset, bot_token_set is False and prefix is (unset)., The live fields show a running poller and no webhook when healthy., The exact 'card arrives but tap does nothing' state is made visible: no poll…, A failed live lookup must degrade to a diagnostic, never 500 the endpoint., Build a TestClient against the FastAPI app with controlled env. (+13 more)

### Community 450 - "_P"
Cohesion: 0.19
Nodes (8): _ids(), _P, A provider with no latency sample must be able to earn one., The safety invariant: a shuffle may not promote a paid provider ahead of the…, With every provider idle a stable sort would send the whole burst to the first…, No explicit weights: the provider that has spent less of its minute should be…, Minimal provider stand-in — the director only needs ``provider_id``., TestOrdering

### Community 451 - "create_wiki_page"
Cohesion: 0.14
Nodes (13): create_wiki_page(), fetch_and_store(), Any, AsyncClient, Create (or silently skip if duplicate title) a Wiki page., Ingest a URL into the Sources database so it becomes RAG-searchable. Returns…, _FakeClient, _FakeResp (+5 more)

### Community 452 - "PersistentMemoryStore"
Cohesion: 0.22
Nodes (20): PersistentMemoryStore, Enhanced persistent memory store with auto-loading support. Features: -…, cmd_autoload(), cmd_delete(), cmd_export(), cmd_import(), cmd_list(), cmd_recall() (+12 more)

### Community 453 - "RegistrySkill"
Cohesion: 0.16
Nodes (11): _fmt_name(), AsyncClient, A skill fetched from a remote or local registry., Fetch skills from all configured GitHub registries. Returns count added., Fetch one GitHub registry and return a list of RegistrySkill objects. Handles…, Fetch a registry whose skills live in arbitrarily nested directories. Uses the…, Fetch one nested SKILL.md via raw.githubusercontent.com., Fetch a flat .md file and convert it to a RegistrySkill. (+3 more)

### Community 454 - "_ensure_tasks_source_id_unique_index"
Cohesion: 0.14
Nodes (20): _agent_provider_failure_response(), _ensure_tasks_source_id_unique_index(), _is_index_options_conflict(), Exception, True when *exc* is Mongo refusing to redefine an existing index. Mongo raises…, Add a unique **partial** index on tasks.source_id — isolated from the main…, Fall back to a direct LLM call when the agent loop cannot reach any provider.…, asyncio (+12 more)

### Community 455 - "V3 API Migration Plan — LLM Relay Platform"
Cohesion: 0.10
Nodes (20): Acceptance Checks, Approach, Auth Flow (v3 JWT-based), Backward Compatibility, Current State Analysis, Data Model Changes, Database/Storage, Files to Create/Modify (+12 more)

### Community 456 - "test_north_mini_code.py"
Cohesion: 0.10
Nodes (11): north_mini_code_model_for(), Return the North Mini Code model id served by *provider*, else ``None``.…, tests/test_north_mini_code.py — North Mini Code 1.0 integration. Covers the…, The switch defaults ON so North is the default post-install., The agency/Hermes execution path defaults to North via the resolver., Hermes must be able to run the agency with the full Hermes-OS capacity set —…, test_flag_default_is_on(), test_hermes_declares_full_capability_set() (+3 more)

### Community 457 - "test_chat_mode_regressions.py"
Cohesion: 0.18
Nodes (19): ProviderResult, _auth_headers(), test_agent_status_endpoint_reports_live_progress_and_tool_calls(), test_agent_stream_endpoint_emits_server_sent_events(), test_chat_send_emits_langfuse_observation_for_direct_chat(), test_chat_send_keeps_complex_prompt_on_direct_path_when_agent_mode_is_off(), test_chat_send_keeps_explanatory_github_pr_guidance_on_direct_path(), test_chat_send_keeps_general_docker_explanation_on_direct_path_when_no_repo_action_is_requested() (+11 more)

### Community 458 - "_env_float"
Cohesion: 0.11
Nodes (12): _env_float(), Read a float env var, falling back to *default* on unset/garbage., parametrize, Hermes must survive free-tier cold starts, and fallback must not log errors.…, A handled fallback is a warning; only an unrecoverable state is an error., A free Render service takes 30-60s to wake; 5s could never see it., A typo in the env var must not brick the health probe., The sidecar needs its own warm ping — the backend's does not cover it. (+4 more)

### Community 459 - "AgentMessageBus"
Cohesion: 0.18
Nodes (7): AgentMessageBus, Remove a subscription., Return all topics that have history., Pub/sub message bus for inter-agent communication. Agents subscribe to topics…, Decorator: subscribe a callback to a topic pattern. Supports ``*`` (single…, asyncio, TestAgentMessageBus

### Community 460 - "DecisionsStoreTests"
Cohesion: 0.10
Nodes (7): Test-only: clears the cached singleton so the next get_decisions_store() builds…, reset_decisions_store_singleton(), DecisionsStoreTests, _fresh_store(), Smoke: create() returns a fresh dec_<hex8> per call (no error surfaces from…, tests/test_decisions_store.py — Coverage for the generic decision store. Each…, Backdates the older row via raw SQLite UPDATE so it falls outside the cutoff…

### Community 461 - "GuardrailEngine"
Cohesion: 0.16
Nodes (7): get_guardrails(), GuardrailEngine, Configurable safety rail engine for LLM inputs and outputs. Supports: -…, Load guardrail rules from a YAML or JSON config file., Compile regex patterns from the rules configuration., Return the module-level GuardrailEngine singleton., TestGuardrailEngine

### Community 462 - "test_issue_triage.py"
Cohesion: 0.17
Nodes (19): _match_family(), Any, services/issue_triage.py — inbound GitHub issue triage. Closes the intake gap…, Classify a single GitHub issue payload and return the routing decision. Pure…, Fetch unlabeled open issues, triage each, and route them. Returns a summary…, run_triage_cycle(), _severity_for(), triage_enabled() (+11 more)

### Community 463 - "weekly_digest.py"
Cohesion: 0.13
Nodes (15): build_digest(), _count_open_auto_prs(), _load_readiness(), Any, services/weekly_digest.py — Weekly readiness digest for Telegram. Compiles loop…, Send the digest text via NotificationDispatcher (Telegram)., Load loop readiness report from the registry., Count open PRs with the 'automated' or 'auto-pr' label via git log heuristic. (+7 more)

### Community 464 - "test_autonomous_agency_e2e.py"
Cohesion: 0.10
Nodes (15): FakeTask, End-to-end tests for the autonomous AI agency system (issue #467). These tests…, Tests for Telegram notification dispatch., Verify NotificationDispatcher.on_task_complete dispatches notifications., Tests for portfolio intelligence system., Verify PortfolioManager initializes correctly., Verify PortfolioIntelligence can build from live signals., Tests for agile sprint management. (+7 more)

### Community 465 - "_FakeSandbox"
Cohesion: 0.10
Nodes (9): fake_sandbox(), _FakeAsyncSandboxClass, _FakeCommands, _FakeFiles, _FakeSandbox, _make_fake_sandbox(), Any, Mimics e2b_code_interpreter.AsyncSandbox for tests. (+1 more)

### Community 466 - "test_local_controller.py"
Cohesion: 0.17
Nodes (20): _env_defaults(), _fake_http_sequence(), _fake_subprocess_run(), _import_controller(), tests/test_local_controller.py — unit tests for the local GLM-5.2 daemon. These…, The diag output must surface binary/model errors clearly., Pins the v3 fix: after the multi-port preamble probe finds colibri serving a…, Yield a list of (status, body) tuples the daemon will see in order when it… (+12 more)

### Community 467 - "test_provider_state_durability.py"
Cohesion: 0.12
Nodes (9): fake_mongo(), _FakeCollection, _FakeDb, _live_mongo_url(), Operator provider state must survive a redeploy. The per-provider kill switch…, Return a reachable MONGO_URL, or None so the test skips., Both halves matter, and the second one is easy to drop. Redirecting…, test_conftest_isolates_operator_state_for_every_test() (+1 more)

### Community 468 - "run_trend_analysis"
Cohesion: 0.18
Nodes (13): Tests for trend_analysis.py — last30days-style window over TrendWatcher (issue…, TestRunTrendAnalysis, TestWindow, BaseModel, trend_analysis.py — last30days-style trend analysis (issue #493). Adapts the…, True if the ISO-ish published date falls within the last N days.…, Fetch trends via TrendWatcher, filter to a 30-day window, persist summary., Write trends/trend_summary.md (and a dated copy); return the path. (+5 more)

### Community 469 - "test_unit5_ui_provider_surface.py"
Cohesion: 0.10
Nodes (15): tests/test_unit5_ui_provider_surface.py — UNIT 5 regression tests. Verifies…, The component must call ``providerLabel(p)`` rather than indexing a 4-entry…, The dropdown shows a [free]/[paid]/[local] tier tag so the operator can tell…, The <option> tag uses providerLabel(p), not PROVIDER_LABELS[]., The operator must be able to see what a key really serves. ``candidates`` is…, The GET endpoint response must list every BrainProvider Literal entry. Before…, Providers that were filtered out before UNIT 5 are now present. ``mistral``,…, A known paid provider is reported as tier=paid (was filtered before). (+7 more)

### Community 470 - "test_agent_tools.py"
Cohesion: 0.17
Nodes (19): Register the built-in agent tools that are always available., _register_builtin_tools(), Path, Trailing spaces on lines must not block the edit., Replacing with empty string removes the matched text., edit_file must be discoverable via the capability registry., test_edit_file_delete_old_string(), test_edit_file_exact_match() (+11 more)

### Community 471 - "LocalWorkspace"
Cohesion: 0.16
Nodes (9): LocalWorkspace, Path, Manages a local git clone of a GitHub repository. Clones are stored under…, Run a git command. Never uses shell=True., Clone the repo if it doesn't exist; pull if it does., Return the current working-tree diff (staged + unstaged)., Stage files and commit. paths=None stages everything; paths=[] raises., Create and checkout a new branch from base_branch. (+1 more)

### Community 472 - "MemoryCategory"
Cohesion: 0.16
Nodes (14): Memory middleware for automatic context injection into AI tool requests. This…, MemoryCategory, MemoryEntry, MemoryScope, Enum, Row, str, Enhanced persistent memory system with auto-loading across AI coding tools.… (+6 more)

### Community 473 - "Skill: modularity-review"
Cohesion: 0.10
Nodes (19): Acceptance Checks, Applying to This Repo, Further Reading, Modularity Findings Template, Part A: Reviewing Existing Code for Modularity Problems, Part B: Designing New Modular Boundaries, Skill: modularity-review, Step 1 — Map the dependency graph (+11 more)

### Community 474 - "Design Audit"
Cohesion: 0.10
Nodes (19): Code Quality, Color and Surfaces, Component Patterns, Content, Design Audit, Fix Priority, How This Works, Iconography (+11 more)

### Community 475 - "Findings"
Cohesion: 0.10
Nodes (19): API Documentation, Architecture Documentation, DOC-001 [HIGH] — No SECURITY.md, DOC-002 [HIGH] — No CONTRIBUTING.md, DOC-003 [HIGH] — No API.md / OpenAPI Export, DOC-004 [MEDIUM] — README.md is 31KB and Needs Pruning, DOC-005 [MEDIUM] — `REVIEW_AND_FIXES.md` and `AGENCY_CORE_V5_PROGRESS.md` are Unclear, DOC-006 [MEDIUM] — No DEPLOYMENT.md at Root (+11 more)

### Community 476 - "test_minimax_bug_fixes.py"
Cohesion: 0.12
Nodes (10): Resolve the JWT signing secret, with a *stable* fallback. Bug fix: the previous…, _resolve_jwt_secret(), Regression tests for the production bugs reported by the MiniMax audit. Each…, Podman/systemd-nspawn set ``container=podman`` but no /.dockerenv., The bug: an unset JWT_SECRET minted a fresh random key each process start,…, The old sync callback called the deprecated ``asyncio.get_event_loop()`` from…, test_scheduler_on_fire_is_a_coroutine(), TestContainerDetection (+2 more)

### Community 477 - "Skill: modularity-review"
Cohesion: 0.10
Nodes (19): Acceptance Checks, Applying to This Repo, Further Reading, Modularity Findings Template, Part A: Reviewing Existing Code for Modularity Problems, Part B: Designing New Modular Boundaries, Skill: modularity-review, Step 1 — Map the dependency graph (+11 more)

### Community 478 - "crispy_client.py"
Cohesion: 0.14
Nodes (18): cmd_approve(), cmd_artifacts(), cmd_build(), cmd_events(), cmd_reject(), cmd_status(), cmd_watch(), _get() (+10 more)

### Community 479 - "4. Troubleshooting"
Cohesion: 0.10
Nodes (19): 1. Which sandbox backend applies where, 2. Container hardening, 3. Supply chain, 4. Troubleshooting, 5. Scaling, Agents suddenly failing after enabling enforcement, An agent is stuck, Applying the overlay to the local stack (+11 more)

### Community 480 - "Docker AI Governance Audit — Final Report"
Cohesion: 0.10
Nodes (20): 1. Executive summary, 2. Architecture review, 3. Risk assessment, 4. Security review, 5. What was implemented, 6. Explicitly not implemented, 7. Remaining recommendations, 8. Future enhancements (+12 more)

### Community 481 - "1. Capability-by-capability"
Cohesion: 0.10
Nodes (19): 0. The finding that shapes everything else, 1.10 Least Privilege, 1.11 Multi-Agent Governance (10 / 100 / 1000 agents), 1.12 Cost Governance, 1.13 Compliance (SOC2 / ISO27001 / GDPR), 1.14 Local Development Experience, 1.1 Agent Identity, 1.2 Tool Governance (+11 more)

### Community 482 - "4. Threats"
Cohesion: 0.10
Nodes (20): 1. What makes this system different from a normal web app, 2. Assets, 3. Trust boundaries, 4. Threats, 5. Why the engine fails open but approvals fail closed, 6. Honest limits, 7. Priority follow-ups, T10 — Supply-chain compromise via base image (+12 more)

### Community 483 - "Dynamic Model Routing"
Cohesion: 0.10
Nodes (20): Architecture, Built-in Claude → local alias table, Configuring fast_response routing, Configuring model preferences, Curl example, Dynamic Model Routing, Fallback execution, Health check and availability filtering (+12 more)

### Community 484 - "FeatureUnavailableError"
Cohesion: 0.13
Nodes (14): check_feature(), get_feature(), list_features(), Any, get, post, features/api.py — Admin API for the feature support matrix. Exposes: GET…, Return the full support matrix with summary. (+6 more)

### Community 485 - "PortfolioScreen.jsx"
Cohesion: 0.11
Nodes (12): getPortfolioBoard(), refreshPortfolio(), btnStyle, HEALTH, HORIZONS, PortfolioScreen(), SOURCE, STATUS_COLOR (+4 more)

### Community 486 - "infra_cost.py"
Cohesion: 0.15
Nodes (14): compute_request_cost(), _float_env(), get_infra_config(), InfraConfig, load_infra_config(), project_session_cost(), Local infrastructure cost model for true TCO analysis. This module computes the…, Compute infrastructure cost for a single request given its latency. (+6 more)

### Community 487 - "ai/__init__.py"
Cohesion: 0.16
Nodes (17): packages.ai — provider abstraction, model registry, and failover manager., all_models(), best_model_for(), get(), ModelInfo, models_by_provider(), packages/ai/registry.py — Model Registry. Centralized registry of all models…, Register the default free-tier models. (+9 more)

### Community 488 - "ClaudeCodeAdapter"
Cohesion: 0.19
Nodes (17): ClaudeCodeAdapter, Any, Adapter for Claude Code CLI — FIRST CLASS autonomous coding runtime., adapter(), asyncio, Tests for runtimes/adapters/claude_code.py, setup_database_moks(), test_adapter_metadata() (+9 more)

### Community 489 - "build_workflow.py"
Cohesion: 0.30
Nodes (19): _c(), _get(), _header(), main(), _make_headers(), _phase_icon(), _post(), _print_phases() (+11 more)

### Community 490 - "context_plan_gate.py"
Cohesion: 0.15
Nodes (18): evaluate(), evaluate_path(), main(), _parse_args(), PlanDecision, Namespace, Path, Did the planner actually retrieve the source it reasoned about? (+10 more)

### Community 491 - "run_bot"
Cohesion: 0.12
Nodes (19): _configure(), _default(), main(), Entry point for the always-on FreeBuff Telegram bot (Render worker / Docker).…, Set an env var only when the operator hasn't already provided one., get_webhook_info(), Any, Call a Telegram Bot API method and return the parsed JSON (best-effort).… (+11 more)

### Community 492 - "HarnessRegistry"
Cohesion: 0.16
Nodes (8): HarnessMetrics, HarnessRegistry, HarnessSessionRecord, _NoopDB, Any, BaseModel, services/harness_registry.py — Persistent Harness Registry Tracks which AI…, Persistent registry of harnesses and their performance history. Stores session…

### Community 493 - "test_kimi_bridge_server.py"
Cohesion: 0.12
Nodes (11): _messages_to_prompt(), Flatten an OpenAI messages list into a single string for the web UI., auth_token(), fake_driver(), kimi_app(), Tests for the Kimi web-bridge HTTP service. All tests mock browser_driver.ask…, A canned KimiBrowserDriver stand-in that never touches a real browser., Return a TestClient for the Kimi bridge app, with a mocked driver. The key is… (+3 more)

### Community 494 - "ProviderCircuit"
Cohesion: 0.15
Nodes (8): ProviderCircuit, Attempt to move from OPEN to HALF_OPEN after recovery timeout., Check if a request can be made through this circuit., Per-provider circuit breaker state machine., TestProviderCircuit, parametrize, Counting every sub-500 as a success meant the breaker could never open for the…, TestNimPoolCountsRateLimitsAsFailures

### Community 495 - "PriorityTaskQueue"
Cohesion: 0.15
Nodes (7): get_task_queue(), PriorityTaskQueue, Stop the worker pool gracefully., Return the module-level PriorityTaskQueue singleton., Asyncio-based priority queue with backpressure and worker pool. Features: -…, Higher-priority tasks should be processed before lower-priority ones., TestPriorityTaskQueue

### Community 497 - "Page"
Cohesion: 0.15
Nodes (7): Page, Chat: send message, view sessions, delete session, agent mode toggle., Runtimes: list, health, decisions, policy., Settings, Secrets, Features, Setup, GitHub, Activation., TestChat, TestRuntimes, TestSettings

### Community 498 - "TestBrainFailoverModelUpdates"
Cohesion: 0.18
Nodes (3): Verify the provider registry in brain_failover contains the 2026 model set., The rotation must equal the catalogue, which the probe keeps honest., TestBrainFailoverModelUpdates

### Community 499 - "._call"
Cohesion: 0.18
Nodes (4): Any, A message list that exceeds the pruner's threshold should be trimmed., TestApplyReasoningBudget, TestPruneChatMessages

### Community 501 - "test_tasks_cache_ttl_env.py"
Cohesion: 0.21
Nodes (19): MonkeyPatch, Round-trip tests for TASKS_LIST_ALL_CACHE_TTL_SEC env-var override in…, With a lowered cap, a value above the new cap falls back to default., Reload tasks.api after injecting TASKS_LIST_ALL_CACHE_TTL_SEC=value (or unset)., Values above the 1h upper bound in _safe_ttl fall back to default. Guards the…, Value equal to the 1h upper bound is honored (boundary case)., ``TASKS_MAX_CACHE_TTL_SEC`` env var overrides the cap module-level constant., _reload_tasks_api_with_env() (+11 more)

### Community 502 - "test_voice_pipeline.py"
Cohesion: 0.14
Nodes (14): asyncio, Tests: Voice pipeline — STT backend selection, TTS backend selection, memory…, A stalled gTTS/pyttsx3 call must not hang synthesize() forever. gTTS/pyttsx3…, TTS_SYNTHESIZE_TIMEOUT_SEC must override the default ceiling., gTTS/pyttsx3 must run on a dedicated executor, not the shared default.…, test_memory_export_markdown(), test_memory_forget(), test_memory_recall_empty() (+6 more)

### Community 503 - "TestUpdateTask"
Cohesion: 0.16
Nodes (7): _NoopCheckpointStore, WorkflowRun, tests/test_workflow_orchestrator_update_task.py Pytest coverage for…, Stand-in for the real Mongo checkpoint store., Two consecutive updates collapse: the latest instruction wins. This matches…, _run(), TestUpdateTask

### Community 504 - "MemoryKernel"
Cohesion: 0.16
Nodes (7): Fact, get_memory_kernel(), MemoryKernel, voice/memory_kernel.py — Jarvis OS-inspired Memory Kernel. Stores atomic facts…, Return most relevant facts. Simple substring match on content., SQLite-backed atomic fact store with Markdown mirror., Store a new atomic fact or reinforce an existing one.

### Community 505 - "open_phase_report"
Cohesion: 0.14
Nodes (19): note_phase_end(), note_phase_start(), open_phase_report(), Record that *phase* began; returns the token that ends it. Called from…, Close the invocation identified by *token*. Never raises., Describe the phases currently in flight, innermost (newest) first. A phase that…, Tracked as it happens, so the duration is measured rather than inferred., `execute_step` wraps `tool_dispatch`; a stuck inner call leaves both open, and… (+11 more)

### Community 506 - "SamAgent"
Cohesion: 0.16
Nodes (10): Any, SAM voice agent — the voice-controlled interface to the agency., Process a voice command and return SAM's spoken response. Args: text: The…, Public snapshot of live agency state (used by the LiveKit worker tools)., Gather live agency state for SAM's situational awareness., Call the NVIDIA NIM LLM (free tier) for SAM's response., Rule-based fallback when the LLM is unavailable., SamAgent (+2 more)

### Community 507 - "_extract_tech_relevance"
Cohesion: 0.17
Nodes (6): _extract_tech_relevance(), Dynamic extraction: finds any tech keyword mentioned in the skill content,…, Tests for _extract_tech_relevance() word-boundary matching., Integration-style tests for the recommendation path (no I/O)., TestExtractTechRelevance, TestRecommendLogic

### Community 508 - "HarnessAdapter"
Cohesion: 0.12
Nodes (9): HarnessAdapter, HarnessSpec, Any, agents/harness_adapter.py — ECC Cross-Harness Adapter Normalises API…, Adapt harness-native requests to the local-llm-server internal format. Each…, Detect which harness sent this request from headers. Check order: explicit…, Convert a harness-native request dict to the local-llm-server format., Return the recommended model for this harness. (+1 more)

### Community 509 - "Skill: fabric-patterns"
Cohesion: 0.11
Nodes (18): 1. Ensure Pattern Directory Exists, 2. List Available Patterns, 3. Retrieve a Pattern, 4. Apply a Pattern with Variables, 5. Stitch Patterns Together, 6. Create New Patterns, Acceptance Checks, Directory Structure (+10 more)

### Community 510 - "Analysis & Synthesis Instructions"
Cohesion: 0.11
Nodes (18): 1. Define the Atmosphere, 2. Map the Color Palette, 3. Establish Typography Rules, 4. Define the Hero Section, 5. Describe Component Stylings, 6. Define Layout Principles, 7. Define Responsive Rules, 8. Encode Motion Philosophy (+10 more)

### Community 511 - "Production Readiness Assessment — local-llm-server"
Cohesion: 0.11
Nodes (18): 1. Availability & Reliability, 2. Observability, 3. Deployment Architecture, 4. Configuration & Secrets, 5. Recovery & Backup, 6. Cloudflare Worker Audit, Current State, Current State (+10 more)

### Community 512 - "_is_admin"
Cohesion: 0.11
Nodes (17): backend/ceo_router.py — observability and manual control for the CEO. Surfaces…, Reject non-admin callers for routes that spend provider budget. Delegates to…, _require_admin(), _is_admin(), Check if a user has admin role. Works for both social_auth users (role in…, _actor(), ControlUpdateBody, BaseModel (+9 more)

### Community 513 - "clear_override"
Cohesion: 0.13
Nodes (19): build_platform_controls_router(), APIRouter, Build the router, bound to the app's auth dependency. Takes…, clear_override(), Persist the full override set., Validate, persist, and apply *updates*. A value equal to the environment/code…, Drop the override for *key*, reverting it to the environment default., Of *changed*, the keys whose readers only see the new value after a restart. (+11 more)

### Community 514 - "verify_service_token"
Cohesion: 0.15
Nodes (18): merge_pr_route(), PRMergeRequest, N5 dual-auth dependency: accept EITHER a user session OR a service token. Used…, Body for POST /admin/api/prs/{number}/merge — service-token-gated., Merge a PR via the GitHub API. Service-token-gated (N5). Returns the merge…, _user_or_service_token(), _get_hashed_token(), _hash_token() (+10 more)

### Community 515 - "TestNormalizeResponseFormat"
Cohesion: 0.11
Nodes (7): _normalize_response_format(), Translate OpenAI ``response_format`` into Ollama's ``format`` field. For…, Payload without 'model' field should apply normalization (no '/' → local)., _normalize_response_format must not mutate the input dict., Unit tests for chat_handlers._normalize_response_format., If json_schema has no 'schema' key, don't break., TestNormalizeResponseFormat

### Community 516 - "Skill: fabric-patterns"
Cohesion: 0.11
Nodes (18): 1. Ensure Pattern Directory Exists, 2. List Available Patterns, 3. Retrieve a Pattern, 4. Apply a Pattern with Variables, 5. Stitch Patterns Together, 6. Create New Patterns, Acceptance Checks, Directory Structure (+10 more)

### Community 517 - "db/__init__.py"
Cohesion: 0.14
Nodes (7): _LazyModuleProxy, db — storage abstraction layer (V2.0 Phase 5: real code moved to…, Loads the real module on first attribute access, then replaces itself., # IMPORTANT: keep these imports LAZY (inside __getattr__) so that a Mongo-only, MongoStore, db/mongo_store.py — MongoDB store backed by Motor (existing implementation).…, Thin wrapper that exposes the Motor database as collection attributes.…

### Community 518 - "Admin Dashboard Guide"
Cohesion: 0.11
Nodes (19): Accessing the Dashboard, Admin API (Programmatic Access), Admin Dashboard Guide, Dashboard — healthy state, Dashboard — key created (one-time token flash), Dashboard — Langfuse diagnostic, Dashboard Layout, Login page (+11 more)

### Community 519 - "Implementation Plan"
Cohesion: 0.11
Nodes (18): (1) & partly (4): "Something went wrong" masks the real error everywhere, (2) & (3): Company creation flow / non-admin gate placement, (4): Agent provisioning "loading forever" — blocking subprocess in async path, (5): Tailored questions are hardcoded today, A0. Fix live scanner crashes on real-world sites (`services/scanner.py`) — do first, A. Fix error-message masking (`frontend/src/api.js`), Agent Prompt (paste this to start the implementation session), B. Make runtime activation non-blocking (`runtimes/control.py`, (+10 more)

### Community 520 - "Feature Guide"
Cohesion: 0.11
Nodes (19): 10. Langfuse Observability, 11. Coding Agent API, 12. Browser Admin UI, 13. Telegram Remote Control Bot, 14. Tunnel — Permanent Static URL via ngrok, 15. CORS Support, 16. Streaming Support, 17. Workspace Isolation (+11 more)

### Community 521 - "resolve_free_nvidia_brain"
Cohesion: 0.12
Nodes (18): livenim, Resolve the free NVIDIA NIM brain from env, or ``None`` if unconfigured.…, resolve_free_nvidia_brain(), test_resolve_free_nvidia_brain_from_env(), test_resolve_free_nvidia_brain_none_without_key(), _live_models(), The free-brain default must be an id the endpoint actually serves. Two…, The ids the catalogue currently vouches for. Derived, not frozen: a hardcoded… (+10 more)

### Community 522 - "scripts/doctor.py"
Cohesion: 0.27
Nodes (17): NamedTuple, Check, check_core_deps(), check_env(), check_git(), check_mongo(), check_node(), check_ollama() (+9 more)

### Community 523 - "build_matrix"
Cohesion: 0.19
Nodes (16): build_matrix(), _families(), main(), Any, scripts/generate_specialist_skill_matrix.py — Specialist × Skill matrix.…, Map family -> sorted list of test files that mention it (quoted token)., Return one row per family, derived entirely from code., render_markdown() (+8 more)

### Community 524 - "Delegation Plan (agent-ready work packages)"
Cohesion: 0.11
Nodes (18): Delegation Plan (agent-ready work packages), Findings, http://127.0.0.1:8899/, Page Details (worst first), Pillar Scores, `seo-fix-canonicals` - Fix Canonicals findings: 1 finding type(s) across 1 URL hit(s), `seo-fix-content` - Fix Content findings: 1 finding type(s) across 1 URL hit(s), `seo-fix-geo` - Fix GEO findings: 5 finding type(s) across 5 URL hit(s) (+10 more)

### Community 525 - "test_p0_roadmap_a4_a5_b2.py"
Cohesion: 0.15
Nodes (9): get_steering_injector(), Return recommended steering labels for a given task category. Used by the model…, Return the module-level SteeringInjector singleton., steering_for_task(), get_agent_bus(), Return the module-level AgentMessageBus singleton., TestPriority, TestSteeringForTask (+1 more)

### Community 526 - "RuntimeHealthService"
Cohesion: 0.15
Nodes (8): Return the last-known health for *runtime_id* (may be stale)., Return True if the runtime is available (not circuit-open)., Return health snapshots for all known runtimes., Force an immediate health check of all runtimes and return results., Attempt to start a dead runtime subprocess before re-probing. Uses the local…, Async health polling service for all registered runtimes., Start the background polling loop with an immediate initial check., RuntimeHealthService

### Community 527 - "agency_fix.py"
Cohesion: 0.19
Nodes (18): apply_edits(), build_prompt(), call_llm(), collect_context(), collect_source_files(), decline_cleanly(), extract_failing_tests(), _is_blocked() (+10 more)

### Community 528 - "LocalLLMSetup"
Cohesion: 0.15
Nodes (8): LocalLLMSetup, Update .env file with configuration., Check if services are already running., Setup wizard for the Autonomous AI Agency. Scans local models, configures…, Start the proxy server., Scan for local models., Scan the models folder for available models., Configure which models to use for agent roles.

### Community 529 - "test_brain_patch_service_token.py"
Cohesion: 0.18
Nodes (18): clean_store(), _clear_overrides(), _make_client_with_user(), tests/test_brain_patch_service_token.py — N5 acceptance: PATCH…, N5 acceptance: no service token + no user session → 401 (not 200)., N5 regression: the existing dashboard path (no service token, non-admin user)…, N5 regression: the existing admin dashboard path (no service token, admin user)…, Reset the brain config store + point SQLITE_DB_PATH at a tmp path. (+10 more)

### Community 530 - "TestSelfHealingInfrastructureClassification"
Cohesion: 0.19
Nodes (4): _classify_failure correctly identifies infrastructure errors., MongoDB timeout is an infra error, not a generic timeout., MongoDB 'connection refused' is infra, not generic network., TestSelfHealingInfrastructureClassification

### Community 531 - "test_fabric_patterns.py"
Cohesion: 0.11
Nodes (5): MonkeyPatch, Path, Tests for scripts/fabric_cli.py and the fabric-patterns pattern engine., test_new_scaffolds_pattern(), test_save_and_show_roundtrip()

### Community 532 - "test_fixes_reliability.py"
Cohesion: 0.11
Nodes (11): tests/test_fixes_reliability.py — Regression tests for the batch of fixes.…, InternalAgentAdapter should construct without error., AgentRunner must expose a public plan() coroutine., DashboardHome.js must use Promise.allSettled() not Promise.all(). Promise.all()…, AgentRunner.run() must accept a metadata= keyword argument., plan() should delegate to _generate_plan() and return an AgentPlan. Uses async…, plan() must accept (and ignore) metadata= for forward-compat., InternalAgentAdapter.execute() must NOT pass provider_chain= to AgentRunner.… (+3 more)

### Community 533 - "_Recorder"
Cohesion: 0.13
Nodes (7): tests/test_probe_report.py — the catalogue-probe drift-report step.…, Injectable stand-ins for the three GitHub operations., _Recorder, report(), TestBuildBody, TestFindTrackingIssue, TestReconciliation

### Community 534 - "test_repowise_intelligence.py"
Cohesion: 0.11
Nodes (18): Test that search_codebase returns a string., Test that get_decision_flownodes returns a string., Test that update_intelligence creates the expected intelligence files., Test that get_overview returns a dictionary., Test that get_context returns a string., Test that get_risk returns a dictionary., Test that get_why returns a string., Test that the RepowiseIntelligence class initializes correctly. (+10 more)

### Community 535 - "validate_session_id"
Cohesion: 0.16
Nodes (5): TestSessionIdValidation, WorkspaceNotFoundError should not expose the base root in error messages., TestNoInternalPathLeakage, Validate and return a session ID, or raise InvalidSessionIdError., validate_session_id()

### Community 536 - "ErrorInterceptorMiddleware"
Cohesion: 0.18
Nodes (11): _dispatch_async(), ErrorInterceptorMiddleware, Any, BaseHTTPMiddleware, Exception, Request, Response, agent/error_interceptor.py — HTTP Error Interceptor Middleware… (+3 more)

### Community 537 - "SkillRegistry"
Cohesion: 0.15
Nodes (8): Any, Central registry that indexes local + remote skills and provides context-aware…, Return ranked skill recommendations based on tech stack, active workflow types,…, Force-refresh remote skills, bypassing TTL. Returns count added., Update the GitHub token used for authenticated API calls., SkillRegistry, SkillRegistry method signature enforcement., TestSkillRegistryContracts

### Community 538 - "agile_sprints.py"
Cohesion: 0.14
Nodes (14): generate_sprint_retro(), Derive retro notes for ``sprint`` from its current metrics. Records…, Enum, Agentic Agile — Sprint management with velocity tracking and burndown. Issue:…, Sprint retrospective notes and follow-up action items., Whether the retrospective has any recorded content., Lifecycle status of a sprint., Status of a user story within a sprint. (+6 more)

### Community 539 - "DreamMemory"
Cohesion: 0.13
Nodes (10): ConsolidationPhase, DreamMemory, MemoryKind, Enum, str, Dream Memory Consolidation — pattern consolidation across AI sessions. Inspired…, What kind of memory artifact this is., Current phase of the consolidation lifecycle. (+2 more)

### Community 540 - "Comprehensive Skill Index (By Category)"
Cohesion: 0.11
Nodes (17): 10. Domain (Modelling, Training, Infra), 1. Planning and Implementation, 2. Code Quality, Architecture, and Audits, 3. State Management and Git Flow, 4. Memory, Knowledge, and Context Tuning, 5. Research, Browsing, and External Intel, 6. Session Lifecycle and Workflow, 7. Style and Craft Polish (UI / Docs / Tone) (+9 more)

### Community 541 - "Agent Skill: Principal UI/UX Architect & Motion Choreographer (Awwwards-Tier)"
Cohesion: 0.11
Nodes (17): 1. Meta Information & Core Directive, 2. THE "ABSOLUTE ZERO" DIRECTIVE (STRICT ANTI-PATTERNS), 3. THE CREATIVE VARIANCE ENGINE, 4. HAPTIC MICRO-AESTHETICS (COMPONENT MASTERY), 5. MOTION CHOREOGRAPHY (FLUID DYNAMICS), 6. PERFORMANCE GUARDRAILS, 7. EXECUTION PROTOCOL, 8. PRE-OUTPUT CHECKLIST (+9 more)

### Community 542 - "Component Map"
Cohesion: 0.11
Nodes (17): Architecture Audit — local-llm-server, Architecture Diagram, Component Map, Layer 10 — WebUI (`webui/`), Layer 11 — Infrastructure, Layer 1 — API Proxy (`proxy.py`, 1719 lines), Layer 2 — Chat Handlers (`chat_handlers.py`, 710 lines), Layer 3 — Model Router (`router/`) (+9 more)

### Community 543 - "render_router.py"
Cohesion: 0.14
Nodes (13): build_render_router(), Any, APIRouter, Exception, backend/render_router.py — Render platform view for operators and agents.…, Reject anyone who is not the agency admin., Map an MCP transport failure onto 503 rather than a 500. The distinction…, _require_admin() (+5 more)

### Community 544 - "Architecture Overview — local-llm-server"
Cohesion: 0.11
Nodes (18): `admin_auth.py` + `admin_gui.py`, `agent/`, Architecture Overview — local-llm-server, `chat_handlers.py`, Deployment, Feature Maturity Tiers, `handlers/anthropic_compat.py`, High-Level Architecture (+10 more)

### Community 545 - "Pending Activities — Implementation Playbook"
Cohesion: 0.11
Nodes (17): Context: what already works (do NOT redo), Definition of done (per task), How to verify the whole thing end-to-end (local, no external infra), P0 — Make autonomy real in production, P1 — Close the remaining product gaps, P2 — ECC harness & polish, Pending Activities — Implementation Playbook, Task 10 — ECC cross-harness adapter (currently PLANNED only) (+9 more)

### Community 546 - "Platform Guide — the full tour"
Cohesion: 0.11
Nodes (18): Agent runtimes, Architecture, Cloud deployment (Render + GitHub Pages), Development, Feature maturity — what's stable vs. beta, HITL approval gates — you stay in control, How it works — the 5-minute version, Learning loop — failures become context (+10 more)

### Community 547 - "The rules"
Cohesion: 0.11
Nodes (17): Changing these rules, How the gate behaves, Quick-Note Context Rulebook, R10 — Use the repository's real identity **[gate]**, R11 — Name a real integration point **[gate]**, R12 — Mark epistemic status at the claim **[review]**, R1 — Ground the plan in the source before planning anything **[gate]**, R2 — Say what the artifact actually is **[gate]** (+9 more)

### Community 548 - "Part A — Health Report"
Cohesion: 0.11
Nodes (17): F1 — CLAUDE.md documents an architecture that no longer exists, F2 — 15 skills have no frontmatter description, F3 — Direct `os.environ` reads outside config modules, F4 — `print()` in importable production modules, F5 — graphify hook nags every session, F6 — God files, Healthy signals, P1 — Refresh CLAUDE.md and AGENTS.md to match the real architecture (+9 more)

### Community 549 - "WorkflowScreen.jsx"
Cohesion: 0.14
Nodes (14): approveWorkflow(), buildWorkflow(), cancelWorkflow(), getWorkflowRun(), getWorkflowRuns(), rejectWorkflow(), btn(), BuildForm() (+6 more)

### Community 550 - "sync_readme_gallery.py"
Cohesion: 0.22
Nodes (15): main(), _out_dir(), Path, Generate Web UI screenshots for README/docs. Requires: pip install playwright…, build_gallery(), GallerySection, main(), Path (+7 more)

### Community 551 - "test_p0_roadmap_b3_b4_b5.py"
Cohesion: 0.16
Nodes (11): _deep_merge(), Deep merge two dicts. Override values take precedence., CircuitBreakerOpenError, CircuitState, Enum, RuntimeError, Raised when a request is blocked by an open circuit breaker., get_synthetic_pipeline() (+3 more)

### Community 552 - "TrainingSample"
Cohesion: 0.15
Nodes (9): Any, Add a step result. Returns the sample if accepted, None if filtered out., Bulk-add samples from an agent session's step results. Each step result with…, Return pipeline statistics., A single instruction/response pair for fine-tuning., Convert to Alpaca format: {instruction, input, output}., Convert to ShareGPT format: {conversations: [{from, value}]}., TrainingSample (+1 more)

### Community 553 - "test_company_api.py"
Cohesion: 0.11
Nodes (13): client(), Tests for Company Graph API endpoints., Create a test client for the FastAPI app., Test Company Graph API endpoints., Test that the company API router is included., Test Doctor endpoint., Test the public doctor endpoint., Regression tests for BUG-1: POST /api/company failing with `{"loc": ["body",… (+5 more)

### Community 554 - "TestStopSlopChecker"
Cohesion: 0.11
Nodes (10): Should detect phrases case-insensitively, Should detect throat-clearing phrases, Should return no issues for clean text, Strict mode should detect passive voice, Should detect multiple types of tells in one text, Issues should have helpful suggestions, Should detect business jargon, Should remove throat-clearing phrases (+2 more)

### Community 555 - "test_schedule_persistence.py"
Cohesion: 0.16
Nodes (13): _FakePersistence, tests/test_schedule_persistence.py — #505 schedules survive restart. Regression…, Populate the store directly so hydration tests don't depend on the timing of…, Regression for the production startup path: services/background.py runs inside…, The sync attach_persistence()/rehydrate() must stay safe even if called from…, In-memory stand-in for ScheduleStore (no Mongo needed in tests)., A disabled job must be registered (paused) on rehydrate so a later…, _seed() (+5 more)

### Community 556 - "test_telegram_service_webhook.py"
Cohesion: 0.18
Nodes (11): _FakeResponse, _make_task(), SimpleNamespace, Regression tests for telegram_service.NotificationDispatcher._notify_webhook.…, Regression: _notify_webhook used to define _send() but never call it., Drain any daemon threads spawned by the dispatcher (webhook/telegram). Snapshot…, Ensure _notify_webhook redacts secrets/PII before sending the webhook payload.…, Replace threading.Thread with a synchronous stub for this test class. (+3 more)

### Community 557 - "test_telegram_webhook.py"
Cohesion: 0.14
Nodes (11): client(), asyncio, tests/test_telegram_webhook.py — inbound Telegram webhook receiver. The webhook…, When every attempt fails, the last error is returned so the caller can fall…, The secret must go in the POST body, never the URL (URLs get logged)., A transient setWebhook failure (Telegram's own resolver hiccup) is retried and…, test_process_webhook_update_never_raises(), test_process_webhook_update_routes_callback_and_message() (+3 more)

### Community 558 - "handle_workflow_ide_chat"
Cohesion: 0.18
Nodes (17): _extract_last_user_message(), handle_workflow_ide_chat(), _json_response(), Any, JSONResponse, Request, StreamingResponse, workflow/ide_bridge.py — OpenAI-compatible SSE bridge for IDE clients. This… (+9 more)

### Community 559 - "harness_spec.py"
Cohesion: 0.19
Nodes (14): _int_env(), _known_entry_texts(), _one_line(), Any, Path, agent/harness_spec.py — the Continual Harness: a persistent, cited spec.…, Absolute path of the harness spec for a workspace., Recorded lessons as ``{signature: {acceptable text, ...}}``. The citation binds… (+6 more)

### Community 560 - "scrub"
Cohesion: 0.12
Nodes (16): _phase_section(), Any, Strip credentials from text before it is written into an issue body. Failure…, Live counters, for the diagnostics endpoint and tests., The in-process phase view — authoritative, and the reason this works with no…, The Render-log view: a cross-check, and the only source for windows the process…, Run *coro* without blocking the caller, from any thread. The caller is a…, _render_section() (+8 more)

### Community 561 - "_extract_tags"
Cohesion: 0.15
Nodes (8): _extract_tags(), _first_paragraph(), Path, Return the first non-empty, non-heading line. Skips YAML frontmatter (--- ...…, Pull hashtags and bold words from markdown as tags., Tests for module-level helper functions., Regression: frontmatter (--- ... ---) must not surface as '---'., TestHelpers

### Community 562 - "agile_api.py"
Cohesion: 0.28
Nodes (16): complete_sprint(), create_sprint(), _get_mgr(), get_velocity(), list_sprints(), Any, BaseModel, get (+8 more)

### Community 563 - "SKILL: Industrial Brutalism & Tactical Telemetry UI"
Cohesion: 0.12
Nodes (16): 1. Skill Meta, 2.1 Swiss Industrial Print, 2.2 Tactical Telemetry & CRT Terminal, 2. Visual Archetypes, 3.1 Macro-Typography (Structural Headers), 3.2 Micro-Typography (Data & Telemetry), 3.3 Textural Contrast (Artistic Disruption), 3. Typographic Architecture (+8 more)

### Community 564 - "Skill: data-quality-audit"
Cohesion: 0.12
Nodes (16): 1. Token Length Distribution, 2. Deduplication Check, 3. Tokenizer Fertility Check, 4. Special Token Consistency, 5. Language Detection (if langdetect available), 6. Content Quality Signals, Background (Why This Matters), Checks Performed (+8 more)

### Community 565 - "What "Slop" Looks Like"
Cohesion: 0.12
Nodes (16): Acceptance Checks, Category 1 — Obvious Comments, Category 2 — Phantom Abstractions, Category 3 — Defensive Checks for Impossible Cases, Category 4 — Speculative Generality, Category 5 — Verbose Variable Names, Category 6 — Unasked-For Boilerplate, Instructions (+8 more)

### Community 566 - "local_brain_router.py"
Cohesion: 0.19
Nodes (16): get_local_brain_state(), HeartbeatBody, post_local_brain_heartbeat(), post_local_brain_toggle(), Any, BaseModel, get, post (+8 more)

### Community 567 - "run"
Cohesion: 0.18
Nodes (14): CreateIssue, build_body(), _failures(), find_tracking_issue(), _gh_ops(), main(), Reconcile the probe summary to exactly one tracking issue. Returns an action…, probe_report.py — turn a catalogue-probe run into one tracking issue. The… (+6 more)

### Community 568 - "Section-by-Section Acceptance Criteria"
Cohesion: 0.12
Nodes (16): 467 Final Acceptance Criteria, §A — Company Graph + Onboarding, §B — 34 Specialist Families, §C — ECC, Obsidian, Graphify, Council Review Wiring, §D — Direct Chat as Control Center, Definition of Done, §E — Workflow Engine as Canonical Backbone + Worktree Isolation, §F — Doctor Full Check List (+8 more)

### Community 569 - "McpCard.jsx"
Cohesion: 0.14
Nodes (9): getRenderHealth(), getRenderOpsStatus(), runRenderOpsScan(), api, BTN, McpCard(), NOTE(), relTime() (+1 more)

### Community 570 - "Provider"
Cohesion: 0.15
Nodes (10): NVIDIA NIM provider adapter — wraps the existing provider_router logic. This is…, Ollama provider adapter — local LLM inference., packages/ai/manager.py — ProviderManager. Single entry point for all LLM calls.…, Provider, ABC, packages/ai/provider.py — Provider abstraction interface. Every LLM provider…, Base interface every provider must implement. Implementations live in…, Lower = higher priority in the fallback chain. (+2 more)

### Community 571 - "redact_connection_url"
Cohesion: 0.17
Nodes (7): packages/security/redact.py — strip secrets out of strings before they reach a…, Strip embedded credentials from a connection URI before logging it. Covers both…, redact_connection_url(), Regression test: production leaked a live MongoDB password in plaintext.…, Integration coverage: the actual log lines this module emits must never carry…, TestLoggingCallSitesRedactCredentials, TestRedactConnectionUrl

### Community 572 - "agent_readiness_audit.py"
Cohesion: 0.21
Nodes (15): _grade(), main(), PillarResult, scripts/agent_readiness_audit.py — score this repo's fitness for autonomous…, ReadinessReport, run_audit(), score_build_system(), score_dev_environment() (+7 more)

### Community 573 - "sync_ngrok.py"
Cohesion: 0.24
Nodes (15): detect_ngrok_url(), dim(), fail(), header(), info(), main(), ok(), patch_platform_brain_via_switch_brain() (+7 more)

### Community 574 - "test_ci.sh"
Cohesion: 0.15
Nodes (16): ADMIN_EMAIL, ADMIN_PASSWORD, API_KEYS, cleanup(), DB_NAME, fail(), LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY (+8 more)

### Community 575 - "test_task_brain_preflight.py"
Cohesion: 0.21
Nodes (14): _is_brain_connection_error(), BaseException, True if *exc* looks like an LLM-brain/endpoint connectivity failure. Such…, _coordinator(), asyncio, BaseException, Brain-availability preflight tests (graceful degradation). When NO LLM brain is…, _RecordingRuntimeManager (+6 more)

### Community 576 - "test_activation_api.py"
Cohesion: 0.21
Nodes (16): _client(), TestClient, Tests for activation_api — instance status, OpenAPI schema, and role route.…, GET /api/activation/settings is PUBLIC — non-admin users need to read the…, test_change_role_rejects_invalid_role(), test_change_role_requires_authentication(), test_change_role_returns_404_for_missing_user(), test_change_role_updates_existing_user() (+8 more)

### Community 577 - "TestAListingFailureDoesNotVetoTheAnswer"
Cohesion: 0.17
Nodes (9): A refused catalogue says nothing about whether a named model answers. On…, A provider whose /models refuses but whose /chat works., No ``--model`` given: the provider's declared default is the target., Answered-but-unlistable is a different fact from unreachable. Collapsing the…, The relaxation must not turn a real failure into a pass., Nothing was asked to be called, so nothing proved the provider is up., Rule 6, re-asserted on the branch this change introduces., A call that was never sent is not evidence that anything answered.… (+1 more)

### Community 578 - "test_daily_automation_2026_07_11.py"
Cohesion: 0.15
Nodes (16): Path, Tests for daily automation 2026-07-11: sub-agent delegation depth guard.…, The depth guard must return a dict, never raise an exception., Default depth cap matches Claude Code's 5-level limit., MAX_SUBAGENT_DEPTH must be a positive integer (safety assertion)., When _depth == MAX_SUBAGENT_DEPTH, _spawn_subagent must return an error., At depth MAX_SUBAGENT_DEPTH - 1 the spawn must be attempted (not blocked)., Child AgentRunner._depth must be parent._depth + 1. (+8 more)

### Community 579 - "test_frontend_deployment_guards.py"
Cohesion: 0.18
Nodes (16): SetupWizardPage must render <input type='checkbox'> for each provider toggle., Step 3 runtime config must render checkboxes for each runtime., OAuth must originate from the operator-configured backend, never a hardcoded…, index.css must override appearance:none for checkboxes/radios., The checkbox appearance override must NOT set appearance:none (that would keep…, The checkbox appearance override must use 'auto' to request native rendering.…, _read(), test_api_redirects_respect_public_and_backend_paths() (+8 more)

### Community 580 - "test_health_endpoints.py"
Cohesion: 0.17
Nodes (16): _make_fake_client(), Exception, Tests for /health, /live, and /api/health endpoints., When Ollama is down, /api/health should also return a degraded status., Return a context-manager-compatible mock for httpx.AsyncClient., Container liveness probe must always return 200., Health endpoint exists and returns a JSON body., Health endpoint includes provider states when ProviderRouter is wired in. (+8 more)

### Community 581 - "test_keepalive.py"
Cohesion: 0.18
Nodes (16): Path, Smoke test for scripts/keepalive.py (Windows-friendly Render + Ollama keepalive…, `--diagnose` mode exits 1 when hosts are unreachable (per docstring: exit 0/1)., Reload scripts.keepalive with KEEPALIVE_LOG = log_path and clear cache., KEEPALIVE_LOG under tmp_path; log_path() ensures parent directory exists., _rotate_log_if_needed() is a no-op when file is under MAX_LOG_BYTES; truncates…, _log() writes '[YYYY-MM-DD HH:MM:SS] <line>' to KEEPALIVE_LOG., When Render + Ollama are both unreachable, run_once() returns 1. (+8 more)

### Community 582 - "test_openclaw_endpoints.py"
Cohesion: 0.12
Nodes (10): client(), tests/test_openclaw_endpoints.py — OpenClaw HTTP + WebSocket endpoint tests., After pairing, ping command returns pong., Unknown command returns error., WebSocket with wrong token is rejected (connection closed)., WebSocket with correct token pairs successfully., test_websocket_pairing_accepts_correct_token(), test_websocket_pairing_rejects_wrong_token() (+2 more)

### Community 583 - "test_orchestrator_merge_decision.py"
Cohesion: 0.22
Nodes (13): _company(), _FakeStore, orch(), Company, Tests for the G5 RepoConnection/DeliveryPolicy wiring into the orchestrator…, test_record_consent_noop_for_non_gate_decision(), test_record_consent_noop_without_decision(), test_record_consent_persists_for_first_merge() (+5 more)

### Community 584 - "TestRoutes"
Cohesion: 0.19
Nodes (7): _install_service(), Tests for agents/portfolio_api.py — the v5 portfolio board API. Loads the…, A materializer exception must not break /refresh (the board still returns), and…, Install a PortfolioService whose portfolio is fixed (no rebuild)., _seeded_manager(), TestBoardPayload, TestRoutes

### Community 585 - "test_skill_registry.py"
Cohesion: 0.13
Nodes (9): _FakeClient, _FakeResp, tests/test_skill_registry.py — Unit tests for agent/skill_registry.py, Tests for WORKFLOW_SKILL_MAP., Stub httpx client for nested-registry fetch tests., Production regression: server started from a non-repo CWD indexed 0 local…, test_local_skills_dir_defaults_to_repo_root_not_cwd(), test_nested_registry_indexes_deeply_nested_skills() (+1 more)

### Community 586 - "hermes_prompt.py"
Cohesion: 0.19
Nodes (15): build_chatml_system_prompt(), format_chatml_message(), format_tool_call(), format_tool_response(), messages_to_chatml(), model_supports_chatml(), parse_tool_call_from_chatml(), Any (+7 more)

### Community 587 - "test_lessons.py"
Cohesion: 0.25
Nodes (14): _get_store(), Failure lessons: turn failed runs into context for the next run. The supervisor…, Formatted prompt block of recent lessons, or '' when none exist., Persist a lesson for every failed step in a run. Never raises., recent_lessons_block(), record_step_failures(), _fresh_store(), Tests for agent/lessons.py — the failure-lesson learning loop. (+6 more)

### Community 588 - "MemoryMiddleware"
Cohesion: 0.17
Nodes (10): create_memory_middleware(), MemoryMiddleware, Any, Process incoming chat request and inject memories., Extract and save learnings from model responses., Factory function to create memory middleware instance., Middleware for automatic memory loading and injection., Detect AI coding tool from request headers. (+2 more)

### Community 589 - ".force_cleanup"
Cohesion: 0.14
Nodes (11): Atomically delete a run-once row only while it is still unfired. Closes the…, _age_seconds(), The one retention policy for unfired one-shots, read from its owner.…, Drop a job from in-memory state and APScheduler (mirrors ``delete()``). Popping…, Durably remove one job, then drop its in-memory + APScheduler mirrors. The…, Durably remove one **unfired** run-once row and its in-memory mirror. Prefers…, Force-dedup and clean stale schedules from both the durable store and in-memory…, Seconds since ``created_at``. Unparseable or missing reads as brand new. Erring… (+3 more)

### Community 590 - "._resolve_path"
Cohesion: 0.15
Nodes (5): Path, Precise string replacement — F1 roadmap item (Codebuff/Claude Code-style edit).…, Return the first *lines* lines of a file. Just-in-time retrieval: the executor…, Return a lightweight index of files with line counts and sizes. This is the…, Resolve filepath relative to workspace_root, rejecting traversal attempts. Uses…

### Community 591 - "AITellIssue"
Cohesion: 0.17
Nodes (8): AITellIssue, Find all AI tells in text, Find throat-clearing phrases, Find emphasis crutches (weak adverbs), Find meta-commentary (text referring to itself), Find Wh-sentence starters (weak prose starters), Find basic passive voice patterns (strict mode only), Format issues as human-readable report

### Community 592 - "Skill: repowise-intelligence"
Cohesion: 0.12
Nodes (15): 1. Graph Intelligence (Dependency Graph), 2. Git Intelligence, 3. Documentation Intelligence, 4. Decision Intelligence, Acceptance Checks, Directory Structure, Example Usage, Implementation Approach (+7 more)

### Community 593 - "ARCHITECTURE.md — Target Architecture"
Cohesion: 0.12
Nodes (15): 1. Target Repository Structure, 2. Dependency Rules, 3. Provider Architecture (Target), 4. Configuration Architecture (Target), 5. Event Bus Architecture (Target), 6. Scheduler Architecture (Target), 7. Dashboard Architecture (Target), 8. Migration Principles (+7 more)

### Community 594 - "_valid_login_state"
Cohesion: 0.24
Nodes (15): Return True if a fetched oauth_states doc is a valid, unexpired login state., _valid_login_state(), _doc(), Regression tests for social-login (GitHub & Google) OAuth state handling. Bug…, MongoDB/motor returns naive UTC datetimes. Subtracting a naive datetime from an…, The login handlers must persist state via _store_login_state, not the session…, test_expired_state_rejected(), test_just_within_window_accepted() (+7 more)

### Community 595 - "Skill: repowise-intelligence"
Cohesion: 0.12
Nodes (15): 1. Graph Intelligence (Dependency Graph), 2. Git Intelligence, 3. Documentation Intelligence, 4. Decision Intelligence, Acceptance Checks, Directory Structure, Example Usage, Implementation Approach (+7 more)

### Community 596 - "The 10-Step Workflow"
Cohesion: 0.12
Nodes (15): Cross-Tool Compatibility, Quick Reference Card, Skill: session-planning — Mandatory Planning Workflow for All AI Agents, Step 10 — Close Out, Step 1 — Orient (free), Step 2 — Understand the Task, Step 3 — Load Relevant Skills, Step 4 — Research (if novel task) (+7 more)

### Community 597 - "Nothing is blocked on an agent. Two things need a human."
Cohesion: 0.12
Nodes (15): 0. NVIDIA models — resolved, with one measurement still missing, 0b. `nvidia/nemotron-3-ultra-550b-a55b` — RESOLVED, restored to the rotation, 0c. The daily `Update repo with latest details` routine needs one edit from you, 1. Render is suspended for billing — this is the big one, 2. `anthropic >=1.0.0` — resolved, and the premise was wrong, 3. The loop overrode its own recorded REJECT, inside a single pull request, 4. The backlog is at zero, and the gates that let bad work through are closed, 5. The catalogue probe was letting a refused listing veto the answering (+7 more)

### Community 598 - "Contributing to local-llm-server"
Cohesion: 0.12
Nodes (16): Architecture, Bug Reports, Changelog, Coding Standards, Commit Message Convention, Contributing to local-llm-server, Development Setup, Feature Requests (+8 more)

### Community 599 - "refresh_agent_built_proof.py"
Cohesion: 0.20
Nodes (13): date, extract_counts(), fetch_counts(), main(), ProofCounts, scripts/refresh_agent_built_proof.py Root-cause fix for the "agent-built proof"…, Parse the counts currently committed in proof/agent-built.md's table., Rewrite the "As of", table rows, and summary sentence in agent-built.md. (+5 more)

### Community 600 - "CEO Micro-Management"
Cohesion: 0.12
Nodes (16): A failed drive does not abandon the goal, CEO Micro-Management, Configuration reference, Escalation, and why it terminates, Five bounds, Operator surface, Tests, The 24x7 supervisor (+8 more)

### Community 601 - "467 Brutal Audit — File-by-File Status"
Cohesion: 0.12
Nodes (15): 467 Brutal Audit — File-by-File Status, Agent System, Backend & Services, Core Proxy & Routing, Direct Chat, Feature Matrix (spec §I — demotions needed), Frontend / Public Site (spec §H — 0% delivered), GitHub Workflows (+7 more)

### Community 602 - "Migration Notes"
Cohesion: 0.12
Nodes (16): Compose secret scoping — shipped, opt-in, Container hardening overlay, Known limitations at merge, Migration Notes, Optional hardening (operator decisions), Path to enforcement, Protect the policy file from agents, Rollback (+8 more)

### Community 603 - "Runbook — Apply the Fast Free NVIDIA Brain to Render (TASK 2)"
Cohesion: 0.12
Nodes (15): B.1 — Open the service's Environment tab, B.2 — Set these five keys on each service, B.3 — Sanity-check the secrets that must NOT regress, B.4 — Trigger TASK 5 keep-alive immediately, Option A — Blueprint sync (preferred), Option B — manual per-service editor, Rollback, Runbook — Apply the Fast Free NVIDIA Brain to Render (TASK 2) (+7 more)

### Community 604 - "test_agent_chat_integration.py"
Cohesion: 0.23
Nodes (14): LogCaptureFixture, _fake_auth(), _make_nim_providers(), AuthContext, MonkeyPatch, Path, Integration tests for /agent/chat endpoint and AGENT_RUNNER configuration.…, test_agent_chat_passes_session_store_to_runner() (+6 more)

### Community 605 - "NvidiaProvider"
Cohesion: 0.13
Nodes (5): NvidiaProvider, NVIDIA NIM — free LLM provider (meta/llama-3.3-70b-instruct)., RateLimit, Provider rate limit info., Return the provider's rate limits.

### Community 606 - "SQLiteStore"
Cohesion: 0.17
Nodes (8): Connection, Top-level store — exposes collections as attributes. Usage:: store =…, Lazily build the pool of read-only connections (idempotent)., Yield a read connection from the pool (falls back to the writer). On in-memory…, Create tables if they don't already exist., SQLiteStore, store(), test_get_store_returns_sqlite()

### Community 607 - "fabric_cli.py"
Cohesion: 0.29
Nodes (15): cmd_apply(), cmd_list(), cmd_new(), cmd_save(), cmd_show(), cmd_stitch(), _ensure_patterns_dir(), main() (+7 more)

### Community 608 - "AdminDigestRouterAuthTests"
Cohesion: 0.20
Nodes (6): DigestPayload, AdminDigestRouterAuthTests, Stub for telegram_service.NotificationDispatcher used by /send., tests/test_admin_digest_router.py — Coverage for /api/admin/digest/* endpoints.…, Build a FastAPI TestClient against an app shell with only the…, _StubDispatcher

### Community 609 - "GuardResult"
Cohesion: 0.16
Nodes (8): GuardResult, Any, Check user input against input safety rules. Returns a GuardResult with…, Check model output against output safety rules. Returns a GuardResult with…, Unified check method. direction = 'input' or 'output'., Return guardrail statistics., Result of a guardrail check., TestGuardResult

### Community 610 - "test_telegram_auto_approve.py"
Cohesion: 0.21
Nodes (15): is_sensitive(), True when *text* references a sensitive target (auth/keys/secrets/service…, _build_execution_request(), Any, Build a minimal ``ExecutionRequest`` for plain-text → orchestrator.execute.…, admin_user(), _auto_approve(), non_admin_user() (+7 more)

### Community 611 - "ManagedAgentDreams"
Cohesion: 0.22
Nodes (4): ManagedAgentDreams, Manages recording session memories and consolidating them into dreams., Tests for ManagedAgentDreams., TestManagedAgentDreams

### Community 612 - "e2e/test_browser.py"
Cohesion: 0.21
Nodes (15): base_url(), do_login(), fail(), ok(), Page, Navigate to a page and verify it loads without errors., Browser-based E2E tests — runs with Playwright against a live LLM Relay…, Verify server responds to health check before running browser tests. (+7 more)

### Community 613 - "test_agency_workflows_carry_the_failover_chain.py"
Cohesion: 0.18
Nodes (12): _agency_workflows(), parametrize, Path, Every workflow that runs an agent script must carry the whole brain chain.…, Rule 6 again, on the deploy side: `sync: false`, never `value:`., A selector that matched nothing would make every assertion vacuous., Rule 6: secrets are environment-only, never written into a file., `render.yaml` is the infrastructure declaration for the backend. A key that… (+4 more)

### Community 614 - "test_autonomy_status.py"
Cohesion: 0.12
Nodes (15): client(), TestClient, tests/test_autonomy_status.py — public /api/autonomy/status readiness probe.…, No auth required; response carries the readiness contract keys., The probe carries the loop fleet readiness summary (loop-audit)., Without NVIDIA key AND without Ollama, the probe must report no_brain., When NVIDIA is absent but Ollama is configured, report brain as ollama., With an NVIDIA key the brain resolves and the secret is no longer flagged. (+7 more)

### Community 615 - "test_dockerfile_ships_root_modules.py"
Cohesion: 0.17
Nodes (13): _dockerfile_text(), Regression guard: the backend image must ship every root-level Python module…, An env var set to empty string means unset, not a commit named ''., Unknown must read as unknown — a deploy check treats None as 'unverifiable' and…, True when the Dockerfile copies root .py modules wholesale (`COPY *.py ...`)., The worker's `python worker_main.py` start command needs worker_main.py., V2.0 Modernization: the image must ship `packages/` (provider_router,…, _ships_all_root_modules() (+5 more)

### Community 616 - "test_langfuse_agency_wide.py"
Cohesion: 0.12
Nodes (15): tests/test_langfuse_agency_wide.py — tests for PR #961 agency-wide Langfuse.…, langfuse_obs.py must define emit_agency_observation., emit_agency_observation must be a no-op when Langfuse is not configured., tasks/service.py must call emit_agency_observation for task execution., agent/agency.py must call emit_agency_observation for CEO directives., backend/server.py scheduler_tick must call emit_agency_observation., packages/ai/self_heal.py must call emit_agency_observation., emit_agency_observation must accept all documented parameters. (+7 more)

### Community 617 - "test_local_brain_state.py"
Cohesion: 0.12
Nodes (10): tests/test_local_brain_state.py — regression test for the cross-machine toggle.…, Operator flips OFF — any prior lease must be dropped so a future ON doesn't…, The store must not corrupt the model listing when reading back., The 3 endpoints MUST refuse calls without SERVICE_TOKEN — confirmed by mounting…, All three endpoints must be present on the router (regression guard against…, store(), test_router_3_endpoints_are_registered(), test_router_endpoints_require_service_token() (+2 more)

### Community 619 - "test_migrate_local_brain_env.py"
Cohesion: 0.38
Nodes (15): _make_env(), CompletedProcess, Path, tests/test_migrate_local_brain_env.py - regression suite for…, _run(), test_crlf_preserved_on_untouched_lines(), test_dry_run_does_not_mutate(), test_env_path_missing_file_exits_1() (+7 more)

### Community 620 - "test_phase5_doctor.py"
Cohesion: 0.12
Nodes (10): client(), tests/test_phase5_doctor.py Phase 5: /api/doctor endpoint tests. Coverage: -…, If RuntimeManager raises, /api/doctor still returns 200 with a warn check., If DirectChatDoctor.check_all raises, /api/doctor still returns 200., MongoStore.__getattr__ proxies any name to a Motor collection, so…, Langfuse check is always emitted (pass or warn based on env)., test_doctor_langfuse_check_present(), test_doctor_survives_preflight_error() (+2 more)

### Community 621 - "TestBrainFailoverBackoff"
Cohesion: 0.23
Nodes (7): The anti-wedge valve must not fire for an ordinary 429 backoff — otherwise it…, The threshold must clear the widest backoff ANY registered provider can earn.…, A corrupted/absurd cooldown must still be recoverable., The honest reset: probe permitted, failure history kept., A real success must still clear the breaker — allow_probe exists so that…, The behaviour the doom loop destroyed: each 429 waits longer. With…, TestBrainFailoverBackoff

### Community 622 - "test_refresh_agent_built_proof.py"
Cohesion: 0.12
Nodes (4): doc_paths(), tests/test_refresh_agent_built_proof.py Root-cause fix for the "agent-built…, The real committed docs, run through the rewriter with their own current…, test_rewrite_functions_are_idempotent_on_live_docs()

### Community 623 - "test_tasks_reconciler_todo_requeue.py"
Cohesion: 0.20
Nodes (15): _make_task(), asyncio, Task, Tests: reconciler handles TODO tasks with pending_agent_run=False. Covers the…, A TODO task with pending_agent_run=False must be re-queued by the reconciler., A TODO task with pending_agent_run=True does NOT need reconciliation., A DONE task is never touched by the reconciler regardless of pending flag., A TODO task currently in the active set must not be re-queued. (+7 more)

### Community 624 - "_hash_component"
Cohesion: 0.16
Nodes (6): TestWorkspacePathDerivation, The hash component should not be reversible to the original ID., Workspace root path should be fully resolved (no . or ..)., TestWorkspaceHashing, _hash_component(), Derive a stable, opaque directory name from a validated ID. Using a truncated…

### Community 625 - "check_kwargs"
Cohesion: 0.18
Nodes (8): check_kwargs(), Any, agent/contract_enforcement.py — Runtime signature locking (J) Provides…, # NOTE: limit has a default so it is accepted; owner_id is keyword-only., Raise TypeError on unknown kwarg (runtime extra='forbid'). Args: kwargs: The…, # NOTE: limit is NOT locked — it is a legitimate optional param that does not, Unit tests for the check_kwargs helper., TestCheckKwargs

### Community 626 - ".build"
Cohesion: 0.18
Nodes (11): MemoryTurn, Rough token estimate: 4 chars ≈ 1 token (minimum 1)., Run the full RAG pipeline and return a token-budget-respecting context.…, One turn in the conversation history., Select up to *top_k* highest-scoring turns that fit within *budget*. Returns…, A document selected by retrieval, with its compressed excerpt., RetrievedDoc, _token_count() (+3 more)

### Community 627 - "Skill: agent-harness"
Cohesion: 0.13
Nodes (14): Architecture, Combining with Other Skills, Key Concepts, Output Format, Purpose, Safety Rules, Skill: agent-harness, Step 1 — Define the task clearly (+6 more)

### Community 628 - "Skill: checkpoint-strategy"
Cohesion: 0.13
Nodes (14): After a Loss Spike, Aggressive (Long Runs with Stable Training), Background, Checkpoint Policy Templates, Conservative (Recommended for First Runs), Integration Points, Output Format, Purpose (+6 more)

### Community 629 - "Process"
Cohesion: 0.13
Nodes (14): Anti-Patterns, Process, Purpose, Rules, Skill: debug-tracer, Step 1: Reproduce First, Step 2: Gather Evidence, Step 3: Form Hypotheses (+6 more)

### Community 630 - "Skill: local-ai-query"
Cohesion: 0.13
Nodes (14): 1. Verify Ollama is available, 2. Choose appropriate model, 3. Send query to local model, 4. Generate embeddings (for RAG), 5. List running models, Integration with ChromaDB (RAG), Limitations, Prerequisites (+6 more)

### Community 631 - "Skill: parallel-agents"
Cohesion: 0.13
Nodes (14): Combining with Other Skills, Core Concepts (from the Modal/OpenAI Agents SDK pattern), Example — parallel approach exploration, Example — parallel research, Output Format, Phase 1 — Decompose, Phase 2 — Dispatch (simulate parallelism), Phase 3 — Aggregate (+6 more)

### Community 632 - "Skill: parallel-worktrees"
Cohesion: 0.13
Nodes (14): Acceptance Checks, Common Patterns, Concept, Constraints, Instructions, Pattern A — Test main while you implement, Pattern B — Review reference during refactor, Pattern C — Hotfix without disturbing feature work (+6 more)

### Community 633 - "Design System: Taste Standard"
Cohesion: 0.13
Nodes (14): 1. Visual Theme & Atmosphere, 2. Color Palette & Roles, 3. Typography Rules, 4. Component Stylings, 5. Hero Section, 6. Layout Principles, 7. Responsive Rules, 8. Motion & Interaction (Code-Phase Intent) (+6 more)

### Community 634 - "Process"
Cohesion: 0.13
Nodes (14): Integration with Other Skills, Process, Purpose, Rules, Skill: ticket-to-pr, Step 1: Parse the Issue, Step 2: Context Prime, Step 3: Plan the Implementation (+6 more)

### Community 635 - "cost_tracker.py"
Cohesion: 0.15
Nodes (14): cost_table(), Return the active per-model cost table (USD per million tokens). Useful for…, _build_cost_table(), clear_stats(), get_cost_table(), get_stats(), _load_env_overrides(), Any (+6 more)

### Community 636 - "Skill: user-research"
Cohesion: 0.13
Nodes (14): Architecture, As a Python library, As an agent tool, Auto-Registration, Files, Purpose, Pydantic Models (extra="forbid"), Sample-Size Math (+6 more)

### Community 637 - "Agency Core — Progress & Resume Log"
Cohesion: 0.13
Nodes (14): Agency Core — Progress & Resume Log, Audit (committed), Environment constraints discovered this session, How to resume (read before doing anything), Key findings (so we don't re-investigate), Open risks / must-know before merging, Phase 0 — Stabilize & quarantine (commit `713184a`, pushed), Planned CI-parity hardening (the immediate next commit) (+6 more)

### Community 638 - "Attention Mechanisms Internals"
Cohesion: 0.13
Nodes (14): Attention Complexity, Attention Mechanisms Internals, Causal Masking, Flash Attention, Grouped Query Attention (GQA), Multi-Head Attention (MHA), Multi-Query Attention (MQA), Parameter count for MHA: (+6 more)

### Community 639 - "ChatScreen.jsx"
Cohesion: 0.14
Nodes (8): listProviderModels(), listProviders(), AVAILABLE_AGENTS, CHAT_PHASES, HistorySidebar(), ModelPicker(), relTime(), SUGGESTIONS

### Community 640 - "_push_down_where"
Cohesion: 0.14
Nodes (14): _fully_pushable(), _is_pushable_scalar(), _push_down_where(), Any, Scalar values whose `str()` form matches how they were stored in the indexed…, Build a SQL ``WHERE`` suffix from the subset of *query* conditions that map…, True if EVERY condition in *query* is expressible in the SQL WHERE. Unlike…, Try to satisfy a sorted/paginated find entirely in SQL. Returns the decoded… (+6 more)

### Community 641 - "verify_api_key"
Cohesion: 0.14
Nodes (14): check_rate_limit(), _enforce_rate_limit(), _is_freebuff_unlimited(), True when this request targets a FreeBuff route and should skip rate limiting.…, Apply the per-key RPM limiter unless this request is FreeBuff-exempt.…, Accept both Authorization: Bearer <key> (standard) and x-api-key: <key> (Claude…, verify_api_key(), test_freebuff_unlimited_can_be_disabled() (+6 more)

### Community 642 - "router/health.py"
Cohesion: 0.20
Nodes (14): _enabled(), get_available_models(), invalidate_cache(), is_model_available(), Ollama model availability check with TTL cache. Keeps a short-lived cache of…, Force the next call to re-probe Ollama (useful in tests)., Return True if *model* is in the Ollama tag list (or health checks off).…, Return the set of model names currently present in Ollama. Returns an empty set… (+6 more)

### Community 643 - "check_model_catalog_consistency.py"
Cohesion: 0.22
Nodes (14): _check_cross_catalogue(), _check_prefer_models(), _check_presets(), _llm_declared(), _load(), main(), Any, Path (+6 more)

### Community 644 - "TestDecisionsBotLinks"
Cohesion: 0.17
Nodes (5): # NOTE: ``decision_id`` is NOT a SQL FOREIGN KEY here. The bot's, tests/test_decisions_bot_links.py Pytest coverage for the new…, Decision prompts that exist *before* the orchestrator creates a run (e.g. a…, Re-sending the same Telegram message (offset rewind, bot restart re-delivery)…, TestDecisionsBotLinks

### Community 645 - "DecisionsStore"
Cohesion: 0.30
Nodes (3): DecisionsStore, Any, Connection

### Community 646 - "clear_wizard_state_cache"
Cohesion: 0.21
Nodes (10): clear_wizard_state_cache(), Override the persistence collection used for wizard state. Tests and hosted…, Clear the in-memory wizard-state cache., set_wizard_state_collection(), _FakeWizardCollection, SimpleNamespace, TestClient, _setup_client() (+2 more)

### Community 647 - "test_critical_flows.py"
Cohesion: 0.26
Nodes (14): _do_login(), _http_ok(), _playwright(), Critical-flow E2E tests (Playwright) — the five journeys that must never break.…, Create a task via the REST API (the same endpoint the UI calls) and poll its…, Direct (non-agent) chat: hit the OpenAI-compatible proxy completion the same…, Best-effort login. Returns True if we end up authenticated., _require_backend() (+6 more)

### Community 648 - "TestBrainConfigUpdates"
Cohesion: 0.22
Nodes (3): Verify brain_config.py changes: Google provider, updated presets., The durable property, not the id of the week. This assertion has been amended…, TestBrainConfigUpdates

### Community 649 - "test_dockerfile_ships_config_dir.py"
Cohesion: 0.14
Nodes (14): _dockerfile_text(), Regression guard: the backend image must ship ``config/``. `config/llm/*.yaml`…, The two properties that made the ungated entry expensive in production., The ceiling that #1172 added must survive in the file that ships. Sized against…, Without this COPY the router silently runs on defaults in production., A shipped directory is worthless if the files moved out of it., A .dockerignore entry would defeat the COPY without touching it., A keyless local provider must not join the chain just by existing. ``ollama``… (+6 more)

### Community 650 - "test_scanner_live.py"
Cohesion: 0.23
Nodes (14): _assert_scan_contract(), asyncio, parametrize, LIVE integration tests for the website scanner — these actually hit the real…, Representative large storefronts that commonly sit behind bot protection. Same…, Directly exercise the BuiltWith fallback against the live builtwith.com.…, The invariants that must hold for any live scan, bot-protected or not., A normal, non-bot-protected site must yield real detections. This is the… (+6 more)

### Community 651 - "test_task_service_failed_comment.py"
Cohesion: 0.21
Nodes (14): coordinator(), _make_result(), asyncio, tests/test_task_service_failed_comment.py — verify that a FAILED TaskResult…, A FAILED TaskResult without agent_comment transitions to FAILED without…, A FAILED TaskResult sets task.error_message to result.output., A SUCCESS TaskResult with agent_comment posts it as a task comment., Build a minimal TaskResult-like object for _apply_result. (+6 more)

### Community 652 - "compilerOptions"
Cohesion: 0.13
Nodes (14): compilerOptions, isolatedModules, jsx, lib, module, moduleResolution, noEmit, resolveJsonModule (+6 more)

### Community 653 - "migrate_local_brain_env.py"
Cohesion: 0.19
Nodes (12): Any, Return recent commits with agent attribution trailers parsed out., _detect_crlf(), _enumerate_matching_lines(), _eprint(), main(), Path, CRLF present if any line ends in CRLF. (+4 more)

### Community 654 - "_TFIDFIndex"
Cohesion: 0.16
Nodes (11): Lightweight TF-IDF index over a fixed document collection. Sparse dict vectors…, Return ``(doc_index, cosine_score)`` pairs for the top-*k* matches., Return lowercase alphanumeric tokens with stop-words removed. Numeric tokens…, _TFIDFIndex, _tokenize(), test_tfidf_empty_corpus(), test_tfidf_empty_query(), test_tfidf_finds_relevant() (+3 more)

### Community 655 - "StopSlopChecker"
Cohesion: 0.14
Nodes (8): Initialize checker. Args: strict: If True, also report adverbs even if not in…, Remove most obvious AI tells from text, Detect and optionally remove AI tells from text, StopSlopChecker, Should format report correctly, Should report success on clean text, Should detect weak emphasis adverbs, Should detect meta-commentary

### Community 656 - "Process"
Cohesion: 0.14
Nodes (13): 1. Read and Understand the Issue, 2. Explore the Codebase, 3. Plan the Solution, 4. Implement, 5. Test, 6. Document, 7. Commit and Push, Notes (+5 more)

### Community 657 - "Skill: lr-schedule-advisor"
Cohesion: 0.14
Nodes (13): Background (Why This Matters), Common Mistakes, Cosine with Warmup (Recommended for Pretraining), Fine-tuning vs Pretraining, Integration Points, Output Format, Peak LR Heuristics by Model Size, Purpose (+5 more)

### Community 658 - "Instructions"
Cohesion: 0.14
Nodes (13): 1 — Tests green, 2 — Changelog updated, 3 — Determine the version bump, 4 — Update changelog, 5 — Commit the changelog update, 6 — Tag the release, 7 — Verify CI on the tag, 8 — Post-release (+5 more)

### Community 659 - "Instructions"
Cohesion: 0.14
Nodes (13): Acceptance Checks, `admin_auth.py` checklist, `agent/tools.py` checklist, Escalation, Instructions, `key_store.py` checklist, `proxy.py` auth middleware checklist, Risky Modules in This Repo (+5 more)

### Community 660 - "Process"
Cohesion: 0.14
Nodes (13): 1. Decompose the Task, 2. Sequence the Skills, 3. Execute in Order, 4. Handle Failures, 5. Synthesize Output, 6. Document the Composition, Example Compositions, Notes (+5 more)

### Community 661 - "Checks Performed"
Cohesion: 0.14
Nodes (13): 1. Round-trip Consistency, 2. Numeric Tokenization, 3. Whitespace Handling, 4. Special Character Coverage, 5. Fertility by Domain, 6. Vocabulary Overlap Check (for model updates), Background, Checks Performed (+5 more)

### Community 662 - "Skill: training-stability-monitor"
Cohesion: 0.14
Nodes (13): Example Checks Performed, Gradient Norm Check, Integration Points, Key Lessons (from LLM-from-scratch practitioners), Loss Spike Detection, LR Warmup Validation, Notes, Output Format (+5 more)

### Community 663 - "test_new_features_e2e.py"
Cohesion: 0.29
Nodes (12): APIRequestContext, base_url(), do_login(), fail(), ok(), Page, Browser-based E2E tests for the 33 new roadmap features. Covers: - Dashboard UI…, Result (+4 more)

### Community 664 - "admin_digest_router.py"
Cohesion: 0.22
Nodes (13): _build_payload_or_500(), _check_secret(), _expected_secret(), preview_digest_endpoint(), Any, get, post, Dry-run: same auth, returns the would-be markdown body but does NOT dispatch to… (+5 more)

### Community 665 - "Skill: branch-cleanup"
Cohesion: 0.14
Nodes (13): Acceptance Checks, Automation — post-merge hook (optional), Option A — git push (standard), Option B — GitHub API (use when `git push --delete` returns 403), Option C — Delete local tracking refs after remote deletion, Skill: branch-cleanup, Step 1 — Confirm master is up to date, Step 2 — List all remote branches (+5 more)

### Community 666 - "Skill: perplexity — Web Research via Perplexity API"
Cohesion: 0.14
Nodes (13): Applying to this Repo, How to Query, No API Key? Use WebSearch, Prerequisites, Quick query (one-shot Python call), Run inline, Skill: perplexity — Web Research via Perplexity API, Skill Steps (+5 more)

### Community 667 - "Instructions"
Cohesion: 0.14
Nodes (13): 1 — Tests green, 2 — Changelog updated, 3 — Determine the version bump, 4 — Update changelog, 5 — Commit the changelog update, 6 — Tag the release, 7 — Verify CI on the tag, 8 — Post-release (+5 more)

### Community 668 - "Instructions"
Cohesion: 0.14
Nodes (13): Acceptance Checks, `admin_auth.py` checklist, `agent/tools.py` checklist, Escalation, Instructions, `key_store.py` checklist, `proxy.py` auth middleware checklist, Risky Modules in This Repo (+5 more)

### Community 669 - "Quick-Note Issues Processing Summary"
Cohesion: 0.14
Nodes (13): 🔗 Branch References, ✅ Completed, Future Session, Immediate (Session-Aware), Issue #229 — Stop-Slop AI Quality Checker, Issue #263 — Graphiti Temporal Context, Issue #266 — ECC Multi-Harness Adapter, 💡 Key Learnings (+5 more)

### Community 670 - "DirectChatSession"
Cohesion: 0.15
Nodes (10): detect_company_id(), DirectChatSession, handle_chat_message_with_context(), Direct chat session with Company Graph context binding., Bind a company to this chat session and load its Company Graph., Bind a repository to this chat session., Get the bound Company Graph., Get enriched context including Company Graph data. (+2 more)

### Community 671 - "Main proxy (`proxy.py`)"
Cohesion: 0.14
Nodes (14): Agent and workflow surfaces, API Surfaces and Route Map, Built-in admin and web UI, Connectors (`/api/connectors/*`, `backend/connectors_api.py`, admin-only), Control-plane style routers mounted in the proxy, CRISPY Workflow engine (`/api/workflow/*`, `workflow/api.py`, admin-only), Governance (`/api/governance/*`, admin-only), Main proxy (`proxy.py`) (+6 more)

### Community 672 - "Implementation Plan — DB-persisted, UI-switchable Brain (no redeploy)"
Cohesion: 0.14
Nodes (13): 0. Why this exists (root cause this fixes), 1. Hard constraints (from the owner), 2. Provider strategy (the recommendation), 3. Architecture, 3a. Store — `services/brain_config_store.py` (new), 3b. Call-time resolution — `agent/loop.py`, 3c. Admin API — `backend/server.py`, 3d. UI — `webui/frontend/src/pages` (+ `webui/router.py` / `providers.py`) (+5 more)

### Community 673 - "Backend changes"
Cohesion: 0.14
Nodes (13): `activation_api.py`, `app_settings.py` (new), Backend changes, `backend/company_api.py`, `db/sqlite_store.py`, Docs / changelog, Frontend changes, Goal (+5 more)

### Community 674 - "Render MCP — autonomous platform debugging and environment monitoring"
Cohesion: 0.14
Nodes (13): 1. Coding sessions — stdio, via `.mcp.json`, 2. The running agency — Streamable HTTP against a deployed sidecar, Configuration, Enabling it, HTTP API, If the private address does not resolve, Playwright, Render MCP — autonomous platform debugging and environment monitoring (+5 more)

### Community 675 - "Runbook: Auto-Resume After Cooldown / Interruption"
Cohesion: 0.14
Nodes (13): Commands, Cooldown Detection, Cooldown Detection Logic, Force-Resume After Stale Lock, Forcing an Abort, How It Works, Inspecting a Stuck Run, Overview (+5 more)

### Community 676 - "SEO / GEO / AIO Audit Engine"
Cohesion: 0.14
Nodes (14): API, Architecture, Delegation plan → agent tasks, Demo from the UI, Exports — the full heavy report, Fetching bot-protected sites (`fetch_mode`), Provenance, Repo-aware auto-fixing (+6 more)

### Community 677 - "overrides"
Cohesion: 0.14
Nodes (14): @tootallnate/once, overrides, bfj, css-select, http-proxy-agent, jsonpath, nth-check, postcss (+6 more)

### Community 678 - "_build_request"
Cohesion: 0.18
Nodes (7): _build_request(), Return ``(url, headers, is_anthropic_native)`` for *provider*. Anthropic's…, TestBuildRequest, Rotation needs the variable the key came from. Deriving it from the provider id…, No pool configured — the pre-rotation path, unchanged., Anthropic uses x-api-key, not Bearer — the override must reach it., TestBrainChainIntegration

### Community 679 - "_parse_reset_epoch"
Cohesion: 0.21
Nodes (6): _parse_reset_epoch(), _ProviderQuota, Response, Parse x-ratelimit-* headers and update per-provider quota state. Safe to call…, Convert a provider reset-time header value to a monotonic deadline. Supported…, TestParseResetEpoch

### Community 680 - "extract_failures"
Cohesion: 0.21
Nodes (7): extract_failures(), Return up to *max_results* unique failing node IDs from pytest *output*. Order…, Without a banner we scan everything, but the shape check still holds., End-to-end extraction over realistic pytest output., Issue #1354: log records must never be reported as failing tests., Issue #1352: an ERROR-only run must still report the failing test., TestExtractFailures

### Community 681 - "_RedisBackend"
Cohesion: 0.22
Nodes (5): Redis-backed shared state using SET NX / DELETE / SETEX / INCR+EXPIRE., Lazy-create the Redis client (imported on first use so a missing ``redis``…, Clear all cooldown entries (for test teardown)., Clear all probe-lock entries (for test teardown). Mirrors…, _RedisBackend

### Community 682 - "cmd_autonomy"
Cohesion: 0.23
Nodes (13): _backend_get(), cmd_autonomy(), cmd_loops(), _grade_icon(), GET an un-gated backend read endpoint (/api/autonomy/status, /api/loops). These…, Snapshot of the agency's autonomy: active brain, loop readiness, dispatch., Loop Engineering fleet readiness + the costliest loops, from /api/loops., tests/test_telegram_observe.py Tests for the read-only "observe from Telegram"… (+5 more)

### Community 683 - "_process_task_callback"
Cohesion: 0.34
Nodes (13): _process_task_callback(), Handle Approve/Reject inline-button presses for task execution gates. Callback…, _make_fake_task(), _patch_workflow(), Robustness tests for the Telegram inline-button callback flow., test_approve_success_clears_spinner_and_edits_message(), test_reject_success_clears_spinner_and_edits_message(), test_storage_init_failure_clears_spinner() (+5 more)

### Community 684 - "TestAnthropicToolListCaching"
Cohesion: 0.34
Nodes (3): input_schema passthrough — native Anthropic tools should not be wrapped again., AnthropicProvider.build_payload caches the tool list when prompt_caching=True…, TestAnthropicToolListCaching

### Community 685 - "TestMCPToolsListCache"
Cohesion: 0.19
Nodes (8): asyncio, list_tools() caches the result for ttlMs milliseconds., Second call within TTL must not issue an RPC., After the TTL elapses the next call issues a fresh RPC., invalidate_tools_cache() forces a fresh RPC on the next call., When the server omits ttlMs the default TTL is applied., ttlMs: 0 from the server is treated as absent (use default TTL)., TestMCPToolsListCache

### Community 687 - "test_openclaw_gateway.py"
Cohesion: 0.14
Nodes (4): tests/test_openclaw_gateway.py — OpenClaw in-process WebSocket gateway tests., Dockerfile.backend does NOT install @openclaw/cli (in-process gateway now)., render_yaml(), test_dockerfile_backend_no_openclaw_cli()

### Community 688 - "TestDisabledReasonRendering"
Cohesion: 0.14
Nodes (5): ``describe_disabled_reason`` is rendered next to the on/off switch. The stored…, Anthropic sends 400 for an empty balance, not 402., A reason the operator cannot read still beats no reason at all., Guards the seam: the writer and this renderer must not drift apart. Scans the…, TestDisabledReasonRendering

### Community 689 - "AGENTS.md — Codebase Map & Operations Reference"
Cohesion: 0.15
Nodes (13): Agent roles, AGENTS.md — Codebase Map & Operations Reference, Architecture, Claude Code subagents (cost-aware routing), Codebase map, Deployment, File-size exceptions, Further reading (+5 more)

### Community 690 - "CollaborationContext"
Cohesion: 0.21
Nodes (3): CollaborationContext, Shared context blob propagated to all session participants. Carries the active…, TestCollaborationContext

### Community 691 - "EdgeType"
Cohesion: 0.18
Nodes (8): EdgeType, Enum, Obsidian Knowledge Graph — KnowledgeNode and KnowledgeGraph with typed edges.…, Import edges from (source, target, edge_type) tuples., Types of relationships between knowledge nodes., Add a directed edge between two nodes., Get outgoing edges from a node as (target_id, edge_type) pairs., Get incoming edges to a node as (source_id, edge_type) pairs.

### Community 692 - "Process"
Cohesion: 0.15
Nodes (12): Output Format, Process, Purpose, Rules, Skill: auto-fix, Step 1: Discover Fix Commands, Step 2: Run Fixers (Auto-fixable), Step 3: Run Checkers (Non-auto-fixable) (+4 more)

### Community 693 - "Skill: Brain Dump"
Cohesion: 0.15
Nodes (12): Example Prompt to Trigger, Instructions, Notes, Output Format, Purpose, Skill: Brain Dump, Step 1: Capture Everything, Step 2: Categorize (+4 more)

### Community 694 - "Process"
Cohesion: 0.15
Nodes (12): Process, Purpose, Rules, Skill: context-prime, Step 1: Read Core Docs, Step 2: Map the Architecture, Step 3: Find Conventions, Step 4: Understand Data Flow (+4 more)

### Community 695 - "Instructions"
Cohesion: 0.15
Nodes (12): Acceptance Checks, Instructions, Role 1: Security Reviewer, Role 2: Correctness Reviewer, Role 3: Performance Reviewer, Role 4: Maintainability Reviewer, Skill: council-review, Step 1 — Gather the diff (+4 more)

### Community 696 - "Skill: duplicate-thread"
Cohesion: 0.15
Nodes (12): Files, How It Works, In a Claude prompt, Integration, Manual duplication, Merging Back, meta.json Schema, Purpose (+4 more)

### Community 697 - "Skill: Email Triage"
Cohesion: 0.15
Nodes (12): Example Prompt to Trigger, Instructions, Notes, Output Format, Purpose, Skill: Email Triage, Step 1: Intake, Step 2: Triage Categories (+4 more)

### Community 698 - "Process"
Cohesion: 0.15
Nodes (12): Anti-Patterns, Process, Purpose, Rules, Skill: feature-flag, Step 1: Assess Flag Need, Step 2: Define the Flag, Step 3: Implement the Guard (+4 more)

### Community 699 - "Process"
Cohesion: 0.15
Nodes (12): 1. Review Staged and Unstaged Changes, 2. Review Commit History, 3. Validate Commit Messages, 4. Clean Up if Needed, 5. Confirm Branch State, 6. Push, Notes, Output (+4 more)

### Community 700 - "Skill: graphify — Knowledge Graph Token Optimization"
Cohesion: 0.15
Nodes (12): Acceptance Checks, Claude's query protocol (use this instead of Read tool for exploration):, Graph Artifacts — What to Commit, How to Use the Graph (Token Savings Protocol), Installation (one-time per machine), Instead of reading raw files:, Key commands:, Relationship to repowise-intelligence Skill (+4 more)

### Community 701 - "Skill: prompt-library"
Cohesion: 0.15
Nodes (12): 1. Sync Snapshots, 2. Generate Library Index, 3. Generate TRANSPARENCY.md, 4. Update CHANGELOG.md in prompts/, 5. Commit, Directory Structure Created, Output, Purpose (+4 more)

### Community 702 - "Skill: prompt-transparency"
Cohesion: 0.15
Nodes (12): 1. Collect All Agent & Skill Definitions, 2. Extract Key Behavioral Dimensions, 3. Generate Transparency Report, 4. Flag Risks, 5. Commit the Report, Example Usage, Inspiration, Output Format (+4 more)

### Community 703 - "Skill: Research"
Cohesion: 0.15
Nodes (12): Example Prompt to Trigger, Instructions, Notes, Output Format, Purpose, Skill: Research, Step 1: Define the Research Question, Step 2: Identify Source Categories (+4 more)

### Community 704 - "Skill: scope-guard"
Cohesion: 0.15
Nodes (12): Anti-Patterns to Avoid, Output Format, Process, Purpose, Rules, Skill: scope-guard, Step 1: Define the Scope Contract, Step 2: Pre-Implementation Check (+4 more)

### Community 705 - "admin_update_task_router.py"
Cohesion: 0.22
Nodes (12): _expected_admin_secret(), _extract_admin_token(), BaseModel, backend/admin_update_task_router.py Step 1: POST…, Mount the update-task endpoint on ``app``. Idempotent: skips if a path with the…, Body for ``POST /api/workflow/orchestrator/update-task/{run_id}``.…, Resolve the admin secret from env. Order matches admin_digest_router.py:…, Inject ``additional_instructions`` into a paused or running WorkflowRun.… (+4 more)

### Community 706 - "Instructions"
Cohesion: 0.15
Nodes (12): Acceptance Checks, Instructions, Role 1: Security Reviewer, Role 2: Correctness Reviewer, Role 3: Performance Reviewer, Role 4: Maintainability Reviewer, Skill: council-review, Step 1 — Gather the diff (+4 more)

### Community 707 - "Skill: graphify — Knowledge Graph Token Optimization"
Cohesion: 0.15
Nodes (12): Acceptance Checks, Claude's query protocol (use this instead of Read tool for exploration):, Graph Artifacts — What to Commit, How to Use the Graph (Token Savings Protocol), Installation (one-time per machine), Instead of reading raw files:, Key commands:, Relationship to repowise-intelligence Skill (+4 more)

### Community 708 - "Skill: platform-setup — Autonomous Agency Bootstrap"
Cohesion: 0.15
Nodes (12): Ongoing autonomous operation, Phase 1 — Verify deployment health (no auth needed), Phase 2 — Login as admin, Phase 3 — Onboard the platform itself as a company, Phase 4 — Verify specialists were provisioned, Phase 5 — Configure GitHub integration, Phase 6 — Trigger first agency cycle manually, Phase 7 — Verify autonomous schedule is active (+4 more)

### Community 709 - "Device compatibility and model picks"
Cohesion: 0.15
Nodes (12): Acceleration at a glance, Apple Silicon: chip tier vs bandwidth (qualitative), Desktops and workstations, Device compatibility and model picks, Edge cases, How to read memory on different platforms, Laptops and all-in-ones, NVIDIA examples by VRAM (CUDA) (+4 more)

### Community 710 - "Autonomy Uplift — Living Roadmap & Detailed Implementation Specs"
Cohesion: 0.15
Nodes (12): 0. The goal (operator's words), 1. Shipped ✅, 2. In flight 🟡, 3. Pending ⬜ — detailed implementation specs, 3a. Apply the slop-gate to the sibling auto-PR scripts ✅  (size: S), 3b. Hermes — **our own** Hermes server (in-repo), UI-wired ✅  (size: M), 3c. CRISPY — harden, then re-enable ✅  (size: L, risky-module-review), 3d. Phase 3 — auto-PR *quality* beyond the slop-gate ✅  (size: M) (+4 more)

### Community 711 - "OpenClaw — iOS Control of the Agency (Single-Service Free-Tier Deploy)"
Cohesion: 0.15
Nodes (12): 1. Set env vars on the existing `local-llm-server` service, 2. Deploy, 3. Check the status, 4. Get the pairing QR, 5. Pair and verify, Alternative: Telegram bot, Architecture (single-service), Free-tier caveats (+4 more)

### Community 712 - "rules"
Cohesion: 0.15
Nodes (12): rules, import/no-anonymous-default-export, jsx-a11y/anchor-is-valid, jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions, jsx-a11y/no-static-element-interactions, no-console, no-template-curly-in-string (+4 more)

### Community 713 - "ApplyReviewAgent"
Cohesion: 0.22
Nodes (6): ApplyReviewAgent, _openai_tools_to_anthropic(), Convert OpenAI function-calling tool schemas to Anthropic tool schemas., Return (result_text, should_stop)., Run using NVIDIA NIM (OpenAI-compatible). Called as fallback., Run using Claude Opus via Anthropic SDK (primary path).

### Community 714 - "ChatResponse"
Cohesion: 0.18
Nodes (4): CerebrasProvider, Cerebras provider adapter — free, fast LLM (qwen-3-coder-480b)., ChatResponse, Standard response from a provider chat call.

### Community 715 - "HealthStatus"
Cohesion: 0.18
Nodes (5): GroqProvider, Groq provider adapter — free, fast LLM (deepseek-r1-distill-llama-70b)., HealthStatus, Provider health check result., Check provider health.

### Community 716 - "_Budget"
Cohesion: 0.15
Nodes (5): _Budget, Shared attempt + wall-clock budget for one logical completion. Bounds the whole…, True when free/local providers have used everything but the reserve. Only the…, disabled(), Record auto-disable calls instead of writing operator state.

### Community 717 - "._order_group"
Cohesion: 0.22
Nodes (8): Unique identifier (e.g. 'nvidia', 'cerebras')., provider_id_of(), Any, Extract a provider id from a ProviderConfig dataclass or a plain dict., Return *providers* reordered according to the active strategy. ``group_key``…, Reorder one interchangeable group of providers., Ascending sort by *score* with a random tie-break. The tie-break is the point:…, Weighted random permutation — heavier providers tend to come first. Weight…

### Community 718 - "_is_bedrock_model_id"
Cohesion: 0.27
Nodes (3): _is_bedrock_model_id(), Return True if model_id is an AWS Bedrock model or inference profile ID., TestIsBedrockModelId

### Community 719 - "Summary"
Cohesion: 0.15
Nodes (12): Checklist, Rollout notes, Summary, Test plan, UNIT 1 — Fix duplicate ceo_direct tasks ✅, UNIT 2 — Portfolio → task materializer (default ON) ✅, UNIT 3 — Config hygiene (zero behavior change) ✅, UNIT 4 — Commit model catalog `config/models.yaml` ✅ (+4 more)

### Community 720 - "Agent Transparency Report"
Cohesion: 0.15
Nodes (12): Agent Transparency Report, Guardrails and Limits, How to Verify This, Human Oversight Points, 🔨 Implementer, ⚖️ Judge, 📋 Planner, 🔍 Reviewer (+4 more)

### Community 721 - "update_provider_policy"
Cohesion: 0.19
Nodes (12): _get_provider_policy(), ProviderPolicyUpdate, BaseModel, get, put, Read the durable provider policy, falling back to a safe default. Returns a…, Persist the provider policy and return the new state., Return the durable provider policy (single source of truth for paid-provider… (+4 more)

### Community 722 - ".publish"
Cohesion: 0.17
Nodes (7): Any, Task, Broadcast an event to all matching subscribers. Returns the number of callbacks…, Fire-and-forget publish. Creates a background task. Returns the asyncio.Task so…, Return recent events for a topic., Return bus statistics., Check if a topic matches a pattern with * and ** wildcards.

### Community 723 - "_InMemoryBackend"
Cohesion: 0.18
Nodes (4): _InMemoryBackend, Single-process backend using asyncio.Lock + dicts with TTL timestamps., Clear all cooldown entries (for test teardown)., Clear all probe-lock entries (for test teardown). ``cooldown_clear`` only…

### Community 724 - ".on_task_complete"
Cohesion: 0.18
Nodes (6): Any, Callback for BackgroundAgent.on_task_complete. Dispatches task result…, Send notification to configured Telegram chat IDs., Dispatch the daily review digest to every authorized chat_id. Mirrors…, POST task result to configured webhook URL. Both ``error`` and ``result`` are…, Send an ad-hoc notification through all channels.

### Community 725 - "_provider"
Cohesion: 0.23
Nodes (5): _provider(), SimpleNamespace, Listing is not proof. A retired id can still appear in a catalogue., TestAFailedProbeIsNotASuccess, TestAuthFollowsTheProviderDeclaration

### Community 726 - "TestModelCostTableUpdates"
Cohesion: 0.26
Nodes (3): New models are present in the cost table with sensible prices., get_cost_table() API exposes the new models with correct structure., TestModelCostTableUpdates

### Community 727 - "TestMCPClientStructuredOutput"
Cohesion: 0.31
Nodes (5): asyncio, Tests for MCPClient.call_tool_structured() using an async mock., call_tool() (legacy) is unchanged., list_tools() already returns raw tool dicts; outputSchema is preserved., TestMCPClientStructuredOutput

### Community 728 - "test_deploy_trigger_covers_image.py"
Cohesion: 0.21
Nodes (12): _image_copy_sources(), Regression guard: the Render deploy trigger must cover everything the image…, `packages/` holds the AI layer — the most deploy-sensitive code there is., The health step must be able to fail. It previously polled for any 200 starting…, Top-level paths ``Dockerfile.backend`` copies into the runtime image., Top-level path prefixes in the deploy workflow's push ``paths:`` filter., The filter must take root modules wholesale, matching `COPY *.py ./`. Listing…, test_deploy_verification_cannot_pass_silently_on_failure() (+4 more)

### Community 729 - "TestKillSwitchDurability"
Cohesion: 0.15
Nodes (4): The local mirror is what keeps operator intent during a Mongo outage., A restart clears every in-memory cache; the state must still be there., Never claim a switch took effect when no store accepted it. Mongo off…, TestKillSwitchDurability

### Community 730 - "test_quick_note_engine.py"
Cohesion: 0.17
Nodes (11): _before(), Guard that the quick-note engine agents use NVIDIA NIM as the primary engine…, implement_agent.py must not spend paid credits behind the operator. This used…, Rule 2: all LLM calls go through packages/ai/router.py. A private model list in…, Nemotron first — asserted against behaviour, not file contents. This used to…, Regression: _run_baseline_pytest() ran the FULL suite (no path filter,…, test_baseline_pytest_timeout_is_generous_and_failure_is_caught(), test_implement_agent_never_escalates_to_paid() (+3 more)

### Community 731 - "test_task_clarification.py"
Cohesion: 0.15
Nodes (5): auth_headers(), Tests for needs_clarification status and /api/tasks/{id}/clarify endpoint., Get auth headers for an admin user., task_id(), test_needs_clarification_in_enum()

### Community 732 - "validate_job_id"
Cohesion: 0.19
Nodes (5): TestJobIdValidation, parametrize, TestPathTraversalPrevention, Validate and return a job ID, or raise InvalidJobIdError., validate_job_id()

### Community 733 - "skill_registry.py"
Cohesion: 0.17
Nodes (6): agent/skill_registry.py — Dynamic Skill Registry & Recommender Fetches skill…, Holds a pre-compiled regex + the original tech name., set_skill_registry(), _TechPattern, Tests for module-level pre-compiled pattern constants., TestPreCompiledPatterns

### Community 734 - "Trajectory"
Cohesion: 0.20
Nodes (7): Path, Persist trajectory as JSON and return the file path., Reload a previously saved trajectory (read-only replay)., Return a summary dict suitable for logging / leaderboards., Complete record of one agent run against one task. Compatible with the…, Mark the trajectory as complete., Trajectory

### Community 735 - "Instructions"
Cohesion: 0.17
Nodes (11): Acceptance Checks, Idempotency Rules, Instructions, Skill: cooldown-resume, Step 1 — Read the checkpoint files, Step 2 — Assess the state, Step 3 — Verify changed files are correct, Step 4 — Run tests to confirm baseline (+3 more)

### Community 736 - "Instructions"
Cohesion: 0.17
Nodes (11): Acceptance Checks, Current Dependencies (quick reference), Instructions, Skill: dependency-audit, Step 1 — Evaluate the new dependency, Step 2 — Pin appropriately, Step 3 — Install and verify, Step 4 — Check for conflicts (+3 more)

### Community 737 - "Process"
Cohesion: 0.17
Nodes (11): 1. Audit Existing Skills, 2. Identify Gaps, 3. Propose Improvements, 4. Implement, 5. Validate, Notes, Output, Process (+3 more)

### Community 738 - "Instructions"
Cohesion: 0.17
Nodes (11): Acceptance Checks, Instructions, Skill: smart-commit, Step 1 — Confirm changelog is updated, Step 2 — Run tests, Step 3 — Check for obvious issues, Step 4 — Stage your changes, Step 5 — Write a conventional commit message (+3 more)

### Community 739 - "Skill: system-prompt-audit"
Cohesion: 0.17
Nodes (11): 1. Inventory Collection, 2. Consistency Check, 3. Safety Check, 4. Generate Audit Report, 5. Exit Codes, Integration, Purpose, Related Skills (+3 more)

### Community 740 - "Skill: task-alive-updates"
Cohesion: 0.17
Nodes (11): Example Output, Files, How It Works, Implementation Rules, In a shell script / agent harness, In Claude task descriptions, Integration with parallel-agents, Purpose (+3 more)

### Community 741 - "Process"
Cohesion: 0.17
Nodes (11): 1. Read the Task Carefully, 2. Define the Boundary, 3. Identify Temptations, 4. Lock the Scope, 5. Out-of-Scope Findings, Notes, Output, Process (+3 more)

### Community 742 - "Instructions"
Cohesion: 0.17
Nodes (11): Acceptance Checks, Instructions, Skill: test-first-executor, Step 1 — Identify what needs testing, Step 2 — Write the test first, Step 3 — Confirm the test FAILS before implementation, Step 4 — Implement until the test passes, Step 5 — Run the full suite (+3 more)

### Community 743 - "Skill: agent-browser — Real Chrome Browser Automation"
Cohesion: 0.17
Nodes (11): Applying to the local-llm-server Platform, Core Commands, How to Use This Skill, Installation (one-time), Skill: agent-browser — Real Chrome Browser Automation, Step 1 — Check Chrome is running with debugging, Step 2 — Navigate and snapshot, Step 3 — Interact using element refs (+3 more)

### Community 744 - "Instructions"
Cohesion: 0.17
Nodes (11): Acceptance Checks, Idempotency Rules, Instructions, Skill: cooldown-resume, Step 1 — Read the checkpoint files, Step 2 — Assess the state, Step 3 — Verify changed files are correct, Step 4 — Run tests to confirm baseline (+3 more)

### Community 745 - "Instructions"
Cohesion: 0.17
Nodes (11): Acceptance Checks, Current Dependencies (quick reference), Instructions, Skill: dependency-audit, Step 1 — Evaluate the new dependency, Step 2 — Pin appropriately, Step 3 — Install and verify, Step 4 — Check for conflicts (+3 more)

### Community 746 - "Skill: dev-browser — Browser Automation via Sandboxed JS"
Cohesion: 0.17
Nodes (11): Browser API, CLI flags, Connect to existing Chrome, Full script example (Playwright Page API), Installation, LLM usage patterns, Performance, Primary invocation styles (+3 more)

### Community 747 - "Instructions"
Cohesion: 0.17
Nodes (11): Acceptance Checks, Instructions, Skill: test-first-executor, Step 1 — Identify what needs testing, Step 2 — Write the test first, Step 3 — Confirm the test FAILS before implementation, Step 4 — Implement until the test passes, Step 5 — Run the full suite (+3 more)

### Community 748 - "Agent Orchestration Design"
Cohesion: 0.17
Nodes (12): Agent Orchestration Design, Execution Pathway, Four-Agent Structure, Key Invariants, OSS Inspirations (Clean-Room), Overview, Plan-First Pathway, Release-Readiness Pathway (+4 more)

### Community 749 - "Universality: case-coverage matrix"
Cohesion: 0.17
Nodes (12): A. Connection & credentials, B. Provider & host, C. Delivery / branch policy  *(detected — see DeliveryPolicy)*, D. CI / checks, E. Review automation & humans, F. Repo state & conflicts, G. Task origin, H. Governance / safety / HITL (+4 more)

### Community 750 - "Quantization Internals"
Cohesion: 0.17
Nodes (12): Absmax Quantization (Symmetric), Activation Quantization, AWQ (Activation-Aware Weight Quantization), Bits and Bytes (bitsandbytes), Data Types, GGUF / llama.cpp Quantization, GPTQ (Post-Training Quantization for GPT), Post-Training Quantization (PTQ) (+4 more)

### Community 751 - "Implementation — DB-persisted, UI-switchable Brain (PR #824 follow-up)"
Cohesion: 0.17
Nodes (11): Architecture (per plan §3), Files touched, Hard constraints (from the plan) — all met, Implementation — DB-persisted, UI-switchable Brain (PR #824 follow-up), Modified files, New files, Resolution precedence, Risks & mitigations (per plan §6) (+3 more)

### Community 752 - "2. Pending ⬜ — detailed implementation specs"
Cohesion: 0.17
Nodes (11): 0. The goal (unchanged), 1. Shipped in the previous pass ✅ (recap, do not redo), 2. Pending ⬜ — detailed implementation specs, 3. Deferred 🔭, 4. Operating notes (unchanged, for implementers), N1. Activate the reliability spine — wire the watchdog, schedule the digest ⬜  (size: M, risk: low), N2. Surface Hermes (and all runtimes) status in the Doctor/Runtimes UI ⬜  (size: S, risk: low), N3. Real CI-failure autofix — close the "Agency: cannot fix tests" loop (issue #398) ✅  (size: L, risk: medium) (+3 more)

### Community 753 - "467 Public Site Truth Spec"
Cohesion: 0.17
Nodes (11): 467 Public Site Truth Spec, Architecture Page Truth, Content Rules, Current State, Feature Matrix Truth, Required: Public Site Truth Spec, Site Structure, Tier System for Features (+3 more)

### Community 754 - "GovernanceScreen.jsx"
Cohesion: 0.18
Nodes (6): OBSERVE_STATUS, AuditTable(), BACKEND_META, DECISION_COLOR, relTime(), GovernanceScreen

### Community 755 - "extract_refusal"
Cohesion: 0.27
Nodes (4): extract_refusal(), Extract the ``refusal`` string from an OpenAI-format response body. Returns the…, extract_refusal() surfaces model refusals from provider response bodies., TestExtractRefusal

### Community 756 - "install-agents.sh"
Cohesion: 0.39
Nodes (11): classify_current_or_legacy(), fail(), install_missing(), path_exists(), replace_legacy_role(), report_preflight_error(), role_selected(), same_state() (+3 more)

### Community 757 - "TestModelsEndpointAliases"
Cohesion: 0.26
Nodes (5): _get_model_map(), Merge built-in defaults with MODEL_MAP env overrides (lazy, cached)., Daily automation tests — 2026-05-14 Covers three features implemented in this…, Tests that /v1/models exposes Claude/Anthropic alias entries., TestModelsEndpointAliases

### Community 758 - "check_container_posture.py"
Cohesion: 0.26
Nodes (11): check_compose(), check_policy_baseline(), check_sandbox_profiles(), _load_yaml(), main(), Any, Path, scripts/check_container_posture.py — assert the container security posture. CI… (+3 more)

### Community 759 - "test_pytest_failure_parser.py"
Cohesion: 0.23
Nodes (8): is_node_id(), Return True if *candidate* has the shape of a pytest node ID. A node ID is…, parametrize, Regression tests for ``scripts/parse_pytest_failures.py``. Guards the two…, The naive greps must not come back — that is the whole bug., The shape check that separates real node IDs from log locators., TestIsNodeId, TestWorkflowsUseTheParser

### Community 760 - "Kimi Web-Bridge Service"
Cohesion: 0.17
Nodes (11): API, Connecting to the Main Backend, Docker, Environment Variables, `GET /health`, `GET /v1/models`, How It Works, Kimi Web-Bridge Service (+3 more)

### Community 761 - "setup_ngrok.py"
Cohesion: 0.27
Nodes (11): _api(), authenticate_ngrok(), _find_ngrok(), get_or_create_static_domain(), main(), setup_ngrok.py — One-time ngrok static domain setup. Usage: python…, Return path to the ngrok binary (pyngrok location or PATH)., Update or append KEY=value in .env. (+3 more)

### Community 762 - "._coerce_ts"
Cohesion: 0.26
Nodes (5): _coerce_ts(), Any, field_validator, Coerce ISO-8601 datetime strings (from DB) to float timestamps., Dict-compatible accessor. Log entries are serialized to/from dicts in many…

### Community 763 - "test_admin_local_brain_router.py"
Cohesion: 0.29
Nodes (11): _make_app(), FastAPI, tests/test_admin_local_brain_router.py — auth + toggle flow for…, Build a minimal FastAPI app wrapping the admin router with a fake auth dep.…, test_get_state_admin_returns_documented_shape(), test_get_state_non_admin_returns_403(), test_get_state_unauthenticated_returns_401(), test_post_toggle_invalid_state_returns_422() (+3 more)

### Community 764 - "test_agile_api.py"
Cohesion: 0.17
Nodes (3): auth_headers(), Tests for /api/agile/* endpoints., Get auth headers for the seeded admin user (matched to seed_admin email).

### Community 765 - "test_app_settings.py"
Cohesion: 0.21
Nodes (10): asyncio, Tests for app_settings — DB-persisted settings + onboarding-gate default. These…, Point db.get_store() at an isolated temp SQLite DB. Patches…, is_user_onboarding_allowed falls back to the global default for users with no…, sqlite_store(), test_defaults_when_unset(), test_gate_default_controls_unlisted_user(), test_refresh_cache_warms_sync_readers() (+2 more)

### Community 766 - "test_brain_default_consistency.py"
Cohesion: 0.24
Nodes (11): _catalogue_default(), One brain default, consistent across every surface that names one. This file…, Guards every assertion below from passing vacuously on an empty string., ``packages/ai/brain.py`` is a separate copy of "the free NVIDIA model"., A default that is not the first candidate wastes the first attempt., Production env values override every default in the code. ``render.yaml``…, test_brain_default_matches_the_catalogue(), test_every_nvidia_role_preset_matches_the_catalogue() (+3 more)

### Community 767 - "TestAnthropicWorkspaceIdCapture"
Cohesion: 0.33
Nodes (5): asyncio, Verify the workspace-id header is captured from Anthropic API responses., _parse must work without passing workspace_id (backwards compat)., chat() must read anthrophic-workspace-id from the response headers., TestAnthropicWorkspaceIdCapture

### Community 768 - "_FakeFiles"
Cohesion: 0.17
Nodes (6): fake_sandbox(), _FakeAsyncSandboxClass, _FakeFiles, _FakeSandbox, Any, In-memory FS that resolves paths against SANDBOX_WORKDIR.

### Community 769 - "test_providers_live_e2e.py"
Cohesion: 0.27
Nodes (11): _auth_headers(), _login_via_email(), Any, tests/test_providers_live_e2e.py — Live integration test for…, The /api/providers list now annotates each record with is_brain/role. The role-…, Skip the current test with a structured reason (pytest.skip is fine too)., POST /api/auth/login and return the parsed JSON body. Raises on failure., Full JWT round-trip: login → PUT → GET → cleanup. Asserts that the providers… (+3 more)

### Community 770 - "BenchmarkReport"
Cohesion: 0.20
Nodes (3): BenchmarkReport, Run multiple tasks and aggregate into a BenchmarkReport. Set concurrency > 1 to…, Aggregated results for a full benchmark suite run.

### Community 771 - "MCPToolResult"
Cohesion: 0.27
Nodes (5): MCPToolResult, Result from ``call_tool_structured()``. ``structured`` is populated when the…, Prefer structured data; fall back to text when unavailable., Unit tests for agent.mcp_client.MCPToolResult., TestMCPToolResult

### Community 772 - "_keyword_search"
Cohesion: 0.20
Nodes (10): Document, _keyword_search(), Score documents by query-term coverage with a title-match boost., A single knowledge-base entry (wiki page, source document, etc.)., _doc(), test_keyword_search_empty_query(), test_keyword_search_finds_relevant(), test_keyword_search_no_match() (+2 more)

### Community 773 - "_extractive_compress"
Cohesion: 0.18
Nodes (11): _extractive_compress(), Split text into sentences on . ! ? followed by whitespace or end-of-string., Return the highest-value sentences from *text* within *max_tokens*. Each…, _split_sentences(), test_compress_empty_text(), test_compress_prefers_query_relevant_sentences(), test_compress_result_non_empty_for_non_empty_input(), test_compress_short_text_verbatim() (+3 more)

### Community 774 - "Instructions"
Cohesion: 0.18
Nodes (10): Acceptance Checks, Failure / Retry Behaviour, Instructions, Skill: implementation-planner, Step 1 — Understand the current state, Step 2 — Write the plan, Step 3 — Get implicit approval before coding, Step 4 — Implement (+2 more)

### Community 775 - "Skill: pro-workflow"
Cohesion: 0.18
Nodes (10): Acceptance Checks, Instructions, Model Selection Guide, Phase 1 — Research (Scout), Phase 2 — Plan, Phase 3 — Implement, Phase 4 — Wrap Up, Skill: pro-workflow (+2 more)

### Community 776 - "Instructions"
Cohesion: 0.18
Nodes (10): Acceptance Checks, Instructions, Learnings File Doesn't Exist?, Skill: replay-learnings, Step 1 — Read the learnings file, Step 2 — Filter relevant learnings, Step 3 — Check recent checkpoint history, Step 4 — Surface blockers from previous session (+2 more)

### Community 777 - "Instructions"
Cohesion: 0.18
Nodes (10): Acceptance Checks, Instructions, Skill: repo-memory-updater, Step 1 — Inventory what changed, Step 2 — Check root AGENTS.md, Step 3 — Check module AGENTS.md files, Step 4 — Update .Codex/state/, Step 5 — Commit the update (+2 more)

### Community 778 - "Skill: resource-panel"
Cohesion: 0.18
Nodes (10): Ask Claude to emit a resource panel, Automated via shell (git-based), Fields, Files, How to Use, Integration, Output Format, Purpose (+2 more)

### Community 779 - "Skill: sandboxed-exec"
Cohesion: 0.18
Nodes (10): Example — run tests in isolation, Example — validate a generated script before saving, How It Works, Output Format, Purpose, Security Notes, Skill: sandboxed-exec, Steps (for Claude to follow) (+2 more)

### Community 780 - "Workflow"
Cohesion: 0.18
Nodes (10): Acceptance checks, Fill these in, Skill: client-onboarding, Step 1 — Create the company and kick off onboarding, Step 2 — Poll progress, Step 3 — Verify specialists were provisioned, Step 4 — Confirm the 24x7 agency runtime is live, Step 5 — Note real gaps instead of pretending they're solved (+2 more)

### Community 781 - "ECC Harness Patterns Skill"
Cohesion: 0.18
Nodes (10): 1. Harness Detection & Adaptation, 2. Session Lifecycle Hooks, 3. Cross-Harness Model Selection, 4. Persistent Harness Registry, ECC Harness Patterns Skill, Files to Create/Modify, Implementation Plan, Patterns to Adopt (+2 more)

### Community 782 - "Instructions"
Cohesion: 0.18
Nodes (10): Acceptance Checks, Failure / Retry Behaviour, Instructions, Skill: implementation-planner, Step 1 — Understand the current state, Step 2 — Write the plan, Step 3 — Get implicit approval before coding, Step 4 — Implement (+2 more)

### Community 783 - "Instructions"
Cohesion: 0.18
Nodes (10): Acceptance Checks, Instructions, Skill: repo-memory-updater, Step 1 — Inventory what changed, Step 2 — Check root CLAUDE.md, Step 3 — Check module CLAUDE.md files, Step 4 — Update .claude/state/, Step 5 — Commit the update (+2 more)

### Community 784 - "Stop-Slop Quality Skill"
Cohesion: 0.18
Nodes (10): AI Tells Detected, Business Jargon, Emphasis Crutches (Banned Adverbs), Implementation, Integration Points, Meta-Commentary, References, Stop-Slop Quality Skill (+2 more)

### Community 785 - "Agency Core — Ruthless Architecture Audit & Migration Plan"
Cohesion: 0.18
Nodes (10): Acceptance check, Agency Core — Ruthless Architecture Audit & Migration Plan, Root causes (not symptoms), Section 1 — The Brutal Truth, Section 2 — Keep / Salvage / Replace / Remove, Section 3 — The Chosen Foundation, Section 4 — The New Agency Core, Section 5 — Migration Plan (minimal chaos, all on PR, CI green at each step) (+2 more)

### Community 786 - "AUTONOMY_CHARTER.md"
Cohesion: 0.18
Nodes (6): How to add or change a loop, LOOP.md — The loops that run this agency, Maturity ladder, The five building blocks (and how this repo realises them), The three operator tools (`agent/loop_registry.py`), Why this exists

### Community 787 - "Tailored Onboarding, Editable Companies & Dynamic Roles"
Cohesion: 0.18
Nodes (10): 1. Editable companies, anytime (not a one-shot wizard), 2. Question-driven provisioning — no cosmetic questions, 3. Dynamic, expandable roles (open registry, not a closed enum), 4. Agents start pre-powered, Invariants, Phases, Tailored Onboarding, Editable Companies & Dynamic Roles, The gaps to close (+2 more)

### Community 788 - "Issue #467 — Section 1: Pulled State + PR Inventory"
Cohesion: 0.18
Nodes (10): 1. Current Git State, 2. Open PRs (as of 2026-06-08), 3. Files Modified on consolidate/maturation-stable (vs master), 4. What Master Has (that consolidate doesn't), 5. What Is MISSING from master (0% delivered in #467), 6. Required Action Before Code, Branch: `consolidate/maturation-stable`, Issue #467 — Section 1: Pulled State + PR Inventory (+2 more)

### Community 789 - "Autonomy Charter — Telegram-Gated Self-Running Agency"
Cohesion: 0.18
Nodes (11): 1. Mission & operating principles, 2. Brain policy (free cloud LLMs), 3. The Gate Matrix (core artifact), 4. Telegram gate protocol, 6. Integration gaps to wire (follow-up implementation), 7. Definition of "fully autonomous" — acceptance criteria, 8. Safety invariants (carried from `agent/CLAUDE.md`), 🟢 Autonomous — run, then notify-only (+3 more)

### Community 790 - "Context: Agentic Agile + Portfolio Management"
Cohesion: 0.18
Nodes (10): Agile improvements shipped alongside, Autonomous intelligence (`agents/portfolio_intelligence.py`), Capacity & roadmap, Context: Agentic Agile + Portfolio Management, Extension ideas (not yet built), Prioritisation model — WSJF (SAFe), Problem, The two layers (+2 more)

### Community 791 - "Deploy to Google Cloud Run"
Cohesion: 0.18
Nodes (10): 1) Admin protection (required), 2) User API keys (required), 3) LLM provider (recommended), Build + deploy (Dockerfile), Deploy to Google Cloud Run, Notes / limitations on Cloud Run, Prereqs, Required configuration (+2 more)

### Community 792 - "Key Components"
Cohesion: 0.18
Nodes (10): 1. Input Embedding, 2. Multi-Head Self-Attention, 3. Residual Connections, 4. Feed-Forward Network (FFN), 5. Layer Normalization, Decoder-Only vs Encoder-Decoder, High-Level Structure, Key Components (+2 more)

### Community 793 - "Sampling Strategies Internals"
Cohesion: 0.18
Nodes (11): Beam Search, Greedy Decoding, Logit Processors (Structured Output), Min-p Sampling, Repetition Penalty, Sampling Strategies Internals, Temperature Sampling, The Output Distribution (+3 more)

### Community 794 - "LLM Router — architecture"
Cohesion: 0.18
Nodes (11): Bulkheads, Circuit breaker, Compatibility, Configuration, Context management, LLM Router — architecture, Modules, Request lifecycle (+3 more)

### Community 795 - "Killer TODO Roadmap — local-llm-server"
Cohesion: 0.18
Nodes (10): G1 — Per-Model Cost and Latency Attribution [P1] [NVD], G2 — Request Replay for Debugging [P2] [CBF], H1 — Vision Input Support for Multimodal Models [P2] [NVD], H2 — Audio Input / Whisper Transcription [P3] [NVD], Implementation Notes, Killer TODO Roadmap — local-llm-server, Priority Summary, SECTION G — Observability (NVD / CHM) (+2 more)

### Community 796 - "NVIDIA NIM — Free Tier Setup"
Cohesion: 0.18
Nodes (10): 1. Get your free API key, 2. Set the environment variable, 3. Restart the server, 4. Verify, How the kill switch protects you, NVIDIA NIM — Free Tier Setup, Related, Setup (5 minutes) (+2 more)

### Community 797 - "What to clean up"
Cohesion: 0.18
Nodes (10): 1. Render (production backend + worker), 2. Cloudflare Worker (frontend), 3. Local development machines, 4. GitHub secrets, 5. MongoDB collections, Post-Merge Environment Cleanup Guide, Post-merge verification checklist, Rollback (+2 more)

### Community 798 - "Worker Service — Operations Runbook"
Cohesion: 0.18
Nodes (10): Architecture, Deployment on Render, Environment variables, First-time setup, Graceful shutdown, Local development, Overview, Troubleshooting (+2 more)

### Community 799 - "LoopsScreen.jsx"
Cohesion: 0.22
Nodes (9): getLoops(), COST_COLOR, fmtTokens(), GATE_META, GRADE_COLOR, LEVEL_META, LoopsScreen(), ReadinessHeader() (+1 more)

### Community 800 - "test_bedrock_live.py"
Cohesion: 0.25
Nodes (10): _NEEDS_CREDS, asyncio, ProviderRouter discovers Bedrock from env and completes a real chat call., Health check returns True when real credentials are loaded from env., Call Bedrock Converse API directly with boto3 — no proxy layer., Verify the configured model ID accepts a converse request without auth errors., test_bedrock_direct_boto3_ping(), test_bedrock_health_check_with_real_creds() (+2 more)

### Community 801 - "ProviderManager"
Cohesion: 0.18
Nodes (6): ProviderManager, Any, Coordinates provider selection, failover, and health., Return providers sorted by priority (lowest = highest priority)., Send a chat request with automatic failover. Retry policy: 1. If ``model`` is…, Check health of all configured providers.

### Community 802 - "._prune"
Cohesion: 0.22
Nodes (6): _ProviderUsage, Sliding-window usage counters for one provider., Drop request/token events that have fallen out of the window., Count a request that is about to be sent to *provider_id*. Called immediately…, Record the outcome of a request started with ``record_start``. Must be called…, Count a request that was routed away from *provider_id* (diagnostics).

### Community 803 - "mask_secret"
Cohesion: 0.25
Nodes (5): mask_dict(), mask_secret(), Redact secret-looking substrings from a string. Always safe to call on user-…, Return a copy of *data* with secret values masked. Common secret key names are…, TestMaskSecret

### Community 804 - "capture_screens.py"
Cohesion: 0.25
Nodes (10): Popen, _capture(), _login(), main(), Capture README screenshots of every v5 screen from a locally-running server.…, Launch the local uvicorn server (activated, sqlite, loops off) for capture., _start_server(), _wait_up() (+2 more)

### Community 805 - "run_proxy.sh"
Cohesion: 0.18
Nodes (10): AIDER_BASE_URL, GOOSE_BASE_URL, HERMES_BASE_URL, LOG_LEVEL, OLLAMA_BASE, OPENCODE_BASE_URL, PROXY_PORT, RATE_LIMIT_RPM (+2 more)

### Community 806 - "build_tech_db.py"
Cohesion: 0.35
Nodes (10): _as_list(), _clean(), convert(), _default_source(), _has_pattern(), main(), Any, Strip Wappalyzer's `\\;tag:...` metadata, leaving a plain regex. (+2 more)

### Community 807 - "Security Policy"
Cohesion: 0.18
Nodes (11): Authentication, Authorization, How to Report, Known Security Trade-offs, Reporting a Vulnerability, Response Timeline, Scope, Security Design (+3 more)

### Community 808 - "test_conftest_hermetic_env.py"
Cohesion: 0.18
Nodes (10): parametrize, Guards the hermeticity contract that ``tests/conftest.py`` establishes. Rule 32…, conftest must pin every hermeticity flag before backend import., The env admin address must be the one ``backend.server`` captured.…, Guards the specific landmine: a module-level ADMIN_EMAIL setdefault.…, conftest must NOT pin ``STORAGE_BACKEND=sqlite``. It looks like the obvious…, test_admin_identity_matches_the_server_module(), test_conftest_does_not_pin_storage_backend() (+2 more)

### Community 809 - "test_empirical_verify.py"
Cohesion: 0.49
Nodes (10): _make_runner(), MonkeyPatch, Path, Tests for AgentRunner._empirical_verify (opt-in executable validation gate)., test_empirical_verify_disabled_by_default(), test_empirical_verify_flags_compile_failure(), test_empirical_verify_passes_clean_module_without_tests(), test_empirical_verify_runs_matching_tests_and_passes() (+2 more)

### Community 810 - "test_event_log.py"
Cohesion: 0.45
Nodes (10): Path, _store(), test_append_event_payload_roundtrips(), test_append_event_positions_are_monotonic(), test_append_event_stores_and_increments_count(), test_events_are_isolated_per_session(), test_events_survive_store_restart(), test_get_events_empty_session() (+2 more)

### Community 812 - "test_telegram_task_callback.py"
Cohesion: 0.27
Nodes (10): _parked_task(), asyncio, Task, Telegram inline-button callbacks for the task pre-execution gate. Regression:…, A non-admin tapping Approve must get a modal (show_alert), not silence.…, store(), test_approve_button_approves_and_requeues(), test_non_admin_tap_gets_visible_alert_not_silent_toast() (+2 more)

### Community 813 - "SavingsTracker"
Cohesion: 0.20
Nodes (4): Any, Track cumulative token savings across filtering operations., One-line summary of savings (rtk gain style)., SavingsTracker

### Community 814 - "Instructions"
Cohesion: 0.20
Nodes (9): Acceptance Checks, Instructions, Skill: insights, Step 1 — File change heatmap (which files change most), Step 2 — Failure pattern analysis, Step 3 — Retry analysis, Step 4 — Learnings frequency analysis, Step 5 — Produce a summary report (+1 more)

### Community 815 - "Protocol: Premium Utilitarian Minimalism UI Architect"
Cohesion: 0.20
Nodes (9): 1. Protocol Overview, 2. Absolute Negative Constraints (Banned Elements), 3. Typographic Architecture, 4. Color Palette (Warm Monochrome + Spot Pastels), 5. Component Specifications, 6. Iconography & Imagery Directives, 7. Subtle Motion & Micro-Animations, 8. Execution Protocol (+1 more)

### Community 816 - "The 5-Step Wrap-Up Ritual"
Cohesion: 0.20
Nodes (9): Acceptance Checks, Skill: wrap-up, Step 1 — Changes Audit, Step 2 — Quality Check, Step 3 — Learning Capture, Step 4 — Next Session Planning, Step 5 — One-Paragraph Summary, The 5-Step Wrap-Up Ritual (+1 more)

### Community 817 - "admin_local_brain_router.py"
Cohesion: 0.22
Nodes (9): build_admin_local_brain_router(), Any, APIRouter, BaseModel, backend/admin_local_brain_router.py — admin-session proxy for the local-brain…, Construct a ready-to-mount APIRouter with the auth dependency baked in. The…, _require_admin(), _store() (+1 more)

### Community 818 - "connectors_api.py"
Cohesion: 0.22
Nodes (9): build_connectors_router(), Any, APIRouter, BaseModel, backend/connectors_api.py — the connector catalogue API (`/api/connectors/*`).…, Reject anyone who is not the agency admin., Body for ``POST /api/connectors/webhook/send`` (rule 11 — no raw dict in)., _require_admin() (+1 more)

### Community 819 - "_normalize_tool_choice"
Cohesion: 0.31
Nodes (4): _normalize_tool_choice(), Normalize the ``tool_choice`` parameter for the upstream backend. OpenAI…, Cloud models (with / in name) should keep tool_choice as-is., TestNormalizeToolChoice

### Community 820 - "Agent: Reviewer (Verifier)"
Cohesion: 0.20
Nodes (10): Activation, Agent: Reviewer (Verifier), Blocking Conditions (must return `fail`), Handoff, Key Invariant, Non-Blocking (may return `pass` with suggestions), Output Format, Preferred Model (+2 more)

### Community 821 - "Skill: Agentic Agile"
Cohesion: 0.20
Nodes (9): Autonomous ceremonies (`agents/agile_ceremonies.py`), Key Classes, Purpose, Related, Retrospective & health, Scheduled workflow, Skill: Agentic Agile, Testing (+1 more)

### Community 822 - "Skill: browserbase-ui-test — Adversarial UI Testing"
Cohesion: 0.20
Nodes (9): Applying to local-llm-server platform, Core philosophy, Execution pattern, Reporting, Round 1 — Core flow mapping, Round 2 — Adversarial scenarios, Round 3 — Accessibility + mobile, Skill: browserbase-ui-test — Adversarial UI Testing (+1 more)

### Community 823 - "Skill: financial-analyst (Agentic CFO)"
Cohesion: 0.20
Nodes (9): Branch, Components, Decision Rules, Purpose, Quick Start, Skill: financial-analyst (Agentic CFO), SKILL.md refresh Tue Jun  2 11:35:52 CEST 2026, Testing (+1 more)

### Community 824 - "Graphiti Temporal Context Skill"
Cohesion: 0.20
Nodes (9): 1. Agent Memory as Temporal Graph, 2. Multi-Agent Coordination, 3. Knowledge Queries, Database Schema, Files to Create, Graphiti Temporal Context Skill, Integration Opportunities, References (+1 more)

### Community 825 - "Skill: seo-audit-report"
Cohesion: 0.20
Nodes (9): How This Skill Works (Agent Instructions), Output Files, Parameters, Purpose, Quick Start, Revenue-at-Risk Disclaimer (load-bearing — always include in reports), Skill: seo-audit-report, Troubleshooting (+1 more)

### Community 826 - "ADR-008: LLMRouter — the single multi-provider routing gateway"
Cohesion: 0.20
Nodes (10): ADR-008: LLMRouter — the single multi-provider routing gateway, Comparison with OmniRoute, Consequences, Context, Differences — why a port was rejected, Incompatible components (explicitly rejected), References, Reusable components (ideas adopted) (+2 more)

### Community 827 - "Core Pillars"
Cohesion: 0.20
Nodes (9): 1. Unified Intent Orchestration, 2. Deep Sticky Memory, 3. Execution Cognition Flow, 4. Progress Humanization, Core Pillars, Direct Chat Evolution: Seamless Assistant Architecture, Failure Recovery, Overview (+1 more)

### Community 828 - "467 Golden Path — Locked Implementation Order"
Cohesion: 0.20
Nodes (10): 467 Golden Path — Locked Implementation Order, Agent Code (agent/ directory), Backend Code (backend/, handlers/), Golden Path Exceptions, Module-Specific Golden Paths, Skill Code (.agents/skills/), Verification, What Breaks the Golden Path (+2 more)

### Community 829 - "Competitor Analysis — Autonomous AI Agency"
Cohesion: 0.20
Nodes (9): 1. Fix the framing first: these are two different markets, 2. What this repo actually is (verified on `master`), 3. Where we already beat the competitor set — keep and market these, 4. The gaps worth closing (ranked by value ÷ effort), 5. Recommended PR sequence, Competitor Analysis — Autonomous AI Agency, Gap A — The workflow engine is built but unreachable  ← **highest leverage**, Gap B — Connector catalog is nearly empty (+1 more)

### Community 830 - "Issue #1427: quick-note:https://github.com/bingreeky/JIT"
Cohesion: 0.20
Nodes (9): Context Plan — Issue #1427: quick-note:https://github.com/bingreeky/JIT, Decision, How its four axes map onto what this repo already has, Issue #1427: quick-note:https://github.com/bingreeky/JIT, Recommendation to the maintainer, Source Grounding, What the source actually is, What was considered and rejected (+1 more)

### Community 831 - "LLM Router — configuration guide"
Cohesion: 0.20
Nodes (10): Budgets, cache.yaml, Environment variables, health.yaml, keys.yaml, LLM Router — configuration guide, models.yaml, Per-agent policies (+2 more)

### Community 832 - "LLM Router — provider guide"
Cohesion: 0.20
Nodes (9): Adding any OpenAI-compatible provider, Auth styles, Cheap tiers, Cloud providers, Free tiers, LLM Router — provider guide, Multiple keys, Premium (+1 more)

### Community 833 - "CI Troubleshooting Runbook"
Cohesion: 0.20
Nodes (10): A test hangs in CI but passes locally, All three CI jobs fail with "git exit code 128" in Post Checkout, CI Troubleshooting Runbook, CodeQL action version, Frontend tests fail in parallel / async timer leaks, GitHub Actions YAML block scalar — bash heredoc content at column 0, Python 3.13 compatibility status, Python test job fails — "Process completed with exit code 1", no .pytest_cache found (+2 more)

### Community 834 - "_is_denied_path"
Cohesion: 0.33
Nodes (3): _is_denied_path(), Return a rejection reason, or "" if *path* is allowed., TestIsDeniedPath

### Community 835 - "OutputFilter"
Cohesion: 0.24
Nodes (7): OutputFilter, Token-optimizing output filter for command stdout. Usage:: from output_filter…, Any, Path, run_command(), _safe_allowlist(), validate_command()

### Community 836 - "CircuitState"
Cohesion: 0.27
Nodes (3): CircuitState, Reduce probe frequency for runtimes that have never come online., TestCircuitState

### Community 837 - "enrich_quick_note_issues.py"
Cohesion: 0.36
Nodes (9): _dispatch_generation(), _fetch_open_issues(), _has_context(), _headers(), _is_quick_note(), main(), Ask the bulk context workflow to generate documents for these issues., Find quick-note issues that have no context document and queue real generation.… (+1 more)

### Community 838 - "Dream"
Cohesion: 0.22
Nodes (6): Dream, Return the most recent dreams, newest first., A consolidated dream built from multiple session memories., Return a brief summary of the dream., Tests for Dream dataclass., TestDream

### Community 839 - "_resolve_push_token"
Cohesion: 0.31
Nodes (9): GitHub token used to push branches / open PRs during EXECUTION (#506).…, _resolve_push_token(), _clean_env(), tests/test_orchestrator_push_token.py — #506 push/PR token resolution.…, test_falls_through_gh_pat_and_github_token(), test_internal_run_uses_server_token(), test_per_user_token_always_wins(), test_user_run_with_optin_uses_server_token() (+1 more)

### Community 840 - "_redact_for_notification"
Cohesion: 0.24
Nodes (5): Proactively push a Telegram approval-gate message with inline buttons. Sent…, Send a Telegram message with an inline keyboard to all configured chats., Best-effort secret/email/IP redaction for outbound Telegram/webhook messages., _redact_for_notification(), TestRedactForNotification

### Community 841 - "test_catalogue_probe.py"
Cohesion: 0.20
Nodes (6): probe(), The provider catalogue probe: must not leak, must not lie, must not be…, The first real run died in 10 seconds on ModuleNotFoundError: httpx. The probe…, `--json PATH` writes a machine-readable summary the scheduled drift-report step…, TestTheJsonSummary, TestTheWorkflowInstallsWhatTheImportNeeds

### Community 842 - "TestZeroAttemptDiagnostics"
Cohesion: 0.29
Nodes (4): A zero-attempt exhaustion must say WHICH of the three causes it is. Nothing…, An operator whose switches reset on deploy needs to know that here., A broken registry must not turn a failed call into a crash., TestZeroAttemptDiagnostics

### Community 843 - "TestPoliciesGovernanceStableClaim"
Cohesion: 0.20
Nodes (5): `policies_governance` may be STABLE only while enforcement is real. The same…, Each documented ceiling must fire from its own counter alone., LLM cost/tokens and spawn depth must be chargeable onto the budget — the wiring…, The runtime-dispatch seam must consult the same gate budget, so work handed to…, TestPoliciesGovernanceStableClaim

### Community 844 - "TestSessionMemory"
Cohesion: 0.20
Nodes (3): Tests for services/managed_agents.py — Managed Agents Dreams. Uses importlib to…, Tests for SessionMemory dataclass., TestSessionMemory

### Community 845 - "test_model_catalog_guard.py"
Cohesion: 0.29
Nodes (8): _declared(), Unit tests for scripts/check_model_catalog_consistency.py. The guard is CI's…, The shipped catalogues must pass the guard — this is what CI enforces., test_declared_folds_both_provider_spellings(), test_legacy_only_provider_is_not_a_contradiction(), test_prefer_models_must_be_declared(), test_real_contradiction_is_a_hard_failure(), test_the_real_repo_catalogues_are_consistent()

### Community 846 - "TestParsing"
Cohesion: 0.22
Nodes (5): parametrize, Includes a bare 404 with an empty body (observed on NVIDIA NIM) — no…, A malformed listing must never be read as "the key serves nothing"., TestParsing, TestUnknownModelDetection

### Community 847 - "TestMongoGate"
Cohesion: 0.20
Nodes (3): Tests must never mutate a shared operational store., The storage layer's localhost default is a placeholder, not config. Treating it…, TestMongoGate

### Community 848 - "_FakeInner"
Cohesion: 0.22
Nodes (3): _FakeInner, Any, Stands in for MCPClient inside RenderMCPClient.

### Community 850 - "_Recorder"
Cohesion: 0.20
Nodes (4): _Captured, Load telegram_bot fresh in each test, with env vars reset., telegram_bot(), _Recorder

### Community 851 - "test_workflow_api_mount.py"
Cohesion: 0.20
Nodes (9): tests/test_workflow_api_mount.py — the CRISPY workflow router is mounted and…, Anonymous callers are rejected (401), never served., A signed-in non-admin is forbidden (403) — this is an admin surface., An admin reaches the mounted router and gets a well-formed list payload., A missing run returns 404 from the handler, proving the route exists (an…, test_workflow_list_forbidden_for_non_admin(), test_workflow_list_ok_for_admin(), test_workflow_list_requires_authentication() (+1 more)

### Community 852 - "synthesize"
Cohesion: 0.36
Nodes (9): _convert_to_ogg(), voice/tts.py — Text-to-Speech for the CEO voice pipeline. Converts text to an…, Convert audio to OGG Opus (Telegram voice note format) via pydub+ffmpeg., Convert text to OGG voice note bytes. Returns None on failure., _select_backend(), synthesize(), _synthesize_elevenlabs(), _synthesize_gtts() (+1 more)

### Community 853 - "Path"
Cohesion: 0.20
Nodes (4): Path, Simple counters for workspace operations., Safely resolve a path inside a workspace's source directory. Rejects traversal…, WorkspaceMetrics

### Community 854 - "rag_context.py"
Cohesion: 0.22
Nodes (8): ContextResult, agent/rag_context.py — Advanced RAG context management layer. Pipeline --------…, Combine ranked lists with Reciprocal Rank Fusion., Final output of the RAG pipeline., _rrf(), test_rrf_merges_two_rankings(), test_rrf_scores_descending(), test_rrf_single_ranking_preserves_order()

### Community 855 - "_extract_workflow_relevance"
Cohesion: 0.33
Nodes (4): _extract_workflow_relevance(), Return workflow types mentioned in the skill content., Tests for _extract_workflow_relevance()., TestExtractWorkflowRelevance

### Community 856 - "task.py"
Cohesion: 0.31
Nodes (7): Enum, str, Task definition schema for the evaluation harness. Inspired by OpenHarness'…, Returns (success: bool, score: float ∈ [0, 1]). Raises NotImplementedError for…, SuccessCriterion, SuccessCriterionType, TaskDifficulty

### Community 857 - "Skill: changelog-enforcer"
Cohesion: 0.22
Nodes (8): Acceptance Checks, Changelog Location, Entry Format, Examples, Hook Behaviour, Instructions, Skill: changelog-enforcer, When to Use

### Community 858 - "Skill: learn-rule"
Cohesion: 0.22
Nodes (8): Acceptance Checks, Instructions, Learnings File Format, Skill: learn-rule, Step 1 — Identify the rule, Step 2 — Append to learnings file, Step 3 — Check if CLAUDE.md should be updated, When to Use

### Community 859 - "Instructions"
Cohesion: 0.22
Nodes (8): Acceptance Checks, Instructions, Skill: session-handoff, Step 1 — Capture current state, Step 2 — Write the handoff document, Step 3 — Update machine-readable state, Step 4 — Confirm the handoff is self-contained, When to Use

### Community 860 - "prompts/README.md"
Cohesion: 0.22
Nodes (4): Command: /resume, References, Usage, What It Does

### Community 861 - "Skill: Agentic Portfolio Management"
Cohesion: 0.22
Nodes (8): Key Classes, Purpose, Related, Skill actions (via SkillBindings), Skill: Agentic Portfolio Management, Testing, Usage, WSJF

### Community 862 - "Skill: changelog-enforcer"
Cohesion: 0.22
Nodes (8): Acceptance Checks, Changelog Location, Entry Format, Examples, Hook Behaviour, Instructions, Skill: changelog-enforcer, When to Use

### Community 863 - "Skill: cowork-session (Claude Cowork)"
Cohesion: 0.22
Nodes (8): Branch, Components, Purpose, Quick Start, Session Roles, Skill: cowork-session (Claude Cowork), Testing, When to Use

### Community 864 - "Skill: video-context — read a video without watching it"
Cohesion: 0.22
Nodes (8): How It Works, Limits — know these before relying on it, Skill: video-context — read a video without watching it, Testing, Usage, What To Do With The Transcript, When To Use This, Why This Exists

### Community 865 - "Active Task Tracker"
Cohesion: 0.22
Nodes (7): Active Task Tracker, Bug Log, Current Sprint Tasks, Roadmap Items (from `docs/roadmap-killer-todos.md`), Status Key, Completed Task Archive — June to August 2026, Session Log

### Community 866 - "Decision"
Cohesion: 0.22
Nodes (9): 1. `LLMRouter` is the only gateway, 2. Providers are data, not code, 3. Secrets stay in the environment, 4. Three independent failure scopes, 5. Bulkhead isolation, 6. Context is managed losslessly, 7. Configuration is six committed YAML files, 8. Backwards compatibility by shim, not by rewrite (+1 more)

### Community 867 - "ADR 003: Multi-Agent Orchestration with Plan-Execute-Verify Loop"
Cohesion: 0.22
Nodes (8): ADR 003: Multi-Agent Orchestration with Plan-Execute-Verify Loop, Alternatives Considered, Consequences, Context, Decision, Negative, Neutral, Positive

### Community 868 - "Autonomous SDLC Loop (Agency Core, repo-agnostic)"
Cohesion: 0.22
Nodes (9): Autonomous SDLC Loop (Agency Core, repo-agnostic), Companies without a connected repo (URL-only onboarding), Design principle: repo-agnostic, not GitHub-Actions-bound, Detect & respect each repo's delivery policy, Integrations & intake sources (honest tiers), Reuse map (what already exists), Safety invariants (carry over from `agent/CLAUDE.md`), The gap this closes (+1 more)

### Community 869 - "The 8-Step Golden Path"
Cohesion: 0.22
Nodes (9): Step 1: Scout — Understand the territory, Step 2: Plan — Define the change, Step 3: Write tests first, Step 4: Implement, Step 5: Validate, Step 6: Review, Step 7: Document, Step 8: Commit and propose (+1 more)

### Community 870 - "Issue #1356: quick-note:https://searchengineland.com/turn-seo-backlog-into-roadmap-485713"
Cohesion: 0.22
Nodes (8): Architectural Notes, Context Plan — Issue #1356: quick-note:https://searchengineland.com/turn-seo-backlog-into-roadmap-485713, Decision, Issue #1356: quick-note:https://searchengineland.com/turn-seo-backlog-into-roadmap-485713, Quality Gate, Source Grounding, What the source actually is, What was considered

### Community 871 - "PR #634 Implementation Tracker"
Cohesion: 0.22
Nodes (8): Phase 1 — Stop the bleeding + paid kill switch ✅, Phase 2 — Per-surface assignment in the UI 🔄, Phase 3 — Persistence hardening (#537, #524) ⏳, Phase 4 — Onboarding fixes (#593, #619, PR #623) ⏳, Phase 5 — Reliability (#522) ⏳, Phase 6 — Green tests + housekeeping ⏳, PR #634 Implementation Tracker, Verification checklist (final)

### Community 872 - "KV Cache Internals"
Cohesion: 0.22
Nodes (9): KV Cache Internals, KV Cache with Grouped Query Attention, Memory Layout, Paged Attention (vLLM), Prefill vs Decode Phase, Quantization of KV Cache, Speculative Decoding, The Problem: Redundant Computation (+1 more)

### Community 873 - "Platform Controls"
Cohesion: 0.22
Nodes (8): Across processes, Adding a control, API, Groups, How a value is resolved, Live vs restart-required, Platform Controls, What is deliberately **not** here

### Community 874 - "Release Procedure"
Cohesion: 0.22
Nodes (8): Changelog Update, Commit and Tag, Post-Release Checklist, Pre-Flight, Release Procedure, Rollback, Verify CI, Version Bump

### Community 875 - "V2.0 Modernization — Runbook"
Cohesion: 0.22
Nodes (8): Adding a new provider adapter, CI, Importing new code, Module map (old → new), Removing the shims (future cleanup), Rollback, Test migration, V2.0 Modernization — Runbook

### Community 876 - "Setup"
Cohesion: 0.22
Nodes (8): 1. Get LiveKit credentials, 2. Configure the backend (Render env vars), 3. The SAM voice worker, 4. Talk to SAM, Architecture, SAM Realtime Voice over LiveKit, Setup, Troubleshooting

### Community 877 - "Troubleshooting"
Cohesion: 0.22
Nodes (9): Bot doesn't respond to messages, Bot runs but service control commands fail, Multiple simultaneous users cause slowdowns, Performance Issues, "Permission denied" from admin commands, Quick Diagnostics, Telegram Bot Issues, Tokens-per-second is low (+1 more)

### Community 878 - "ENGINEERING_STANDARDS.md — Patterns & Reference"
Cohesion: 0.22
Nodes (9): Architecture decision records, Authorization patterns, Commit messages, Database indexes, ENGINEERING_STANDARDS.md — Patterns & Reference, Error handling, Log levels, Performance targets (+1 more)

### Community 879 - "apply_overrides"
Cohesion: 0.22
Nodes (9): apply_overrides(), Write *overrides* into ``os.environ`` and refresh dependent caches. Keys that…, Re-read every ``settings`` attribute from the updated environment. Re-runs…, _refresh_settings_singleton(), Re-running Settings.__init__ mints a new random secret when SECRET_KEY is…, test_apply_overrides_refreshes_the_settings_singleton(), test_apply_overrides_writes_only_catalogued_keys(), test_clearing_an_override_restores_the_startup_environment() (+1 more)

### Community 881 - "test_backend_requirements_cover_runtime_imports.py"
Cohesion: 0.25
Nodes (8): _declared_packages(), parametrize, Path, Guard against the recurring "works in CI, missing in prod" dependency drift.…, Return the normalised distribution names declared in *requirements*., If the Dockerfile ever installs the root file, this guard can relax. Until then…, test_backend_requirements_declares_runtime_package(), test_dockerfile_still_installs_backend_requirements_only()

### Community 883 - "test_changelog_parity_guard.py"
Cohesion: 0.22
Nodes (3): tests/test_changelog_parity_guard.py — corruption guard for the changelog gate.…, A 7-equals line under a title (Markdown setext H1) must not false-positive., test_setext_heading_underline_is_not_flagged()

### Community 885 - "TestPolicyAuthoringUiStableClaim"
Cohesion: 0.22
Nodes (4): `policy_authoring_ui` may be STABLE only while safe in-product authoring is…, The load-bearing safety check: dropping a baseline guardrail is refused., The router must expose the propose route the STABLE claim depends on., TestPolicyAuthoringUiStableClaim

### Community 886 - "TestPaidPolicyDurability"
Cohesion: 0.22
Nodes (3): This is the document the UI toggle writes via _set_provider_policy., Never enable paid spend by accident., TestPaidPolicyDurability

### Community 887 - "test_scanner_deps_parity.py"
Cohesion: 0.31
Nodes (8): _declared_packages(), Guard against the CI-vs-production dependency drift that made gucci.com (and…, Top-level module names imported anywhere in services/scanner.py., Every third-party package the scanner imports must be in the file the…, Belt-and-suspenders: the two deps whose absence caused the gucci.com production…, _scanner_imports(), test_critical_scanner_deps_explicitly_present(), test_scanner_third_party_deps_declared_in_backend_requirements()

### Community 888 - "test_serve_spa_prefixes.py"
Cohesion: 0.31
Nodes (8): _prefixes(), Behavioral: GET to a path that has NO upstream handler but IS in the protected…, Regression tests for SPA catch-all prefix protection (backend/server.py). Bug…, SPA_PROTECTED_PREFIXES must be exposed at module scope (not inside an if-block)…, test_legitimate_spa_paths_are_not_blocked(), test_protected_paths_are_covered_by_prefix_tuple(), test_serve_spa_returns_non_html_for_protected_orphan_path(), test_spa_protected_prefixes_is_module_level_constant()

### Community 889 - "_safe_resolve"
Cohesion: 0.25
Nodes (4): If a symlink inside the workspace points outside, resolve_path blocks it., TestPathSafety, Resolve *path* and verify it stays under *base_root*. Blocks symlink escape:…, _safe_resolve()

### Community 890 - "stt.py"
Cohesion: 0.36
Nodes (8): voice/stt.py — Speech-to-Text for the CEO voice pipeline. Transcribes audio…, Transcribe audio bytes to text. Returns empty string on failure., Fallback: Google Web Speech API via SpeechRecognition library., _select_backend(), transcribe(), _transcribe_google(), _transcribe_local(), _transcribe_openai()

### Community 891 - "EvalHarness"
Cohesion: 0.29
Nodes (5): EvalHarness, Runs agent functions against Tasks, records Trajectories and produces…, Execute the agent on a single task and return an EvalResult., Delegate to the agent callable (sync or async)., AgentFn

### Community 893 - "agent/output_filter.py"
Cohesion: 0.32
Nodes (7): filter_output(), get_output_filter(), get_savings_summary(), agent/output_filter.py — LLM Output Compression & Token Savings Inspired by…, Get or create the singleton OutputFilter instance., Convenience function: filter command output., Get token savings summary.

### Community 894 - "_score_turns"
Cohesion: 0.36
Nodes (8): Score each turn by exponential recency decay combined with query relevance.…, _score_turns(), test_score_turns_empty(), test_score_turns_importance_multiplier(), test_score_turns_recency_newer_scores_higher(), test_score_turns_relevance_boosts_score(), test_score_turns_sorted_descending(), _turn()

### Community 895 - "Task"
Cohesion: 0.32
Nodes (4): Path, Score the agent's final answer. Returns (success, score)., A fully-specified evaluation task. Fields mirror the OpenHarness task schema so…, Task

### Community 896 - "TrajectoryStep"
Cohesion: 0.25
Nodes (5): Any, Agent trajectory recorder – captures every step an agent takes so runs can be…, A single action/observation pair in an agent trajectory., Append a step and return it., TrajectoryStep

### Community 897 - "quality_checker.py"
Cohesion: 0.32
Nodes (6): AITellType, Enum, str, Quality checker inspired by stop-slop (https://github.com/hardikpandya/stop-…, Categories of AI tells, Tests for quality checker (stop-slop inspired)

### Community 898 - "Skill: docs-sync"
Cohesion: 0.25
Nodes (7): Acceptance Checks, ADR Guidelines, AGENTS.md Update Rules, Docs to Check After Each Change Type, Instructions, Skill: docs-sync, When to Use

### Community 899 - "Agent: Implementer (Executor)"
Cohesion: 0.25
Nodes (8): Activation, Agent: Implementer (Executor), Constraints, Handoff, Preferred Model, Responsibilities, Role, Shared State

### Community 900 - "Agent: Judge (Release / QA Gate)"
Cohesion: 0.25
Nodes (7): Activation, Agent: Judge (Release / QA Gate), Enforcement, Output, Responsibilities, Role, Verdict Meanings

### Community 901 - "Agent: Planner (Architect)"
Cohesion: 0.25
Nodes (8): Activation, Agent: Planner (Architect), Failure Behaviour, Handoff, Output Format, Preferred Model, Responsibilities, Role

### Community 902 - "Skill: browserbase-browser — Real Browser Automation"
Cohesion: 0.25
Nodes (7): Applying to local-llm-server platform, Core commands, Mode selection, Setup, Skill: browserbase-browser — Real Browser Automation, Troubleshooting, Workflow pattern

### Community 903 - "Skill: docs-sync"
Cohesion: 0.25
Nodes (7): Acceptance Checks, ADR Guidelines, CLAUDE.md Update Rules, Docs to Check After Each Change Type, Instructions, Skill: docs-sync, When to Use

### Community 904 - "Skill: memory-consolidation (Dream Memory)"
Cohesion: 0.25
Nodes (7): Branch, Consolidation Lifecycle, Memory Kinds, Purpose, Quick Start, Skill: memory-consolidation (Dream Memory), Testing

### Community 905 - "GitHub Branch Protection Settings"
Cohesion: 0.25
Nodes (7): Branch name pattern: `main` (or `master`), CODEOWNERS Setup, Enabling via GitHub CLI, GitHub Branch Protection Settings, Purpose, Required Settings, Why This Can't Be Fully Repo-Enforced

### Community 906 - "ADR 001: Self-Hosted OpenAI-Compatible Proxy"
Cohesion: 0.25
Nodes (7): ADR 001: Self-Hosted OpenAI-Compatible Proxy, Consequences, Context, Decision, Negative, Neutral, Positive

### Community 907 - "ADR 002: Dynamic Model Routing with Task Classification"
Cohesion: 0.25
Nodes (7): ADR 002: Dynamic Model Routing with Task Classification, Consequences, Context, Decision, Negative, Neutral, Positive

### Community 908 - "AGENTS.md — AI Agent Configuration for local-llm-server"
Cohesion: 0.25
Nodes (7): Agent Roles, AGENTS.md — AI Agent Configuration for local-llm-server, Operating Instructions, Quick Start for Agents, Risky Paths — Require Extra Care, State Files, Workspace Purpose

### Community 909 - "Advisor Strategy — Local Proxy Handling"
Cohesion: 0.25
Nodes (7): Advisor Strategy — Local Proxy Handling, How This Proxy Handles Advisor Requests, Incoming message history (advisor blocks), Local Equivalent: The Planner Role, Outgoing requests (tools array), Using the Real Advisor Strategy via This Proxy, What the Anthropic Advisor Strategy Is

### Community 910 - "ceo-micromanagement.md"
Cohesion: 0.25
Nodes (4): P0 behavior change, Readiness contract, Runtime model, Runtime types

### Community 911 - "Web UI + Admin (Claude Code–style)"
Cohesion: 0.25
Nodes (7): Acceptance checks, Approach, Files to change, Files to read first, Goal, Risks, Web UI + Admin (Claude Code–style)

### Community 912 - "467 Skill Inventory — load / wire / test status"
Cohesion: 0.25
Nodes (7): 467 Skill Inventory — load / wire / test status, Agent Specialties (not skills per se, but referenced in spec §B), Core Agency Skills (load/wire/test), Gaps Summary, Named Skills Referenced in Spec §C, Skill Registry, Test Coverage Summary

### Community 913 - "Free NVIDIA brain + UI-controlled provider policy + no silent spend"
Cohesion: 0.25
Nodes (8): Decisions (locked with the owner), Design: one UI-controlled Provider Policy (single source of truth), Free NVIDIA brain + UI-controlled provider policy + no silent spend, Open-PR / issue disposition (read + acted on), Root cause of the $20 burn (verified in-repo), SELF-CONTAINED AGENT PROMPT (paste to run cold), Verification / acceptance, Why this PR exists (context)

### Community 914 - "Issue #362: Nvidia repo setup"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #362: Nvidia repo setup, Implementation Prompt, Issue #362: Nvidia repo setup, Relevant Files to Read First, Risk Flags, TODO List

### Community 915 - "Issue #364: quick-note:https://www.marktechpost.com/2026/06/01/meet-memory-os-a-6-layer-open-source-memory-stack-built-on-top-of-hermes-agent/"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #364: quick-note:https://www.marktechpost.com/2026/06/01/meet-memory-os-a-6-layer-open-source-memory-stack-built-on-top-of-hermes-agent/, Implementation Prompt, Issue #364: quick-note:https://www.marktechpost.com/2026/06/01/meet-memory-os-a-6-layer-open-source-memory-stack-built-on-top-of-hermes-agent/, Relevant Files to Read First, Risk Flags, TODO List

### Community 916 - "Issue #378: quick-note:https://www.marktechpost.com/2026/06/02/tinyfish-launches-bigset-an-open-source-multi-agent-system-that-builds-structured-live-datasets-from-plain-english-descriptions/"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #378: quick-note:https://www.marktechpost.com/2026/06/02/tinyfish-launches-bigset-an-open-source-multi-agent-system-that-builds-structured-live-datasets-from-plain-english-descriptions/, Implementation Prompt, Issue #378: quick-note:https://www.marktechpost.com/2026/06/02/tinyfish-launches-bigset-an-open-source-multi-agent-system-that-builds-structured-live-datasets-from-plain-english-descriptions/, Relevant Files to Read First, Risk Flags, TODO List

### Community 917 - "Issue #379: quick-note:https://searchengineland.com/schema-markup-optimize-agentic-web-479080"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #379: quick-note:https://searchengineland.com/schema-markup-optimize-agentic-web-479080, Implementation Prompt, Issue #379: quick-note:https://searchengineland.com/schema-markup-optimize-agentic-web-479080, Relevant Files to Read First, Risk Flags, TODO List

### Community 918 - "Issue #380: quick-note:https://cursor.com/blog/cloud-agent-lessons"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #380: quick-note:https://cursor.com/blog/cloud-agent-lessons, Implementation Prompt, Issue #380: quick-note:https://cursor.com/blog/cloud-agent-lessons, Relevant Files to Read First, Risk Flags, TODO List

### Community 919 - "Issue #381: quick-note:https://www.xda-developers.com/claude-code-with-opus-48-is-expensive-but-i-made-it-efficient-with-my-local-ai-workflow/"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #381: quick-note:https://www.xda-developers.com/claude-code-with-opus-48-is-expensive-but-i-made-it-efficient-with-my-local-ai-workflow/, Implementation Prompt, Issue #381: quick-note:https://www.xda-developers.com/claude-code-with-opus-48-is-expensive-but-i-made-it-efficient-with-my-local-ai-workflow/, Relevant Files to Read First, Risk Flags, TODO List

### Community 920 - "Issue #382: quick-note:https://claude.com/blog/how-coderabbit-used-claude-to-build-an-agent-orchestration-system"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #382: quick-note:https://claude.com/blog/how-coderabbit-used-claude-to-build-an-agent-orchestration-system, Implementation Prompt, Issue #382: quick-note:https://claude.com/blog/how-coderabbit-used-claude-to-build-an-agent-orchestration-system, Relevant Files to Read First, Risk Flags, TODO List

### Community 921 - "Issue #383: quick-note:https://www.marktechpost.com/2026/05/29/hexo-labs-open-sources-sia-a-self-improving-agent-that-updates-both-the-harness-and-the-model-weights/"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #383: quick-note:https://www.marktechpost.com/2026/05/29/hexo-labs-open-sources-sia-a-self-improving-agent-that-updates-both-the-harness-and-the-model-weights/, Implementation Prompt, Issue #383: quick-note:https://www.marktechpost.com/2026/05/29/hexo-labs-open-sources-sia-a-self-improving-agent-that-updates-both-the-harness-and-the-model-weights/, Relevant Files to Read First, Risk Flags, TODO List

### Community 922 - "Issue #416: feat: Self-hosted Codebuff (freebuff) on free NVIDIA models + Telegram bot phone control"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #416: feat: Self-hosted Codebuff (freebuff) on free NVIDIA models + Telegram bot phone control, Implementation Prompt, Issue #416: feat: Self-hosted Codebuff (freebuff) on free NVIDIA models + Telegram bot phone control, Relevant Files to Read First, Risk Flags, TODO List

### Community 923 - "Issue #485: [Trend Digest] Week of 2026-06-08"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #485: [Trend Digest] Week of 2026-06-08, Implementation Prompt, Issue #485: [Trend Digest] Week of 2026-06-08, Relevant Files to Read First, Risk Flags, TODO List

### Community 924 - "Issue #488: quick-note:https://github.com/cookiy-ai/user-research-skill"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #488: quick-note:https://github.com/cookiy-ai/user-research-skill, Implementation Prompt, Issue #488: quick-note:https://github.com/cookiy-ai/user-research-skill, Relevant Files to Read First, Risk Flags, TODO List

### Community 925 - "Issue #491: Implement whatever is necessary from https://github.com/BehiSecc/awesome-claude-skills"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #491: Implement whatever is necessary from https://github.com/BehiSecc/awesome-claude-skills, Implementation Prompt, Issue #491: Implement whatever is necessary from https://github.com/BehiSecc/awesome-claude-skills, Relevant Files to Read First, Risk Flags, TODO List

### Community 926 - "Issue #493: Use the https://github.com/mvanhorn/last30days-skill skill to get the trend updated"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #493: Use the https://github.com/mvanhorn/last30days-skill skill to get the trend updated, Implementation Prompt, Issue #493: Use the https://github.com/mvanhorn/last30days-skill skill to get the trend updated, Relevant Files to Read First, Risk Flags, TODO List

### Community 927 - "Issue #495: Read https://www.anthropic.com/news/claude-fable-5-mythos-5 and understand if mythos or fable can be added to the repo"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #495: Read https://www.anthropic.com/news/claude-fable-5-mythos-5 and understand if mythos or fable can be added to the repo, Implementation Prompt, Issue #495: Read https://www.anthropic.com/news/claude-fable-5-mythos-5 and understand if mythos or fable can be added to the repo, Relevant Files to Read First, Risk Flags, TODO List

### Community 928 - "Issue #504: EPIC: Autonomy hardening — live-verified defects 2026-06-10"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #504: EPIC: Autonomy hardening — live-verified defects 2026-06-10, Implementation Prompt, Issue #504: EPIC: Autonomy hardening — live-verified defects 2026-06-10, Relevant Files to Read First, Risk Flags, TODO List

### Community 929 - "Issue #581: Sprint tracker: pending work after brand rename + mobile-first pass"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #581: Sprint tracker: pending work after brand rename + mobile-first pass, Implementation Prompt, Issue #581: Sprint tracker: pending work after brand rename + mobile-first pass, Relevant Files to Read First, Risk Flags, TODO List

### Community 930 - "Issue #656: Bugs"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #656: Bugs, Implementation Prompt, Issue #656: Bugs, Relevant Files to Read First, Risk Flags, TODO List

### Community 931 - "Issue #657: quick-note:https://github.com/earendil-works/pi"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #657: quick-note:https://github.com/earendil-works/pi, Implementation Prompt, Issue #657: quick-note:https://github.com/earendil-works/pi, Relevant Files to Read First, Risk Flags, TODO List

### Community 932 - "Issue #659: quick-note:https://github.com/nex-agi/Nex-N2"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #659: quick-note:https://github.com/nex-agi/Nex-N2, Implementation Prompt, Issue #659: quick-note:https://github.com/nex-agi/Nex-N2, Relevant Files to Read First, Risk Flags, TODO List

### Community 933 - "Issue #660: quick-note:https://github.com/getsentry/sentry-for-ai"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #660: quick-note:https://github.com/getsentry/sentry-for-ai, Implementation Prompt, Issue #660: quick-note:https://github.com/getsentry/sentry-for-ai, Relevant Files to Read First, Risk Flags, TODO List

### Community 934 - "Issue #661: quick-note:https://github.com/XiaomiMiMo/MiMo-Code"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #661: quick-note:https://github.com/XiaomiMiMo/MiMo-Code, Implementation Prompt, Issue #661: quick-note:https://github.com/XiaomiMiMo/MiMo-Code, Relevant Files to Read First, Risk Flags, TODO List

### Community 935 - "Issue #664: quick-note:https://github.com/Grominet95/jarvis-OS"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #664: quick-note:https://github.com/Grominet95/jarvis-OS, Implementation Prompt, Issue #664: quick-note:https://github.com/Grominet95/jarvis-OS, Relevant Files to Read First, Risk Flags, TODO List

### Community 936 - "Issue #666: quick-note:https://github.com/porokka/jarvis-os"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #666: quick-note:https://github.com/porokka/jarvis-os, Implementation Prompt, Issue #666: quick-note:https://github.com/porokka/jarvis-os, Relevant Files to Read First, Risk Flags, TODO List

### Community 937 - "Issue #670: quick-note:https://github.com/perplexityai/bumblebee"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #670: quick-note:https://github.com/perplexityai/bumblebee, Implementation Prompt, Issue #670: quick-note:https://github.com/perplexityai/bumblebee, Relevant Files to Read First, Risk Flags, TODO List

### Community 938 - "Issue #672: quick-note:https://github.com/Chachamaru127/claude-code-harness"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #672: quick-note:https://github.com/Chachamaru127/claude-code-harness, Implementation Prompt, Issue #672: quick-note:https://github.com/Chachamaru127/claude-code-harness, Relevant Files to Read First, Risk Flags, TODO List

### Community 939 - "Issue #676: quick-note:https://github.com/WeiboAI/VibeThinker"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #676: quick-note:https://github.com/WeiboAI/VibeThinker, Implementation Prompt, Issue #676: quick-note:https://github.com/WeiboAI/VibeThinker, Relevant Files to Read First, Risk Flags, TODO List

### Community 940 - "Issue #820: quick-note:https://github.com/cobusgreyling/loop-engineering"
Cohesion: 0.25
Nodes (7): Architectural Notes, Context Plan — Issue #820: quick-note:https://github.com/cobusgreyling/loop-engineering, Implementation Prompt, Issue #820: quick-note:https://github.com/cobusgreyling/loop-engineering, Relevant Files to Read First, Risk Flags, TODO List

### Community 941 - "Positional Encoding Internals"
Cohesion: 0.25
Nodes (7): ALiBi (Attention with Linear Biases), Comparison, Learned Positional Embeddings, Positional Encoding Internals, RoPE Scaling for Long Contexts, Rotary Positional Embedding (RoPE), Sinusoidal Positional Encoding (Original Transformer)

### Community 942 - "Setup"
Cohesion: 0.25
Nodes (8): 1. Clone and install, 2. Configure, 3. Start the backend, 4. Start the frontend (development), 5. Onboard your first company, 6. Connect your AI coding tools (optional), Setup, What you need

### Community 943 - "TOP 6 — Highest-ROI Items (Validated by Opus Research Agent)"
Cohesion: 0.25
Nodes (8): ★1 — 3-Phase Context-Pruner Middleware [P0] [CBF], ★2 — Specialized Sub-Agents with Per-Role Cheap Models [P0] [CBF + HRM], ★3 — Reasoning Token Budget + Toggle [P0] [NVD], ★4 — Skill/Procedural Memory (agentskills.io compatible) [P1] [HRM], ★5 — Sandboxed Agent Execution (E2B / Docker micro-VM) [P1] [CHM] ✅ Delivered 2026-07-04, ★6 — Cost Analytics + FTS5 Shared Memory + Agent Constitution [P1] [AOS], ★7 — Adaptive Loop Halting (Early Exit on High Confidence) [P1] [MYT + HRM], TOP 6 — Highest-ROI Items (Validated by Opus Research Agent)

### Community 944 - "SECTION A — Agent Efficiency (Hermes / AOS / MYT)"
Cohesion: 0.25
Nodes (8): A1 — Hermes ChatML Prompt Format for Tool Calling [P0] [HRM], A2 — Multi-Hop Reasoning Chain (ReAct / Tree-of-Thought) [P0] [HRM], A3 — Agent Capability Registry + Dynamic Tool Discovery [P1] [AOS], A4 — Async Task Queue with Priority and Backpressure [P1] [AOS], A5 — Inter-Agent Message Bus [P1] [AOS / MYT], A6 — Shared Blackboard Memory for Swarm Agents [P1] [MYT], A7 — Agent Self-Improvement Loop [P2] [HRM / AOS], SECTION A — Agent Efficiency (Hermes / AOS / MYT)

### Community 945 - "SECTION C — Direct Chat Improvements (CBF / HRM)"
Cohesion: 0.25
Nodes (8): C1 — Structured Output / JSON Mode [P0] [CBF / HRM], C2 — Function Calling / Tool Use (OpenAI-Compatible) [P0] [CBF / HRM], C3 — Streaming with Proper Delta Reconstruction [P1] [CBF], C4 — Chat History Persistence + Retrieval [P1] [AOS / HRM], C5 — Context Window Management + Smart Truncation [P1] [CBF / HRM], C6 — Prompt Caching (Anthropic-Compatible) [P1] [HRM], C7 — Embeddings Pipeline + Vector Search [P2] [AOS / CBF], SECTION C — Direct Chat Improvements (CBF / HRM)

### Community 946 - "Runbook — Instance Activation"
Cohesion: 0.25
Nodes (7): Option A — disable the gate (self-hosted), Option B — self-mint a signed code with your own key, Option C — request a code (downstream user), Runbook — Instance Activation, Security notes, TL;DR — you are blocked at the activation screen, Why activation exists

### Community 947 - "Continual Harness (`agent/harness_spec.py`)"
Cohesion: 0.25
Nodes (7): Configuration, Continual Harness (`agent/harness_spec.py`), Flow, Reviewing what it wrote, The two rules that keep it honest, Trying it, Where it lives

### Community 948 - "Prime Agent Runtime"
Cohesion: 0.25
Nodes (8): Configuration, Deploying on Render, Installation, Prime Agent Runtime, `PRIME_AGENT_TRUST_WORKSPACE`, Routing LLM traffic through our proxy, Verifying, What the adapter drives

### Community 949 - "PULL_REQUEST_TEMPLATE.md"
Cohesion: 0.25
Nodes (7): Changelog, Changes, Council Review (for larger PRs), Related, Risky Module Review, Summary, Testing

### Community 950 - "fetch_url.py"
Cohesion: 0.43
Nodes (7): extract_real_url(), fetch(), main(), meaningful(), Drop site navigation chrome and repeated nav blocks from stripped text. A fetch…, strip_boilerplate(), strip_html()

### Community 951 - "security_fix_agent.py"
Cohesion: 0.46
Nodes (7): codeql_count(), dependabot_count(), main(), Any, OpenClaw security fix helper. Lightweight CLI used by CI to check/fix…, _repo_parts(), _request()

### Community 953 - "Sol Advisor"
Cohesion: 0.25
Nodes (7): Go deeper, Quick start, Routes, Sol Advisor, Updating, What happens automatically, What you do

### Community 954 - "verify.sh"
Cohesion: 0.50
Nodes (6): fail(), pass(), verify.sh script, snapshot_files(), write_legacy_roles(), write_v050_roles()

### Community 955 - "Prompt Library"
Cohesion: 0.25
Nodes (8): Agents, Commands, How This Library Is Maintained, Philosophy, Prompt Library, Skills, Transparency, What Is This?

### Community 956 - "crispy_burn_in.py"
Cohesion: 0.36
Nodes (7): evaluate_burn_in(), fetch_status_json(), main(), Any, scripts/crispy_burn_in.py — Evaluate CRISPY burn-in criteria for promotion.…, Fetch /api/autonomy/status and return the parsed JSON., Evaluate the burn-in criteria against a ``crispy_run_history`` payload. Returns…

### Community 957 - "e2e_smoke.py"
Cohesion: 0.46
Nodes (6): _chat(), check(), _health(), _models(), Real-API end-to-end smoke test for a *running* LLM Relay instance. Unlike the…, _req()

### Community 958 - "run_patched_colibri.py"
Cohesion: 0.36
Nodes (7): _exit_watch_delay(), main(), _patched_popen(), scripts/run_patched_colibri.py Pre-launch wrapper for JustVugg/colibri…, Resolve the COLIBRI_PATCH_EXIT_WATCH delay in seconds, clamped to [0, 60].…, Intercept JustVugg Engine -> glm.exe Popen and forward outer argv. Upstream…, _resolve_target()

### Community 959 - "SessionMemory"
Cohesion: 0.25
Nodes (5): Any, Managed Agents Dreams — session memory and dream consolidation for managed…, An individual memory snapshot from an agent session., Record a new session memory for this agent., SessionMemory

### Community 960 - "_NoopStore"
Cohesion: 0.29
Nodes (4): _NoopStore, Any, List recent runs. When ``owner_id`` is provided, only runs stamped with that…, No-op checkpoint store when the real one is unavailable.

### Community 961 - "task_runner.py"
Cohesion: 0.29
Nodes (7): check_health(), Simple task runner for local-llm-server. Submit a task description and get…, Submit a task to the agent planner., Submit a simple task via the tasks API., Check if the proxy is running., submit_simple_task(), submit_task()

### Community 964 - "TestItIsNotBuiltForOneVendor"
Cohesion: 0.25
Nodes (4): The bug being fixed is single-provider hardcoding; the fix must not reintroduce…, The probe asks what exists; it must not tell. Checked against the real…, Whatever kinds the config can express, the probe must handle., TestItIsNotBuiltForOneVendor

### Community 965 - "test_compose_and_coordinate_api.py"
Cohesion: 0.36
Nodes (5): _auth_override(), AuthContext, test_coordinate_dependency_aware_tasks_block_missing_dependencies(), test_coordinate_dependency_aware_tasks_succeed_with_dependencies(), test_coordinate_legacy_workers_flow_remains_backward_compatible()

### Community 966 - "test_daily_automation_2026_07_09.py"
Cohesion: 0.25
Nodes (5): proxy_client(), Daily automation tests — 2026-07-09. Covers: 1. Agent time-awareness:…, Minimal proxy test client with a seeded API key via env var., Integration smoke test for POST /agent/budget/reset., TestBudgetResetEndpoint

### Community 967 - "test_generate_context_standing_instructions.py"
Cohesion: 0.32
Nodes (7): _load_module(), Regression test: autonomous issue-context generation must not truncate…, Sanity check on the fixture assumption this test relies on., §3 onward is architecture reference, not instruction — dropping it is what buys…, test_claude_md_has_the_carved_out_sections(), test_load_codebase_context_includes_rules_and_standing_instructions(), test_reference_sections_are_not_shipped()

### Community 968 - "test_local_brain_router_smoke.py"
Cohesion: 0.25
Nodes (7): Smoke test: backend/local_brain_router is mounted on the public FastAPI app.…, Importing backend.server.app must not raise AttributeError or NameError., The /api/local-brain/state GET route must be reachable via the FastAPI app.…, The local_brain_router symbol MUST be importable + prefixed correctly. Quick…, test_backend_server_app_loads_without_attributeerror(), test_local_brain_router_module_is_wired(), test_local_brain_state_route_is_mounted_on_public_app()

### Community 970 - "test_ping.py"
Cohesion: 0.39
Nodes (7): client(), TestClient, Tests for the /api/ping health endpoint (no auth required)., test_ping_no_auth_required(), test_ping_response_shape(), test_ping_returns_ok(), test_ping_timestamp_is_iso()

### Community 971 - "test_provider_models_db_outage.py"
Cohesion: 0.25
Nodes (7): tests/test_provider_models_db_outage.py — GET /api/providers/{id}/models…, A DB exception during the provider lookup must not surface as a 500., A catalog provider (unified BrainConfig) with no legacy `providers` row must…, A provider_id absent from both Mongo and the predefined catalog is a genuine…, test_provider_models_falls_back_on_db_outage(), test_provider_models_truly_unknown_provider_still_404s(), test_provider_models_unregistered_provider_uses_predefined_catalog()

### Community 972 - "test_runtimes_health_endpoint.py"
Cohesion: 0.25
Nodes (7): hermes_only_manager(), tests/test_runtimes_health_endpoint.py — N2 acceptance: GET /runtimes/health…, Build a RuntimeManager with only internal_agent + Hermes registered. Mirrors…, GET /runtimes/health must include a `hermes` entry when the adapter is…, End-to-end (router level): GET /runtimes/health returns JSON with a `health`…, test_runtimes_health_endpoint_returns_hermes_via_testclient(), test_runtimes_health_includes_hermes_entry()

### Community 973 - "test_seo_audit_pending_expiry.py"
Cohesion: 0.43
Nodes (7): _pending_started(), Regression tests for the SEO perpetual-pending guard. Background: when…, Reload backend.seo_api with a fresh expiry threshold (env-scoped)., _reload_with_expiry(), test_non_pending_status_is_never_expired(), test_pending_stub_older_than_threshold_is_auto_failed(), test_pending_stub_within_threshold_is_left_alone()

### Community 976 - "test_task_store_fails_loud_in_production.py"
Cohesion: 0.25
Nodes (7): fresh_store_module(), Regression: prevent silent TaskStore in-memory fallback in production. The…, Force a fresh import of tasks.store so module-level state is clean., With TESTING unset (production), TaskStore(db=None) MUST raise., With TESTING=true (CI), TaskStore(db=None) MUST allow in-memory fallback., test_task_store_allows_inmemory_when_testing(), test_task_store_raises_in_production()

### Community 977 - "dry_clone_repo"
Cohesion: 0.36
Nodes (5): test_dry_clone_repo_handles_missing_url(), test_dry_clone_repo_handles_subprocess_failure(), dry_clone_repo(), Validate repository access by performing a shallow, no-checkout git clone and…, Attempt a shallow, non-checkout clone into a temporary directory to validate…

### Community 978 - "TOOLS.md — Available Tools for AI Agents"
Cohesion: 0.25
Nodes (7): AI Runner Tools, API Endpoints (when proxy is running), File Tools, OpenClaw Integration, Shell / Process Tools, Skills (invoke via CLAUDE.md instructions), TOOLS.md — Available Tools for AI Agents

### Community 979 - "CLAUDE.md — agent/"
Cohesion: 0.29
Nodes (6): Adding a new tool, CLAUDE.md — agent/, Security surface, Skills worth invoking here, Testing, What this package does

### Community 980 - "SamConversation"
Cohesion: 0.29
Nodes (6): A single voice conversation session with SAM., SamConversation, add_turn must append to history and increment command_count., History must be capped at 20 entries (10 turns)., test_conversation_add_turn(), test_conversation_history_capped()

### Community 982 - "Full-Output Enforcement"
Cohesion: 0.29
Nodes (6): Banned Output Patterns, Baseline, Execution Process, Full-Output Enforcement, Handling Long Outputs, Quick Check

### Community 983 - "summarise.sh"
Cohesion: 0.48
Nodes (5): bottom(), divider(), row(), summarise.sh script, top()

### Community 984 - "updater.py"
Cohesion: 0.43
Nodes (6): _extract_unreleased_body(), _insert(), main(), Insert the Maintenance changelog section at the end of the [Unreleased] block.…, Return (body_start, body_end_exclusive, body) for the [Unreleased] block., _read_template()

### Community 985 - "ModelRegistry"
Cohesion: 0.29
Nodes (4): ModelRegistry, A centralized registry for available LLM models and their metadata. This class…, Returns a list of all registered models metadata., Retrieves a specific model's metadata by its name (case-insensitive). Returns…

### Community 986 - "Changelog"
Cohesion: 0.29
Nodes (6): Added, Changed, Changelog, Fixed, Maintenance, [v4.1.0]

### Community 987 - "[5.0.0]"
Cohesion: 0.29
Nodes (7): [5.0.0], Added, Changed, Fixed, Maintenance, Removed, Security

### Community 988 - "Changelog"
Cohesion: 0.29
Nodes (7): Added, Changed, Changelog, Fixed, Maintenance, Removed, Security

### Community 989 - "AI Engineering Insights Skill"
Cohesion: 0.29
Nodes (6): AI Engineering Insights Skill, Integration Points, Key Design Choices, Module: `agents/ai_insights.py`, References, What's Unique About the DX Report

### Community 990 - "Skill: hybrid-reasoning (Hybrid AI)"
Cohesion: 0.29
Nodes (6): Branch, Components, Purpose, Quick Start, Skill: hybrid-reasoning (Hybrid AI), Testing

### Community 991 - "Karpathy Guidelines Skill"
Cohesion: 0.29
Nodes (6): 1. Think Before Coding, 2. Simplicity First, 3. Surgical Changes, 4. Goal-Driven Execution, Integration points in this repo, Karpathy Guidelines Skill

### Community 992 - "Skill: Managed Agents Dreams"
Cohesion: 0.29
Nodes (6): Key Classes, Purpose, Related Issues, Skill: Managed Agents Dreams, Testing, Usage

### Community 993 - "Skill: Multi-Agent Coordinator"
Cohesion: 0.29
Nodes (6): Key Classes, Purpose, Related Issues, Skill: Multi-Agent Coordinator, Testing, Usage

### Community 994 - "Skill: Obsidian Knowledge Graph"
Cohesion: 0.29
Nodes (6): Key Classes, Purpose, Related Issues, Skill: Obsidian Knowledge Graph, Testing, Usage

### Community 995 - "Multi-Agent Research Coordinator Skill"
Cohesion: 0.29
Nodes (6): Default Plan Shape, Module: `agents/research_coordinator.py`, Multi-Agent Research Coordinator Skill, Quick-Note Issue: #238, Roles, What's Unique

### Community 996 - "Skill: SuperClaude Slash Commands"
Cohesion: 0.29
Nodes (6): Key Classes, Purpose, Related Issues, Skill: SuperClaude Slash Commands, Testing, Usage

### Community 997 - "Skill: SuperClaude Workflow Engine"
Cohesion: 0.29
Nodes (6): Key Classes, Purpose, Related Issues, Skill: SuperClaude Workflow Engine, Testing, Usage

### Community 998 - "_AllSignatures"
Cohesion: 0.29
Nodes (5): dict, set, _AllSignatures, _AnyText, A mapping that accepts any entry text for any signature.

### Community 999 - "ADR-006: Strangler Fig migration with backward-compat shims"
Cohesion: 0.29
Nodes (6): ADR-006: Strangler Fig migration with backward-compat shims, Consequences, Context, Decision, Examples, Migration path

### Community 1000 - "Changelog"
Cohesion: 0.29
Nodes (6): Added, Changed, Changelog, Fixed, Maintenance, [v4.1.0]

### Community 1001 - "[5.0.0]"
Cohesion: 0.29
Nodes (7): [5.0.0], Added, Changed, Fixed, Maintenance, Removed, Security

### Community 1002 - "Changelog"
Cohesion: 0.29
Nodes (7): Added, Changed, Changelog, Fixed, Maintenance, Removed, Security

### Community 1003 - "claude-mem Plugin — Persistent Memory for All Sessions"
Cohesion: 0.29
Nodes (6): claude-mem Plugin — Persistent Memory for All Sessions, Enabling it elsewhere, How it's wired, Notes, Scope and limits, Why the source is pinned (`ref` + `sha`)

### Community 1004 - "Implementation plan + TO-DO (check off as you go)"
Cohesion: 0.29
Nodes (7): Implementation plan + TO-DO (check off as you go), Phase 1 — Stop the bleeding + paid kill switch (do first, ship alone if needed), Phase 2 — Per-surface assignment in the UI (the "one place"), Phase 3 — Persistence hardening (issues #537, #524), Phase 4 — Onboarding fixes (issues #593, #619; PR #623), Phase 5 — Reliability for hands-off autonomy (issue #522) [larger; may split to own PR], Phase 6 — Green the tests + housekeeping

### Community 1005 - "Topics Covered"
Cohesion: 0.29
Nodes (7): 1. Architecture, 2. Tokenization, 3. Training, 4. Inference, 5. Embeddings, LLM Internals, Topics Covered

### Community 1006 - "LLM Router — migration guide"
Cohesion: 0.29
Nodes (7): Adding the config files, Gateway mode, LLM Router — migration guide, Migrating a caller to the router directly, Rollback checklist, What changes for callers, What is not migrated

### Community 1007 - "What's New"
Cohesion: 0.29
Nodes (7): 2026-06-16, 2026-06-25, 2026-06-26, 2026-07-04, 2026-07-05, 2026-07-09, What's New

### Community 1008 - "Cloudflare = the real working app"
Cohesion: 0.29
Nodes (6): Backend (Render), Cloudflare dashboard settings to verify, Cloudflare = the real working app, How it works, Notes, Verify after deploy

### Community 1009 - "Workspace Issues"
Cohesion: 0.29
Nodes (7): "Invalid session ID" or "Invalid job ID" error, "Workspace cleanup blocked" error, Workspace Issues, "Workspace manifest corrupt" error, "Workspace not found" error, "Workspace not resumable" error, "Workspace outside root" error

### Community 1010 - "Model and Response Issues"
Cohesion: 0.29
Nodes (7): Model and Response Issues, Model eviction between requests, "Model not found" or 404 on model requests, Responses are empty or very short, Responses get cut off mid-sentence, `<think>...</think>` appears in responses, Very slow first response (30–90 seconds)

### Community 1011 - "Cost-aware routing evaluation"
Cohesion: 0.29
Nodes (6): Caveats, CLI, Cost-aware routing evaluation, How the metric resists gaming, Method, What's here

### Community 1012 - "GitHubScreen"
Cohesion: 0.33
Nodes (6): deleteGithubToken(), githubStatus(), listGithubRepos(), errText(), GitHubScreen(), GitHubScreen

### Community 1013 - "launch-claude-code.sh"
Cohesion: 0.43
Nodes (6): ANTHROPIC_API_KEY, ANTHROPIC_MODEL, log_error(), log_header(), log_success(), launch-claude-code.sh script

### Community 1015 - "PRD — README Marketing Refresh"
Cohesion: 0.29
Nodes (6): Backlog / Nice-to-Have, Files Touched, Original Problem Statement, PRD — README Marketing Refresh, User Decisions, What Was Done — 2026-04-27

### Community 1016 - "CLAUDE.md — router/"
Cohesion: 0.29
Nodes (6): Adding a model, Adding a task category, CLAUDE.md — router/, Environment variables, Testing, What this package does

### Community 1017 - "_replace"
Cohesion: 0.33
Nodes (6): main(), Path, Bump the application version in every place that hardcodes it. Usage: python…, Regex-replace ``pattern`` with ``repl`` in ``path``; return the match count., Bump the version across all version-bearing files; fail fast if any are missed., _replace()

### Community 1018 - "check_changelog_parity.py"
Cohesion: 0.43
Nodes (6): _blocks(), main(), normalize_text(), scripts/check_changelog_parity.py CI guard for the changelog mirror. Closes the…, Return a list of human-readable corruption issues in *content*. Detects (1) git…, scan_corruption()

### Community 1019 - "check_doc_images.py"
Cohesion: 0.48
Nodes (6): check_broken_links(), check_gallery_sync(), find_duplicate_images(), _local_refs(), main(), Validate documentation image references and README gallery freshness. Guards…

### Community 1020 - "client"
Cohesion: 0.29
Nodes (7): auth_headers(), client(), TestClient, TestClient for the backend FastAPI app (one per module for speed)., Login once and return auth headers for the entire module., admin_jwt(), Module-scoped so we log in once and reuse the JWT across the test.

### Community 1021 - "TestDashboard"
Cohesion: 0.29
Nodes (4): Run fn() and report any critical console errors., Dashboard page — stats, activity, navigation., TestDashboard, with_console_check()

### Community 1022 - "test_daily_2026_06_14.py"
Cohesion: 0.38
Nodes (6): Regression tests for daily-2026-06-14 improvements. Anthropic retires the…, ci-failure-autofix.yml must call the Anthropic API with claude-sonnet-4-6, as…, No GitHub Actions workflow or CI script should reference a retired Claude 4…, _read(), test_ci_autofix_workflow_uses_sonnet_4_6(), test_no_retired_claude_4_model_ids_in_workflows_or_scripts()

### Community 1023 - "TestSupportMatrixDocsSync"
Cohesion: 0.29
Nodes (4): The feature matrix can produce a markdown table for docs., Every config flag referenced in the matrix should be documented., The matrix should cover the key areas from the spec., TestSupportMatrixDocsSync

### Community 1024 - "test_doctor_coding_brain.py"
Cohesion: 0.38
Nodes (6): client(), _coding_brain_check(), tests/test_doctor_coding_brain.py Surfaces the North Mini Code coding-brain…, With NORTH_MINI_CODE_DEFAULT off, the check warns and says so., test_coding_brain_check_reflects_flag_off(), test_doctor_includes_coding_brain_check()

### Community 1025 - "TestGithubTokenSQLiteRegression"
Cohesion: 0.38
Nodes (4): MonkeyPatch, TestClient, Regression test for PUT/DELETE /api/github/token returning 500 for SQLite-…, TestGithubTokenSQLiteRegression

### Community 1026 - "TestReasonsAreActionable"
Cohesion: 0.29
Nodes (4): X is not set' leaves the operator to go find out what to do., Red is reserved for real faults., A backend-served server reads as healthy, not as a warning., TestReasonsAreActionable

### Community 1027 - "TestProvidersScreen"
Cohesion: 0.43
Nodes (3): The four invented 'connected' entries must not come back. Asserts on the…, No seeding on an empty response — that is what made the page lie., TestProvidersScreen

### Community 1028 - "TestCli"
Cohesion: 0.57
Nodes (3): Path, The workflows call this as a subprocess, so the CLI contract matters., TestCli

### Community 1030 - "TestActiveStrategy"
Cohesion: 0.29
Nodes (3): parametrize, A typo must not silently pick some other distribution., TestActiveStrategy

### Community 1031 - "InitiativeProgress"
Cohesion: 0.33
Nodes (4): InitiativeProgress, Delivery roll-up for a single initiative across its linked sprints., Percentage of linked sprint points completed., Aggregate delivery progress per initiative from its linked sprints. Reads each…

### Community 1032 - "_brain_provider_status"
Cohesion: 0.33
Nodes (6): _brain_provider_status(), Return per-provider metadata for the GET endpoint. Iterates every provider in…, Return the discovered model list for *provider_id*, or ``[]`` if unknown., _served_models(), cached_models(), Return the cached list for *provider_id* without any network call. The…

### Community 1033 - "brain_providers"
Cohesion: 0.33
Nodes (6): brain_providers(), Every configured provider with its health AND its on/off state. Powers the…, describe_disabled_reason(), True when operator state is stored somewhere that survives a redeploy. False…, Render a stored disable reason for display. Returns ``code`` (the HTTP status…, state_is_durable()

### Community 1034 - "openclaw_mobile_ui"
Cohesion: 0.33
Nodes (5): openclaw_mobile_ui(), Mobile web UI for iOS control of the agency. Open this on your iPhone, tap…, get_mobile_html(), services/openclaw_mobile.py — Mobile web UI for iOS control of the agency.…, Return the mobile web UI HTML.

### Community 1035 - "/fix-bug — Bug Fix Agent"
Cohesion: 0.33
Nodes (5): Escalation, /fix-bug — Bug Fix Agent, Process, Rules, Usage

### Community 1036 - "Command: /plan"
Cohesion: 0.33
Nodes (5): Command: /plan, References, Usage, What It Does, When to Use

### Community 1037 - "pre-commit"
Cohesion: 0.60
Nodes (5): pre-commit script, _error(), _head(), _info(), _warn()

### Community 1038 - "Skill: browserbase-fetch — Lightweight Web Fetch"
Cohesion: 0.33
Nodes (5): Checking the platform health, Python snippet, Setup, Skill: browserbase-fetch — Lightweight Web Fetch, When to use vs browser

### Community 1039 - "Twitter Insights — Issue #228"
Cohesion: 0.33
Nodes (5): Action Items, Key Observations, References, Summary, Twitter Insights — Issue #228

### Community 1040 - "Twitter Insights — Issue #231"
Cohesion: 0.33
Nodes (5): Action Items, Key Observations, References, Summary, Twitter Insights — Issue #231

### Community 1041 - "OpenAI Codex CLI — Local LLM Server Config"
Cohesion: 0.33
Nodes (5): Codex Config File (`~/.codex/config.yaml`), Notes, OpenAI Codex CLI — Local LLM Server Config, Recommended Models, Setup

### Community 1042 - "ADR-001: Adopt packages/ directory structure"
Cohesion: 0.33
Nodes (5): ADR-001: Adopt packages/ directory structure, Consequences, Context, Decision, Status

### Community 1043 - "ADR-002: Centralize configuration in packages/config/"
Cohesion: 0.33
Nodes (5): ADR-002: Centralize configuration in packages/config/, Consequences, Context, Decision, Status

### Community 1044 - "ADR-003: Provider abstraction with unified interface"
Cohesion: 0.33
Nodes (5): ADR-003: Provider abstraction with unified interface, Consequences, Context, Decision, Status

### Community 1045 - "ADR-004: Event bus for loosely coupled communication"
Cohesion: 0.33
Nodes (5): ADR-004: Event bus for loosely coupled communication, Consequences, Context, Decision, Status

### Community 1046 - "ADR-005: Merge Hermes into the main backend service"
Cohesion: 0.33
Nodes (5): ADR-005: Merge Hermes into the main backend service, Consequences, Context, Decision, Status

### Community 1047 - "ADR-007: Storage backend duck-typing over formal ABC"
Cohesion: 0.33
Nodes (5): ADR-007: Storage backend duck-typing over formal ABC, Consequences, Context, Decision, Rationale

### Community 1048 - "Phases"
Cohesion: 0.33
Nodes (6): Phase 0 — `RepoConnection` plumbing + delivery-policy detection, Phase 1 — Plan-PR → Implementation  *(highest leverage; closes the live gap)*, Phase 2 — Review-comment resolution (Codex / CodeRabbit), Phase 3 — Quality gate + policy-conformant landing, Phase 4 — Monitor & regression guard, Phases

### Community 1049 - "5. The five autonomous loops"
Cohesion: 0.33
Nodes (6): 5. The five autonomous loops, Loop 1 — Self-heal from logs *(closed loop)*, Loop 2 — Feature generation, Loop 3 — Agentic SDLC (the golden path), Loop 4 — Trends contextually applied, Loop 5 — Per-onboarded-site autonomy

### Community 1050 - "Master Goal Prompt — Autonomous Agency CEO"
Cohesion: 0.33
Nodes (6): Cadence & stop conditions, First-run bootstrap, Hard constraints, Master Goal Prompt — Autonomous Agency CEO, Mission, The gate contract (Telegram human-in-the-loop)

### Community 1051 - "Agency Core — Operational Knowledge (verified live, 2026-06-10/11)"
Cohesion: 0.33
Nodes (5): Agency Core — Operational Knowledge (verified live, 2026-06-10/11), Architecture truths, Open backlog (epic #504), Pros of linking the GitHub repo (vs running unlinked), Runbooks

### Community 1052 - "The full agent capability roster"
Cohesion: 0.33
Nodes (6): Agile, portfolio & product, Business & domain specialists (auto-provisioned from the URL scan), Content & knowledge, Engineering, Operations & DevOps, The full agent capability roster

### Community 1053 - "Pre-Mortem Analysis: Agency Core autonomy story (Cloudflare deployment)"
Cohesion: 0.33
Nodes (5): Elephants, named, Pre-Mortem Analysis: Agency Core autonomy story (Cloudflare deployment), Risk Registry, Summary, What was already fixed during this pre-mortem

### Community 1054 - "SECTION B — NVIDIA / Cloud Model Integration (Nemotron / NVD)"
Cohesion: 0.33
Nodes (6): B1 — Nemotron Reward Model for Agent Step Scoring [P0] [NVD], B2 — SteerLM / RLHF-Style Steering for Local Models [P1] [NVD], B3 — Synthetic Training Data Generation Pipeline [P1] [NVD], B4 — NeMo Guardrails Integration [P1] [NVD], B5 — NIM API Connection Pooling + Circuit Breaker [P1] [NVD], SECTION B — NVIDIA / Cloud Model Integration (Nemotron / NVD)

### Community 1055 - "SECTION D — Deployment & Infrastructure (CHM / NVD)"
Cohesion: 0.33
Nodes (6): D1 — Helm Chart for Kubernetes Deployment [P1] [CHM], D2 — Docker Compose Production Stack [P1] [CHM], D3 — OpenTelemetry Distributed Tracing [P1] [NVD / CHM], D4 — Horizontal Scaling with Redis State Backend [P2] [CHM / AOS], D5 — Model Auto-Management (Pull, Warm, Evict) [P2] [NVD], SECTION D — Deployment & Infrastructure (CHM / NVD)

### Community 1056 - "Feature Support Matrix"
Cohesion: 0.33
Nodes (6): Admin API, Config Overrides, Feature Matrix, Feature Support Matrix, Gating Behavior, Maturity Tiers

### Community 1057 - "Startup Issues"
Cohesion: 0.33
Nodes (6): Cloudflare tunnel fails to start, Frontend dev server fails to start (Node 22+), Ollama fails to start, Proxy fails to start, Server starts but backend doesn't respond on port 8000, Startup Issues

### Community 1058 - "StatusPill.jsx"
Cohesion: 0.47
Nodes (5): C, STATUS_META, StatusPill(), TONE_BG(), TONE_BORDER()

### Community 1059 - "scripts/agile_ceremonies.py"
Cohesion: 0.47
Nodes (5): _load(), main(), ModuleType, Scheduled agile ceremonies digest. Run by `.github/workflows/agile-…, _write_summary()

### Community 1060 - "get_control"
Cohesion: 0.33
Nodes (6): get_control(), The spec for *key*, or ``None`` when it is not operator-controllable., The call-volume throttle is present, numeric, and defaults to the calmer free-…, A runtime an operator cannot pick from the dropdown is unreachable., test_agency_tick_minutes_throttle_exists(), test_runtime_choices_cover_every_registered_adapter_id()

### Community 1061 - "apply_phase1_changes.py"
Cohesion: 0.33
Nodes (5): apply_backend_change(), apply_workflow_change(), Apply Phase 1 paid-provider kill switch changes to backend/server.py and…, Insert provider policy endpoints before @app.get('/api/models/catalog')., Modify _resolve_brain_provider to read allow_paid from the durable policy.

### Community 1062 - "gen_screenshots.py"
Cohesion: 0.47
Nodes (5): main(), out_path(), Path, Generate Langfuse and Telegram mockup screenshots for documentation., save_html_screenshot()

### Community 1063 - "gen_v4_screenshots.py"
Cohesion: 0.60
Nodes (5): build_screens(), page(), Generate v4 UI screenshots for the README using HTML mockups + system…, shot(), sidebar()

### Community 1064 - "parse_pytest_failures.py"
Cohesion: 0.40
Nodes (5): main(), scripts/parse_pytest_failures.py Extract failing test node IDs from a pytest…, Return the lines at or after pytest's first summary banner. Falls back to the…, _read(), _summary_region()

### Community 1065 - "reset_kv_state"
Cohesion: 0.33
Nodes (6): Drop the cached Mongo client, backoff, and read caches (tests)., reset_kv_state(), one_configured_provider(), A registry with exactly two known providers and isolated state., isolated_state(), Temp SQLite mirror + clean caches, so no test sees another's state.

### Community 1067 - "setup-claude-code.sh script"
Cohesion: 0.60
Nodes (5): log_error(), log_info(), log_success(), print_header(), setup-claude-code.sh script

### Community 1071 - "TestCli"
Cohesion: 0.47
Nodes (4): parametrize, Path, The workflow branches on the verdict file, so that contract matters., TestCli

### Community 1072 - "TestAgentRunnerExecution"
Cohesion: 0.33
Nodes (4): Verify AgentRunner has _execute_step for ReAct execution loop., Verify _BYPASS context var is used for internal agent execution., Tests for AgentRunner execution path., TestAgentRunnerExecution

### Community 1073 - "TestDirectChatAgentExecution"
Cohesion: 0.33
Nodes (4): Tests for direct chat agent execution beyond planning., Verify ChatSendRequest supports agent mode execution., Verify WorkspaceTools provides filesystem operations for agents., TestDirectChatAgentExecution

### Community 1074 - "TestDisabledProvidersAreNotFalselyReportedUnreachable"
Cohesion: 0.33
Nodes (3): Local providers (ollama, lmstudio, vllm, localai) default to a localhost…, ``gh workflow run ... -f provider=ollama`` must still work: an operator…, TestDisabledProvidersAreNotFalselyReportedUnreachable

### Community 1075 - "_auth_headers"
Cohesion: 0.73
Nodes (5): _auth_headers(), TestClient, test_agent_profile_api_preserves_ui_fields(), test_backend_server_exposes_observability_savings_and_usage(), test_backend_server_exposes_schedules_routes()

### Community 1076 - "TestNoHardcodedModels"
Cohesion: 0.33
Nodes (3): parametrize, The regression itself: a model id baked into this script., TestNoHardcodedModels

### Community 1078 - ".update_status"
Cohesion: 0.33
Nodes (4): _now(), WorkspaceStatusLiteral, Transition to a new status and update cleanup eligibility., Touch the last_heartbeat timestamp.

### Community 1079 - "harness.py"
Cohesion: 0.40
Nodes (3): EvalResult, Evaluation harness – runs an agent against a Task, records the Trajectory,…, Outcome of running one task through the harness.

### Community 1081 - "feature-implementer.md"
Cohesion: 0.40
Nodes (4): Before you edit, Prove it, Report back, While you edit

### Community 1082 - "/arch-review — Architecture Agent"
Cohesion: 0.40
Nodes (4): /arch-review — Architecture Agent, Key Architectural Principles, Steps, When to use

### Community 1083 - "/devops-check — DevOps Agent"
Cohesion: 0.40
Nodes (4): Deployment Checklist, /devops-check — DevOps Agent, Steps, When to use

### Community 1084 - "/docs-update — Documentation Agent"
Cohesion: 0.40
Nodes (4): /docs-update — Documentation Agent, Documentation Standards, Steps, When to use

### Community 1085 - "/qa-check — QA Agent"
Cohesion: 0.40
Nodes (4): /qa-check — QA Agent, Steps, What NOT to do, When to use

### Community 1086 - "Command: /review"
Cohesion: 0.40
Nodes (4): Command: /review, References, Usage, What It Does

### Community 1087 - "/security-audit — Security Agent"
Cohesion: 0.40
Nodes (4): Escalation, /security-audit — Security Agent, Steps, When to use

### Community 1088 - "pre-push"
Cohesion: 0.70
Nodes (4): pre-push script, _error(), _head(), _info()

### Community 1089 - "Skill: browserbase-search — Structured Web Search"
Cohesion: 0.40
Nodes (4): Best practice: search → fetch → browse, Python snippet, Setup, Skill: browserbase-search — Structured Web Search

### Community 1090 - "Issue #230 — DUPLICATE"
Cohesion: 0.40
Nodes (4): Actions Taken, Issue #230 — DUPLICATE, References, Resolution

### Community 1092 - "Agent job lifecycle"
Cohesion: 0.40
Nodes (4): Agent job lifecycle, API, Progress phases, States

### Community 1093 - "Docker (local or any container host)"
Cohesion: 0.40
Nodes (4): Build, Docker (local or any container host), Provider configuration (recommended for cloud), Run (minimal)

### Community 1094 - "Rollout"
Cohesion: 0.40
Nodes (5): 1. Verify the router sees your providers, 2. Enable on one instance, 3. Watch for a few hours, 4. Roll out or roll back, Rollout

### Community 1095 - "Who is this for?"
Cohesion: 0.40
Nodes (5): The 5-person SaaS startup that can't afford a full team yet, The digital agency running 10 client accounts, The e-commerce shop with a 10-person ops team, The professional services firm that runs on documents and tribal knowledge, Who is this for?

### Community 1096 - "SECTION E — Autonomy & Self-Healing (AOS / MYT / ECC)"
Cohesion: 0.40
Nodes (5): E1 — Cross-Harness Routing (ECC Pattern) [P1] [ECC], E2 — Self-Healing Agent Loop (Detect + Repair Own Failures) [P1] [AOS / MYT], E3 — Autonomous Monitoring with Trend Watcher [P2] [AOS], E4 — Nightly Self-Evaluation + Regression Tests [P2] [HRM / AOS], SECTION E — Autonomy & Self-Healing (AOS / MYT / ECC)

### Community 1097 - "SECTION F — Developer Experience (CBF / ECC)"
Cohesion: 0.40
Nodes (5): F1 — Codebuff-Style Precise Diff Application [P0] [CBF], F2 — MCP Server Exposing Proxy Capabilities [P1] [CBF / ECC], F3 — Local Dev Dashboard with Live Metrics [P2] [CBF / CHM], F4 — SDK / Client Library Generation [P2] [CBF], SECTION F — Developer Experience (CBF / ECC)

### Community 1098 - "Runtime troubleshooting"
Cohesion: 0.40
Nodes (4): Agent mode timeout, Missing binary / task harness, Runtime troubleshooting, Workspace validation failures

### Community 1099 - "Admin Dashboard Issues"
Cohesion: 0.40
Nodes (5): Admin Dashboard Issues, Dashboard shows "KEYS_FILE not configured", New key flash banner not appearing after key creation, "Stop stack" disconnects me from the dashboard, Windows auth login fails

### Community 1100 - "Agent API Issues"
Cohesion: 0.40
Nodes (5): Agent API Issues, Agent makes a change but doesn't verify correctly, Agent returns empty or incomplete plan, Agent workspace errors ("file not found"), Rollback command fails

### Community 1101 - "Network and Tunnel Issues"
Cohesion: 0.40
Nodes (5): Can't find current tunnel URL, High latency from remote clients, Network and Tunnel Issues, Remote client gets "SSL certificate error", Tunnel URL changes on every restart

### Community 1102 - "knowledgeGraphTab.test.js"
Cohesion: 0.40
Nodes (4): { describe, test, expect }, fs, path, src

### Community 1103 - "loginFlowNoTimeout.test.js"
Cohesion: 0.40
Nodes (4): apiSource, { describe, test, expect }, fs, path

### Community 1104 - "test_company_stale_id_recovery.test.js"
Cohesion: 0.40
Nodes (4): { describe, test, expect }, fs, path, src

### Community 1105 - "worker_no_cache.test.js"
Cohesion: 0.40
Nodes (4): { describe, test, expect }, fs, path, workerSource

### Community 1106 - ".chat"
Cohesion: 0.40
Nodes (3): Any, Send a chat completion request., Stream a chat completion response.

### Community 1107 - "governance/__init__.py"
Cohesion: 0.40
Nodes (3): __getattr__(), Any, packages/governance — agent identity, policy, approvals, audit, sandboxes. The…

### Community 1108 - "inspect-agent-runtime.sh"
Cohesion: 0.60
Nodes (3): fail(), inspect-agent-runtime.sh script, usage()

### Community 1109 - "Prompt Library Changelog"
Cohesion: 0.40
Nodes (4): Added, Format, Prompt Library Changelog, [Unreleased]

### Community 1110 - "_add_colibri_shim_changelog_entry.py"
Cohesion: 0.50
Nodes (4): main(), _normalise_crlf(), Insert a single new [Unreleased] / ### Added bullet into BOTH changelogs.…, Force LF on write (parity script tolerates either, but a stray CRLF introduced…

### Community 1111 - "build_llama_cpp.ps1"
Cohesion: 0.70
Nodes (4): Fail(), Ok(), W(), Warn()

### Community 1112 - "download_glm52_weights.ps1"
Cohesion: 0.70
Nodes (4): Fail(), Ok(), Warn(), W()

### Community 1113 - "download_glm52_weights.sh script"
Cohesion: 0.70
Nodes (4): download_glm52_weights.sh script, fail(), ok(), warn()

### Community 1114 - "_fetch_pytest_failures.py"
Cohesion: 0.50
Nodes (4): _gh_json(), main(), Pull the python-test failure log via gh run view --log and print the failing-…, Run a gh CLI call and parse its JSON stdout. Returns (parsed | None, stderr).

### Community 1115 - "setup_colibri.ps1"
Cohesion: 0.70
Nodes (4): Fail(), Ok(), Warn(), W()

### Community 1116 - "setup_colibri.sh script"
Cohesion: 0.70
Nodes (4): setup_colibri.sh script, fail(), ok(), warn()

### Community 1117 - "status_colibri_server.ps1"
Cohesion: 0.70
Nodes (4): Fail(), Ok(), W(), Warn()

### Community 1118 - "._resolve_merge_decision"
Cohesion: 0.40
Nodes (3): MergeDecision, G5: resolve how a run should land from the company's DeliveryPolicy. Returns…, G5: how a completed run should land, derived from the company's DeliveryPolicy.…

### Community 1119 - "start_tunnel.py"
Cohesion: 0.50
Nodes (4): check_services(), main(), Start an ngrok tunnel for the Autonomous AI Agency with public access. Requires…, Check if local services are running. Extends the original (proxy + Ollama)…

### Community 1121 - "TestMobileNavigation"
Cohesion: 0.40
Nodes (3): Mobile-specific: hamburger menu, responsive layout., Verify key pages load in mobile viewport., TestMobileNavigation

### Community 1122 - "test_v5_screens_smoke.py"
Cohesion: 0.50
Nodes (3): _login(), E2E UI smoke test: every v5 screen renders without errors. This is the…, test_every_v5_screen_renders_without_errors()

### Community 1123 - "nvidia_live_test.py"
Cohesion: 0.40
Nodes (3): pytest guard: this file is a standalone script, not a pytest test. Collection…, Live-test each NVIDIA NIM model candidate for availability and function…, test_nvidia_live_is_standalone_script()

### Community 1125 - "test_agent_runtime_wrapper.py"
Cohesion: 0.70
Nodes (4): _load_agent_runtime_module(), test_wrapper_exposes_hermes_task_endpoints(), test_wrapper_exposes_opencode_run_endpoint(), test_wrapper_falls_back_to_installed_model()

### Community 1127 - "TestNoKeyEverReachesTheLog"
Cohesion: 0.40
Nodes (3): Rule 6: secrets are never logged, not even partially., Error paths print exception text — that must not carry the key., TestNoKeyEverReachesTheLog

### Community 1128 - "TestTheProbeIdentifiesItself"
Cohesion: 0.40
Nodes (3): ``urllib``'s default User-Agent is a 403 waiting to happen. Unset, every…, ``extra_headers`` is applied last, so a provider stays in control., TestTheProbeIdentifiesItself

### Community 1129 - "TestModelRoleSeparation"
Cohesion: 0.40
Nodes (3): Module-level defaults must be read from AGENT_*_MODEL env vars. These defaults…, All three model role env vars must be recognised by loop.py., TestModelRoleSeparation

### Community 1130 - "worker/index.js"
Cohesion: 0.60
Nodes (4): fetch(), needsProxy(), PROXY_PREFIXES, scheduled()

### Community 1131 - "gather_render_evidence"
Cohesion: 0.50
Nodes (4): gather_render_evidence(), Pull recent Render logs and summarise them for the issue body. This is the…, No RENDER_API_KEY must still file the incident — the recurrence itself is the…, test_evidence_reports_unavailable_when_render_is_not_configured()

### Community 1132 - "_clean_phases"
Cohesion: 0.50
Nodes (4): Drop all open-phase state. Used by tests., reset_phase_tracking(), _clean_phases(), Phase state is module-global — keep tests from leaking into each other.

### Community 1133 - "recovery.py"
Cohesion: 0.67
Nodes (3): detect_secrets(), main(), Recover CHANGELOG.md from a Git merge conflict in its [Unreleased] block. Pre-…

### Community 1134 - "test_activity_logs.py"
Cohesion: 0.67
Nodes (3): clear_error_log_buffer(), _auth_headers(), test_activity_endpoint_includes_recent_error_logs()

### Community 1135 - "_InMemoryErrorLogHandler"
Cohesion: 0.50
Nodes (3): _ensure_error_log_capture(), _InMemoryErrorLogHandler, LogRecord

### Community 1136 - "codebase-explorer.md"
Cohesion: 0.50
Nodes (3): Hard constraints, Method, Output

### Community 1137 - "docs-auditor.md"
Cohesion: 0.50
Nodes (3): Hard constraints, Output, What to check

### Community 1138 - "risk-reviewer.md"
Cohesion: 0.50
Nodes (3): Output, Rules of evidence, What you weigh

### Community 1139 - "verification-reviewer.md"
Cohesion: 0.50
Nodes (3): Output, Rules of evidence, What you evaluate

### Community 1140 - "aider_config.sh"
Cohesion: 0.50
Nodes (3): OPENAI_API_BASE, OPENAI_API_KEY, aider_config.sh script

### Community 1143 - "providers.yaml"
Cohesion: 0.50
Nodes (4): Bulkhead sizing, Per-minute token budgets, providers.yaml, Tiers

### Community 1144 - "Issue → Context → Draft PR automation"
Cohesion: 0.50
Nodes (4): Backfilling existing issues, Free-first model routing, Issue → Context → Draft PR automation, The workflows

### Community 1145 - "The 24x7 agency — your agents never go idle"
Cohesion: 0.50
Nodes (4): Nothing goes down quietly, The 24x7 agency — your agents never go idle, What runs automatically after onboarding, When something goes wrong, agents fix it — not you

### Community 1146 - "Privacy, security, and cost"
Cohesion: 0.50
Nodes (4): Privacy, security, and cost, Security posture, What it costs to run, Your data never leaves your server

### Community 1147 - "Credential Rotation Runbook"
Cohesion: 0.50
Nodes (3): Credential Rotation Runbook, Guardrails already in place, What to rotate (owner action, ~10 minutes)

### Community 1148 - "Runbook: `make doctor`"
Cohesion: 0.50
Nodes (3): Roadmap, Runbook: `make doctor`, What it checks and why

### Community 1149 - "Authentication Issues"
Cohesion: 0.50
Nodes (4): 401 Unauthorized, 403 Forbidden from remote machine, 429 Too Many Requests, Authentication Issues

### Community 1150 - "Feature Maturity Issues"
Cohesion: 0.50
Nodes (4): Beta/experimental warning in API response, Feature Maturity Issues, Feature not appearing in admin UI, "Feature unavailable" error

### Community 1151 - "Claude Code Specific Issues"
Cohesion: 0.50
Nodes (4): Claude Code sends requests but gets no useful response, Claude Code shows model as "claude-sonnet-4-6" but proxy logs show wrong model, Claude Code Specific Issues, "Context length exceeded" in Claude Code

### Community 1152 - "Langfuse Issues"
Cohesion: 0.50
Nodes (4): Langfuse Issues, Langfuse shows "cost" as $0, No traces appearing in Langfuse, Traces appear but metadata is missing

### Community 1153 - "Runtime & Onboarding Issues"
Cohesion: 0.50
Nodes (4): Onboarding endpoints crash with 500, Runtime endpoints return 500 errors (decisions, health, policy), Runtime & Onboarding Issues, Website scan returns "No systems detected" for JS-rendered sites

### Community 1154 - "render"
Cohesion: 0.50
Nodes (3): RENDER_API_KEY, docker, render

### Community 1155 - "portfolio_refresh.py"
Cohesion: 0.67
Nodes (3): _load(), main(), Scheduled portfolio intelligence sweep. Run by `.github/workflows/portfolio-…

### Community 1156 - "_resolve_default_executor_model"
Cohesion: 0.50
Nodes (3): Any, Resolve the default executor model via the catalog (UNIT 7). Was hardcoded to…, _resolve_default_executor_model()

### Community 1157 - "stop_colibri_server.ps1"
Cohesion: 0.83
Nodes (3): Fail(), Ok(), W()

### Community 1158 - "test_nim_models.py"
Cohesion: 0.67
Nodes (3): main(), Quick smoke-test for NVIDIA NIM model IDs. Usage: NVIDIA_API_KEY=nvapi-...…, test_model()

### Community 1160 - "start_server.sh"
Cohesion: 0.50
Nodes (3): OLLAMA_HOST, OLLAMA_MODELS, start_server.sh script

### Community 1161 - "e2e_nvidia_fallback.py"
Cohesion: 0.50
Nodes (3): _classify_error(), Exception, End-to-end verification of the hardened NVIDIA NIM fallback logic. Tests: 1.…

### Community 1168 - "sam"
Cohesion: 0.50
Nodes (4): agent/sam.py must call emit_agency_observation for voice commands., test_sam_py_traces_voice_commands(), Fresh SAM agent with mocked dependencies., sam()

### Community 1170 - "test_no_exception_detail_leaks.py"
Cohesion: 0.50
Nodes (3): parametrize, tests/test_no_exception_detail_leaks.py — Guard against str(exc)/str(e) leaking…, test_no_raw_exception_detail_in_http_response()

### Community 1171 - "test_skills_route_order.py"
Cohesion: 0.67
Nodes (3): tests/test_skills_route_order.py — /api/company/skills must not be shadowed.…, _route_index(), test_static_skills_routes_precede_dynamic_company_id_route()

### Community 1172 - "github"
Cohesion: 0.50
Nodes (3): github, enabled, silent

### Community 1177 - "Configuration reference"
Cohesion: 0.67
Nodes (3): Configuration reference, Provider priority chain, Running the brain on local Ollama (via a tunnel)

### Community 1200 - "test_the_reserve_is_bounded_when_read_from_the_environment"
Cohesion: 0.67
Nodes (3): parametrize, Read through the ENV, not the constant — that is where the bug lived.…, test_the_reserve_is_bounded_when_read_from_the_environment()

## Knowledge Gaps
- **3521 isolated node(s):** `duplicate.sh script`, `heartbeat.sh script`, `redact_secrets.sh script`, `docker`, `RENDER_API_KEY` (+3516 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 13414 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **116 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `_fixture()` connect `_fixture` to `test_doctor_coding_brain.py`, `clear_override`, `TaskStatus`, `TestNormalizeResponseFormat`, `WebsiteScanner`, `config.py`, `test_llm_router_queue_cache.py`, `test_llm_router_strategies.py`, `Task`, `PolicyEngine`, `test_ceo_supervision.py`, `test_brain_patch_service_token.py`, `SelfHealingAgent`, `_Recorder`, `TaskWorkflowService`, `test_llm_router_resilience.py`, `test_agent_tool_governance.py`, `ImprovementLoop`, `test_failover_client_shared.py`, `test_unit8_model_catalog.py`, `get_workflow_orchestrator`, `test_model_router.py`, `reset_kv_state`, `test_company_api.py`, `PrimeAgentAdapter`, `services/seo_audit.py`, `UserRole`, `settings.py`, `resolve_active_brain`, `test_telegram_service_webhook.py`, `AgentJobManager`, `test_telegram_webhook.py`, `test_ceo_router.py`, `get_registry`, `test_sam_livekit.py`, `Agency`, `test_webui_provider_priority.py`, `ChatHistoryStore`, `test_task_brain_preflight.py`, `AgentSwarm`, `test_openclaw_endpoints.py`, `test_orchestrator_merge_decision.py`, `services/background.py`, `ResearchTask`, `TestClient`, `test_ai_insights.py`, `test_startup_warmup.py`, `get_scheduler`, `test_procedural_memory.py`, `test_llm_router_e2e.py`, `ArtifactStore`, `SQLiteStore`, `BackgroundAgent`, `test_telegram_auto_approve.py`, `e2e/test_browser.py`, `test_autonomy_status.py`, `test_issue_intake.py`, `test_local_brain_state.py`, `_clean_phases`, `test_phase5_doctor.py`, `test_provider_router.py`, `test_refresh_agent_built_proof.py`, `test_tasks_reconciler_todo_requeue.py`, `KeyStore`, `failover_client.py`, `get_self_healing_agent`, `test_context_rulebook.py`, `cost_tracker.py`, `run_task`, `test_trend_scoping.py`, `FeatureMaturity`, `test_task_service_failed_comment.py`, `_step`, `test_trend_watcher.py`, `sam`, `claim`, `TestHarnessAdapter`, `persist_plan_spec`, `test_new_features_e2e.py`, `TestEstimateTokensForMessages`, `MCPClient`, `test_portfolio_intake.py`, `BudgetTracker`, `clear_cooldowns`, `test_daily_2026_07_27.py`, `test_openclaw_gateway.py`, `OllamaCircuitBreaker`, `_job_text`, `TestRuntimeControl`, `test_dashboard_cache.py`, `test_features_api.py`, `test_video_transcript.py`, `SchedulerStore`, `_Budget`, `test_process_quick_note_workflow.py`, `nvidia_models.py`, `TrendWatcher`, `timedelta`, `test_task_clarification.py`, `NotificationDispatcher`, `WorkspaceTools`, `test_llm_router_disabled.py`, `TestClient`, `WorkflowBuildRequest`, `test_knowledge_sync.py`, `TestAuthAndTaskOwnership`, `ContextPruner`, `test_agile_api.py`, `test_app_settings.py`, `provider_max_rpm`, `_FakeFiles`, `test_persistent_memory.py`, `SecurityScanner`, `api_keys_for`, `OutputFilter`, `_resolve_user_github_token`, `brain_config.py`, `test_platform_controls.py`, `test_rate_limiter.py`, `capture_screens.py`, `test_sam_voice.py`, `test_telegram_task_callback.py`, `test_nvidia_model_discovery.py`, `test_direct_chat_evolution.py`, `OrchestratorCheckpointStore`, `session_retro.py`, `analyze_page`, `_resolve_push_token`, `test_catalogue_probe.py`, `test_tasks_awaiting_approval_api.py`, `SeoFixRequest`, `TestMongoGate`, `OrchestratorQueue`, `_Recorder`, `test_regression.py`, `test_agent_scripts_share_one_model_list.py`, `test_crispy_burn_in.py`, `test_skill_registry_boot_refresh.py`, `tests/conftest.py`, `model_discovery.py`, `isolated_telegram_config`, `TestSwarmRoleRouting`, `test_scheduler_hydration_bounded.py`, `get_failover_manager`, `test_provider_enable_disable.py`, `_undeclared`, `test_rate_limit_backoff_survives.py`, `test_service_token.py`, `test_harness_spec.py`, `test_agent_free_brain.py`, `test_agency_fix.py`, `test_monitor_lib.py`, `test_v4_api.py`, `OperationalIncidentTracker`, `test_telegram_diag_endpoint.py`, `TestTheWorkflowIsSafeAndReadOnly`, `test_daily_automation_2026_07_09.py`, `test_ping.py`, `test_runtimes_health_endpoint.py`, `test_task_store_fails_loud_in_production.py`, `_FakeSandbox`, `test_provider_state_durability.py`, `ClaudeCodeAdapter`, `test_kimi_bridge_server.py`, `test_voice_pipeline.py`, `client`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `AgentRunner` connect `AgentRunner` to `ExecutionRequest`, `backend/server.py`, `proxy.py`, `test_governance_api.py`, `TaskSpec`, `ReactScratchpad`, `E2BAdapter`, `PolicyEngine`, `E2BSandboxSession`, `test_fixes_reliability.py`, `MCPClient`, `ContextManager`, `test_agent_free_brain.py`, `CEODispatcher`, `test_agent_tool_governance.py`, `test_failover_client_shared.py`, `MultiAgentSwarm`, `test_empirical_verify.py`, `TestAgentRunnerExecution`, `AgentJobManager`, `StuckDetector`, `AgentSessionStore`, `test_agent_runner.py`, `test_backend_server_features.py`, `test_daily_automation_2026_07_11.py`, `test_daily_automation_2026_07_09.py`, `TestAgentLoopMCPIntegration`, `test_autonomous_agency_e2e.py`, `LocalWorkspace`, `direct_chat.py`, `FreeBuffAgent`, `RewardScorer`, `WorkspaceTools`, `test_agent_chat_integration.py`, `TokenBudget`, `InternalAgentAdapter`, `WorkflowBuildRequest`, `GitHubTools`, `loop.py`, `UserMemoryStore`, `AdaptiveHalter`, `ContextPruner`, `get_failover_manager`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `ProviderRouter` connect `ProviderRouter` to `backend/server.py`, `test_rate_limit_backoff_survives.py`, `test_all_providers_discovery.py`, `call_llm`, `clear_cooldowns`, `test_bedrock_live.py`, `resolve_active_brain`, `ai/router.py`, `Provider`, `TestLegacyRouterCacheTTL`, `test_anthropic_refusal_fallback.py`, `test_colibri_provider.py`, `_payload`, `TestAnthropicPayloadStructuredOutput`, `test_bedrock_provider.py`, `direct_chat.py`, `TrafficDirector`, `NvidiaProvider`, `TestLegacyRouterServerFallback`, `test_provider_router.py`, `TestOpenAiToBedrockConverse`, `failover_client.py`, `system_instruction`, `implement_agent.py`, `ProviderConfig`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Are the 73 inferred relationships involving `Task` (e.g. with `fan_out_trend()` and `fan_out_trends()`) actually correct?**
  _`Task` has 73 INFERRED edges - model-reasoned connections that need verification._
- **Are the 216 inferred relationships involving `HTTPException` (e.g. with `activate_instance()` and `change_user_role()`) actually correct?**
  _`HTTPException` has 216 INFERRED edges - model-reasoned connections that need verification._
- **Are the 60 inferred relationships involving `AgentRunner` (e.g. with `MultiAgentSwarm` and `AdaptiveHalter`) actually correct?**
  _`AgentRunner` has 60 INFERRED edges - model-reasoned connections that need verification._
- **Are the 95 inferred relationships involving `TaskStatus` (e.g. with `list_agents()` and `submit_onboarding_answers()`) actually correct?**
  _`TaskStatus` has 95 INFERRED edges - model-reasoned connections that need verification._
<template>
  <main v-if="!currentUser" class="col-auth-page">
    <section class="col-auth-panel clean">
      <div class="col-login-card clean">
        <div class="login-brand">
          <span class="wordmark-symbol"><IconGlyph name="logo" /></span>
          <div>
            <strong>MedGuard</strong>
            <small>Authorization workspace</small>
          </div>
        </div>
        <div>
          <p class="eyebrow">Secure access</p>
          <h1>Content authorization console</h1>
          <p class="muted">Use your assigned work email and password, or continue through your enterprise identity provider.</p>
        </div>
        <div class="auth-security-strip">
          <span><IconGlyph name="compliance" /> SSO ready</span>
          <span><IconGlyph name="key" /> Audit protected</span>
          <span><IconGlyph name="users" /> Role-based access</span>
        </div>
        <div class="auth-standards-strip">
          <span>21 CFR Part 11 aligned</span>
          <span>GDPR-ready controls</span>
          <span>GxP auditability</span>
          <span>Global MLR governance</span>
        </div>
        <form class="auth-form-clean" @submit.prevent="signIn">
          <label>Email<input v-model="loginForm.email" autocomplete="email" placeholder="name@company.com" type="email" /></label>
          <label>Password<input v-model="loginForm.password" autocomplete="current-password" placeholder="Enter password" type="password" /></label>
          <button class="btn" :disabled="authLoading" type="submit">{{ authLoading ? 'Signing in...' : 'Sign in' }}</button>
          <div class="sso-provider-grid">
            <button class="btn inverse sso-provider google" :disabled="authLoading" type="button" aria-label="Continue with Google" title="Continue with Google" @click="startSso('Google')">
              <svg class="sso-logo" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.54-.2-2.27H12v4.29h6.47a5.53 5.53 0 0 1-2.4 3.63v2.8h3.89c2.27-2.1 3.53-5.19 3.53-8.45z"/>
                <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.95-2.9l-3.89-3.02c-1.08.72-2.46 1.15-4.06 1.15-3.12 0-5.77-2.1-6.72-4.94H1.27v3.12A12 12 0 0 0 12 24z"/>
                <path fill="#FBBC05" d="M5.28 14.29A7.21 7.21 0 0 1 4.9 12c0-.8.14-1.58.38-2.29V6.59H1.27A12 12 0 0 0 0 12c0 1.94.46 3.77 1.27 5.41l4.01-3.12z"/>
                <path fill="#EA4335" d="M12 4.77c1.76 0 3.35.61 4.6 1.8l3.44-3.44A11.5 11.5 0 0 0 12 0 12 12 0 0 0 1.27 6.59l4.01 3.12C6.23 6.87 8.88 4.77 12 4.77z"/>
              </svg>
            </button>
            <button class="btn inverse sso-provider microsoft" :disabled="authLoading" type="button" aria-label="Continue with Microsoft" title="Continue with Microsoft" @click="startSso('Microsoft')">
              <svg class="sso-logo" viewBox="0 0 24 24" aria-hidden="true">
                <path fill="#F25022" d="M1 1h10v10H1z"/>
                <path fill="#7FBA00" d="M13 1h10v10H13z"/>
                <path fill="#00A4EF" d="M1 13h10v10H1z"/>
                <path fill="#FFB900" d="M13 13h10v10H13z"/>
              </svg>
            </button>
          </div>
          <button class="link-button" type="button">Forgot password?</button>
          <p v-if="ssoMessage" class="form-success">{{ ssoMessage }}</p>
          <p v-if="authError" class="form-alert">{{ authError }}</p>
        </form>
        <div class="syrencloud-credit">
          <img src="/syren-logo.svg" alt="Syren" />
          <small>A product of <strong>Syren</strong></small>
        </div>
      </div>
    </section>
  </main>

  <main v-else class="col-app-shell ec-shell" :class="{ 'sidebar-hidden': sidebarHidden }">
    <aside v-if="!sidebarHidden" class="col-sidebar ec-sidebar">
      <div class="product-brand">
        <span class="wordmark-symbol"><IconGlyph name="logo" /></span>
        <div>
          <strong>MedGuard</strong>
          <small>Enterprise control</small>
        </div>
        <button class="icon-button sidebar-close" title="Hide left panel" aria-label="Hide left panel" type="button" @click="sidebarHidden = true">
          <IconGlyph name="panel-left" />
        </button>
      </div>

      <section class="sidebar-user ec-sidebar-user">
        <span><IconGlyph name="users" /></span>
        <div>
          <strong>{{ currentUser.name }}</strong>
          <small>{{ currentUser.role.replace('_', ' ') }} · {{ currentUser.team }}</small>
          <small>{{ currentUser.email }}</small>
        </div>
      </section>

      <nav class="product-nav" aria-label="Application views">
        <button
          v-for="item in navItems"
          :key="item.id"
          class="product-nav-button"
          :class="{ active: activeView === item.id }"
          type="button"
          @click="activeView = item.id"
        >
          <span><IconGlyph :name="item.icon" /></span>
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <button v-if="sidebarHidden" class="panel-edge-toggle" title="Show left panel" aria-label="Show left panel" type="button" @click="sidebarHidden = false">
      <IconGlyph name="panel-right" />
    </button>

    <section class="col-main ec-main">
      <header class="product-topbar soft ec-topbar">
        <div>
          <p class="eyebrow">{{ currentUser.team }}</p>
          <h1>{{ viewTitle }}</h1>
        </div>
        <div class="topbar-actions icon-actions">
          <div class="notification-menu-wrap">
            <button class="icon-button notification-trigger" title="Notifications" aria-label="Notifications" type="button" @click="showNotificationMenu = !showNotificationMenu">
              <IconGlyph name="evidence" />
              <span v-if="unreadNotifications">{{ unreadNotifications }}</span>
            </button>
            <div v-if="showNotificationMenu" class="notification-menu">
              <header>
                <strong>Notifications</strong>
                <small>{{ unreadNotifications }} unread</small>
              </header>
              <button v-for="note in notifications" :key="note.id" :class="note.severity" type="button" @click="openNotification(note)">
                <span>{{ note.title }}</span>
                <small>{{ note.stage }} · {{ note.timestamp }}</small>
                <em>{{ note.message }}</em>
              </button>
              <p v-if="!notifications.length">No notifications.</p>
            </div>
          </div>
          <button v-if="activeView === 'workflow'" class="icon-button" :title="showWorkflowPanel ? 'Hide workflow rail' : 'Show workflow rail'" type="button" @click="showWorkflowPanel = !showWorkflowPanel">
            <IconGlyph :name="showWorkflowPanel ? 'eye-off' : 'eye'" />
          </button>
          <button class="icon-button" title="Sign out" aria-label="Sign out" type="button" @click="signOut">
            <IconGlyph name="logout" />
          </button>
        </div>
      </header>

      <div v-if="showGlobalContextControls" class="locked-selector-grid global-context-controls">
        <label v-for="group in lockedSelectorGroups" :key="group.key">
          <span>{{ group.label }}</span>
          <select v-model="lockedSelection[group.key]" @change="normalizeLockedSelection(group.key)">
            <option v-for="option in group.options" :key="option.value" :value="option.value" :disabled="option.locked">
              {{ option.label }}
            </option>
          </select>
        </label>
      </div>

      <section v-if="activeView === 'dashboard'" class="col-view ec-view">
        <div class="ec-kpi-grid">
          <button
            v-for="card in dashboardKpis"
            :key="`${card.group}-${card.label}`"
            class="ec-kpi-card"
            :class="[card.status, { active: activeDashboardGroup === card.group }]"
            type="button"
            @click="activeDashboardGroup = card.group"
          >
            <span>{{ card.group }}</span>
            <strong>{{ card.value }}</strong>
            <small>{{ card.label }} · {{ card.trend }}</small>
          </button>
        </div>

        <div class="ec-dashboard-grid">
          <article class="console-card ec-panel root-cause-card">
            <p class="eyebrow">Validation blockers</p>
            <h2>Root cause analysis</h2>
            <div class="root-cause-chart">
              <div class="pie-visual" :style="{ background: pieGradient }">
                <span>{{ rootCauseTotal }}</span>
                <small>signals</small>
              </div>
              <div class="pie-legend">
                <button v-for="item in rootCauseSegments" :key="item.label" type="button">
                  <i :style="{ background: item.color }"></i>
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </button>
              </div>
            </div>
            <div class="dashboard-micro-ledger">
              <span v-for="item in rootCauseDeepDive" :key="item.label">
                <b>{{ item.label }}</b>
                {{ item.value }}
              </span>
            </div>
          </article>

          <article class="console-card ec-panel throughput-card">
            <div class="card-head">
              <div>
                <p class="eyebrow">Authorization throughput</p>
                <h2>Stage volume by gate</h2>
              </div>
              <button class="btn inverse" type="button" @click="activeView = 'workflow'">Open workflow</button>
            </div>
            <div class="throughput-chart">
              <button v-for="bar in throughputBars" :key="bar.stage" type="button" :title="`${bar.stage}: ${bar.count}`" @click="selectStageByName(bar.stage)">
                <span>{{ bar.count }}</span>
                <em :style="{ height: `${bar.height}%`, background: bar.color }"></em>
                <small><b>{{ bar.short }}</b>{{ bar.stage }}</small>
              </button>
            </div>
            <div class="dashboard-micro-ledger throughput-detail-ledger">
              <span v-for="item in throughputDeepDive" :key="item.label">
                <b>{{ item.label }}</b>
                {{ item.value }}
              </span>
            </div>
          </article>

          <article class="console-card ec-panel wide">
            <div class="card-head">
              <div>
                <p class="eyebrow">SLA</p>
                <h2>Risk table</h2>
              </div>
            </div>
            <table class="sla-risk-table">
              <thead>
                <tr><th>Stage</th><th>SLA</th><th>Severity</th><th>Status</th></tr>
              </thead>
              <tbody>
                <tr v-for="row in slaRiskRows" :key="row.label" :class="row.severity" @click="selectStageByName(row.label)">
                  <td>{{ row.label }}</td>
                  <td>{{ row.sla }}</td>
                  <td><span>{{ row.severity }}</span></td>
                  <td>{{ row.status }}</td>
                </tr>
              </tbody>
            </table>
          </article>

          <article class="console-card ec-panel wide">
            <p class="eyebrow">Task completion</p>
            <h2>Gantt view</h2>
            <div class="gantt-chart">
              <div class="gantt-head">
                <span>Task</span>
                <small v-for="day in ganttDays" :key="day">{{ day }}</small>
              </div>
              <div v-for="task in ganttTasks" :key="task.id" class="gantt-row">
                <span><b>{{ task.id }}</b>{{ task.title }}</span>
                <i v-for="cell in task.cells" :key="`${task.id}-${cell.day}`" :class="cell.state"></i>
              </div>
            </div>
          </article>

          <article class="console-card ec-panel">
            <p class="eyebrow">Validation operations</p>
            <h2>Operations cockpit</h2>
            <div class="validation-ops-grid">
              <article v-for="item in validationOps" :key="item.label" :class="item.tone">
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
                <em :style="{ width: `${item.progress}%` }"></em>
                <small>{{ item.detail }}</small>
              </article>
            </div>
            <div class="dashboard-micro-ledger">
              <span v-for="item in validationOpsDeepDive" :key="item.label">
                <b>{{ item.label }}</b>
                {{ item.value }}
              </span>
            </div>
          </article>

          <article class="console-card ec-panel">
            <p class="eyebrow">Audit exceptions</p>
            <h2>Exception signals</h2>
            <div class="audit-exception-stack">
              <button v-for="event in auditExceptionRows" :key="event.id" :class="event.severity || 'low'" type="button" @click="activeView = 'audit'">
                <span>{{ event.id }}</span>
                <strong>{{ event.stage }}</strong>
                <small>{{ event.decision }}</small>
              </button>
            </div>
            <div class="dashboard-micro-ledger">
              <span v-for="item in auditDeepDive" :key="item.label">
                <b>{{ item.label }}</b>
                {{ item.value }}
              </span>
            </div>
          </article>
        </div>
      </section>

      <section v-else-if="activeView === 'workflow'" class="col-view ec-view">
        <article v-if="showWorkflowPanel" class="console-card ec-workflow-map">
          <div class="card-head">
            <div>
              <p class="eyebrow">End-to-end authorization</p>
              <h2>Global Stage and Local Stage</h2>
            </div>
          </div>
          <div v-if="workflowStageGroups.length" class="ec-stage-groups">
            <section
              v-for="group in workflowStageGroups"
              :key="group.id"
              class="ec-stage-group"
              :class="[group.id, { dimmed: activeFlowScope && activeFlowScope !== group.id }]"
            >
              <header>
                <span>{{ group.title }}</span>
                <small>{{ group.id === 'global' ? 'Stage 1-4' : 'Stage 5-8' }}</small>
              </header>
              <div class="ec-stage-rail">
                <button
                  v-for="stage in group.stages"
                  :key="stage.id"
                  class="ec-stage-tile"
                  :class="[stage.risk, stage.status, { active: selectedStage?.id === stage.id }]"
                  type="button"
                  @click="selectedStageId = stage.id"
                >
                  <span>{{ stage.order }}</span>
                  <strong>{{ stage.name }}</strong>
                  <small>{{ stage.flow_scope }} · {{ stage.sla }}</small>
                  <div>
                    <em>{{ stage.validation_score }}%</em>
                    <b>{{ stage.system }}</b>
                  </div>
                </button>
              </div>
            </section>
          </div>
          <div v-else class="ec-stage-rail">
            <button
              v-for="stage in visibleStages"
              :key="stage.id"
              class="ec-stage-tile"
              :class="[stage.risk, stage.status, { active: selectedStage?.id === stage.id }]"
              type="button"
              @click="selectedStageId = stage.id"
            >
              <span>{{ stage.order }}</span>
              <strong>{{ stage.name }}</strong>
              <small>{{ stage.flow_scope }} · {{ stage.sla }}</small>
              <div>
                <em>{{ stage.validation_score }}%</em>
                <b>{{ stage.system }}</b>
              </div>
            </button>
          </div>
        </article>

        <article v-if="selectedStage" class="console-card ec-stage-workbench">
          <div class="stage-detail-head">
            <div>
              <p class="eyebrow">{{ selectedStage.trigger }} · {{ selectedStage.asset_id }}</p>
              <h2>{{ selectedStage.name }}</h2>
              <p>{{ selectedStage.output }}</p>
              <div class="stage-meta-strip">
                <span><b>Brand</b>{{ lockedSelection.brand }}</span>
                <span><b>Content type</b>{{ lockedSelection.contentType }}</span>
                <span><b>Market</b>{{ lockedSelection.market }}</span>
                <span><b>Channel</b>{{ lockedSelection.channel }}</span>
              </div>
            </div>
            <div class="stage-flow-card">
              <span>{{ selectedStage.flow_scope }}</span>
              <strong>{{ selectedStage.engine_label }}</strong>
              <small>{{ stageModelDisplay }}</small>
            </div>
          </div>

          <section class="ec-layer input document-source-layer workflow-doc-strip" :class="{ locked: documentPanelLocked }">
              <div class="card-head compact">
                <div>
                  <p class="eyebrow">Documents used for validation and checks</p>
                  <h3>{{ selectedStage.order === 1 ? 'Respivara brief and planning records' : `${selectedDocumentIds.length} source and validation documents` }}</h3>
                </div>
                <span class="lock-pill">{{ documentPanelLocked ? 'Selected brief bundle' : 'Choose one brief / plan' }}</span>
              </div>
              <div class="required-doc-strip">
                <span v-for="docType in selectedStage.required_documents" :key="docType">{{ docType }}</span>
              </div>
              <div v-if="selectedStage.order > 1" class="workflow-source-row">
                <div class="validated-content-strip">
                  <p class="eyebrow">New content selected for validation</p>
                  <div>
                    <article v-for="media in selectedMedia" :key="media.id">
                      <img v-if="media.thumbnail_url || (media.url && media.mime_type.startsWith('image'))" :src="media.thumbnail_url || media.url" :alt="media.name" />
                      <span v-else><IconGlyph name="asset" /></span>
                      <strong>{{ media.name }}</strong>
                      <small>{{ media.type }} · {{ media.source_system || 'DAM' }}</small>
                      <button class="btn ghost" type="button" @click="previewMedia(media)">View</button>
                    </article>
                  </div>
                </div>
                <div class="validation-documents-panel">
                  <p class="eyebrow">Validation documents</p>
                  <div class="document-source-grid">
                    <article v-for="doc in validationStageDocuments.slice(0, 8)" :key="doc.id" class="document-card" :class="{ selected: selectedDocumentIds.includes(doc.id) }">
                      <header>
                        <span><IconGlyph :name="docIcon(doc)" /></span>
                        <div>
                          <strong>{{ doc.title }}</strong>
                          <small>{{ doc.source_name }} · {{ doc.version }} · {{ doc.approval_status }}</small>
                        </div>
                      </header>
                      <p>{{ doc.summary }}</p>
                      <p class="doc-preview-text">{{ doc.preview }}</p>
                      <div class="doc-claim-list">
                        <small v-for="claim in doc.claims.slice(0, 3)" :key="claim">{{ claim }}</small>
                      </div>
                      <div class="doc-meta-row">
                        <span>{{ doc.brand }}</span>
                        <span>{{ doc.document_type }}</span>
                        <span>{{ doc.market }}</span>
                        <span>{{ doc.channel }}</span>
                      </div>
                      <footer>
                        <button class="btn inverse" :disabled="documentPanelLocked" type="button" @click="toggleDocumentSelection(doc)">{{ selectedDocumentIds.includes(doc.id) ? 'Remove' : 'Select' }}</button>
                        <button class="btn ghost" type="button" @click="previewDocument(doc)">Preview</button>
                      </footer>
                    </article>
                  </div>
                </div>
              </div>
              <div v-else class="workflow-source-row">
                <div class="validation-documents-panel">
                  <p class="eyebrow">Brief and plan</p>
                  <div class="document-source-grid">
                    <article v-for="doc in primaryStageDocuments.slice(0, 6)" :key="doc.id" class="document-card" :class="{ selected: selectedDocumentIds.includes(doc.id) }">
                      <header>
                        <span><IconGlyph :name="docIcon(doc)" /></span>
                        <div>
                          <strong>{{ doc.title }}</strong>
                          <small>{{ doc.source_name }} · {{ doc.version }} · {{ doc.approval_status }}</small>
                        </div>
                      </header>
                      <p>{{ doc.summary }}</p>
                      <p class="doc-preview-text">{{ doc.preview }}</p>
                      <div class="doc-claim-list">
                        <small v-for="claim in doc.claims.slice(0, 3)" :key="claim">{{ claim }}</small>
                      </div>
                      <div class="doc-meta-row">
                        <span>{{ doc.brand }}</span>
                        <span>{{ doc.document_type }}</span>
                        <span>{{ doc.market }}</span>
                        <span>{{ doc.channel }}</span>
                      </div>
                      <footer>
                        <button class="btn inverse" :disabled="documentPanelLocked" type="button" @click="toggleDocumentSelection(doc)">{{ selectedDocumentIds.includes(doc.id) ? 'Remove' : 'Select' }}</button>
                        <button class="btn ghost" type="button" @click="previewDocument(doc)">Preview</button>
                      </footer>
                    </article>
                  </div>
                </div>
                <div class="validation-documents-panel">
                  <p class="eyebrow">Validation documents</p>
                  <div class="document-source-grid">
                    <article v-for="doc in validationStageDocuments.slice(0, 6)" :key="doc.id" class="document-card" :class="{ selected: selectedDocumentIds.includes(doc.id) }">
                      <header>
                        <span><IconGlyph :name="docIcon(doc)" /></span>
                        <div>
                          <strong>{{ doc.title }}</strong>
                          <small>{{ doc.source_name }} · {{ doc.version }} · {{ doc.approval_status }}</small>
                        </div>
                      </header>
                      <p>{{ doc.summary }}</p>
                      <p class="doc-preview-text">{{ doc.preview }}</p>
                      <div class="doc-claim-list">
                        <small v-for="claim in doc.claims.slice(0, 3)" :key="claim">{{ claim }}</small>
                      </div>
                      <div class="doc-meta-row">
                        <span>{{ doc.brand }}</span>
                        <span>{{ doc.document_type }}</span>
                        <span>{{ doc.market }}</span>
                        <span>{{ doc.channel }}</span>
                      </div>
                      <footer>
                        <button class="btn inverse" :disabled="documentPanelLocked" type="button" @click="toggleDocumentSelection(doc)">{{ selectedDocumentIds.includes(doc.id) ? 'Remove' : 'Select' }}</button>
                        <button class="btn ghost" type="button" @click="previewDocument(doc)">Preview</button>
                      </footer>
                    </article>
                  </div>
                </div>
              </div>
              <article v-if="activeBundle" class="bundle-summary-card">
                <strong>{{ activeBundle.name }}</strong>
                <small>{{ activeBundle.documents.length }} documents · {{ activeBundle.approval_status }} · {{ activeBundle.id }}</small>
                <p>{{ activeBundle.taxonomy.join(', ') }}</p>
              </article>
              <article v-if="activePreviewDocument" class="document-preview-card">
                <header>
                  <strong>{{ activePreviewDocument.title }}</strong>
                </header>
                <div v-if="activePreviewDocument.url" class="asset-viewer-frame inline-doc-frame">
                  <img v-if="isImageUrl(activePreviewDocument.url)" :src="activePreviewDocument.url" :alt="activePreviewDocument.title" />
                  <iframe v-else :src="activePreviewDocument.url" :title="activePreviewDocument.title"></iframe>
                </div>
                <p>{{ activePreviewDocument.preview }}</p>
                <small>{{ activePreviewDocument.claims.join(' · ') }}</small>
              </article>
              <article v-if="activePreviewMedia" class="document-preview-card">
                <header>
                  <strong>{{ activePreviewMedia.name }}</strong>
                  <button class="icon-button" type="button" title="Close viewer" @click="activePreviewMedia = null">x</button>
                </header>
                <div class="asset-viewer-frame inline-doc-frame">
                  <img v-if="activePreviewMedia.mime_type.startsWith('image')" :src="activePreviewMedia.url" :alt="activePreviewMedia.name" />
                  <iframe v-else-if="activePreviewMedia.url" :src="activePreviewMedia.url" :title="activePreviewMedia.name"></iframe>
                </div>
                <p>{{ activePreviewMedia.preview }}</p>
              </article>
              <p v-if="bundleMessage" class="form-success">{{ bundleMessage }}</p>
              <p v-if="bundleError" class="form-alert">{{ bundleError }}</p>
            </section>

          <div class="validation-shell">
            <section class="ec-layer validation">
              <div class="card-head compact">
                <div>
                  <p class="eyebrow">{{ selectedStage.engine_label }}</p>
                  <h3>{{ selectedRuleRun?.status || selectedStage.last_validation?.decision || selectedStage.recommendation }}</h3>
                  <label class="model-select-inline">
                    <span>Model</span>
                    <select v-model="selectedModelProfile">
                      <option v-for="model in aiModels" :key="model.id" :value="model.id">
                        {{ modelOptionLabel(model) }}
                      </option>
                    </select>
                  </label>
                </div>
                <div class="validation-action-stack">
                  <button class="btn run-validation-btn" :class="{ running: stageRunLoading, clicked: runButtonPulse }" :disabled="stageRunLoading" type="button" @click="runStageRuleEngine">
                    {{ stageRunLoading ? 'Running all checks...' : 'Run Validations' }}
                  </button>
                  <div class="validation-score-badge" :class="selectedStage.risk">
                    <strong>{{ selectedRuleRun?.stage_score || selectedStage.validation_score }}%</strong>
                    <span>{{ selectedStage.risk }}</span>
                  </div>
                </div>
              </div>
              <div v-if="selectedRuleTemplate" class="rule-engine-panel">
                <div class="rule-summary-strip">
                  <span>Threshold {{ selectedRuleRun?.threshold || selectedRuleTemplate.threshold }}%</span>
                  <span>{{ selectedRuleRun?.mandatory_checks_passed || 0 }}/{{ selectedRuleRun?.mandatory_checks_total || selectedRuleSteps.length }} mandatory passed</span>
                  <span>{{ ruleUiState?.percent || 0 }}% complete</span>
                </div>
                <div class="rule-progress-row">
                  <article v-for="step in selectedRuleSteps" :key="step.id" class="rule-progress-step">
                    <span class="rule-step-circle" :class="stepDisplayStatus(step)">
                      {{ stepDisplayStatus(step) === 'passed' ? '✓' : ['failed', 'blocked', 'rework'].includes(stepDisplayStatus(step)) ? '!' : step.order }}
                    </span>
                    <small>{{ step.name }}</small>
                  </article>
                </div>
                <div class="rule-results-grid">
                  <article v-for="step in selectedRuleSteps" :key="`${step.id}-detail`" class="rule-result-card" :class="stepDisplayStatus(step)">
                    <header>
                      <div>
                        <span>{{ step.category }}</span>
                        <strong>{{ step.name }}</strong>
                      </div>
                      <b>{{ step.score || '—' }}%</b>
                    </header>
                    <p>{{ step.summary }}</p>
                    <div class="rule-mini-grid">
                      <small v-for="source in step.source_refs.slice(0, 3)" :key="source">{{ source }}</small>
                    </div>
                    <div class="rule-step-evidence">
                      <div>
                        <b>KPIs</b>
                        <small v-for="(value, label) in step.kpis" :key="String(label)">{{ label }}: {{ value }}</small>
                      </div>
                      <div>
                        <b>Checks</b>
                        <small v-for="rule in step.static_rules.slice(0, 3)" :key="rule">{{ rule }}</small>
                      </div>
                    </div>
                    <ul v-if="step.findings.length">
                      <li v-for="finding in step.findings.slice(0, 2)" :key="finding">{{ finding }}</li>
                    </ul>
                    <footer class="result-action-footer">
                      <span>{{ step.mode || 'rules' }} · {{ step.model_used || 'pending' }}</span>
                      <textarea v-model="ruleStepComments[step.id]" rows="2" :placeholder="step.score < 80 ? 'Add rework comment for the owner' : 'Add reviewer feedback before continuing'"></textarea>
                      <div>
                        <button class="btn inverse" type="button" @click="submitWorkflowAction('comment', step)">Comment</button>
                        <button class="btn ghost danger" type="button" @click="submitWorkflowAction('request_rework', step)">Flag issue</button>
                        <button class="btn inverse" :disabled="stageRunLoading" type="button" @click="rerunRuleStep(step)">Rerun step</button>
                        <button class="btn" type="button" @click="submitWorkflowAction('send_next_stage', step)">Submit</button>
                      </div>
                    </footer>
                  </article>
                </div>
                <article v-if="latestStageOutput" class="stage-output-preview">
                  <header>
                    <div>
                      <p class="eyebrow">Output validation report</p>
                      <h3>{{ latestStageOutput.title }}</h3>
                    </div>
                    <small>{{ latestStageOutput.version }} · {{ latestStageOutput.created_at }}</small>
                  </header>
                  <div class="report-body">
                    <template v-for="(block, index) in outputReportBlocks" :key="`${block.type}-${index}`">
                      <h4 v-if="block.type === 'heading'">{{ block.text }}</h4>
                      <p v-else-if="block.type === 'paragraph'">{{ block.text }}</p>
                      <ul v-else-if="block.type === 'list'">
                        <li v-for="item in block.items" :key="item">{{ item }}</li>
                      </ul>
                      <div v-else-if="block.type === 'table'" class="report-table-wrap">
                        <table>
                          <thead>
                            <tr><th v-for="header in block.headers" :key="header">{{ header }}</th></tr>
                          </thead>
                          <tbody>
                            <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
                              <td v-for="(cell, cellIndex) in row" :key="`${rowIndex}-${cellIndex}`">{{ cell }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </template>
                  </div>
                </article>
                <div v-if="selectedStage.last_validation || selectedRuleRun" class="ec-validation-result final-decision-card">
                  <strong>{{ selectedRuleRun?.status || selectedStage.last_validation?.decision }}</strong>
                  <p>{{ selectedRuleRun ? `${selectedRuleRun.critical_blockers.length} blockers · audit ${selectedRuleRun.audit_id}` : selectedStage.last_validation?.recommended_action }}</p>
                  <small>{{ selectedRuleRun ? `${selectedRuleRun.steps.length} checks · ${selectedRuleRun.risk_flags.length} risk flags` : `${selectedStage.last_validation?.findings.length || 0} findings · ${selectedStage.last_validation?.trace.length || 0} trace events` }}</small>
                </div>
              </div>
              <template v-else>
                <div class="ec-check-tabs">
                  <button v-for="tab in checkTabs" :key="tab.id" :class="{ active: activeCheckTab === tab.id }" type="button" @click="activeCheckTab = tab.id">{{ tab.label }}</button>
                </div>
                <div class="ec-check-list">
                  <article v-for="check in activeChecks" :key="check.name || check.claim" :class="check.status">
                    <strong>{{ check.name || check.claim }}</strong>
                    <span>{{ check.status.replace('_', ' ') }}</span>
                    <small>{{ check.detail || check.evidence || `${check.score || selectedStage.score}% confidence` }}</small>
                  </article>
                </div>
              </template>
              <article v-if="!selectedRuleTemplate && latestStageOutput" class="stage-output-preview">
                <header>
                  <div>
                    <p class="eyebrow">Output validation report</p>
                    <h3>{{ latestStageOutput.title }}</h3>
                  </div>
                  <small>{{ latestStageOutput.version }} · {{ latestStageOutput.created_at }}</small>
                </header>
                <div class="report-body">
                  <template v-for="(block, index) in outputReportBlocks" :key="`${block.type}-${index}`">
                    <h4 v-if="block.type === 'heading'">{{ block.text }}</h4>
                    <p v-else-if="block.type === 'paragraph'">{{ block.text }}</p>
                    <ul v-else-if="block.type === 'list'">
                      <li v-for="item in block.items" :key="item">{{ item }}</li>
                    </ul>
                    <div v-else-if="block.type === 'table'" class="report-table-wrap">
                      <table>
                        <thead>
                          <tr><th v-for="header in block.headers" :key="header">{{ header }}</th></tr>
                        </thead>
                        <tbody>
                          <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
                            <td v-for="(cell, cellIndex) in row" :key="`${rowIndex}-${cellIndex}`">{{ cell }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </template>
                </div>
              </article>
              <div v-if="!selectedRuleTemplate && (selectedStage.last_validation || selectedRuleRun)" class="ec-validation-result final-decision-card">
                <strong>{{ selectedRuleRun?.status || selectedStage.last_validation?.decision }}</strong>
                <p>{{ selectedRuleRun ? `${selectedRuleRun.critical_blockers.length} blockers · audit ${selectedRuleRun.audit_id}` : selectedStage.last_validation?.recommended_action }}</p>
                <small>{{ selectedRuleRun ? `${selectedRuleRun.steps.length} checks · ${selectedRuleRun.risk_flags.length} risk flags` : `${selectedStage.last_validation?.findings.length || 0} findings · ${selectedStage.last_validation?.trace.length || 0} trace events` }}</small>
              </div>
            </section>
            <aside class="ec-layer live-process-panel">
              <div class="card-head compact">
                <div>
                  <p class="eyebrow">Real-time validation process</p>
                  <h3>{{ ruleUiState?.percent || 0 }}% complete</h3>
                </div>
              </div>
              <div class="process-list">
                <article v-for="step in selectedRuleSteps" :key="`${step.id}-process`" :class="stepDisplayStatus(step)">
                  <span>{{ step.order }}</span>
                  <div>
                    <strong>{{ step.name }}</strong>
                    <small>{{ step.category }} · {{ stepDisplayStatus(step) }}</small>
                    <em v-for="(value, label) in step.kpis" :key="String(label)">{{ label }}: {{ value }}</em>
                  </div>
                </article>
              </div>
            </aside>
          </div>
        </article>
      </section>

      <section v-else-if="activeView === 'dam'" class="col-view ec-view">
        <article class="console-card ec-panel">
          <div class="card-head">
            <div>
              <p class="eyebrow">Digital Asset Management</p>
              <h2>DAM evidence and media assets</h2>
            </div>
            <button class="btn" type="button" @click="addDamAsset">Add asset</button>
          </div>
          <form class="dam-add-form dam-page-form" @submit.prevent="addDamAsset">
            <input v-model="damForm.name" placeholder="Asset name or URL" />
            <select v-model="damForm.source_system">
              <option v-for="source in damSources.filter(item => item !== 'All sources')" :key="source">{{ source }}</option>
            </select>
            <input v-model="damForm.url" placeholder="https:// or /samples/file.html" />
            <input v-model="damForm.preview" placeholder="Description and usage rights" />
            <button class="btn" type="submit">Save asset</button>
          </form>
          <div class="dam-source-tabs">
            <button v-for="source in damSources" :key="source" :class="{ active: damSourceFilter === source }" type="button" @click="damSourceFilter = source">
              {{ source }}
            </button>
          </div>
          <div class="dam-library-grid">
            <article v-for="media in filteredDamMedia" :key="media.id" class="dam-card">
              <div class="media-preview">
                <img v-if="media.thumbnail_url || (media.url && media.mime_type.startsWith('image'))" :src="media.thumbnail_url || media.url" :alt="media.name" />
                <span v-else>{{ media.type }}</span>
              </div>
              <div>
                <span>{{ media.source_system || 'DAM' }} · {{ media.connector_status || 'available' }}</span>
                <strong>{{ media.name }}</strong>
                <small>{{ media.preview }}</small>
                <div class="dam-actions">
                  <button class="btn inverse" type="button" @click="previewMedia(media)">View asset</button>
                </div>
              </div>
            </article>
          </div>
          <article v-if="activePreviewMedia" class="asset-viewer-card">
            <header>
              <div>
                <p class="eyebrow">{{ activePreviewMedia.source_system || 'DAM' }}</p>
                <h3>{{ activePreviewMedia.name }}</h3>
              </div>
              <button class="icon-button" type="button" title="Close viewer" @click="activePreviewMedia = null">x</button>
            </header>
            <div class="asset-viewer-frame">
              <img v-if="activePreviewMedia.mime_type.startsWith('image')" :src="activePreviewMedia.url" :alt="activePreviewMedia.name" />
              <iframe v-else-if="activePreviewMedia.url" :src="activePreviewMedia.url" :title="activePreviewMedia.name"></iframe>
            </div>
            <p>{{ activePreviewMedia.preview }}</p>
          </article>
        </article>
      </section>

      <section v-else-if="activeView === 'library'" class="col-view ec-view">
        <article class="console-card ec-panel">
          <div class="card-head">
            <div>
              <p class="eyebrow">Content Library</p>
              <h2>Validated Respivara resources</h2>
            </div>
            <button class="btn inverse" type="button" @click="loadContentLibrary">Refresh library</button>
          </div>
          <div class="document-search-grid library-search">
            <input v-model="documentSearch.q" placeholder="Search Respivara validation resources" @keyup.enter="loadContentLibrary" />
            <select v-model="lockedSelection.contentType" @change="normalizeLockedSelection('contentType')">
              <option v-for="option in lockedSelectorGroups.find(group => group.key === 'contentType')?.options || []" :key="option.value" :value="option.value" :disabled="option.locked">
                {{ option.label }}
              </option>
            </select>
          </div>
          <div class="content-library-grid">
            <article v-for="doc in allLibraryDocuments" :key="doc.id" class="document-card">
              <header>
                <span><IconGlyph :name="docIcon(doc)" /></span>
                <div>
                  <strong>{{ doc.title }}</strong>
                  <small>{{ doc.source_name }} · {{ doc.document_type }} · {{ doc.version }}</small>
                </div>
              </header>
              <p>{{ doc.summary }}</p>
              <p class="doc-preview-text">{{ doc.preview }}</p>
              <div class="doc-claim-list">
                <small v-for="claim in doc.claims.slice(0, 3)" :key="claim">{{ claim }}</small>
              </div>
              <div class="doc-meta-row">
                <span>{{ doc.document_type }}</span>
                <span>{{ doc.version }}</span>
                <span>{{ doc.approval_status }}</span>
              </div>
              <footer>
                <button class="btn inverse" type="button" @click="previewDocument(doc)">Preview</button>
                <a v-if="doc.external_url" :href="doc.external_url" target="_blank" rel="noreferrer">Official source</a>
              </footer>
            </article>
          </div>
          <article v-if="activePreviewDocument" class="asset-viewer-card document-viewer">
            <header>
              <div>
                <p class="eyebrow">{{ activePreviewDocument.source_name }} · {{ activePreviewDocument.document_type }}</p>
                <h3>{{ activePreviewDocument.title }}</h3>
              </div>
              <button class="icon-button" type="button" title="Close viewer" @click="activePreviewDocument = null">x</button>
            </header>
            <div class="asset-viewer-frame">
              <img v-if="isImageUrl(activePreviewDocument.url)" :src="activePreviewDocument.url" :alt="activePreviewDocument.title" />
              <iframe v-else-if="activePreviewDocument.url" :src="activePreviewDocument.url" :title="activePreviewDocument.title"></iframe>
            </div>
            <p>{{ activePreviewDocument.preview }}</p>
            <div class="doc-meta-row">
              <span v-for="claim in activePreviewDocument.claims" :key="claim">{{ claim }}</span>
            </div>
          </article>
        </article>
      </section>

      <section v-else-if="activeView === 'imcp'" class="col-view ec-view">
        <article class="console-card ec-panel">
          <div class="card-head">
            <div>
              <p class="eyebrow">IMCP Framework</p>
              <h2>Validated resource blueprint</h2>
            </div>
          </div>
          <div class="imcp-document-layout">
            <nav class="imcp-grid">
              <button v-for="pillar in imcpFramework" :key="pillar.name" :class="{ active: activeImcpName === pillar.name }" type="button" @click="activeImcpName = pillar.name">
              <span><IconGlyph :name="pillar.icon" /></span>
              <div>
                <strong>{{ pillar.name }}</strong>
                <p>{{ pillar.description }}</p>
                <small v-for="item in pillar.items" :key="item">{{ item }}</small>
              </div>
              </button>
            </nav>
            <article v-if="activeImcpPillar" class="imcp-document">
              <header>
                <p class="eyebrow">Controlled blueprint document</p>
                <h3>{{ activeImcpPillar.name }}</h3>
                <p>{{ activeImcpPillar.description }}</p>
              </header>
              <section v-for="section in activeImcpPillar.sections" :key="section.title">
                <h4>{{ section.title }}</h4>
                <ul>
                  <li v-for="line in section.lines" :key="line">{{ line }}</li>
                </ul>
              </section>
            </article>
          </div>
        </article>
      </section>

      <section v-else-if="activeView === 'connections' && canViewConnections" class="col-view ec-view">
        <div class="ec-connections-layout">
          <article class="console-card ec-panel">
            <div class="card-head">
              <div>
                <p class="eyebrow">Connector manager</p>
                <h2>Integration actions</h2>
              </div>
              <button class="btn" type="button" @click="showConnectorForm = !showConnectorForm">
                {{ showConnectorForm ? 'Close' : 'Add connector' }}
              </button>
            </div>
            <form v-if="showConnectorForm || editingConnectorId" class="ec-form" @submit.prevent="createConnector">
              <label>Name<input v-model="connectorForm.name" placeholder="Approved Content Store" /></label>
              <label>Scope<input v-model="connectorForm.scope" placeholder="Documents, metadata, approvals" /></label>
              <label>Auth method<input v-model="connectorForm.auth_method" placeholder="OAuth 2.0" /></label>
              <label>Owner<input v-model="connectorForm.owner" placeholder="Platform Governance" /></label>
              <label>Status<select v-model="connectorForm.status"><option>candidate</option><option>planned</option><option>connected</option><option>disabled</option></select></label>
              <button class="btn" type="submit">{{ editingConnectorId ? 'Save connector' : 'Add connector' }}</button>
            </form>
            <div v-else class="connector-empty-state">
              <span><IconGlyph name="integration" /></span>
              <strong>Add, test, disable, rotate, or remove enterprise connectors from one place.</strong>
              <small>OAuth, webhook, API, OCR, IAM, and content repository integrations are tracked with owner, health, scopes, and audit events.</small>
            </div>
            <p v-if="connectionMessage" class="form-success">{{ connectionMessage }}</p>
            <p v-if="connectionError" class="form-alert">{{ connectionError }}</p>
          </article>

          <article class="console-card ec-panel wide">
            <div class="card-head">
              <div>
                <p class="eyebrow">Connected apps</p>
                <h2>Manage integrations</h2>
              </div>
            </div>
            <div class="ec-connector-grid">
              <article v-for="connection in connections" :key="connection.id" class="ec-connector-card" :class="connection.status">
                <div class="ec-connector-head">
                  <span class="connector-logo" :style="{ background: connection.logo_color || '#eef4ff', color: connection.logo_color ? '#fff' : '#315ddc' }">
                    {{ connection.logo_text || '' }}
                    <IconGlyph v-if="!connection.logo_text" :name="connection.icon || 'integration'" />
                  </span>
                  <div>
                    <strong>{{ connection.name }}</strong>
                    <small>{{ connection.owner }} · {{ connection.auth_method }}</small>
                  </div>
                  <em>{{ connection.health }}%</em>
                </div>
                <p>{{ connection.scope }}</p>
                <div class="ec-scope-list">
                  <span v-for="scope in connection.scopes" :key="scope">{{ scope }}</span>
                </div>
                <footer>
                  <button class="btn inverse" type="button" @click="testConnector(connection)">Test</button>
                  <button class="btn inverse" type="button" @click="editConnector(connection)">Edit</button>
                  <button class="btn ghost" type="button" @click="toggleConnector(connection)">{{ connection.status === 'disabled' ? 'Enable' : 'Disable' }}</button>
                  <button class="btn ghost danger" type="button" @click="deleteConnector(connection)">Delete</button>
                </footer>
                <small>{{ connection.last_event }} · {{ connection.last_sync }}</small>
              </article>
            </div>
          </article>
        </div>
      </section>

      <section v-else-if="activeView === 'audit'" class="col-view ec-view">
        <article class="console-card ec-panel">
          <div class="card-head">
            <div>
              <p class="eyebrow">Inspectable event ledger</p>
              <h2>Audit Trail</h2>
            </div>
            <button class="btn inverse" type="button" @click="loadAudit">Refresh</button>
          </div>
          <div class="ec-audit-filters">
            <input v-model="auditFilters.q" placeholder="Search event, source, evidence" @input="loadAudit" />
            <input v-model="auditFilters.actor" placeholder="User ID or email" @input="loadAudit" />
            <select v-model="auditFilters.severity" @change="loadAudit"><option value="">All severity</option><option>low</option><option>medium</option><option>high</option></select>
            <select v-model="auditFilters.stage" @change="loadAudit"><option value="">All stages</option><option v-for="stage in stages" :key="stage.id">{{ stage.name }}</option></select>
            <select v-model="auditFilters.source_system" @change="loadAudit"><option value="">All sources</option><option v-for="source in auditSourceSystems" :key="source">{{ source }}</option></select>
            <button class="btn inverse" type="button" @click="clearAuditFilters">Clear filters</button>
          </div>
          <p class="ledger-count">{{ auditEvents.length }} event records match the current filter.</p>
          <div class="ec-ledger">
            <article v-for="event in auditEvents" :key="event.id" class="ec-ledger-row" :class="event.severity || 'low'">
              <span>{{ event.id }}</span>
              <div>
                <strong>{{ event.stage }}</strong>
                <p>{{ event.action || event.trigger }} · {{ event.decision }}</p>
                <small>{{ event.timestamp }} · {{ event.actor_id || 'SYSTEM' }} · {{ event.actor_email || event.actor || event.reviewer }} · {{ event.source_system || event.trigger }}</small>
              </div>
              <em>{{ event.final_recommendation }}</em>
              <details>
                <summary>Evidence</summary>
                <p>{{ event.reason }}</p>
                <small>{{ (event.evidence_links || []).join(', ') || event.agent_output }}</small>
              </details>
            </article>
            <article v-if="!auditEvents.length" class="empty-ledger">
              <strong>No audit events found</strong>
              <small>Clear filters or search by stage, source system, user ID, evidence ID, decision, or asset ID.</small>
            </article>
          </div>
        </article>
      </section>

      <section v-else-if="activeView === 'profile'" class="col-view ec-view">
        <div class="profile-page-grid">
          <article class="console-card ec-panel">
            <div class="profile-hero">
              <span><IconGlyph name="users" /></span>
              <div>
                <p class="eyebrow">User access center</p>
                <h2>{{ currentUser.name }}</h2>
                <p>{{ currentUser.email }}</p>
              </div>
            </div>
            <div class="profile-detail-grid">
              <div><span>Role</span><strong>{{ currentUser.role.replace('_', ' ') }}</strong></div>
              <div><span>Team</span><strong>{{ currentUser.team }}</strong></div>
              <div><span>Workflow Access</span><strong>{{ visibleStages.length }} visible stages</strong></div>
              <div><span>Stage Access</span><strong>{{ currentUser.stage_access?.length || visibleStages.length }} stages</strong></div>
            </div>
          </article>
          <article class="console-card ec-panel">
            <p class="eyebrow">Security</p>
            <h2>Change password</h2>
            <form class="admin-form" @submit.prevent="changeOwnPassword">
              <label>Current password<input v-model="profilePasswordForm.current" type="password" /></label>
              <label>New password<input v-model="profilePasswordForm.next" type="password" /></label>
              <button class="btn" type="submit">Update password</button>
            </form>
            <p v-if="profileMessage" class="form-success">{{ profileMessage }}</p>
            <p v-if="profileError" class="form-alert">{{ profileError }}</p>
          </article>
          <article class="console-card ec-panel profile-permissions-card">
            <p class="eyebrow">Permission sets</p>
            <h2>RBAC features</h2>
            <div class="ec-permission-grid">
              <span v-for="permission in currentUser.permission_sets" :key="permission">{{ permission }}</span>
              <span v-for="group in currentUser.role_groups" :key="group">{{ group }}</span>
            </div>
          </article>
        </div>
      </section>

      <section v-else-if="activeView === 'users' && isAdmin" class="col-view ec-view">
        <div class="ec-user-tabs">
          <button v-for="tab in userTabs" :key="tab.id" :class="{ active: activeUserTab === tab.id }" type="button" @click="activeUserTab = tab.id">{{ tab.label }}</button>
        </div>
        <div class="manage-users-grid ec-users-grid">
          <article class="console-card ec-panel">
            <div class="card-head compact">
              <div>
                <p class="eyebrow">{{ isSuperAdmin ? 'Super admin' : 'Admin' }}</p>
                <h2>User actions</h2>
              </div>
              <button class="btn" type="button" @click="showUserCreateForm = !showUserCreateForm">
                {{ showUserCreateForm ? 'Close' : 'Create user' }}
              </button>
            </div>
            <form v-if="showUserCreateForm" class="admin-form" @submit.prevent="createManagedUser">
              <label>Name<input v-model="createUserForm.name" placeholder="Sana Iyer" /></label>
              <label>Email<input v-model="createUserForm.email" placeholder="sana.review@medguard.ai" type="email" /></label>
              <label>Role<select v-model="createUserForm.role"><option v-for="role in managedRoleOptions" :key="role.id" :value="role.id">{{ role.label }}</option></select></label>
              <label>Persona<input v-model="createUserForm.persona" placeholder="Regional reviewer" /></label>
              <label>Team<input v-model="createUserForm.team" placeholder="Affiliate operations" /></label>
              <button class="btn" :disabled="adminLoading" type="submit">Create user</button>
            </form>
            <div v-else class="connector-empty-state">
              <span><IconGlyph name="users" /></span>
              <strong>Create, deactivate, delete, reset, and assign stage access for MedGuard users.</strong>
              <small>Use the account table to manage active users, deactivated users, invited users, role sets, and security actions.</small>
            </div>
          </article>

          <article class="console-card ec-panel wide">
            <div class="card-head">
              <div>
                <p class="eyebrow">{{ activeUserTabLabel }}</p>
                <h2>{{ filteredUsers.length }} accounts</h2>
              </div>
              <button class="btn inverse" type="button" @click="loadManagedUsers">Refresh</button>
            </div>
            <div class="ec-user-list">
              <article v-for="user in filteredUsers" :key="user.id" class="ec-user-row">
                <div class="user-identity">
                  <span>{{ initials(user.name) }}</span>
                  <div>
                    <strong>{{ user.name }}</strong>
                    <small>{{ user.id }} · {{ user.email }}</small>
                  </div>
                </div>
                <div class="user-tags">
                  <span class="role-badge">{{ user.role.replace('_', ' ') }}</span>
                  <span class="status-badge" :class="user.status">{{ user.status }}</span>
                  <span class="role-badge">{{ user.stage_access?.length || 0 }} stages</span>
                  <span v-if="user.password" class="role-badge">Password: {{ user.password }}</span>
                </div>
                <div class="ec-user-access">
                  <select v-model="accessDrafts[user.id].role">
                    <option v-for="role in managedRoleOptions" :key="role.id" :value="role.id">{{ role.label }}</option>
                  </select>
                  <input v-model="passwordDrafts[user.id]" placeholder="New password" type="password" />
                  <button class="btn inverse" type="button" @click="saveUserAccess(user)">Save access</button>
                  <button class="btn inverse" type="button" @click="changeUserPassword(user)">Change</button>
                  <button class="btn inverse" type="button" @click="resetUserPassword(user)">Reset</button>
                  <button class="btn ghost" type="button" @click="toggleUserStatus(user)">{{ user.status === 'active' ? 'Deactivate' : 'Activate' }}</button>
                  <button class="btn ghost danger" type="button" @click="deleteManagedUser(user)">Delete</button>
                </div>
              </article>
            </div>
            <p v-if="adminMessage" class="form-success">{{ adminMessage }}</p>
            <p v-if="adminError" class="form-alert">{{ adminError }}</p>
          </article>
        </div>
      </section>

    </section>
  </main>
</template>

<script setup lang="ts">
type UserRole = 'super_admin' | 'admin' | 'workflow_owner' | 'content_author' | 'medical_reviewer' | 'regulatory_reviewer' | 'compliance_reviewer' | 'legal_reviewer' | 'local_market_reviewer' | 'qa_specialist' | 'approver' | 'audit_viewer' | 'user'
type UserStatus = 'active' | 'inactive'
type TaskStatus = 'queued' | 'in_progress' | 'blocked' | 'complete'
type Risk = 'low' | 'medium' | 'high'
type AppUser = {
  id: string
  name: string
  email: string
  role: UserRole
  persona: string
  team: string
  status: UserStatus
  modules: string[]
  last_login: string
  password?: string
  permission_sets?: string[]
  role_groups?: string[]
  markets?: string[]
  stage_access?: string[]
}
type AuthResponse = { token: string; user: AppUser }
type StageTask = { id: string; title: string; owner: string; status: TaskStatus; priority: 'High' | 'Medium' | 'Low'; analysis: string; next_action: string; stage?: string }
type CheckItem = { name?: string; claim?: string; status: string; score?: number; detail?: string; evidence?: string }
type StageValidation = { stage_id: string; risk_score: number; validation_score: number; decision: string; findings: CheckItem[]; recommended_action: string; suggested_fixes: string[]; trace: Array<Record<string, unknown>>; sources: SourceItem[] }
type SourceItem = { id: string; title: string; type: string; confidence: number }
type RuleStepStatus = 'queued' | 'running' | 'passed' | 'rework' | 'blocked' | 'failed'
type RuleStep = {
  id: string
  order: number
  name: string
  category: string
  mandatory: boolean
  critical: boolean
  status: RuleStepStatus
  score: number
  progress: number
  summary: string
  findings: string[]
  risk_flags: string[]
  suggested_fix: string
  confidence: number
  model_used: string
  mode: string
  source_refs: string[]
  static_rules: string[]
  kpis: Record<string, number>
  human_approval: { status: string; actor: string; reason: string; timestamp: string }
}
type RuleRun = {
  run_id: string
  content_id: string
  stage_id: string
  stage: string
  purpose: string
  threshold: number
  stage_score: number
  status: 'PASS' | 'REWORK' | 'BLOCK'
  mandatory_checks_passed: number
  mandatory_checks_total: number
  critical_blockers: string[]
  risk_flags: string[]
  kpis: Record<string, number>
  reviewer_action_required: boolean
  audit_id: string
  steps: RuleStep[]
  media: SampleMedia[]
  selected_documents?: LibraryDocument[]
  model_profile?: AIModelProfile
  approval: { status: string; actor: string; reason: string; timestamp: string }
}
type RuleStageTemplate = { stage_id: string; threshold: number; purpose: string; steps: Array<Record<string, any>> }
type NotificationItem = { id: string; stage_id: string; stage: string; title: string; message: string; severity: Risk; timestamp: string; read: boolean }
type SampleMedia = { id: string; name: string; type: string; mime_type: string; url?: string; thumbnail_url?: string; source_system?: string; connector_status?: string; stage_ids: string[]; preview: string; checks: string[]; risk_notes: string[] }
type ReportBlock =
  | { type: 'heading'; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'list'; items: string[] }
  | { type: 'table'; headers: string[]; rows: string[][] }
type Stage = {
  id: string
  order: number
  name: string
  trigger: string
  system: string
  score: number
  validation_score: number
  risk: Risk
  status: string
  sla: string
  recommendation: string
  issues: string[]
  output: string
  engine_label: string
  flow_scope: string
  default_model_profile: string
  active_model: AIModelProfile
  required_documents: string[]
  available_documents: string[]
  model_profiles: AIModelProfile[]
  modules: string[]
  tasks: StageTask[]
  task_count: number
  open_task_count: number
  asset_id: string
  brand: string
  content_type?: string
  market: string
  channel: string
  inputs: Array<{ name: string; value: string; source: string }>
  outputs: Array<{ name: string; value: string; detail: string }>
  sources: SourceItem[]
  validation_checks: CheckItem[]
  regulatory_checks: CheckItem[]
  claim_verifiers: CheckItem[]
  security_checks: CheckItem[]
  stage_kpis: Array<{ label: string; value: string; trend: string }>
  review_actions: Array<{ id: string; label: string; impact: string }>
  agent_trace: Array<Record<string, unknown>>
  last_validation?: StageValidation
  last_rule_run?: RuleRun
  stage_output_document?: StageOutputDocument
}
type Connection = { id: string; name: string; logo_text?: string; logo_color?: string; icon?: string; scope: string; status: 'connected' | 'planned' | 'candidate' | 'disabled'; health: number; auth_method: string; owner: string; scopes: string[]; handoff: string; last_event: string; last_sync: string; latency_ms: number; actions: string[] }
type AuditEvent = { id: string; stage: string; trigger: string; severity?: Risk; source_system?: string; asset_id?: string; actor?: string; actor_id?: string; actor_email?: string; action?: string; agent_output: string; decision: string; reviewer: string; reason: string; timestamp: string; final_recommendation: string; evidence_links?: string[] }
type ArchitectureItem = { name: string; detail?: string; status?: string; system?: string; payload?: string; items?: string[]; checks?: string[]; output?: string; owner?: string }
type ArchitectureFlow = { summary: { title: string; description: string; flow: string[] }; connected_systems: ArchitectureItem[]; validation_workflow: ArchitectureItem[] }
type Dashboard = {
  filters: Record<string, string[]>
  kpi_cards: Array<{ group: string; label: string; value: string; trend: string; status: string }>
  workflow_funnel: Array<{ stage: string; count: number; blocked: number; score: number; flow?: string }>
  market_heatmap: Array<{ market: string; flag?: string; risk: Risk; score: number; assets?: number; blocked?: number; sla?: string }>
  sla_timeline: Array<{ label: string; sla: string; risk: Risk; status: string }>
  blocker_distribution: Array<{ label: string; value: number }>
  task_summary: { open: number; blocked: number; complete: number; high_priority: number }
  audit_exceptions: AuditEvent[]
  rule_engine?: { configured_stages: number; runs_today: number; pending_approvals: number; open_notifications: number; gemini_available: boolean }
  notifications?: NotificationItem[]
  approval_tracker?: Array<Record<string, unknown>>
  dashboard_depth?: Record<string, Array<{ label: string; value: string }>>
}
type AIModelProfile = { id: string; label: string; model: string; display?: string; speed: string; depth: string; detail: string; capabilities?: string[]; confidence_bias?: number }
type LibraryDocument = {
  id: string
  title: string
  source_id: string
  source_name: string
  brand: string
  document_type: string
  region: string
  market: string
  channel: string
  approval_status: string
  version: string
  effective_date: string
  updated_at: string
  url?: string
  external_url?: string
  taxonomy: string[]
  claims: string[]
  summary: string
  preview: string
  evidence_strength: number
  stage_ids: string[]
}
type DocumentFacets = { sources: Array<Record<string, any>>; brands: string[]; document_types: string[]; regions: string[]; markets: string[]; channels: string[]; approval_statuses: string[] }
type DocumentSearchResponse = { documents: LibraryDocument[]; facets: DocumentFacets; total: number }
type InputBundle = { id: string; name: string; stage_id: string; document_ids: string[]; documents: LibraryDocument[]; taxonomy: string[]; approval_status: string; created_by: string; created_at: string; notes: string }
type DocumentCompareResult = { documents: LibraryDocument[]; shared_taxonomy: string[]; conflicts: string[]; recommendation: string }
type StageOutputDocument = { id: string; stage_id: string; stage: string; title: string; document_type: string; version: string; status: string; created_by: string; created_at: string; content: string; next_stage_id: string; audit_id: string; source_documents: string[] }

useHead({ title: 'MedGuard' })

const activeView = ref('dashboard')
const currentUser = ref<AppUser | null>(null)
const authLoading = ref(false)
const adminLoading = ref(false)
const stageRunLoading = ref(false)
const authError = ref('')
const ssoMessage = ref('')
const adminError = ref('')
const adminMessage = ref('')
const decisionMessage = ref('')
const decisionError = ref('')
const connectionMessage = ref('')
const connectionError = ref('')
const overrideReason = ref('')
const stages = ref<Stage[]>([])
const selectedStageId = ref('')
const connections = ref<Connection[]>([])
const dashboard = ref<Dashboard | null>(null)
const auditEvents = ref<AuditEvent[]>([])
const managedUsers = ref<AppUser[]>([])
const architectureFlow = ref<ArchitectureFlow | null>(null)
const ruleStageTemplates = ref<RuleStageTemplate[]>([])
const ruleRuns = ref<RuleRun[]>([])
const notifications = ref<NotificationItem[]>([])
const sampleMedia = ref<SampleMedia[]>([])
const aiModels = ref<AIModelProfile[]>([])
const libraryDocuments = ref<LibraryDocument[]>([])
const contentLibraryDocuments = ref<LibraryDocument[]>([])
const documentFacets = reactive<DocumentFacets>({ sources: [], brands: [], document_types: [], regions: [], markets: [], channels: [], approval_statuses: [] })
const selectedDocumentIds = ref<string[]>([])
const activePreviewDocument = ref<LibraryDocument | null>(null)
const activePreviewMedia = ref<SampleMedia | null>(null)
const activeBundle = ref<InputBundle | null>(null)
const workflowBundle = ref<InputBundle | null>(null)
const compareResult = ref<DocumentCompareResult | null>(null)
const stageOutputs = ref<StageOutputDocument[]>([])
const sidebarHidden = ref(false)
const showWorkflowPanel = ref(true)
const activeCheckTab = ref('validation_checks')
const activeDashboardGroup = ref('Compliance')
const activeUserTab = ref('active')
const editingConnectorId = ref('')
const showConnectorForm = ref(false)
const showUserCreateForm = ref(false)
const showNotificationMenu = ref(false)
const runButtonPulse = ref(false)
const damSourceFilter = ref('All sources')
const activeImcpName = ref('Intent')
const passwordDrafts = reactive<Record<string, string>>({})
const accessDrafts = reactive<Record<string, { role: UserRole; team: string; persona: string }>>({})
const filterState = reactive<Record<string, string>>({})
const auditFilters = reactive({ q: '', severity: '', stage: '', actor: '', source_system: '' })
const loginForm = reactive({ email: '', password: '' })
const profileMessage = ref('')
const profileError = ref('')
const profilePasswordForm = reactive({ current: '', next: '' })
const createUserForm = reactive({ name: '', email: '', role: 'content_author' as UserRole, persona: '', team: '' })
const connectorForm = reactive({ name: '', scope: '', auth_method: 'OAuth 2.0', owner: 'Platform Governance', status: 'candidate' as Connection['status'], icon: 'integration', scopes: ['metadata.read', 'audit.write'] })
const ruleDecisionReason = ref('')
const ruleDecisionCode = ref('reviewer-confirmed')
const damForm = reactive({ name: '', type: 'Reference Pack', source_system: 'Veeva Vault', url: '', preview: '' })
const selectedModelProfile = ref('balanced')
const actionCommand = ref('')
const ruleStepComments = reactive<Record<string, string>>({})
const bundleName = ref('')
const bundleMessage = ref('')
const bundleError = ref('')
const documentSearch = reactive({ q: '', brand: '', document_type: '', region: '', market: '', channel: '', approval_status: '', source_id: '' })
const ruleProgress = reactive<Record<string, { running: boolean; activeIndex: number; statuses: Record<string, RuleStepStatus>; percent: number }>>({})
type LockedSelectorKey = 'brand' | 'market' | 'channel' | 'contentType'
type LockedOption = { label: string; value: string; locked?: boolean }
const fixedWorkflowContext = {
  brand: 'Respivara',
  market: 'India',
  channels: ['Veeva CRM', 'Vault', 'Litmus'],
  contentTypes: ['Campaign Brief', 'Email', 'CLM / eDetail Aid', 'HCP Leave Behind']
}
const lockedSelection = reactive<Record<LockedSelectorKey, string>>({
  brand: fixedWorkflowContext.brand,
  market: fixedWorkflowContext.market,
  channel: fixedWorkflowContext.channels[0],
  contentType: fixedWorkflowContext.contentTypes[0]
})
const lockedAllowList: Record<LockedSelectorKey, Set<string>> = {
  brand: new Set([fixedWorkflowContext.brand]),
  market: new Set([fixedWorkflowContext.market]),
  channel: new Set(fixedWorkflowContext.channels),
  contentType: new Set(fixedWorkflowContext.contentTypes)
}
const lockedSelectorGroups: Array<{ key: LockedSelectorKey; label: string; options: LockedOption[] }> = [
  { key: 'brand', label: 'Brand', options: ['Respivara', 'Cardiava', 'Immunava', 'Dermexa', 'Neurovance'].map(value => ({ label: value, value, locked: !lockedAllowList.brand.has(value) })) },
  { key: 'market', label: 'Market', options: ['India', 'Global', 'US', 'UK', 'Saudi Arabia', 'Germany', 'Brazil'].map(value => ({ label: value, value, locked: !lockedAllowList.market.has(value) })) },
  { key: 'channel', label: 'Channel', options: ['Veeva CRM', 'Vault', 'Litmus', 'Agency DAM', 'SharePoint', 'Web portal', 'Print'].map(value => ({ label: value, value, locked: !lockedAllowList.channel.has(value) })) },
  { key: 'contentType', label: 'Content type', options: ['Campaign Brief', 'Email', 'CLM / eDetail Aid', 'HCP Leave Behind', 'Landing page', 'Publication Plan', 'Policy Pack', 'Social Asset'].map(value => ({ label: value, value, locked: !lockedAllowList.contentType.has(value) })) }
]
const chartPalette = ['#7aa7d9', '#7bb9aa', '#d8b56f', '#c98a86', '#a99bd6', '#82b7c7', '#c894b2']

const isAdmin = computed(() => currentUser.value?.role === 'admin' || currentUser.value?.role === 'super_admin')
const isSuperAdmin = computed(() => currentUser.value?.role === 'super_admin')
const canSeeFullWorkflow = computed(() => isAdmin.value)
const canViewConnections = computed(() => isAdmin.value || !!currentUser.value?.modules.includes('integration-layer'))
const showGlobalContextControls = computed(() => ['dashboard', 'workflow'].includes(activeView.value))
const navItems = computed(() => {
  const items = [
    { id: 'dashboard', label: 'Dashboard', icon: 'home' },
    { id: 'workflow', label: 'Authorization Workflow', icon: 'workflow' },
    { id: 'dam', label: 'DAM', icon: 'asset' },
    { id: 'library', label: 'Content Library', icon: 'content' },
    { id: 'imcp', label: 'IMCP', icon: 'claims' },
    ...(canViewConnections.value ? [{ id: 'connections', label: 'Connections', icon: 'integration' }] : []),
    { id: 'audit', label: 'Audit Trail', icon: 'evidence' },
    { id: 'profile', label: 'Profile', icon: 'settings' },
    ...(isAdmin.value ? [{ id: 'users', label: 'Users', icon: 'users' }] : [])
  ]
  return items
})
const visibleStages = computed(() => {
  if (!currentUser.value) return []
  if (canSeeFullWorkflow.value) return stages.value
  const access = new Set(currentUser.value.stage_access || [])
  if (access.size) return stages.value.filter(stage => access.has(stage.id))
  const moduleSet = new Set(currentUser.value.modules)
  return stages.value.filter(stage => stage.modules.some(module => moduleSet.has(module)))
})
const selectedStage = computed(() => visibleStages.value.find(stage => stage.id === selectedStageId.value) || visibleStages.value[0])
const activeFlowScope = computed(() => {
  if (!selectedStage.value) return ''
  return selectedStage.value.order <= 4 ? 'global' : 'local'
})
const workflowStageGroups = computed(() => [
  {
    id: 'global',
    title: 'Global Stage',
    range: 'Stages 1-4',
    stages: visibleStages.value.filter(stage => stage.order <= 4)
  },
  {
    id: 'local',
    title: 'Local Stage',
    range: 'Stages 5-8',
    stages: visibleStages.value.filter(stage => stage.order >= 5)
  }
].filter(group => group.stages.length))
const activeModel = computed(() => aiModels.value.find(model => model.id === selectedModelProfile.value) || aiModels.value[0])
const stageModelDisplay = computed(() => selectedStage.value?.active_model?.display || activeModel.value?.display || activeModel.value?.label || 'Automatic model')
const selectedRuleTemplate = computed(() => ruleStageTemplates.value.find(item => item.stage_id === selectedStage.value?.id))
const selectedRuleRun = computed(() => {
  const stageId = selectedStage.value?.id
  if (!stageId) return null
  return ruleRuns.value.find(run => run.stage_id === stageId) || selectedStage.value?.last_rule_run || null
})
const selectedRuleSteps = computed<RuleStep[]>(() => {
  if (selectedRuleRun.value) return selectedRuleRun.value.steps
  return (selectedRuleTemplate.value?.steps || []).map((step, index) => ({
    id: String(step.id),
    order: index + 1,
    name: String(step.name),
    category: String(step.category),
    mandatory: Boolean(step.mandatory),
    critical: Boolean(step.critical),
    status: 'queued',
    score: Number(step.static_score || 0),
    progress: 0,
    summary: 'Waiting for validation run.',
    findings: [],
    risk_flags: [],
    suggested_fix: '',
    confidence: 0,
    model_used: '',
    mode: '',
    source_refs: (step.source_refs || []) as string[],
    static_rules: (step.static_rules || []) as string[],
    kpis: (step.kpis || {}) as Record<string, number>,
    human_approval: { status: 'pending', actor: '', reason: '', timestamp: '' }
  }))
})
function matchesSelectedContentType(text: string) {
  const haystack = text.toLowerCase()
  const aliases: Record<string, string[]> = {
    'Campaign Brief': ['campaign brief', 'brief', 'planning pack'],
    'Email': ['email', 'approved email', 'email html', 'litmus'],
    'CLM / eDetail Aid': ['clm', 'edetail', 'e-detail', 'detail aid', 'storyboard'],
    'HCP Leave Behind': ['leave behind', 'brochure', 'handout', 'print']
  }
  return (aliases[lockedSelection.contentType] || [lockedSelection.contentType]).some(term => haystack.includes(term.toLowerCase()))
}
const selectedMedia = computed(() => {
  const stageId = selectedStage.value?.id
  const stageMedia = sampleMedia.value.filter(item => !stageId || item.stage_ids.includes(stageId))
  const contentMedia = stageMedia.filter(item => matchesSelectedContentType(`${item.name} ${item.type} ${item.preview} ${(item.checks || []).join(' ')}`))
  return contentMedia.length ? contentMedia : stageMedia
})
function documentIdentity(doc: LibraryDocument) {
  return `${doc.title} ${doc.document_type}`.toLowerCase()
}
function isValidationSourceDocument(doc: LibraryDocument) {
  const identity = documentIdentity(doc)
  const taxonomy = (doc.taxonomy || []).join(' ').toLowerCase()
  const validationTerms = [
    'validation',
    'qa report',
    'support pack',
    'supporting documents',
    'matrix',
    'test cases',
    'smpc',
    'prescribing',
    'safety',
    'clinical',
    'claim library',
    'local disclaimer',
    'promotional rules',
    'print qa',
    'policy',
    'sop',
    'litmus',
    'approval',
    'qr',
    'distribution',
    'metadata and audience control',
    'publication and evidence',
    'speaker disclosure'
  ]
  return validationTerms.some(term => identity.includes(term) || taxonomy.includes(term))
}
const primaryStageDocuments = computed(() => {
  const contentNeedles = {
    'Campaign Brief': ['campaign brief', 'hcp campaign brief', 'omnichannel hcp campaign brief', 'veeva crm hcp campaign brief'],
    'Email': ['approved email copy deck', 'email brief and plan', 'hcp approved email', 'email html package'],
    'CLM / eDetail Aid': ['clm / edetail aid brief', 'clm / edetail aid screen storyboard', 'clm storyboard', 'edetail storyboard'],
    'HCP Leave Behind': ['hcp leave behind brief', 'hcp leave behind content master', 'leave behind pdf']
  }[lockedSelection.contentType] || []
  return libraryDocuments.value.filter(doc => {
    const haystack = `${doc.title} ${doc.summary} ${doc.preview} ${(doc.taxonomy || []).join(' ')}`.toLowerCase()
    return !isValidationSourceDocument(doc) && contentNeedles.some(needle => haystack.includes(needle))
  })
})
const validationStageDocuments = computed(() => {
  const primaryIds = new Set(primaryStageDocuments.value.map(doc => doc.id))
  const validationDocs = libraryDocuments.value.filter(doc => !primaryIds.has(doc.id) && isValidationSourceDocument(doc))
  return validationDocs.length ? validationDocs : libraryDocuments.value.filter(doc => !primaryIds.has(doc.id))
})
const documentPanelLocked = computed(() => !!selectedStage.value && selectedStage.value.order > 1 && !!workflowBundle.value)
const selectedValidationDocuments = computed(() => {
  if (activeBundle.value?.documents?.length) return activeBundle.value.documents
  return libraryDocuments.value.filter(doc => selectedDocumentIds.value.includes(doc.id))
})
const allLibraryDocuments = computed(() => contentLibraryDocuments.value.length ? contentLibraryDocuments.value : libraryDocuments.value)
const selectedStageNotifications = computed(() => {
  const stageId = selectedStage.value?.id
  return notifications.value.filter(item => item.stage_id === stageId).slice(0, 4)
})
const ruleUiState = computed(() => selectedStage.value ? ruleProgress[selectedStage.value.id] : undefined)
const visibleTasks = computed(() => visibleStages.value.flatMap(stage => stage.tasks.map(task => ({ ...task, stage: stage.name }))))
const rootCauseSegments = computed(() => (dashboard.value?.blocker_distribution || []).map((item, index) => ({ ...item, color: chartPalette[index % chartPalette.length] })))
const rootCauseTotal = computed(() => rootCauseSegments.value.reduce((sum, item) => sum + item.value, 0))
const rootCauseDeepDive = computed(() => dashboard.value?.dashboard_depth?.root_cause || [])
const pieGradient = computed(() => {
  if (!rootCauseTotal.value) return '#eef2f7'
  let cursor = 0
  const stops = rootCauseSegments.value.map(item => {
    const start = cursor
    cursor += (item.value / rootCauseTotal.value) * 100
    return `${item.color} ${start}% ${cursor}%`
  })
  return `conic-gradient(${stops.join(', ')})`
})
const throughputBars = computed(() => {
  const items = dashboard.value?.workflow_funnel || []
  const maxCount = Math.max(1, ...items.map(item => item.count))
  return items.map((item, index) => ({
    ...item,
    short: `S${index + 1}`,
    color: chartPalette[index % chartPalette.length],
    height: Math.max(18, Math.round((item.count / maxCount) * 100))
  }))
})
const throughputDeepDive = computed(() => dashboard.value?.dashboard_depth?.throughput || [])
const slaRiskRows = computed(() => (dashboard.value?.sla_timeline || []).map(item => {
  const text = `${item.sla} ${item.status}`.toLowerCase()
  const severity = text.includes('overdue') || item.status === 'blocked'
    ? 'critical'
    : item.risk === 'high'
      ? 'high'
      : item.risk === 'medium' || text.includes('remaining')
        ? 'medium'
        : 'low'
  return { ...item, severity }
}))
const ganttDays = ['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7']
const ganttTasks = computed(() => visibleTasks.value.slice(0, 8).map((task, index) => {
  const completeDays = task.status === 'complete' ? 7 : task.status === 'in_progress' ? 4 : task.status === 'blocked' ? 2 : 1
  return {
    ...task,
    cells: ganttDays.map((day, dayIndex) => ({
      day,
      state: dayIndex < completeDays ? 'complete' : task.status === 'blocked' || dayIndex >= 5 - (index % 2) ? 'remaining critical' : 'remaining'
    }))
  }
}))
const validationOps = computed(() => [
  { label: 'Configured stages', value: String(dashboard.value?.rule_engine?.configured_stages || 0), progress: 100, detail: 'Rules active across workflow', tone: 'good' },
  { label: 'Runs today', value: String(dashboard.value?.rule_engine?.runs_today || 0), progress: Math.min(100, (dashboard.value?.rule_engine?.runs_today || 0) * 18), detail: 'Validation activity', tone: 'info' },
  { label: 'Human approvals', value: String(dashboard.value?.rule_engine?.pending_approvals || 0), progress: Math.min(100, (dashboard.value?.rule_engine?.pending_approvals || 0) * 22), detail: 'Awaiting reviewer action', tone: 'watch' },
  { label: 'Model status', value: dashboard.value?.rule_engine?.gemini_available ? 'On' : 'Fallback', progress: dashboard.value?.rule_engine?.gemini_available ? 96 : 42, detail: 'Gemini validation layer', tone: dashboard.value?.rule_engine?.gemini_available ? 'good' : 'watch' }
])
const validationOpsDeepDive = computed(() => dashboard.value?.dashboard_depth?.validation_operations || [])
const auditExceptionRows = computed(() => dashboard.value?.audit_exceptions?.slice(0, 5) || [])
const auditDeepDive = computed(() => dashboard.value?.dashboard_depth?.audit_exceptions || [])
const dashboardFilters = computed(() => {
  const allowed = ['markets', 'brands', 'content_types', 'risks', 'channels', 'date_range']
  const filters = dashboard.value?.filters || {}
  return Object.fromEntries(allowed.map(key => [key, filters[key] || []]).filter(([, values]) => Array.isArray(values) && values.length))
})
const dashboardKpis = computed(() => dashboard.value?.kpi_cards || [])
const unreadNotifications = computed(() => notifications.value.filter(note => !note.read).length)
const latestStageOutput = computed(() => stageOutputs.value[0] || selectedStage.value?.stage_output_document || null)
const outputReportBlocks = computed(() => parseReportContent(latestStageOutput.value?.content || ''))
const auditSourceSystems = computed(() => Array.from(new Set(auditEvents.value.map(event => event.source_system).filter(Boolean))) as string[])
const checkTabs = [
  { id: 'validation_checks', label: 'Validation' },
  { id: 'regulatory_checks', label: 'Regulatory' },
  { id: 'claim_verifiers', label: 'Claims' },
  { id: 'security_checks', label: 'Security' }
]
const activeChecks = computed(() => selectedStage.value ? ((selectedStage.value as any)[activeCheckTab.value] || []) : [])
const userTabs = [
  { id: 'active', label: 'Active' },
  { id: 'inactive', label: 'Deactivated' },
  { id: 'new', label: 'Invited/New' },
  { id: 'roles', label: 'Roles & Permission Sets' },
  { id: 'security', label: 'Security Actions' }
]
const managedRoleOptions: Array<{ id: UserRole; label: string }> = [
  { id: 'workflow_owner', label: 'Workflow Owner' },
  { id: 'content_author', label: 'Content Author' },
  { id: 'medical_reviewer', label: 'Medical Reviewer' },
  { id: 'regulatory_reviewer', label: 'Regulatory Reviewer' },
  { id: 'compliance_reviewer', label: 'Compliance Reviewer' },
  { id: 'legal_reviewer', label: 'Legal Reviewer' },
  { id: 'local_market_reviewer', label: 'Local Market Reviewer' },
  { id: 'qa_specialist', label: 'QA / Channel Specialist' },
  { id: 'approver', label: 'Approver' },
  { id: 'audit_viewer', label: 'Audit Viewer' },
  { id: 'admin', label: 'Admin' },
  { id: 'super_admin', label: 'Super Admin' }
]
const imcpFramework = [
  { name: 'Intent', icon: 'strategy', description: 'Business objective, audience, channel, market, and message intent.', items: ['Campaign brief', 'Audience plan', 'Channel strategy', 'Owner matrix'], sections: [
    { title: 'Purpose', lines: ['Define brand objective, approved audience, market scope, channel fit, and commercial/medical boundaries.', 'Map campaign objective to validated source documents before any stage validation begins.'] },
    { title: 'Required records', lines: ['Campaign brief, target audience definition, channel plan, owner matrix, timeline, and decision rights.', 'Every selected source receives an IMCP taxonomy tag and bundle ID.'] },
    { title: 'Controls', lines: ['Brief completeness, indication fit, audience eligibility, source readiness, and stage handoff lock.'] },
  ] },
  { name: 'Medical', icon: 'pharma', description: 'Scientific claim, evidence, safety, and reviewer-ready medical lineage.', items: ['SmPC / PI', 'Clinical study report', 'Claim matrix', 'Safety statement'], sections: [
    { title: 'Purpose', lines: ['Create claim registry, evidence links, label alignment, fair-balance controls, and reviewer-ready evidence packet.', 'Preserve source lineage for every claim and safety statement used downstream.'] },
    { title: 'Required records', lines: ['Approved claims, references, CSR synopsis, SmPC/PI, publication plan, safety statement library, and redline log.', 'Evidence strength, citation freshness, endpoint match, and population match are stored as validation facts.'] },
    { title: 'Controls', lines: ['Claim extraction, reference provenance, evidence alignment, off-label detection, fair balance, and MLR package completeness.'] },
  ] },
  { name: 'Compliance', icon: 'compliance', description: 'Policy, SOP, legal, privacy, approval authority, and exception controls.', items: ['Global SOP', 'Policy pack', 'Disclosure library', 'Approval matrix'], sections: [
    { title: 'Purpose', lines: ['Map content to current global SOPs, legal disclaimers, privacy requirements, approval matrix, and exception register.', 'Separate hard blockers from soft findings for global and local policy overlays.'] },
    { title: 'Required records', lines: ['Global promotional policy, local code overlays, privacy pack, legal disclaimer library, authority matrix, exception log, and audit trail.', 'Each override stores reason code, affected rule, reviewer ID, timestamp, and final recommendation.'] },
    { title: 'Controls', lines: ['Policy version match, disclosure completeness, privacy compliance, authority validation, escalation routing, and audit completeness.'] },
  ] },
  { name: 'Publishing', icon: 'email', description: 'Channel package, QA evidence, audience controls, tracking, and monitoring.', items: ['Email HTML', 'Litmus report', 'Audience list', 'Publish readiness token'], sections: [
    { title: 'Purpose', lines: ['Prepare final channel package with rendering evidence, link/CTA validation, consent checks, audience lock, and post-launch KPI stream.', 'Ensure final assets match the locked approved version before distribution.'] },
    { title: 'Required records', lines: ['Email HTML, CLM package, landing page spec, audience export, consent/suppression list, tracking map, Litmus report, and publish approval log.', 'Channel evidence remains connected to final asset ID and publish window.'] },
    { title: 'Controls', lines: ['Rendering QA, broken link scan, tracking compliance, audience validation, A/B parity, readiness token, and post-publish monitoring.'] },
  ] },
]
const activeImcpPillar = computed(() => imcpFramework.find(item => item.name === activeImcpName.value) || imcpFramework[0])
const damSources = computed(() => ['All sources', ...Array.from(new Set(sampleMedia.value.map(item => item.source_system || 'DAM'))).sort()])
const filteredDamMedia = computed(() => damSourceFilter.value === 'All sources' ? sampleMedia.value : sampleMedia.value.filter(item => (item.source_system || 'DAM') === damSourceFilter.value))
const activeUserTabLabel = computed(() => userTabs.find(tab => tab.id === activeUserTab.value)?.label || 'Accounts')
const filteredUsers = computed(() => {
  if (activeUserTab.value === 'inactive') return managedUsers.value.filter(user => user.status === 'inactive')
  if (activeUserTab.value === 'new') return managedUsers.value.filter(user => user.last_login === 'Never')
  return managedUsers.value.filter(user => user.status === 'active')
})
const viewTitle = computed(() => ({
  dashboard: 'Enterprise Dashboard',
  workflow: 'Authorization Workflow',
  dam: 'Digital Asset Management',
  library: 'Content Library',
  imcp: 'IMCP Framework',
  connections: 'Connections',
  audit: 'Audit Trail',
  profile: 'User Profile',
  users: 'User Management'
}[activeView.value] || 'MedGuard'))

watch(visibleStages, (items) => {
  if (!items.length) return
  if (!items.some(stage => stage.id === selectedStageId.value)) selectedStageId.value = items[0].id
})
watch(selectedStageId, async () => {
  activeBundle.value = selectedStage.value?.order && selectedStage.value.order > 1 ? workflowBundle.value : null
  compareResult.value = null
  activePreviewDocument.value = null
  selectedDocumentIds.value = activeBundle.value?.document_ids || []
  bundleName.value = selectedStage.value ? `${selectedStage.value.brand} ${selectedStage.value.name} source bundle` : ''
  selectedModelProfile.value = selectedStage.value?.default_model_profile || 'balanced'
  await loadDocuments()
  await loadStageOutputs()
})

onMounted(async () => {
  await loadAppData()
  if (consumeSsoRedirect()) return
  const saved = localStorage.getItem('col-console-user')
  if (!saved) return
  try {
    currentUser.value = JSON.parse(saved) as AppUser
    selectedStageId.value = visibleStages.value[0]?.id || ''
    if (isAdmin.value) await loadManagedUsers()
  } catch {
    localStorage.removeItem('col-console-user')
  }
})

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/')
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
  const binary = atob(padded)
  const bytes = Uint8Array.from(binary, char => char.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

function consumeSsoRedirect() {
  const params = new URLSearchParams(window.location.search)
  const error = params.get('sso_error')
  const encodedSession = params.get('sso_session')
  if (error) {
    authError.value = error
    window.history.replaceState({}, document.title, window.location.pathname)
    return false
  }
  if (!encodedSession) return false
  try {
    const session = JSON.parse(decodeBase64Url(encodedSession)) as AuthResponse
    currentUser.value = session.user
    localStorage.setItem('col-console-user', JSON.stringify(session.user))
    selectedStageId.value = visibleStages.value[0]?.id || ''
    ssoMessage.value = 'SSO sign-in complete.'
    window.history.replaceState({}, document.title, window.location.pathname)
    if (isAdmin.value) loadManagedUsers()
    return true
  } catch {
    authError.value = 'SSO sign-in completed, but the returned session could not be read.'
    window.history.replaceState({}, document.title, window.location.pathname)
    return false
  }
}

async function loadAppData() {
  const [stageData, connectionData, dashboardData, auditData, architectureData, ruleTemplateData, ruleRunData, notificationData, mediaData, modelData] = await Promise.all([
    $fetch<Stage[]>('/api/orchestration/stages'),
    $fetch<Connection[]>('/api/connections/status'),
    $fetch<Dashboard>('/api/dashboard/overview'),
    $fetch<AuditEvent[]>('/api/audit/events'),
    $fetch<ArchitectureFlow>('/api/architecture/flow'),
    $fetch<RuleStageTemplate[]>('/api/rule-engine/stages'),
    $fetch<RuleRun[]>('/api/rule-engine/runs'),
    $fetch<NotificationItem[]>('/api/notifications'),
    $fetch<SampleMedia[]>('/api/sample-media'),
    $fetch<AIModelProfile[]>('/api/ai-models')
  ])
  stages.value = stageData
  connections.value = connectionData
  dashboard.value = dashboardData
  auditEvents.value = auditData
  architectureFlow.value = architectureData
  ruleStageTemplates.value = ruleTemplateData
  ruleRuns.value = ruleRunData
  notifications.value = notificationData
  sampleMedia.value = mediaData
  aiModels.value = modelData
  Object.assign(filterState, { brands: lockedSelection.brand, markets: lockedSelection.market, channels: lockedSelection.channel, content_types: lockedSelection.contentType })
  Object.assign(documentSearch, { brand: lockedSelection.brand, market: lockedSelection.market, channel: lockedSelection.channel, document_type: lockedSelection.contentType })
  selectedModelProfile.value = selectedStage.value?.default_model_profile || modelData[1]?.id || modelData[0]?.id || 'balanced'
  Object.entries(dashboardData.filters).forEach(([key, values]) => {
    if (!filterState[key]) filterState[key] = values[0]
  })
  await loadDocuments()
  await loadContentLibrary()
  await loadStageOutputs()
}
async function normalizeLockedSelection(key: LockedSelectorKey) {
  if (!lockedAllowList[key].has(lockedSelection[key])) {
    lockedSelection[key] = Array.from(lockedAllowList[key])[0]
  }
  Object.assign(filterState, { brands: lockedSelection.brand, markets: lockedSelection.market, channels: lockedSelection.channel, content_types: lockedSelection.contentType })
  Object.assign(documentSearch, { brand: lockedSelection.brand, market: lockedSelection.market, channel: lockedSelection.channel, document_type: lockedSelection.contentType })
  selectedDocumentIds.value = []
  activeBundle.value = null
  workflowBundle.value = null
  await loadDashboard()
  await loadDocuments()
  await loadContentLibrary()
}
async function loadDashboard() {
  dashboard.value = await $fetch<Dashboard>('/api/dashboard/overview', {
    query: {
      markets: lockedSelection.market,
      brands: lockedSelection.brand,
      content_types: lockedSelection.contentType,
      risks: filterState.risks || '',
      channels: lockedSelection.channel,
      date_range: filterState.date_range || '',
    }
  })
}

function initials(name: string) {
  return name.split(' ').filter(Boolean).map(part => part[0]).join('').slice(0, 2).toUpperCase()
}
function formatFeature(feature: string) {
  return feature.split(/[-_]/).map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(' ')
}
function modelOptionLabel(model: AIModelProfile) {
  const recommended = selectedStage.value?.default_model_profile === model.id ? ' recommended' : ''
  return `${model.display || model.label}${recommended}`
}
function parseMarkdownTable(lines: string[]) {
  const rows = lines
    .map(line => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim()))
    .filter(row => row.some(Boolean))
    .filter(row => !row.every(cell => /^:?-{3,}:?$/.test(cell)))
  return { headers: rows[0] || [], rows: rows.slice(1) }
}
function parseReportContent(content: string): ReportBlock[] {
  const lines = content.split(/\r?\n/)
  const blocks: ReportBlock[] = []
  let index = 0
  while (index < lines.length) {
    const line = lines[index].trim()
    if (!line) {
      index += 1
      continue
    }
    if (line.startsWith('|')) {
      const tableLines: string[] = []
      while (index < lines.length && lines[index].trim().startsWith('|')) {
        tableLines.push(lines[index])
        index += 1
      }
      const table = parseMarkdownTable(tableLines)
      if (table.headers.length) blocks.push({ type: 'table', headers: table.headers, rows: table.rows })
      continue
    }
    if (line.startsWith('- ')) {
      const items: string[] = []
      while (index < lines.length && lines[index].trim().startsWith('- ')) {
        items.push(lines[index].trim().replace(/^- /, ''))
        index += 1
      }
      blocks.push({ type: 'list', items })
      continue
    }
    const nextLine = lines[index + 1]?.trim() || ''
    const isHeading = !line.includes('.') && line.length <= 70 && (nextLine === '' || nextLine.startsWith('- ') || nextLine.startsWith('|'))
    blocks.push({ type: isHeading ? 'heading' : 'paragraph', text: line })
    index += 1
  }
  return blocks
}
function docIcon(doc: LibraryDocument) {
  const type = doc.document_type.toLowerCase()
  if (type.includes('claim')) return 'claims'
  if (type.includes('clinical') || type.includes('study')) return 'evidence'
  if (type.includes('smpc') || type.includes('policy') || type.includes('sop')) return 'compliance'
  if (type.includes('email')) return 'email'
  if (type.includes('brand') || type.includes('creative')) return 'visual'
  if (type.includes('local')) return 'localization'
  return 'content'
}
function isImageUrl(url = '') {
  return /\.(svg|png|jpe?g|webp|gif)$/i.test(url)
}
function previewMedia(media: SampleMedia) {
  activePreviewMedia.value = media
}
async function loadDocuments() {
  const stageId = selectedStage.value?.id || ''
  const response = await $fetch<DocumentSearchResponse>('/api/documents/search', {
    query: { ...documentSearch, brand: lockedSelection.brand, market: lockedSelection.market, channel: '', document_type: '', stage_id: stageId }
  })
  libraryDocuments.value = response.documents
  Object.assign(documentFacets, response.facets)
  if (documentPanelLocked.value && workflowBundle.value) {
    selectedDocumentIds.value = workflowBundle.value.document_ids
    activeBundle.value = workflowBundle.value
    return
  }
  if (!selectedDocumentIds.value.length) {
    const autoDocs = stageId === 'briefing'
      ? primaryStageDocuments.value.slice(0, 3)
      : response.documents.filter(doc => doc.approval_status === 'approved' && !isValidationSourceDocument(doc)).slice(0, 6)
    selectedDocumentIds.value = (autoDocs.length ? autoDocs : response.documents.slice(0, stageId === 'briefing' ? 3 : 6)).map(doc => doc.id)
  }
  if (!bundleName.value && selectedStage.value) bundleName.value = `${selectedStage.value.brand} ${selectedStage.value.name} source bundle`
}
async function ensureWorkflowBundle() {
  if (!selectedStage.value || !currentUser.value) return null
  if (workflowBundle.value) {
    activeBundle.value = workflowBundle.value
    return workflowBundle.value
  }
  const documentIds = selectedDocumentIds.value.length
    ? selectedDocumentIds.value
    : (selectedStage.value.id === 'briefing'
      ? primaryStageDocuments.value.slice(0, 3)
      : libraryDocuments.value.filter(doc => doc.approval_status === 'approved' && !isValidationSourceDocument(doc)).slice(0, 6)
    ).map(doc => doc.id)
  if (!documentIds.length) return null
  activeBundle.value = await $fetch<InputBundle>('/api/input-bundles', {
    method: 'POST',
    body: {
      actor_email: currentUser.value.email,
      stage_id: selectedStage.value.id,
      name: bundleName.value || `${selectedStage.value.brand} frozen validation bundle`,
      document_ids: documentIds,
      notes: 'Auto-frozen source bundle for end-to-end validation.'
    }
  })
  workflowBundle.value = activeBundle.value
  selectedDocumentIds.value = activeBundle.value.document_ids
  bundleMessage.value = `${activeBundle.value.documents.length} linked source document(s) frozen from selected brief.`
  return activeBundle.value
}
async function loadContentLibrary() {
  const response = await $fetch<DocumentSearchResponse>('/api/documents/search', {
    query: { q: documentSearch.q, brand: lockedSelection.brand, document_type: lockedSelection.contentType, market: lockedSelection.market, channel: '' }
  })
  contentLibraryDocuments.value = response.documents
  Object.assign(documentFacets, response.facets)
}
async function loadStageOutputs() {
  stageOutputs.value = await $fetch<StageOutputDocument[]>('/api/stage-outputs', { query: { stage_id: selectedStage.value?.id || '' } })
}
function toggleDocumentSelection(doc: LibraryDocument) {
  if (selectedDocumentIds.value.includes(doc.id)) {
    selectedDocumentIds.value = selectedDocumentIds.value.filter(id => id !== doc.id)
  } else {
    selectedDocumentIds.value = [...selectedDocumentIds.value, doc.id]
  }
}
async function previewDocument(doc: LibraryDocument) {
  const result = await $fetch<{ document: LibraryDocument }>('/api/documents/' + doc.id)
  activePreviewDocument.value = result.document
}
async function createInputBundle() {
  if (!selectedStage.value || !currentUser.value) return
  bundleError.value = ''
  bundleMessage.value = ''
  try {
    activeBundle.value = await $fetch<InputBundle>('/api/input-bundles', {
      method: 'POST',
      body: {
        actor_email: currentUser.value.email,
        stage_id: selectedStage.value.id,
        name: bundleName.value || `${selectedStage.value.name} source bundle`,
        document_ids: selectedDocumentIds.value,
        notes: actionCommand.value
      }
    })
    if (selectedStage.value.order === 1 || !workflowBundle.value) workflowBundle.value = activeBundle.value
    bundleMessage.value = `${activeBundle.value.documents.length} source document(s) bundled.`
    await loadAudit()
  } catch (error: any) {
    bundleError.value = error?.data?.detail || error?.message || 'Could not create input bundle.'
  }
}
async function compareSelectedDocuments() {
  bundleError.value = ''
  try {
    compareResult.value = await $fetch<DocumentCompareResult>('/api/documents/compare', { method: 'POST', body: { document_ids: selectedDocumentIds.value } })
  } catch (error: any) {
    bundleError.value = error?.data?.detail || error?.message || 'Select at least two documents to compare.'
  }
}
function selectStageByName(name: string) {
  const stage = stages.value.find(item => item.name === name)
  if (!stage) return
  selectedStageId.value = stage.id
  activeView.value = 'workflow'
}
function openNotification(note: NotificationItem) {
  showNotificationMenu.value = false
  if (note.stage_id) selectedStageId.value = note.stage_id
  activeView.value = note.stage_id ? 'workflow' : 'audit'
}
function syncAccessDrafts() {
  managedUsers.value.forEach(user => {
    accessDrafts[user.id] = { role: user.role, team: user.team, persona: user.persona }
  })
}

async function signIn() {
  authError.value = ''
  ssoMessage.value = ''
  authLoading.value = true
  try {
    const result = await $fetch<AuthResponse>('/api/auth/login', { method: 'POST', body: { email: loginForm.email.trim(), password: loginForm.password.trim() } })
    currentUser.value = result.user
    localStorage.setItem('col-console-user', JSON.stringify(result.user))
    selectedStageId.value = visibleStages.value[0]?.id || ''
    if (isAdmin.value) await loadManagedUsers()
  } catch (error: any) {
    authError.value = error?.data?.detail || error?.message || 'Login failed.'
  } finally {
    authLoading.value = false
  }
}
async function startSso(provider: 'Google' | 'Microsoft') {
  authError.value = ''
  ssoMessage.value = `Starting ${provider} SSO...`
  authLoading.value = true
  const providerKey = provider === 'Google' ? 'google' : 'microsoft'
  try {
    const result = await $fetch<{ authorization_url: string }>(`/api/auth/sso/${providerKey}/start`)
    window.location.href = result.authorization_url
  } catch (error: any) {
    authError.value = error?.data?.detail || error?.message || `${provider} SSO is not configured.`
    ssoMessage.value = ''
    authLoading.value = false
  }
}
function signOut() {
  currentUser.value = null
  managedUsers.value = []
  activeView.value = 'dashboard'
  sidebarHidden.value = false
  localStorage.removeItem('col-console-user')
}
async function runSelectedStage() {
  if (!selectedStage.value) return
  stageRunLoading.value = true
  decisionMessage.value = ''
  try {
    const result = await $fetch<{ stage: Stage; dashboard: Dashboard; rule_engine?: RuleRun; output_document?: StageOutputDocument }>('/api/orchestration/run', {
      method: 'POST',
      body: {
        stage_id: selectedStage.value.id,
        actor_email: currentUser.value?.email || '',
        use_gemini: true,
        model_profile: selectedStage.value.default_model_profile || 'auto',
        bundle_id: activeBundle.value?.id || '',
        action_context: actionCommand.value
      }
    })
    const index = stages.value.findIndex(stage => stage.id === result.stage.id)
    if (index >= 0) stages.value[index] = result.stage
    if (result.rule_engine) upsertRuleRun(result.rule_engine)
    dashboard.value = result.dashboard
    decisionMessage.value = `Validation completed for ${result.stage.name}.`
    await loadAudit()
    notifications.value = await $fetch<NotificationItem[]>('/api/notifications')
  } catch (error: any) {
    decisionError.value = error?.data?.detail || error?.message || 'Stage validation failed.'
  } finally {
    stageRunLoading.value = false
  }
}
function upsertRuleRun(run: RuleRun) {
  const index = ruleRuns.value.findIndex(item => item.run_id === run.run_id || item.stage_id === run.stage_id)
  if (index >= 0) ruleRuns.value[index] = run
  else ruleRuns.value.unshift(run)
}
function sleep(ms: number) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
function stepDisplayStatus(step: RuleStep): RuleStepStatus {
  const stageId = selectedStage.value?.id || ''
  return ruleProgress[stageId]?.statuses[step.id] || step.status || 'queued'
}
async function animateRuleRun(run: RuleRun, delay = 420) {
  const state = ruleProgress[run.stage_id] = { running: true, activeIndex: 0, statuses: {}, percent: 0 }
  run.steps.forEach(step => { state.statuses[step.id] = 'running' })
  for (let index = 0; index < run.steps.length; index += 1) {
    const step = run.steps[index]
    state.activeIndex = index
    state.statuses[step.id] = 'running'
    state.percent = Math.round((index / run.steps.length) * 100)
    await sleep(delay)
    state.statuses[step.id] = step.status === 'blocked' ? 'failed' : step.status
    state.percent = Math.round(((index + 1) / run.steps.length) * 100)
  }
  state.running = false
}
async function runStageRuleEngine() {
  if (!selectedStage.value || !currentUser.value) return
  stageRunLoading.value = true
  decisionError.value = ''
  decisionMessage.value = ''
  try {
    await ensureWorkflowBundle()
    runButtonPulse.value = true
    setTimeout(() => { runButtonPulse.value = false }, 420)
    const pendingRun: RuleRun = {
      run_id: `PENDING-${selectedStage.value.id}`,
      content_id: selectedStage.value.asset_id,
      stage_id: selectedStage.value.id,
      stage: selectedStage.value.name,
      purpose: selectedRuleTemplate.value?.purpose || selectedStage.value.engine_label,
      threshold: selectedRuleTemplate.value?.threshold || 0,
      stage_score: selectedStage.value.validation_score,
      status: 'REWORK',
      mandatory_checks_passed: 0,
      mandatory_checks_total: selectedRuleSteps.value.length,
      critical_blockers: [],
      risk_flags: [],
      kpis: {},
      reviewer_action_required: true,
      audit_id: 'pending',
      steps: selectedRuleSteps.value.map(step => ({ ...step, status: 'queued', summary: 'Queued for validation run.' })),
      media: selectedMedia.value,
      selected_documents: selectedValidationDocuments.value,
      model_profile: activeModel.value,
      approval: { status: 'pending', actor: '', reason: '', timestamp: '' }
    }
    upsertRuleRun(pendingRun)
    const pendingAnimation = animateRuleRun(pendingRun, 260)
    const result = await $fetch<{ run: RuleRun; stage: Stage; dashboard: Dashboard; output_document?: StageOutputDocument }>('/api/rule-engine/run', {
      method: 'POST',
      body: {
        stage_id: selectedStage.value.id,
        content_id: selectedStage.value.asset_id,
        actor_email: currentUser.value.email,
        use_gemini: true,
        model_profile: selectedModelProfile.value || selectedStage.value.default_model_profile || 'auto',
        bundle_id: activeBundle.value?.id || '',
        action_context: actionCommand.value
      }
    })
    await pendingAnimation
    if (result.stage) {
      const index = stages.value.findIndex(stage => stage.id === result.stage.id)
      if (index >= 0) stages.value[index] = result.stage
    }
    dashboard.value = result.dashboard
    upsertRuleRun(result.run)
    await animateRuleRun(result.run)
    notifications.value = await $fetch<NotificationItem[]>('/api/notifications')
    await loadAudit()
    decisionMessage.value = `${result.run.stage} returned ${result.run.status} with ${result.run.stage_score}% score.`
  } catch (error: any) {
    decisionError.value = error?.data?.detail || error?.message || 'Rule engine failed.'
  } finally {
    stageRunLoading.value = false
  }
}
async function rerunRuleStep(step: RuleStep) {
  if (!selectedStage.value || !currentUser.value) return
  const stageId = selectedStage.value.id
  const state = ruleProgress[stageId] || (ruleProgress[stageId] = { running: false, activeIndex: 0, statuses: {}, percent: 0 })
  state.statuses[step.id] = 'running'
  stageRunLoading.value = true
  decisionMessage.value = `Rerunning ${step.name}.`
  try {
    await sleep(360)
    const result = await $fetch<{ run: RuleRun; stage: Stage; dashboard: Dashboard; output_document?: StageOutputDocument }>('/api/rule-engine/run', {
      method: 'POST',
      body: {
        stage_id: selectedStage.value.id,
        content_id: selectedStage.value.asset_id,
        actor_email: currentUser.value.email,
        use_gemini: true,
        model_profile: selectedModelProfile.value || selectedStage.value.default_model_profile || 'auto',
        bundle_id: activeBundle.value?.id || '',
        action_context: `Rerun individual validation step: ${step.name}. ${ruleStepComments[step.id] || ''}`
      }
    })
    upsertRuleRun(result.run)
    if (result.stage) {
      const index = stages.value.findIndex(stage => stage.id === result.stage.id)
      if (index >= 0) stages.value[index] = result.stage
    }
    dashboard.value = result.dashboard
    const updatedStep = result.run.steps.find(item => item.id === step.id)
    state.statuses[step.id] = updatedStep?.status || step.status
    decisionMessage.value = `${step.name} rerun completed.`
    await loadAudit()
    await loadStageOutputs()
  } catch (error: any) {
    state.statuses[step.id] = 'failed'
    decisionError.value = error?.data?.detail || error?.message || 'Step rerun failed.'
  } finally {
    stageRunLoading.value = false
  }
}
async function submitRuleApproval(stepId = 'overall', action: 'approve' | 'request_changes' | 'override' = 'approve') {
  if (!currentUser.value || !selectedStage.value) return
  decisionError.value = ''
  decisionMessage.value = ''
  try {
    const response = await $fetch<{ runs: RuleRun[]; dashboard: Dashboard }>('/api/rule-engine/approval', {
      method: 'POST',
      body: {
        actor_email: currentUser.value.email,
        stage_id: selectedStage.value.id,
        step_id: stepId,
        action,
        reason: action === 'approve' ? ruleDecisionReason.value || 'Reviewer approved validation result.' : ruleDecisionReason.value,
        reason_code: ruleDecisionCode.value,
        affected_rule: stepId
      }
    })
    ruleRuns.value = response.runs
    dashboard.value = response.dashboard
    ruleDecisionReason.value = ''
    decisionMessage.value = action === 'approve' ? 'Approval captured.' : 'Reviewer input captured.'
    await loadAudit()
  } catch (error: any) {
    decisionError.value = error?.data?.detail || error?.message || 'Approval could not be captured.'
  }
}
async function submitWorkflowAction(actionType: 'accept' | 'reject' | 'edit_output' | 'comment' | 'override' | 'rerun' | 'escalate' | 'request_rework' | 'send_next_stage', step?: RuleStep) {
  if (!currentUser.value || !selectedStage.value) return
  decisionError.value = ''
  decisionMessage.value = ''
  const affectedStep = step || selectedRuleSteps.value.find(item => item.status !== 'passed' || item.score < 80)
  const stepComment = step ? (ruleStepComments[step.id] || '').trim() : ''
  const command = stepComment
    || actionCommand.value.trim()
    || (actionType === 'request_rework' && affectedStep ? `Raise validation flag for ${affectedStep.name}: score ${affectedStep.score}% is below the 80% rework threshold.` : '')
    || (actionType === 'send_next_stage' ? 'Reviewer confirmed thumbs-up to continue to the next validation check.' : '')
    || 'Reviewer action captured.'
  try {
    const response = await $fetch<{ stage: Stage; dashboard: Dashboard }>('/api/workflow/actions', {
      method: 'POST',
      body: {
        actor_email: currentUser.value.email,
        stage_id: selectedStage.value.id,
        action_type: actionType,
        command,
        output_text: actionType === 'edit_output' ? command : '',
        reason_code: actionType,
        affected_rule: affectedStep?.id || 'overall'
      }
    })
    const index = stages.value.findIndex(stage => stage.id === response.stage.id)
    if (index >= 0) stages.value[index] = response.stage
    dashboard.value = response.dashboard
    if (step) ruleStepComments[step.id] = ''
    actionCommand.value = ''
    decisionMessage.value = `${formatFeature(actionType)} captured.`
    await loadAudit()
    await loadStageOutputs()
  } catch (error: any) {
    decisionError.value = error?.data?.detail || error?.message || 'Workflow action could not be captured.'
  }
}
function completeTask(task: StageTask) {
  task.status = 'complete'
  decisionMessage.value = `${task.id} marked complete.`
}
function addDamAsset() {
  if (!selectedStage.value || !damForm.name.trim()) return
  sampleMedia.value.unshift({
    id: `dam-${Date.now()}`,
    name: damForm.name.trim(),
    type: damForm.type,
    mime_type: damForm.url.endsWith('.svg') ? 'image/svg+xml' : damForm.url.endsWith('.html') ? 'text/html' : 'application/link',
    url: damForm.url.trim() || undefined,
    source_system: damForm.source_system,
    connector_status: 'added',
    stage_ids: [selectedStage.value.id],
    preview: damForm.preview.trim() || 'User-added DAM source for this workflow stage.',
    checks: ['source availability', 'metadata review', 'stage relevance'],
    risk_notes: ['Newly added by reviewer; validate before final approval.']
  })
  Object.assign(damForm, { name: '', type: 'Reference Pack', source_system: 'Veeva Vault', url: '', preview: '' })
}
async function submitDecision(action: 'accept' | 'override') {
  if (!currentUser.value || !selectedStage.value) return
  decisionError.value = ''
  decisionMessage.value = ''
  try {
    await $fetch('/api/orchestration/decision', { method: 'POST', body: { actor_email: currentUser.value.email, stage_id: selectedStage.value.id, action, reason: action === 'override' ? overrideReason.value : '' } })
    overrideReason.value = ''
    decisionMessage.value = action === 'accept' ? 'Recommendation accepted.' : 'Override captured.'
    await loadAudit()
  } catch (error: any) {
    decisionError.value = error?.data?.detail || error?.message || 'Decision could not be captured.'
  }
}
async function loadAudit() {
  auditEvents.value = await $fetch<AuditEvent[]>('/api/audit/events', {
    query: {
      q: auditFilters.q,
      severity: auditFilters.severity,
      stage: auditFilters.stage,
      actor: auditFilters.actor,
      source_system: auditFilters.source_system,
    }
  })
}
async function clearAuditFilters() {
  Object.assign(auditFilters, { q: '', severity: '', stage: '', actor: '', source_system: '' })
  await loadAudit()
}
async function createConnector() {
  if (!currentUser.value) return
  connectionError.value = ''
  connectionMessage.value = ''
  try {
    const body = { actor_email: currentUser.value.email, ...connectorForm }
    if (editingConnectorId.value) {
      await $fetch(`/api/connections/${editingConnectorId.value}`, { method: 'PUT', body })
      connectionMessage.value = 'Connector updated.'
    } else {
      await $fetch('/api/connections', { method: 'POST', body })
      connectionMessage.value = 'Connector added.'
    }
    Object.assign(connectorForm, { name: '', scope: '', auth_method: 'OAuth 2.0', owner: 'Platform Governance', status: 'candidate', icon: 'integration', scopes: ['metadata.read', 'audit.write'] })
    editingConnectorId.value = ''
    showConnectorForm.value = false
    connections.value = await $fetch<Connection[]>('/api/connections/status')
  } catch (error: any) {
    connectionError.value = error?.data?.detail || error?.message || 'Connector action failed.'
  }
}
function editConnector(connection: Connection) {
  editingConnectorId.value = connection.id
  Object.assign(connectorForm, { name: connection.name, scope: connection.scope, auth_method: connection.auth_method, owner: connection.owner, status: connection.status, icon: connection.icon || 'integration', scopes: connection.scopes })
}
async function testConnector(connection: Connection) {
  if (!currentUser.value) return
  await $fetch(`/api/connections/${connection.id}/test`, { method: 'POST', body: { actor_email: currentUser.value.email } })
  connectionMessage.value = `${connection.name} tested successfully.`
  connections.value = await $fetch<Connection[]>('/api/connections/status')
}
async function toggleConnector(connection: Connection) {
  if (!currentUser.value) return
  await $fetch(`/api/connections/${connection.id}`, { method: 'PUT', body: { actor_email: currentUser.value.email, name: connection.name, scope: connection.scope, auth_method: connection.auth_method, owner: connection.owner, status: connection.status === 'disabled' ? 'connected' : 'disabled', icon: connection.icon || 'integration', scopes: connection.scopes } })
  connections.value = await $fetch<Connection[]>('/api/connections/status')
}
async function deleteConnector(connection: Connection) {
  if (!currentUser.value) return
  await $fetch(`/api/connections/${connection.id}`, { method: 'DELETE', query: { actor_email: currentUser.value.email } })
  connections.value = await $fetch<Connection[]>('/api/connections/status')
}
async function changeOwnPassword() {
  if (!currentUser.value) return
  profileError.value = ''
  profileMessage.value = ''
  try {
    await $fetch('/api/profile/password', { method: 'POST', body: { email: currentUser.value.email, current_password: profilePasswordForm.current.trim(), new_password: profilePasswordForm.next.trim() } })
    profilePasswordForm.current = ''
    profilePasswordForm.next = ''
    profileMessage.value = 'Password updated.'
  } catch (error: any) {
    profileError.value = error?.data?.detail || error?.message || 'Could not update password.'
  }
}
async function loadManagedUsers() {
  if (!currentUser.value || !isAdmin.value) return
  managedUsers.value = await $fetch<AppUser[]>('/api/users', { query: { actor_email: currentUser.value.email } })
  syncAccessDrafts()
}
async function createManagedUser() {
  if (!currentUser.value) return
  adminError.value = ''
  adminMessage.value = ''
  adminLoading.value = true
  try {
    await $fetch<AppUser>('/api/users', { method: 'POST', body: { actor_email: currentUser.value.email, ...createUserForm, password: '12345', modules: ['workflow-orchestration', 'claims-governance', 'compliance', 'analytics'] } })
    Object.assign(createUserForm, { name: '', email: '', role: 'content_author', persona: '', team: '' })
    showUserCreateForm.value = false
    adminMessage.value = 'User created.'
    await loadManagedUsers()
  } catch (error: any) {
    adminError.value = error?.data?.detail || error?.message || 'Could not create user.'
  } finally {
    adminLoading.value = false
  }
}
async function saveUserAccess(user: AppUser) {
  if (!currentUser.value) return
  const draft = accessDrafts[user.id]
  await $fetch(`/api/users/${user.id}/access`, { method: 'POST', body: { actor_email: currentUser.value.email, role: draft.role, team: draft.team, persona: draft.persona, modules: user.modules } })
  adminMessage.value = `Access updated for ${user.email}.`
  await loadManagedUsers()
}
async function changeUserPassword(user: AppUser) {
  if (!currentUser.value) return
  const password = passwordDrafts[user.id]?.trim()
  if (!password) {
    adminError.value = 'Enter a new password first.'
    return
  }
  await $fetch(`/api/users/${user.id}/password`, { method: 'POST', body: { actor_email: currentUser.value.email, password } })
  passwordDrafts[user.id] = ''
  adminMessage.value = `Password changed for ${user.email}.`
  await loadManagedUsers()
}
async function resetUserPassword(user: AppUser) {
  if (!currentUser.value) return
  await $fetch(`/api/users/${user.id}/password/reset`, { method: 'POST', body: { actor_email: currentUser.value.email } })
  adminMessage.value = `Password reset for ${user.email}.`
  await loadManagedUsers()
}
async function toggleUserStatus(user: AppUser) {
  if (!currentUser.value) return
  await $fetch<AppUser>(`/api/users/${user.id}/status`, { method: 'POST', body: { actor_email: currentUser.value.email, status: user.status === 'active' ? 'inactive' : 'active' } })
  adminMessage.value = `Status updated for ${user.email}.`
  await loadManagedUsers()
}
async function deleteManagedUser(user: AppUser) {
  if (!currentUser.value) return
  await $fetch(`/api/users/${user.id}`, { method: 'DELETE', query: { actor_email: currentUser.value.email } })
  adminMessage.value = `Deleted ${user.email}.`
  await loadManagedUsers()
}
</script>
